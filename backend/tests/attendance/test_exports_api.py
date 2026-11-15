"""CSV export contract: columns, formatting, escaping, BOM, and scope.

The HTTP seam is ``/attendance/months/{month}/exports``; tests assert the
14-column payroll file and the union detail file field by field (spec
sections 7.13 and 8.3.8).
"""

import csv
import io
import uuid
from datetime import date
from typing import Any

from fastapi.testclient import TestClient
from sqlmodel import Session, func, select

from app.core.config import settings
from app.enums import AttendanceMonthStatus, DayStatus
from app.models import AttendanceMonthSummary
from tests.utils.attendance_factories import (
    create_attendance_day_result,
    create_attendance_day_shift_result,
    create_attendance_month,
    create_attendance_month_summary,
    create_calc_run,
    create_shift,
)
from tests.utils.factories import (
    create_company,
    create_department,
    create_employee,
    create_position,
)

PAYROLL_COLUMNS = [
    "attendance_month",
    "company_name",
    "employee_no",
    "employee_name",
    "department_name",
    "weekday_full",
    "weekend_full",
    "weekday_attended",
    "weekend_attended",
    "paid_leave_days",
    "ot_weekday_hours",
    "ot_weekend_hours",
    "ot_holiday_hours",
    "attendance_deduct",
]
MONTH = "2026-09"
MONTH_START = date(2026, 9, 1)


def export_url(kind: str, month: str = MONTH) -> str:
    return f"{settings.API_V1_STR}/attendance/months/{month}/exports/{kind}"


def read_csv(response: Any) -> list[list[str]]:
    text = response.content.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(text)))


class Setup:
    def __init__(
        self,
        db: Session,
        *,
        company_name: str = "荣新矿业",
        department_name: str = "生产部",
        employee_no: str = "E101",
        employee_name: str = "张建国",
    ) -> None:
        self.company = create_company(db, company_name=company_name)
        self.department = create_department(
            db, company=self.company, dept_name=department_name
        )
        self.position = create_position(db, company=self.company, dept=self.department)
        self.employee = create_employee(
            db,
            dept=self.department,
            position=self.position,
            employee_no=employee_no,
            name=employee_name,
        )
        self.month = create_attendance_month(
            db,
            company_id=self.company.id,
            status=AttendanceMonthStatus.CALCULATED,
            is_stale=False,
        )
        self.calc_run = create_calc_run(db, attendance_month_id=self.month.id)
        self.shift = create_shift(db, company_id=self.company.id)

    def summary(self, db: Session, **overrides: Any) -> AttendanceMonthSummary:
        values: dict[str, Any] = {
            "weekday_full": 21,
            "weekend_full": 4.5,
            "weekday_attended": 20.5,
            "weekend_attended": 4,
            "paid_leave_days": 0.5,
            "ot_weekday_hours": "1.25",
            "ot_weekend_hours": "2.50",
            "ot_holiday_hours": "0.00",
            "attendance_deduct": "-20.00",
        }
        values.update(overrides)
        return create_attendance_month_summary(
            db,
            company_id=self.company.id,
            attendance_month_id=self.month.id,
            calc_run_id=self.calc_run.id,
            employee_id=self.employee.id,
            **values,
        )

    def day(self, db: Session, **overrides: Any):
        values: dict[str, Any] = {
            "work_date": date(2026, 9, 7),
            "day_status": DayStatus.LATE,
            "late_minutes": 7,
        }
        values.update(overrides)
        return create_attendance_day_result(
            db,
            company_id=self.company.id,
            attendance_month_id=self.month.id,
            calc_run_id=self.calc_run.id,
            employee_id=self.employee.id,
            **values,
        )


def test_exports_require_authentication(client: TestClient) -> None:
    for kind in ("payroll.csv", "detail.csv"):
        response = client.get(
            export_url(kind), params={"company_id": str(uuid.uuid7())}
        )
        assert response.status_code == 401
        assert response.json() == {"detail": "未登录或登录状态已过期"}


def test_exports_reject_an_unknown_company(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    for kind in ("payroll.csv", "detail.csv"):
        response = client.get(
            export_url(kind),
            headers=superuser_token_headers,
            params={"company_id": str(uuid.uuid7())},
        )
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "not_found"


def test_payroll_csv_has_fixed_columns_and_formatted_values(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    setup = Setup(db)
    setup.summary(db)

    response = client.get(
        export_url("payroll.csv"),
        headers=superuser_token_headers,
        params={"company_id": str(setup.company.id)},
    )

    assert response.status_code == 200, response.text
    assert response.content.startswith(b"\xef\xbb\xbf")
    assert response.headers["content-type"].startswith("text/csv")
    rows = read_csv(response)
    assert rows[0] == PAYROLL_COLUMNS
    assert rows[1] == [
        "2026-09",
        "荣新矿业",
        "E101",
        "张建国",
        "生产部",
        "21.0",
        "4.5",
        "20.5",
        "4.0",
        "0.5",
        "1.25",
        "2.50",
        "0.00",
        "-20.00",
    ]


def test_payroll_csv_escapes_formula_strings_but_not_numbers(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    setup = Setup(
        db,
        company_name="=荣新矿业",
        department_name="+生产部",
        employee_name="-张建国",
    )
    setup.summary(db, attendance_deduct="-30.00")

    response = client.get(
        export_url("payroll.csv"),
        headers=superuser_token_headers,
        params={"company_id": str(setup.company.id)},
    )

    rows = read_csv(response)
    assert rows[1][1] == "'=荣新矿业"
    assert rows[1][3] == "'-张建国"
    assert rows[1][4] == "'+生产部"
    assert rows[1][13] == "-30.00"


def test_empty_month_returns_a_header_only_csv(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    setup = Setup(db)
    setup.summary(db)

    existing_but_empty = client.get(
        export_url("payroll.csv", "2026-10"),
        headers=superuser_token_headers,
        params={"company_id": str(setup.company.id)},
    )
    assert existing_but_empty.status_code == 200
    assert existing_but_empty.content.startswith(b"\xef\xbb\xbf")
    assert read_csv(existing_but_empty) == [PAYROLL_COLUMNS]

    no_month_row = client.get(
        export_url("payroll.csv", "2026-11"),
        headers=superuser_token_headers,
        params={"company_id": str(setup.company.id)},
    )
    assert no_month_row.status_code == 200
    assert read_csv(no_month_row) == [PAYROLL_COLUMNS]

    detail = client.get(
        export_url("detail.csv", "2026-10"),
        headers=superuser_token_headers,
        params={"company_id": str(setup.company.id)},
    )
    assert detail.status_code == 200
    detail_rows = read_csv(detail)
    assert len(detail_rows) == 1
    assert detail_rows[0][0] == "record_type"


def test_detail_csv_unions_summary_day_and_shift_rows(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    setup = Setup(db)
    setup.summary(db)
    day = setup.day(db)
    create_attendance_day_shift_result(
        db,
        company_id=setup.company.id,
        day_result_id=day.id,
        calc_run_id=setup.calc_run.id,
        employee_id=setup.employee.id,
        shift=setup.shift,
        work_date=date(2026, 9, 7),
        late_minutes=7,
    )

    response = client.get(
        export_url("detail.csv"),
        headers=superuser_token_headers,
        params={"company_id": str(setup.company.id)},
    )

    assert response.status_code == 200, response.text
    assert response.content.startswith(b"\xef\xbb\xbf")
    rows = read_csv(response)
    header = rows[0]
    assert header[0] == "record_type"
    assert "day_status" in header
    assert "shift_code" in header
    records = [dict(zip(header, row, strict=True)) for row in rows[1:]]
    assert [record["record_type"] for record in records] == [
        "month_summary",
        "day_result",
        "shift_result",
    ]

    summary, day_row, shift_row = records
    assert summary["company_id"] == str(setup.company.id)
    assert summary["attendance_month_id"] == str(setup.month.id)
    assert summary["employee_no"] == "E101"
    assert summary["weekday_full"] == "21.0"
    assert summary["work_date"] == ""
    assert day_row["work_date"] == "2026-09-07"
    assert day_row["day_status"] == "late"
    assert day_row["day_late_minutes"] == "7"
    assert day_row["weekday_full"] == ""
    assert day_row["attendance_month_id"] == str(setup.month.id)
    assert shift_row["shift_day_result_id"] == str(day.id)
    assert shift_row["attendance_month_id"] == str(setup.month.id)
    assert shift_row["shift_code"] == setup.shift.shift_code
    assert shift_row["shift_late_minutes"] == "7"


def test_detail_csv_escapes_string_cells(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    setup = Setup(db)
    setup.summary(db)
    setup.day(db, note="@公式")

    response = client.get(
        export_url("detail.csv"),
        headers=superuser_token_headers,
        params={"company_id": str(setup.company.id)},
    )
    rows = read_csv(response)
    header = rows[0]
    day_row = dict(zip(header, rows[2], strict=True))
    assert day_row["day_note"] == "'@公式"


def test_exports_only_include_the_requested_company(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    setup = Setup(db)
    setup.summary(db)
    other = Setup(
        db,
        company_name="荣新物流",
        employee_no="E201",
        employee_name="李雷",
    )
    other.summary(db)

    response = client.get(
        export_url("payroll.csv"),
        headers=superuser_token_headers,
        params={"company_id": str(setup.company.id)},
    )
    rows = read_csv(response)
    assert [row[2] for row in rows[1:]] == ["E101"]

    count = db.exec(select(func.count()).select_from(AttendanceMonthSummary)).one()
    assert count == 2

    detail = client.get(
        export_url("detail.csv"),
        headers=superuser_token_headers,
        params={"company_id": str(setup.company.id)},
    )
    detail_rows = read_csv(detail)
    employee_index = detail_rows[0].index("employee_no")
    assert {row[employee_index] for row in detail_rows[1:]} == {"E101"}
