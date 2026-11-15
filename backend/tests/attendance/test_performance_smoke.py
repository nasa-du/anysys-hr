"""Calculation performance smoke.

CI gate (spec sections 14.9 and 17.2): 100 people × 31 days with daily punches
and OA requests must calculate in at most five seconds. Setup is not part of
the budget; the timer covers the real ``calculate_month`` path (DB adapter,
pure kernel, result persistence, and the calculation run). Setup also goes
through the service layer: the plan expands through ``create_schedule_plan``
and all four inputs commit through preview/commit.
"""

import time
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlmodel import Session, select

from app.core.config import settings
from app.enums import CalcRunStatus, ImportDataType, ScheduleScopeType
from app.models import (
    AttendanceDayResult,
    AttendanceDayShiftResult,
    AttendanceMonthSummary,
    Employee,
    User,
)
from app.schemas_attendance.scheduling import PlanDayInput, SchedulePlanCreate
from app.services.attendance import imports, months, schedule_plans
from tests.utils.attendance_factories import create_shift
from tests.utils.factories import (
    create_company,
    create_department,
    create_position,
)
from tests.utils.utils import random_upper_code

PEOPLE = 100
DAYS = 31
BUDGET_SECONDS = 5.0
MONTH = date(2026, 10, 1)

PUNCH_HEADER = "工号,考勤日期,打卡时间,打卡结果"
TRIP_HEADER = "出差人,开始时间,结束时间,审批结果,审批编号"
OT_HEADER = "创建人,加班开始时间,加班结束时间,审批结果,审批编号"
LEAVE_HEADER = "创建人,请假类型,请假天数,休息开始时间,休息结束时间,审批结果,审批编号"


def _commit_csv(
    db: Session,
    operator: User,
    company_id: uuid.UUID,
    data_type: ImportDataType,
    file_name: str,
    header: str,
    rows: list[str],
) -> None:
    """Preview and commit generated rows through the real import services."""
    content = "\n".join([header, *rows]).encode("utf-8")
    preview = imports.preview_import(
        db,
        company_id=company_id,
        data_type=data_type,
        month=MONTH,
        operator=operator,
        content=content,
        file_name=file_name,
    )
    assert preview.stats.valid_records == len(rows), preview.stats
    imports.commit_batch(db, preview.batch.id, operator=operator)


@pytest.mark.performance
def test_100_employees_31_days_calculate_under_budget(db: Session) -> None:
    company = create_company(db)
    department = create_department(db, company=company)
    position = create_position(db, company=company, dept=department)
    shift = create_shift(db, company_id=company.id)
    operator = db.exec(select(User).where(User.email == settings.FIRST_SUPERUSER)).one()
    now = datetime.now(UTC)

    employee_rows = [
        {
            "id": uuid.uuid7(),
            "employee_no": random_upper_code("E"),
            "name": f"测试员工{index}",
            "gender": None,
            "dept_id": department.id,
            "position_id": position.id,
            "cost_org_id": None,
            "manager_id": None,
            "status": "active",
            "hire_date": date(2026, 1, 1),
            "resign_date": None,
            "contract_type": "full_time",
            "daily_hours": None,
            "monthly_rest": None,
            "confidentiality_level": None,
            "note": None,
            "created_at": now,
            "updated_at": now,
        }
        for index in range(PEOPLE)
    ]
    db.execute(sa.insert(Employee), employee_rows)
    db.commit()

    # Expansion goes through the real service path; the timed section starts
    # only after setup, so scaling setup cost is not part of the gate.
    schedule_plans.create_schedule_plan(
        db,
        SchedulePlanCreate(
            company_id=company.id,
            month=MONTH.strftime("%Y-%m"),
            plan_name="性能方案",
            scope_type=ScheduleScopeType.ALL,
            scope_ids=[],
            days=[
                PlanDayInput(day_of_month=offset + 1, seq=0, shift_id=shift.id)
                for offset in range(DAYS)
            ],
        ),
    )

    work_dates = [MONTH + timedelta(days=offset) for offset in range(DAYS)]
    punch_rows = [
        f"{employee['employee_no']},{work_date.isoformat()},"
        f"{work_date.isoformat()} {punch_time},正常"
        for employee in employee_rows
        for work_date in work_dates
        for punch_time in ("08:20", "17:35")
    ]
    _commit_csv(
        db,
        operator,
        company.id,
        ImportDataType.PUNCH,
        "performance-punch.csv",
        PUNCH_HEADER,
        punch_rows,
    )
    _commit_csv(
        db,
        operator,
        company.id,
        ImportDataType.TRIP,
        "performance-trip.csv",
        TRIP_HEADER,
        [
            f"{employee['name']},2026-10-15 09:00,2026-10-15 18:00,"
            f"审批通过,TRIP-{index}"
            for index, employee in enumerate(employee_rows)
        ],
    )
    _commit_csv(
        db,
        operator,
        company.id,
        ImportDataType.OT,
        "performance-ot.csv",
        OT_HEADER,
        [
            f"{employee['name']},2026-10-16 18:00,2026-10-16 20:00,审批通过,OT-{index}"
            for index, employee in enumerate(employee_rows)
        ],
    )
    _commit_csv(
        db,
        operator,
        company.id,
        ImportDataType.LEAVE,
        "performance-leave.csv",
        LEAVE_HEADER,
        [
            f"{employee['name']},事假,1,2026-10-20 08:30,"
            f"2026-10-20 18:00,审批通过,LV-{index}"
            for index, employee in enumerate(employee_rows)
        ],
    )

    started = time.perf_counter()
    calc_run = months.calculate_month(db, company_id=company.id, month=MONTH)
    elapsed = time.perf_counter() - started

    db.expire_all()
    day_count = db.execute(
        sa.select(sa.func.count()).select_from(AttendanceDayResult)
    ).scalar_one()
    shift_count = db.execute(
        sa.select(sa.func.count()).select_from(AttendanceDayShiftResult)
    ).scalar_one()
    summary_count = db.execute(
        sa.select(sa.func.count()).select_from(AttendanceMonthSummary)
    ).scalar_one()

    assert calc_run.status == CalcRunStatus.SUCCESS
    assert day_count == PEOPLE * DAYS
    assert shift_count == PEOPLE * DAYS
    assert summary_count == PEOPLE
    assert elapsed <= BUDGET_SECONDS, f"calculation took {elapsed:.2f}s"
