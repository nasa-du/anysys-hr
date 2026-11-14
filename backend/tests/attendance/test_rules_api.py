"""Company rule and plan rule-override API contract tests.

Seam: ``/api/v1/attendance/rules`` and
``/api/v1/attendance/schedule-plans/{plan_id}/rule-overrides``. The tests
assert the contract from ``docs/specs/attendance-management.md`` sections
4.6, 8.3.7, 8.4, 8.5, and 9.2: read-only defaults, first-write PUT,
idempotency, validation, override inheritance, wholesale replacement, and
stale marking that never touches confirmed or locked months.
"""

import uuid
from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.enums import AttendanceMonthStatus, PlanStatus, ScheduleScopeType
from app.models import AttendanceRule, PlanRuleOverride
from tests.utils.attendance_factories import (
    create_attendance_month,
    create_attendance_rule,
    create_schedule_plan,
)
from tests.utils.factories import create_company, create_department

RULES_URL = f"{settings.API_V1_STR}/attendance/rules/"
PLANS_URL = f"{settings.API_V1_STR}/attendance/schedule-plans/"

DEFAULT_DEDUCTIONS = {
    "absent_deduct_per_day": "0.00",
    "late_deduct_per_occurrence": "0.00",
    "early_deduct_per_occurrence": "0.00",
    "missing_punch_deduct_per_occurrence": "0.00",
}

DEFAULT_RULE_BODY: dict[str, Any] = {
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
    **DEFAULT_DEDUCTIONS,
}

RULE_FIELDS = tuple(DEFAULT_RULE_BODY)


def error_detail(response: Any) -> dict[str, Any]:
    body = response.json()
    assert isinstance(body["detail"], dict), body
    return body["detail"]


def plan_overrides_url(plan_id: uuid.UUID | str) -> str:
    return f"{PLANS_URL}{plan_id}/rule-overrides"


def get_rule(
    client: TestClient, headers: dict[str, str], company_id: uuid.UUID | str
) -> dict[str, Any]:
    response = client.get(
        RULES_URL, headers=headers, params={"company_id": str(company_id)}
    )
    assert response.status_code == 200, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Company default rules
# ---------------------------------------------------------------------------


def test_rule_endpoints_require_authentication(client: TestClient) -> None:
    company_id = uuid.uuid7()
    for method, kwargs in (
        ("get", {}),
        ("put", {"json": {}}),
    ):
        response = getattr(client, method)(
            RULES_URL,
            params={"company_id": str(company_id)},
            **kwargs,
        )
        assert response.status_code == 401, (method, response.text)
        assert response.json() == {"detail": "未登录或登录状态已过期"}


def test_get_returns_documented_defaults_without_writing(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)

    body = get_rule(client, superuser_token_headers, company.id)

    assert body["id"] is None
    assert body["is_default"] is True
    assert body["company_id"] == str(company.id)
    assert body["created_at"] is None
    assert body["updated_at"] is None
    assert {field: body[field] for field in RULE_FIELDS} == DEFAULT_RULE_BODY
    assert db.exec(select(AttendanceRule)).all() == []


def test_first_put_creates_the_row_and_later_puts_are_idempotent(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    payload = {
        "punch_window_min": 90,
        "late_grace_min": 10,
        "absent_deduct_per_day": "150.50",
    }

    created = client.put(
        RULES_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
        json=payload,
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["id"] is not None
    assert body["is_default"] is False
    assert body["punch_window_min"] == 90
    assert body["late_grace_min"] == 10
    assert body["absent_deduct_per_day"] == "150.50"
    # Omitted fields keep the system defaults.
    assert body["early_grace_min"] == 5
    assert body["missing_punch_deduct_per_occurrence"] == "0.00"

    rows = db.exec(select(AttendanceRule)).all()
    assert len(rows) == 1

    repeated = client.put(
        RULES_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
        json=payload,
    )
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["id"] == body["id"]
    assert len(db.exec(select(AttendanceRule)).all()) == 1

    fetched = get_rule(client, superuser_token_headers, company.id)
    assert fetched == repeated.json()


def test_rule_updates_apply_only_the_supplied_fields(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    create_attendance_rule(
        db,
        company_id=company.id,
        punch_window_min=90,
        late_grace_min=10,
    )

    response = client.put(
        RULES_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
        json={"early_grace_min": 15},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["punch_window_min"] == 90
    assert body["late_grace_min"] == 10
    assert body["early_grace_min"] == 15


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"late_grace_min": -1}, "late_grace_min"),
        ({"punch_window_min": -30}, "punch_window_min"),
        ({"absent_deduct_per_day": "-1.00"}, "absent_deduct_per_day"),
        ({"late_deduct_per_occurrence": "-0.01"}, "late_deduct_per_occurrence"),
        ({"late_grace_min": "not-a-number"}, "late_grace_min"),
        ({"absent_if_no_punch": "maybe"}, "absent_if_no_punch"),
        ({"late_grace_min": 2_147_483_648}, "late_grace_min"),
        ({"absent_deduct_per_day": "1000000000000.00"}, "absent_deduct_per_day"),
    ],
)
def test_invalid_rule_values_return_chinese_422_errors(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    payload: dict[str, Any],
    field: str,
) -> None:
    company = create_company(db)

    response = client.put(
        RULES_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
        json=payload,
    )

    assert response.status_code == 422, response.text
    errors = response.json()["detail"]
    assert errors[0]["loc"][-1] == field
    assert errors[0]["msg"]


def test_explicit_null_and_unknown_rule_fields_are_rejected(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)

    nulled = client.put(
        RULES_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
        json={"late_grace_min": None},
    )
    assert nulled.status_code == 422, nulled.text
    assert nulled.json()["detail"][0]["msg"] == "该字段不能为空"

    extra = client.put(
        RULES_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
        json={"is_default": True},
    )
    assert extra.status_code == 422, extra.text
    assert extra.json()["detail"][0]["msg"] == "该字段不可修改"


def test_unknown_company_returns_404(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    company_id = uuid.uuid7()

    fetched = client.get(
        RULES_URL, headers=superuser_token_headers, params={"company_id": company_id}
    )
    written = client.put(
        RULES_URL,
        headers=superuser_token_headers,
        params={"company_id": company_id},
        json={"late_grace_min": 10},
    )

    for response in (fetched, written):
        assert response.status_code == 404, response.text
        assert error_detail(response)["code"] == "not_found"


def test_rule_changes_mark_only_draft_and_calculated_months_stale(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    other_company = create_company(db)
    months = {
        status: create_attendance_month(
            db,
            company_id=company.id,
            month=date(2026, index + 1, 1),
            status=status,
            is_stale=False,
        )
        for index, status in enumerate(
            (
                AttendanceMonthStatus.DRAFT,
                AttendanceMonthStatus.CALCULATED,
                AttendanceMonthStatus.CONFIRMED,
                AttendanceMonthStatus.LOCKED,
            )
        )
    }
    other_month = create_attendance_month(
        db,
        company_id=other_company.id,
        month=date(2026, 1, 1),
        status=AttendanceMonthStatus.CALCULATED,
        is_stale=False,
    )

    response = client.put(
        RULES_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
        json={"late_grace_min": 12},
    )
    assert response.status_code == 200, response.text

    for status, month in months.items():
        db.refresh(month)
        expected = status in (
            AttendanceMonthStatus.DRAFT,
            AttendanceMonthStatus.CALCULATED,
        )
        assert month.is_stale is expected, status

    db.refresh(other_month)
    assert other_month.is_stale is False


def test_reading_company_rules_never_marks_months_stale(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    month = create_attendance_month(
        db,
        company_id=company.id,
        status=AttendanceMonthStatus.CALCULATED,
        is_stale=False,
    )

    get_rule(client, superuser_token_headers, company.id)

    db.refresh(month)
    assert month.is_stale is False


def test_company_rules_are_isolated_by_company(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    first = create_company(db, company_code="C-RULE-1")
    second = create_company(db, company_code="C-RULE-2")
    create_attendance_rule(db, company_id=first.id, late_grace_min=11)

    first_rule = get_rule(client, superuser_token_headers, first.id)
    second_rule = get_rule(client, superuser_token_headers, second.id)

    assert first_rule["late_grace_min"] == 11
    assert first_rule["is_default"] is False
    assert second_rule["late_grace_min"] == 5
    assert second_rule["is_default"] is True


# ---------------------------------------------------------------------------
# Plan rule overrides
# ---------------------------------------------------------------------------


def test_plan_override_endpoints_require_authentication(client: TestClient) -> None:
    url = plan_overrides_url(uuid.uuid7())
    assert client.get(url).status_code == 401
    assert client.put(url, json={"overrides": {}}).status_code == 401


def test_get_plan_overrides_returns_null_inheritance_and_effective_rule(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    create_attendance_rule(
        db,
        company_id=company.id,
        late_grace_min=8,
        ot_threshold_min=20,
    )
    plan = create_schedule_plan(db, company_id=company.id)

    response = client.get(plan_overrides_url(plan.id), headers=superuser_token_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["overrides"] == dict.fromkeys(RULE_FIELDS)
    assert body["company_default"]["late_grace_min"] == 8
    assert body["company_default"]["ot_threshold_min"] == 20
    assert body["effective"]["late_grace_min"] == 8
    assert body["effective"]["ot_threshold_min"] == 20
    assert body["effective"]["punch_window_min"] == 120


def test_put_replaces_overrides_wholesale_and_merges_with_company_defaults(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    create_attendance_rule(db, company_id=company.id, late_grace_min=8)
    plan = create_schedule_plan(db, company_id=company.id)

    first = client.put(
        plan_overrides_url(plan.id),
        headers=superuser_token_headers,
        json={
            "overrides": {
                "late_grace_min": 12,
                "absent_deduct_per_day": "50.00",
            }
        },
    )
    assert first.status_code == 200, first.text
    assert first.json()["overrides"]["late_grace_min"] == 12
    assert first.json()["overrides"]["absent_deduct_per_day"] == "50.00"
    assert first.json()["effective"]["late_grace_min"] == 12
    assert first.json()["effective"]["absent_deduct_per_day"] == "50.00"

    second = client.put(
        plan_overrides_url(plan.id),
        headers=superuser_token_headers,
        json={"overrides": {"ot_threshold_min": 45}},
    )
    assert second.status_code == 200, second.text
    body = second.json()
    # The previous overrides are gone; these two fields inherit again.
    assert body["overrides"]["late_grace_min"] is None
    assert body["overrides"]["absent_deduct_per_day"] is None
    assert body["effective"]["late_grace_min"] == 8
    assert body["effective"]["absent_deduct_per_day"] == "0.00"
    assert body["effective"]["ot_threshold_min"] == 45

    stored = db.exec(select(PlanRuleOverride)).one()
    assert stored.late_grace_min is None
    assert stored.absent_deduct_per_day is None
    assert stored.ot_threshold_min == 45


def test_put_with_all_null_clears_the_override_row(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    plan = create_schedule_plan(db, company_id=company.id)
    client.put(
        plan_overrides_url(plan.id),
        headers=superuser_token_headers,
        json={"overrides": {"late_grace_min": 12}},
    )

    cleared = client.put(
        plan_overrides_url(plan.id),
        headers=superuser_token_headers,
        json={"overrides": {}},
    )

    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["overrides"] == dict.fromkeys(RULE_FIELDS)
    assert cleared.json()["effective"]["late_grace_min"] == 5
    assert db.exec(select(PlanRuleOverride)).all() == []


def test_plan_overrides_use_the_plans_company_default(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    plan_company = create_company(db, company_code="C-PLAN")
    other_company = create_company(db, company_code="C-OTHER")
    create_attendance_rule(db, company_id=other_company.id, late_grace_min=99)
    plan = create_schedule_plan(db, company_id=plan_company.id)

    body = client.get(
        plan_overrides_url(plan.id), headers=superuser_token_headers
    ).json()

    assert body["company_default"]["late_grace_min"] == 5
    assert body["effective"]["late_grace_min"] == 5


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (AttendanceMonthStatus.CONFIRMED, "month_confirmed"),
        (AttendanceMonthStatus.LOCKED, "month_locked"),
    ],
)
def test_plan_overrides_are_blocked_in_confirmed_or_locked_months(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    status: AttendanceMonthStatus,
    code: str,
) -> None:
    company = create_company(db)
    plan = create_schedule_plan(db, company_id=company.id)
    create_attendance_month(db, company_id=company.id, status=status)

    response = client.put(
        plan_overrides_url(plan.id),
        headers=superuser_token_headers,
        json={"overrides": {"late_grace_min": 12}},
    )

    assert response.status_code == 409, response.text
    assert error_detail(response)["code"] == code
    assert db.exec(select(PlanRuleOverride)).all() == []


def test_plan_override_changes_mark_a_calculated_month_stale(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    plan = create_schedule_plan(db, company_id=company.id)
    month = create_attendance_month(
        db,
        company_id=company.id,
        status=AttendanceMonthStatus.CALCULATED,
        is_stale=False,
    )

    response = client.put(
        plan_overrides_url(plan.id),
        headers=superuser_token_headers,
        json={"overrides": {"late_grace_min": 12}},
    )

    assert response.status_code == 200, response.text
    db.refresh(month)
    assert month.is_stale is True


def test_plan_overrides_reject_an_archived_plan(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    plan = create_schedule_plan(db, company_id=company.id, status=PlanStatus.ARCHIVED)

    response = client.put(
        plan_overrides_url(plan.id),
        headers=superuser_token_headers,
        json={"overrides": {"late_grace_min": 12}},
    )

    assert response.status_code == 409, response.text
    assert error_detail(response)["code"] == "plan_archived"


def test_unknown_plan_override_returns_404(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    plan_id = uuid.uuid7()
    fetched = client.get(plan_overrides_url(plan_id), headers=superuser_token_headers)
    written = client.put(
        plan_overrides_url(plan_id),
        headers=superuser_token_headers,
        json={"overrides": {"late_grace_min": 12}},
    )

    for response in (fetched, written):
        assert response.status_code == 404, response.text
        assert error_detail(response)["code"] == "not_found"


# ---------------------------------------------------------------------------
# Plan list (needed by the rules page override selector)
# ---------------------------------------------------------------------------


def test_schedule_plan_list_filters_by_company_month_status_and_keyword(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db, company_code="C-LIST-1")
    other_company = create_company(db, company_code="C-LIST-2")
    create_schedule_plan(
        db,
        company_id=company.id,
        month=date(2026, 9, 1),
        plan_name="行政班方案",
    )
    create_schedule_plan(
        db,
        company_id=company.id,
        month=date(2026, 10, 1),
        plan_name="归档方案",
        status=PlanStatus.ARCHIVED,
    )
    create_schedule_plan(
        db,
        company_id=other_company.id,
        month=date(2026, 9, 1),
        plan_name="其他公司方案",
    )

    response = client.get(
        PLANS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "limit": 500},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["count"] == 2
    assert [plan["plan_name"] for plan in body["data"]] == [
        "归档方案",
        "行政班方案",
    ]

    september = client.get(
        PLANS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "month": "2026-09"},
    ).json()
    assert september["count"] == 1
    assert september["data"][0]["plan_name"] == "行政班方案"
    assert september["data"][0]["month"] == "2026-09"

    enabled = client.get(
        PLANS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "status": "enabled"},
    ).json()
    assert enabled["count"] == 1

    keyword = client.get(
        PLANS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "keyword": "行政"},
    ).json()
    assert keyword["count"] == 1
    assert keyword["data"][0]["plan_name"] == "行政班方案"

    other = client.get(
        PLANS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(other_company.id)},
    ).json()
    assert [plan["plan_name"] for plan in other["data"]] == ["其他公司方案"]


def test_schedule_plan_list_resolves_scope_display_fields(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    department = create_department(db, company=company, dept_code="D-SCOPE")
    create_schedule_plan(
        db,
        company_id=company.id,
        scope_type=ScheduleScopeType.DEPT,
        scope_ids=[department.id],
    )

    body = client.get(
        PLANS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    ).json()

    plan = body["data"][0]
    assert [scope["scope_id"] for scope in plan["scopes"]] == [str(department.id)]
    assert plan["scopes"][0]["scope_code"] == "D-SCOPE"
    assert plan["scopes"][0]["scope_name"] == department.dept_name
    # The A2 selector does not need plan-day snapshots; A3 extends this read.
    assert plan["days"] == []


def test_schedule_plan_list_requires_authentication_and_an_existing_company(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    assert client.get(PLANS_URL, params={"company_id": uuid.uuid7()}).status_code == 401

    response = client.get(
        PLANS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(uuid.uuid7())},
    )
    assert response.status_code == 404
    assert error_detail(response)["code"] == "not_found"
