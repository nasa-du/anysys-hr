"""Holiday calendar API contract tests.

Seam: ``/api/v1/attendance/holidays``. The tests assert the contract from
``docs/specs/attendance-management.md`` sections 4.5, 5.7, 8.3.7, 8.4, 8.5,
and 9.2: company-scoped CRUD, ``(company_id, date)`` uniqueness, immutable
dates, copy-year preview/apply with conflict and overwrite, and stale marking
that never touches confirmed or locked months.
"""

import uuid
from datetime import date
from typing import Any

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.enums import AttendanceMonthStatus, HolidayDayType
from app.models import Holiday
from tests.utils.attendance_factories import (
    create_attendance_month,
    create_holiday,
)
from tests.utils.factories import create_company

HOLIDAYS_URL = f"{settings.API_V1_STR}/attendance/holidays/"
COPY_PREVIEW_URL = f"{HOLIDAYS_URL}copy-year/preview"
COPY_URL = f"{HOLIDAYS_URL}copy-year"


def holiday_url(holiday_id: uuid.UUID | str) -> str:
    return f"{HOLIDAYS_URL}{holiday_id}"


def error_detail(response: Any) -> dict[str, Any]:
    body = response.json()
    assert isinstance(body["detail"], dict), body
    return body["detail"]


def holiday_payload(company_id: uuid.UUID | str, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "company_id": str(company_id),
        "date": "2026-09-25",
        "name": "中秋节",
        "day_type": "holiday",
        "note": None,
    }
    payload.update(overrides)
    return payload


def list_holidays(
    client: TestClient,
    headers: dict[str, str],
    company_id: uuid.UUID | str,
    **params: Any,
) -> dict[str, Any]:
    response = client.get(
        HOLIDAYS_URL,
        headers=headers,
        params={"company_id": str(company_id), "limit": 500, **params},
    )
    assert response.status_code == 200, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Authentication and listing
# ---------------------------------------------------------------------------


def test_holiday_endpoints_require_authentication(client: TestClient) -> None:
    company_id = uuid.uuid7()
    holiday_id = uuid.uuid7()
    calls = (
        ("get", HOLIDAYS_URL, {"params": {"company_id": str(company_id)}}),
        ("post", HOLIDAYS_URL, {"json": {}}),
        ("post", COPY_PREVIEW_URL, {"json": {}}),
        ("post", COPY_URL, {"json": {}}),
        ("patch", holiday_url(holiday_id), {"json": {}}),
        ("delete", holiday_url(holiday_id), {}),
    )
    for method, url, kwargs in calls:
        response = getattr(client, method)(url, **kwargs)
        assert response.status_code == 401, (method, url, response.text)
        assert response.json() == {"detail": "未登录或登录状态已过期"}


def test_list_holidays_filters_by_year_sorts_and_paginates(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    other_company = create_company(db)
    create_holiday(
        db, company_id=company.id, holiday_date=date(2026, 10, 1), name="国庆节"
    )
    create_holiday(
        db,
        company_id=company.id,
        holiday_date=date(2026, 9, 27),
        name="调休上班",
        day_type=HolidayDayType.ADJUSTED_WORKDAY,
    )
    create_holiday(
        db, company_id=company.id, holiday_date=date(2025, 12, 31), name="跨年"
    )
    create_holiday(db, company_id=other_company.id, holiday_date=date(2026, 9, 25))

    body = list_holidays(client, superuser_token_headers, company.id, year=2026)
    assert body["count"] == 2
    assert [item["date"] for item in body["data"]] == ["2026-09-27", "2026-10-01"]
    assert body["data"][0]["day_type"] == "adjusted_workday"

    page = list_holidays(
        client, superuser_token_headers, company.id, year=2026, skip=1, limit=1
    )
    assert page["count"] == 2
    assert [item["date"] for item in page["data"]] == ["2026-10-01"]

    all_years = list_holidays(client, superuser_token_headers, company.id)
    assert all_years["count"] == 3
    assert [item["date"] for item in all_years["data"]] == [
        "2025-12-31",
        "2026-09-27",
        "2026-10-01",
    ]


def test_list_rejects_an_unknown_company(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(
        HOLIDAYS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(uuid.uuid7())},
    )

    assert response.status_code == 404
    assert error_detail(response)["code"] == "not_found"


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def test_create_update_and_delete_a_holiday(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)

    created = client.post(
        HOLIDAYS_URL,
        headers=superuser_token_headers,
        json=holiday_payload(company.id, note="三倍工资"),
    )
    assert created.status_code == 201, created.text
    holiday = created.json()
    assert holiday["date"] == "2026-09-25"
    assert holiday["name"] == "中秋节"
    assert holiday["day_type"] == "holiday"
    assert holiday["note"] == "三倍工资"

    updated = client.patch(
        holiday_url(holiday["id"]),
        headers=superuser_token_headers,
        json={"name": "中秋节（调整）", "day_type": "adjusted_workday"},
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["name"] == "中秋节（调整）"
    assert body["day_type"] == "adjusted_workday"
    assert body["date"] == "2026-09-25"

    deleted = client.delete(holiday_url(holiday["id"]), headers=superuser_token_headers)
    assert deleted.status_code == 200, deleted.text
    assert deleted.json() == {"message": "节假日删除成功"}
    assert db.exec(select(Holiday)).all() == []


def test_duplicate_company_date_returns_409_and_other_companies_may_share(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db, company_code="C-HOL-1")
    other_company = create_company(db, company_code="C-HOL-2")
    created = client.post(
        HOLIDAYS_URL,
        headers=superuser_token_headers,
        json=holiday_payload(company.id),
    )
    assert created.status_code == 201

    duplicate = client.post(
        HOLIDAYS_URL,
        headers=superuser_token_headers,
        json=holiday_payload(company.id, name="另一个名称"),
    )
    assert duplicate.status_code == 409, duplicate.text
    detail = error_detail(duplicate)
    assert detail["code"] == "duplicate_holiday"
    assert "date" in detail["field_errors"]

    other = client.post(
        HOLIDAYS_URL,
        headers=superuser_token_headers,
        json=holiday_payload(other_company.id),
    )
    assert other.status_code == 201, other.text


def test_holiday_date_is_immutable_and_unknown_ids_return_404(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    holiday = create_holiday(db, company_id=company.id)

    moved = client.patch(
        holiday_url(holiday.id),
        headers=superuser_token_headers,
        json={"date": "2026-10-01"},
    )
    assert moved.status_code == 422, moved.text
    assert moved.json()["detail"][0]["msg"] == "该字段不可修改"

    for method, url, kwargs in (
        ("patch", holiday_url(uuid.uuid7()), {"json": {"name": "不存在"}}),
        ("delete", holiday_url(uuid.uuid7()), {}),
    ):
        response = getattr(client, method)(
            url, headers=superuser_token_headers, **kwargs
        )
        assert response.status_code == 404, (method, response.text)
        assert error_detail(response)["code"] == "not_found"


def test_holiday_writes_mark_only_draft_and_calculated_months_stale(
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

    created = client.post(
        HOLIDAYS_URL,
        headers=superuser_token_headers,
        json=holiday_payload(company.id),
    )
    assert created.status_code == 201, created.text
    holiday = created.json()

    for status, month in months.items():
        db.refresh(month)
        expected = status in (
            AttendanceMonthStatus.DRAFT,
            AttendanceMonthStatus.CALCULATED,
        )
        assert month.is_stale is expected, status

    # Reset for update and delete assertions.
    for month in months.values():
        month.is_stale = False
    db.commit()

    updated = client.patch(
        holiday_url(holiday["id"]),
        headers=superuser_token_headers,
        json={"name": "中秋"},
    )
    assert updated.status_code == 200
    for status, month in months.items():
        db.refresh(month)
        expected = status in (
            AttendanceMonthStatus.DRAFT,
            AttendanceMonthStatus.CALCULATED,
        )
        assert month.is_stale is expected, ("update", status)

    for month in months.values():
        month.is_stale = False
    db.commit()

    deleted = client.delete(holiday_url(holiday["id"]), headers=superuser_token_headers)
    assert deleted.status_code == 200
    for status, month in months.items():
        db.refresh(month)
        expected = status in (
            AttendanceMonthStatus.DRAFT,
            AttendanceMonthStatus.CALCULATED,
        )
        assert month.is_stale is expected, ("delete", status)

    db.refresh(other_month)
    assert other_month.is_stale is False


def test_reading_holidays_never_marks_months_stale(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    create_holiday(db, company_id=company.id)
    month = create_attendance_month(
        db,
        company_id=company.id,
        status=AttendanceMonthStatus.CALCULATED,
        is_stale=False,
    )

    list_holidays(client, superuser_token_headers, company.id)

    db.refresh(month)
    assert month.is_stale is False


# ---------------------------------------------------------------------------
# Copy previous year
# ---------------------------------------------------------------------------


def _seed_copy_source(db: Session, company_id: uuid.UUID) -> None:
    create_holiday(
        db,
        company_id=company_id,
        holiday_date=date(2025, 9, 25),
        name="中秋节",
    )
    create_holiday(
        db,
        company_id=company_id,
        holiday_date=date(2025, 10, 1),
        name="国庆节",
    )
    create_holiday(
        db,
        company_id=company_id,
        holiday_date=date(2025, 10, 2),
        name="国庆节",
    )


def test_copy_preview_lists_creates_and_conflicts(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    _seed_copy_source(db, company.id)
    create_holiday(
        db,
        company_id=company.id,
        holiday_date=date(2026, 10, 2),
        name="已有国庆安排",
    )

    response = client.post(
        COPY_PREVIEW_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
        json={"source_year": 2025, "target_year": 2026, "overwrite": False},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["create_count"] == 2
    assert body["conflict_count"] == 1
    assert body["creates"] == [
        {"date": "2026-09-25", "name": "中秋节", "day_type": "holiday"},
        {"date": "2026-10-01", "name": "国庆节", "day_type": "holiday"},
    ]
    assert body["conflicts"] == [
        {
            "date": "2026-10-02",
            "name": "国庆节",
            "existing_name": "已有国庆安排",
        }
    ]


def test_copy_without_overwrite_returns_409_and_writes_nothing(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    _seed_copy_source(db, company.id)
    create_holiday(
        db,
        company_id=company.id,
        holiday_date=date(2026, 10, 2),
        name="已有国庆安排",
    )

    response = client.post(
        COPY_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
        json={"source_year": 2025, "target_year": 2026, "overwrite": False},
    )

    assert response.status_code == 409, response.text
    detail = error_detail(response)
    assert detail["code"] == "holiday_conflict"
    assert "overwrite" in detail["field_errors"]
    assert "已存在" in detail["message"] or "冲突" in detail["message"]

    target_holidays = db.exec(
        select(Holiday).where(Holiday.date >= date(2026, 1, 1))
    ).all()
    assert len(target_holidays) == 1
    assert target_holidays[0].name == "已有国庆安排"


def test_copy_with_overwrite_updates_conflicts_and_creates_missing(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    _seed_copy_source(db, company.id)
    create_holiday(
        db,
        company_id=company.id,
        holiday_date=date(2026, 10, 2),
        name="已有国庆安排",
        note="旧备注",
    )

    response = client.post(
        COPY_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
        json={"source_year": 2025, "target_year": 2026, "overwrite": True},
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"created": 2, "updated": 1, "skipped": 0}

    holidays = {
        holiday.date: holiday
        for holiday in db.exec(
            select(Holiday).where(Holiday.date >= date(2026, 1, 1))
        ).all()
    }
    assert sorted(holidays) == [
        date(2026, 9, 25),
        date(2026, 10, 1),
        date(2026, 10, 2),
    ]
    assert holidays[date(2026, 10, 2)].name == "国庆节"
    assert holidays[date(2026, 10, 2)].note is None

    # A repeat copy changes nothing: no rows are updated and a fresh editable
    # month must not be marked stale.
    month = create_attendance_month(
        db,
        company_id=company.id,
        status=AttendanceMonthStatus.CALCULATED,
        is_stale=False,
    )
    repeated = client.post(
        COPY_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
        json={"source_year": 2025, "target_year": 2026, "overwrite": True},
    )
    assert repeated.status_code == 200, repeated.text
    assert repeated.json() == {"created": 0, "updated": 0, "skipped": 0}
    target_rows = db.exec(select(Holiday).where(Holiday.date >= date(2026, 1, 1))).all()
    assert len(target_rows) == 3
    db.refresh(month)
    assert month.is_stale is False


def test_copy_skips_february_29_when_the_target_year_is_not_a_leap_year(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    create_holiday(
        db,
        company_id=company.id,
        holiday_date=date(2024, 2, 29),
        name="闰日",
    )

    preview = client.post(
        COPY_PREVIEW_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
        json={"source_year": 2024, "target_year": 2025},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["create_count"] == 0
    assert preview.json()["conflict_count"] == 0
    assert preview.json()["creates"] == []

    applied = client.post(
        COPY_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
        json={"source_year": 2024, "target_year": 2025},
    )
    assert applied.status_code == 200, applied.text
    assert applied.json() == {"created": 0, "updated": 0, "skipped": 1}
    assert len(db.exec(select(Holiday)).all()) == 1


def test_copy_is_company_scoped_and_marks_stale_months(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db, company_code="C-COPY-1")
    other_company = create_company(db, company_code="C-COPY-2")
    create_holiday(
        db,
        company_id=company.id,
        holiday_date=date(2025, 9, 25),
        name="本公司",
    )
    create_holiday(
        db,
        company_id=other_company.id,
        holiday_date=date(2025, 9, 26),
        name="其他公司",
    )
    month = create_attendance_month(
        db,
        company_id=company.id,
        status=AttendanceMonthStatus.CALCULATED,
        is_stale=False,
    )

    response = client.post(
        COPY_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
        json={"source_year": 2025, "target_year": 2026},
    )
    assert response.status_code == 200, response.text

    copied = db.exec(
        select(Holiday).where(
            Holiday.company_id == company.id, Holiday.date >= date(2026, 1, 1)
        )
    ).all()
    assert [holiday.date for holiday in copied] == [date(2026, 9, 25)]
    other_copied = db.exec(
        select(Holiday).where(
            Holiday.company_id == other_company.id, Holiday.date >= date(2026, 1, 1)
        )
    ).all()
    assert other_copied == []

    db.refresh(month)
    assert month.is_stale is True


def test_copy_requests_require_a_query_company_id(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.post(
        COPY_URL,
        headers=superuser_token_headers,
        json={"source_year": 2025, "target_year": 2026},
    )
    assert response.status_code == 422, response.text
