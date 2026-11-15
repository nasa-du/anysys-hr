"""Month closing transitions, snapshots, and calc-run queries.

The HTTP seam is ``/attendance/months`` plus the company-scoped
``/attendance/calc-runs`` and ``/attendance/snapshots`` resource routes. Tests
assert the state machine, snapshot contract, cross-company isolation, and
authentication (spec sections 5.6, 7.12, 8.3.6, and 8.7).
"""

import uuid
from datetime import UTC, date, datetime
from typing import Any

from fastapi.testclient import TestClient
from sqlmodel import Session, col, select

from app.core.config import settings
from app.enums import AttendanceMonthStatus, CalcRunStatus, DayStatus
from app.models import AttendanceMonthSnapshot, User
from tests.utils.attendance_factories import (
    create_attendance_adjustment,
    create_attendance_day_result,
    create_attendance_day_shift_result,
    create_attendance_month,
    create_attendance_month_summary,
    create_calc_run,
    create_month_snapshot,
    create_shift,
)
from tests.utils.factories import (
    create_company,
    create_department,
    create_employee,
    create_position,
)
from tests.utils.user import create_random_user

MONTHS_URL = f"{settings.API_V1_STR}/attendance/months/"
MONTH = "2026-09"


def error_detail(response: Any) -> dict[str, Any]:
    body = response.json()
    assert isinstance(body["detail"], dict), body
    return body["detail"]


def action_url(action: str, month: str = MONTH) -> str:
    return f"{MONTHS_URL}{month}/{action}"


def test_confirm_requires_a_calculated_non_stale_month(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    month = create_attendance_month(
        db,
        company_id=company.id,
        status=AttendanceMonthStatus.CALCULATED,
        is_stale=False,
        calculated_at=datetime(2026, 9, 28, 9, 0, tzinfo=UTC),
    )

    response = client.post(
        action_url("confirm"),
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == str(month.id)
    assert body["status"] == "confirmed"
    assert body["is_stale"] is False
    assert body["confirmed_at"] is not None
    assert body["calculated_at"] is not None


def test_confirm_rejects_illegal_month_states(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    draft = create_attendance_month(
        db, company_id=company.id, status=AttendanceMonthStatus.DRAFT
    )
    stale = create_attendance_month(
        db,
        company_id=company.id,
        month=date(2026, 10, 1),
        status=AttendanceMonthStatus.CALCULATED,
        is_stale=True,
    )
    confirmed = create_attendance_month(
        db,
        company_id=company.id,
        month=date(2026, 11, 1),
        status=AttendanceMonthStatus.CONFIRMED,
        is_stale=False,
    )
    locked = create_attendance_month(
        db,
        company_id=company.id,
        month=date(2026, 12, 1),
        status=AttendanceMonthStatus.LOCKED,
        is_stale=False,
    )

    def confirm(month: date) -> Any:
        return client.post(
            action_url("confirm", month.strftime("%Y-%m")),
            headers=superuser_token_headers,
            params={"company_id": str(company.id)},
        )

    missing = confirm(date(2026, 8, 1))
    assert missing.status_code == 409
    assert error_detail(missing)["code"] == "month_not_calculated"

    draft_response = confirm(draft.month)
    assert draft_response.status_code == 409
    assert error_detail(draft_response)["code"] == "month_not_calculated"

    stale_response = confirm(stale.month)
    assert stale_response.status_code == 409
    assert error_detail(stale_response)["code"] == "month_stale"

    confirmed_response = confirm(confirmed.month)
    assert confirmed_response.status_code == 409
    assert error_detail(confirmed_response)["code"] == "invalid_month_transition"

    locked_response = confirm(locked.month)
    assert locked_response.status_code == 409
    assert error_detail(locked_response)["code"] == "month_locked"

    unknown_company = client.post(
        action_url("confirm"),
        headers=superuser_token_headers,
        params={"company_id": str(uuid.uuid7())},
    )
    assert unknown_company.status_code == 404
    assert error_detail(unknown_company)["code"] == "not_found"

    unauthenticated = client.post(
        action_url("confirm"), params={"company_id": str(company.id)}
    )
    assert unauthenticated.status_code == 401


def test_unconfirm_returns_to_calculated_without_a_reason(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    confirmed = create_attendance_month(
        db,
        company_id=company.id,
        status=AttendanceMonthStatus.CONFIRMED,
        is_stale=False,
        calculated_at=datetime(2026, 9, 28, 9, 0, tzinfo=UTC),
        confirmed_at=datetime(2026, 9, 30, 10, 0, tzinfo=UTC),
    )
    calculated = create_attendance_month(
        db,
        company_id=company.id,
        month=date(2026, 10, 1),
        status=AttendanceMonthStatus.CALCULATED,
        is_stale=False,
    )

    response = client.post(
        action_url("unconfirm", confirmed.month.strftime("%Y-%m")),
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "calculated"
    assert body["is_stale"] is False
    assert body["confirmed_at"] is None
    assert body["calculated_at"] is not None

    not_confirmed = client.post(
        action_url("unconfirm", calculated.month.strftime("%Y-%m")),
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )
    assert not_confirmed.status_code == 409
    assert error_detail(not_confirmed)["code"] == "invalid_month_transition"

    unauthenticated = client.post(
        action_url("unconfirm"), params={"company_id": str(company.id)}
    )
    assert unauthenticated.status_code == 401


def test_lock_creates_an_immutable_snapshot(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db, company_name="荣新矿业")
    department = create_department(db, company=company, dept_name="生产部")
    position = create_position(db, company=company, dept=department)
    employee = create_employee(
        db,
        dept=department,
        position=position,
        employee_no="E101",
        name="张建国",
    )
    shift = create_shift(db, company_id=company.id, shift_code="DAY")
    month = create_attendance_month(
        db,
        company_id=company.id,
        status=AttendanceMonthStatus.CONFIRMED,
        is_stale=False,
        calculated_at=datetime(2026, 9, 28, 9, 0, tzinfo=UTC),
        confirmed_at=datetime(2026, 9, 30, 10, 0, tzinfo=UTC),
    )
    calc_run = create_calc_run(
        db,
        attendance_month_id=month.id,
        summary={"employees_calculated": 1, "days_total": 1},
        started_at=datetime(2026, 9, 28, 9, 0, tzinfo=UTC),
        finished_at=datetime(2026, 9, 28, 9, 1, tzinfo=UTC),
    )
    create_calc_run(
        db,
        attendance_month_id=month.id,
        status=CalcRunStatus.FAILED,
        error_code="calc_run_failed",
        error_message="模拟失败",
        started_at=datetime(2026, 9, 30, 9, 30, tzinfo=UTC),
        finished_at=datetime(2026, 9, 30, 9, 31, tzinfo=UTC),
    )
    day = create_attendance_day_result(
        db,
        company_id=company.id,
        attendance_month_id=month.id,
        calc_run_id=calc_run.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 1),
        day_status=DayStatus.LATE,
        late_minutes=7,
    )
    create_attendance_day_shift_result(
        db,
        company_id=company.id,
        day_result_id=day.id,
        calc_run_id=calc_run.id,
        employee_id=employee.id,
        shift=shift,
        work_date=date(2026, 9, 1),
        late_minutes=7,
    )
    create_attendance_month_summary(
        db,
        company_id=company.id,
        attendance_month_id=month.id,
        calc_run_id=calc_run.id,
        employee_id=employee.id,
        weekday_full=1,
        weekday_attended=1,
        attendance_deduct="-20.00",
    )
    operator = db.exec(
        select(User).where(col(User.email) == settings.FIRST_SUPERUSER)
    ).one()
    create_attendance_adjustment(
        db,
        company_id=company.id,
        attendance_month_id=month.id,
        calc_run_id=calc_run.id,
        employee_id=employee.id,
        adjusted_by=operator.id,
        work_date=date(2026, 9, 1),
        original_values={"late_minutes": 7},
        adjusted_values={"late_minutes": 0},
        reason="核实后不计迟到",
    )

    response = client.post(
        action_url("lock"),
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "locked"
    assert body["locked_at"] is not None
    assert body["confirmed_at"] is not None

    snapshots = db.exec(
        select(AttendanceMonthSnapshot).where(
            col(AttendanceMonthSnapshot.attendance_month_id) == month.id
        )
    ).all()
    assert len(snapshots) == 1
    snapshot = snapshots[0]
    assert snapshot.version == 1
    assert snapshot.calc_run_id == calc_run.id
    assert snapshot.locked_by == operator.id
    payload = snapshot.payload
    assert payload["schema_version"] == 1
    assert payload["company_id"] == str(company.id)
    assert payload["month"] == "2026-09"
    assert payload["locked_by"] == str(operator.id)
    assert payload["attendance_month"]["status"] == "locked"
    assert payload["calc_run"]["id"] == str(calc_run.id)
    assert payload["calc_run"]["summary"]["employees_calculated"] == 1
    assert payload["day_results"][0]["day_status"] == "late"
    assert payload["shift_results"][0]["late_minutes"] == 7
    assert payload["month_summaries"][0]["attendance_deduct"] == "-20.00"
    assert payload["adjustments"][0]["reason"] == "核实后不计迟到"
    assert payload["export"]["columns"][0] == "attendance_month"
    assert payload["export"]["rows"][0][2] == "E101"
    assert payload["export"]["rows"][0][5] == "1.0"
    assert payload["export"]["rows"][0][13] == "-20.00"


def test_lock_rejects_unconfirmed_months(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    draft = create_attendance_month(
        db, company_id=company.id, status=AttendanceMonthStatus.DRAFT
    )
    calculated = create_attendance_month(
        db,
        company_id=company.id,
        month=date(2026, 10, 1),
        status=AttendanceMonthStatus.CALCULATED,
        is_stale=False,
    )
    locked = create_attendance_month(
        db,
        company_id=company.id,
        month=date(2026, 11, 1),
        status=AttendanceMonthStatus.LOCKED,
        is_stale=False,
    )

    def lock(month: date) -> Any:
        return client.post(
            action_url("lock", month.strftime("%Y-%m")),
            headers=superuser_token_headers,
            params={"company_id": str(company.id)},
        )

    missing = lock(date(2026, 8, 1))
    assert missing.status_code == 409
    assert error_detail(missing)["code"] == "month_not_calculated"

    draft_response = lock(draft.month)
    assert draft_response.status_code == 409
    assert error_detail(draft_response)["code"] == "month_not_calculated"

    calculated_response = lock(calculated.month)
    assert calculated_response.status_code == 409
    assert error_detail(calculated_response)["code"] == "invalid_month_transition"

    locked_response = lock(locked.month)
    assert locked_response.status_code == 409
    assert error_detail(locked_response)["code"] == "month_locked"

    unauthenticated = client.post(
        action_url("lock"), params={"company_id": str(company.id)}
    )
    assert unauthenticated.status_code == 401


def test_unlock_requires_a_reason_and_keeps_snapshots(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    month = create_attendance_month(
        db,
        company_id=company.id,
        status=AttendanceMonthStatus.LOCKED,
        is_stale=False,
        calculated_at=datetime(2026, 9, 28, 9, 0, tzinfo=UTC),
        confirmed_at=datetime(2026, 9, 30, 10, 0, tzinfo=UTC),
        locked_at=datetime(2026, 9, 30, 11, 0, tzinfo=UTC),
    )
    calc_run = create_calc_run(db, attendance_month_id=month.id)
    operator = db.exec(
        select(User).where(col(User.email) == settings.FIRST_SUPERUSER)
    ).one()
    create_month_snapshot(
        db,
        attendance_month_id=month.id,
        calc_run_id=calc_run.id,
        locked_by=operator.id,
        company_id=company.id,
        locked_at=datetime(2026, 9, 30, 11, 0, tzinfo=UTC),
    )

    missing_reason = client.post(
        action_url("unlock"),
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
        json={},
    )
    assert missing_reason.status_code == 422

    blank_reason = client.post(
        action_url("unlock"),
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
        json={"reason": "   "},
    )
    assert blank_reason.status_code == 422
    assert "解锁理由" in blank_reason.text

    response = client.post(
        action_url("unlock"),
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
        json={"reason": "复核后重新打开"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "calculated"
    assert body["is_stale"] is True
    assert body["locked_at"] is None
    assert body["unlock_reason"] == "复核后重新打开"
    assert body["confirmed_at"] is None

    snapshots = db.exec(
        select(AttendanceMonthSnapshot).where(
            col(AttendanceMonthSnapshot.attendance_month_id) == month.id
        )
    ).all()
    assert len(snapshots) == 1

    confirm_again = client.post(
        action_url("confirm"),
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )
    assert confirm_again.status_code == 409
    assert error_detail(confirm_again)["code"] == "month_stale"

    not_locked = client.post(
        action_url("unlock"),
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
        json={"reason": "再次解锁"},
    )
    assert not_locked.status_code == 409
    assert error_detail(not_locked)["code"] == "invalid_month_transition"

    unauthenticated = client.post(
        action_url("unlock"),
        params={"company_id": str(company.id)},
        json={"reason": "未登录"},
    )
    assert unauthenticated.status_code == 401


def test_full_lock_lifecycle_appends_snapshot_versions(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    month = create_attendance_month(
        db,
        company_id=company.id,
        status=AttendanceMonthStatus.CALCULATED,
        is_stale=False,
        calculated_at=datetime(2026, 9, 28, 9, 0, tzinfo=UTC),
    )
    first_run = create_calc_run(db, attendance_month_id=month.id)
    calculate_url = action_url("calculate")
    params = {"company_id": str(company.id)}

    confirmed = client.post(
        action_url("confirm"), headers=superuser_token_headers, params=params
    )
    assert confirmed.status_code == 200, confirmed.text
    first_lock = client.post(
        action_url("lock"), headers=superuser_token_headers, params=params
    )
    assert first_lock.status_code == 200, first_lock.text
    assert first_lock.json()["status"] == "locked"

    blocked_calculation = client.post(
        calculate_url, headers=superuser_token_headers, params=params
    )
    assert blocked_calculation.status_code == 409
    assert error_detail(blocked_calculation)["code"] == "month_locked"

    blocked_unconfirm = client.post(
        action_url("unconfirm"), headers=superuser_token_headers, params=params
    )
    assert blocked_unconfirm.status_code == 409
    assert error_detail(blocked_unconfirm)["code"] == "month_locked"

    unlocked = client.post(
        action_url("unlock"),
        headers=superuser_token_headers,
        params=params,
        json={"reason": "复核后重新打开"},
    )
    assert unlocked.status_code == 200, unlocked.text
    assert unlocked.json()["status"] == "calculated"
    assert unlocked.json()["is_stale"] is True

    recalculated = client.post(
        calculate_url, headers=superuser_token_headers, params=params
    )
    assert recalculated.status_code == 200, recalculated.text
    assert recalculated.json()["status"] == "success"

    confirmed_again = client.post(
        action_url("confirm"), headers=superuser_token_headers, params=params
    )
    assert confirmed_again.status_code == 200, confirmed_again.text
    second_lock = client.post(
        action_url("lock"), headers=superuser_token_headers, params=params
    )
    assert second_lock.status_code == 200, second_lock.text

    snapshots = db.exec(
        select(AttendanceMonthSnapshot)
        .where(col(AttendanceMonthSnapshot.attendance_month_id) == month.id)
        .order_by(col(AttendanceMonthSnapshot.version).asc())
    ).all()
    assert [snapshot.version for snapshot in snapshots] == [1, 2]
    assert snapshots[0].calc_run_id == first_run.id
    assert snapshots[1].calc_run_id != first_run.id


def test_calc_run_detail_is_company_scoped(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    other_company = create_company(db)
    month = create_attendance_month(db, company_id=company.id)
    other_month = create_attendance_month(db, company_id=other_company.id)
    calc_run = create_calc_run(db, attendance_month_id=month.id)
    other_run = create_calc_run(db, attendance_month_id=other_month.id)

    response = client.get(
        f"{settings.API_V1_STR}/attendance/calc-runs/{calc_run.id}",
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )
    assert response.status_code == 200, response.text
    assert response.json()["id"] == str(calc_run.id)
    assert response.json()["attendance_month_id"] == str(month.id)

    cross_company = client.get(
        f"{settings.API_V1_STR}/attendance/calc-runs/{other_run.id}",
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )
    assert cross_company.status_code == 404
    assert error_detail(cross_company)["code"] == "not_found"

    missing = client.get(
        f"{settings.API_V1_STR}/attendance/calc-runs/{uuid.uuid7()}",
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )
    assert missing.status_code == 404

    unauthenticated = client.get(
        f"{settings.API_V1_STR}/attendance/calc-runs/{calc_run.id}",
        params={"company_id": str(company.id)},
    )
    assert unauthenticated.status_code == 401


def test_snapshot_queries_hide_payload_by_default(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    other_company = create_company(db)
    month = create_attendance_month(
        db,
        company_id=company.id,
        status=AttendanceMonthStatus.LOCKED,
        is_stale=False,
    )
    calc_run = create_calc_run(
        db, attendance_month_id=month.id, summary={"employees_calculated": 1}
    )
    operator = create_random_user(db)
    operator.full_name = "王会计"
    db.add(operator)
    db.commit()
    first = create_month_snapshot(
        db,
        attendance_month_id=month.id,
        calc_run_id=calc_run.id,
        locked_by=operator.id,
        company_id=company.id,
        version=1,
        locked_at=datetime(2026, 9, 30, 10, 0, tzinfo=UTC),
    )
    second = create_month_snapshot(
        db,
        attendance_month_id=month.id,
        calc_run_id=calc_run.id,
        locked_by=operator.id,
        company_id=company.id,
        version=2,
        locked_at=datetime(2026, 10, 1, 10, 0, tzinfo=UTC),
    )
    other_month = create_attendance_month(
        db, company_id=other_company.id, status=AttendanceMonthStatus.LOCKED
    )
    other_run = create_calc_run(db, attendance_month_id=other_month.id)
    other_snapshot = create_month_snapshot(
        db,
        attendance_month_id=other_month.id,
        calc_run_id=other_run.id,
        locked_by=operator.id,
        company_id=other_company.id,
    )

    listing = client.get(
        f"{MONTHS_URL}{MONTH}/snapshots/",
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )
    assert listing.status_code == 200, listing.text
    body = listing.json()
    assert body["count"] == 2
    assert [item["version"] for item in body["data"]] == [2, 1]
    assert all("payload" not in item for item in body["data"])
    assert body["data"][0]["locked_by_name"] == "王会计"
    assert body["data"][0]["summary"]["employees_calculated"] == 1
    assert body["data"][0]["id"] == str(second.id)
    assert body["data"][1]["id"] == str(first.id)

    detail = client.get(
        f"{settings.API_V1_STR}/attendance/snapshots/{second.id}",
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )
    assert detail.status_code == 200, detail.text
    assert "payload" not in detail.json()

    with_payload = client.get(
        f"{settings.API_V1_STR}/attendance/snapshots/{second.id}",
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "include_payload": True},
    )
    assert with_payload.status_code == 200, with_payload.text
    payload = with_payload.json()["payload"]
    assert payload["schema_version"] == 1
    assert payload["month"] == MONTH
    assert "export" in payload

    cross_company = client.get(
        f"{settings.API_V1_STR}/attendance/snapshots/{other_snapshot.id}",
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )
    assert cross_company.status_code == 404
    assert error_detail(cross_company)["code"] == "not_found"

    empty = client.get(
        f"{MONTHS_URL}2026-10/snapshots/",
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )
    assert empty.status_code == 200
    assert empty.json() == {"data": [], "count": 0}

    unauthenticated = client.get(
        f"{MONTHS_URL}{MONTH}/snapshots/", params={"company_id": str(company.id)}
    )
    assert unauthenticated.status_code == 401
