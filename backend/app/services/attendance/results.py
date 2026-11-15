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
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import delete, or_
from sqlmodel import Session, col, select

from app.enums import (
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
)
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
from app.services.attendance.expansion import month_bounds
from app.services.attendance.rules import (
    RULE_FIELDS,
    SYSTEM_DEFAULT_RULE_VALUES,
    company_default_values,
)

SHANGHAI = ZoneInfo("Asia/Shanghai")


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


__all__ = [
    "MonthCalculationData",
    "build_month_inputs",
    "canonical_hash",
    "default_rules_snapshot",
    "empty_input_batches",
    "replace_month_results",
    "roster_fingerprint",
    "summary_payload",
]
