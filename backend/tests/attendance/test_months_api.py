"""Read-only attendance-month list used by the rules impact hint."""

import uuid
from datetime import date

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.enums import (
    AttendanceMonthStatus,
    DayStatus,
    ImportBatchStatus,
    ImportDataType,
)
from tests.utils.attendance_factories import (
    create_attendance_day_result,
    create_attendance_month,
    create_attendance_month_summary,
    create_calc_run,
    create_import_batch,
)
from tests.utils.factories import (
    create_company,
    create_department,
    create_employee,
    create_position,
)
from tests.utils.user import create_random_user

MONTHS_URL = f"{settings.API_V1_STR}/attendance/months/"


def error_detail(response: object) -> dict[str, object]:
    body = response.json()  # type: ignore[attr-defined]
    assert isinstance(body["detail"], dict), body
    return body["detail"]


def test_month_list_requires_authentication(client: TestClient) -> None:
    response = client.get(MONTHS_URL, params={"company_id": str(uuid.uuid7())})
    assert response.status_code == 401
    assert response.json() == {"detail": "未登录或登录状态已过期"}


def test_month_list_rejects_an_unknown_company(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(
        MONTHS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(uuid.uuid7())},
    )

    assert response.status_code == 404
    assert error_detail(response)["code"] == "not_found"


def test_month_list_returns_only_existing_months_with_counts_and_inputs(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    other_company = create_company(db)
    department = create_department(db, company=company)
    position = create_position(db, company=company)
    employee = create_employee(db, dept=department, position=position)
    operator = create_random_user(db)

    september = create_attendance_month(
        db,
        company_id=company.id,
        month=date(2026, 9, 1),
        status=AttendanceMonthStatus.DRAFT,
        is_stale=True,
    )
    october = create_attendance_month(
        db,
        company_id=company.id,
        month=date(2026, 10, 1),
        status=AttendanceMonthStatus.CALCULATED,
        is_stale=False,
    )
    create_attendance_month(
        db,
        company_id=other_company.id,
        month=date(2026, 9, 1),
        status=AttendanceMonthStatus.LOCKED,
    )

    calc_run = create_calc_run(db, attendance_month_id=september.id)
    create_import_batch(
        db,
        company_id=company.id,
        operator_id=operator.id,
        data_type=ImportDataType.PUNCH,
        month=date(2026, 9, 1),
        status=ImportBatchStatus.COMMITTED,
        committed_at=calc_run.started_at,
    )
    create_attendance_day_result(
        db,
        company_id=company.id,
        attendance_month_id=september.id,
        calc_run_id=calc_run.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 1),
        day_status=DayStatus.LATE,
    )
    normal = create_attendance_day_result(
        db,
        company_id=company.id,
        attendance_month_id=september.id,
        calc_run_id=calc_run.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 2),
        day_status=DayStatus.NORMAL,
    )
    flagged = create_attendance_day_result(
        db,
        company_id=company.id,
        attendance_month_id=september.id,
        calc_run_id=calc_run.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 3),
        day_status=DayStatus.NORMAL,
    )
    flagged.day_flags = ["leave_trip_conflict"]
    db.add(flagged)
    db.commit()
    assert normal.day_flags == []
    create_attendance_month_summary(
        db,
        company_id=company.id,
        attendance_month_id=september.id,
        calc_run_id=calc_run.id,
        employee_id=employee.id,
    )

    response = client.get(
        MONTHS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["count"] == 2
    assert [month["month"] for month in body["data"]] == ["2026-09", "2026-10"]
    assert all(month["exists"] for month in body["data"])

    september_body, october_body = body["data"]
    assert september_body["id"] == str(september.id)
    assert september_body["status"] == "draft"
    assert september_body["is_stale"] is True
    assert september_body["latest_calc_run"]["id"] == str(calc_run.id)
    assert september_body["active_batches"]["punch"]["id"] is not None
    assert september_body["active_batches"]["trip"] is None
    assert september_body["counts"] == {
        "employee_count": 1,
        "day_result_count": 3,
        "abnormal_day_count": 2,
        "month_summary_count": 1,
    }

    assert october_body["id"] == str(october.id)
    assert october_body["status"] == "calculated"
    assert october_body["latest_calc_run"] is None
    assert october_body["active_batches"] == {
        "punch": None,
        "trip": None,
        "ot": None,
        "leave": None,
    }
    assert october_body["counts"] == {
        "employee_count": 0,
        "day_result_count": 0,
        "abnormal_day_count": 0,
        "month_summary_count": 0,
    }

    filtered = client.get(
        MONTHS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "year": 2026},
    ).json()
    assert filtered["count"] == 2

    other = client.get(
        MONTHS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(other_company.id)},
    ).json()
    assert [month["month"] for month in other["data"]] == ["2026-09"]
    assert other["data"][0]["status"] == "locked"
