"""Read-only attendance contract consumed by payroll (payroll spec 7.7, 14.4).

Seam: ``app.services.attendance.read_contract``. Payroll reads a locked
attendance month's month summary in-process and receives frozen value and
source-metadata dataclasses; unlocked or missing sources fail with explicit
contract codes.
"""

import ast
import uuid
from dataclasses import FrozenInstanceError, is_dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlmodel import Session

from app.core.errors import DomainError
from app.enums import AttendanceMonthStatus
from app.services.attendance import read_contract
from tests.utils.attendance_factories import (
    create_attendance_month,
    create_attendance_month_summary,
    create_calc_run,
    create_month_snapshot,
)
from tests.utils.factories import (
    create_company,
    create_department,
    create_employee,
    create_position,
)
from tests.utils.user import create_random_user

MONTH = date(2026, 9, 1)
LOCKED_AT = datetime(2026, 10, 5, 2, 0, tzinfo=UTC)


def _locked_month(db: Session):
    company = create_company(db)
    department = create_department(db, company=company)
    position = create_position(db, company=company)
    employee = create_employee(db, dept=department, position=position)
    operator = create_random_user(db)
    month = create_attendance_month(
        db,
        company_id=company.id,
        month=MONTH,
        status=AttendanceMonthStatus.LOCKED,
        is_stale=False,
        locked_at=LOCKED_AT,
    )
    calc_run = create_calc_run(
        db,
        attendance_month_id=month.id,
        calc_version="attendance-calc-v1",
        rules_version="rules-2026.09",
    )
    snapshot = create_month_snapshot(
        db,
        attendance_month_id=month.id,
        calc_run_id=calc_run.id,
        locked_by=operator.id,
        company_id=company.id,
        month=MONTH,
        version=3,
        locked_at=LOCKED_AT,
    )
    summary = create_attendance_month_summary(
        db,
        company_id=company.id,
        attendance_month_id=month.id,
        calc_run_id=calc_run.id,
        employee_id=employee.id,
        weekday_full=Decimal("21.0"),
        weekend_full=Decimal("9.0"),
        weekday_attended=Decimal("20.5"),
        weekend_attended=Decimal("4.0"),
        paid_leave_days=Decimal("0.5"),
        ot_weekday_hours=Decimal("12.50"),
        ot_weekend_hours=Decimal("3.00"),
        ot_holiday_hours=Decimal("0"),
        attendance_deduct=Decimal("-125.50"),
    )
    return company, employee, month, snapshot, calc_run, summary


def test_reads_the_nine_values_and_source_metadata_for_a_locked_month(
    db: Session,
) -> None:
    company, employee, month, snapshot, calc_run, _ = _locked_month(db)

    source = read_contract.read_locked_month_summary(
        db,
        company_id=company.id,
        month=MONTH,
        employee_id=employee.id,
    )

    assert source.attendance_month_id == month.id
    assert source.attendance_snapshot_id == snapshot.id
    assert source.attendance_snapshot_version == 3
    assert source.attendance_calc_run_id == calc_run.id
    assert source.calc_version == "attendance-calc-v1"
    assert source.rules_version == "rules-2026.09"
    assert source.locked_at == LOCKED_AT
    assert source.values.weekday_full == Decimal("21.0")
    assert source.values.weekend_full == Decimal("9.0")
    assert source.values.weekday_attended == Decimal("20.5")
    assert source.values.weekend_attended == Decimal("4.0")
    assert source.values.paid_leave_days == Decimal("0.5")
    assert source.values.ot_weekday_hours == Decimal("12.50")
    assert source.values.ot_weekend_hours == Decimal("3.00")
    assert source.values.ot_holiday_hours == Decimal("0.00")
    assert source.values.attendance_deduct == Decimal("-125.50")
    assert is_dataclass(source) and is_dataclass(source.values)
    with pytest.raises(FrozenInstanceError):
        source.values.weekday_full = Decimal("1.0")


def test_missing_attendance_month_fails_with_the_contract_code(db: Session) -> None:
    company = create_company(db)

    with pytest.raises(DomainError) as exc_info:
        read_contract.read_locked_month_summary(
            db,
            company_id=company.id,
            month=MONTH,
            employee_id=uuid.uuid7(),
        )

    assert exc_info.value.code == read_contract.AttendanceReadErrorCode.MONTH_MISSING


def test_unlocked_attendance_month_fails_with_the_contract_code(db: Session) -> None:
    company = create_company(db)
    department = create_department(db, company=company)
    position = create_position(db, company=company)
    employee = create_employee(db, dept=department, position=position)
    create_attendance_month(
        db,
        company_id=company.id,
        month=MONTH,
        status=AttendanceMonthStatus.CALCULATED,
        is_stale=False,
    )

    with pytest.raises(DomainError) as exc_info:
        read_contract.read_locked_month_summary(
            db,
            company_id=company.id,
            month=MONTH,
            employee_id=employee.id,
        )

    assert exc_info.value.code == read_contract.AttendanceReadErrorCode.MONTH_NOT_LOCKED


def test_missing_month_summary_fails_with_the_contract_code(db: Session) -> None:
    company, employee, _, _, _, summary = _locked_month(db)
    db.delete(summary)
    db.commit()

    with pytest.raises(DomainError) as exc_info:
        read_contract.read_locked_month_summary(
            db,
            company_id=company.id,
            month=MONTH,
            employee_id=employee.id,
        )

    assert exc_info.value.code == read_contract.AttendanceReadErrorCode.SUMMARY_MISSING


def test_summary_run_mismatch_fails_with_the_contract_code(db: Session) -> None:
    company, employee, month, _, _, summary = _locked_month(db)
    other_run = create_calc_run(db, attendance_month_id=month.id)
    summary.calc_run_id = other_run.id
    db.add(summary)
    db.commit()

    with pytest.raises(DomainError) as exc_info:
        read_contract.read_locked_month_summary(
            db,
            company_id=company.id,
            month=MONTH,
            employee_id=employee.id,
        )

    assert (
        exc_info.value.code == read_contract.AttendanceReadErrorCode.SOURCE_INCONSISTENT
    )


def test_another_companys_locked_month_is_not_readable(db: Session) -> None:
    _, employee, _, _, _, _ = _locked_month(db)
    other_company = create_company(db)

    with pytest.raises(DomainError) as exc_info:
        read_contract.read_locked_month_summary(
            db,
            company_id=other_company.id,
            month=MONTH,
            employee_id=employee.id,
        )

    assert exc_info.value.code == read_contract.AttendanceReadErrorCode.MONTH_MISSING


def test_read_contract_imports_no_payroll_code() -> None:
    path = Path(read_contract.__file__ or "")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)

    assert not any(
        name.startswith(("app.services.payroll", "app.schemas_payroll"))
        for name in imported
    ), imported
