"""Helpers for the attendance import fixtures (docs/specs/attendance-fixtures)."""

import uuid
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient
from httpx import Response
from sqlmodel import Session

from app.core.config import settings
from app.enums import EmployeeStatus, ImportDataType
from app.models import Company, Employee
from app.services.attendance import import_mapping, import_parsing
from tests.utils.factories import (
    create_department,
    create_employee,
    create_position,
)

IMPORTS_URL = f"{settings.API_V1_STR}/attendance/imports"

FIXTURE_DIR = (
    Path(__file__).resolve().parents[3] / "docs" / "specs" / "attendance-fixtures"
)

FIXTURE_FILES = {
    ImportDataType.PUNCH: "punch-2026-09.csv",
    ImportDataType.TRIP: "oa-trip-2026-09.csv",
    ImportDataType.OT: "oa-overtime-2026-09.csv",
    ImportDataType.LEAVE: "oa-leave-2026-09.csv",
}

# Employee seed from docs/specs/attendance-fixtures/README.md section 1.
EMPLOYEES = [
    ("E101", "冯芷茵", "生产部", date(2020, 4, 11), None),
    ("E102", "刘衍英", "财务部", date(2018, 9, 3), None),
    ("E103", "周玉琼", "生产部", date(2019, 3, 18), None),
    ("E104", "胡国邵", "生产部", date(2017, 6, 1), None),
    ("E105", "李金辉", "生产部", date(2021, 11, 8), None),
    ("E106", "黄佳誉", "技术部", date(2020, 2, 17), None),
    ("E107", "梁林高", "行政部", date(2016, 5, 23), None),
    ("E108", "黄国锋", "生产部", date(2019, 8, 30), None),
    ("E109", "申佳林", "行政部", date(2015, 10, 12), None),
    ("E110", "张伟", "生产部", date(2019, 1, 1), None),
    ("E111", "张伟", "财务部", date(2020, 1, 1), None),
    ("E112", "王强", "生产部", date(2018, 1, 1), date(2026, 8, 31)),
    ("E113", "李娜", "生产部", date(2026, 9, 15), None),
]


def fixture_path(data_type: ImportDataType) -> Path:
    return FIXTURE_DIR / FIXTURE_FILES[data_type]


def load_fixture_bytes(data_type: ImportDataType) -> bytes:
    return fixture_path(data_type).read_bytes()


def seed_fixture_employees(db: Session, company: Company) -> dict[str, Employee]:
    departments = {
        name: create_department(db, company=company, dept_name=name)
        for name in ("生产部", "财务部", "技术部", "行政部")
    }
    position = create_position(db, company=company, position_name="员工级")
    employees: dict[str, Employee] = {}
    for employee_no, name, dept_name, hire_date, resign_date in EMPLOYEES:
        employees[employee_no] = create_employee(
            db,
            dept=departments[dept_name],
            position=position,
            employee_no=employee_no,
            name=name,
            hire_date=hire_date,
            resign_date=resign_date,
            status=(EmployeeStatus.RESIGNED if resign_date else EmployeeStatus.ACTIVE),
        )
    return employees


def parse_fixture(
    data_type: ImportDataType,
) -> import_mapping.DetectedTable:
    parsed = import_parsing.parse_upload(
        content=load_fixture_bytes(data_type),
        file_name=FIXTURE_FILES[data_type],
    )
    return import_mapping.detect_header(parsed, data_type)


def preview_fixture(
    client: TestClient,
    headers: dict[str, str],
    company_id: uuid.UUID,
    data_type: ImportDataType,
    *,
    month: str = "2026-09",
) -> Response:
    """Upload one repository fixture as a preview batch through the API."""
    return client.post(
        f"{IMPORTS_URL}/preview",
        headers=headers,
        data={
            "company_id": str(company_id),
            "data_type": data_type.value,
            "month": month,
        },
        files={
            "file": (
                FIXTURE_FILES[data_type],
                load_fixture_bytes(data_type),
                "application/octet-stream",
            )
        },
    )
