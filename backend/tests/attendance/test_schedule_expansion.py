"""Schedule expansion semantics (spec section 5.1).

The API seam proves priority resolution, employment-range exclusion, and
manual-exception preservation end to end. Pure-function tests cover the
warning and resolution helpers so the priority table and cross-day overlap
math are pinned without a database.
"""

import uuid
from datetime import date, time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.enums import (
    RosterSource,
    RosterState,
    ScheduleScopeType,
)
from app.models import Employee, RosterEntry, RosterEntryShift, SchedulePlan, Shift
from app.services.attendance import expansion
from tests.utils.attendance_factories import create_roster_entry, create_shift
from tests.utils.factories import (
    create_company,
    create_department,
    create_employee,
    create_position,
)

PLANS_URL = f"{settings.API_V1_STR}/attendance/schedule-plans/"


def create_plan(
    client: TestClient,
    headers: dict[str, str],
    body: dict[str, Any],
) -> dict[str, Any]:
    response = client.post(PLANS_URL, headers=headers, json=body)
    assert response.status_code == 201, response.text
    return response.json()


def plan_payload(
    company_id: uuid.UUID,
    *,
    plan_name: str,
    scope_type: ScheduleScopeType = ScheduleScopeType.ALL,
    scope_ids: list[uuid.UUID] | None = None,
    days: list[tuple[int, int, uuid.UUID]] | None = None,
) -> dict[str, Any]:
    return {
        "company_id": str(company_id),
        "month": "2026-09",
        "plan_name": plan_name,
        "scope_type": scope_type.value,
        "scope_ids": [str(scope_id) for scope_id in scope_ids or []],
        "days": [
            {
                "day_of_month": day_of_month,
                "seq": seq,
                "shift_id": str(shift_id),
            }
            for day_of_month, seq, shift_id in days or []
        ],
    }


def entry(db: Session, employee_id: uuid.UUID, work_date: date) -> RosterEntry | None:
    db.expire_all()
    return db.exec(
        select(RosterEntry).where(
            RosterEntry.employee_id == employee_id,
            RosterEntry.work_date == work_date,
        )
    ).first()


def snapshot_shift_ids(db: Session, entry_id: uuid.UUID) -> list[uuid.UUID]:
    db.expire_all()
    return [
        shift.shift_id
        for shift in db.exec(
            select(RosterEntryShift)
            .where(RosterEntryShift.roster_entry_id == entry_id)
            .order_by(RosterEntryShift.seq.asc())
        ).all()
    ]


@pytest.fixture
def hierarchy(db: Session) -> dict[str, Any]:
    company = create_company(db, company_code="C-EXP")
    first_department = create_department(db, company=company, dept_code="D-1")
    second_department = create_department(db, company=company, dept_code="D-2")
    first_position = create_position(
        db, company=company, dept=first_department, position_code="P-1"
    )
    second_position = create_position(
        db, company=company, dept=second_department, position_code="P-2"
    )
    first_employee = create_employee(
        db,
        dept=first_department,
        position=first_position,
        employee_no="E-1",
        hire_date=date(2026, 1, 1),
    )
    second_employee = create_employee(
        db,
        dept=second_department,
        position=second_position,
        employee_no="E-2",
        hire_date=date(2026, 1, 1),
    )
    shifts = {
        "all": create_shift(db, company_id=company.id, shift_code="A"),
        "dept": create_shift(db, company_id=company.id, shift_code="D"),
        "position": create_shift(db, company_id=company.id, shift_code="P"),
        "employee": create_shift(db, company_id=company.id, shift_code="E"),
    }
    return {
        "company": company,
        "departments": (first_department, second_department),
        "positions": (first_position, second_position),
        "employees": (first_employee, second_employee),
        "shifts": shifts,
    }


def test_expansion_priority_employee_position_dept_company(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    hierarchy: dict[str, Any],
) -> None:
    company = hierarchy["company"]
    department, _other_department = hierarchy["departments"]
    position, _other_position = hierarchy["positions"]
    employee, other_employee = hierarchy["employees"]
    shifts = hierarchy["shifts"]

    all_plan = create_plan(
        client,
        superuser_token_headers,
        plan_payload(
            company.id,
            plan_name="全公司",
            days=[(1, 0, shifts["all"].id)],
        ),
    )
    db.expire_all()
    assert snapshot_shift_ids(db, entry(db, employee.id, date(2026, 9, 1)).id) == [
        shifts["all"].id
    ]
    assert snapshot_shift_ids(
        db, entry(db, other_employee.id, date(2026, 9, 1)).id
    ) == [shifts["all"].id]

    dept_plan = create_plan(
        client,
        superuser_token_headers,
        plan_payload(
            company.id,
            plan_name="部门",
            scope_type=ScheduleScopeType.DEPT,
            scope_ids=[department.id],
            days=[(1, 0, shifts["dept"].id)],
        ),
    )
    db.expire_all()
    assert snapshot_shift_ids(db, entry(db, employee.id, date(2026, 9, 1)).id) == [
        shifts["dept"].id
    ]
    # The other department keeps the all-company plan.
    assert snapshot_shift_ids(
        db, entry(db, other_employee.id, date(2026, 9, 1)).id
    ) == [shifts["all"].id]

    position_plan = create_plan(
        client,
        superuser_token_headers,
        plan_payload(
            company.id,
            plan_name="岗位",
            scope_type=ScheduleScopeType.POSITION,
            scope_ids=[position.id],
            days=[(1, 0, shifts["position"].id)],
        ),
    )
    db.expire_all()
    assert snapshot_shift_ids(db, entry(db, employee.id, date(2026, 9, 1)).id) == [
        shifts["position"].id
    ]

    employee_plan = create_plan(
        client,
        superuser_token_headers,
        plan_payload(
            company.id,
            plan_name="员工",
            scope_type=ScheduleScopeType.EMPLOYEE,
            scope_ids=[employee.id],
            days=[(1, 0, shifts["employee"].id)],
        ),
    )
    db.expire_all()
    day_one = entry(db, employee.id, date(2026, 9, 1))
    assert snapshot_shift_ids(db, day_one.id) == [shifts["employee"].id]
    assert day_one.plan_id == uuid.UUID(employee_plan["id"])

    # A higher-specificity plan with no day rows wins as a rest day, even
    # though lower-specificity plans schedule work that day.
    day_two = entry(db, employee.id, date(2026, 9, 2))
    assert day_two.state == RosterState.REST
    assert day_two.plan_id == uuid.UUID(employee_plan["id"])
    assert snapshot_shift_ids(db, day_two.id) == []

    # Archiving the employee plan hands the day back to the position plan;
    # each archive re-expands the whole month.
    client.post(
        f"{PLANS_URL}{employee_plan['id']}/archive",
        headers=superuser_token_headers,
    )
    db.expire_all()
    assert snapshot_shift_ids(db, entry(db, employee.id, date(2026, 9, 1)).id) == [
        shifts["position"].id
    ]
    client.post(
        f"{PLANS_URL}{position_plan['id']}/archive",
        headers=superuser_token_headers,
    )
    db.expire_all()
    assert snapshot_shift_ids(db, entry(db, employee.id, date(2026, 9, 1)).id) == [
        shifts["dept"].id
    ]
    client.post(
        f"{PLANS_URL}{dept_plan['id']}/archive",
        headers=superuser_token_headers,
    )
    db.expire_all()
    assert snapshot_shift_ids(db, entry(db, employee.id, date(2026, 9, 1)).id) == [
        shifts["all"].id
    ]
    client.post(
        f"{PLANS_URL}{all_plan['id']}/archive",
        headers=superuser_token_headers,
    )
    db.expire_all()
    assert entry(db, employee.id, date(2026, 9, 1)) is None


def test_expansion_excludes_dates_outside_hire_and_resign(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    hierarchy: dict[str, Any],
) -> None:
    company = hierarchy["company"]
    department, _ = hierarchy["departments"]
    position, other_position = hierarchy["positions"]
    _employee, other_employee = hierarchy["employees"]
    late_hire = create_employee(
        db,
        dept=department,
        position=position,
        employee_no="E-LATE",
        hire_date=date(2026, 9, 15),
    )
    from app.enums import EmployeeStatus

    resigned = create_employee(
        db,
        dept=department,
        position=other_position,
        employee_no="E-GONE",
        status=EmployeeStatus.RESIGNED,
        hire_date=date(2026, 1, 1),
        resign_date=date(2026, 9, 10),
    )
    create_plan(
        client,
        superuser_token_headers,
        plan_payload(company.id, plan_name="全公司"),
    )

    db.expire_all()
    assert entry(db, late_hire.id, date(2026, 9, 14)) is None
    assert entry(db, late_hire.id, date(2026, 9, 15)) is not None
    assert entry(db, resigned.id, date(2026, 9, 10)) is not None
    assert entry(db, resigned.id, date(2026, 9, 11)) is None
    assert entry(db, other_employee.id, date(2026, 9, 1)) is not None

    # A later resignation removes the out-of-range plan entries on expansion.
    db.expire_all()
    resigned_row = db.get(Employee, resigned.id)
    resigned_row.resign_date = date(2026, 9, 5)
    db.add(resigned_row)
    db.commit()
    plan = db.exec(select(SchedulePlan)).one()
    response = client.post(
        f"{PLANS_URL}{plan.id}/expand", headers=superuser_token_headers
    )
    assert response.status_code == 200, response.text
    db.expire_all()
    assert entry(db, resigned.id, date(2026, 9, 5)) is not None
    assert entry(db, resigned.id, date(2026, 9, 6)) is None


def test_manual_exceptions_are_preserved_and_never_replaced(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    hierarchy: dict[str, Any],
) -> None:
    company = hierarchy["company"]
    employee = hierarchy["employees"][0]
    shift = hierarchy["shifts"]["all"]

    manual = create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 1),
        state=RosterState.REST,
        source=RosterSource.MANUAL,
        shifts=[],
    )
    plan = create_plan(
        client,
        superuser_token_headers,
        plan_payload(
            company.id,
            plan_name="全公司",
            days=[(1, 0, shift.id)],
        ),
    )

    db.expire_all()
    preserved = entry(db, employee.id, date(2026, 9, 1))
    assert preserved.id == manual.id
    assert preserved.source == RosterSource.MANUAL
    assert preserved.state == RosterState.REST
    assert preserved.plan_id is None
    # Days without a manual exception are expanded normally.
    generated = entry(db, employee.id, date(2026, 9, 2))
    assert generated.source == RosterSource.PLAN
    assert generated.plan_id == uuid.UUID(plan["id"])

    response = client.post(
        f"{PLANS_URL}{plan['id']}/expand-preview",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["manual_preserved"] == 1


def test_expand_preview_reports_added_updated_deleted_and_employee_count(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    hierarchy: dict[str, Any],
) -> None:
    company = hierarchy["company"]
    _employee, other_employee = hierarchy["employees"]
    shift = hierarchy["shifts"]["all"]
    plan = create_plan(
        client,
        superuser_token_headers,
        plan_payload(company.id, plan_name="全公司"),
    )
    assert plan["days"] == []

    # Removing a second plan's only day row changes the month back to rest.
    update = client.patch(
        f"{PLANS_URL}{plan['id']}",
        headers=superuser_token_headers,
        json={
            "days": [{"day_of_month": 1, "seq": 0, "shift_id": str(shift.id)}]
        },
    )
    assert update.status_code == 200, update.text

    preview = client.post(
        f"{PLANS_URL}{plan['id']}/expand-preview",
        headers=superuser_token_headers,
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["added"] == 0
    assert body["deleted"] == 0
    assert body["affected_employees"] == 0

    # Changing the shift time refreshes one snapshot per scheduled day.
    db.expire_all()
    shift_row = db.get(Shift, shift.id)
    shift_row.start_time = time(9, 0)
    shift_row.end_time = time(18, 0)
    db.add(shift_row)
    db.commit()
    preview_after = client.post(
        f"{PLANS_URL}{plan['id']}/expand-preview",
        headers=superuser_token_headers,
    )
    assert preview_after.status_code == 200, preview_after.text
    assert preview_after.json()["updated"] == 2
    assert preview_after.json()["affected_employees"] == 2


# ---------------------------------------------------------------------------
# Pure expansion helpers
# ---------------------------------------------------------------------------


def _shift(
    code: str,
    start: time,
    end: time,
    *,
    cross_day: bool = False,
    company_id: uuid.UUID | None = None,
) -> Shift:
    return Shift(
        company_id=company_id or uuid.uuid7(),
        shift_code=code,
        shift_name=code,
        start_time=start,
        end_time=end,
        cross_day=cross_day,
        rest_minutes=0,
    )


def test_shift_overlap_warnings_cover_same_day_and_cross_day() -> None:
    early = _shift("EARLY", time(8, 0), time(14, 0))
    late = _shift("LATE", time(13, 0), time(21, 0))
    night = _shift("NIGHT", time(22, 0), time(6, 0), cross_day=True)
    dawn = _shift("DAWN", time(2, 0), time(10, 0))

    same_day = expansion.shift_overlap_warnings([(1, early), (1, late)])
    assert len(same_day) == 1
    assert "时间重叠" in same_day[0]

    cross_day = expansion.shift_overlap_warnings([(1, night), (2, dawn)])
    assert len(cross_day) == 1
    assert "跨天" in cross_day[0]

    # A cross-day shift and the next day's afternoon shift do not overlap.
    assert (
        expansion.shift_overlap_warnings(
            [(1, night), (2, _shift("DAY", time(8, 0), time(17, 0)))]
        )
        == []
    )
    # Consecutive, non-overlapping same-day intervals are quiet.
    assert (
        expansion.shift_overlap_warnings(
            [
                (1, _shift("A", time(8, 0), time(12, 0))),
                (1, _shift("B", time(13, 0), time(17, 0))),
            ]
        )
        == []
    )


def test_resolve_winner_uses_precision_and_rejects_ties(db: Session) -> None:
    company = create_company(db, company_code="C-RES")
    department = create_department(db, company=company)
    position = create_position(db, company=company, dept=department)
    employee = create_employee(
        db,
        dept=department,
        position=position,
        hire_date=date(2026, 1, 1),
    )
    all_candidate = expansion.PlanCandidate(
        plan_id=uuid.uuid7(),
        plan_name="all",
        scope_type=ScheduleScopeType.ALL,
        scope_ids=frozenset(),
    )
    dept_candidate = expansion.PlanCandidate(
        plan_id=uuid.uuid7(),
        plan_name="dept",
        scope_type=ScheduleScopeType.DEPT,
        scope_ids=frozenset({department.id}),
    )
    position_candidate = expansion.PlanCandidate(
        plan_id=uuid.uuid7(),
        plan_name="position",
        scope_type=ScheduleScopeType.POSITION,
        scope_ids=frozenset({position.id}),
    )
    employee_candidate = expansion.PlanCandidate(
        plan_id=uuid.uuid7(),
        plan_name="employee",
        scope_type=ScheduleScopeType.EMPLOYEE,
        scope_ids=frozenset({employee.id}),
    )

    candidates = [
        all_candidate,
        dept_candidate,
        position_candidate,
        employee_candidate,
    ]
    assert expansion.resolve_winner(candidates, employee) is employee_candidate
    assert (
        expansion.resolve_winner(candidates[:3], employee) is position_candidate
    )
    assert expansion.resolve_winner(candidates[:2], employee) is dept_candidate
    assert expansion.resolve_winner(candidates[:1], employee) is all_candidate
    assert expansion.resolve_winner([], employee) is None

    second_dept = expansion.PlanCandidate(
        plan_id=uuid.uuid7(),
        plan_name="dept-2",
        scope_type=ScheduleScopeType.DEPT,
        scope_ids=frozenset({department.id}),
    )
    with pytest.raises(expansion.SamePrecisionConflict):
        expansion.resolve_winner([dept_candidate, second_dept], employee)


def test_plan_candidate_matches_scope_types(db: Session) -> None:
    company = create_company(db, company_code="C-MATCH")
    department = create_department(db, company=company)
    position = create_position(db, company=company, dept=department)
    employee = create_employee(
        db,
        dept=department,
        position=position,
        hire_date=date(2026, 1, 1),
    )
    assert expansion.candidate_matches(
        expansion.PlanCandidate(
            plan_id=uuid.uuid7(),
            plan_name="all",
            scope_type=ScheduleScopeType.ALL,
            scope_ids=frozenset(),
        ),
        employee,
    )
    assert not expansion.candidate_matches(
        expansion.PlanCandidate(
            plan_id=uuid.uuid7(),
            plan_name="other employee",
            scope_type=ScheduleScopeType.EMPLOYEE,
            scope_ids=frozenset({uuid.uuid7()}),
        ),
        employee,
    )
