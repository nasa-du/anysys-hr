"""Schedule-plan API contract tests.

Seam: ``/api/v1/attendance/schedule-plans``. The tests assert the contract from
``docs/specs/attendance-management.md`` sections 4.3, 5.1-5.5, 8.3.2, 8.4, 8.5,
and 14.3: CRUD, scope validation, same-precision conflicts, save-and-expand,
archive/unarchive/delete, next-month copy, and authentication.

Roster rows are asserted directly in the database because the roster query API
belongs to the next slice (A4); expansion has no other public read surface yet.
"""

import calendar
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
    PlanStatus,
    RosterSource,
    RosterState,
    ScheduleScopeType,
)
from app.models import (
    AttendanceMonth,
    PlanDay,
    PlanRuleOverride,
    PlanScope,
    RosterEntry,
    RosterEntryShift,
    SchedulePlan,
    Shift,
)
from tests.utils.attendance_factories import (
    create_attendance_month,
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

PLANS_URL = f"{settings.API_V1_STR}/attendance/schedule-plans/"
MONTH = "2026-09"
MONTH_START = date(2026, 9, 1)


def error_detail(response: Any) -> dict[str, Any]:
    body = response.json()
    assert isinstance(body["detail"], dict), body
    return body["detail"]


def plan_url(plan_id: uuid.UUID | str, suffix: str = "") -> str:
    return f"{PLANS_URL}{plan_id}{suffix}"


def month_entries(
    db: Session, company_id: uuid.UUID, month: date = MONTH_START
) -> list[RosterEntry]:
    db.expire_all()
    last_day = calendar.monthrange(month.year, month.month)[1]
    return list(
        db.exec(
            select(RosterEntry).where(
                RosterEntry.company_id == company_id,
                RosterEntry.work_date >= month,
                RosterEntry.work_date <= date(month.year, month.month, last_day),
            )
        ).all()
    )


def entry_for(
    db: Session, employee_id: uuid.UUID, work_date: date
) -> RosterEntry | None:
    db.expire_all()
    return db.exec(
        select(RosterEntry).where(
            RosterEntry.employee_id == employee_id,
            RosterEntry.work_date == work_date,
        )
    ).first()


def entry_shifts(db: Session, entry_id: uuid.UUID) -> list[RosterEntryShift]:
    db.expire_all()
    return list(
        db.exec(
            select(RosterEntryShift)
            .where(RosterEntryShift.roster_entry_id == entry_id)
            .order_by(RosterEntryShift.seq.asc())
        ).all()
    )


def payload(
    company_id: uuid.UUID,
    *,
    month: str = MONTH,
    plan_name: str = "行政班方案",
    scope_type: ScheduleScopeType = ScheduleScopeType.ALL,
    scope_ids: list[uuid.UUID] | None = None,
    days: list[tuple[int, int, uuid.UUID]] | None = None,
    rule_overrides: dict[str, Any] | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "company_id": str(company_id),
        "month": month,
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
    if rule_overrides is not None:
        body["rule_overrides"] = rule_overrides
    if note is not None:
        body["note"] = note
    return body


def _preview_body(body: dict[str, Any]) -> dict[str, Any]:
    body.pop("plan_name", None)
    return body


def create_plan(
    client: TestClient,
    headers: dict[str, str],
    body: dict[str, Any],
) -> dict[str, Any]:
    response = client.post(PLANS_URL, headers=headers, json=body)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def org(db: Session) -> dict[str, Any]:
    """One company with a department, position, an employee, and a shift."""
    company = create_company(db, company_code="C-PLAN")
    department = create_department(db, company=company, dept_code="D-PLAN")
    position = create_position(db, company=company, dept=department, position_code="P-PLAN")
    employee = create_employee(
        db,
        dept=department,
        position=position,
        employee_no="E-PLAN",
        hire_date=date(2026, 1, 1),
    )
    shift = create_shift(db, company_id=company.id, shift_code="ADM")
    return {
        "company": company,
        "department": department,
        "position": position,
        "employee": employee,
        "shift": shift,
    }


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


def test_all_plan_endpoints_require_authentication(client: TestClient) -> None:
    plan_id = uuid.uuid7()
    company_id = uuid.uuid7()
    no_auth_calls = [
        client.get(PLANS_URL, params={"company_id": company_id}),
        client.post(f"{PLANS_URL}preview", json={}),
        client.post(PLANS_URL, json={}),
        client.get(plan_url(plan_id)),
        client.patch(plan_url(plan_id), json={}),
        client.post(plan_url(plan_id, "/expand-preview")),
        client.post(plan_url(plan_id, "/expand")),
        client.post(plan_url(plan_id, "/archive")),
        client.post(plan_url(plan_id, "/unarchive")),
        client.delete(plan_url(plan_id)),
        client.post(plan_url(plan_id, "/copy-preview"), json={}),
        client.post(plan_url(plan_id, "/copy"), json={}),
        client.get(plan_url(plan_id, "/rule-overrides")),
        client.put(plan_url(plan_id, "/rule-overrides"), json={}),
    ]
    for response in no_auth_calls:
        assert response.status_code == 401, response.text


# ---------------------------------------------------------------------------
# Create / read / list / patch
# ---------------------------------------------------------------------------


def test_create_all_plan_saves_children_and_expands_month(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company, employee, shift = org["company"], org["employee"], org["shift"]

    body = create_plan(
        client,
        superuser_token_headers,
        payload(
            company.id,
            days=[(1, 0, shift.id)],
            rule_overrides={"late_grace_min": 12},
            note="九月行政班",
        ),
    )

    assert body["month"] == MONTH
    assert body["status"] == "enabled"
    assert body["scopes"] == []
    assert [day["day_of_month"] for day in body["days"]] == [1]
    assert body["days"][0]["shift_code"] == "ADM"
    assert body["copied_from_plan_id"] is None

    db.expire_all()
    plan = db.get(SchedulePlan, uuid.UUID(body["id"]))
    assert plan is not None
    assert plan.month == MONTH_START
    assert db.exec(select(PlanScope).where(PlanScope.plan_id == plan.id)).all() == []
    assert db.get(PlanRuleOverride, plan.id).late_grace_min == 12
    month = db.exec(
        select(AttendanceMonth).where(AttendanceMonth.company_id == company.id)
    ).one()
    assert month.month == MONTH_START
    assert month.status == AttendanceMonthStatus.DRAFT

    # The plan covers the whole month: day 1 is work, every other day is rest.
    work_entry = entry_for(db, employee.id, date(2026, 9, 1))
    assert work_entry is not None
    assert work_entry.state == RosterState.WORK
    assert work_entry.source == RosterSource.PLAN
    assert work_entry.plan_id == plan.id
    snapshots = entry_shifts(db, work_entry.id)
    assert [(snapshot.shift_id, snapshot.seq) for snapshot in snapshots] == [
        (shift.id, 0)
    ]
    assert snapshots[0].shift_code == "ADM"

    rest_entry = entry_for(db, employee.id, date(2026, 9, 2))
    assert rest_entry is not None
    assert rest_entry.state == RosterState.REST
    assert rest_entry.plan_id == plan.id
    assert entry_shifts(db, rest_entry.id) == []


def test_create_rejects_duplicate_plan_day_pairs(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company, shift = org["company"], org["shift"]
    for days in (
        [(1, 0, shift.id), (1, 0, shift.id)],
        [(1, 0, shift.id), (1, 1, shift.id)],
    ):
        response = client.post(
            PLANS_URL,
            headers=superuser_token_headers,
            json=payload(company.id, days=days),
        )
        assert response.status_code == 409, response.text
        assert error_detail(response)["code"] == "invalid_scope"

    db.expire_all()
    assert db.exec(select(SchedulePlan)).all() == []


def test_detail_and_list_return_days_and_scope_labels(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company, department, shift = org["company"], org["department"], org["shift"]
    other_shift = create_shift(db, company_id=company.id, shift_code="NIGHT")
    created = create_plan(
        client,
        superuser_token_headers,
        payload(
            company.id,
            plan_name="生产部方案",
            scope_type=ScheduleScopeType.DEPT,
            scope_ids=[department.id],
            days=[(2, 0, shift.id), (2, 1, other_shift.id)],
        ),
    )

    detail = client.get(plan_url(created["id"]), headers=superuser_token_headers)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["scopes"][0]["scope_id"] == str(department.id)
    assert body["scopes"][0]["scope_code"] == "D-PLAN"
    assert [day["shift_code"] for day in body["days"]] == ["ADM", "NIGHT"]
    assert [day["seq"] for day in body["days"]] == [0, 1]

    listed = client.get(
        PLANS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "month": MONTH},
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["count"] == 1
    assert listed.json()["data"][0]["days"] == body["days"]


def test_month_and_company_are_immutable_and_validated(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    org: dict[str, Any],
) -> None:
    company = org["company"]
    created = create_plan(client, superuser_token_headers, payload(company.id))

    for field, value in (
        ("month", "2026-10"),
        ("company_id", str(uuid.uuid7())),
    ):
        response = client.patch(
            plan_url(created["id"]),
            headers=superuser_token_headers,
            json={field: value},
        )
        assert response.status_code == 422, response.text
        assert response.json()["detail"][0]["msg"] == "该字段不可修改"

    bad_month = client.post(
        PLANS_URL,
        headers=superuser_token_headers,
        json={**payload(company.id), "month": "2026-9"},
    )
    assert bad_month.status_code == 422, bad_month.text


def test_patch_replaces_supplied_children_wholesale(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company, department, shift = org["company"], org["department"], org["shift"]
    position = org["position"]
    created = create_plan(
        client,
        superuser_token_headers,
        payload(
            company.id,
            scope_type=ScheduleScopeType.DEPT,
            scope_ids=[department.id],
            days=[(1, 0, shift.id), (2, 0, shift.id)],
            rule_overrides={"late_grace_min": 10},
        ),
    )

    renamed = client.patch(
        plan_url(created["id"]),
        headers=superuser_token_headers,
        json={"plan_name": "改名方案", "note": "备注"},
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["plan_name"] == "改名方案"
    assert renamed.json()["note"] == "备注"
    # Omitted children are unchanged.
    assert [day["day_of_month"] for day in renamed.json()["days"]] == [1, 2]
    assert renamed.json()["scopes"][0]["scope_id"] == str(department.id)

    replaced_days = client.patch(
        plan_url(created["id"]),
        headers=superuser_token_headers,
        json={"days": [{"day_of_month": 3, "seq": 0, "shift_id": str(shift.id)}]},
    )
    assert replaced_days.status_code == 200, replaced_days.text
    assert [day["day_of_month"] for day in replaced_days.json()["days"]] == [3]

    replaced_scope = client.patch(
        plan_url(created["id"]),
        headers=superuser_token_headers,
        json={
            "scope_type": "position",
            "scope_ids": [str(position.id)],
            "rule_overrides": {"early_grace_min": 7},
        },
    )
    assert replaced_scope.status_code == 200, replaced_scope.text
    assert replaced_scope.json()["scope_type"] == "position"
    assert replaced_scope.json()["scopes"][0]["scope_id"] == str(position.id)
    db.expire_all()
    override = db.get(PlanRuleOverride, uuid.UUID(created["id"]))
    assert override.late_grace_min is None
    assert override.early_grace_min == 7

    cleared = client.patch(
        plan_url(created["id"]),
        headers=superuser_token_headers,
        json={"rule_overrides": {}},
    )
    assert cleared.status_code == 200, cleared.text
    db.expire_all()
    assert db.get(PlanRuleOverride, uuid.UUID(created["id"])) is None

    beyond_month = client.patch(
        plan_url(created["id"]),
        headers=superuser_token_headers,
        json={"days": [{"day_of_month": 31, "seq": 0, "shift_id": str(shift.id)}]},
    )
    assert beyond_month.status_code == 409, beyond_month.text
    assert error_detail(beyond_month)["code"] == "invalid_scope"


def test_unknown_plan_returns_404(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    plan_id = uuid.uuid7()
    for response in (
        client.get(plan_url(plan_id), headers=superuser_token_headers),
        client.patch(plan_url(plan_id), headers=superuser_token_headers, json={}),
        client.post(plan_url(plan_id, "/expand"), headers=superuser_token_headers),
        client.post(plan_url(plan_id, "/archive"), headers=superuser_token_headers),
        client.post(plan_url(plan_id, "/unarchive"), headers=superuser_token_headers),
        client.delete(plan_url(plan_id), headers=superuser_token_headers),
    ):
        assert response.status_code == 404, response.text
        assert error_detail(response)["code"] == "not_found"


def test_unknown_company_returns_404(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(
        PLANS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(uuid.uuid7())},
    )
    assert response.status_code == 404
    created = client.post(
        PLANS_URL,
        headers=superuser_token_headers,
        json=payload(uuid.uuid7()),
    )
    assert created.status_code == 404
    assert error_detail(created)["code"] == "not_found"


# ---------------------------------------------------------------------------
# Scope validation
# ---------------------------------------------------------------------------


def test_all_scope_rejects_child_rows_and_typed_scopes_require_ids(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    org: dict[str, Any],
) -> None:
    company, department = org["company"], org["department"]
    cases = [
        payload(
            company.id,
            scope_type=ScheduleScopeType.ALL,
            scope_ids=[department.id],
        ),
        payload(
            company.id,
            scope_type=ScheduleScopeType.DEPT,
            scope_ids=[],
        ),
        payload(
            company.id,
            scope_type=ScheduleScopeType.EMPLOYEE,
            scope_ids=[],
        ),
    ]
    for body in cases:
        response = client.post(
            PLANS_URL, headers=superuser_token_headers, json=body
        )
        assert response.status_code == 409, response.text
        assert error_detail(response)["code"] == "invalid_scope"


def test_scope_type_mismatch_is_rejected(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    org: dict[str, Any],
) -> None:
    company, employee = org["company"], org["employee"]
    response = client.post(
        PLANS_URL,
        headers=superuser_token_headers,
        json=payload(
            company.id,
            scope_type=ScheduleScopeType.DEPT,
            scope_ids=[employee.id],
        ),
    )
    assert response.status_code == 409, response.text
    assert error_detail(response)["code"] == "invalid_scope"

    missing = client.post(
        PLANS_URL,
        headers=superuser_token_headers,
        json=payload(
            company.id,
            scope_type=ScheduleScopeType.DEPT,
            scope_ids=[uuid.uuid7()],
        ),
    )
    assert missing.status_code == 409, missing.text
    assert error_detail(missing)["code"] == "invalid_reference"


def test_inactive_and_cross_company_scope_targets_are_rejected(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company = org["company"]
    inactive_department = create_department(
        db, company=company, is_active=False
    )
    inactive_position = create_position(
        db, company=company, dept=org["department"], is_active=False
    )
    other_company = create_company(db, company_code="C-OTHER")
    other_department = create_department(db, company=other_company)
    other_shift = create_shift(db, company_id=other_company.id, shift_code="X")
    foreign_employee = create_employee(
        db,
        dept=other_department,
        position=create_position(db, company=other_company, dept=other_department),
        hire_date=date(2026, 1, 1),
    )

    cases = [
        (
            payload(
                company.id,
                scope_type=ScheduleScopeType.DEPT,
                scope_ids=[inactive_department.id],
            ),
            "inactive_reference",
        ),
        (
            payload(
                company.id,
                scope_type=ScheduleScopeType.POSITION,
                scope_ids=[inactive_position.id],
            ),
            "inactive_reference",
        ),
        (
            payload(
                company.id,
                scope_type=ScheduleScopeType.DEPT,
                scope_ids=[other_department.id],
            ),
            "cross_company",
        ),
        (
            payload(
                company.id,
                scope_type=ScheduleScopeType.EMPLOYEE,
                scope_ids=[foreign_employee.id],
            ),
            "cross_company",
        ),
        (
            payload(
                company.id,
                days=[(1, 0, other_shift.id)],
            ),
            "cross_company",
        ),
        (
            payload(
                company.id,
                days=[(1, 0, uuid.uuid7())],
            ),
            "invalid_reference",
        ),
    ]
    for body, code in cases:
        response = client.post(
            PLANS_URL, headers=superuser_token_headers, json=body
        )
        assert response.status_code == 409, (code, response.text)
        assert error_detail(response)["code"] == code


def test_inactive_shift_is_rejected_when_saving(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company = org["company"]
    inactive_shift = create_shift(
        db, company_id=company.id, shift_code="OFF", is_active=False
    )
    response = client.post(
        PLANS_URL,
        headers=superuser_token_headers,
        json=payload(company.id, days=[(1, 0, inactive_shift.id)]),
    )
    assert response.status_code == 409, response.text
    assert error_detail(response)["code"] == "inactive_reference"


def test_employee_scope_outside_employment_range_is_rejected(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company, department, position = (
        org["company"],
        org["department"],
        org["position"],
    )
    future_employee = create_employee(
        db,
        dept=department,
        position=position,
        hire_date=date(2026, 10, 1),
    )
    resigned_employee = create_employee(
        db,
        dept=department,
        position=position,
        status=EmployeeStatus.RESIGNED,
        hire_date=date(2025, 1, 1),
        resign_date=date(2026, 8, 31),
    )
    for employee in (future_employee, resigned_employee):
        response = client.post(
            PLANS_URL,
            headers=superuser_token_headers,
            json=payload(
                company.id,
                scope_type=ScheduleScopeType.EMPLOYEE,
                scope_ids=[employee.id],
            ),
        )
        assert response.status_code == 409, response.text
        assert error_detail(response)["code"] == "employee_out_of_range"

    # An employee who overlaps the month, even partially, is valid.
    partial = create_employee(
        db,
        dept=department,
        position=position,
        hire_date=date(2026, 9, 15),
    )
    accepted = client.post(
        PLANS_URL,
        headers=superuser_token_headers,
        json=payload(
            company.id,
            scope_type=ScheduleScopeType.EMPLOYEE,
            scope_ids=[partial.id],
        ),
    )
    assert accepted.status_code == 201, accepted.text


# ---------------------------------------------------------------------------
# Same-precision conflicts
# ---------------------------------------------------------------------------


def test_same_precision_scope_conflicts_return_409(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company, department = org["company"], org["department"]
    create_plan(
        client,
        superuser_token_headers,
        payload(
            company.id,
            plan_name="部门方案 A",
            scope_type=ScheduleScopeType.DEPT,
            scope_ids=[department.id],
        ),
    )
    conflict = client.post(
        PLANS_URL,
        headers=superuser_token_headers,
        json=payload(
            company.id,
            plan_name="部门方案 B",
            scope_type=ScheduleScopeType.DEPT,
            scope_ids=[department.id],
        ),
    )
    assert conflict.status_code == 409, conflict.text
    detail = error_detail(conflict)
    assert detail["code"] == "schedule_conflict"
    assert "部门方案 A" in detail["message"]

    # A different precision may coexist.
    all_plan = client.post(
        PLANS_URL,
        headers=superuser_token_headers,
        json=payload(company.id, plan_name="全公司方案"),
    )
    assert all_plan.status_code == 201, all_plan.text

    all_conflict = client.post(
        PLANS_URL,
        headers=superuser_token_headers,
        json=payload(company.id, plan_name="全公司方案 B"),
    )
    assert all_conflict.status_code == 409, all_conflict.text
    assert error_detail(all_conflict)["code"] == "schedule_conflict"

    # A second department without overlap is allowed.
    second_department = create_department(db, company=company, dept_code="D-2")
    allowed = client.post(
        PLANS_URL,
        headers=superuser_token_headers,
        json=payload(
            company.id,
            plan_name="部门方案 C",
            scope_type=ScheduleScopeType.DEPT,
            scope_ids=[second_department.id],
        ),
    )
    assert allowed.status_code == 201, allowed.text

    # Archived plans do not occupy a scope.
    archived = db.get(SchedulePlan, uuid.UUID(all_plan.json()["id"]))
    archived.status = PlanStatus.ARCHIVED
    db.add(archived)
    db.commit()
    replacement = client.post(
        PLANS_URL,
        headers=superuser_token_headers,
        json=payload(company.id, plan_name="替代全公司方案"),
    )
    assert replacement.status_code == 201, replacement.text


def test_plan_preview_reports_conflicts_and_impact_without_writing(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company, department, employee, shift = (
        org["company"],
        org["department"],
        org["employee"],
        org["shift"],
    )
    existing = create_plan(
        client,
        superuser_token_headers,
        payload(
            company.id,
            plan_name="部门方案 A",
            scope_type=ScheduleScopeType.DEPT,
            scope_ids=[department.id],
            days=[(1, 0, shift.id)],
        ),
    )

    preview = client.post(
        f"{PLANS_URL}preview",
        headers=superuser_token_headers,
        json=_preview_body(
            payload(
                company.id,
                scope_type=ScheduleScopeType.DEPT,
                scope_ids=[department.id],
                days=[(2, 0, shift.id)],
            )
        ),
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["can_apply"] is False
    assert body["conflicts"] == [
        {
            "scope_type": "dept",
            "scope_id": str(department.id),
            "plan_id": existing["id"],
            "plan_name": "部门方案 A",
        }
    ]
    db.expire_all()
    assert len(db.exec(select(SchedulePlan)).all()) == 1
    assert len(month_entries(db, company.id)) == 30

    # A position plan does not conflict and would win for its employee.
    preview_ok = client.post(
        f"{PLANS_URL}preview",
        headers=superuser_token_headers,
        json=_preview_body(
            payload(
                company.id,
                scope_type=ScheduleScopeType.POSITION,
                scope_ids=[org["position"].id],
                days=[(2, 0, shift.id)],
            )
        ),
    )
    assert preview_ok.status_code == 200, preview_ok.text
    ok_body = preview_ok.json()
    assert ok_body["can_apply"] is True
    assert ok_body["conflicts"] == []
    assert ok_body["affected_employees"] == 1
    assert ok_body["added"] == 0
    assert ok_body["updated"] == 30
    assert ok_body["manual_preserved"] == 0
    db.expire_all()
    assert len(month_entries(db, company.id)) == 30
    assert entry_for(db, employee.id, date(2026, 9, 2)).plan_id == uuid.UUID(
        existing["id"]
    )


def test_plan_preview_for_an_edit_excludes_the_plan_itself(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    org: dict[str, Any],
) -> None:
    company, department, shift = org["company"], org["department"], org["shift"]
    created = create_plan(
        client,
        superuser_token_headers,
        payload(
            company.id,
            scope_type=ScheduleScopeType.DEPT,
            scope_ids=[department.id],
            days=[(1, 0, shift.id)],
        ),
    )
    body = _preview_body(
        payload(
            company.id,
            scope_type=ScheduleScopeType.DEPT,
            scope_ids=[department.id],
            days=[(2, 0, shift.id)],
        )
    )
    without_plan_id = client.post(
        f"{PLANS_URL}preview", headers=superuser_token_headers, json=body
    )
    assert without_plan_id.status_code == 200, without_plan_id.text
    assert without_plan_id.json()["can_apply"] is False

    with_plan_id = client.post(
        f"{PLANS_URL}preview",
        headers=superuser_token_headers,
        json={**body, "plan_id": created["id"]},
    )
    assert with_plan_id.status_code == 200, with_plan_id.text
    assert with_plan_id.json()["can_apply"] is True
    assert with_plan_id.json()["conflicts"] == []


def test_preview_with_a_foreign_plan_id_is_rejected(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    org: dict[str, Any],
) -> None:
    company, shift = org["company"], org["shift"]
    created = create_plan(
        client,
        superuser_token_headers,
        payload(company.id, days=[(1, 0, shift.id)]),
    )
    body = _preview_body(
        payload(
            company.id,
            month="2026-10",
            days=[(1, 0, shift.id)],
        )
    )
    response = client.post(
        f"{PLANS_URL}preview",
        headers=superuser_token_headers,
        json={**body, "plan_id": created["id"]},
    )
    assert response.status_code == 409, response.text
    assert error_detail(response)["code"] == "invalid_reference"


def test_preview_with_a_cross_company_or_archived_plan_id_is_rejected(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company, shift = org["company"], org["shift"]
    other_company = create_company(db, company_code="C-PREVIEW-2")
    other_plan = create_schedule_plan(db, company_id=other_company.id)
    body = _preview_body(payload(company.id, days=[(1, 0, shift.id)]))

    cross = client.post(
        f"{PLANS_URL}preview",
        headers=superuser_token_headers,
        json={**body, "plan_id": str(other_plan.id)},
    )
    assert cross.status_code == 409, cross.text
    assert error_detail(cross)["code"] == "cross_company"

    archived = create_schedule_plan(
        db, company_id=company.id, status=PlanStatus.ARCHIVED
    )
    archived_response = client.post(
        f"{PLANS_URL}preview",
        headers=superuser_token_headers,
        json={**body, "plan_id": str(archived.id)},
    )
    assert archived_response.status_code == 409, archived_response.text
    assert error_detail(archived_response)["code"] == "plan_archived"


def test_duplicate_scope_ids_are_rejected(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    org: dict[str, Any],
) -> None:
    company, department = org["company"], org["department"]
    response = client.post(
        PLANS_URL,
        headers=superuser_token_headers,
        json=payload(
            company.id,
            scope_type=ScheduleScopeType.DEPT,
            scope_ids=[department.id, department.id],
        ),
    )
    assert response.status_code == 409, response.text
    assert error_detail(response)["code"] == "invalid_scope"


def test_changing_scope_type_without_scope_ids_rejects_old_scopes(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    org: dict[str, Any],
) -> None:
    company, department = org["company"], org["department"]
    created = create_plan(
        client,
        superuser_token_headers,
        payload(
            company.id,
            scope_type=ScheduleScopeType.DEPT,
            scope_ids=[department.id],
        ),
    )
    response = client.patch(
        plan_url(created["id"]),
        headers=superuser_token_headers,
        json={"scope_type": "all"},
    )
    assert response.status_code == 409, response.text
    assert error_detail(response)["code"] == "invalid_scope"


def test_preview_reports_time_overlap_warnings(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company = org["company"]
    early = create_shift(
        db, company_id=company.id, shift_code="EARLY", end_time=time(14, 0)
    )
    late = create_shift(
        db,
        company_id=company.id,
        shift_code="LATE",
        start_time=time(13, 0),
        end_time=time(21, 0),
    )
    response = client.post(
        f"{PLANS_URL}preview",
        headers=superuser_token_headers,
        json=_preview_body(
            payload(
                company.id,
                days=[(1, 0, early.id), (1, 1, late.id)],
            )
        ),
    )
    assert response.status_code == 200, response.text
    warnings = response.json()["warnings"]
    assert any("时间重叠" in warning for warning in warnings)


# ---------------------------------------------------------------------------
# Lifecycle: expand, archive, unarchive, delete
# ---------------------------------------------------------------------------


def test_expand_preview_and_expand_apply(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company, employee, shift = org["company"], org["employee"], org["shift"]
    created = create_plan(
        client,
        superuser_token_headers,
        payload(company.id, days=[(1, 0, shift.id)]),
    )

    # Shift times change after the plan was expanded; snapshots stay old.
    db.expire_all()
    shift_row = db.get(Shift, shift.id)
    shift_row.start_time = time(9, 0)
    shift_row.end_time = time(18, 0)
    db.add(shift_row)
    db.commit()

    stale_snapshot = entry_shifts(
        db, entry_for(db, employee.id, date(2026, 9, 1)).id
    )[0]
    assert stale_snapshot.start_time.hour == 8

    preview = client.post(
        plan_url(created["id"], "/expand-preview"),
        headers=superuser_token_headers,
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["updated"] == 1
    assert preview.json()["can_apply"] is True

    applied = client.post(
        plan_url(created["id"], "/expand"),
        headers=superuser_token_headers,
    )
    assert applied.status_code == 200, applied.text
    body = applied.json()
    assert body["roster_change"]["updated"] == 1
    assert body["month_stale"] is True
    refreshed = entry_shifts(
        db, entry_for(db, employee.id, date(2026, 9, 1)).id
    )[0]
    assert refreshed.start_time.hour == 9


def test_archive_removes_plan_entries_and_preserves_manual_exceptions(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company, employee, shift = org["company"], org["employee"], org["shift"]
    manual = create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 2),
        state=RosterState.WORK,
        source=RosterSource.MANUAL,
        shifts=[shift],
    )
    created = create_plan(
        client,
        superuser_token_headers,
        payload(company.id, days=[(1, 0, shift.id)]),
    )

    archived = client.post(
        plan_url(created["id"], "/archive"),
        headers=superuser_token_headers,
    )
    assert archived.status_code == 200, archived.text
    assert archived.json()["plan"]["status"] == "archived"
    assert archived.json()["roster_change"]["deleted"] >= 1

    db.expire_all()
    assert entry_for(db, employee.id, date(2026, 9, 1)) is None
    still_there = entry_for(db, employee.id, date(2026, 9, 2))
    assert still_there.id == manual.id
    assert still_there.source == RosterSource.MANUAL


def test_unarchive_requires_active_shifts_and_rechecks_conflicts(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company, department, shift = org["company"], org["department"], org["shift"]
    created = create_plan(
        client,
        superuser_token_headers,
        payload(
            company.id,
            scope_type=ScheduleScopeType.DEPT,
            scope_ids=[department.id],
            days=[(1, 0, shift.id)],
        ),
    )
    client.post(plan_url(created["id"], "/archive"), headers=superuser_token_headers)

    db.expire_all()
    shift_row = db.get(Shift, shift.id)
    shift_row.is_active = False
    db.add(shift_row)
    db.commit()

    blocked = client.post(
        plan_url(created["id"], "/unarchive"),
        headers=superuser_token_headers,
    )
    assert blocked.status_code == 409, blocked.text
    detail = error_detail(blocked)
    assert detail["code"] == "activation_blocked"
    assert detail["blocker_count"] == 1
    assert detail["blockers"][0]["code"] == "ADM"

    shift_row.is_active = True
    db.add(shift_row)
    db.commit()

    # Another plan takes the scope while the first is archived.
    duplicate = create_plan(
        client,
        superuser_token_headers,
        payload(
            company.id,
            plan_name="部门方案 2",
            scope_type=ScheduleScopeType.DEPT,
            scope_ids=[department.id],
        ),
    )
    conflict = client.post(
        plan_url(created["id"], "/unarchive"),
        headers=superuser_token_headers,
    )
    assert conflict.status_code == 409, conflict.text
    assert error_detail(conflict)["code"] == "schedule_conflict"

    client.post(plan_url(duplicate["id"], "/archive"), headers=superuser_token_headers)
    reactivated = client.post(
        plan_url(created["id"], "/unarchive"),
        headers=superuser_token_headers,
    )
    assert reactivated.status_code == 200, reactivated.text
    assert reactivated.json()["plan"]["status"] == "enabled"
    assert reactivated.json()["roster_change"]["added"] > 0


def test_delete_is_blocked_by_roster_references(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company, shift = org["company"], org["shift"]
    created = create_plan(
        client,
        superuser_token_headers,
        payload(company.id, days=[(1, 0, shift.id)]),
    )

    blocked = client.delete(
        plan_url(created["id"]), headers=superuser_token_headers
    )
    assert blocked.status_code == 409, blocked.text
    detail = error_detail(blocked)
    assert detail["code"] == "referenced"
    assert detail["blocker_count"] == 30
    assert detail["blockers"][0]["type"] == "roster_entry"
    assert detail["blockers"][0]["code"] == "E-PLAN"

    # Archive re-expands the month, so the plan no longer owns entries.
    client.post(plan_url(created["id"], "/archive"), headers=superuser_token_headers)
    deleted = client.delete(
        plan_url(created["id"]), headers=superuser_token_headers
    )
    assert deleted.status_code == 200, deleted.text
    db.expire_all()
    assert db.get(SchedulePlan, uuid.UUID(created["id"])) is None
    assert db.exec(select(PlanDay)).all() == []


def test_unreferenced_plan_can_be_deleted(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company = org["company"]
    plan = create_schedule_plan(db, company_id=company.id)
    plan_id = plan.id
    response = client.delete(plan_url(plan_id), headers=superuser_token_headers)
    assert response.status_code == 200, response.text
    db.expire_all()
    assert db.get(SchedulePlan, plan_id) is None


# ---------------------------------------------------------------------------
# Copy to next month
# ---------------------------------------------------------------------------


def test_copy_next_month_maps_days_and_reports_big_small_month(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company, employee, shift = org["company"], org["employee"], org["shift"]
    created = create_plan(
        client,
        superuser_token_headers,
        payload(
            company.id,
            month="2026-01",
            plan_name="2026-01 行政班",
            days=[(1, 0, shift.id), (30, 0, shift.id), (31, 0, shift.id)],
            rule_overrides={"late_grace_min": 15},
        ),
    )
    copy_request = {
        "target_month": "2026-02",
        "include_manual_exceptions": False,
        "confirm_overwrite": False,
    }
    preview = client.post(
        plan_url(created["id"], "/copy-preview"),
        headers=superuser_token_headers,
        json=copy_request,
    )
    assert preview.status_code == 200, preview.text
    preview_body = preview.json()
    assert preview_body["target_month"] == "2026-02"
    assert preview_body["can_apply"] is True
    assert any("少 3 天" in warning for warning in preview_body["warnings"])

    copied = client.post(
        plan_url(created["id"], "/copy"),
        headers=superuser_token_headers,
        json=copy_request,
    )
    assert copied.status_code == 201, copied.text
    body = copied.json()
    assert body["month"] == "2026-02"
    assert body["copied_from_plan_id"] == created["id"]
    # The spec copies the plan definition; it defines no rename rule.
    assert body["plan_name"] == "2026-01 行政班"
    assert [(day["day_of_month"], day["seq"]) for day in body["days"]] == [
        (1, 0)
    ]
    db.expire_all()
    new_override = db.get(PlanRuleOverride, uuid.UUID(body["id"]))
    assert new_override.late_grace_min == 15
    assert entry_for(db, employee.id, date(2026, 2, 1)).state == RosterState.WORK
    assert entry_for(db, employee.id, date(2026, 2, 2)).state == RosterState.REST


def test_copy_to_bigger_month_keeps_source_days_and_warns(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    org: dict[str, Any],
) -> None:
    company, shift = org["company"], org["shift"]
    source = create_plan(
        client,
        superuser_token_headers,
        payload(
            company.id,
            month="2026-09",
            plan_name="九月方案",
            days=[(30, 0, shift.id)],
        ),
    )
    preview = client.post(
        plan_url(source["id"], "/copy-preview"),
        headers=superuser_token_headers,
        json={"target_month": "2026-10"},
    )
    assert preview.status_code == 200, preview.text
    assert any("多 1 天" in warning for warning in preview.json()["warnings"])

    copied = client.post(
        plan_url(source["id"], "/copy"),
        headers=superuser_token_headers,
        json={"target_month": "2026-10"},
    )
    assert copied.status_code == 201, copied.text
    assert [(day["day_of_month"], day["seq"]) for day in copied.json()["days"]] == [
        (30, 0)
    ]


def test_copy_rejects_non_next_month_and_same_scope_conflicts(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    org: dict[str, Any],
) -> None:
    company, department = org["company"], org["department"]
    created = create_plan(
        client,
        superuser_token_headers,
        payload(
            company.id,
            scope_type=ScheduleScopeType.DEPT,
            scope_ids=[department.id],
        ),
    )
    for target in ("2026-09", "2026-11"):
        response = client.post(
            plan_url(created["id"], "/copy"),
            headers=superuser_token_headers,
            json={"target_month": target},
        )
        assert response.status_code == 409, response.text
        assert error_detail(response)["code"] == "invalid_scope"

    create_plan(
        client,
        superuser_token_headers,
        payload(
            company.id,
            month="2026-10",
            plan_name="十月部门方案",
            scope_type=ScheduleScopeType.DEPT,
            scope_ids=[department.id],
        ),
    )
    conflict = client.post(
        plan_url(created["id"], "/copy"),
        headers=superuser_token_headers,
        json={"target_month": "2026-10"},
    )
    assert conflict.status_code == 409, conflict.text
    detail = error_detail(conflict)
    assert detail["code"] == "schedule_conflict"
    assert "十月部门方案" in detail["message"]

    preview = client.post(
        plan_url(created["id"], "/copy-preview"),
        headers=superuser_token_headers,
        json={"target_month": "2026-10"},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["can_apply"] is False
    assert preview.json()["conflicts"][0]["plan_name"] == "十月部门方案"


def test_copy_can_include_manual_exceptions_for_existing_target_dates(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company, employee, shift = org["company"], org["employee"], org["shift"]
    manual = create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=date(2026, 1, 20),
        state=RosterState.WORK,
        source=RosterSource.MANUAL,
        shifts=[shift],
    )
    source = create_plan(
        client,
        superuser_token_headers,
        payload(
            company.id,
            month="2026-01",
            plan_name="一月方案",
            days=[(1, 0, shift.id)],
        ),
    )
    # The source expansion preserved the manual exception.
    db.expire_all()
    assert entry_for(db, employee.id, date(2026, 1, 20)).source == RosterSource.MANUAL

    copied = client.post(
        plan_url(source["id"], "/copy"),
        headers=superuser_token_headers,
        json={
            "target_month": "2026-02",
            "include_manual_exceptions": True,
        },
    )
    assert copied.status_code == 201, copied.text

    db.expire_all()
    copied_manual = entry_for(db, employee.id, date(2026, 2, 20))
    assert copied_manual is not None
    assert copied_manual.source == RosterSource.MANUAL
    assert copied_manual.state == RosterState.WORK
    # The copied plan covers the day, so the manual exception records which
    # plan it overrides (spec section 5.3).
    assert copied_manual.plan_id == uuid.UUID(copied.json()["id"])
    assert [snapshot.shift_id for snapshot in entry_shifts(db, copied_manual.id)] == [
        shift.id
    ]
    assert entry_for(db, employee.id, date(2026, 1, 20)).id == manual.id


def test_copy_skips_manual_exceptions_on_dates_the_target_month_lacks(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company, employee, shift = org["company"], org["employee"], org["shift"]
    create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=date(2026, 1, 31),
        state=RosterState.WORK,
        source=RosterSource.MANUAL,
        shifts=[shift],
    )
    source = create_plan(
        client,
        superuser_token_headers,
        payload(company.id, month="2026-01", plan_name="一月方案"),
    )
    preview = client.post(
        plan_url(source["id"], "/copy-preview"),
        headers=superuser_token_headers,
        json={"target_month": "2026-02", "include_manual_exceptions": True},
    )
    assert preview.status_code == 200, preview.text
    assert any("跳过" in warning for warning in preview.json()["warnings"])

    copied = client.post(
        plan_url(source["id"], "/copy"),
        headers=superuser_token_headers,
        json={"target_month": "2026-02", "include_manual_exceptions": True},
    )
    assert copied.status_code == 201, copied.text
    db.expire_all()
    # February has no 31st; the source exception is skipped, not copied.
    assert entry_for(db, employee.id, date(2026, 2, 28)).source == RosterSource.PLAN
    assert (
        db.exec(
            select(RosterEntry).where(
                RosterEntry.employee_id == employee.id,
                RosterEntry.source == RosterSource.MANUAL,
                RosterEntry.work_date >= date(2026, 2, 1),
            )
        ).all()
        == []
    )


def test_copy_requires_overwrite_confirmation_for_existing_plan_entries(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company, department, employee, shift = (
        org["company"],
        org["department"],
        org["employee"],
        org["shift"],
    )
    source = create_plan(
        client,
        superuser_token_headers,
        payload(
            company.id,
            plan_name="九月部门方案",
            scope_type=ScheduleScopeType.DEPT,
            scope_ids=[department.id],
            days=[(1, 0, shift.id)],
        ),
    )
    # An all-company plan in the target month currently owns the employee's
    # days; the copied department plan outranks it and would overwrite them.
    create_plan(
        client,
        superuser_token_headers,
        payload(
            company.id,
            month="2026-10",
            plan_name="十月全公司方案",
        ),
    )

    blocked = client.post(
        plan_url(source["id"], "/copy"),
        headers=superuser_token_headers,
        json={"target_month": "2026-10", "confirm_overwrite": False},
    )
    assert blocked.status_code == 409, blocked.text
    assert "确认覆盖" in error_detail(blocked)["message"]

    preview = client.post(
        plan_url(source["id"], "/copy-preview"),
        headers=superuser_token_headers,
        json={"target_month": "2026-10", "confirm_overwrite": False},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["updated"] > 0
    assert any("确认覆盖" in warning for warning in preview.json()["warnings"])

    copied = client.post(
        plan_url(source["id"], "/copy"),
        headers=superuser_token_headers,
        json={"target_month": "2026-10", "confirm_overwrite": True},
    )
    assert copied.status_code == 201, copied.text
    db.expire_all()
    target_entry = entry_for(db, employee.id, date(2026, 10, 1))
    assert target_entry.plan_id == uuid.UUID(copied.json()["id"])


def test_copy_blocked_in_confirmed_or_locked_target_month(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company = org["company"]
    source = create_plan(client, superuser_token_headers, payload(company.id))
    for status in (
        AttendanceMonthStatus.CONFIRMED,
        AttendanceMonthStatus.LOCKED,
    ):
        create_attendance_month(
            db,
            company_id=company.id,
            month=date(2026, 10, 1),
            status=status,
        )
        response = client.post(
            plan_url(source["id"], "/copy"),
            headers=superuser_token_headers,
            json={"target_month": "2026-10"},
        )
        assert response.status_code == 409, response.text
        assert error_detail(response)["code"] == "schedule_expansion_blocked"
        db.expire_all()
        db.exec(select(AttendanceMonth).where(AttendanceMonth.month == date(2026, 10, 1))).one()
        db.delete(db.exec(select(AttendanceMonth).where(AttendanceMonth.month == date(2026, 10, 1))).one())
        db.commit()


# ---------------------------------------------------------------------------
# Month state and stale marking
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (AttendanceMonthStatus.CONFIRMED, "month_confirmed"),
        (AttendanceMonthStatus.LOCKED, "month_locked"),
    ],
)
def test_plan_writes_are_blocked_in_confirmed_or_locked_months(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
    status: AttendanceMonthStatus,
    code: str,
) -> None:
    company, shift = org["company"], org["shift"]
    create_attendance_month(db, company_id=company.id, status=status)
    response = client.post(
        PLANS_URL,
        headers=superuser_token_headers,
        json=payload(company.id, days=[(1, 0, shift.id)]),
    )
    assert response.status_code == 409, response.text
    assert error_detail(response)["code"] == code
    db.expire_all()
    assert db.exec(select(SchedulePlan)).all() == []


@pytest.mark.parametrize(
    "status",
    [AttendanceMonthStatus.CONFIRMED, AttendanceMonthStatus.LOCKED],
)
def test_expand_blocked_in_confirmed_or_locked_months(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
    status: AttendanceMonthStatus,
) -> None:
    company = org["company"]
    plan = create_schedule_plan(db, company_id=company.id)
    create_attendance_month(db, company_id=company.id, status=status)
    for response in (
        client.post(plan_url(plan.id, "/expand"), headers=superuser_token_headers),
        client.post(
            plan_url(plan.id, "/expand-preview"), headers=superuser_token_headers
        ),
    ):
        assert response.status_code == 409, response.text
        assert error_detail(response)["code"] == "schedule_expansion_blocked"


@pytest.mark.parametrize(
    "status",
    [AttendanceMonthStatus.CONFIRMED, AttendanceMonthStatus.LOCKED],
)
def test_copy_from_a_closed_source_month_is_allowed(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
    status: AttendanceMonthStatus,
) -> None:
    """Only the target month must be editable; planning next month is normal."""
    company = org["company"]
    plan = create_schedule_plan(db, company_id=company.id)
    create_attendance_month(db, company_id=company.id, status=status)
    response = client.post(
        plan_url(plan.id, "/copy"),
        headers=superuser_token_headers,
        json={"target_month": "2026-10"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["month"] == "2026-10"


def test_plan_save_marks_a_calculated_month_stale(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company, shift = org["company"], org["shift"]
    month = create_attendance_month(
        db,
        company_id=company.id,
        status=AttendanceMonthStatus.CALCULATED,
        is_stale=False,
    )
    create_plan(
        client,
        superuser_token_headers,
        payload(company.id, days=[(1, 0, shift.id)]),
    )
    db.refresh(month)
    assert month.is_stale is True


def test_plan_rule_override_patch_marks_calculated_month_stale(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company = org["company"]
    plan = create_schedule_plan(db, company_id=company.id)
    month = create_attendance_month(
        db,
        company_id=company.id,
        status=AttendanceMonthStatus.CALCULATED,
        is_stale=False,
    )
    response = client.patch(
        plan_url(plan.id),
        headers=superuser_token_headers,
        json={"rule_overrides": {"late_grace_min": 9}},
    )
    assert response.status_code == 200, response.text
    db.refresh(month)
    assert month.is_stale is True
    db.expire_all()
    assert db.get(PlanRuleOverride, plan.id).late_grace_min == 9


def test_archived_plan_cannot_be_edited_or_expanded(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company = org["company"]
    plan = create_schedule_plan(
        db, company_id=company.id, status=PlanStatus.ARCHIVED
    )
    for response in (
        client.patch(plan_url(plan.id), headers=superuser_token_headers, json={"plan_name": "x"}),
        client.post(plan_url(plan.id, "/expand"), headers=superuser_token_headers),
        client.post(plan_url(plan.id, "/expand-preview"), headers=superuser_token_headers),
    ):
        assert response.status_code == 409, response.text
        assert error_detail(response)["code"] == "plan_archived"


# ---------------------------------------------------------------------------
# Company isolation
# ---------------------------------------------------------------------------


def test_plans_and_expansion_never_cross_companies(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    org: dict[str, Any],
) -> None:
    company, department = org["company"], org["department"]
    other_company = create_company(db, company_code="C-PLAN-2")
    other_department = create_department(db, company=other_company, dept_code="D-X")
    other_position = create_position(
        db, company=other_company, dept=other_department
    )
    other_employee = create_employee(
        db,
        dept=other_department,
        position=other_position,
        employee_no="E-OTHER",
        hire_date=date(2026, 1, 1),
    )
    create_plan(
        client,
        superuser_token_headers,
        payload(
            company.id,
            scope_type=ScheduleScopeType.DEPT,
            scope_ids=[department.id],
        ),
    )

    listed = client.get(
        PLANS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(other_company.id)},
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["count"] == 0
    db.expire_all()
    assert month_entries(db, other_company.id) == []
    assert entry_for(db, other_employee.id, date(2026, 9, 1)) is None
    assert entry_for(db, org["employee"].id, date(2026, 9, 1)) is not None
