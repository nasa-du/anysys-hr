"""Manual adjustment versioning, optimistic locking, and recalculation replay.

The HTTP seam is ``/attendance/results/adjustments``; the recalculation seam is
``POST /attendance/months/{month}/calculate`` observed through the result and
adjustment queries. Tests assert the persisted contract, not service internals
(spec sections 4.9.4, 7.11, 8.3.5, and 8.5).
"""

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, time
from decimal import Decimal
from threading import Event
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlmodel import Session, col, select

from app.core.config import settings
from app.core.db import engine
from app.core.errors import DomainError
from app.enums import (
    AttendanceMonthStatus,
    DayStatus,
    ImportBatchStatus,
    ImportDataType,
)
from app.models import PunchRecord, RosterEntry, User
from app.schemas_attendance.results import AttendanceAdjustmentCreate
from app.services.attendance import adjustments as adjustment_service
from tests.utils.attendance_factories import (
    DEFAULT_RULE_VALUES,
    create_attendance_day_result,
    create_attendance_month,
    create_attendance_month_summary,
    create_attendance_rule,
    create_calc_run,
    create_import_batch,
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

ADJUSTMENTS_URL = f"{settings.API_V1_STR}/attendance/results/adjustments/"
SUMMARY_URL = f"{settings.API_V1_STR}/attendance/results/summary/"
CALCULATE_URL = f"{settings.API_V1_STR}/attendance/months/2026-09/calculate"
MONTH = "2026-09"
MONTH_START = date(2026, 9, 1)
WORK_DATE = date(2026, 9, 7)
SHANGHAI = ZoneInfo("Asia/Shanghai")


def error_detail(response: Any) -> dict[str, Any]:
    body = response.json()
    assert isinstance(body["detail"], dict), body
    return body["detail"]


def _detail_url(employee_id: uuid.UUID, work_date: date) -> str:
    return (
        f"{settings.API_V1_STR}/attendance/results/days/"
        f"{employee_id}/{work_date.isoformat()}"
    )


class Setup:
    """One company with an employee, a month, and a calculation run."""

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
        self.operator = create_random_user(db)
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

    def day(
        self,
        db: Session,
        work_date: date = WORK_DATE,
        *,
        employee_id: uuid.UUID | None = None,
        **overrides: Any,
    ):
        values: dict[str, Any] = {
            "day_status": DayStatus.NORMAL,
            "day_flags": [],
            "attendance_fraction": Decimal("1.0"),
            "worked_minutes": 480,
            "late_minutes": 0,
            "late_count": 0,
            "missing_punch_count": 0,
            "leave_days": Decimal("0"),
            "paid_leave_days": Decimal("0"),
            "unpaid_leave_days": Decimal("0"),
            "comp_leave_days": Decimal("0"),
            "trip_fraction": Decimal("0"),
            "ot_weekday_minutes": 0,
            "ot_weekend_minutes": 0,
            "ot_holiday_minutes": 0,
            "comp_offset_minutes": 0,
            "comp_offset_unused_minutes": 0,
            "deduction_total": Decimal("0"),
        }
        values.update(overrides)
        return create_attendance_day_result(
            db,
            company_id=self.company.id,
            attendance_month_id=self.month.id,
            calc_run_id=self.calc_run.id,
            employee_id=employee_id or self.employee.id,
            work_date=work_date,
            **values,
        )

    def summary(
        self, db: Session, *, employee_id: uuid.UUID | None = None, **overrides: Any
    ):
        values: dict[str, Any] = {
            "weekday_full": Decimal("1.0"),
            "weekday_attended": Decimal("1.0"),
            "late_count": 0,
            "late_minutes": 0,
            "missing_punch_count": 0,
            "absent_days": 0,
            "worked_minutes": 480,
            "attendance_deduct": Decimal("0"),
        }
        values.update(overrides)
        return create_attendance_month_summary(
            db,
            company_id=self.company.id,
            attendance_month_id=self.month.id,
            calc_run_id=self.calc_run.id,
            employee_id=employee_id or self.employee.id,
            **values,
        )


@pytest.fixture
def setup(db: Session) -> Setup:
    return Setup(db)


def _payload(setup: Setup, **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "company_id": str(setup.company.id),
        "employee_id": str(setup.employee.id),
        "work_date": WORK_DATE.isoformat(),
        "base_version": 0,
        "adjusted_values": {
            "day_status": "normal",
            "attendance_fraction": "1.0",
            "worked_minutes": 480,
            "note": "人工补录",
        },
        "reason": "打卡异常，人工确认",
    }
    body.update(overrides)
    return body


def test_create_adjustment_applies_values_and_records_original(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    setup: Setup,
) -> None:
    setup.day(
        db,
        day_status=DayStatus.LATE,
        attendance_fraction=Decimal("0.5"),
        worked_minutes=240,
        late_minutes=12,
        late_count=1,
        missing_punch_count=1,
    )
    setup.summary(
        db,
        weekday_attended=Decimal("0.5"),
        late_count=1,
        late_minutes=12,
        missing_punch_count=1,
        worked_minutes=240,
    )

    response = client.post(
        ADJUSTMENTS_URL,
        headers=superuser_token_headers,
        json=_payload(setup),
    )

    assert response.status_code == 201, response.text
    adjustment = response.json()
    superuser = db.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).one()
    assert adjustment["version"] == 1
    assert adjustment["status"] == "active"
    assert adjustment["employee_id"] == str(setup.employee.id)
    assert adjustment["work_date"] == WORK_DATE.isoformat()
    assert adjustment["calc_run_id"] == str(setup.calc_run.id)
    assert adjustment["adjusted_by"] == str(superuser.id)
    assert adjustment["adjusted_by_name"]
    assert adjustment["reason"] == "打卡异常，人工确认"
    assert adjustment["original_values"] == {
        "day_status": "late",
        "attendance_fraction": "0.5",
        "worked_minutes": 240,
        "note": None,
    }
    assert adjustment["adjusted_values"] == {
        "day_status": "normal",
        "attendance_fraction": "1.0",
        "worked_minutes": 480,
        "note": "人工补录",
    }

    detail = client.get(
        _detail_url(setup.employee.id, WORK_DATE),
        headers=superuser_token_headers,
        params={"company_id": str(setup.company.id)},
    )
    assert detail.status_code == 200, detail.text
    day_result = detail.json()["day_result"]
    assert day_result["is_adjusted"] is True
    assert day_result["adjustment_id"] == adjustment["id"]
    assert day_result["day_status"] == "normal"
    assert day_result["attendance_fraction"] == "1.0"
    assert day_result["worked_minutes"] == 480
    assert day_result["late_minutes"] == 12
    assert day_result["note"] == "人工补录"
    assert [item["version"] for item in detail.json()["adjustments"]] == [1]

    summaries = client.get(
        SUMMARY_URL,
        headers=superuser_token_headers,
        params={"company_id": str(setup.company.id), "month": MONTH},
    )
    assert summaries.status_code == 200, summaries.text
    summary = summaries.json()["data"][0]
    assert summary["is_adjusted"] is True
    assert summary["weekday_attended"] == "1.0"
    assert summary["worked_minutes"] == 480
    assert summary["late_minutes"] == 12


def test_lists_versions_with_filters_and_returns_detail(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    setup: Setup,
) -> None:
    setup.day(db)
    setup.day(db, date(2026, 9, 8))
    first = client.post(
        ADJUSTMENTS_URL,
        headers=superuser_token_headers,
        json=_payload(setup, adjusted_values={"late_minutes": 5}, reason="首次调整"),
    )
    assert first.status_code == 201, first.text
    second = client.post(
        ADJUSTMENTS_URL,
        headers=superuser_token_headers,
        json=_payload(
            setup,
            base_version=1,
            adjusted_values={"early_minutes": 3},
            reason="再次调整",
        ),
    )
    assert second.status_code == 201, second.text
    other_day = client.post(
        ADJUSTMENTS_URL,
        headers=superuser_token_headers,
        json=_payload(
            setup,
            work_date="2026-09-08",
            adjusted_values={"missing_punch_count": 1},
            reason="次日调整",
        ),
    )
    assert other_day.status_code == 201, other_day.text

    response = client.get(
        ADJUSTMENTS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(setup.company.id), "month": MONTH},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["count"] == 3
    assert [(item["work_date"], item["version"]) for item in body["data"]] == [
        ("2026-09-08", 1),
        ("2026-09-07", 2),
        ("2026-09-07", 1),
    ]
    assert [item["status"] for item in body["data"]] == [
        "active",
        "active",
        "superseded",
    ]
    assert all(item["adjusted_by_name"] for item in body["data"])

    superseded = client.get(
        ADJUSTMENTS_URL,
        headers=superuser_token_headers,
        params={
            "company_id": str(setup.company.id),
            "month": MONTH,
            "employee_id": str(setup.employee.id),
            "work_date": WORK_DATE.isoformat(),
            "status": "superseded",
        },
    )
    assert superseded.status_code == 200, superseded.text
    assert superseded.json()["count"] == 1
    assert superseded.json()["data"][0]["reason"] == "首次调整"

    detail = client.get(
        f"{ADJUSTMENTS_URL}{second.json()['id']}",
        headers=superuser_token_headers,
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["version"] == 2
    assert detail.json()["adjusted_values"] == {"early_minutes": 3}
    assert detail.json()["original_values"] == {"early_minutes": 0}

    missing = client.get(
        f"{ADJUSTMENTS_URL}{uuid.uuid7()}", headers=superuser_token_headers
    )
    assert missing.status_code == 404
    assert error_detail(missing)["code"] == "not_found"


def test_version_chain_supersedes_and_undo_restores_original(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    setup: Setup,
) -> None:
    setup.day(
        db,
        day_status=DayStatus.LATE,
        late_minutes=12,
        late_count=1,
        worked_minutes=240,
    )
    first = client.post(
        ADJUSTMENTS_URL,
        headers=superuser_token_headers,
        json=_payload(
            setup,
            adjusted_values={"day_status": "normal", "late_minutes": 0},
            reason="迟到经核实",
        ),
    )
    assert first.status_code == 201, first.text

    second = client.post(
        ADJUSTMENTS_URL,
        headers=superuser_token_headers,
        json=_payload(
            setup,
            base_version=1,
            adjusted_values={"worked_minutes": 300},
            reason="补录工时",
        ),
    )
    assert second.status_code == 201, second.text
    assert second.json()["version"] == 2
    assert second.json()["original_values"] == {"worked_minutes": 240}

    # The new version is the complete override set: v1's fields fall back.
    detail = client.get(
        _detail_url(setup.employee.id, WORK_DATE),
        headers=superuser_token_headers,
        params={"company_id": str(setup.company.id)},
    ).json()
    assert detail["day_result"]["day_status"] == "late"
    assert detail["day_result"]["late_minutes"] == 12
    assert detail["day_result"]["worked_minutes"] == 300
    assert detail["day_result"]["adjustment_id"] == second.json()["id"]
    assert [(item["version"], item["status"]) for item in detail["adjustments"]] == [
        (2, "active"),
        (1, "superseded"),
    ]

    stale = client.post(
        ADJUSTMENTS_URL,
        headers=superuser_token_headers,
        json=_payload(
            setup,
            base_version=1,
            adjusted_values={"worked_minutes": 420},
            reason="过期提交",
        ),
    )
    assert stale.status_code == 409
    assert error_detail(stale)["code"] == "adjustment_conflict"

    undo = client.post(
        ADJUSTMENTS_URL,
        headers=superuser_token_headers,
        json=_payload(
            setup,
            base_version=2,
            adjusted_values=second.json()["original_values"],
            reason="撤销调整",
        ),
    )
    assert undo.status_code == 201, undo.text
    assert undo.json()["version"] == 3

    restored = client.get(
        _detail_url(setup.employee.id, WORK_DATE),
        headers=superuser_token_headers,
        params={"company_id": str(setup.company.id)},
    ).json()
    assert restored["day_result"]["worked_minutes"] == 240
    assert restored["day_result"]["late_minutes"] == 12
    assert restored["day_result"]["day_status"] == "late"
    assert restored["day_result"]["is_adjusted"] is True
    assert restored["day_result"]["adjustment_id"] == undo.json()["id"]
    assert [(item["version"], item["status"]) for item in restored["adjustments"]] == [
        (3, "active"),
        (2, "superseded"),
        (1, "superseded"),
    ]


def _validation_messages(response: Any) -> list[str]:
    detail = response.json()["detail"]
    assert isinstance(detail, list), detail
    return [item["msg"] for item in detail]


@pytest.mark.parametrize(
    ("adjusted_values", "message"),
    [
        ({}, "请至少调整一个字段"),
        ({"attendance_fraction": "1.5"}, "不能大于 1"),
        ({"leave_days": "-0.5"}, "不能小于 0"),
        ({"worked_minutes": -1}, "不能小于 0"),
        ({"late_minutes": -1}, "不能小于 0"),
        ({"early_minutes": -1}, "不能小于 0"),
        ({"missing_punch_count": -1}, "不能小于 0"),
        ({"ot_weekday_minutes": -1}, "不能小于 0"),
        ({"day_flags": ["late"]}, "该字段不可修改"),
        ({"day_status": None}, "调整值不能为空"),
        ({"late_minutes": None}, "调整值不能为空"),
    ],
)
def test_rejects_values_outside_the_adjustable_contract(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    setup: Setup,
    adjusted_values: dict[str, Any],
    message: str,
) -> None:
    setup.day(db, late_minutes=12)

    response = client.post(
        ADJUSTMENTS_URL,
        headers=superuser_token_headers,
        json=_payload(setup, adjusted_values=adjusted_values),
    )

    assert response.status_code == 422, response.text
    assert message in _validation_messages(response)


def test_adjustment_requires_reason_and_non_negative_base_version(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    setup: Setup,
) -> None:
    setup.day(db)

    missing_reason = client.post(
        ADJUSTMENTS_URL,
        headers=superuser_token_headers,
        json=_payload(setup, reason=""),
    )
    assert missing_reason.status_code == 422
    assert "长度不能少于 1 个字符" in _validation_messages(missing_reason)

    negative_base = client.post(
        ADJUSTMENTS_URL,
        headers=superuser_token_headers,
        json=_payload(setup, base_version=-1),
    )
    assert negative_base.status_code == 422
    assert "不能小于 0" in _validation_messages(negative_base)


def test_adjustment_requires_an_existing_result_and_editable_month(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    setup: Setup,
) -> None:
    missing = client.post(
        ADJUSTMENTS_URL,
        headers=superuser_token_headers,
        json=_payload(setup),
    )
    assert missing.status_code == 404
    assert error_detail(missing)["code"] == "not_found"

    setup.day(db)
    setup.month.status = AttendanceMonthStatus.CONFIRMED
    setup.month.is_stale = False
    db.add(setup.month)
    db.commit()

    confirmed = client.post(
        ADJUSTMENTS_URL,
        headers=superuser_token_headers,
        json=_payload(setup),
    )
    assert confirmed.status_code == 409
    assert error_detail(confirmed)["code"] == "month_confirmed"

    setup.month.status = AttendanceMonthStatus.LOCKED
    db.add(setup.month)
    db.commit()

    locked = client.post(
        ADJUSTMENTS_URL,
        headers=superuser_token_headers,
        json=_payload(setup),
    )
    assert locked.status_code == 409
    assert error_detail(locked)["code"] == "month_locked"


def test_adjustment_endpoints_require_authentication(client: TestClient) -> None:
    post = client.post(
        ADJUSTMENTS_URL,
        json={
            "company_id": str(uuid.uuid7()),
            "employee_id": str(uuid.uuid7()),
            "work_date": WORK_DATE.isoformat(),
            "base_version": 0,
            "adjusted_values": {"late_minutes": 0},
            "reason": "未登录",
        },
    )
    assert post.status_code == 401
    assert post.json() == {"detail": "未登录或登录状态已过期"}

    listing = client.get(ADJUSTMENTS_URL, params={"company_id": str(uuid.uuid7())})
    assert listing.status_code == 401

    detail = client.get(f"{ADJUSTMENTS_URL}{uuid.uuid7()}")
    assert detail.status_code == 401


def test_adjustment_rejects_foreign_employee_and_filters_by_company(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    setup: Setup,
) -> None:
    other = Setup(db)
    setup.day(db)
    other.day(db)

    own = client.post(
        ADJUSTMENTS_URL,
        headers=superuser_token_headers,
        json=_payload(setup, adjusted_values={"late_minutes": 1}, reason="本公司"),
    )
    assert own.status_code == 201, own.text
    foreign_employee = client.post(
        ADJUSTMENTS_URL,
        headers=superuser_token_headers,
        json=_payload(
            setup,
            employee_id=str(other.employee.id),
            adjusted_values={"late_minutes": 1},
            reason="跨公司",
        ),
    )
    assert foreign_employee.status_code == 409
    assert error_detail(foreign_employee)["code"] == "cross_company"

    unknown_employee = client.post(
        ADJUSTMENTS_URL,
        headers=superuser_token_headers,
        json=_payload(
            setup,
            employee_id=str(uuid.uuid7()),
            adjusted_values={"late_minutes": 1},
            reason="不存在",
        ),
    )
    assert unknown_employee.status_code == 409
    assert error_detail(unknown_employee)["code"] == "invalid_reference"

    other_list = client.get(
        ADJUSTMENTS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(other.company.id)},
    )
    assert other_list.status_code == 200
    assert other_list.json()["count"] == 0


CALC_DATE = date(2026, 9, 1)


class CalculationSetup:
    """A calculated company-month with one late day built from real inputs."""

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
            employee_no="E101",
            name="冯芷茵",
            hire_date=date(2020, 4, 11),
        )
        self.shift = create_shift(
            db,
            company_id=self.company.id,
            shift_code="ADM",
            shift_name="行政班",
            start_time=time(8, 30),
            end_time=time(17, 30),
            rest_minutes=60,
        )
        self.operator = create_random_user(db)
        create_attendance_rule(db, company_id=self.company.id)
        self.roster_entry = create_roster_entry(
            db,
            company_id=self.company.id,
            employee_id=self.employee.id,
            work_date=CALC_DATE,
            shifts=[self.shift],
        )
        self.batch = create_import_batch(
            db,
            company_id=self.company.id,
            operator_id=self.operator.id,
            data_type=ImportDataType.PUNCH,
            month=MONTH_START,
            status=ImportBatchStatus.COMMITTED,
            committed_at=datetime(2026, 9, 28, tzinfo=UTC),
        )
        self.in_punch = create_punch_record(
            db,
            company_id=self.company.id,
            batch_id=self.batch.id,
            employee_id=self.employee.id,
            attendance_date=CALC_DATE,
            punch_time=datetime.fromisoformat("2026-09-01T08:42:00+08:00"),
            source_row_number=2,
        )
        create_punch_record(
            db,
            company_id=self.company.id,
            batch_id=self.batch.id,
            employee_id=self.employee.id,
            attendance_date=CALC_DATE,
            punch_time=datetime.fromisoformat("2026-09-01T17:30:00+08:00"),
            source_row_number=3,
        )


def _calculate(
    client: TestClient, headers: dict[str, str], setup: CalculationSetup
) -> dict[str, Any]:
    response = client.post(
        CALCULATE_URL,
        headers=headers,
        params={"company_id": str(setup.company.id)},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _day_detail(
    client: TestClient, headers: dict[str, str], setup: CalculationSetup
) -> dict[str, Any]:
    response = client.get(
        _detail_url(setup.employee.id, CALC_DATE),
        headers=headers,
        params={"company_id": str(setup.company.id)},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _listed(
    client: TestClient,
    headers: dict[str, str],
    setup: CalculationSetup,
    **params: Any,
) -> dict[str, Any]:
    response = client.get(
        ADJUSTMENTS_URL,
        headers=headers,
        params={"company_id": str(setup.company.id), **params},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_recalculation_reapplies_adjustments_and_orphans_missing_days(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    setup = CalculationSetup(db)
    first_run = _calculate(client, superuser_token_headers, setup)
    baseline = _day_detail(client, superuser_token_headers, setup)["day_result"]
    assert baseline["late_minutes"] > 0
    assert baseline["day_status"] == "late"

    created = client.post(
        ADJUSTMENTS_URL,
        headers=superuser_token_headers,
        json={
            "company_id": str(setup.company.id),
            "employee_id": str(setup.employee.id),
            "work_date": CALC_DATE.isoformat(),
            "base_version": 0,
            "adjusted_values": {"day_status": "normal", "late_minutes": 0},
            "reason": "迟到已核实，不计迟到",
        },
    )
    assert created.status_code == 201, created.text
    adjustment = created.json()
    assert adjustment["original_values"] == {
        "day_status": "late",
        "late_minutes": baseline["late_minutes"],
    }

    # The recalculated baseline changes; the active override still wins, while
    # the version keeps the values recorded when it was made.
    setup.in_punch.punch_time = datetime(2026, 9, 1, 8, 55, tzinfo=SHANGHAI)
    db.add(setup.in_punch)
    db.commit()

    second_run = _calculate(client, superuser_token_headers, setup)
    assert second_run["id"] != first_run["id"]
    replayed = _day_detail(client, superuser_token_headers, setup)["day_result"]
    assert replayed["late_minutes"] == 0
    assert replayed["day_status"] == "normal"
    assert replayed["is_adjusted"] is True
    assert replayed["adjustment_id"] == adjustment["id"]

    active = _listed(
        client, superuser_token_headers, setup, month=MONTH, status="active"
    )
    assert active["count"] == 1
    assert active["data"][0]["id"] == adjustment["id"]
    assert active["data"][0]["version"] == 1
    assert active["data"][0]["original_values"] == {
        "day_status": "late",
        "late_minutes": baseline["late_minutes"],
    }
    assert active["data"][0]["calc_run_id"] == first_run["id"]

    summaries = client.get(
        SUMMARY_URL,
        headers=superuser_token_headers,
        params={"company_id": str(setup.company.id), "month": MONTH},
    ).json()
    assert summaries["data"][0]["is_adjusted"] is True

    # A second calculation with identical inputs stays idempotent.
    _calculate(client, superuser_token_headers, setup)
    idempotent = _listed(
        client, superuser_token_headers, setup, month=MONTH, status="active"
    )
    assert idempotent["count"] == 1
    assert idempotent["data"][0]["version"] == 1
    assert (
        idempotent["data"][0]["original_values"]["late_minutes"]
        == baseline["late_minutes"]
    )

    # Removing the day from the result set orphans, never deletes, the version.
    db.execute(delete(PunchRecord).where(col(PunchRecord.batch_id) == setup.batch.id))
    db.execute(delete(RosterEntry).where(col(RosterEntry.id) == setup.roster_entry.id))
    db.commit()
    _calculate(client, superuser_token_headers, setup)

    missing = client.get(
        _detail_url(setup.employee.id, CALC_DATE),
        headers=superuser_token_headers,
        params={"company_id": str(setup.company.id)},
    )
    assert missing.status_code == 404

    assert (
        _listed(client, superuser_token_headers, setup, month=MONTH, status="active")[
            "count"
        ]
        == 0
    )
    orphaned = _listed(
        client, superuser_token_headers, setup, month=MONTH, status="orphaned"
    )
    assert orphaned["count"] == 1
    assert orphaned["data"][0]["id"] == adjustment["id"]
    assert orphaned["data"][0]["version"] == 1
    assert orphaned["data"][0]["reason"] == "迟到已核实，不计迟到"

    # Orphaned versions stay retained across later calculations.
    _calculate(client, superuser_token_headers, setup)
    assert (
        _listed(client, superuser_token_headers, setup, month=MONTH, status="orphaned")[
            "count"
        ]
        == 1
    )


def test_concurrent_submissions_with_the_same_base_version_conflict(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    setup: Setup,
) -> None:
    setup.day(db)
    start = Event()

    def submit(late_minutes: int) -> tuple[str, str | int]:
        with Session(engine) as session:
            operator = session.exec(
                select(User).where(User.email == settings.FIRST_SUPERUSER)
            ).one()
            payload = AttendanceAdjustmentCreate(
                company_id=setup.company.id,
                employee_id=setup.employee.id,
                work_date=WORK_DATE,
                base_version=0,
                adjusted_values={"late_minutes": late_minutes},
                reason=f"并发提交 {late_minutes}",
            )
            start.wait()
            try:
                created = adjustment_service.create_adjustment(
                    session, payload, operator=operator
                )
                return ("created", created.version)
            except DomainError as error:
                return ("error", str(error.code))

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(submit, value) for value in (1, 2)]
        start.set()
        results = [future.result() for future in futures]

    assert sorted(results) == [
        ("created", 1),
        ("error", "adjustment_conflict"),
    ]
    active = _listed(
        client, superuser_token_headers, setup, month=MONTH, status="active"
    )
    assert active["count"] == 1
    assert active["data"][0]["version"] == 1
    assert _listed(client, superuser_token_headers, setup, month=MONTH)["count"] == 1


def test_adjustment_updates_the_affected_month_summary_fields(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    setup: Setup,
) -> None:
    setup.day(
        db,
        day_status=DayStatus.ABSENT,
        attendance_fraction=Decimal("0"),
        worked_minutes=0,
        missing_punch_count=1,
        deduction_total=Decimal("-100.00"),
    )
    setup.day(
        db,
        date(2026, 9, 8),
        attendance_fraction=Decimal("1.0"),
        worked_minutes=480,
    )
    setup.summary(
        db,
        weekday_full=Decimal("2.0"),
        weekday_attended=Decimal("1.0"),
        missing_punch_count=1,
        absent_days=1,
        worked_minutes=480,
        attendance_deduct=Decimal("-100.00"),
    )

    response = client.post(
        ADJUSTMENTS_URL,
        headers=superuser_token_headers,
        json=_payload(
            setup,
            adjusted_values={
                "day_status": "normal",
                "attendance_fraction": "1.0",
                "worked_minutes": 480,
                "ot_weekday_minutes": 60,
                "missing_punch_count": 0,
            },
            reason="补录出勤与加班",
        ),
    )
    assert response.status_code == 201, response.text

    summary = client.get(
        SUMMARY_URL,
        headers=superuser_token_headers,
        params={"company_id": str(setup.company.id), "month": MONTH},
    ).json()["data"][0]
    assert summary["weekday_full"] == "2.0"
    assert summary["weekday_attended"] == "2.0"
    assert summary["absent_days"] == 0
    assert summary["worked_minutes"] == 960
    assert summary["ot_weekday_minutes"] == 60
    assert summary["ot_weekday_hours"] == "1.00"
    assert summary["missing_punch_count"] == 0
    # Deduction suggestions are re-derived from the adjusted facts; this day
    # has no late/early counts and the adjusted missing count is zero.
    assert summary["attendance_deduct"] == "0.00"
    assert summary["is_adjusted"] is True


def test_adjustment_recomputes_itemized_deduction_suggestions(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    setup: Setup,
) -> None:
    setup.calc_run.rules_snapshot = {
        "company_rule": {
            **DEFAULT_RULE_VALUES,
            "absent_deduct_per_day": "100.00",
            "late_deduct_per_occurrence": "20.00",
            "early_deduct_per_occurrence": "20.00",
            "missing_punch_deduct_per_occurrence": "10.00",
        },
        "plan_overrides": [],
        "holidays": [],
    }
    db.add(setup.calc_run)
    db.commit()
    setup.day(
        db,
        day_status=DayStatus.ABSENT,
        attendance_fraction=Decimal("0"),
        worked_minutes=0,
        late_count=2,
        early_count=1,
        missing_punch_count=1,
        absent_deduct_amount=Decimal("-100.00"),
        deduction_total=Decimal("-100.00"),
    )
    setup.summary(
        db,
        weekday_attended=Decimal("0"),
        late_count=2,
        early_count=1,
        missing_punch_count=1,
        absent_days=1,
        worked_minutes=0,
        attendance_deduct=Decimal("-100.00"),
    )

    created = client.post(
        ADJUSTMENTS_URL,
        headers=superuser_token_headers,
        json=_payload(
            setup,
            adjusted_values={
                "day_status": "late",
                "attendance_fraction": "1.0",
                "worked_minutes": 480,
                "missing_punch_count": 0,
            },
            reason="核销旷工与缺卡",
        ),
    )
    assert created.status_code == 201, created.text

    day_result = client.get(
        _detail_url(setup.employee.id, WORK_DATE),
        headers=superuser_token_headers,
        params={"company_id": str(setup.company.id)},
    ).json()["day_result"]
    assert day_result["absent_deduct_amount"] == "0.00"
    assert day_result["late_deduct_amount"] == "-40.00"
    assert day_result["early_deduct_amount"] == "-20.00"
    assert day_result["missing_punch_deduct_amount"] == "0.00"
    assert day_result["deduction_total"] == "-60.00"
    summary = client.get(
        SUMMARY_URL,
        headers=superuser_token_headers,
        params={"company_id": str(setup.company.id), "month": MONTH},
    ).json()["data"][0]
    assert summary["attendance_deduct"] == "-60.00"

    undo = client.post(
        ADJUSTMENTS_URL,
        headers=superuser_token_headers,
        json=_payload(
            setup,
            base_version=1,
            adjusted_values=created.json()["original_values"],
            reason="撤销调整",
        ),
    )
    assert undo.status_code == 201, undo.text
    restored = client.get(
        _detail_url(setup.employee.id, WORK_DATE),
        headers=superuser_token_headers,
        params={"company_id": str(setup.company.id)},
    ).json()["day_result"]
    assert restored["absent_deduct_amount"] == "-100.00"
    assert restored["deduction_total"] == "-100.00"
    summary = client.get(
        SUMMARY_URL,
        headers=superuser_token_headers,
        params={"company_id": str(setup.company.id), "month": MONTH},
    ).json()["data"][0]
    assert summary["attendance_deduct"] == "-100.00"


def test_adjustments_have_no_delete_endpoint(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    setup: Setup,
) -> None:
    setup.day(db)
    created = client.post(
        ADJUSTMENTS_URL,
        headers=superuser_token_headers,
        json=_payload(setup),
    )
    assert created.status_code == 201, created.text

    response = client.delete(
        f"{ADJUSTMENTS_URL}{created.json()['id']}",
        headers=superuser_token_headers,
    )

    assert response.status_code == 405
