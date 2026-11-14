"""Factories for Attendance test data.

Each factory only inserts a row (or a small graph of rows). State transitions
such as plan expansion, import commit, calculation, confirmation, and locking
must always go through the service or API layer.
"""

import uuid
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Any

from sqlmodel import Session, SQLModel

from app.enums import (
    AdjustmentStatus,
    AttendanceMonthStatus,
    CalcRunStatus,
    CalcRunTrigger,
    DayStatus,
    DayType,
    HolidayDayType,
    ImportBatchStatus,
    ImportDataType,
    ImportSeverity,
    ImportSource,
    LeaveKind,
    PlanStatus,
    ResultRosterState,
    RosterSource,
    RosterState,
    ScheduleScopeType,
)
from app.models import (
    AttendanceDayResult,
    AttendanceDayShiftResult,
    AttendanceMonth,
    AttendanceMonthSnapshot,
    AttendanceMonthSummary,
    AttendanceResultAdjustment,
    AttendanceRule,
    CalcRun,
    Holiday,
    ImportBatch,
    ImportBatchError,
    ImportMappingTemplate,
    OaLeave,
    OaOvertime,
    OaOvertimeDay,
    OaTrip,
    PlanDay,
    PlanRuleOverride,
    PlanScope,
    PunchRecord,
    RosterEntry,
    RosterEntryShift,
    SchedulePlan,
    Shift,
)
from tests.utils.utils import random_upper_code

DEFAULT_MONTH = date(2026, 9, 1)

DEFAULT_RULE_VALUES: dict[str, Any] = {
    "punch_window_min": 120,
    "late_cap_min": 240,
    "early_cap_min": 240,
    "ot_max_min": 600,
    "late_grace_min": 5,
    "early_grace_min": 5,
    "ot_threshold_min": 30,
    "absent_if_no_punch": True,
    "break_punch_required": True,
    "break_punch_tolerance_min": 60,
    "absent_deduct_per_day": 0.0,
    "late_deduct_per_occurrence": 0.0,
    "early_deduct_per_occurrence": 0.0,
    "missing_punch_deduct_per_occurrence": 0.0,
}


def _default_rules_snapshot() -> dict[str, Any]:
    return {
        "company_rule": dict(DEFAULT_RULE_VALUES),
        "plan_overrides": [],
        "holidays": [],
    }


def _default_input_batches() -> dict[str, Any]:
    return {"punch": None, "trip": None, "ot": None, "leave": None}


def _default_snapshot_payload(
    *,
    company_id: uuid.UUID | None,
    calc_run_id: uuid.UUID,
    locked_at: datetime,
    locked_by: uuid.UUID,
    month: date,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "company_id": str(company_id or uuid.uuid4()),
        "month": month.strftime("%Y-%m"),
        "locked_at": locked_at.isoformat(),
        "locked_by": str(locked_by),
        "attendance_month": {"status": "locked"},
        "calc_run": {"id": str(calc_run_id)},
        "day_results": [],
        "shift_results": [],
        "month_summaries": [],
        "adjustments": [],
        "export": {"columns": [], "rows": []},
    }


def _persist[ModelT: SQLModel](db: Session, entity: ModelT) -> ModelT:
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


def create_shift(
    db: Session,
    *,
    company_id: uuid.UUID,
    shift_code: str | None = None,
    shift_name: str = "行政班",
    start_time: time = time(8, 30),
    end_time: time = time(17, 30),
    cross_day: bool = False,
    break_start: time | None = None,
    break_end: time | None = None,
    rest_minutes: int = 60,
    color: str | None = None,
    note: str | None = None,
    is_active: bool = True,
) -> Shift:
    shift = Shift(
        company_id=company_id,
        shift_code=shift_code or random_upper_code("S"),
        shift_name=shift_name,
        start_time=start_time,
        end_time=end_time,
        cross_day=cross_day,
        break_start=break_start,
        break_end=break_end,
        rest_minutes=rest_minutes,
        color=color,
        note=note,
        is_active=is_active,
    )
    return _persist(db, shift)


def create_holiday(
    db: Session,
    *,
    company_id: uuid.UUID,
    holiday_date: date = date(2026, 9, 25),
    name: str = "中秋节",
    day_type: HolidayDayType = HolidayDayType.HOLIDAY,
    note: str | None = None,
) -> Holiday:
    holiday = Holiday(
        company_id=company_id,
        date=holiday_date,
        name=name,
        day_type=day_type,
        note=note,
    )
    return _persist(db, holiday)


def create_attendance_rule(
    db: Session,
    *,
    company_id: uuid.UUID,
    **overrides: Any,
) -> AttendanceRule:
    rule = AttendanceRule(company_id=company_id, **overrides)
    return _persist(db, rule)


def create_schedule_plan(
    db: Session,
    *,
    company_id: uuid.UUID,
    month: date = DEFAULT_MONTH,
    plan_name: str = "行政班",
    scope_type: ScheduleScopeType = ScheduleScopeType.ALL,
    scope_ids: list[uuid.UUID] | None = None,
    days: list[tuple[int, int, uuid.UUID]] | None = None,
    rule_overrides: dict[str, Any] | None = None,
    status: PlanStatus = PlanStatus.ENABLED,
    copied_from_plan_id: uuid.UUID | None = None,
    note: str | None = None,
) -> SchedulePlan:
    """Create a plan and optionally its scopes, days, and rule override."""
    plan = _persist(
        db,
        SchedulePlan(
            company_id=company_id,
            month=month,
            plan_name=plan_name,
            scope_type=scope_type,
            status=status,
            copied_from_plan_id=copied_from_plan_id,
            note=note,
        ),
    )
    for scope_id in scope_ids or []:
        _persist(db, PlanScope(plan_id=plan.id, scope_id=scope_id))
    for day_of_month, seq, shift_id in days or []:
        _persist(
            db,
            PlanDay(
                plan_id=plan.id,
                day_of_month=day_of_month,
                seq=seq,
                shift_id=shift_id,
            ),
        )
    if rule_overrides is not None:
        _persist(db, PlanRuleOverride(plan_id=plan.id, **rule_overrides))
    return plan


def create_roster_entry(
    db: Session,
    *,
    company_id: uuid.UUID,
    employee_id: uuid.UUID,
    work_date: date,
    state: RosterState = RosterState.WORK,
    source: RosterSource = RosterSource.PLAN,
    plan_id: uuid.UUID | None = None,
    shifts: list[Shift] | None = None,
    note: str | None = None,
) -> RosterEntry:
    """Create a roster entry and snapshot every supplied shift."""
    entry = _persist(
        db,
        RosterEntry(
            company_id=company_id,
            employee_id=employee_id,
            work_date=work_date,
            state=state,
            source=source,
            plan_id=plan_id,
            note=note,
        ),
    )
    for seq, shift in enumerate(shifts or []):
        _persist(
            db,
            RosterEntryShift(
                roster_entry_id=entry.id,
                seq=seq,
                shift_id=shift.id,
                shift_code=shift.shift_code,
                shift_name=shift.shift_name,
                start_time=shift.start_time,
                end_time=shift.end_time,
                cross_day=shift.cross_day,
                break_start=shift.break_start,
                break_end=shift.break_end,
                rest_minutes=shift.rest_minutes,
            ),
        )
    return entry


def create_attendance_month(
    db: Session,
    *,
    company_id: uuid.UUID,
    month: date = DEFAULT_MONTH,
    status: AttendanceMonthStatus = AttendanceMonthStatus.DRAFT,
    is_stale: bool = True,
    calculated_at: datetime | None = None,
    confirmed_at: datetime | None = None,
    locked_at: datetime | None = None,
    unlock_reason: str | None = None,
) -> AttendanceMonth:
    attendance_month = AttendanceMonth(
        company_id=company_id,
        month=month,
        status=status,
        is_stale=is_stale,
        calculated_at=calculated_at,
        confirmed_at=confirmed_at,
        locked_at=locked_at,
        unlock_reason=unlock_reason,
    )
    return _persist(db, attendance_month)


def create_calc_run(
    db: Session,
    *,
    attendance_month_id: uuid.UUID,
    trigger: CalcRunTrigger = CalcRunTrigger.MANUAL,
    status: CalcRunStatus = CalcRunStatus.SUCCESS,
    calc_version: str = "attendance-calc-v1",
    rules_version: str = "rules",
    roster_version: str = "roster",
    rules_snapshot: dict[str, Any] | None = None,
    input_batches: dict[str, Any] | None = None,
    summary: dict[str, Any] | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
) -> CalcRun:
    now = datetime.now(UTC)
    calc_run = CalcRun(
        attendance_month_id=attendance_month_id,
        trigger=trigger,
        status=status,
        calc_version=calc_version,
        rules_version=rules_version,
        roster_version=roster_version,
        rules_snapshot=rules_snapshot or _default_rules_snapshot(),
        input_batches=input_batches or _default_input_batches(),
        summary=summary,
        error_code=error_code,
        error_message=error_message,
        started_at=started_at or now,
        finished_at=finished_at or now,
    )
    return _persist(db, calc_run)


def create_month_snapshot(
    db: Session,
    *,
    attendance_month_id: uuid.UUID,
    calc_run_id: uuid.UUID,
    locked_by: uuid.UUID,
    company_id: uuid.UUID | None = None,
    month: date = DEFAULT_MONTH,
    version: int = 1,
    locked_at: datetime | None = None,
    payload: dict[str, Any] | None = None,
) -> AttendanceMonthSnapshot:
    effective_locked_at = locked_at or datetime.now(UTC)
    snapshot = AttendanceMonthSnapshot(
        attendance_month_id=attendance_month_id,
        calc_run_id=calc_run_id,
        version=version,
        locked_at=effective_locked_at,
        locked_by=locked_by,
        payload=payload
        or _default_snapshot_payload(
            company_id=company_id,
            calc_run_id=calc_run_id,
            locked_at=effective_locked_at,
            locked_by=locked_by,
            month=month,
        ),
    )
    return _persist(db, snapshot)


def create_import_batch(
    db: Session,
    *,
    company_id: uuid.UUID,
    operator_id: uuid.UUID,
    data_type: ImportDataType = ImportDataType.PUNCH,
    month: date = DEFAULT_MONTH,
    status: ImportBatchStatus = ImportBatchStatus.PREVIEW,
    source: ImportSource = ImportSource.UPLOAD,
    file_name: str | None = "fixture.csv",
    file_size: int | None = 100,
    file_sha256: str | None = "0" * 64,
    sheet_name: str | None = None,
    header_row_number: int | None = 1,
    header_columns: list[Any] | None = None,
    column_mapping: dict[str, Any] | None = None,
    parser_version: str = "attendance-import-v1",
    source_rows: int = 0,
    valid_records: int = 0,
    skipped_records: int = 0,
    error_records: int = 0,
    warning_records: int = 0,
    skip_counts: dict[str, Any] | None = None,
    warning_counts: dict[str, Any] | None = None,
    committed_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> ImportBatch:
    batch = ImportBatch(
        company_id=company_id,
        data_type=data_type,
        month=month,
        status=status,
        source=source,
        file_name=file_name,
        file_size=file_size,
        file_sha256=file_sha256,
        sheet_name=sheet_name,
        header_row_number=header_row_number,
        header_columns=header_columns or [],
        column_mapping=column_mapping or {},
        parser_version=parser_version,
        source_rows=source_rows,
        valid_records=valid_records,
        skipped_records=skipped_records,
        error_records=error_records,
        warning_records=warning_records,
        skip_counts=skip_counts or {},
        warning_counts=warning_counts or {},
        operator_id=operator_id,
        committed_at=committed_at,
        expires_at=expires_at,
    )
    return _persist(db, batch)


def create_import_batch_error(
    db: Session,
    *,
    batch_id: uuid.UUID,
    source_row_number: int = 2,
    code: str = "unknown_employee",
    message: str = "员工不存在",
    severity: ImportSeverity = ImportSeverity.ERROR,
    column_name: str | None = None,
    raw_row: dict[str, Any] | None = None,
) -> ImportBatchError:
    error = ImportBatchError(
        batch_id=batch_id,
        source_row_number=source_row_number,
        column_name=column_name,
        code=code,
        message=message,
        severity=severity,
        raw_row=raw_row or {},
    )
    return _persist(db, error)


def create_import_mapping_template(
    db: Session,
    *,
    company_id: uuid.UUID,
    updated_by: uuid.UUID,
    data_type: ImportDataType = ImportDataType.PUNCH,
    mapping: dict[str, Any] | None = None,
    header_columns: list[Any] | None = None,
) -> ImportMappingTemplate:
    template = ImportMappingTemplate(
        company_id=company_id,
        data_type=data_type,
        mapping=mapping or {},
        header_columns=header_columns or [],
        updated_by=updated_by,
    )
    return _persist(db, template)


def create_punch_record(
    db: Session,
    *,
    company_id: uuid.UUID,
    batch_id: uuid.UUID,
    employee_id: uuid.UUID,
    attendance_date: date = DEFAULT_MONTH,
    punch_time: datetime | None = None,
    source_row_number: int = 2,
    punch_result_raw: str = "正常",
    employee_no_raw: str = "E101",
    employee_name_raw: str = "冯芷茵",
    department_raw: str = "生产部",
    raw_row: dict[str, Any] | None = None,
) -> PunchRecord:
    record = PunchRecord(
        company_id=company_id,
        batch_id=batch_id,
        source_row_number=source_row_number,
        employee_id=employee_id,
        employee_no_raw=employee_no_raw,
        employee_name_raw=employee_name_raw,
        department_raw=department_raw,
        attendance_date=attendance_date,
        punch_time=punch_time or datetime.combine(attendance_date, time(8, 30), UTC),
        punch_result_raw=punch_result_raw,
        raw_row=raw_row or {},
    )
    return _persist(db, record)


def create_oa_trip(
    db: Session,
    *,
    company_id: uuid.UUID,
    batch_id: uuid.UUID,
    employee_id: uuid.UUID,
    source_row_number: int = 2,
    split_index: int = 0,
    approval_no: str | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    approval_result_raw: str = "审批通过",
) -> OaTrip:
    effective_start = start_at or datetime.now(UTC)
    effective_start_date = start_date or effective_start.date()
    effective_end = end_at or effective_start
    trip = OaTrip(
        company_id=company_id,
        batch_id=batch_id,
        employee_id=employee_id,
        source_row_number=source_row_number,
        split_index=split_index,
        approval_no=approval_no,
        employee_name_raw="冯芷茵",
        department_raw="生产部",
        application_type_raw="出差",
        approval_result_raw=approval_result_raw,
        approval_status_raw="已完成",
        start_at=effective_start,
        end_at=effective_end,
        start_date=effective_start_date,
        end_date=end_date or effective_end.date(),
        raw_row={},
    )
    return _persist(db, trip)


def create_oa_overtime(
    db: Session,
    *,
    company_id: uuid.UUID,
    batch_id: uuid.UUID,
    employee_id: uuid.UUID,
    source_row_number: int = 2,
    approval_no: str | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    declared_raw: str | None = None,
    approval_result_raw: str = "审批通过",
    days: list[tuple[date, int]] | None = None,
) -> OaOvertime:
    effective_start = start_at or datetime.now(UTC)
    overtime = _persist(
        db,
        OaOvertime(
            company_id=company_id,
            batch_id=batch_id,
            employee_id=employee_id,
            source_row_number=source_row_number,
            approval_no=approval_no,
            employee_name_raw="冯芷茵",
            department_raw="生产部",
            approval_result_raw=approval_result_raw,
            approval_status_raw="已完成",
            start_at=effective_start,
            end_at=end_at or effective_start,
            declared_raw=declared_raw,
            raw_row={},
        ),
    )
    for work_date, minutes in days or []:
        _persist(
            db,
            OaOvertimeDay(
                company_id=company_id,
                overtime_id=overtime.id,
                work_date=work_date,
                minutes=minutes,
            ),
        )
    return overtime


def create_oa_leave(
    db: Session,
    *,
    company_id: uuid.UUID,
    batch_id: uuid.UUID,
    employee_id: uuid.UUID,
    source_row_number: int = 2,
    approval_no: str | None = None,
    leave_type_raw: str = "事假",
    leave_kind: LeaveKind = LeaveKind.UNPAID,
    days: Decimal = Decimal("1.00"),
    rest_start_at: datetime | None = None,
    rest_end_at: datetime | None = None,
    rest_start_date: date | None = None,
    rest_end_date: date | None = None,
    work_start_at: datetime | None = None,
    work_end_at: datetime | None = None,
    work_start_date: date | None = None,
    work_end_date: date | None = None,
    approval_result_raw: str = "审批通过",
) -> OaLeave:
    start = rest_start_at or datetime.now(UTC)
    end = rest_end_at or start
    leave = OaLeave(
        company_id=company_id,
        batch_id=batch_id,
        employee_id=employee_id,
        source_row_number=source_row_number,
        approval_no=approval_no,
        employee_name_raw="冯芷茵",
        department_raw="生产部",
        leave_type_raw=leave_type_raw,
        leave_kind=leave_kind,
        days=days,
        rest_start_at=start,
        rest_end_at=end,
        rest_start_date=rest_start_date or start.date(),
        rest_end_date=rest_end_date or end.date(),
        work_start_at=work_start_at,
        work_end_at=work_end_at,
        work_start_date=work_start_date,
        work_end_date=work_end_date,
        approval_result_raw=approval_result_raw,
        approval_status_raw="已完成",
        raw_row={},
    )
    return _persist(db, leave)


def create_attendance_day_result(
    db: Session,
    *,
    company_id: uuid.UUID,
    attendance_month_id: uuid.UUID,
    calc_run_id: uuid.UUID,
    employee_id: uuid.UUID,
    work_date: date = DEFAULT_MONTH,
    day_type: DayType = DayType.WORKDAY,
    roster_state: ResultRosterState = ResultRosterState.WORK,
    day_status: DayStatus = DayStatus.NORMAL,
    **overrides: Any,
) -> AttendanceDayResult:
    result = AttendanceDayResult(
        company_id=company_id,
        attendance_month_id=attendance_month_id,
        calc_run_id=calc_run_id,
        employee_id=employee_id,
        work_date=work_date,
        day_type=day_type,
        roster_state=roster_state,
        day_status=day_status,
        day_flags=[],
        **overrides,
    )
    return _persist(db, result)


def create_attendance_day_shift_result(
    db: Session,
    *,
    company_id: uuid.UUID,
    day_result_id: uuid.UUID,
    calc_run_id: uuid.UUID,
    employee_id: uuid.UUID,
    shift: Shift,
    work_date: date = DEFAULT_MONTH,
    seq: int = 0,
    shift_status: DayStatus = DayStatus.NORMAL,
    **overrides: Any,
) -> AttendanceDayShiftResult:
    result = AttendanceDayShiftResult(
        company_id=company_id,
        day_result_id=day_result_id,
        calc_run_id=calc_run_id,
        employee_id=employee_id,
        work_date=work_date,
        seq=seq,
        shift_id=shift.id,
        shift_code=shift.shift_code,
        shift_name=shift.shift_name,
        start_time=shift.start_time,
        end_time=shift.end_time,
        cross_day=shift.cross_day,
        break_start=shift.break_start,
        break_end=shift.break_end,
        rest_minutes=shift.rest_minutes,
        shift_status=shift_status,
        shift_flags=[],
        **overrides,
    )
    return _persist(db, result)


def create_attendance_month_summary(
    db: Session,
    *,
    company_id: uuid.UUID,
    attendance_month_id: uuid.UUID,
    calc_run_id: uuid.UUID,
    employee_id: uuid.UUID,
    calc_version: str = "attendance-calc-v1",
    rules_version: str = "rules",
    **overrides: Any,
) -> AttendanceMonthSummary:
    summary = AttendanceMonthSummary(
        company_id=company_id,
        attendance_month_id=attendance_month_id,
        calc_run_id=calc_run_id,
        employee_id=employee_id,
        calc_version=calc_version,
        rules_version=rules_version,
        **overrides,
    )
    return _persist(db, summary)


def create_attendance_adjustment(
    db: Session,
    *,
    company_id: uuid.UUID,
    attendance_month_id: uuid.UUID,
    calc_run_id: uuid.UUID,
    employee_id: uuid.UUID,
    adjusted_by: uuid.UUID,
    work_date: date = DEFAULT_MONTH,
    version: int = 1,
    status: AdjustmentStatus = AdjustmentStatus.ACTIVE,
    original_values: dict[str, Any] | None = None,
    adjusted_values: dict[str, Any] | None = None,
    reason: str = "人工调整",
) -> AttendanceResultAdjustment:
    adjustment = AttendanceResultAdjustment(
        company_id=company_id,
        attendance_month_id=attendance_month_id,
        calc_run_id=calc_run_id,
        employee_id=employee_id,
        work_date=work_date,
        version=version,
        status=status,
        original_values=original_values or {},
        adjusted_values=adjusted_values or {},
        reason=reason,
        adjusted_by=adjusted_by,
        adjusted_at=datetime.now(UTC),
    )
    return _persist(db, adjustment)
