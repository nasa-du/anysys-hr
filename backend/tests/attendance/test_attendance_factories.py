"""Attendance factories build database state without state transitions."""

import uuid
from datetime import date, time
from decimal import Decimal

from sqlmodel import Session, select

from app.core.config import settings
from app.enums import (
    AdjustmentStatus,
    AttendanceMonthStatus,
    ImportBatchStatus,
    ImportDataType,
    LeaveKind,
    PlanStatus,
    RosterSource,
    RosterState,
    ScheduleScopeType,
)
from app.models import (
    AttendanceDayResult,
    AttendanceMonth,
    AttendanceResultAdjustment,
    AttendanceRule,
    ImportBatch,
    ImportBatchError,
    OaLeave,
    OaOvertime,
    OaTrip,
    PlanDay,
    PlanRuleOverride,
    PlanScope,
    PunchRecord,
    RosterEntry,
    RosterEntryShift,
    SchedulePlan,
    Shift,
    User,
)
from app.schemas_attendance.core import (
    AttendanceMonthSnapshotPublic,
    CalcRunPublic,
)
from tests.utils.attendance_factories import (
    create_attendance_adjustment,
    create_attendance_day_result,
    create_attendance_day_shift_result,
    create_attendance_month,
    create_attendance_month_summary,
    create_attendance_rule,
    create_calc_run,
    create_holiday,
    create_import_batch,
    create_import_batch_error,
    create_import_mapping_template,
    create_month_snapshot,
    create_oa_leave,
    create_oa_overtime,
    create_oa_trip,
    create_punch_record,
    create_roster_entry,
    create_schedule_plan,
    create_shift,
)
from tests.utils.factories import (
    create_company,
    create_department,
    create_employee,
    create_position,
)


def _operator(db: Session) -> User:
    return db.exec(select(User).where(User.email == settings.FIRST_SUPERUSER)).one()


def _organization(db: Session):
    company = create_company(db)
    department = create_department(db, company=company)
    position = create_position(db, company=company, dept=department)
    employee = create_employee(db, dept=department, position=position)
    return company, department, position, employee


def test_model_defaults_match_the_contract() -> None:
    company_id = uuid.uuid4()

    shift = Shift(
        company_id=company_id,
        shift_code="ADM",
        shift_name="行政班",
        start_time=time(8, 30),
        end_time=time(17, 30),
    )
    assert shift.cross_day is False
    assert shift.break_start is None
    assert shift.break_end is None
    assert shift.rest_minutes == 0
    assert shift.is_active is True

    rule = AttendanceRule(company_id=company_id)
    assert rule.punch_window_min == 120
    assert rule.late_cap_min == 240
    assert rule.early_cap_min == 240
    assert rule.ot_max_min == 600
    assert rule.late_grace_min == 5
    assert rule.early_grace_min == 5
    assert rule.ot_threshold_min == 30
    assert rule.absent_if_no_punch is True
    assert rule.break_punch_required is True
    assert rule.break_punch_tolerance_min == 60
    assert rule.absent_deduct_per_day == Decimal("0")
    assert rule.late_deduct_per_occurrence == Decimal("0")
    assert rule.early_deduct_per_occurrence == Decimal("0")
    assert rule.missing_punch_deduct_per_occurrence == Decimal("0")

    month = AttendanceMonth(company_id=company_id, month=date(2026, 9, 1))
    assert month.status is AttendanceMonthStatus.DRAFT
    assert month.is_stale is True
    assert month.calculated_at is None
    assert month.confirmed_at is None
    assert month.locked_at is None

    plan = SchedulePlan(
        company_id=company_id,
        month=date(2026, 9, 1),
        plan_name="行政班",
        scope_type=ScheduleScopeType.ALL,
    )
    assert plan.status is PlanStatus.ENABLED

    day_result = AttendanceDayResult(
        company_id=company_id,
        attendance_month_id=uuid.uuid4(),
        calc_run_id=uuid.uuid4(),
        employee_id=uuid.uuid4(),
        work_date=date(2026, 9, 1),
        day_type="workday",
        roster_state="work",
        day_status="normal",
    )
    assert day_result.attendance_fraction == Decimal("0")
    assert day_result.worked_minutes == 0
    assert day_result.late_count == 0
    assert day_result.early_count == 0
    assert day_result.missing_punch_count == 0
    assert day_result.deduction_total == Decimal("0")
    assert day_result.is_adjusted is False
    assert day_result.adjustment_id is None


def test_core_factories_create_uuid_v7_rows(db: Session) -> None:
    company, _department, _position, _employee = _organization(db)
    shift = create_shift(db, company_id=company.id)
    holiday = create_holiday(db, company_id=company.id)
    rule = create_attendance_rule(db, company_id=company.id)
    month = create_attendance_month(db, company_id=company.id)
    calc_run = create_calc_run(db, attendance_month_id=month.id)
    snapshot = create_month_snapshot(
        db,
        attendance_month_id=month.id,
        calc_run_id=calc_run.id,
        locked_by=_operator(db).id,
    )

    for row in (shift, holiday, rule, month, calc_run, snapshot):
        assert row.id.version == 7
    for row in (shift, holiday, rule, month):
        assert row.created_at.tzinfo is not None
    assert calc_run.started_at.tzinfo is not None
    assert snapshot.locked_at.tzinfo is not None

    assert month.status is AttendanceMonthStatus.DRAFT
    assert month.is_stale is True
    assert calc_run.summary is None

    assert CalcRunPublic.model_validate(calc_run).rules_snapshot.company_rule
    assert AttendanceMonthSnapshotPublic.model_validate(snapshot).payload is not None


def test_schedule_factories_create_plan_children(db: Session) -> None:
    company, department, _position, employee = _organization(db)
    shift = create_shift(db, company_id=company.id)
    second_shift = create_shift(
        db,
        company_id=company.id,
        shift_name="中班",
        start_time=time(14, 0),
        end_time=time(22, 0),
    )
    plan = create_schedule_plan(
        db,
        company_id=company.id,
        scope_type=ScheduleScopeType.DEPT,
        scope_ids=[department.id],
        days=[(1, 0, shift.id), (1, 1, second_shift.id)],
        rule_overrides={"ot_threshold_min": 15},
    )
    entry = create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 1),
        shifts=[shift, second_shift],
        plan_id=plan.id,
    )
    rest_entry = create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 2),
        state=RosterState.REST,
        source=RosterSource.MANUAL,
    )

    assert plan.status is PlanStatus.ENABLED
    assert {scope.scope_id for scope in db.exec(select(PlanScope)).all()} == {
        department.id
    }
    assert len(db.exec(select(PlanDay)).all()) == 2
    override = db.exec(select(PlanRuleOverride)).one()
    assert override.ot_threshold_min == 15
    assert entry.state is RosterState.WORK
    assert rest_entry.state is RosterState.REST
    assert db.exec(select(RosterEntry)).all()
    snapshots = db.exec(select(RosterEntryShift)).all()
    assert [snapshot.seq for snapshot in snapshots] == [0, 1]
    assert [snapshot.shift_code for snapshot in snapshots] == [
        shift.shift_code,
        second_shift.shift_code,
    ]


def test_import_factories_create_batches_and_typed_records(db: Session) -> None:
    company, _department, _position, employee = _organization(db)
    operator = _operator(db)
    punch_batch = create_import_batch(
        db,
        company_id=company.id,
        operator_id=operator.id,
        data_type=ImportDataType.PUNCH,
        status=ImportBatchStatus.COMMITTED,
        valid_records=1,
    )
    create_punch_record(
        db,
        company_id=company.id,
        batch_id=punch_batch.id,
        employee_id=employee.id,
    )
    create_import_batch_error(db, batch_id=punch_batch.id)
    template = create_import_mapping_template(
        db,
        company_id=company.id,
        updated_by=operator.id,
    )

    trip_batch = create_import_batch(
        db,
        company_id=company.id,
        operator_id=operator.id,
        data_type=ImportDataType.TRIP,
    )
    create_oa_trip(
        db,
        company_id=company.id,
        batch_id=trip_batch.id,
        employee_id=employee.id,
        approval_no="T-1",
    )

    overtime_batch = create_import_batch(
        db,
        company_id=company.id,
        operator_id=operator.id,
        data_type=ImportDataType.OT,
    )
    create_oa_overtime(
        db,
        company_id=company.id,
        batch_id=overtime_batch.id,
        employee_id=employee.id,
        days=[(date(2026, 9, 14), 480), (date(2026, 9, 15), 120)],
    )

    leave_batch = create_import_batch(
        db,
        company_id=company.id,
        operator_id=operator.id,
        data_type=ImportDataType.LEAVE,
    )
    create_oa_leave(
        db,
        company_id=company.id,
        batch_id=leave_batch.id,
        employee_id=employee.id,
        leave_kind=LeaveKind.PAID,
        days=Decimal("0.50"),
    )

    assert len(db.exec(select(ImportBatch)).all()) == 4
    assert db.exec(select(PunchRecord)).one().punch_result_raw == "正常"
    assert db.exec(select(ImportBatchError)).one().code == "unknown_employee"
    assert template.mapping == {}
    assert db.exec(select(OaTrip)).one().approval_no == "T-1"
    assert len(db.exec(select(OaOvertime)).all()) == 1
    assert db.exec(select(OaLeave)).one().days == Decimal("0.50")


def test_result_factories_create_day_shift_summary_and_adjustment(
    db: Session,
) -> None:
    company, _department, _position, employee = _organization(db)
    operator = _operator(db)
    shift = create_shift(db, company_id=company.id)
    month = create_attendance_month(db, company_id=company.id)
    calc_run = create_calc_run(db, attendance_month_id=month.id)
    day_result = create_attendance_day_result(
        db,
        company_id=company.id,
        attendance_month_id=month.id,
        calc_run_id=calc_run.id,
        employee_id=employee.id,
    )
    shift_result = create_attendance_day_shift_result(
        db,
        company_id=company.id,
        day_result_id=day_result.id,
        calc_run_id=calc_run.id,
        employee_id=employee.id,
        shift=shift,
    )
    summary = create_attendance_month_summary(
        db,
        company_id=company.id,
        attendance_month_id=month.id,
        calc_run_id=calc_run.id,
        employee_id=employee.id,
    )
    adjustment = create_attendance_adjustment(
        db,
        company_id=company.id,
        attendance_month_id=month.id,
        calc_run_id=calc_run.id,
        employee_id=employee.id,
        adjusted_by=operator.id,
    )

    assert day_result.is_adjusted is False
    assert shift_result.shift_code == shift.shift_code
    assert summary.weekday_full == Decimal("0")
    assert adjustment.status is AdjustmentStatus.ACTIVE
    assert adjustment.version == 1
    assert db.exec(select(AttendanceResultAdjustment)).one().reason == "人工调整"


def test_factories_never_perform_state_transitions(db: Session) -> None:
    company, _department, _position, employee = _organization(db)
    shift = create_shift(db, company_id=company.id)
    plan = create_schedule_plan(
        db,
        company_id=company.id,
        days=[(1, 0, shift.id)],
    )
    month = create_attendance_month(db, company_id=company.id)

    assert plan.status is PlanStatus.ENABLED
    assert month.status is AttendanceMonthStatus.DRAFT
    assert month.is_stale is True
    assert (
        db.exec(select(RosterEntry).where(RosterEntry.employee_id == employee.id)).all()
        == []
    )
