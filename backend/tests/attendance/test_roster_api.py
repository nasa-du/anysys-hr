"""Roster API contract tests.

Seam: ``/api/v1/attendance/roster`` and ``/api/v1/attendance/roster-entries``.
The tests assert the contract from ``docs/specs/attendance-management.md``
sections 4.4, 5.1, 5.3-5.4, 8.3.3, 8.4, 8.5, and 14.3: calendar completion,
day/month/employee summaries, manual exception CRUD and batch semantics,
restore-on-delete, personnel sync, stale marking, and cross-company isolation.
"""

import uuid
from datetime import date, time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.enums import (
    AttendanceMonthStatus,
    EmployeeStatus,
    HolidayDayType,
    RosterSource,
    RosterState,
    ScheduleScopeType,
)
from app.models import (
    AttendanceMonth,
    Employee,
    RosterEntry,
    RosterEntryShift,
)
from tests.utils.attendance_factories import (
    create_attendance_month,
    create_holiday,
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

ROSTER_URL = f"{settings.API_V1_STR}/attendance/roster"
ENTRIES_URL = f"{settings.API_V1_STR}/attendance/roster-entries"
MONTH = "2026-09"
MONTH_START = date(2026, 9, 1)
LAST_DAY = date(2026, 9, 30)


def error_detail(response: Any) -> dict[str, Any]:
    body = response.json()
    assert isinstance(body["detail"], dict), body
    return body["detail"]


def entry_payload(
    employee_id: uuid.UUID,
    work_date: date,
    *,
    state: RosterState = RosterState.WORK,
    shifts: list[tuple[int, uuid.UUID]] | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "employee_id": str(employee_id),
        "work_date": work_date.isoformat(),
        "state": state.value,
        "shifts": [
            {"seq": seq, "shift_id": str(shift_id)} for seq, shift_id in shifts or []
        ],
    }
    if note is not None:
        body["note"] = note
    return body


def batch_payload(
    company_id: uuid.UUID,
    entries: list[dict[str, Any]],
    delete_entry_ids: list[uuid.UUID] | None = None,
) -> dict[str, Any]:
    return {
        "company_id": str(company_id),
        "entries": entries,
        "delete_entry_ids": [str(entry_id) for entry_id in delete_entry_ids or []],
    }


@pytest.fixture
def org(db: Session) -> dict[str, Any]:
    """One company with a department, two positions, and three employees."""
    company = create_company(db, company_code="C-ROSTER")
    department = create_department(db, company=company, dept_code="D-ROSTER")
    other_department = create_department(
        db, company=company, dept_code="D-ROSTER-2", dept_name="财务部"
    )
    position = create_position(
        db, company=company, dept=department, position_code="P-ROSTER"
    )
    employee = create_employee(
        db,
        dept=department,
        position=position,
        employee_no="E-ROSTER-1",
        name="张三",
        hire_date=date(2026, 1, 1),
    )
    late_hire = create_employee(
        db,
        dept=department,
        position=position,
        employee_no="E-ROSTER-2",
        name="李四",
        hire_date=date(2026, 9, 10),
    )
    other_employee = create_employee(
        db,
        dept=other_department,
        position=position,
        employee_no="E-ROSTER-3",
        name="王五",
        hire_date=date(2026, 1, 1),
    )
    shift = create_shift(db, company_id=company.id, shift_code="ADM")
    night = create_shift(
        db,
        company_id=company.id,
        shift_code="NIGHT",
        shift_name="夜班",
        start_time=time(22, 0),
        end_time=time(6, 0),
        cross_day=True,
        rest_minutes=0,
    )
    return {
        "company": company,
        "department": department,
        "other_department": other_department,
        "position": position,
        "employee": employee,
        "late_hire": late_hire,
        "other_employee": other_employee,
        "shift": shift,
        "night": night,
    }


def month_entries(session: Session, employee_id: uuid.UUID) -> list[RosterEntry]:
    session.expire_all()
    return list(
        session.exec(
            select(RosterEntry)
            .where(
                RosterEntry.employee_id == employee_id,
                RosterEntry.work_date >= MONTH_START,
                RosterEntry.work_date <= LAST_DAY,
            )
            .order_by(RosterEntry.work_date.asc())
        ).all()
    )


def entry_shifts(session: Session, entry_id: uuid.UUID) -> list[RosterEntryShift]:
    session.expire_all()
    return list(
        session.exec(
            select(RosterEntryShift)
            .where(RosterEntryShift.roster_entry_id == entry_id)
            .order_by(RosterEntryShift.seq.asc())
        ).all()
    )


def entry_for(
    session: Session, employee_id: uuid.UUID, work_date: date
) -> RosterEntry | None:
    session.expire_all()
    return session.exec(
        select(RosterEntry).where(
            RosterEntry.employee_id == employee_id,
            RosterEntry.work_date == work_date,
        )
    ).first()


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


def test_all_roster_endpoints_require_authentication(client: TestClient) -> None:
    entry_id = uuid.uuid7()
    company_id = uuid.uuid7()
    employee_id = uuid.uuid7()
    no_auth_calls = [
        client.get(
            f"{ROSTER_URL}/calendar",
            params={
                "company_id": company_id,
                "month": MONTH,
                "employee_id": employee_id,
            },
        ),
        client.get(
            f"{ROSTER_URL}/day",
            params={"company_id": company_id, "date": "2026-09-01"},
        ),
        client.get(
            f"{ROSTER_URL}/month",
            params={"company_id": company_id, "month": MONTH},
        ),
        client.get(
            f"{ROSTER_URL}/employees",
            params={"company_id": company_id, "month": MONTH},
        ),
        client.get(
            f"{ROSTER_URL}/sync-preview",
            params={"company_id": company_id, "month": MONTH},
        ),
        client.post(
            f"{ROSTER_URL}/sync",
            json={"company_id": str(company_id), "month": MONTH},
        ),
        client.get(ENTRIES_URL, params={"company_id": company_id}),
        client.get(f"{ENTRIES_URL}/{entry_id}"),
        client.post(ENTRIES_URL, json={}),
        client.patch(f"{ENTRIES_URL}/{entry_id}", json={}),
        client.delete(f"{ENTRIES_URL}/{entry_id}"),
        client.post(f"{ENTRIES_URL}/batch", json={}),
    ]
    for response in no_auth_calls:
        assert response.status_code == 401, response.text


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------


def test_employee_calendar_fills_unscheduled_dates(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company = org["company"]
    employee = org["employee"]
    shift = org["shift"]
    create_holiday(
        db,
        company_id=company.id,
        holiday_date=date(2026, 9, 25),
        day_type=HolidayDayType.HOLIDAY,
    )
    create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 1),
        state=RosterState.WORK,
        source=RosterSource.PLAN,
        shifts=[shift],
    )
    create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 2),
        state=RosterState.REST,
        source=RosterSource.MANUAL,
        note="调休",
    )

    response = client.get(
        f"{ROSTER_URL}/calendar",
        headers=superuser_token_headers,
        params={
            "company_id": str(company.id),
            "month": MONTH,
            "employee_id": str(employee.id),
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["month"] == MONTH
    assert body["employee"]["employee_no"] == "E-ROSTER-1"
    assert len(body["days"]) == 30

    first, second, third, holiday = (
        body["days"][0],
        body["days"][1],
        body["days"][2],
        body["days"][24],
    )
    assert first["work_date"] == "2026-09-01"
    assert first["state"] == "work"
    assert first["source"] == "plan"
    assert first["shifts"][0]["shift_code"] == "ADM"

    assert second["state"] == "rest"
    assert second["source"] == "manual"
    assert second["note"] == "调休"
    assert second["shifts"] == []

    assert third["state"] == "unscheduled"
    assert third["source"] is None
    assert third["plan_id"] is None
    assert third["shifts"] == []

    assert holiday["day_type"] == "holiday"
    assert holiday["state"] == "unscheduled"


def test_calendar_rejects_cross_company_employee(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    other_company = create_company(db, company_code="C-ROSTER-OTHER")
    other_department = create_department(db, company=other_company, dept_code="D-O")
    other_position = create_position(db, company=other_company, dept=other_department)
    outsider = create_employee(
        db, dept=other_department, position=other_position, employee_no="E-OUT"
    )

    response = client.get(
        f"{ROSTER_URL}/calendar",
        headers=superuser_token_headers,
        params={
            "company_id": str(org["company"].id),
            "month": MONTH,
            "employee_id": str(outsider.id),
        },
    )
    assert response.status_code == 404
    assert error_detail(response)["code"] == "not_found"


def test_calendar_requires_existing_company(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    org: dict[str, Any],
) -> None:
    response = client.get(
        f"{ROSTER_URL}/calendar",
        headers=superuser_token_headers,
        params={
            "company_id": str(uuid.uuid7()),
            "month": MONTH,
            "employee_id": str(org["employee"].id),
        },
    )
    assert response.status_code == 404
    assert error_detail(response)["code"] == "not_found"


# ---------------------------------------------------------------------------
# Entry list and detail
# ---------------------------------------------------------------------------


def test_entry_list_returns_real_rows_and_filters(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company = org["company"]
    employee = org["employee"]
    other_employee = org["other_employee"]
    shift = org["shift"]
    plan = create_schedule_plan(
        db,
        company_id=company.id,
        plan_name="行政班",
        days=[(1, 0, shift.id)],
    )
    plan_entry = create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 1),
        state=RosterState.WORK,
        source=RosterSource.PLAN,
        plan_id=plan.id,
        shifts=[shift],
    )
    manual_entry = create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 2),
        state=RosterState.REST,
        source=RosterSource.MANUAL,
    )
    other_entry = create_roster_entry(
        db,
        company_id=company.id,
        employee_id=other_employee.id,
        work_date=date(2026, 9, 1),
        state=RosterState.WORK,
        source=RosterSource.PLAN,
        plan_id=plan.id,
        shifts=[shift],
    )

    response = client.get(
        ENTRIES_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "month": MONTH},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["count"] == 3
    assert len(body["data"]) == 3
    assert {item["id"] for item in body["data"]} == {
        str(plan_entry.id),
        str(manual_entry.id),
        str(other_entry.id),
    }
    by_id = {item["id"]: item for item in body["data"]}
    assert by_id[str(plan_entry.id)]["employee_no"] == "E-ROSTER-1"
    assert by_id[str(plan_entry.id)]["department_name"] == "生产部"
    assert by_id[str(plan_entry.id)]["shifts"][0]["shift_code"] == "ADM"

    by_source = client.get(
        ENTRIES_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "source": "manual"},
    )
    assert by_source.json()["count"] == 1
    assert by_source.json()["data"][0]["id"] == str(manual_entry.id)

    by_state = client.get(
        ENTRIES_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "state": "rest"},
    )
    assert by_state.json()["count"] == 1

    by_employee = client.get(
        ENTRIES_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "employee_id": str(other_employee.id)},
    )
    assert by_employee.json()["count"] == 1
    assert by_employee.json()["data"][0]["id"] == str(other_entry.id)

    by_dept = client.get(
        ENTRIES_URL,
        headers=superuser_token_headers,
        params={
            "company_id": str(company.id),
            "dept_id": str(org["other_department"].id),
        },
    )
    assert by_dept.json()["count"] == 1


def test_entry_list_is_company_scoped(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    other_company = create_company(db, company_code="C-ROSTER-OTHER")
    other_department = create_department(db, company=other_company, dept_code="D-O")
    other_position = create_position(db, company=other_company, dept=other_department)
    outsider = create_employee(
        db, dept=other_department, position=other_position, employee_no="E-OUT"
    )
    create_roster_entry(
        db,
        company_id=other_company.id,
        employee_id=outsider.id,
        work_date=date(2026, 9, 1),
        state=RosterState.REST,
        source=RosterSource.MANUAL,
    )

    response = client.get(
        ENTRIES_URL,
        headers=superuser_token_headers,
        params={"company_id": str(org["company"].id)},
    )
    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_entry_detail_returns_shifts_and_404s(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    entry = create_roster_entry(
        db,
        company_id=org["company"].id,
        employee_id=org["employee"].id,
        work_date=date(2026, 9, 1),
        state=RosterState.WORK,
        source=RosterSource.MANUAL,
        shifts=[org["shift"], org["night"]],
        note="双班",
    )
    response = client.get(f"{ENTRIES_URL}/{entry.id}", headers=superuser_token_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == "manual"
    assert body["note"] == "双班"
    assert [shift["shift_code"] for shift in body["shifts"]] == ["ADM", "NIGHT"]

    missing = client.get(
        f"{ENTRIES_URL}/{uuid.uuid7()}", headers=superuser_token_headers
    )
    assert missing.status_code == 404
    assert error_detail(missing)["code"] == "not_found"


# ---------------------------------------------------------------------------
# Day and month views
# ---------------------------------------------------------------------------


def test_day_view_lists_scheduled_employees_and_unscheduled_count(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company = org["company"]
    employee = org["employee"]
    other_employee = org["other_employee"]
    shift = org["shift"]
    create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 1),
        state=RosterState.WORK,
        source=RosterSource.PLAN,
        shifts=[shift],
    )
    create_roster_entry(
        db,
        company_id=company.id,
        employee_id=other_employee.id,
        work_date=date(2026, 9, 1),
        state=RosterState.REST,
        source=RosterSource.MANUAL,
    )

    response = client.get(
        f"{ROSTER_URL}/day",
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "date": "2026-09-01"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["date"] == "2026-09-01"
    assert len(body["employees"]) == 2
    by_id = {item["employee"]["employee_id"]: item for item in body["employees"]}
    assert by_id[str(employee.id)]["state"] == "work"
    assert by_id[str(employee.id)]["shifts"][0]["shift_code"] == "ADM"
    assert by_id[str(other_employee.id)]["state"] == "rest"
    # Both employed employees have a row; 李四 is hired 09-10 and is excluded.
    assert body["unscheduled_count"] == 0

    dept_response = client.get(
        f"{ROSTER_URL}/day",
        headers=superuser_token_headers,
        params={
            "company_id": str(company.id),
            "date": "2026-09-01",
            "dept_id": str(org["other_department"].id),
        },
    )
    assert dept_response.status_code == 200
    assert len(dept_response.json()["employees"]) == 1
    assert dept_response.json()["unscheduled_count"] == 0


def test_month_overview_counts_shifts_and_plans(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company = org["company"]
    employee = org["employee"]
    shift = org["shift"]
    plan = create_schedule_plan(
        db,
        company_id=company.id,
        plan_name="行政班",
        days=[(1, 0, shift.id)],
    )
    create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 1),
        state=RosterState.WORK,
        source=RosterSource.PLAN,
        plan_id=plan.id,
        shifts=[shift, org["night"]],
    )
    create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 2),
        state=RosterState.REST,
        source=RosterSource.MANUAL,
    )
    create_holiday(
        db,
        company_id=company.id,
        holiday_date=date(2026, 9, 25),
        day_type=HolidayDayType.HOLIDAY,
    )

    response = client.get(
        f"{ROSTER_URL}/month",
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "month": MONTH},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["month"] == MONTH
    assert len(body["days"]) == 30
    days = {item["date"]: item for item in body["days"]}

    assert days["2026-09-01"]["work_count"] == 1
    assert days["2026-09-01"]["rest_count"] == 0
    assert days["2026-09-01"]["manual_count"] == 0
    assert days["2026-09-01"]["shift_counts"] == [
        {
            "shift_id": str(shift.id),
            "shift_code": "ADM",
            "shift_name": "行政班",
            "color": None,
            "count": 1,
        },
        {
            "shift_id": str(org["night"].id),
            "shift_code": "NIGHT",
            "shift_name": "夜班",
            "color": None,
            "count": 1,
        },
    ]
    assert days["2026-09-01"]["unscheduled_count"] == 1  # 王五
    assert days["2026-09-02"]["rest_count"] == 1
    assert days["2026-09-02"]["manual_count"] == 1
    assert days["2026-09-25"]["day_type"] == "holiday"
    assert days["2026-09-25"]["unscheduled_count"] == 3

    assert [item["plan_name"] for item in body["plans"]] == ["行政班"]


def test_employee_summaries_count_days_and_manual_exceptions(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company = org["company"]
    employee = org["employee"]
    shift = org["shift"]
    create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 1),
        state=RosterState.WORK,
        source=RosterSource.PLAN,
        shifts=[shift],
    )
    create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 2),
        state=RosterState.REST,
        source=RosterSource.MANUAL,
    )

    response = client.get(
        f"{ROSTER_URL}/employees",
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "month": MONTH},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["count"] == 3
    rows = {item["employee_no"]: item for item in body["data"]}
    assert rows["E-ROSTER-1"]["work_days"] == 1
    assert rows["E-ROSTER-1"]["rest_days"] == 1
    assert rows["E-ROSTER-1"]["manual_exception_count"] == 1
    assert rows["E-ROSTER-1"]["unscheduled_days"] == 28
    # 李四 is employed from 09-10, so only 21 days can be unscheduled.
    assert rows["E-ROSTER-2"]["unscheduled_days"] == 21

    keyword = client.get(
        f"{ROSTER_URL}/employees",
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "month": MONTH, "keyword": "李四"},
    )
    assert keyword.json()["count"] == 1
    assert keyword.json()["data"][0]["employee_no"] == "E-ROSTER-2"

    dept = client.get(
        f"{ROSTER_URL}/employees",
        headers=superuser_token_headers,
        params={
            "company_id": str(company.id),
            "month": MONTH,
            "dept_id": str(org["other_department"].id),
        },
    )
    assert dept.json()["count"] == 1


# ---------------------------------------------------------------------------
# Manual exceptions
# ---------------------------------------------------------------------------


def test_create_manual_exception_overrides_plan_entry(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company = org["company"]
    employee = org["employee"]
    shift = org["shift"]
    plan = create_schedule_plan(
        db,
        company_id=company.id,
        plan_name="行政班",
        days=[(1, 0, shift.id)],
    )
    create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 1),
        state=RosterState.WORK,
        source=RosterSource.PLAN,
        plan_id=plan.id,
        shifts=[shift],
    )
    create_attendance_month(
        db,
        company_id=company.id,
        month=MONTH_START,
        status=AttendanceMonthStatus.CALCULATED,
        is_stale=False,
    )

    response = client.post(
        ENTRIES_URL,
        headers=superuser_token_headers,
        json=entry_payload(
            employee.id,
            date(2026, 9, 1),
            state=RosterState.REST,
            note="临时休息",
        ),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["source"] == "manual"
    assert body["state"] == "rest"
    assert body["plan_id"] == str(plan.id)
    assert body["note"] == "临时休息"
    assert body["shifts"] == []

    row = entry_for(db, employee.id, date(2026, 9, 1))
    assert row is not None
    assert row.source == RosterSource.MANUAL
    assert row.plan_id == plan.id
    assert entry_shifts(db, row.id) == []
    month_row = db.exec(
        select(AttendanceMonth).where(AttendanceMonth.company_id == company.id)
    ).one()
    assert month_row.is_stale is True


def test_create_manual_exception_on_unscheduled_date_keeps_null_plan(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    response = client.post(
        ENTRIES_URL,
        headers=superuser_token_headers,
        json=entry_payload(
            org["employee"].id,
            date(2026, 9, 12),
            state=RosterState.WORK,
            shifts=[(0, org["shift"].id), (1, org["night"].id)],
        ),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["plan_id"] is None
    assert [shift["shift_code"] for shift in body["shifts"]] == ["ADM", "NIGHT"]
    assert len(month_entries(db, org["employee"].id)) == 1

    month_row = db.exec(
        select(AttendanceMonth).where(AttendanceMonth.company_id == org["company"].id)
    ).one()
    assert month_row.status == AttendanceMonthStatus.DRAFT
    assert month_row.is_stale is True


def test_create_manual_exception_validates_state_and_shifts(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    org: dict[str, Any],
) -> None:
    employee = org["employee"]
    shift = org["shift"]

    rest_with_shifts = client.post(
        ENTRIES_URL,
        headers=superuser_token_headers,
        json=entry_payload(
            employee.id,
            date(2026, 9, 1),
            state=RosterState.REST,
            shifts=[(0, shift.id)],
        ),
    )
    assert rest_with_shifts.status_code == 409
    assert error_detail(rest_with_shifts)["code"] == "invalid_scope"

    work_without_shifts = client.post(
        ENTRIES_URL,
        headers=superuser_token_headers,
        json=entry_payload(
            employee.id, date(2026, 9, 1), state=RosterState.WORK, shifts=[]
        ),
    )
    assert work_without_shifts.status_code == 409
    assert error_detail(work_without_shifts)["code"] == "invalid_scope"


def test_create_manual_exception_validates_employee_and_shift_references(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    employee = org["employee"]
    other_company = create_company(db, company_code="C-ROSTER-OTHER")
    outsider_shift = create_shift(db, company_id=other_company.id)

    missing_employee = client.post(
        ENTRIES_URL,
        headers=superuser_token_headers,
        json=entry_payload(
            uuid.uuid7(), date(2026, 9, 1), shifts=[(0, org["shift"].id)]
        ),
    )
    assert missing_employee.status_code == 409
    assert error_detail(missing_employee)["code"] == "invalid_reference"

    cross_shift = client.post(
        ENTRIES_URL,
        headers=superuser_token_headers,
        json=entry_payload(
            employee.id, date(2026, 9, 1), shifts=[(0, outsider_shift.id)]
        ),
    )
    assert cross_shift.status_code == 409
    assert error_detail(cross_shift)["code"] == "cross_company"

    missing_shift = client.post(
        ENTRIES_URL,
        headers=superuser_token_headers,
        json=entry_payload(employee.id, date(2026, 9, 1), shifts=[(0, uuid.uuid7())]),
    )
    assert missing_shift.status_code == 409
    assert error_detail(missing_shift)["code"] == "invalid_reference"


def test_create_manual_exception_respects_employment_range_and_month_state(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company = org["company"]
    late_hire = org["late_hire"]
    shift = org["shift"]

    too_early = client.post(
        ENTRIES_URL,
        headers=superuser_token_headers,
        json=entry_payload(late_hire.id, date(2026, 9, 9), shifts=[(0, shift.id)]),
    )
    assert too_early.status_code == 409
    assert error_detail(too_early)["code"] == "employee_out_of_range"
    assert error_detail(too_early)["field_errors"]["work_date"]

    create_attendance_month(
        db,
        company_id=company.id,
        month=MONTH_START,
        status=AttendanceMonthStatus.CONFIRMED,
    )
    confirmed = client.post(
        ENTRIES_URL,
        headers=superuser_token_headers,
        json=entry_payload(
            org["employee"].id, date(2026, 9, 2), shifts=[(0, shift.id)]
        ),
    )
    assert confirmed.status_code == 409
    assert error_detail(confirmed)["code"] == "month_confirmed"

    db.exec(
        select(AttendanceMonth).where(AttendanceMonth.company_id == company.id)
    ).one().status = AttendanceMonthStatus.LOCKED
    db.commit()
    locked = client.post(
        ENTRIES_URL,
        headers=superuser_token_headers,
        json=entry_payload(
            org["employee"].id, date(2026, 9, 2), shifts=[(0, shift.id)]
        ),
    )
    assert locked.status_code == 409
    assert error_detail(locked)["code"] == "month_locked"


def test_patch_delete_and_batch_are_blocked_in_confirmed_and_locked_months(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company = org["company"]
    employee = org["employee"]
    shift = org["shift"]
    manual = create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 1),
        state=RosterState.REST,
        source=RosterSource.MANUAL,
    )
    manual_id = manual.id
    create_attendance_month(
        db,
        company_id=company.id,
        month=MONTH_START,
        status=AttendanceMonthStatus.CONFIRMED,
    )

    patched = client.patch(
        f"{ENTRIES_URL}/{manual_id}",
        headers=superuser_token_headers,
        json={"note": "确认后修改"},
    )
    assert patched.status_code == 409
    assert error_detail(patched)["code"] == "month_confirmed"

    deleted = client.delete(
        f"{ENTRIES_URL}/{manual_id}", headers=superuser_token_headers
    )
    assert deleted.status_code == 409
    assert error_detail(deleted)["code"] == "month_confirmed"

    batch_create = client.post(
        f"{ENTRIES_URL}/batch",
        headers=superuser_token_headers,
        json=batch_payload(
            company.id,
            [entry_payload(employee.id, date(2026, 9, 2), shifts=[(0, shift.id)])],
        ),
    )
    assert batch_create.status_code == 409
    assert error_detail(batch_create)["code"] == "roster_batch_invalid"
    assert "entries[0].work_date" in error_detail(batch_create)["field_errors"]

    batch_delete = client.post(
        f"{ENTRIES_URL}/batch",
        headers=superuser_token_headers,
        json=batch_payload(company.id, [], delete_entry_ids=[manual_id]),
    )
    assert batch_delete.status_code == 409
    assert "delete_entry_ids[0]" in error_detail(batch_delete)["field_errors"]

    month_row = db.exec(
        select(AttendanceMonth).where(AttendanceMonth.company_id == company.id)
    ).one()
    month_row.status = AttendanceMonthStatus.LOCKED
    db.commit()

    locked_patch = client.patch(
        f"{ENTRIES_URL}/{manual_id}",
        headers=superuser_token_headers,
        json={"note": "锁定后修改"},
    )
    assert locked_patch.status_code == 409
    assert error_detail(locked_patch)["code"] == "month_locked"

    locked_delete = client.delete(
        f"{ENTRIES_URL}/{manual_id}", headers=superuser_token_headers
    )
    assert locked_delete.status_code == 409
    assert error_detail(locked_delete)["code"] == "month_locked"


def test_patch_and_delete_reject_plan_generated_entries(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    entry = create_roster_entry(
        db,
        company_id=org["company"].id,
        employee_id=org["employee"].id,
        work_date=date(2026, 9, 1),
        state=RosterState.WORK,
        source=RosterSource.PLAN,
        shifts=[org["shift"]],
    )

    patched = client.patch(
        f"{ENTRIES_URL}/{entry.id}",
        headers=superuser_token_headers,
        json={"state": "rest", "shifts": []},
    )
    assert patched.status_code == 409
    assert error_detail(patched)["code"] == "roster_entry_not_manual"

    deleted = client.delete(
        f"{ENTRIES_URL}/{entry.id}", headers=superuser_token_headers
    )
    assert deleted.status_code == 409
    assert error_detail(deleted)["code"] == "roster_entry_not_manual"
    assert entry_for(db, org["employee"].id, date(2026, 9, 1)) is not None


def test_patch_manual_exception_replaces_state_and_shifts(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    create_attendance_month(
        db,
        company_id=org["company"].id,
        month=MONTH_START,
        status=AttendanceMonthStatus.CALCULATED,
        is_stale=False,
    )
    entry = create_roster_entry(
        db,
        company_id=org["company"].id,
        employee_id=org["employee"].id,
        work_date=date(2026, 9, 1),
        state=RosterState.WORK,
        source=RosterSource.MANUAL,
        shifts=[org["shift"]],
        note="旧备注",
    )
    response = client.patch(
        f"{ENTRIES_URL}/{entry.id}",
        headers=superuser_token_headers,
        json={
            "state": "work",
            "shifts": [{"seq": 0, "shift_id": str(org["night"].id)}],
            "note": "改为夜班",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == "manual"
    assert body["note"] == "改为夜班"
    assert [shift["shift_code"] for shift in body["shifts"]] == ["NIGHT"]

    month_row = db.exec(
        select(AttendanceMonth).where(AttendanceMonth.company_id == org["company"].id)
    ).one()
    assert month_row.is_stale is True

    rest_only = client.patch(
        f"{ENTRIES_URL}/{entry.id}",
        headers=superuser_token_headers,
        json={"state": "rest"},
    )
    assert rest_only.status_code == 200, rest_only.text
    assert rest_only.json()["state"] == "rest"
    assert rest_only.json()["shifts"] == []

    note_only = client.patch(
        f"{ENTRIES_URL}/{entry.id}",
        headers=superuser_token_headers,
        json={"note": "只改备注"},
    )
    assert note_only.status_code == 200, note_only.text
    assert note_only.json()["note"] == "只改备注"
    assert note_only.json()["state"] == "rest"
    assert note_only.json()["shifts"] == []

    missing = client.patch(
        f"{ENTRIES_URL}/{uuid.uuid7()}",
        headers=superuser_token_headers,
        json={"note": "x"},
    )
    assert missing.status_code == 404


def test_delete_manual_exception_restores_current_plan_resolution(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company = org["company"]
    employee = org["employee"]
    shift = org["shift"]
    plan = create_schedule_plan(
        db,
        company_id=company.id,
        plan_name="行政班",
        days=[(1, 0, shift.id)],
    )
    manual = create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 1),
        state=RosterState.REST,
        source=RosterSource.MANUAL,
        plan_id=plan.id,
    )
    create_attendance_month(
        db,
        company_id=company.id,
        month=MONTH_START,
        status=AttendanceMonthStatus.CALCULATED,
        is_stale=False,
    )

    manual_id = manual.id
    response = client.delete(
        f"{ENTRIES_URL}/{manual_id}", headers=superuser_token_headers
    )
    assert response.status_code == 200, response.text
    restored = entry_for(db, employee.id, date(2026, 9, 1))
    assert restored is not None
    assert restored.id != manual_id
    assert restored.source == RosterSource.PLAN
    assert restored.plan_id == plan.id
    assert restored.state == RosterState.WORK
    assert [shift.shift_code for shift in entry_shifts(db, restored.id)] == ["ADM"]
    month_row = db.exec(
        select(AttendanceMonth).where(AttendanceMonth.company_id == company.id)
    ).one()
    assert month_row.is_stale is True


def test_delete_manual_exception_without_plan_deletes_to_unscheduled(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    manual = create_roster_entry(
        db,
        company_id=org["company"].id,
        employee_id=org["employee"].id,
        work_date=date(2026, 9, 2),
        state=RosterState.WORK,
        source=RosterSource.MANUAL,
        shifts=[org["shift"]],
    )
    response = client.delete(
        f"{ENTRIES_URL}/{manual.id}", headers=superuser_token_headers
    )
    assert response.status_code == 200, response.text
    assert entry_for(db, org["employee"].id, date(2026, 9, 2)) is None


# ---------------------------------------------------------------------------
# Batch exceptions
# ---------------------------------------------------------------------------


def test_batch_creates_and_deletes_in_one_transaction(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company = org["company"]
    employee = org["employee"]
    other_employee = org["other_employee"]
    shift = org["shift"]
    manual = create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 3),
        state=RosterState.REST,
        source=RosterSource.MANUAL,
    )

    response = client.post(
        f"{ENTRIES_URL}/batch",
        headers=superuser_token_headers,
        json=batch_payload(
            company.id,
            [
                entry_payload(employee.id, date(2026, 9, 1), shifts=[(0, shift.id)]),
                entry_payload(
                    other_employee.id, date(2026, 9, 2), shifts=[(0, shift.id)]
                ),
            ],
            delete_entry_ids=[manual.id],
        ),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["created"] == 2
    assert body["updated"] == 0
    assert body["deleted"] == 1
    assert body["month_stale"] is True

    assert entry_for(db, employee.id, date(2026, 9, 1)) is not None
    assert entry_for(db, other_employee.id, date(2026, 9, 2)) is not None
    assert entry_for(db, employee.id, date(2026, 9, 3)) is None


def test_batch_is_all_or_nothing_with_indexed_errors(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company = org["company"]
    employee = org["employee"]
    shift = org["shift"]
    late_hire = org["late_hire"]

    response = client.post(
        f"{ENTRIES_URL}/batch",
        headers=superuser_token_headers,
        json=batch_payload(
            company.id,
            [
                entry_payload(employee.id, date(2026, 9, 1), shifts=[(0, shift.id)]),
                # 李四 is not employed yet on 09-09: the whole batch must fail.
                entry_payload(late_hire.id, date(2026, 9, 9), shifts=[(0, shift.id)]),
            ],
        ),
    )
    assert response.status_code == 409, response.text
    detail = error_detail(response)
    assert detail["code"] == "roster_batch_invalid"
    assert "entries[1].work_date" in detail["field_errors"]
    assert entry_for(db, employee.id, date(2026, 9, 1)) is None


def test_batch_reports_indexed_field_errors(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    org: dict[str, Any],
) -> None:
    company = org["company"]
    employee = org["employee"]
    shift = org["shift"]

    response = client.post(
        f"{ENTRIES_URL}/batch",
        headers=superuser_token_headers,
        json=batch_payload(
            company.id,
            [
                entry_payload(employee.id, date(2026, 9, 1), shifts=[(0, shift.id)]),
                entry_payload(
                    employee.id,
                    date(2026, 9, 2),
                    state=RosterState.REST,
                    shifts=[(0, shift.id)],
                ),
            ],
        ),
    )
    assert response.status_code == 409, response.text
    detail = error_detail(response)
    assert detail["code"] == "roster_batch_invalid"
    assert "entries[1].shifts" in detail["field_errors"]


def test_batch_rejects_duplicate_employee_day_and_duplicate_delete(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company = org["company"]
    employee = org["employee"]
    shift = org["shift"]
    manual = create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 3),
        state=RosterState.REST,
        source=RosterSource.MANUAL,
    )

    duplicate = client.post(
        f"{ENTRIES_URL}/batch",
        headers=superuser_token_headers,
        json=batch_payload(
            company.id,
            [
                entry_payload(employee.id, date(2026, 9, 1), shifts=[(0, shift.id)]),
                entry_payload(employee.id, date(2026, 9, 1), shifts=[(0, shift.id)]),
            ],
        ),
    )
    assert duplicate.status_code == 409
    assert "entries[1].work_date" in error_detail(duplicate)["field_errors"]

    conflicting_delete = client.post(
        f"{ENTRIES_URL}/batch",
        headers=superuser_token_headers,
        json=batch_payload(
            company.id,
            [entry_payload(employee.id, date(2026, 9, 3), shifts=[(0, shift.id)])],
            delete_entry_ids=[manual.id],
        ),
    )
    assert conflicting_delete.status_code == 409
    assert "entries[0].work_date" in error_detail(conflicting_delete)["field_errors"]


def test_batch_updates_existing_manual_entry_by_id(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    manual = create_roster_entry(
        db,
        company_id=org["company"].id,
        employee_id=org["employee"].id,
        work_date=date(2026, 9, 3),
        state=RosterState.WORK,
        source=RosterSource.MANUAL,
        shifts=[org["shift"]],
    )
    response = client.post(
        f"{ENTRIES_URL}/batch",
        headers=superuser_token_headers,
        json=batch_payload(
            org["company"].id,
            [
                {
                    **entry_payload(
                        org["employee"].id, date(2026, 9, 3), state=RosterState.REST
                    ),
                    "entry_id": str(manual.id),
                }
            ],
        ),
    )
    assert response.status_code == 200, response.text
    assert response.json()["created"] == 0
    assert response.json()["updated"] == 1
    row = entry_for(db, org["employee"].id, date(2026, 9, 3))
    assert row is not None
    assert row.state == RosterState.REST
    assert entry_shifts(db, row.id) == []


def test_batch_rejects_updating_or_deleting_plan_entries(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    plan_entry = create_roster_entry(
        db,
        company_id=org["company"].id,
        employee_id=org["employee"].id,
        work_date=date(2026, 9, 1),
        state=RosterState.WORK,
        source=RosterSource.PLAN,
        shifts=[org["shift"]],
    )
    update_response = client.post(
        f"{ENTRIES_URL}/batch",
        headers=superuser_token_headers,
        json=batch_payload(
            org["company"].id,
            [
                {
                    **entry_payload(
                        org["employee"].id,
                        date(2026, 9, 1),
                        state=RosterState.REST,
                    ),
                    "entry_id": str(plan_entry.id),
                }
            ],
        ),
    )
    assert update_response.status_code == 409
    assert "entries[0].entry_id" in error_detail(update_response)["field_errors"]

    delete_response = client.post(
        f"{ENTRIES_URL}/batch",
        headers=superuser_token_headers,
        json=batch_payload(org["company"].id, [], delete_entry_ids=[plan_entry.id]),
    )
    assert delete_response.status_code == 409
    assert "delete_entry_ids[0]" in error_detail(delete_response)["field_errors"]
    assert entry_for(db, org["employee"].id, date(2026, 9, 1)) is not None


# ---------------------------------------------------------------------------
# Personnel sync
# ---------------------------------------------------------------------------


def test_sync_preview_and_apply_report_employee_and_entry_changes(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company = org["company"]
    employee = org["employee"]
    late_hire = org["late_hire"]
    other_employee = org["other_employee"]
    shift = org["shift"]
    plan = create_schedule_plan(
        db,
        company_id=company.id,
        plan_name="张三行政班",
        scope_type=ScheduleScopeType.EMPLOYEE,
        scope_ids=[employee.id],
        days=[(1, 0, shift.id), (10, 0, shift.id)],
    )
    create_schedule_plan(
        db,
        company_id=company.id,
        plan_name="李四入职班",
        scope_type=ScheduleScopeType.EMPLOYEE,
        scope_ids=[late_hire.id],
        days=[(10, 0, shift.id)],
    )
    # A stale plan row for 09-01, a row that becomes rest on 09-03, an orphaned
    # row for 王五, and a manual exception that must survive.
    create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 1),
        state=RosterState.WORK,
        source=RosterSource.PLAN,
        plan_id=plan.id,
        shifts=[shift],
    )
    create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 3),
        state=RosterState.WORK,
        source=RosterSource.PLAN,
        plan_id=plan.id,
        shifts=[shift],
    )
    create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 2),
        state=RosterState.REST,
        source=RosterSource.MANUAL,
    )
    create_roster_entry(
        db,
        company_id=company.id,
        employee_id=other_employee.id,
        work_date=date(2026, 9, 1),
        state=RosterState.WORK,
        source=RosterSource.PLAN,
        plan_id=plan.id,
        shifts=[shift],
    )
    create_attendance_month(
        db,
        company_id=company.id,
        month=MONTH_START,
        status=AttendanceMonthStatus.CALCULATED,
        is_stale=False,
    )

    preview = client.get(
        f"{ROSTER_URL}/sync-preview",
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "month": MONTH},
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["added"] == 1  # 李四 enters the roster from his hire date
    assert body["removed"] == 1  # 王五's orphaned plan row disappears
    assert body["changed"] == 1  # 张三 keeps rows but 09-03 becomes rest
    assert body["entries_added"] == 48  # 张三 27 remaining days + 李四 21 days
    assert body["entries_updated"] == 1
    assert body["entries_deleted"] == 1
    assert body["manual_preserved"] == 1

    applied = client.post(
        f"{ROSTER_URL}/sync",
        headers=superuser_token_headers,
        json={"company_id": str(company.id), "month": MONTH},
    )
    assert applied.status_code == 200, applied.text
    result = applied.json()
    assert result["added"] == 1
    assert result["removed"] == 1
    assert result["changed"] == 1
    assert result["entries_added"] == 48
    assert result["entries_updated"] == 1
    assert result["entries_deleted"] == 1
    assert result["manual_preserved"] == 1
    assert result["month_stale"] is True

    rows = month_entries(db, employee.id)
    assert len(rows) == 30
    by_day = {row.work_date.day: row for row in rows}
    assert by_day[1].state == RosterState.WORK
    assert by_day[1].source == RosterSource.PLAN
    assert by_day[2].source == RosterSource.MANUAL
    assert by_day[2].state == RosterState.REST
    assert by_day[3].state == RosterState.REST
    assert by_day[10].state == RosterState.WORK
    late_rows = month_entries(db, late_hire.id)
    assert [row.work_date.day for row in late_rows] == list(range(10, 31))
    assert month_entries(db, other_employee.id) == []


def test_sync_uses_current_department_for_the_whole_month(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company = org["company"]
    employee = org["employee"]
    shift = org["shift"]
    # A plan that covers 财务部 only. The employee currently belongs to 生产部.
    create_schedule_plan(
        db,
        company_id=company.id,
        plan_name="财务技术班",
        scope_type=ScheduleScopeType.DEPT,
        scope_ids=[org["other_department"].id],
        days=[(1, 0, shift.id)],
    )
    create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 1),
        state=RosterState.WORK,
        source=RosterSource.PLAN,
        shifts=[shift],
    )

    preview = client.get(
        f"{ROSTER_URL}/sync-preview",
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "month": MONTH},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["removed"] == 1
    assert preview.json()["entries_deleted"] == 1


def test_sync_is_blocked_in_confirmed_and_locked_months(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company = org["company"]
    create_attendance_month(
        db,
        company_id=company.id,
        month=MONTH_START,
        status=AttendanceMonthStatus.CONFIRMED,
    )
    preview = client.get(
        f"{ROSTER_URL}/sync-preview",
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "month": MONTH},
    )
    assert preview.status_code == 409
    assert error_detail(preview)["code"] == "schedule_expansion_blocked"

    applied = client.post(
        f"{ROSTER_URL}/sync",
        headers=superuser_token_headers,
        json={"company_id": str(company.id), "month": MONTH},
    )
    assert applied.status_code == 409
    assert error_detail(applied)["code"] == "schedule_expansion_blocked"


def test_roster_reads_reject_cross_company_department_filters(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    other_company = create_company(db, company_code="C-ROSTER-OTHER")
    outsider_department = create_department(db, company=other_company, dept_code="D-O")
    params = {
        "company_id": str(org["company"].id),
        "dept_id": str(outsider_department.id),
    }
    calls = [
        client.get(
            f"{ROSTER_URL}/day",
            headers=superuser_token_headers,
            params={**params, "date": "2026-09-01"},
        ),
        client.get(
            f"{ROSTER_URL}/month",
            headers=superuser_token_headers,
            params={**params, "month": MONTH},
        ),
        client.get(
            f"{ROSTER_URL}/employees",
            headers=superuser_token_headers,
            params={**params, "month": MONTH},
        ),
        client.get(ENTRIES_URL, headers=superuser_token_headers, params=params),
    ]
    for response in calls:
        assert response.status_code == 404, response.text
        assert error_detail(response)["code"] == "not_found"


def test_sync_only_touches_the_requested_company(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    other_company = create_company(db, company_code="C-ROSTER-OTHER")
    other_department = create_department(db, company=other_company, dept_code="D-O")
    other_position = create_position(db, company=other_company, dept=other_department)
    outsider = create_employee(
        db, dept=other_department, position=other_position, employee_no="E-OUT"
    )
    other_shift = create_shift(db, company_id=other_company.id)
    create_schedule_plan(
        db,
        company_id=other_company.id,
        plan_name="外部方案",
        days=[(1, 0, other_shift.id)],
    )
    outsider_entry = create_roster_entry(
        db,
        company_id=other_company.id,
        employee_id=outsider.id,
        work_date=date(2026, 9, 15),
        state=RosterState.REST,
        source=RosterSource.MANUAL,
    )
    outsider_entry_id = outsider_entry.id

    applied = client.post(
        f"{ROSTER_URL}/sync",
        headers=superuser_token_headers,
        json={"company_id": str(org["company"].id), "month": MONTH},
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["entries_added"] == 0
    assert applied.json()["manual_preserved"] == 0

    db.expire_all()
    outsider_entries = list(
        db.exec(
            select(RosterEntry).where(RosterEntry.company_id == other_company.id)
        ).all()
    )
    assert [entry.id for entry in outsider_entries] == [outsider_entry_id]
    assert outsider_entries[0].source == RosterSource.MANUAL


def test_sync_preview_treats_partial_month_resignation_as_changed(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company = org["company"]
    employee = org["employee"]
    shift = org["shift"]
    create_schedule_plan(
        db,
        company_id=company.id,
        plan_name="张三行政班",
        scope_type=ScheduleScopeType.EMPLOYEE,
        scope_ids=[employee.id],
        days=[(1, 0, shift.id)],
    )
    for day in range(1, 31):
        create_roster_entry(
            db,
            company_id=company.id,
            employee_id=employee.id,
            work_date=date(2026, 9, day),
            state=RosterState.WORK if day == 1 else RosterState.REST,
            source=RosterSource.PLAN,
            shifts=[shift] if day == 1 else None,
        )
    employee = db.get(Employee, employee.id)
    assert employee is not None
    employee.resign_date = date(2026, 9, 15)
    employee.status = EmployeeStatus.RESIGNED
    db.add(employee)
    db.commit()

    preview = client.get(
        f"{ROSTER_URL}/sync-preview",
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "month": MONTH},
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["removed"] == 0
    assert body["changed"] == 1
    assert body["entries_deleted"] == 15
