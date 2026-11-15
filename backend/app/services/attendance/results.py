"""Database-to-contract adapter and result persistence for calculation.

The pure kernel in :mod:`app.services.attendance.calc` never reads the
database. This module is the only place that turns committed import batches,
roster entries, holidays, and effective rules into frozen contract inputs, and
the only place that writes day results, shift results, and month summaries
(spec sections 7.1, 7.12, and 4.9).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import ColumnElement, delete, func, not_, or_
from sqlmodel import Session, col, select

from app.core.errors import DomainError
from app.enums import (
    DayStatus,
    DayType,
    ImportBatchStatus,
    ImportDataType,
    PlanStatus,
    ResultRosterState,
    RosterState,
    TripKind,
)
from app.models import (
    AttendanceDayResult,
    AttendanceDayShiftResult,
    AttendanceMonth,
    AttendanceMonthSummary,
    AttendanceResultAdjustment,
    CalcRun,
    Department,
    Employee,
    Holiday,
    ImportBatch,
    OaLeave,
    OaOvertime,
    OaOvertimeDay,
    OaTrip,
    PlanRuleOverride,
    PunchRecord,
    RosterEntry,
    RosterEntryShift,
    SchedulePlan,
    User,
)
from app.schemas_attendance.common import EmployeeDisplay
from app.schemas_attendance.core import (
    CalcRunSummary,
    HolidaySnapshot,
    InputBatches,
    InputBatchInfo,
    PlanRuleOverrideSnapshot,
    RuleSnapshotPatch,
    RulesSnapshot,
    RuleValues,
)
from app.schemas_attendance.imports import (
    OaLeavePublic,
    OaOvertimeDayPublic,
    OaTripPublic,
    PunchRecordPublic,
)
from app.schemas_attendance.results import (
    ABNORMAL_DAY_FLAGS,
    ABNORMAL_DAY_STATUSES,
    AttendanceAdjustmentPublic,
    AttendanceDayDetailPublic,
    AttendanceDayResultPublic,
    AttendanceDayResultsPublic,
    AttendanceDayShiftResultPublic,
    AttendanceMonthSummariesPublic,
    AttendanceMonthSummaryPublic,
    EmployeeResultCalendarPublic,
)
from app.schemas_attendance.scheduling import (
    RosterEntryPublic,
    RosterEntryShiftPublic,
)
from app.services.attendance.calc import (
    DayResult,
    Leave,
    MonthInputs,
    MonthOutputs,
    OvertimeDay,
    Punch,
    Rules,
    RunSummary,
    ShiftSnapshot,
    Trip,
)
from app.services.attendance.calc import (
    Employee as CalcEmployee,
)
from app.services.attendance.calc import (
    Holiday as CalcHoliday,
)
from app.services.attendance.calc import (
    RosterEntry as CalcRosterEntry,
)
from app.services.attendance.calc._common import amount_value, day_value, hours_value
from app.services.attendance.errors import AttendanceErrorCode
from app.services.attendance.expansion import month_bounds
from app.services.attendance.month_state import existing_month
from app.services.attendance.rules import (
    RULE_FIELDS,
    SYSTEM_DEFAULT_RULE_VALUES,
    company_default_values,
)
from app.services.common import paginate
from app.services.companies import get_company_or_404

SHANGHAI = ZoneInfo("Asia/Shanghai")

DAY_RESULT_NOT_FOUND_MESSAGE = "日结果不存在"
EMPLOYEE_NOT_FOUND_MESSAGE = "员工不存在"
DEPARTMENT_NOT_FOUND_MESSAGE = "部门不存在"


@dataclass(frozen=True, slots=True)
class MonthCalculationData:
    """Contract inputs plus the audit snapshots written to ``calc_run``."""

    inputs: MonthInputs
    rules_snapshot: dict[str, Any]
    input_batches: dict[str, Any]
    rules_version: str
    roster_version: str
    # Keyed by the kernel's ordinal shift position, not the stored roster seq.
    shift_ids: dict[tuple[uuid.UUID, date, int], uuid.UUID]


def canonical_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _to_shanghai(value: datetime) -> datetime:
    """Stored timestamps are UTC-aware; calculation works in Asia/Shanghai."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(SHANGHAI)


def _batch_by_type(
    session: Session, company_id: uuid.UUID, month: date
) -> dict[ImportDataType, ImportBatch]:
    batches = session.exec(
        select(ImportBatch)
        .where(
            col(ImportBatch.company_id) == company_id,
            col(ImportBatch.month) == month,
            col(ImportBatch.status) == ImportBatchStatus.COMMITTED,
        )
        .order_by(col(ImportBatch.committed_at).desc(), col(ImportBatch.id).desc())
    ).all()
    by_type: dict[ImportDataType, ImportBatch] = {}
    for batch in batches:
        by_type.setdefault(batch.data_type, batch)
    return by_type


def _batch_info(batch: ImportBatch) -> InputBatchInfo:
    return InputBatchInfo(
        id=batch.id,
        committed_at=batch.committed_at,
        file_name=batch.file_name,
        source_rows=batch.source_rows,
        valid_records=batch.valid_records,
    )


def _input_batches(by_type: dict[ImportDataType, ImportBatch]) -> dict[str, Any]:
    def info(data_type: ImportDataType) -> InputBatchInfo | None:
        batch = by_type.get(data_type)
        return _batch_info(batch) if batch is not None else None

    return InputBatches(
        punch=info(ImportDataType.PUNCH),
        trip=info(ImportDataType.TRIP),
        ot=info(ImportDataType.OT),
        leave=info(ImportDataType.LEAVE),
    ).model_dump(mode="json")


def _load_employees(
    session: Session, company_id: uuid.UUID, start: date, end: date
) -> list[tuple[Employee, Department]]:
    return list(
        session.exec(
            select(Employee, Department)
            .join(Department, col(Employee.dept_id) == col(Department.id))
            .where(
                col(Department.company_id) == company_id,
                col(Employee.hire_date) <= end,
                or_(
                    col(Employee.resign_date).is_(None),
                    col(Employee.resign_date) >= start,
                ),
            )
            .order_by(col(Employee.employee_no).asc(), col(Employee.id).asc())
        ).all()
    )


def _load_roster(
    session: Session,
    company_id: uuid.UUID,
    start: date,
    end: date,
    *,
    work_only: bool = False,
) -> list[tuple[RosterEntry, list[RosterEntryShift]]]:
    filters = [
        col(RosterEntry.company_id) == company_id,
        col(RosterEntry.work_date) >= start,
        col(RosterEntry.work_date) <= end,
    ]
    if work_only:
        filters.append(col(RosterEntry.state) == RosterState.WORK)
    entries = list(
        session.exec(
            select(RosterEntry)
            .where(*filters)
            .order_by(
                col(RosterEntry.employee_id).asc(),
                col(RosterEntry.work_date).asc(),
            )
        ).all()
    )
    shift_rows: dict[uuid.UUID, list[RosterEntryShift]] = {}
    if entries:
        for row in session.exec(
            select(RosterEntryShift)
            .where(
                col(RosterEntryShift.roster_entry_id).in_(
                    [entry.id for entry in entries]
                )
            )
            .order_by(
                col(RosterEntryShift.roster_entry_id).asc(),
                col(RosterEntryShift.seq).asc(),
            )
        ).all():
            shift_rows.setdefault(row.roster_entry_id, []).append(row)
    return [(entry, shift_rows.get(entry.id, [])) for entry in entries]


def _shift_snapshot(row: RosterEntryShift) -> ShiftSnapshot:
    return ShiftSnapshot(
        shift_code=row.shift_code,
        shift_name=row.shift_name,
        start_time=row.start_time,
        end_time=row.end_time,
        cross_day=row.cross_day,
        break_start=row.break_start,
        break_end=row.break_end,
        rest_minutes=row.rest_minutes,
    )


def _contract_rules(values: dict[str, Any]) -> Rules:
    return Rules(**{field: values[field] for field in RULE_FIELDS})


def _override_values(row: PlanRuleOverride) -> dict[str, Any]:
    return {field: getattr(row, field) for field in RULE_FIELDS}


def _effective_rules(defaults: dict[str, Any], overrides: dict[str, Any]) -> Rules:
    return _contract_rules(
        {
            field: (
                overrides[field] if overrides[field] is not None else defaults[field]
            )
            for field in RULE_FIELDS
        }
    )


def _load_rules(
    session: Session, company_id: uuid.UUID, month: date
) -> tuple[dict[str, Any], dict[uuid.UUID, Rules], list[PlanRuleOverrideSnapshot]]:
    defaults = company_default_values(session, company_id)
    plans = list(
        session.exec(
            select(SchedulePlan)
            .where(
                col(SchedulePlan.company_id) == company_id,
                col(SchedulePlan.month) == month,
                col(SchedulePlan.status) == PlanStatus.ENABLED,
            )
            .order_by(col(SchedulePlan.id).asc())
        ).all()
    )
    override_rows: dict[uuid.UUID, PlanRuleOverride] = {}
    if plans:
        for row in session.exec(
            select(PlanRuleOverride).where(
                col(PlanRuleOverride.plan_id).in_([plan.id for plan in plans])
            )
        ).all():
            override_rows[row.plan_id] = row

    effective_by_plan: dict[uuid.UUID, Rules] = {}
    snapshots: list[PlanRuleOverrideSnapshot] = []
    for plan in plans:
        override = override_rows.get(plan.id)
        if override is None:
            continue
        values = _override_values(override)
        if all(value is None for value in values.values()):
            continue
        effective_by_plan[plan.id] = _effective_rules(defaults, values)
        snapshots.append(
            PlanRuleOverrideSnapshot(
                plan_id=plan.id,
                overrides=RuleSnapshotPatch.model_validate(values),
            )
        )
    return defaults, effective_by_plan, snapshots


def _load_holidays(
    session: Session, company_id: uuid.UUID, start: date, end: date
) -> list[Holiday]:
    return list(
        session.exec(
            select(Holiday)
            .where(
                col(Holiday.company_id) == company_id,
                col(Holiday.date) >= start,
                col(Holiday.date) <= end,
            )
            .order_by(col(Holiday.date).asc())
        ).all()
    )


def _trip_kind(application_type_raw: str | None) -> TripKind:
    return (
        TripKind.BUSINESS
        if application_type_raw and "出差" in application_type_raw
        else TripKind.OUT
    )


def _roster_payload(
    roster: tuple[CalcRosterEntry, ...],
    adjacent: tuple[CalcRosterEntry, ...],
) -> dict[str, Any]:
    def entry_json(entry: CalcRosterEntry) -> dict[str, Any]:
        return {
            "employee_id": entry.employee_id,
            "work_date": entry.work_date.isoformat(),
            "state": entry.state.value,
            "shifts": [
                {
                    "shift_code": shift.shift_code,
                    "shift_name": shift.shift_name,
                    "start_time": shift.start_time.isoformat(),
                    "end_time": shift.end_time.isoformat(),
                    "cross_day": shift.cross_day,
                    "break_start": (
                        shift.break_start.isoformat() if shift.break_start else None
                    ),
                    "break_end": (
                        shift.break_end.isoformat() if shift.break_end else None
                    ),
                    "rest_minutes": shift.rest_minutes,
                }
                for shift in entry.shifts
            ],
        }

    return {
        "roster": [entry_json(entry) for entry in roster],
        "adjacent": [entry_json(entry) for entry in adjacent],
    }


def roster_fingerprint(
    roster: tuple[CalcRosterEntry, ...],
    adjacent: tuple[CalcRosterEntry, ...],
) -> str:
    """Hash the normalized roster input used by one calculation."""
    return canonical_hash(_roster_payload(roster, adjacent))


def build_month_inputs(
    session: Session, *, company_id: uuid.UUID, month: date
) -> MonthCalculationData:
    """Build the frozen kernel inputs from database state only.

    Calculation reads committed batches and roster snapshots; it never
    re-resolves plans (ADR-0004) and never reads preview or discarded batch
    rows (ADR-0005).
    """
    month = month.replace(day=1)
    start, end = month_bounds(month)
    batches = _batch_by_type(session, company_id, month)

    employees = _load_employees(session, company_id, start, end)
    employee_ids = {employee.id for employee, _department in employees}

    roster_rows = _load_roster(session, company_id, start, end)
    defaults, effective_by_plan, plan_snapshots = _load_rules(
        session, company_id, month
    )

    roster: list[CalcRosterEntry] = []
    shift_ids: dict[tuple[uuid.UUID, date, int], uuid.UUID] = {}
    for entry, shift_rows in roster_rows:
        if entry.employee_id not in employee_ids:
            continue
        rules = effective_by_plan.get(entry.plan_id) if entry.plan_id else None
        roster.append(
            CalcRosterEntry(
                employee_id=str(entry.employee_id),
                work_date=entry.work_date,
                state=entry.state,
                shifts=tuple(_shift_snapshot(row) for row in shift_rows),
                rules=rules,
            )
        )
        for ordinal, row in enumerate(shift_rows):
            shift_ids[(entry.employee_id, entry.work_date, ordinal)] = row.shift_id

    punches: list[Punch] = []
    punch_batch = batches.get(ImportDataType.PUNCH)
    if punch_batch is not None:
        punches = [
            Punch(
                employee_id=str(row.employee_id),
                attendance_date=row.attendance_date,
                punch_time=_to_shanghai(row.punch_time),
                punch_result=row.punch_result_raw,
            )
            for row in session.exec(
                select(PunchRecord)
                .where(col(PunchRecord.batch_id) == punch_batch.id)
                .order_by(
                    col(PunchRecord.attendance_date).asc(),
                    col(PunchRecord.punch_time).asc(),
                    col(PunchRecord.id).asc(),
                )
            ).all()
        ]

    trips: list[Trip] = []
    trip_batch = batches.get(ImportDataType.TRIP)
    if trip_batch is not None:
        trips = [
            Trip(
                id=str(row.id),
                approval_no=row.approval_no or "",
                employee_id=str(row.employee_id),
                kind=_trip_kind(row.application_type_raw),
                start_at=_to_shanghai(row.start_at),
                end_at=_to_shanghai(row.end_at),
            )
            for row in session.exec(
                select(OaTrip)
                .where(col(OaTrip.batch_id) == trip_batch.id)
                .order_by(col(OaTrip.start_at).asc(), col(OaTrip.id).asc())
            ).all()
        ]

    overtime_days: list[OvertimeDay] = []
    overtime_batch = batches.get(ImportDataType.OT)
    if overtime_batch is not None:
        overtime_days = [
            OvertimeDay(
                id=str(day.id),
                approval_no=overtime.approval_no or "",
                employee_id=str(overtime.employee_id),
                work_date=day.work_date,
                minutes=day.minutes,
            )
            for day, overtime in session.exec(
                select(OaOvertimeDay, OaOvertime)
                .join(OaOvertime, col(OaOvertimeDay.overtime_id) == col(OaOvertime.id))
                .where(col(OaOvertime.batch_id) == overtime_batch.id)
                .order_by(
                    col(OaOvertimeDay.work_date).asc(),
                    col(OaOvertimeDay.id).asc(),
                )
            ).all()
        ]

    leaves: list[Leave] = []
    leave_batch = batches.get(ImportDataType.LEAVE)
    if leave_batch is not None:
        leaves = [
            Leave(
                id=str(row.id),
                approval_no=row.approval_no or "",
                employee_id=str(row.employee_id),
                leave_kind=row.leave_kind,
                days=row.days,
                rest_start_at=_to_shanghai(row.rest_start_at),
                rest_end_at=_to_shanghai(row.rest_end_at),
                work_start_at=(
                    _to_shanghai(row.work_start_at)
                    if row.work_start_at is not None
                    else None
                ),
                work_end_at=(
                    _to_shanghai(row.work_end_at)
                    if row.work_end_at is not None
                    else None
                ),
            )
            for row in session.exec(
                select(OaLeave)
                .where(col(OaLeave.batch_id) == leave_batch.id)
                .order_by(col(OaLeave.rest_start_at).asc(), col(OaLeave.id).asc())
            ).all()
        ]

    adjacent: list[CalcRosterEntry] = []
    if leaves:
        leave_start = min(leave.rest_start_at.date() for leave in leaves)
        leave_end = max(leave.rest_end_at.date() for leave in leaves)
        adjacent = [
            CalcRosterEntry(
                employee_id=str(entry.employee_id),
                work_date=entry.work_date,
                state=entry.state,
            )
            for entry, _shift_rows in _load_roster(
                session,
                company_id,
                min(start, leave_start),
                max(end, leave_end),
                work_only=True,
            )
            if not start <= entry.work_date <= end and entry.employee_id in employee_ids
        ]

    holidays = _load_holidays(session, company_id, start, end)
    rules_snapshot_model = RulesSnapshot(
        company_rule=RuleValues.model_validate(defaults),
        plan_overrides=plan_snapshots,
        holidays=[
            HolidaySnapshot(
                date=holiday.date, name=holiday.name, day_type=holiday.day_type
            )
            for holiday in holidays
        ],
    )
    rules_snapshot = rules_snapshot_model.model_dump(mode="json")

    contract_roster = tuple(roster)
    contract_adjacent = tuple(adjacent)
    inputs = MonthInputs(
        month=month,
        employees=tuple(
            CalcEmployee(
                employee_id=str(employee.id),
                employee_no=employee.employee_no,
                name=employee.name,
                hire_date=employee.hire_date,
                resign_date=employee.resign_date,
                department=department.dept_name,
            )
            for employee, department in employees
        ),
        roster=contract_roster,
        rules=_contract_rules(defaults),
        punches=tuple(punches),
        trips=tuple(trips),
        overtime_days=tuple(overtime_days),
        leaves=tuple(leaves),
        holidays=tuple(
            CalcHoliday(date=holiday.date, name=holiday.name, day_type=holiday.day_type)
            for holiday in holidays
        ),
        adjacent_roster=contract_adjacent,
        roster_default=ResultRosterState.UNSCHEDULED,
    )
    return MonthCalculationData(
        inputs=inputs,
        rules_snapshot=rules_snapshot,
        input_batches=_input_batches(batches),
        rules_version=canonical_hash(rules_snapshot),
        roster_version=roster_fingerprint(contract_roster, contract_adjacent),
        shift_ids=shift_ids,
    )


def _delete_month_results(session: Session, month_id: uuid.UUID) -> None:
    day_ids = select(AttendanceDayResult.id).where(
        col(AttendanceDayResult.attendance_month_id) == month_id
    )
    session.exec(
        delete(AttendanceDayShiftResult).where(
            col(AttendanceDayShiftResult.day_result_id).in_(day_ids)
        )
    )
    session.exec(
        delete(AttendanceDayResult).where(
            col(AttendanceDayResult.attendance_month_id) == month_id
        )
    )
    session.exec(
        delete(AttendanceMonthSummary).where(
            col(AttendanceMonthSummary.attendance_month_id) == month_id
        )
    )


def _day_result_row(
    month: AttendanceMonth,
    calc_run_id: uuid.UUID,
    result: DayResult,
) -> AttendanceDayResult:
    return AttendanceDayResult(
        company_id=month.company_id,
        attendance_month_id=month.id,
        calc_run_id=calc_run_id,
        employee_id=uuid.UUID(result.employee_id),
        work_date=result.work_date,
        day_type=result.day_type,
        roster_state=result.roster_state,
        day_status=result.day_status,
        day_flags=list(result.day_flags),
        attendance_fraction=result.attendance_fraction,
        scheduled_minutes=result.scheduled_minutes,
        worked_minutes=result.worked_minutes,
        late_minutes=result.late_minutes,
        early_minutes=result.early_minutes,
        late_count=result.late_count,
        early_count=result.early_count,
        missing_punch_count=result.missing_punch_count,
        leave_kind=result.leave_kind,
        leave_days=result.leave_days,
        paid_leave_days=result.paid_leave_days,
        unpaid_leave_days=result.unpaid_leave_days,
        comp_leave_days=result.comp_leave_days,
        trip_kind=result.trip_kind,
        trip_fraction=result.trip_fraction,
        ot_weekday_minutes=result.ot_weekday_minutes,
        ot_weekend_minutes=result.ot_weekend_minutes,
        ot_holiday_minutes=result.ot_holiday_minutes,
        comp_offset_minutes=result.comp_offset_minutes,
        comp_offset_unused_minutes=result.comp_offset_unused_minutes,
        absent_deduct_amount=result.absent_deduct_amount,
        late_deduct_amount=result.late_deduct_amount,
        early_deduct_amount=result.early_deduct_amount,
        missing_punch_deduct_amount=result.missing_punch_deduct_amount,
        deduction_total=result.deduction_total,
        is_adjusted=False,
        adjustment_id=None,
    )


def replace_month_results(
    session: Session,
    *,
    month: AttendanceMonth,
    calc_run_id: uuid.UUID,
    data: MonthCalculationData,
    outputs: MonthOutputs,
) -> None:
    """Replace day/shift/month results for one month in the caller's transaction."""
    _delete_month_results(session, month.id)

    day_rows: list[AttendanceDayResult] = []
    shift_rows: list[AttendanceDayShiftResult] = []
    for result in outputs.day_results:
        day_row = _day_result_row(month, calc_run_id, result)
        day_rows.append(day_row)
        employee_id = uuid.UUID(result.employee_id)
        for shift in result.shift_results:
            shift_id = data.shift_ids.get((employee_id, result.work_date, shift.seq))
            if shift_id is None:
                raise ValueError(
                    "shift snapshot missing for "
                    f"{result.employee_id} {result.work_date} seq {shift.seq}"
                )
            shift_rows.append(
                AttendanceDayShiftResult(
                    company_id=month.company_id,
                    day_result_id=day_row.id,
                    calc_run_id=calc_run_id,
                    employee_id=employee_id,
                    work_date=result.work_date,
                    seq=shift.seq,
                    shift_id=shift_id,
                    shift_code=shift.shift_code,
                    shift_name=shift.shift_name,
                    start_time=shift.start_time,
                    end_time=shift.end_time,
                    cross_day=shift.cross_day,
                    break_start=shift.break_start,
                    break_end=shift.break_end,
                    rest_minutes=shift.rest_minutes,
                    shift_status=shift.shift_status,
                    shift_flags=list(shift.shift_flags),
                    punch_in_at=shift.punch_in_at,
                    punch_out_at=shift.punch_out_at,
                    break_out_at=shift.break_out_at,
                    break_in_at=shift.break_in_at,
                    scheduled_minutes=shift.scheduled_minutes,
                    worked_minutes=shift.worked_minutes,
                    late_minutes=shift.late_minutes,
                    early_minutes=shift.early_minutes,
                    missing_punch_count=shift.missing_punch_count,
                    ot_minutes=shift.ot_minutes,
                    comp_offset_minutes=shift.comp_offset_minutes,
                    leave_days=shift.leave_days,
                )
            )

    summary_rows = [
        AttendanceMonthSummary(
            company_id=month.company_id,
            attendance_month_id=month.id,
            calc_run_id=calc_run_id,
            employee_id=uuid.UUID(summary.employee_id),
            weekday_full=summary.weekday_full,
            weekend_full=summary.weekend_full,
            weekday_attended=summary.weekday_attended,
            weekend_attended=summary.weekend_attended,
            paid_leave_days=summary.paid_leave_days,
            unpaid_leave_days=summary.unpaid_leave_days,
            comp_leave_days=summary.comp_leave_days,
            trip_days=summary.trip_days,
            ot_weekday_minutes=summary.ot_weekday_minutes,
            ot_weekend_minutes=summary.ot_weekend_minutes,
            ot_holiday_minutes=summary.ot_holiday_minutes,
            ot_weekday_hours=summary.ot_weekday_hours,
            ot_weekend_hours=summary.ot_weekend_hours,
            ot_holiday_hours=summary.ot_holiday_hours,
            comp_leave_used_hours=summary.comp_leave_used_hours,
            comp_offset_unused_minutes=summary.comp_offset_unused_minutes,
            late_count=summary.late_count,
            late_minutes=summary.late_minutes,
            early_count=summary.early_count,
            early_minutes=summary.early_minutes,
            missing_punch_count=summary.missing_punch_count,
            absent_days=summary.absent_days,
            worked_minutes=summary.worked_minutes,
            attendance_deduct=summary.attendance_deduct,
            is_adjusted=summary.is_adjusted,
            calc_version=summary.calc_version,
            rules_version=data.rules_version,
        )
        for summary in outputs.month_summaries
    ]

    session.add_all(day_rows)
    session.add_all(shift_rows)
    session.add_all(summary_rows)
    session.flush()


_DEDUCTION_RULE_FIELDS = (
    "absent_deduct_per_day",
    "late_deduct_per_occurrence",
    "early_deduct_per_occurrence",
    "missing_punch_deduct_per_occurrence",
)


def _as_decimal(value: Any) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _deduction_rule_values(
    session: Session, day: AttendanceDayResult
) -> dict[str, Any] | None:
    """Effective rule values for one day, resolved from the calculation snapshot."""
    calc_run = session.get(CalcRun, day.calc_run_id)
    if calc_run is None:
        return None
    snapshot = RulesSnapshot.model_validate(calc_run.rules_snapshot)
    values: dict[str, Any] = snapshot.company_rule.model_dump()

    roster_entry = session.exec(
        select(RosterEntry).where(
            col(RosterEntry.company_id) == day.company_id,
            col(RosterEntry.employee_id) == day.employee_id,
            col(RosterEntry.work_date) == day.work_date,
        )
    ).first()
    if roster_entry is not None and roster_entry.plan_id is not None:
        override = next(
            (
                item
                for item in snapshot.plan_overrides
                if item.plan_id == roster_entry.plan_id
            ),
            None,
        )
        if override is not None:
            patch = override.overrides.model_dump()
            values = {
                field: (patch[field] if patch.get(field) is not None else values[field])
                for field in RULE_FIELDS
            }

    return {
        field: (
            _as_decimal(values[field])
            if field in _DEDUCTION_RULE_FIELDS
            else values[field]
        )
        for field in RULE_FIELDS
    }


def recompute_day_deductions(session: Session, day: AttendanceDayResult) -> None:
    """Re-derive one day's deduction suggestions from its effective facts.

    The section 7.10 formula reads the day's effective status and counts, so
    an adjustment to ``day_status`` or ``missing_punch_count`` must move the
    itemized amounts and total, not just the raw fields. Rule values come from
    the calculation the result belongs to. Callers own the transaction.
    """
    rules = _deduction_rule_values(session, day)
    if rules is None:
        return
    absent = day.day_status is DayStatus.ABSENT
    absent_days = 1 if absent else 0
    late_count = 0 if absent else day.late_count
    early_count = 0 if absent else day.early_count
    missing_count = 0 if absent else day.missing_punch_count
    absent_amount = -rules["absent_deduct_per_day"] * absent_days
    late_amount = -rules["late_deduct_per_occurrence"] * late_count
    early_amount = -rules["early_deduct_per_occurrence"] * early_count
    missing_amount = -rules["missing_punch_deduct_per_occurrence"] * missing_count
    day.absent_deduct_amount = amount_value(absent_amount)
    day.late_deduct_amount = amount_value(late_amount)
    day.early_deduct_amount = amount_value(early_amount)
    day.missing_punch_deduct_amount = amount_value(missing_amount)
    day.deduction_total = amount_value(
        absent_amount + late_amount + early_amount + missing_amount
    )


def recompute_month_summary_from_days(
    session: Session, *, month_id: uuid.UUID, employee_id: uuid.UUID
) -> None:
    """Re-derive one employee's summary from the persisted, adjusted day rows.

    Adjustments change day fields after calculation; the month summary must
    follow for the fields that aggregate day values (spec section 7.9).
    Deduction amounts are not adjustable, so they keep the calculated day
    totals. Callers own the transaction.
    """
    summary = session.exec(
        select(AttendanceMonthSummary).where(
            col(AttendanceMonthSummary.attendance_month_id) == month_id,
            col(AttendanceMonthSummary.employee_id) == employee_id,
        )
    ).first()
    if summary is None:
        return
    days = list(
        session.exec(
            select(AttendanceDayResult).where(
                col(AttendanceDayResult.attendance_month_id) == month_id,
                col(AttendanceDayResult.employee_id) == employee_id,
            )
        ).all()
    )
    work_days = [day for day in days if day.roster_state is ResultRosterState.WORK]
    ot_weekday = sum(day.ot_weekday_minutes for day in days)
    ot_weekend = sum(day.ot_weekend_minutes for day in days)
    ot_holiday = sum(day.ot_holiday_minutes for day in days)

    summary.weekday_full = day_value(
        sum(
            1
            for day in days
            if day.day_type is DayType.WORKDAY
            and day.roster_state is ResultRosterState.WORK
        )
    )
    summary.weekend_full = day_value(
        sum(
            1
            for day in days
            if day.day_type is DayType.WEEKEND
            and day.roster_state is ResultRosterState.WORK
        )
    )
    summary.weekday_attended = day_value(
        sum(
            (
                day.attendance_fraction
                for day in days
                if day.day_type is DayType.WORKDAY
            ),
            Decimal(0),
        )
    )
    summary.weekend_attended = day_value(
        sum(
            (
                day.attendance_fraction
                for day in days
                if day.day_type is DayType.WEEKEND
            ),
            Decimal(0),
        )
    )
    summary.paid_leave_days = day_value(
        sum((day.paid_leave_days for day in work_days), Decimal(0))
    )
    summary.unpaid_leave_days = day_value(
        sum((day.unpaid_leave_days for day in work_days), Decimal(0))
    )
    summary.comp_leave_days = day_value(
        sum((day.comp_leave_days for day in work_days), Decimal(0))
    )
    summary.trip_days = day_value(
        sum((day.trip_fraction for day in work_days), Decimal(0))
    )
    summary.ot_weekday_minutes = ot_weekday
    summary.ot_weekend_minutes = ot_weekend
    summary.ot_holiday_minutes = ot_holiday
    summary.ot_weekday_hours = hours_value(ot_weekday)
    summary.ot_weekend_hours = hours_value(ot_weekend)
    summary.ot_holiday_hours = hours_value(ot_holiday)
    summary.comp_leave_used_hours = hours_value(
        sum(day.comp_offset_minutes for day in days)
    )
    summary.comp_offset_unused_minutes = sum(
        day.comp_offset_unused_minutes for day in days
    )
    summary.late_count = sum(day.late_count for day in days)
    summary.late_minutes = sum(day.late_minutes for day in days)
    summary.early_count = sum(day.early_count for day in days)
    summary.early_minutes = sum(day.early_minutes for day in days)
    summary.missing_punch_count = sum(day.missing_punch_count for day in days)
    summary.absent_days = sum(
        1
        for day in days
        if day.day_status is DayStatus.ABSENT and day.attendance_fraction == 0
    )
    summary.worked_minutes = sum(day.worked_minutes for day in days)
    summary.attendance_deduct = amount_value(
        sum((day.deduction_total for day in days), Decimal(0))
    )
    summary.is_adjusted = any(day.is_adjusted for day in days)
    session.add(summary)


def default_rules_snapshot() -> dict[str, Any]:
    """Valid rules snapshot used when a run fails before the adapter read."""
    return RulesSnapshot(
        company_rule=RuleValues.model_validate(SYSTEM_DEFAULT_RULE_VALUES),
        plan_overrides=[],
        holidays=[],
    ).model_dump(mode="json")


def empty_input_batches() -> dict[str, Any]:
    return InputBatches().model_dump(mode="json")


def summary_payload(summary: RunSummary) -> dict[str, Any]:
    """Validate and serialize a run summary through its JSONB schema."""
    return CalcRunSummary.model_validate(asdict(summary)).model_dump(mode="json")


# ---------------------------------------------------------------------------
# Result queries (spec sections 8.3.5 and 9.2)
# ---------------------------------------------------------------------------


def _month_start_from_string(month: str) -> date:
    return date(int(month[:4]), int(month[5:7]), 1)


def _employee_department(session: Session, employee: Employee) -> Department:
    department = session.get(Department, employee.dept_id)
    if department is None:
        raise DomainError(AttendanceErrorCode.NOT_FOUND, DEPARTMENT_NOT_FOUND_MESSAGE)
    return department


def _company_employee_or_404(
    session: Session, company_id: uuid.UUID, employee_id: uuid.UUID
) -> tuple[Employee, Department]:
    """Resolve an employee only when the current department is in the company."""
    employee = session.get(Employee, employee_id)
    if employee is None:
        raise DomainError(AttendanceErrorCode.NOT_FOUND, EMPLOYEE_NOT_FOUND_MESSAGE)
    department = _employee_department(session, employee)
    if department.company_id != company_id:
        raise DomainError(AttendanceErrorCode.NOT_FOUND, EMPLOYEE_NOT_FOUND_MESSAGE)
    return employee, department


def _company_department_or_404(
    session: Session, company_id: uuid.UUID, dept_id: uuid.UUID
) -> Department:
    department = session.get(Department, dept_id)
    if department is None or department.company_id != company_id:
        raise DomainError(AttendanceErrorCode.NOT_FOUND, DEPARTMENT_NOT_FOUND_MESSAGE)
    return department


def _employee_displays(
    session: Session, employee_ids: set[uuid.UUID]
) -> dict[uuid.UUID, tuple[Employee, Department]]:
    if not employee_ids:
        return {}
    employees = {
        employee.id: employee
        for employee in session.exec(
            select(Employee).where(col(Employee.id).in_(employee_ids))
        ).all()
    }
    departments = {
        department.id: department
        for department in session.exec(
            select(Department).where(
                col(Department.id).in_(
                    {employee.dept_id for employee in employees.values()}
                )
            )
        ).all()
    }
    return {
        employee.id: (employee, departments[employee.dept_id])
        for employee in employees.values()
        if employee.dept_id in departments
    }


def _employee_display(employee: Employee, department: Department) -> EmployeeDisplay:
    return EmployeeDisplay(
        employee_id=employee.id,
        employee_no=employee.employee_no,
        employee_name=employee.name,
        department_id=department.id,
        department_name=department.dept_name,
    )


def _day_result_public(
    result: AttendanceDayResult,
    displays: dict[uuid.UUID, tuple[Employee, Department]],
) -> AttendanceDayResultPublic:
    public = AttendanceDayResultPublic.model_validate(result)
    display = displays.get(result.employee_id)
    if display is not None:
        employee, department = display
        public.employee_no = employee.employee_no
        public.employee_name = employee.name
        public.department_name = department.dept_name
    return public


def _summary_public(
    summary: AttendanceMonthSummary,
    displays: dict[uuid.UUID, tuple[Employee, Department]],
) -> AttendanceMonthSummaryPublic:
    public = AttendanceMonthSummaryPublic.model_validate(summary)
    display = displays.get(summary.employee_id)
    if display is not None:
        employee, department = display
        public.employee_no = employee.employee_no
        public.employee_name = employee.name
        public.department_name = department.dept_name
    return public


def _abnormal_condition() -> ColumnElement[bool]:
    """The derived anomaly view from section 8.3.5; never a stored column."""
    return or_(
        col(AttendanceDayResult.day_status).in_(tuple(ABNORMAL_DAY_STATUSES)),
        *[
            col(AttendanceDayResult.day_flags).contains([flag])
            for flag in sorted(ABNORMAL_DAY_FLAGS)
        ],
    )


def _apply_day_result_filters(
    filters: list[ColumnElement[bool]],
    *,
    company_id: uuid.UUID,
    start: date,
    end: date,
    employee_id: uuid.UUID | None,
    dept_id: uuid.UUID | None,
    date_from: date | None,
    date_to: date | None,
    day_type: DayType | None,
    roster_state: ResultRosterState | None,
    day_statuses: list[DayStatus] | None,
    flags: list[str] | None,
    is_abnormal: bool | None,
    has_adjustment: bool | None,
    keyword: str | None,
) -> None:
    filters.extend(
        [
            col(AttendanceDayResult.company_id) == company_id,
            col(AttendanceDayResult.work_date) >= start,
            col(AttendanceDayResult.work_date) <= end,
        ]
    )
    if employee_id is not None:
        filters.append(col(AttendanceDayResult.employee_id) == employee_id)
    if dept_id is not None:
        filters.append(col(Employee.dept_id) == dept_id)
    if date_from is not None:
        filters.append(col(AttendanceDayResult.work_date) >= date_from)
    if date_to is not None:
        filters.append(col(AttendanceDayResult.work_date) <= date_to)
    if day_type is not None:
        filters.append(col(AttendanceDayResult.day_type) == day_type)
    if roster_state is not None:
        filters.append(col(AttendanceDayResult.roster_state) == roster_state)
    statuses = list(dict.fromkeys(day_statuses or []))
    if statuses:
        filters.append(col(AttendanceDayResult.day_status).in_(statuses))
    selected_flags = list(dict.fromkeys(flag for flag in flags or [] if flag))
    if selected_flags:
        filters.append(
            or_(
                *[
                    col(AttendanceDayResult.day_flags).contains([flag])
                    for flag in selected_flags
                ]
            )
        )
    if is_abnormal is True:
        filters.append(_abnormal_condition())
    elif is_abnormal is False:
        filters.append(not_(_abnormal_condition()))
    if has_adjustment is not None:
        filters.append(col(AttendanceDayResult.is_adjusted) == has_adjustment)
    normalized_keyword = keyword.strip() if keyword else ""
    if normalized_keyword:
        filters.append(
            or_(
                col(Employee.employee_no).ilike(f"%{normalized_keyword}%"),
                col(Employee.name).ilike(f"%{normalized_keyword}%"),
            )
        )


def list_day_results(
    session: Session,
    *,
    company_id: uuid.UUID,
    month: str,
    employee_id: uuid.UUID | None,
    dept_id: uuid.UUID | None,
    date_from: date | None,
    date_to: date | None,
    day_type: DayType | None,
    roster_state: ResultRosterState | None,
    day_statuses: list[DayStatus] | None,
    flags: list[str] | None,
    is_abnormal: bool | None,
    has_adjustment: bool | None,
    keyword: str | None,
    skip: int,
    limit: int,
) -> AttendanceDayResultsPublic:
    """List day results with the full filter set; anomaly is derived on read."""
    get_company_or_404(session, company_id)
    if dept_id is not None:
        _company_department_or_404(session, company_id, dept_id)
    start, end = month_bounds(_month_start_from_string(month))

    filters: list[ColumnElement[bool]] = []
    _apply_day_result_filters(
        filters,
        company_id=company_id,
        start=start,
        end=end,
        employee_id=employee_id,
        dept_id=dept_id,
        date_from=date_from,
        date_to=date_to,
        day_type=day_type,
        roster_state=roster_state,
        day_statuses=day_statuses,
        flags=flags,
        is_abnormal=is_abnormal,
        has_adjustment=has_adjustment,
        keyword=keyword,
    )
    statement = (
        select(AttendanceDayResult)
        .join(Employee, col(AttendanceDayResult.employee_id) == col(Employee.id))
        .where(*filters)
        .order_by(
            col(AttendanceDayResult.work_date).asc(),
            col(Employee.employee_no).asc(),
            col(AttendanceDayResult.id).asc(),
        )
    )
    count_statement = (
        select(func.count())
        .select_from(AttendanceDayResult)
        .join(Employee, col(AttendanceDayResult.employee_id) == col(Employee.id))
        .where(*filters)
    )
    results, count = paginate(
        session, statement, count_statement, skip=skip, limit=limit
    )
    displays = _employee_displays(session, {result.employee_id for result in results})
    return AttendanceDayResultsPublic(
        data=[_day_result_public(result, displays) for result in results],
        count=count,
    )


def _roster_entry_public(
    session: Session,
    entry: RosterEntry,
    employee: Employee,
    department: Department,
) -> RosterEntryPublic:
    shifts = session.exec(
        select(RosterEntryShift)
        .where(col(RosterEntryShift.roster_entry_id) == entry.id)
        .order_by(col(RosterEntryShift.seq).asc())
    ).all()
    return RosterEntryPublic(
        id=entry.id,
        company_id=entry.company_id,
        employee_id=entry.employee_id,
        employee_no=employee.employee_no,
        employee_name=employee.name,
        department_name=department.dept_name,
        work_date=entry.work_date,
        state=entry.state,
        source=entry.source,
        plan_id=entry.plan_id,
        note=entry.note,
        shifts=[RosterEntryShiftPublic.model_validate(shift) for shift in shifts],
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


def _detail_punches(
    session: Session,
    *,
    company_id: uuid.UUID,
    month: date,
    employee_id: uuid.UUID,
    work_date: date,
) -> list[PunchRecordPublic]:
    rows = session.exec(
        select(PunchRecord)
        .join(ImportBatch, col(PunchRecord.batch_id) == col(ImportBatch.id))
        .where(
            col(ImportBatch.company_id) == company_id,
            col(ImportBatch.month) == month,
            col(ImportBatch.status) == ImportBatchStatus.COMMITTED,
            col(ImportBatch.data_type) == ImportDataType.PUNCH,
            col(PunchRecord.employee_id) == employee_id,
            col(PunchRecord.attendance_date) == work_date,
        )
        .order_by(col(PunchRecord.punch_time).asc(), col(PunchRecord.id).asc())
    ).all()
    return [PunchRecordPublic.model_validate(row) for row in rows]


def _detail_trips(
    session: Session,
    *,
    company_id: uuid.UUID,
    month: date,
    employee_id: uuid.UUID,
    work_date: date,
) -> list[OaTripPublic]:
    rows = session.exec(
        select(OaTrip)
        .join(ImportBatch, col(OaTrip.batch_id) == col(ImportBatch.id))
        .where(
            col(ImportBatch.company_id) == company_id,
            col(ImportBatch.month) == month,
            col(ImportBatch.status) == ImportBatchStatus.COMMITTED,
            col(ImportBatch.data_type) == ImportDataType.TRIP,
            col(OaTrip.employee_id) == employee_id,
            col(OaTrip.start_date) <= work_date,
            col(OaTrip.end_date) >= work_date,
        )
        .order_by(col(OaTrip.start_at).asc(), col(OaTrip.id).asc())
    ).all()
    return [OaTripPublic.model_validate(row) for row in rows]


def _detail_overtime_days(
    session: Session,
    *,
    company_id: uuid.UUID,
    month: date,
    employee_id: uuid.UUID,
    work_date: date,
) -> list[OaOvertimeDayPublic]:
    rows = session.exec(
        select(OaOvertimeDay)
        .join(OaOvertime, col(OaOvertimeDay.overtime_id) == col(OaOvertime.id))
        .join(ImportBatch, col(OaOvertime.batch_id) == col(ImportBatch.id))
        .where(
            col(ImportBatch.company_id) == company_id,
            col(ImportBatch.month) == month,
            col(ImportBatch.status) == ImportBatchStatus.COMMITTED,
            col(ImportBatch.data_type) == ImportDataType.OT,
            col(OaOvertime.employee_id) == employee_id,
            col(OaOvertimeDay.work_date) == work_date,
        )
        .order_by(col(OaOvertimeDay.id).asc())
    ).all()
    return [OaOvertimeDayPublic.model_validate(row) for row in rows]


def _detail_leaves(
    session: Session,
    *,
    company_id: uuid.UUID,
    month: date,
    employee_id: uuid.UUID,
    work_date: date,
) -> list[OaLeavePublic]:
    rows = session.exec(
        select(OaLeave)
        .join(ImportBatch, col(OaLeave.batch_id) == col(ImportBatch.id))
        .where(
            col(ImportBatch.company_id) == company_id,
            col(ImportBatch.month) == month,
            col(ImportBatch.status) == ImportBatchStatus.COMMITTED,
            col(ImportBatch.data_type) == ImportDataType.LEAVE,
            col(OaLeave.employee_id) == employee_id,
            col(OaLeave.rest_start_date) <= work_date,
            col(OaLeave.rest_end_date) >= work_date,
        )
        .order_by(col(OaLeave.rest_start_at).asc(), col(OaLeave.id).asc())
    ).all()
    return [OaLeavePublic.model_validate(row) for row in rows]


def _detail_adjustments(
    session: Session,
    *,
    company_id: uuid.UUID,
    employee_id: uuid.UUID,
    work_date: date,
) -> list[AttendanceAdjustmentPublic]:
    rows = list(
        session.exec(
            select(AttendanceResultAdjustment)
            .where(
                col(AttendanceResultAdjustment.company_id) == company_id,
                col(AttendanceResultAdjustment.employee_id) == employee_id,
                col(AttendanceResultAdjustment.work_date) == work_date,
            )
            .order_by(col(AttendanceResultAdjustment.version).desc())
        ).all()
    )
    user_ids = {row.adjusted_by for row in rows}
    names = {
        user.id: (user.full_name or user.email)
        for user in (
            session.exec(select(User).where(col(User.id).in_(user_ids))).all()
            if user_ids
            else []
        )
    }
    data: list[AttendanceAdjustmentPublic] = []
    for row in rows:
        public = AttendanceAdjustmentPublic.model_validate(row)
        public.adjusted_by_name = names.get(row.adjusted_by)
        data.append(public)
    return data


def read_day_detail(
    session: Session,
    *,
    company_id: uuid.UUID,
    employee_id: uuid.UUID,
    work_date: date,
) -> AttendanceDayDetailPublic:
    """Compose one day's result with roster, punches, OA rows, and adjustments."""
    get_company_or_404(session, company_id)
    employee, department = _company_employee_or_404(session, company_id, employee_id)
    month = work_date.replace(day=1)

    day_result = session.exec(
        select(AttendanceDayResult).where(
            col(AttendanceDayResult.company_id) == company_id,
            col(AttendanceDayResult.employee_id) == employee_id,
            col(AttendanceDayResult.work_date) == work_date,
        )
    ).first()
    if day_result is None:
        raise DomainError(AttendanceErrorCode.NOT_FOUND, DAY_RESULT_NOT_FOUND_MESSAGE)

    shift_results = session.exec(
        select(AttendanceDayShiftResult)
        .where(col(AttendanceDayShiftResult.day_result_id) == day_result.id)
        .order_by(col(AttendanceDayShiftResult.seq).asc())
    ).all()
    roster_entry = session.exec(
        select(RosterEntry).where(
            col(RosterEntry.company_id) == company_id,
            col(RosterEntry.employee_id) == employee_id,
            col(RosterEntry.work_date) == work_date,
        )
    ).first()

    displays = {employee.id: (employee, department)}
    return AttendanceDayDetailPublic(
        day_result=_day_result_public(day_result, displays),
        shift_results=[
            AttendanceDayShiftResultPublic.model_validate(row) for row in shift_results
        ],
        roster_entry=(
            _roster_entry_public(session, roster_entry, employee, department)
            if roster_entry is not None
            else None
        ),
        punches=_detail_punches(
            session,
            company_id=company_id,
            month=month,
            employee_id=employee_id,
            work_date=work_date,
        ),
        oa_trips=_detail_trips(
            session,
            company_id=company_id,
            month=month,
            employee_id=employee_id,
            work_date=work_date,
        ),
        oa_overtime_days=_detail_overtime_days(
            session,
            company_id=company_id,
            month=month,
            employee_id=employee_id,
            work_date=work_date,
        ),
        oa_leaves=_detail_leaves(
            session,
            company_id=company_id,
            month=month,
            employee_id=employee_id,
            work_date=work_date,
        ),
        adjustments=_detail_adjustments(
            session,
            company_id=company_id,
            employee_id=employee_id,
            work_date=work_date,
        ),
    )


def list_month_summaries(
    session: Session,
    *,
    company_id: uuid.UUID,
    month: str,
    employee_id: uuid.UUID | None,
    dept_id: uuid.UUID | None,
    keyword: str | None,
    skip: int,
    limit: int,
) -> AttendanceMonthSummariesPublic:
    """List persisted month summaries; a month without results is empty, not 404."""
    get_company_or_404(session, company_id)
    if dept_id is not None:
        _company_department_or_404(session, company_id, dept_id)
    month_start = _month_start_from_string(month)
    month_row = existing_month(session, company_id, month_start)
    if month_row is None:
        return AttendanceMonthSummariesPublic(data=[], count=0)

    filters: list[ColumnElement[bool]] = [
        col(AttendanceMonthSummary.company_id) == company_id,
        col(AttendanceMonthSummary.attendance_month_id) == month_row.id,
    ]
    if employee_id is not None:
        filters.append(col(AttendanceMonthSummary.employee_id) == employee_id)
    if dept_id is not None:
        filters.append(col(Employee.dept_id) == dept_id)
    normalized_keyword = keyword.strip() if keyword else ""
    if normalized_keyword:
        filters.append(
            or_(
                col(Employee.employee_no).ilike(f"%{normalized_keyword}%"),
                col(Employee.name).ilike(f"%{normalized_keyword}%"),
            )
        )

    statement = (
        select(AttendanceMonthSummary)
        .join(Employee, col(AttendanceMonthSummary.employee_id) == col(Employee.id))
        .where(*filters)
        .order_by(
            col(Employee.employee_no).asc(),
            col(AttendanceMonthSummary.id).asc(),
        )
    )
    count_statement = (
        select(func.count())
        .select_from(AttendanceMonthSummary)
        .join(Employee, col(AttendanceMonthSummary.employee_id) == col(Employee.id))
        .where(*filters)
    )
    summaries, count = paginate(
        session, statement, count_statement, skip=skip, limit=limit
    )
    displays = _employee_displays(
        session, {summary.employee_id for summary in summaries}
    )
    return AttendanceMonthSummariesPublic(
        data=[_summary_public(summary, displays) for summary in summaries],
        count=count,
    )


def read_result_calendar(
    session: Session,
    *,
    company_id: uuid.UUID,
    month: str,
    employee_id: uuid.UUID,
) -> EmployeeResultCalendarPublic:
    """Return one employee's month summary and day results; empty when uncalculated."""
    get_company_or_404(session, company_id)
    employee, department = _company_employee_or_404(session, company_id, employee_id)
    month_start = _month_start_from_string(month)
    start, end = month_bounds(month_start)
    displays = {employee.id: (employee, department)}

    summary: AttendanceMonthSummaryPublic | None = None
    month_row = existing_month(session, company_id, month_start)
    if month_row is not None:
        summary_row = session.exec(
            select(AttendanceMonthSummary).where(
                col(AttendanceMonthSummary.attendance_month_id) == month_row.id,
                col(AttendanceMonthSummary.employee_id) == employee_id,
            )
        ).first()
        if summary_row is not None:
            summary = _summary_public(summary_row, displays)

    day_rows = session.exec(
        select(AttendanceDayResult)
        .where(
            col(AttendanceDayResult.company_id) == company_id,
            col(AttendanceDayResult.employee_id) == employee_id,
            col(AttendanceDayResult.work_date) >= start,
            col(AttendanceDayResult.work_date) <= end,
        )
        .order_by(
            col(AttendanceDayResult.work_date).asc(),
            col(AttendanceDayResult.id).asc(),
        )
    ).all()
    return EmployeeResultCalendarPublic(
        employee=_employee_display(employee, department),
        month=month,
        summary=summary,
        days=[_day_result_public(row, displays) for row in day_rows],
    )


__all__ = [
    "MonthCalculationData",
    "build_month_inputs",
    "canonical_hash",
    "default_rules_snapshot",
    "empty_input_batches",
    "list_day_results",
    "list_month_summaries",
    "read_day_detail",
    "read_result_calendar",
    "replace_month_results",
    "roster_fingerprint",
    "summary_payload",
]
