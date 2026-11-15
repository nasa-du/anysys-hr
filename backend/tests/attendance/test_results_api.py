"""Result inspection queries (spec sections 4.9, 7.8, 7.9, 8.3.5, and 8.4).

The HTTP seam is ``/attendance/results``. Tests cover the four query
endpoints, the derived anomaly view, detail composition, filtering, display
enrichment, authentication, and cross-company isolation.
"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.enums import (
    AdjustmentStatus,
    AttendanceMonthStatus,
    DayStatus,
    DayType,
    ImportBatchStatus,
    ImportDataType,
    LeaveKind,
    ResultRosterState,
)
from tests.utils.attendance_factories import (
    create_attendance_adjustment,
    create_attendance_day_result,
    create_attendance_day_shift_result,
    create_attendance_month,
    create_attendance_month_summary,
    create_calc_run,
    create_holiday,
    create_import_batch,
    create_oa_leave,
    create_oa_overtime,
    create_oa_trip,
    create_punch_record,
    create_roster_entry,
    create_shift,
)
from tests.utils.factories import (
    create_company,
    create_department,
    create_employee,
    create_position,
)
from tests.utils.user import create_random_user
from tests.utils.utils import random_upper_code

DAYS_URL = f"{settings.API_V1_STR}/attendance/results/days/"
SUMMARY_URL = f"{settings.API_V1_STR}/attendance/results/summary/"
CALENDAR_URL = f"{settings.API_V1_STR}/attendance/results/calendar"
MONTH = "2026-09"
MONTH_START = date(2026, 9, 1)


def error_detail(response: Any) -> dict[str, Any]:
    body = response.json()
    assert isinstance(body["detail"], dict), body
    return body["detail"]


def _prefix(url: str) -> str:
    return f"{settings.API_V1_STR}{url}"


def _detail_url(employee_id: uuid.UUID, work_date: date) -> str:
    return _prefix(f"/attendance/results/days/{employee_id}/{work_date.isoformat()}")


class Setup:
    """One company with an employee, a shift, a month, and a calculation run."""

    def __init__(self, db: Session) -> None:
        self.company = create_company(db)
        self.department = create_department(
            db, company=self.company, dept_name="生产部"
        )
        self.position = create_position(db, company=self.company, dept=self.department)
        self.employee = create_employee(
            db,
            dept=self.department,
            position=self.position,
            employee_no=random_upper_code("E"),
            name="冯芷茵",
            hire_date=date(2020, 4, 11),
        )
        self.shift = create_shift(db, company_id=self.company.id)
        self.month = create_attendance_month(
            db,
            company_id=self.company.id,
            status=AttendanceMonthStatus.CALCULATED,
            is_stale=False,
        )
        self.calc_run = create_calc_run(
            db,
            attendance_month_id=self.month.id,
            started_at=datetime(2026, 9, 28, tzinfo=UTC),
            finished_at=datetime(2026, 9, 28, tzinfo=UTC),
        )
        self.operator = create_random_user(db)

    def day(
        self,
        db: Session,
        work_date: date,
        *,
        employee_id: uuid.UUID | None = None,
        day_status: DayStatus = DayStatus.NORMAL,
        day_flags: list[str] | None = None,
        **overrides: Any,
    ) -> Any:
        return create_attendance_day_result(
            db,
            company_id=self.company.id,
            attendance_month_id=self.month.id,
            calc_run_id=self.calc_run.id,
            employee_id=employee_id or self.employee.id,
            work_date=work_date,
            day_status=day_status,
            day_flags=day_flags or [],
            **overrides,
        )


@pytest.fixture
def setup(db: Session) -> Setup:
    return Setup(db)


def test_day_results_requires_authentication(client: TestClient) -> None:
    response = client.get(
        DAYS_URL,
        params={"company_id": str(uuid.uuid7()), "month": MONTH},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "未登录或登录状态已过期"}


def test_day_results_derives_abnormal_and_supports_filters(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    setup: Setup,
) -> None:
    setup.day(db, date(2026, 9, 1), day_flags=["break_punch_missing"])
    setup.day(db, date(2026, 9, 2), day_status=DayStatus.LATE, day_flags=["late"])
    setup.day(
        db,
        date(2026, 9, 3),
        day_flags=["leave_trip_conflict"],
        is_adjusted=True,
    )
    setup.day(
        db,
        date(2026, 9, 4),
        day_type=DayType.WEEKEND,
        roster_state=ResultRosterState.REST,
        day_status=DayStatus.REST,
    )

    def query(**params: Any) -> list[dict[str, Any]]:
        response = client.get(
            DAYS_URL,
            headers=superuser_token_headers,
            params={"company_id": str(setup.company.id), "month": MONTH, **params},
        )
        assert response.status_code == 200, response.text
        return response.json()["data"]

    all_rows = query()
    assert len(all_rows) == 4
    assert [row["work_date"] for row in all_rows] == [
        "2026-09-01",
        "2026-09-02",
        "2026-09-03",
        "2026-09-04",
    ]
    assert all(row["employee_name"] == "冯芷茵" for row in all_rows)
    assert all(row["employee_no"] == setup.employee.employee_no for row in all_rows)
    assert all(row["department_name"] == "生产部" for row in all_rows)
    assert [row["is_abnormal"] for row in all_rows] == [False, True, True, False]

    abnormal = query(is_abnormal="true")
    assert [row["work_date"] for row in abnormal] == ["2026-09-02", "2026-09-03"]
    normal = query(is_abnormal="false")
    assert [row["work_date"] for row in normal] == ["2026-09-01", "2026-09-04"]

    assert len(query(day_status="late")) == 1
    assert len(query(flag="leave_trip_conflict")) == 1
    assert [
        row["work_date"]
        for row in query(flag=["break_punch_missing", "leave_trip_conflict"])
    ] == ["2026-09-01", "2026-09-03"]
    assert len(query(has_adjustment="true")) == 1
    assert len(query(day_type="weekend")) == 1
    assert len(query(roster_state="rest")) == 1
    assert len(query(date_from="2026-09-02", date_to="2026-09-03")) == 2
    assert len(query(day_status=["late", "rest"])) == 2


def test_day_results_filter_by_employee_department_and_keyword(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    setup: Setup,
) -> None:
    other_department = create_department(db, company=setup.company, dept_name="财务部")
    other_position = create_position(db, company=setup.company, dept=other_department)
    other_employee = create_employee(
        db,
        dept=other_department,
        position=other_position,
        employee_no=random_upper_code("E"),
        name="刘衍英",
        hire_date=date(2020, 1, 1),
    )
    setup.day(db, date(2026, 9, 1))
    setup.day(db, date(2026, 9, 1), employee_id=other_employee.id)

    def query(**params: Any) -> list[dict[str, Any]]:
        response = client.get(
            DAYS_URL,
            headers=superuser_token_headers,
            params={"company_id": str(setup.company.id), "month": MONTH, **params},
        )
        assert response.status_code == 200, response.text
        return response.json()["data"]

    by_employee = query(employee_id=str(other_employee.id))
    assert [row["employee_no"] for row in by_employee] == [other_employee.employee_no]
    by_department = query(dept_id=str(setup.department.id))
    assert [row["employee_no"] for row in by_department] == [setup.employee.employee_no]
    by_keyword = query(keyword="衍英")
    assert [row["employee_no"] for row in by_keyword] == [other_employee.employee_no]
    by_no = query(keyword=setup.employee.employee_no)
    assert [row["employee_no"] for row in by_no] == [setup.employee.employee_no]

    unknown_department = client.get(
        DAYS_URL,
        headers=superuser_token_headers,
        params={
            "company_id": str(setup.company.id),
            "month": MONTH,
            "dept_id": str(uuid.uuid7()),
        },
    )
    assert unknown_department.status_code == 404
    assert error_detail(unknown_department)["code"] == "not_found"


def test_day_results_paginate_and_keep_fixed_sorting(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    setup: Setup,
) -> None:
    for day in range(1, 5):
        setup.day(db, date(2026, 9, day))

    first = client.get(
        DAYS_URL,
        headers=superuser_token_headers,
        params={
            "company_id": str(setup.company.id),
            "month": MONTH,
            "skip": 0,
            "limit": 2,
        },
    )
    second = client.get(
        DAYS_URL,
        headers=superuser_token_headers,
        params={
            "company_id": str(setup.company.id),
            "month": MONTH,
            "skip": 2,
            "limit": 2,
        },
    )

    assert first.status_code == 200
    assert first.json()["count"] == 4
    assert [row["work_date"] for row in first.json()["data"]] == [
        "2026-09-01",
        "2026-09-02",
    ]
    assert second.status_code == 200
    assert second.json()["count"] == 4
    assert [row["work_date"] for row in second.json()["data"]] == [
        "2026-09-03",
        "2026-09-04",
    ]


def test_day_results_are_isolated_by_company(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    setup: Setup,
) -> None:
    setup.day(db, date(2026, 9, 1))
    other = Setup(db)
    other.day(db, date(2026, 9, 1))

    response = client.get(
        DAYS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(setup.company.id), "month": MONTH},
    )
    assert response.status_code == 200
    employee_ids = {row["employee_id"] for row in response.json()["data"]}
    assert employee_ids == {str(setup.employee.id)}

    foreign_department = client.get(
        DAYS_URL,
        headers=superuser_token_headers,
        params={
            "company_id": str(setup.company.id),
            "month": MONTH,
            "dept_id": str(other.department.id),
        },
    )
    assert foreign_department.status_code == 404
    assert error_detail(foreign_department)["code"] == "not_found"


def test_day_detail_composes_roster_punches_oa_and_adjustments(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    setup: Setup,
) -> None:
    work_date = date(2026, 9, 7)
    create_holiday(
        db,
        company_id=setup.company.id,
        holiday_date=date(2026, 9, 25),
    )
    roster_entry = create_roster_entry(
        db,
        company_id=setup.company.id,
        employee_id=setup.employee.id,
        work_date=work_date,
        shifts=[setup.shift],
    )
    day = setup.day(
        db,
        work_date,
        day_status=DayStatus.LATE,
        day_flags=["late", "leave_trip_conflict"],
        late_minutes=12,
        late_count=1,
    )
    create_attendance_day_shift_result(
        db,
        company_id=setup.company.id,
        day_result_id=day.id,
        calc_run_id=setup.calc_run.id,
        employee_id=setup.employee.id,
        shift=setup.shift,
        work_date=work_date,
        punch_in_at=datetime(2026, 9, 7, 0, 42, tzinfo=UTC),
        punch_out_at=datetime(2026, 9, 7, 9, 30, tzinfo=UTC),
    )

    punch_batch = create_import_batch(
        db,
        company_id=setup.company.id,
        operator_id=setup.operator.id,
        data_type=ImportDataType.PUNCH,
        month=MONTH_START,
        status=ImportBatchStatus.COMMITTED,
        committed_at=datetime(2026, 9, 28, tzinfo=UTC),
    )
    create_punch_record(
        db,
        company_id=setup.company.id,
        batch_id=punch_batch.id,
        employee_id=setup.employee.id,
        attendance_date=work_date,
        punch_time=datetime(2026, 9, 7, 0, 42, tzinfo=UTC),
        source_row_number=2,
    )
    preview_batch = create_import_batch(
        db,
        company_id=setup.company.id,
        operator_id=setup.operator.id,
        data_type=ImportDataType.PUNCH,
        month=MONTH_START,
        status=ImportBatchStatus.PREVIEW,
    )
    create_punch_record(
        db,
        company_id=setup.company.id,
        batch_id=preview_batch.id,
        employee_id=setup.employee.id,
        attendance_date=work_date,
        punch_time=datetime(2026, 9, 7, 1, 0, tzinfo=UTC),
        source_row_number=3,
    )

    trip_batch = create_import_batch(
        db,
        company_id=setup.company.id,
        operator_id=setup.operator.id,
        data_type=ImportDataType.TRIP,
        month=MONTH_START,
        status=ImportBatchStatus.COMMITTED,
    )
    create_oa_trip(
        db,
        company_id=setup.company.id,
        batch_id=trip_batch.id,
        employee_id=setup.employee.id,
        start_at=datetime(2026, 9, 7, 1, 0, tzinfo=UTC),
        end_at=datetime(2026, 9, 7, 4, 0, tzinfo=UTC),
        approval_no="TRIP-1",
    )
    overtime_batch = create_import_batch(
        db,
        company_id=setup.company.id,
        operator_id=setup.operator.id,
        data_type=ImportDataType.OT,
        month=MONTH_START,
        status=ImportBatchStatus.COMMITTED,
    )
    create_oa_overtime(
        db,
        company_id=setup.company.id,
        batch_id=overtime_batch.id,
        employee_id=setup.employee.id,
        approval_no="OT-1",
        days=[(work_date, 90)],
    )
    leave_batch = create_import_batch(
        db,
        company_id=setup.company.id,
        operator_id=setup.operator.id,
        data_type=ImportDataType.LEAVE,
        month=MONTH_START,
        status=ImportBatchStatus.COMMITTED,
    )
    create_oa_leave(
        db,
        company_id=setup.company.id,
        batch_id=leave_batch.id,
        employee_id=setup.employee.id,
        approval_no="LEAVE-1",
        leave_kind=LeaveKind.PAID,
        days=Decimal("0.50"),
        rest_start_at=datetime(2026, 9, 7, 1, 0, tzinfo=UTC),
        rest_end_at=datetime(2026, 9, 7, 5, 0, tzinfo=UTC),
        rest_start_date=work_date,
        rest_end_date=work_date,
    )
    create_attendance_adjustment(
        db,
        company_id=setup.company.id,
        attendance_month_id=setup.month.id,
        calc_run_id=setup.calc_run.id,
        employee_id=setup.employee.id,
        adjusted_by=setup.operator.id,
        work_date=work_date,
        version=1,
        status=AdjustmentStatus.SUPERSEDED,
        reason="旧版本",
    )
    create_attendance_adjustment(
        db,
        company_id=setup.company.id,
        attendance_month_id=setup.month.id,
        calc_run_id=setup.calc_run.id,
        employee_id=setup.employee.id,
        adjusted_by=setup.operator.id,
        work_date=work_date,
        version=2,
        reason="核对补卡",
    )

    response = client.get(
        _detail_url(setup.employee.id, work_date),
        headers=superuser_token_headers,
        params={"company_id": str(setup.company.id)},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["day_result"]["work_date"] == "2026-09-07"
    assert body["day_result"]["is_abnormal"] is True
    assert body["day_result"]["employee_name"] == "冯芷茵"
    assert body["day_result"]["department_name"] == "生产部"
    assert len(body["shift_results"]) == 1
    assert body["shift_results"][0]["shift_code"] == setup.shift.shift_code
    assert body["roster_entry"]["id"] == str(roster_entry.id)
    assert body["roster_entry"]["state"] == "work"
    assert len(body["roster_entry"]["shifts"]) == 1
    assert len(body["punches"]) == 1
    assert body["punches"][0]["source_row_number"] == 2
    assert [trip["approval_no"] for trip in body["oa_trips"]] == ["TRIP-1"]
    assert [day["minutes"] for day in body["oa_overtime_days"]] == [90]
    assert [leave["approval_no"] for leave in body["oa_leaves"]] == ["LEAVE-1"]
    assert [item["version"] for item in body["adjustments"]] == [2, 1]
    assert body["adjustments"][0]["status"] == "active"
    assert body["adjustments"][0]["adjusted_by_name"] == (
        setup.operator.full_name or setup.operator.email
    )


def test_day_detail_returns_not_found_for_missing_or_foreign_day(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    setup: Setup,
) -> None:
    setup.day(db, date(2026, 9, 1))

    missing = client.get(
        _detail_url(setup.employee.id, date(2026, 9, 2)),
        headers=superuser_token_headers,
        params={"company_id": str(setup.company.id)},
    )
    assert missing.status_code == 404
    assert error_detail(missing)["code"] == "not_found"

    other = Setup(db)
    other.day(db, date(2026, 9, 1))
    foreign = client.get(
        _detail_url(other.employee.id, date(2026, 9, 1)),
        headers=superuser_token_headers,
        params={"company_id": str(setup.company.id)},
    )
    assert foreign.status_code == 404
    assert error_detail(foreign)["code"] == "not_found"

    unauthenticated = client.get(
        _detail_url(setup.employee.id, date(2026, 9, 1)),
        params={"company_id": str(setup.company.id)},
    )
    assert unauthenticated.status_code == 401


def test_month_summaries_filter_and_return_full_fields(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    setup: Setup,
) -> None:
    create_attendance_month_summary(
        db,
        company_id=setup.company.id,
        attendance_month_id=setup.month.id,
        calc_run_id=setup.calc_run.id,
        employee_id=setup.employee.id,
        weekday_full=Decimal("22.0"),
        weekday_attended=Decimal("21.5"),
        paid_leave_days=Decimal("0.5"),
        ot_weekday_minutes=120,
        ot_weekday_hours=Decimal("2.00"),
        late_count=1,
        late_minutes=12,
        missing_punch_count=1,
        absent_days=0,
        worked_minutes=10_200,
        attendance_deduct=Decimal("-30.00"),
    )
    other_department = create_department(db, company=setup.company, dept_name="财务部")
    other_position = create_position(db, company=setup.company, dept=other_department)
    other_employee = create_employee(
        db,
        dept=other_department,
        position=other_position,
        employee_no=random_upper_code("E"),
        name="刘衍英",
        hire_date=date(2020, 1, 1),
    )
    create_attendance_month_summary(
        db,
        company_id=setup.company.id,
        attendance_month_id=setup.month.id,
        calc_run_id=setup.calc_run.id,
        employee_id=other_employee.id,
    )

    def query(**params: Any) -> dict[str, Any]:
        response = client.get(
            SUMMARY_URL,
            headers=superuser_token_headers,
            params={"company_id": str(setup.company.id), "month": MONTH, **params},
        )
        assert response.status_code == 200, response.text
        return response.json()

    body = query()
    assert body["count"] == 2
    assert [row["employee_no"] for row in body["data"]] == sorted(
        [setup.employee.employee_no, other_employee.employee_no]
    )
    first = next(
        row for row in body["data"] if row["employee_id"] == str(setup.employee.id)
    )
    assert first["employee_name"] == "冯芷茵"
    assert first["department_name"] == "生产部"
    assert first["weekday_full"] == "22.0"
    assert first["weekday_attended"] == "21.5"
    assert first["ot_weekday_minutes"] == 120
    assert first["ot_weekday_hours"] == "2.00"
    assert first["late_count"] == 1
    assert first["attendance_deduct"] == "-30.00"
    assert first["calc_version"] == "attendance-calc-v1"

    assert query(employee_id=str(other_employee.id))["count"] == 1
    assert query(dept_id=str(setup.department.id))["count"] == 1
    assert query(keyword="衍英")["data"][0]["employee_no"] == (
        other_employee.employee_no
    )
    assert query(keyword="不存在")["count"] == 0


def test_month_summaries_uncalculated_month_is_empty(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    setup: Setup,
) -> None:
    response = client.get(
        SUMMARY_URL,
        headers=superuser_token_headers,
        params={"company_id": str(setup.company.id), "month": "2026-10"},
    )
    assert response.status_code == 200
    assert response.json() == {"data": [], "count": 0}


def test_month_summaries_require_authentication(client: TestClient) -> None:
    response = client.get(
        SUMMARY_URL,
        params={"company_id": str(uuid.uuid7()), "month": MONTH},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "未登录或登录状态已过期"}


def test_month_summaries_are_isolated_by_company(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    setup: Setup,
) -> None:
    create_attendance_month_summary(
        db,
        company_id=setup.company.id,
        attendance_month_id=setup.month.id,
        calc_run_id=setup.calc_run.id,
        employee_id=setup.employee.id,
    )
    other = Setup(db)
    create_attendance_month_summary(
        db,
        company_id=other.company.id,
        attendance_month_id=other.month.id,
        calc_run_id=other.calc_run.id,
        employee_id=other.employee.id,
    )

    response = client.get(
        SUMMARY_URL,
        headers=superuser_token_headers,
        params={"company_id": str(setup.company.id), "month": MONTH},
    )
    assert response.status_code == 200, response.text
    assert response.json()["count"] == 1
    assert response.json()["data"][0]["employee_id"] == str(setup.employee.id)

    foreign_department = client.get(
        SUMMARY_URL,
        headers=superuser_token_headers,
        params={
            "company_id": str(setup.company.id),
            "month": MONTH,
            "dept_id": str(other.department.id),
        },
    )
    assert foreign_department.status_code == 404
    assert error_detail(foreign_department)["code"] == "not_found"


def test_result_calendar_composes_summary_and_days(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    setup: Setup,
) -> None:
    setup.day(db, date(2026, 9, 1))
    setup.day(db, date(2026, 9, 2), day_status=DayStatus.ABSENT)
    create_attendance_month_summary(
        db,
        company_id=setup.company.id,
        attendance_month_id=setup.month.id,
        calc_run_id=setup.calc_run.id,
        employee_id=setup.employee.id,
        weekday_full=Decimal("22.0"),
        absent_days=1,
    )

    response = client.get(
        CALENDAR_URL,
        headers=superuser_token_headers,
        params={
            "company_id": str(setup.company.id),
            "month": MONTH,
            "employee_id": str(setup.employee.id),
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["employee"]["employee_no"] == setup.employee.employee_no
    assert body["employee"]["department_name"] == "生产部"
    assert body["month"] == MONTH
    assert body["summary"]["absent_days"] == 1
    assert [day["work_date"] for day in body["days"]] == [
        "2026-09-01",
        "2026-09-02",
    ]

    empty = client.get(
        CALENDAR_URL,
        headers=superuser_token_headers,
        params={
            "company_id": str(setup.company.id),
            "month": "2026-10",
            "employee_id": str(setup.employee.id),
        },
    )
    assert empty.status_code == 200
    assert empty.json()["summary"] is None
    assert empty.json()["days"] == []

    foreign = client.get(
        CALENDAR_URL,
        headers=superuser_token_headers,
        params={
            "company_id": str(setup.company.id),
            "month": MONTH,
            "employee_id": str(Setup(db).employee.id),
        },
    )
    assert foreign.status_code == 404
    assert error_detail(foreign)["code"] == "not_found"

    unauthenticated = client.get(
        CALENDAR_URL,
        params={
            "company_id": str(setup.company.id),
            "month": MONTH,
            "employee_id": str(setup.employee.id),
        },
    )
    assert unauthenticated.status_code == 401
