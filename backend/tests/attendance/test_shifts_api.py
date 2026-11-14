"""Shift API contract tests.

Seam: ``/api/v1/attendance/shifts``. The tests assert the approved contract
from ``docs/specs/attendance-management.md``: CRUD, company-scoped codes,
uppercase normalization, immutable identifiers, time/break/rest validation,
deactivate and delete blockers, filters, and authentication.
"""

import uuid
from datetime import date, time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.enums import PlanStatus
from app.models import RosterEntryShift, Shift
from tests.utils.attendance_factories import (
    create_roster_entry,
    create_schedule_plan,
)
from tests.utils.factories import (
    create_company,
    create_department,
    create_employee,
    create_position,
)
from tests.utils.utils import random_upper_code

SHIFTS_URL = f"{settings.API_V1_STR}/attendance/shifts/"


def shift_url(shift_id: uuid.UUID | str) -> str:
    return f"{SHIFTS_URL}{shift_id}"


def shift_payload(company_id: uuid.UUID | str, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "company_id": str(company_id),
        "shift_code": random_upper_code("S"),
        "shift_name": "行政班",
        "start_time": "08:30:00",
        "end_time": "17:30:00",
        "cross_day": False,
        "break_start": None,
        "break_end": None,
        "rest_minutes": 60,
        "color": "#2563EB",
        "note": None,
        "is_active": True,
    }
    payload.update(overrides)
    return payload


def create_shift_via_api(
    client: TestClient,
    headers: dict[str, str],
    company_id: uuid.UUID | str,
    **overrides: Any,
) -> dict[str, Any]:
    response = client.post(
        SHIFTS_URL,
        headers=headers,
        json=shift_payload(company_id, **overrides),
    )
    assert response.status_code == 201, response.text
    return response.json()


def error_detail(response: Any) -> dict[str, Any]:
    body = response.json()
    assert isinstance(body["detail"], dict), body
    return body["detail"]


def test_shift_endpoints_require_authentication(client: TestClient) -> None:
    company_id = uuid.uuid7()
    for method, url, kwargs in (
        ("get", SHIFTS_URL, {"params": {"company_id": str(company_id)}}),
        ("post", SHIFTS_URL, {"json": {}}),
        ("get", shift_url(uuid.uuid7()), {}),
        ("patch", shift_url(uuid.uuid7()), {"json": {}}),
        ("delete", shift_url(uuid.uuid7()), {}),
    ):
        response = getattr(client, method)(url, **kwargs)
        assert response.status_code == 401, (method, response.text)
        assert response.json() == {"detail": "未登录或登录状态已过期"}


def test_create_shift_normalizes_the_code_and_returns_public_fields(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db, company_name="荣新建设")

    response = client.post(
        SHIFTS_URL,
        headers=superuser_token_headers,
        json=shift_payload(company.id, shift_code="  adm-1  ", note="常用"),
    )

    assert response.status_code == 201, response.text
    shift = response.json()
    assert shift["shift_code"] == "ADM-1"
    assert shift["shift_name"] == "行政班"
    assert shift["start_time"] == "08:30:00"
    assert shift["end_time"] == "17:30:00"
    assert shift["cross_day"] is False
    assert shift["break_start"] is None
    assert shift["break_end"] is None
    assert shift["rest_minutes"] == 60
    assert shift["color"] == "#2563EB"
    assert shift["note"] == "常用"
    assert shift["is_active"] is True
    assert shift["company_id"] == str(company.id)
    assert shift["id"]
    assert shift["created_at"].endswith("Z")
    assert shift["updated_at"].endswith("Z")


def test_duplicate_codes_conflict_within_a_company_only(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    first_company = create_company(db, company_code="C-A")
    second_company = create_company(db, company_code="C-B")
    create_shift_via_api(
        client, superuser_token_headers, first_company.id, shift_code="ADM"
    )

    duplicate = client.post(
        SHIFTS_URL,
        headers=superuser_token_headers,
        json=shift_payload(first_company.id, shift_code=" adm "),
    )

    assert duplicate.status_code == 409, duplicate.text
    detail = error_detail(duplicate)
    assert detail["code"] == "duplicate_code"
    assert detail["field_errors"] == {"shift_code": "班次编码已存在"}

    create_shift_via_api(
        client, superuser_token_headers, second_company.id, shift_code="ADM"
    )


def test_shift_code_and_company_are_immutable(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    shift = create_shift_via_api(client, superuser_token_headers, company.id)

    for field, value in (
        ("shift_code", "OTHER"),
        ("company_id", str(uuid.uuid7())),
    ):
        response = client.patch(
            shift_url(shift["id"]),
            headers=superuser_token_headers,
            json={field: value},
        )
        assert response.status_code == 422, (field, response.text)
        errors = response.json()["detail"]
        assert errors[0]["loc"][-1] == field
        assert errors[0]["msg"] == "该字段不可修改"


def test_get_update_and_delete_a_shift(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    created = create_shift_via_api(
        client, superuser_token_headers, company.id, shift_code="ADM"
    )

    fetched = client.get(shift_url(created["id"]), headers=superuser_token_headers)
    assert fetched.status_code == 200
    assert fetched.json() == created

    updated = client.patch(
        shift_url(created["id"]),
        headers=superuser_token_headers,
        json={
            "shift_name": "行政班（新）",
            "start_time": "09:00:00",
            "end_time": "18:00:00",
            "break_start": "12:00:00",
            "break_end": "13:00:00",
            "rest_minutes": 45,
            "color": None,
            "note": "调整",
        },
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["shift_code"] == "ADM"
    assert body["shift_name"] == "行政班（新）"
    assert body["start_time"] == "09:00:00"
    assert body["end_time"] == "18:00:00"
    assert body["break_start"] == "12:00:00"
    assert body["break_end"] == "13:00:00"
    assert body["rest_minutes"] == 45
    assert body["color"] is None
    assert body["note"] == "调整"

    deleted = client.delete(shift_url(created["id"]), headers=superuser_token_headers)
    assert deleted.status_code == 200, deleted.text
    assert deleted.json() == {"message": "班次删除成功"}
    assert (
        client.get(
            shift_url(created["id"]), headers=superuser_token_headers
        ).status_code
        == 404
    )


def test_lists_shifts_with_filters_fixed_sorting_and_pagination(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db, company_code="C-LIST")
    other_company = create_company(db, company_code="C-OTHER")
    for code in ("B", "A", "C"):
        create_shift_via_api(
            client, superuser_token_headers, company.id, shift_code=code
        )
    create_shift_via_api(
        client,
        superuser_token_headers,
        company.id,
        shift_code="OFF",
        shift_name="停用班",
        is_active=False,
    )
    create_shift_via_api(
        client, superuser_token_headers, other_company.id, shift_code="OTHER"
    )

    response = client.get(
        SHIFTS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "limit": 500},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["count"] == 4
    assert [item["shift_code"] for item in body["data"]] == ["A", "B", "C", "OFF"]

    filtered = client.get(
        SHIFTS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "is_active": True},
    ).json()
    assert filtered["count"] == 3
    assert all(item["is_active"] for item in filtered["data"])

    by_code = client.get(
        SHIFTS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "keyword": "b"},
    ).json()
    assert [item["shift_code"] for item in by_code["data"]] == ["B"]

    by_name = client.get(
        SHIFTS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "keyword": "停用"},
    ).json()
    assert [item["shift_code"] for item in by_name["data"]] == ["OFF"]

    page = client.get(
        SHIFTS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "skip": 1, "limit": 2},
    ).json()
    assert page["count"] == 4
    assert [item["shift_code"] for item in page["data"]] == ["B", "C"]

    other = client.get(
        SHIFTS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(other_company.id)},
    ).json()
    assert [item["shift_code"] for item in other["data"]] == ["OTHER"]


def test_list_rejects_an_unknown_company_and_invalid_page_bounds(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    missing = client.get(
        SHIFTS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(uuid.uuid7())},
    )
    assert missing.status_code == 404
    assert error_detail(missing)["code"] == "not_found"

    for params in (
        {"company_id": str(uuid.uuid7()), "skip": -1},
        {"company_id": str(uuid.uuid7()), "limit": 501},
        {"company_id": str(uuid.uuid7()), "limit": 0},
    ):
        response = client.get(
            SHIFTS_URL, headers=superuser_token_headers, params=params
        )
        assert response.status_code == 422, response.text


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"end_time": "08:00:00"}, "end_time"),
        ({"end_time": "08:30:00"}, "end_time"),
        ({"cross_day": True}, "end_time"),
        ({"break_start": "12:00:00"}, "break_end"),
        ({"break_end": "13:00:00"}, "break_start"),
        ({"break_start": "13:00:00", "break_end": "12:00:00"}, "break_start"),
        ({"break_start": "07:00:00", "break_end": "08:00:00"}, "break_start"),
    ],
)
def test_invalid_time_ranges_return_409_with_chinese_field_errors(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    overrides: dict[str, Any],
    field: str,
) -> None:
    company = create_company(db)

    response = client.post(
        SHIFTS_URL,
        headers=superuser_token_headers,
        json=shift_payload(company.id, **overrides),
    )

    assert response.status_code == 409, response.text
    detail = error_detail(response)
    assert detail["code"] == "invalid_time_range"
    assert field in detail["field_errors"]
    assert detail["field_errors"][field]


def test_cross_day_shift_accepts_a_break_after_midnight(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)

    shift = create_shift_via_api(
        client,
        superuser_token_headers,
        company.id,
        shift_code="NIGHT",
        shift_name="夜班",
        start_time="22:00:00",
        end_time="06:00:00",
        cross_day=True,
        break_start="02:00:00",
        break_end="03:00:00",
    )

    assert shift["cross_day"] is True
    assert shift["break_start"] == "02:00:00"


def test_cross_day_shift_at_equal_times_is_a_full_day(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)

    shift = create_shift_via_api(
        client,
        superuser_token_headers,
        company.id,
        start_time="08:00:00",
        end_time="08:00:00",
        cross_day=True,
        rest_minutes=1440,
    )

    assert shift["rest_minutes"] == 1440


def test_rest_minutes_cannot_exceed_the_shift_span(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)

    response = client.post(
        SHIFTS_URL,
        headers=superuser_token_headers,
        json=shift_payload(company.id, rest_minutes=541),
    )

    assert response.status_code == 409, response.text
    detail = error_detail(response)
    assert detail["code"] == "invalid_time_range"
    assert "班次时长" in detail["field_errors"]["rest_minutes"]

    negative = client.post(
        SHIFTS_URL,
        headers=superuser_token_headers,
        json=shift_payload(company.id, rest_minutes=-1),
    )
    assert negative.status_code == 422
    assert negative.json()["detail"][0]["loc"][-1] == "rest_minutes"


def test_update_validates_the_merged_shift_and_can_clear_the_break(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    shift = create_shift_via_api(
        client,
        superuser_token_headers,
        company.id,
        break_start="11:30:00",
        break_end="13:30:00",
        rest_minutes=120,
    )

    invalid = client.patch(
        shift_url(shift["id"]),
        headers=superuser_token_headers,
        json={"end_time": "12:00:00"},
    )
    assert invalid.status_code == 409, invalid.text
    assert error_detail(invalid)["code"] == "invalid_time_range"

    cleared = client.patch(
        shift_url(shift["id"]),
        headers=superuser_token_headers,
        json={"break_start": None, "break_end": None},
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["break_start"] is None
    assert cleared.json()["break_end"] is None

    missing_end = client.patch(
        shift_url(shift["id"]),
        headers=superuser_token_headers,
        json={"break_start": "12:00:00"},
    )
    assert missing_end.status_code == 409, missing_end.text
    assert "break_end" in error_detail(missing_end)["field_errors"]


def test_unknown_shift_operations_return_404(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    shift_id = uuid.uuid7()

    get_response = client.get(shift_url(shift_id), headers=superuser_token_headers)
    patch_response = client.patch(
        shift_url(shift_id),
        headers=superuser_token_headers,
        json={"shift_name": "不存在"},
    )
    delete_response = client.delete(
        shift_url(shift_id), headers=superuser_token_headers
    )

    for response in (get_response, patch_response, delete_response):
        assert response.status_code == 404, response.text
        assert error_detail(response)["code"] == "not_found"


def test_create_requires_an_existing_active_company(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    inactive = create_company(db, company_code="C-OFF", is_active=False)

    missing = client.post(
        SHIFTS_URL,
        headers=superuser_token_headers,
        json=shift_payload(uuid.uuid7()),
    )
    assert missing.status_code == 409
    assert error_detail(missing)["code"] == "invalid_reference"
    assert "company_id" in error_detail(missing)["field_errors"]

    disabled = client.post(
        SHIFTS_URL,
        headers=superuser_token_headers,
        json=shift_payload(inactive.id),
    )
    assert disabled.status_code == 409
    assert error_detail(disabled)["code"] == "inactive_reference"
    assert "company_id" in error_detail(disabled)["field_errors"]


def _employee_for_roster(db: Session, company: Any) -> Any:
    department = create_department(db, company=company)
    position = create_position(db, company=company)
    return create_employee(db, dept=department, position=position)


def test_deactivation_is_blocked_by_an_enabled_plan(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    shift = create_shift_via_api(
        client, superuser_token_headers, company.id, shift_code="ADM"
    )
    create_schedule_plan(
        db,
        company_id=company.id,
        plan_name="行政班方案",
        days=[(1, 0, uuid.UUID(shift["id"])), (2, 0, uuid.UUID(shift["id"]))],
        status=PlanStatus.ENABLED,
    )

    response = client.patch(
        shift_url(shift["id"]),
        headers=superuser_token_headers,
        json={"is_active": False},
    )

    assert response.status_code == 409, response.text
    detail = error_detail(response)
    assert detail["code"] == "deactivate_blocked"
    assert "is_active" in detail["field_errors"]
    assert detail["blocker_count"] == 1
    assert [blocker["type"] for blocker in detail["blockers"]] == ["schedule_plan"]
    assert "2026-09" in detail["blockers"][0]["label"]
    assert "行政班方案" in detail["blockers"][0]["label"]
    assert (
        client.get(shift_url(shift["id"]), headers=superuser_token_headers).json()[
            "is_active"
        ]
        is True
    )


def test_deactivation_ignores_archived_plans_and_roster_entries(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    shift = create_shift_via_api(
        client, superuser_token_headers, company.id, shift_code="ADM"
    )
    create_schedule_plan(
        db,
        company_id=company.id,
        days=[(1, 0, uuid.UUID(shift["id"]))],
        status=PlanStatus.ARCHIVED,
    )
    employee = _employee_for_roster(db, company)
    create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 1),
        shifts=[db.get(Shift, uuid.UUID(shift["id"]))],
    )

    deactivated = client.patch(
        shift_url(shift["id"]),
        headers=superuser_token_headers,
        json={"is_active": False},
    )
    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["is_active"] is False

    reactivated = client.patch(
        shift_url(shift["id"]),
        headers=superuser_token_headers,
        json={"is_active": True},
    )
    assert reactivated.status_code == 200, reactivated.text
    assert reactivated.json()["is_active"] is True


def test_delete_blocks_on_any_plan_or_roster_snapshot(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    plan_shift = create_shift_via_api(
        client, superuser_token_headers, company.id, shift_code="PLAN"
    )
    create_schedule_plan(
        db,
        company_id=company.id,
        plan_name="归档方案",
        days=[(1, 0, uuid.UUID(plan_shift["id"]))],
        status=PlanStatus.ARCHIVED,
    )
    plan_delete = client.delete(
        shift_url(plan_shift["id"]), headers=superuser_token_headers
    )
    assert plan_delete.status_code == 409, plan_delete.text
    plan_detail = error_detail(plan_delete)
    assert plan_detail["code"] == "referenced"
    assert plan_detail["blocker_count"] == 1
    assert plan_detail["blockers"][0]["type"] == "schedule_plan"

    roster_shift = create_shift_via_api(
        client, superuser_token_headers, company.id, shift_code="ROSTER"
    )
    employee = _employee_for_roster(db, company)
    create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 1),
        shifts=[db.get(Shift, uuid.UUID(roster_shift["id"]))],
    )
    roster_delete = client.delete(
        shift_url(roster_shift["id"]), headers=superuser_token_headers
    )
    assert roster_delete.status_code == 409, roster_delete.text
    roster_detail = error_detail(roster_delete)
    assert roster_detail["code"] == "referenced"
    assert roster_detail["blocker_count"] == 1
    assert roster_detail["blockers"][0]["type"] == "roster_entry"
    assert employee.employee_no in roster_detail["blockers"][0]["label"]


def test_shift_edits_do_not_rewrite_roster_snapshots(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    shift = create_shift_via_api(
        client,
        superuser_token_headers,
        company.id,
        shift_code="ADM",
        shift_name="行政班",
        break_start=None,
        break_end=None,
        rest_minutes=60,
    )
    employee = _employee_for_roster(db, company)
    create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 1),
        shifts=[db.get(Shift, uuid.UUID(shift["id"]))],
    )

    response = client.patch(
        shift_url(shift["id"]),
        headers=superuser_token_headers,
        json={
            "shift_name": "行政班（改）",
            "start_time": "09:00:00",
            "end_time": "18:00:00",
            "rest_minutes": 30,
            "break_start": "12:00:00",
            "break_end": "13:00:00",
        },
    )
    assert response.status_code == 200, response.text

    snapshot = db.exec(select(RosterEntryShift)).one()
    assert snapshot.shift_name == "行政班"
    assert snapshot.start_time == time(8, 30)
    assert snapshot.end_time == time(17, 30)
    assert snapshot.rest_minutes == 60
    assert snapshot.break_start is None
    assert snapshot.break_end is None


def test_shift_deletion_is_isolated_by_company(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    first_company = create_company(db, company_code="C-ONE")
    second_company = create_company(db, company_code="C-TWO")
    first_shift = create_shift_via_api(
        client, superuser_token_headers, first_company.id, shift_code="ADM"
    )
    create_shift_via_api(
        client, superuser_token_headers, second_company.id, shift_code="ADM"
    )

    response = client.delete(
        shift_url(first_shift["id"]), headers=superuser_token_headers
    )
    assert response.status_code == 200

    second_list = client.get(
        SHIFTS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(second_company.id)},
    ).json()
    assert second_list["count"] == 1
    assert second_list["data"][0]["shift_code"] == "ADM"


def test_any_logged_in_user_has_attendance_access(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)

    response = client.get(
        SHIFTS_URL,
        headers=normal_user_token_headers,
        params={"company_id": str(company.id)},
    )

    assert response.status_code == 200
    assert response.json() == {"data": [], "count": 0}
