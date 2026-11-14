"""Foundation-scale performance smoke.

The calculation-kernel gate (100 people × 31 days in at most 5 seconds) lands
with the kernel in a later slice. Phase 0 proves the same input volume can be
created and queried through the persistence foundation inside that budget.
"""

import time
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlmodel import Session

from app.models import Employee, RosterEntry, RosterEntryShift
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


@pytest.mark.performance
def test_100_employees_31_days_foundation_stays_under_budget(db: Session) -> None:
    company = create_company(db)
    department = create_department(db, company=company)
    position = create_position(db, company=company, dept=department)
    shift = create_shift(db, company_id=company.id)
    now = datetime.now(UTC)

    started = time.perf_counter()

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

    entry_rows = [
        {
            "id": uuid.uuid7(),
            "company_id": company.id,
            "employee_id": employee["id"],
            "work_date": date(2026, 9, 1) + timedelta(days=offset),
            "state": "work",
            "source": "plan",
            "plan_id": None,
            "note": None,
            "created_at": now,
            "updated_at": now,
        }
        for employee in employee_rows
        for offset in range(DAYS)
    ]
    db.execute(sa.insert(RosterEntry), entry_rows)
    db.commit()

    snapshot_rows = [
        {
            "id": uuid.uuid7(),
            "roster_entry_id": entry["id"],
            "seq": 0,
            "shift_id": shift.id,
            "shift_code": shift.shift_code,
            "shift_name": shift.shift_name,
            "start_time": shift.start_time,
            "end_time": shift.end_time,
            "cross_day": shift.cross_day,
            "break_start": shift.break_start,
            "break_end": shift.break_end,
            "rest_minutes": shift.rest_minutes,
        }
        for entry in entry_rows
    ]
    db.execute(sa.insert(RosterEntryShift), snapshot_rows)
    db.commit()

    entry_count = db.execute(
        sa.select(sa.func.count()).select_from(RosterEntry)
    ).scalar_one()
    snapshot_count = db.execute(
        sa.select(sa.func.count()).select_from(RosterEntryShift)
    ).scalar_one()
    elapsed = time.perf_counter() - started

    assert entry_count == PEOPLE * DAYS
    assert snapshot_count == PEOPLE * DAYS
    assert elapsed <= BUDGET_SECONDS, f"foundation setup took {elapsed:.2f}s"
