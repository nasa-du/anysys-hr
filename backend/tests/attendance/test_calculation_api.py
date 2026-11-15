"""Calculation trigger, persistence, and concurrency (spec 7.1, 7.12, 8.7).

The HTTP seam is ``POST /attendance/months/{month}/calculate``; the service
seam is ``calculate_month``. Tests assert persisted results and error codes
rather than internal calls.
"""

import hashlib
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, time
from decimal import Decimal
from threading import Event

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, select

from app.core.config import settings
from app.core.db import engine
from app.enums import (
    AttendanceMonthStatus,
    CalcRunStatus,
    DayStatus,
    EmployeeStatus,
    ImportBatchStatus,
    ImportDataType,
    ResultRosterState,
)
from app.models import (
    AttendanceDayResult,
    AttendanceDayShiftResult,
    AttendanceMonth,
    AttendanceMonthSummary,
    CalcRun,
)
from app.schemas_attendance.core import AttendanceRuleUpdate
from app.services.attendance import month_state
from app.services.attendance import months as month_service
from app.services.attendance.rules import update_company_rule
from tests.utils.attendance_factories import (
    create_attendance_day_result,
    create_attendance_month,
    create_attendance_month_summary,
    create_attendance_rule,
    create_calc_run,
    create_holiday,
    create_import_batch,
    create_oa_trip,
    create_punch_record,
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
from tests.utils.user import create_random_user

CALCULATE_URL = f"{settings.API_V1_STR}/attendance/months/2026-09/calculate"
MONTH_START = date(2026, 9, 1)


def error_detail(response: object) -> dict[str, object]:
    body = response.json()  # type: ignore[attr-defined]
    assert isinstance(body["detail"], dict), body
    return body["detail"]


def _company_with_employee(
    db: Session,
) -> tuple[uuid.UUID, uuid.UUID]:
    company = create_company(db)
    department = create_department(db, company=company, dept_name="生产部")
    position = create_position(db, company=company, dept=department)
    employee = create_employee(
        db,
        dept=department,
        position=position,
        employee_no="E101",
        name="冯芷茵",
        hire_date=date(2020, 4, 11),
    )
    return company.id, employee.id


def test_calculate_month_persists_results_and_calc_run(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company_id, employee_id = _company_with_employee(db)
    shift = create_shift(
        db,
        company_id=company_id,
        shift_code="ADM",
        shift_name="行政班",
        start_time=time(8, 30),
        end_time=time(17, 30),
        rest_minutes=60,
    )
    create_attendance_rule(db, company_id=company_id)
    create_holiday(db, company_id=company_id)
    create_roster_entry(
        db,
        company_id=company_id,
        employee_id=employee_id,
        work_date=MONTH_START,
        shifts=[shift],
    )
    operator = create_random_user(db)
    batch = create_import_batch(
        db,
        company_id=company_id,
        operator_id=operator.id,
        data_type=ImportDataType.PUNCH,
        month=MONTH_START,
        status=ImportBatchStatus.COMMITTED,
        committed_at=datetime(2026, 9, 28, tzinfo=UTC),
    )
    create_punch_record(
        db,
        company_id=company_id,
        batch_id=batch.id,
        employee_id=employee_id,
        attendance_date=MONTH_START,
        punch_time=datetime.fromisoformat("2026-09-01T08:22:00+08:00"),
        source_row_number=2,
    )
    create_punch_record(
        db,
        company_id=company_id,
        batch_id=batch.id,
        employee_id=employee_id,
        attendance_date=MONTH_START,
        punch_time=datetime.fromisoformat("2026-09-01T17:30:00+08:00"),
        source_row_number=3,
    )

    response = client.post(
        CALCULATE_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company_id)},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "success"
    assert body["trigger"] == "initial"
    assert body["calc_version"] == "attendance-calc-v1"
    assert len(body["rules_version"]) == 64
    assert len(body["roster_version"]) == 64
    assert body["input_batches"]["punch"]["id"] == str(batch.id)
    assert body["input_batches"]["trip"] is None
    assert body["summary"]["employees_total"] == 1
    assert body["summary"]["employees_calculated"] == 1
    assert body["summary"]["days_total"] == 1
    assert body["summary"]["days_by_status"] == {"normal": 1}

    db.expire_all()
    month = db.exec(
        select(AttendanceMonth).where(col(AttendanceMonth.company_id) == company_id)
    ).one()
    assert month.status.value == "calculated"
    assert month.is_stale is False
    assert month.calculated_at is not None

    day = db.exec(
        select(AttendanceDayResult).where(
            col(AttendanceDayResult.employee_id) == employee_id
        )
    ).one()
    assert day.day_type.value == "workday"
    assert day.roster_state == ResultRosterState.WORK
    assert day.day_status == DayStatus.NORMAL
    assert day.scheduled_minutes == 480
    assert day.worked_minutes == 488
    assert day.is_adjusted is False
    assert day.adjustment_id is None

    shift_result = db.exec(
        select(AttendanceDayShiftResult).where(
            col(AttendanceDayShiftResult.day_result_id) == day.id
        )
    ).one()
    assert shift_result.shift_id == shift.id
    assert shift_result.shift_code == "ADM"
    assert shift_result.worked_minutes == 488

    summary = db.exec(
        select(AttendanceMonthSummary).where(
            col(AttendanceMonthSummary.employee_id) == employee_id
        )
    ).one()
    assert summary.weekday_full == Decimal("1.0")
    assert summary.worked_minutes == 488
    assert summary.attendance_deduct == Decimal("0.00")
    assert summary.rules_version == body["rules_version"]


def test_calculate_month_requires_authentication(client: TestClient) -> None:
    response = client.post(CALCULATE_URL, params={"company_id": str(uuid.uuid7())})
    assert response.status_code == 401
    assert response.json() == {"detail": "未登录或登录状态已过期"}


def test_calculate_month_rejects_an_unknown_company(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.post(
        CALCULATE_URL,
        headers=superuser_token_headers,
        params={"company_id": str(uuid.uuid7())},
    )
    assert response.status_code == 404
    assert error_detail(response)["code"] == "not_found"


def test_calculate_month_rejects_an_invalid_month(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    response = client.post(
        f"{settings.API_V1_STR}/attendance/months/2026-13/calculate",
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (AttendanceMonthStatus.CONFIRMED, "month_confirmed"),
        (AttendanceMonthStatus.LOCKED, "month_locked"),
    ],
)
def test_calculate_month_blocks_confirmed_and_locked_months(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    status: AttendanceMonthStatus,
    code: str,
) -> None:
    company = create_company(db)
    create_attendance_month(db, company_id=company.id, status=status)

    response = client.post(
        CALCULATE_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )

    assert response.status_code == 409
    assert error_detail(response)["code"] == code
    db.expire_all()
    month = db.exec(
        select(AttendanceMonth).where(col(AttendanceMonth.company_id) == company.id)
    ).one()
    assert month.status == status
    assert db.exec(select(CalcRun)).all() == []


def test_calculate_month_scopes_employees_and_generates_data_days(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    department = create_department(db, company=company)
    position = create_position(db, company=company, dept=department)
    worked_employee = create_employee(
        db,
        dept=department,
        position=position,
        employee_no="E101",
        name="冯芷茵",
        hire_date=date(2020, 4, 11),
    )
    idle_employee = create_employee(
        db,
        dept=department,
        position=position,
        employee_no="E102",
        name="刘衍英",
        hire_date=date(2018, 9, 3),
    )
    shift = create_shift(db, company_id=company.id, shift_code="ADM")
    create_attendance_rule(db, company_id=company.id)
    create_roster_entry(
        db,
        company_id=company.id,
        employee_id=worked_employee.id,
        work_date=MONTH_START,
        shifts=[shift],
    )
    operator = create_random_user(db)
    batch = create_import_batch(
        db,
        company_id=company.id,
        operator_id=operator.id,
        data_type=ImportDataType.PUNCH,
        month=MONTH_START,
        status=ImportBatchStatus.COMMITTED,
    )
    for row_number, punch_time in (
        (2, "2026-09-01T08:25:00+08:00"),
        (3, "2026-09-01T17:30:00+08:00"),
        (4, "2026-09-03T08:20:00+08:00"),
        (5, "2026-09-03T17:30:00+08:00"),
    ):
        create_punch_record(
            db,
            company_id=company.id,
            batch_id=batch.id,
            employee_id=worked_employee.id,
            attendance_date=date.fromisoformat(punch_time[:10]),
            punch_time=datetime.fromisoformat(punch_time),
            source_row_number=row_number,
        )

    response = client.post(
        CALCULATE_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )

    assert response.status_code == 200, response.text
    assert response.json()["summary"] == {
        "employees_total": 2,
        "employees_calculated": 1,
        "employees_skipped": 1,
        "skipped_reasons": {"no_data": 1},
        "days_total": 2,
        "days_by_status": {"normal": 1, "unscheduled_attendance": 1},
        "flag_counts": {"unscheduled_attendance": 1},
        "late_count": 0,
        "late_minutes": 0,
        "early_count": 0,
        "early_minutes": 0,
        "missing_punch_count": 0,
        "absent_days": 0,
        "ot_weekday_minutes": 0,
        "ot_weekend_minutes": 0,
        "ot_holiday_minutes": 0,
        "comp_offset_unused_minutes": 0,
        "attendance_deduct": "0.00",
    }

    db.expire_all()
    results = db.exec(
        select(AttendanceDayResult).order_by(col(AttendanceDayResult.work_date))
    ).all()
    assert [result.work_date for result in results] == [
        date(2026, 9, 1),
        date(2026, 9, 3),
    ]
    assert results[0].roster_state == ResultRosterState.WORK
    assert results[1].roster_state == ResultRosterState.UNSCHEDULED
    assert results[1].day_status == DayStatus.UNSCHEDULED_ATTENDANCE
    assert (
        db.exec(
            select(AttendanceMonthSummary).where(
                col(AttendanceMonthSummary.employee_id) == idle_employee.id
            )
        ).first()
        is None
    )


def test_calculate_month_respects_inclusive_employment_bounds(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    department = create_department(db, company=company)
    position = create_position(db, company=company, dept=department)
    new_hire = create_employee(
        db,
        dept=department,
        position=position,
        employee_no="E113",
        name="李娜",
        hire_date=date(2026, 9, 15),
    )
    leaver = create_employee(
        db,
        dept=department,
        position=position,
        employee_no="E112",
        name="王强",
        hire_date=date(2018, 1, 1),
        status=EmployeeStatus.RESIGNED,
        resign_date=date(2026, 9, 10),
    )
    shift = create_shift(db, company_id=company.id, shift_code="ADM")
    create_attendance_rule(db, company_id=company.id)
    for employee_id, work_date in (
        (new_hire.id, date(2026, 9, 1)),
        (new_hire.id, date(2026, 9, 15)),
        (leaver.id, date(2026, 9, 10)),
        (leaver.id, date(2026, 9, 11)),
    ):
        create_roster_entry(
            db,
            company_id=company.id,
            employee_id=employee_id,
            work_date=work_date,
            shifts=[shift],
        )

    response = client.post(
        CALCULATE_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )

    assert response.status_code == 200, response.text
    db.expire_all()
    results = db.exec(
        select(AttendanceDayResult).order_by(
            col(AttendanceDayResult.employee_id), col(AttendanceDayResult.work_date)
        )
    ).all()
    assert [(row.employee_id, row.work_date) for row in results] == [
        (new_hire.id, date(2026, 9, 15)),
        (leaver.id, date(2026, 9, 10)),
    ]


def test_calculate_month_ignores_non_committed_batches(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    department = create_department(db, company=company)
    position = create_position(db, company=company, dept=department)
    employee = create_employee(
        db, dept=department, position=position, hire_date=date(2020, 1, 1)
    )
    shift = create_shift(db, company_id=company.id, shift_code="ADM")
    create_attendance_rule(db, company_id=company.id)
    create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=MONTH_START,
        shifts=[shift],
    )
    operator = create_random_user(db)
    preview_batch = create_import_batch(
        db,
        company_id=company.id,
        operator_id=operator.id,
        data_type=ImportDataType.PUNCH,
        month=MONTH_START,
        status=ImportBatchStatus.PREVIEW,
    )
    for row_number, clock in ((2, "08:25"), (3, "17:30")):
        create_punch_record(
            db,
            company_id=company.id,
            batch_id=preview_batch.id,
            employee_id=employee.id,
            attendance_date=MONTH_START,
            punch_time=datetime.fromisoformat(f"2026-09-01T{clock}:00+08:00"),
            source_row_number=row_number,
        )

    response = client.post(
        CALCULATE_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )

    assert response.status_code == 200, response.text
    assert response.json()["input_batches"] == {
        "punch": None,
        "trip": None,
        "ot": None,
        "leave": None,
    }
    db.expire_all()
    day = db.exec(select(AttendanceDayResult)).one()
    assert day.day_status == DayStatus.ABSENT
    assert day.worked_minutes == 0


def test_calculate_month_uses_roster_snapshots_and_never_resolves_plans(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    department = create_department(db, company=company)
    position = create_position(db, company=company, dept=department)
    employee = create_employee(
        db, dept=department, position=position, hire_date=date(2020, 1, 1)
    )
    shift = create_shift(
        db,
        company_id=company.id,
        shift_code="ADM",
        start_time=time(8, 30),
        end_time=time(17, 30),
        rest_minutes=60,
    )
    create_attendance_rule(db, company_id=company.id)
    create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=MONTH_START,
        shifts=[shift],
    )
    # Neither the edited shift template nor an enabled plan may change the
    # frozen roster snapshot (ADR-0004).
    shift.start_time = time(9, 0)
    shift.end_time = time(18, 0)
    db.add(shift)
    create_schedule_plan(
        db,
        company_id=company.id,
        month=MONTH_START,
        days=[(5, 0, shift.id)],
    )
    db.commit()

    response = client.post(
        CALCULATE_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )

    assert response.status_code == 200, response.text
    db.expire_all()
    day = db.exec(select(AttendanceDayResult)).one()
    assert day.work_date == MONTH_START
    shift_result = db.exec(select(AttendanceDayShiftResult)).one()
    assert shift_result.start_time == time(8, 30)
    assert shift_result.end_time == time(17, 30)
    assert shift_result.scheduled_minutes == 480


def test_calculate_month_isolates_companies(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company_a = create_company(db, company_code="CA", company_name="荣新建设")
    company_b = create_company(db, company_code="CB", company_name="荣新科技")
    operator = create_random_user(db)

    def seed(company, employee_no: str):
        department = create_department(db, company=company)
        position = create_position(db, company=company, dept=department)
        employee = create_employee(
            db,
            dept=department,
            position=position,
            employee_no=employee_no,
            hire_date=date(2020, 1, 1),
        )
        shift = create_shift(db, company_id=company.id, shift_code=f"{employee_no}X")
        create_attendance_rule(db, company_id=company.id)
        create_roster_entry(
            db,
            company_id=company.id,
            employee_id=employee.id,
            work_date=MONTH_START,
            shifts=[shift],
        )
        batch = create_import_batch(
            db,
            company_id=company.id,
            operator_id=operator.id,
            data_type=ImportDataType.PUNCH,
            month=MONTH_START,
            status=ImportBatchStatus.COMMITTED,
        )
        for row_number, clock in ((2, "08:30"), (3, "17:30")):
            create_punch_record(
                db,
                company_id=company.id,
                batch_id=batch.id,
                employee_id=employee.id,
                attendance_date=MONTH_START,
                punch_time=datetime.fromisoformat(f"2026-09-01T{clock}:00+08:00"),
                source_row_number=row_number,
            )
        return employee

    employee_a = seed(company_a, "EA01")
    employee_b = seed(company_b, "EB01")

    response_a = client.post(
        CALCULATE_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company_a.id)},
    )
    response_b = client.post(
        CALCULATE_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company_b.id)},
    )

    assert response_a.status_code == 200, response_a.text
    assert response_b.status_code == 200, response_b.text
    assert response_a.json()["summary"]["employees_total"] == 1
    assert response_b.json()["summary"]["employees_total"] == 1
    db.expire_all()
    results_a = db.exec(
        select(AttendanceDayResult).where(
            col(AttendanceDayResult.company_id) == company_a.id
        )
    ).all()
    results_b = db.exec(
        select(AttendanceDayResult).where(
            col(AttendanceDayResult.company_id) == company_b.id
        )
    ).all()
    assert [result.employee_id for result in results_a] == [employee_a.id]
    assert [result.employee_id for result in results_b] == [employee_b.id]


def test_calculate_month_records_rule_holiday_and_batch_snapshots(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    department = create_department(db, company=company)
    position = create_position(db, company=company, dept=department)
    employee = create_employee(
        db, dept=department, position=position, hire_date=date(2020, 1, 1)
    )
    shift = create_shift(
        db,
        company_id=company.id,
        shift_code="ADM",
        start_time=time(8, 30),
        end_time=time(17, 30),
    )
    create_attendance_rule(
        db,
        company_id=company.id,
        late_grace_min=5,
        ot_threshold_min=30,
        absent_deduct_per_day=100,
    )
    create_holiday(
        db,
        company_id=company.id,
        holiday_date=date(2026, 9, 25),
        name="中秋节",
    )
    plan = create_schedule_plan(
        db,
        company_id=company.id,
        month=MONTH_START,
        rule_overrides={"late_grace_min": 0, "ot_threshold_min": 15},
    )
    create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=MONTH_START,
        plan_id=plan.id,
        shifts=[shift],
    )
    create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=date(2026, 9, 25),
        plan_id=plan.id,
        shifts=[shift],
    )
    operator = create_random_user(db)
    batches = {
        data_type: create_import_batch(
            db,
            company_id=company.id,
            operator_id=operator.id,
            data_type=data_type,
            month=MONTH_START,
            status=ImportBatchStatus.COMMITTED,
        )
        for data_type in ImportDataType
    }
    for row_number, clock in ((2, "08:33"), (3, "17:30")):
        create_punch_record(
            db,
            company_id=company.id,
            batch_id=batches[ImportDataType.PUNCH].id,
            employee_id=employee.id,
            attendance_date=MONTH_START,
            punch_time=datetime.fromisoformat(f"2026-09-01T{clock}:00+08:00"),
            source_row_number=row_number,
        )

    response = client.post(
        CALCULATE_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    snapshot = body["rules_snapshot"]
    assert snapshot["company_rule"]["late_grace_min"] == 5
    assert snapshot["company_rule"]["ot_threshold_min"] == 30
    assert snapshot["company_rule"]["absent_deduct_per_day"] == "100.00"
    assert snapshot["plan_overrides"] == [
        {
            "plan_id": str(plan.id),
            "overrides": {
                "punch_window_min": None,
                "late_cap_min": None,
                "early_cap_min": None,
                "ot_max_min": None,
                "late_grace_min": 0,
                "early_grace_min": None,
                "ot_threshold_min": 15,
                "absent_if_no_punch": None,
                "break_punch_required": None,
                "break_punch_tolerance_min": None,
                "absent_deduct_per_day": None,
                "late_deduct_per_occurrence": None,
                "early_deduct_per_occurrence": None,
                "missing_punch_deduct_per_occurrence": None,
            },
        }
    ]
    assert snapshot["holidays"] == [
        {"date": "2026-09-25", "name": "中秋节", "day_type": "holiday"}
    ]
    expected_hash = hashlib.sha256(
        json.dumps(
            snapshot,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    assert body["rules_version"] == expected_hash
    assert body["input_batches"] == {
        data_type.value: {
            "id": str(batch.id),
            "committed_at": None,
            "file_name": "fixture.csv",
            "source_rows": 0,
            "valid_records": 0,
        }
        for data_type, batch in batches.items()
    }

    db.expire_all()
    days = {row.work_date: row for row in db.exec(select(AttendanceDayResult)).all()}
    # The plan override (late_grace_min = 0) is the effective rule for the
    # entry; the company default (5) would make the 3 minutes disappear.
    assert days[date(2026, 9, 1)].late_minutes == 3
    assert days[date(2026, 9, 1)].day_status == DayStatus.LATE
    assert days[date(2026, 9, 25)].day_type.value == "holiday"


def test_calculate_month_failure_rolls_back_and_records_failed_run(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    company = create_company(db)
    department = create_department(db, company=company)
    position = create_position(db, company=company, dept=department)
    employee = create_employee(
        db, dept=department, position=position, hire_date=date(2020, 1, 1)
    )
    shift = create_shift(db, company_id=company.id, shift_code="ADM")
    create_attendance_rule(db, company_id=company.id)
    create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=MONTH_START,
        shifts=[shift],
    )
    month = create_attendance_month(
        db,
        company_id=company.id,
        status=AttendanceMonthStatus.CALCULATED,
        is_stale=False,
    )
    old_run = create_calc_run(db, attendance_month_id=month.id)
    old_day = create_attendance_day_result(
        db,
        company_id=company.id,
        attendance_month_id=month.id,
        calc_run_id=old_run.id,
        employee_id=employee.id,
        work_date=MONTH_START,
        worked_minutes=123,
    )
    old_summary = create_attendance_month_summary(
        db,
        company_id=company.id,
        attendance_month_id=month.id,
        calc_run_id=old_run.id,
        employee_id=employee.id,
        worked_minutes=123,
    )

    def boom(_inputs: object) -> None:
        raise RuntimeError("simulated kernel failure")

    monkeypatch.setattr(month_service, "run_month", boom)
    response = client.post(
        CALCULATE_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )

    assert response.status_code == 409, response.text
    detail = error_detail(response)
    assert detail["code"] == "calc_run_failed"
    assert "calc_run_id" in detail
    failed_run_id = uuid.UUID(str(detail["calc_run_id"]))

    db.expire_all()
    failed_run = db.get(CalcRun, failed_run_id)
    assert failed_run is not None
    assert failed_run.status == CalcRunStatus.FAILED
    assert failed_run.summary is None
    assert failed_run.error_code == "calc_run_failed"
    assert "simulated kernel failure" in (failed_run.error_message or "")
    assert failed_run.rules_snapshot["company_rule"]
    assert failed_run.input_batches == {
        "punch": None,
        "trip": None,
        "ot": None,
        "leave": None,
    }
    assert len(failed_run.rules_version) == 64
    assert len(failed_run.roster_version) == 64

    days = db.exec(select(AttendanceDayResult)).all()
    assert [day.id for day in days] == [old_day.id]
    assert days[0].worked_minutes == 123
    summaries = db.exec(select(AttendanceMonthSummary)).all()
    assert [summary.id for summary in summaries] == [old_summary.id]
    month_row = db.get(AttendanceMonth, month.id)
    assert month_row is not None
    assert month_row.status == AttendanceMonthStatus.CALCULATED
    assert month_row.is_stale is False
    assert len(db.exec(select(CalcRun)).all()) == 2


def test_failed_first_calculation_keeps_a_draft_month_and_failed_run(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    company = create_company(db)

    def boom(_inputs: object) -> None:
        raise RuntimeError("simulated first-run failure")

    monkeypatch.setattr(month_service, "run_month", boom)
    response = client.post(
        CALCULATE_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )

    assert response.status_code == 409, response.text
    detail = error_detail(response)
    assert detail["code"] == "calc_run_failed"
    db.expire_all()
    month = db.exec(
        select(AttendanceMonth).where(col(AttendanceMonth.company_id) == company.id)
    ).one()
    assert month.status == AttendanceMonthStatus.DRAFT
    assert month.is_stale is True
    assert month.calculated_at is None
    failed_run = db.get(CalcRun, uuid.UUID(str(detail["calc_run_id"])))
    assert failed_run is not None
    assert failed_run.attendance_month_id == month.id
    assert failed_run.status == CalcRunStatus.FAILED
    assert db.exec(select(AttendanceDayResult)).all() == []
    assert db.exec(select(AttendanceMonthSummary)).all() == []


def test_concurrent_calculation_returns_calc_in_progress(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    create_attendance_month(db, company_id=company.id)
    ready = Event()
    release = Event()

    def hold_calculation_lock() -> None:
        with Session(engine) as session:
            month_state.lock_month_for_calculation(session, company.id, MONTH_START)
            ready.set()
            assert release.wait(timeout=10)
            session.rollback()

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(hold_calculation_lock)
        try:
            assert ready.wait(timeout=10)
            response = client.post(
                CALCULATE_URL,
                headers=superuser_token_headers,
                params={"company_id": str(company.id)},
            )
        finally:
            release.set()
            future.result(timeout=10)

    assert response.status_code == 409, response.text
    assert error_detail(response)["code"] == "calc_in_progress"
    db.expire_all()
    assert db.exec(select(CalcRun)).all() == []


def _rows_without_audit(session: Session, model: object) -> list[dict[str, object]]:
    rows = session.exec(select(model)).all()  # type: ignore[arg-type]
    payloads = []
    for row in rows:
        payload = row.model_dump()
        for key in ("id", "calc_run_id", "day_result_id", "created_at", "updated_at"):
            payload.pop(key, None)
        payloads.append(payload)
    return sorted(payloads, key=lambda payload: repr(sorted(payload.items())))


def test_calculate_month_is_idempotent_and_creates_a_new_run(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    department = create_department(db, company=company)
    position = create_position(db, company=company, dept=department)
    employee = create_employee(
        db, dept=department, position=position, hire_date=date(2020, 1, 1)
    )
    shift = create_shift(db, company_id=company.id, shift_code="ADM")
    create_attendance_rule(db, company_id=company.id)
    create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=MONTH_START,
        shifts=[shift],
    )
    operator = create_random_user(db)
    batch = create_import_batch(
        db,
        company_id=company.id,
        operator_id=operator.id,
        data_type=ImportDataType.PUNCH,
        month=MONTH_START,
        status=ImportBatchStatus.COMMITTED,
    )
    for row_number, clock in ((2, "08:25"), (3, "17:40")):
        create_punch_record(
            db,
            company_id=company.id,
            batch_id=batch.id,
            employee_id=employee.id,
            attendance_date=MONTH_START,
            punch_time=datetime.fromisoformat(f"2026-09-01T{clock}:00+08:00"),
            source_row_number=row_number,
        )

    first = client.post(
        CALCULATE_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )
    assert first.status_code == 200, first.text
    db.expire_all()
    first_days = _rows_without_audit(db, AttendanceDayResult)
    first_shifts = _rows_without_audit(db, AttendanceDayShiftResult)
    first_summaries = _rows_without_audit(db, AttendanceMonthSummary)

    second = client.post(
        CALCULATE_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )
    assert second.status_code == 200, second.text

    assert first.json()["id"] != second.json()["id"]
    assert first.json()["trigger"] == "initial"
    assert second.json()["trigger"] == "manual"
    assert first.json()["summary"] == second.json()["summary"]
    assert first.json()["rules_version"] == second.json()["rules_version"]
    assert first.json()["roster_version"] == second.json()["roster_version"]
    db.expire_all()
    assert _rows_without_audit(db, AttendanceDayResult) == first_days
    assert _rows_without_audit(db, AttendanceDayShiftResult) == first_shifts
    assert _rows_without_audit(db, AttendanceMonthSummary) == first_summaries
    assert len(db.exec(select(CalcRun)).all()) == 2


def test_rule_change_marks_stale_without_recalculating(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    department = create_department(db, company=company)
    position = create_position(db, company=company, dept=department)
    employee = create_employee(
        db, dept=department, position=position, hire_date=date(2020, 1, 1)
    )
    shift = create_shift(db, company_id=company.id, shift_code="ADM")
    create_attendance_rule(db, company_id=company.id, late_grace_min=5)
    create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=MONTH_START,
        shifts=[shift],
    )
    operator = create_random_user(db)
    batch = create_import_batch(
        db,
        company_id=company.id,
        operator_id=operator.id,
        data_type=ImportDataType.PUNCH,
        month=MONTH_START,
        status=ImportBatchStatus.COMMITTED,
    )
    for row_number, clock in ((2, "08:33"), (3, "17:30")):
        create_punch_record(
            db,
            company_id=company.id,
            batch_id=batch.id,
            employee_id=employee.id,
            attendance_date=MONTH_START,
            punch_time=datetime.fromisoformat(f"2026-09-01T{clock}:00+08:00"),
            source_row_number=row_number,
        )

    calculated = client.post(
        CALCULATE_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )
    assert calculated.status_code == 200, calculated.text
    db.expire_all()
    day_before = _rows_without_audit(db, AttendanceDayResult)
    runs_before = len(db.exec(select(CalcRun)).all())

    update_company_rule(db, company.id, AttendanceRuleUpdate(late_grace_min=0))

    db.expire_all()
    month = db.exec(
        select(AttendanceMonth).where(col(AttendanceMonth.company_id) == company.id)
    ).one()
    assert month.is_stale is True
    assert month.status == AttendanceMonthStatus.CALCULATED
    assert len(db.exec(select(CalcRun)).all()) == runs_before
    assert _rows_without_audit(db, AttendanceDayResult) == day_before

    recalculated = client.post(
        CALCULATE_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )
    assert recalculated.status_code == 200, recalculated.text
    db.expire_all()
    month = db.exec(
        select(AttendanceMonth).where(col(AttendanceMonth.company_id) == company.id)
    ).one()
    assert month.is_stale is False
    assert len(db.exec(select(CalcRun)).all()) == runs_before + 1
    day = db.exec(select(AttendanceDayResult)).one()
    assert day.late_minutes == 3
    assert day.day_status == DayStatus.LATE


def test_calculate_month_with_no_data_persists_an_empty_successful_run(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)

    response = client.post(
        CALCULATE_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "success"
    assert body["summary"]["employees_total"] == 0
    assert body["summary"]["days_total"] == 0
    assert body["summary"]["attendance_deduct"] == "0.00"
    db.expire_all()
    month = db.exec(
        select(AttendanceMonth).where(col(AttendanceMonth.company_id) == company.id)
    ).one()
    assert month.status == AttendanceMonthStatus.CALCULATED
    assert month.is_stale is False
    assert db.exec(select(AttendanceDayResult)).all() == []
    assert db.exec(select(AttendanceMonthSummary)).all() == []


def test_calculate_month_applies_committed_trips(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    department = create_department(db, company=company)
    position = create_position(db, company=company, dept=department)
    employee = create_employee(
        db, dept=department, position=position, hire_date=date(2020, 1, 1)
    )
    shift = create_shift(db, company_id=company.id, shift_code="ADM")
    create_attendance_rule(db, company_id=company.id)
    create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=MONTH_START,
        shifts=[shift],
    )
    operator = create_random_user(db)
    batch = create_import_batch(
        db,
        company_id=company.id,
        operator_id=operator.id,
        data_type=ImportDataType.TRIP,
        month=MONTH_START,
        status=ImportBatchStatus.COMMITTED,
    )
    create_oa_trip(
        db,
        company_id=company.id,
        batch_id=batch.id,
        employee_id=employee.id,
        approval_no="AP-001",
        application_type_raw="出差",
        start_at=datetime.fromisoformat("2026-09-01T08:30:00+08:00"),
        end_at=datetime.fromisoformat("2026-09-01T12:00:00+08:00"),
    )

    response = client.post(
        CALCULATE_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )

    assert response.status_code == 200, response.text
    assert response.json()["input_batches"]["trip"]["id"] == str(batch.id)
    db.expire_all()
    day = db.exec(select(AttendanceDayResult)).one()
    assert day.day_status == DayStatus.TRIP_BUSINESS
    assert day.trip_kind is not None
    assert day.trip_kind.value == "business"
    # Interval overlap, not the declared duration: 210 of 540 minutes.
    assert day.trip_fraction == Decimal("0.4")
    assert day.attendance_fraction == Decimal("0.4")


def test_failure_after_result_writes_rolls_back_all_new_rows(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    company = create_company(db)
    department = create_department(db, company=company)
    position = create_position(db, company=company, dept=department)
    employee = create_employee(
        db, dept=department, position=position, hire_date=date(2020, 1, 1)
    )
    shift = create_shift(db, company_id=company.id, shift_code="ADM")
    create_attendance_rule(db, company_id=company.id)
    create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=MONTH_START,
        shifts=[shift],
    )
    month = create_attendance_month(
        db,
        company_id=company.id,
        status=AttendanceMonthStatus.CALCULATED,
        is_stale=False,
    )
    old_run = create_calc_run(db, attendance_month_id=month.id)
    old_day = create_attendance_day_result(
        db,
        company_id=company.id,
        attendance_month_id=month.id,
        calc_run_id=old_run.id,
        employee_id=employee.id,
        work_date=MONTH_START,
        worked_minutes=321,
    )

    real_replace = month_service.results.replace_month_results

    def replace_then_fail(*args: object, **kwargs: object) -> None:
        real_replace(*args, **kwargs)  # type: ignore[arg-type]
        raise RuntimeError("simulated persistence failure")

    monkeypatch.setattr(
        month_service.results, "replace_month_results", replace_then_fail
    )
    response = client.post(
        CALCULATE_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )

    assert response.status_code == 409, response.text
    assert error_detail(response)["code"] == "calc_run_failed"
    db.expire_all()
    days = db.exec(select(AttendanceDayResult)).all()
    assert [day.id for day in days] == [old_day.id]
    assert days[0].worked_minutes == 321
    assert db.exec(select(AttendanceDayShiftResult)).all() == []
    assert db.exec(select(AttendanceMonthSummary)).all() == []
    month_row = db.get(AttendanceMonth, month.id)
    assert month_row is not None
    assert month_row.status == AttendanceMonthStatus.CALCULATED
    assert month_row.is_stale is False


def test_failed_adapter_read_records_documented_default_snapshots(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    company = create_company(db)

    def broken_adapter(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("simulated adapter failure")

    monkeypatch.setattr(month_service.results, "build_month_inputs", broken_adapter)
    response = client.post(
        CALCULATE_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )

    assert response.status_code == 409, response.text
    detail = error_detail(response)
    failed_run = db.get(CalcRun, uuid.UUID(str(detail["calc_run_id"])))
    assert failed_run is not None
    assert failed_run.trigger.value == "initial"
    assert failed_run.summary is None
    assert failed_run.rules_snapshot["company_rule"]["punch_window_min"] == 120
    assert failed_run.rules_snapshot["plan_overrides"] == []
    assert failed_run.rules_snapshot["holidays"] == []
    assert failed_run.input_batches == {
        "punch": None,
        "trip": None,
        "ot": None,
        "leave": None,
    }


def test_calculate_month_accepts_non_contiguous_roster_shift_seq(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    from app.models import RosterEntryShift

    company = create_company(db)
    department = create_department(db, company=company)
    position = create_position(db, company=company, dept=department)
    employee = create_employee(
        db, dept=department, position=position, hire_date=date(2020, 1, 1)
    )
    morning = create_shift(
        db, company_id=company.id, shift_code="ADM", start_time=time(8, 30)
    )
    evening = create_shift(
        db, company_id=company.id, shift_code="EVE", start_time=time(14, 0)
    )
    create_attendance_rule(db, company_id=company.id)
    create_roster_entry(
        db,
        company_id=company.id,
        employee_id=employee.id,
        work_date=MONTH_START,
        shifts=[morning, evening],
    )
    stored_shifts = db.exec(
        select(RosterEntryShift).order_by(col(RosterEntryShift.seq))
    ).all()
    stored_shifts[0].seq = 100
    db.add(stored_shifts[0])
    db.flush()
    stored_shifts[1].seq = 3
    db.add(stored_shifts[1])
    db.flush()
    stored_shifts[0].seq = 1
    db.add(stored_shifts[0])
    db.commit()

    response = client.post(
        CALCULATE_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )

    assert response.status_code == 200, response.text
    db.expire_all()
    shift_results = db.exec(
        select(AttendanceDayShiftResult).order_by(col(AttendanceDayShiftResult.seq))
    ).all()
    assert [(row.seq, row.shift_code) for row in shift_results] == [
        (0, "ADM"),
        (1, "EVE"),
    ]
