"""Import preview API contract (spec sections 6.6, 6.7.1, 8.3.4, 8.5, 8.8).

Seam: ``POST /api/v1/attendance/imports/preview`` and
``GET /api/v1/attendance/imports/mapping-template``. The tests exercise the
persisted preview batch, stats, employee matching, impact, can_commit reasons,
column overrides, security limits, authentication, and cross-company isolation.
"""

import io
import json
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlmodel import Session, func, select

from app.core.config import settings
from app.enums import (
    AttendanceMonthStatus,
    ImportBatchStatus,
    ImportDataType,
    ImportSource,
)
from app.models import (
    ImportBatch,
    ImportBatchError,
    OaLeave,
    OaOvertime,
    OaOvertimeDay,
    OaTrip,
    PunchRecord,
    User,
)
from app.services.attendance.imports import PARSER_VERSION
from tests.utils.attendance_factories import (
    create_attendance_month,
    create_import_batch,
    create_import_batch_error,
    create_punch_record,
)
from tests.utils.attendance_imports import (
    load_fixture_bytes,
    seed_fixture_employees,
)
from tests.utils.factories import (
    create_company,
    create_department,
    create_employee,
    create_position,
)
from tests.utils.utils import random_upper_code

IMPORTS_URL = f"{settings.API_V1_STR}/attendance/imports"
PREVIEW_URL = f"{IMPORTS_URL}/preview"
TEMPLATE_URL = f"{IMPORTS_URL}/mapping-template"
MONTH = "2026-09"


def error_detail(response: Any) -> dict[str, Any]:
    body = response.json()
    assert isinstance(body["detail"], dict), body
    return body["detail"]


def preview_file(
    client: TestClient,
    headers: dict[str, str],
    *,
    company_id: uuid.UUID,
    data_type: str,
    content: bytes,
    file_name: str,
    month: str = MONTH,
    sheet_name: str | None = None,
    column_mapping: dict[str, Any] | None = None,
) -> Any:
    data: dict[str, Any] = {
        "company_id": str(company_id),
        "data_type": data_type,
        "month": month,
    }
    if sheet_name is not None:
        data["sheet_name"] = sheet_name
    if column_mapping is not None:
        data["column_mapping"] = json.dumps(column_mapping)
    return client.post(
        PREVIEW_URL,
        headers=headers,
        data=data,
        files={"file": (file_name, content, "application/octet-stream")},
    )


def preview_text(
    client: TestClient,
    headers: dict[str, str],
    *,
    company_id: uuid.UUID,
    data_type: str,
    text: str,
    month: str = MONTH,
    column_mapping: dict[str, Any] | None = None,
) -> Any:
    data: dict[str, Any] = {
        "company_id": str(company_id),
        "data_type": data_type,
        "month": month,
        "text": text,
    }
    if column_mapping is not None:
        data["column_mapping"] = json.dumps(column_mapping)
    return client.post(PREVIEW_URL, headers=headers, data=data)


def preview_fixture(
    client: TestClient,
    headers: dict[str, str],
    company_id: uuid.UUID,
    data_type: ImportDataType,
) -> Any:
    return preview_file(
        client,
        headers,
        company_id=company_id,
        data_type=data_type.value,
        content=load_fixture_bytes(data_type),
        file_name=f"{data_type.value}.csv",
    )


def batch_count(db: Session) -> int:
    db.expire_all()
    return db.exec(select(func.count()).select_from(ImportBatch)).one()


def test_invalid_month_is_a_request_shape_error(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    response = preview_text(
        client,
        superuser_token_headers,
        company_id=company.id,
        data_type="punch",
        text="工号,考勤日期,打卡时间,打卡结果\n",
        month="2026-9",
    )

    assert response.status_code == 422


def test_unknown_company_is_404(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    response = preview_text(
        client,
        superuser_token_headers,
        company_id=uuid.uuid7(),
        data_type="punch",
        text="工号,考勤日期,打卡时间,打卡结果\n",
    )

    assert response.status_code == 404
    assert error_detail(response)["code"] == "not_found"
    assert batch_count(db) == 0


def test_import_endpoints_require_authentication(client: TestClient) -> None:
    assert client.post(PREVIEW_URL, data={}).status_code == 401
    assert client.post(PREVIEW_URL, data={}).json() == {
        "detail": "未登录或登录状态已过期"
    }
    assert client.get(TEMPLATE_URL).status_code == 401


def test_punch_fixture_preview_persists_batch_stats_and_samples(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    seed_fixture_employees(db, company)
    content = load_fixture_bytes(ImportDataType.PUNCH)

    response = preview_file(
        client,
        superuser_token_headers,
        company_id=company.id,
        data_type="punch",
        content=content,
        file_name="punch-2026-09.csv",
    )

    assert response.status_code == 200, response.text
    body = response.json()
    batch = body["batch"]
    assert batch["status"] == "preview"
    assert batch["source"] == "upload"
    assert batch["file_name"] == "punch-2026-09.csv"
    assert batch["file_size"] == len(content)
    assert len(batch["file_sha256"]) == 64
    assert batch["header_row_number"] == 1
    assert batch["header_columns"] == [
        "工号",
        "姓名",
        "部门",
        "考勤日期",
        "打卡时间",
        "打卡结果",
        "打卡设备",
        "打卡地址",
        "考勤时间",
    ]
    assert batch["column_mapping"]["employee_no"] == {
        "column": "工号",
        "index": 0,
    }
    assert batch["column_mapping"]["scheduled_time"] == {
        "column": "考勤时间",
        "index": 8,
    }
    assert batch["parser_version"] == PARSER_VERSION
    created_at = datetime.fromisoformat(batch["created_at"].replace("Z", "+00:00"))
    expires_at = datetime.fromisoformat(batch["expires_at"].replace("Z", "+00:00"))
    assert expires_at - created_at == timedelta(hours=24)
    assert batch["valid_records"] == 27
    assert batch["skipped_records"] == 10
    assert batch["error_records"] == 4
    assert batch["warning_records"] == 5

    assert body["stats"] == {
        "source_rows": 37,
        "valid_records": 27,
        "skipped_records": 10,
        "error_records": 4,
        "warning_records": 5,
        "skip_counts": {
            "unknown_employee": 1,
            "out_of_employment": 2,
            "missing_punch_time": 1,
            "invalid_punch": 3,
            "not_in_month": 1,
            "duplicate_punch": 2,
        },
        "warning_counts": {
            "empty_result": 1,
            "name_mismatch": 1,
            "date_mismatch": 1,
            "result_conflict": 1,
            "unknown_result": 1,
        },
    }
    assert body["employees"] == {
        "matched": 11,
        "unknown": 1,
        "duplicate_name": 0,
        "affected": 9,
    }
    assert body["error_total"] == 9
    assert len(body["errors"]) == 9
    assert {
        (error["source_row_number"], error["code"], error["severity"])
        for error in body["errors"]
    } >= {
        (11, "unknown_employee", "error"),
        (22, "out_of_employment", "error"),
        (23, "out_of_employment", "error"),
        (25, "missing_punch_time", "error"),
        (18, "empty_result", "warning"),
        (31, "result_conflict", "warning"),
    }
    assert len(body["samples"]) == 20
    assert body["samples"][0]["employee_no"] == "E101"
    assert body["samples"][0]["attendance_date"] == "2026-09-01"
    assert body["impact"] == {
        "current_batch": None,
        "valid_records_delta": 27,
        "employee_overlap": 0,
        "employees_added": 9,
        "employees_removed": 0,
    }
    assert body["can_commit"] is True
    assert body["commit_blocked_reason"] is None

    db.expire_all()
    stored = db.exec(select(ImportBatch)).one()
    assert stored.id == uuid.UUID(batch["id"])
    assert stored.operator_id is not None
    assert stored.status.value == "preview"
    assert db.exec(select(func.count()).select_from(PunchRecord)).one() == 27
    assert db.exec(select(func.count()).select_from(ImportBatchError)).one() == 9


@pytest.mark.parametrize(
    ("data_type", "model", "valid", "skipped", "errors", "warnings"),
    [
        (ImportDataType.TRIP, OaTrip, 8, 9, 5, 0),
        (ImportDataType.OT, OaOvertime, 8, 7, 3, 1),
        (ImportDataType.LEAVE, OaLeave, 8, 11, 8, 1),
    ],
)
def test_oa_fixture_previews_persist_typed_records(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    data_type: ImportDataType,
    model: Any,
    valid: int,
    skipped: int,
    errors: int,
    warnings: int,
) -> None:
    company = create_company(db)
    seed_fixture_employees(db, company)

    response = preview_fixture(client, superuser_token_headers, company.id, data_type)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["stats"]["valid_records"] == valid
    assert body["stats"]["skipped_records"] == skipped
    assert body["stats"]["error_records"] == errors
    assert body["stats"]["warning_records"] == warnings

    db.expire_all()
    assert db.exec(select(func.count()).select_from(model)).one() == valid


def test_overtime_preview_persists_daily_minutes(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    seed_fixture_employees(db, company)

    response = preview_fixture(
        client, superuser_token_headers, company.id, ImportDataType.OT
    )

    assert response.status_code == 200, response.text
    db.expire_all()
    assert db.exec(select(func.count()).select_from(OaOvertimeDay)).one() == 13
    rows = db.exec(
        select(OaOvertimeDay).where(OaOvertimeDay.work_date == date(2026, 9, 14))
    ).all()
    assert sorted(row.minutes for row in rows) == [480, 480]


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        (AttendanceMonthStatus.CONFIRMED, "month_confirmed"),
        (AttendanceMonthStatus.LOCKED, "month_locked"),
    ],
)
def test_preview_succeeds_for_confirmed_or_locked_months(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    status: AttendanceMonthStatus,
    reason: str,
) -> None:
    company = create_company(db)
    seed_fixture_employees(db, company)
    create_attendance_month(
        db, company_id=company.id, month=date(2026, 9, 1), status=status
    )

    response = preview_fixture(
        client, superuser_token_headers, company.id, ImportDataType.PUNCH
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["can_commit"] is False
    assert body["commit_blocked_reason"] == reason
    assert body["stats"]["valid_records"] == 27


def test_zero_valid_records_blocks_commit(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    content = (
        "工号,考勤日期,打卡时间,打卡结果\nE999,2026-09-01,2026-09-01 08:00,正常\n"
    ).encode()

    response = preview_file(
        client,
        superuser_token_headers,
        company_id=company.id,
        data_type="punch",
        content=content,
        file_name="punch.csv",
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["stats"]["valid_records"] == 0
    assert body["stats"]["skipped_records"] == 1
    assert body["can_commit"] is False
    assert body["commit_blocked_reason"] == "no_valid_rows"


def test_column_mapping_overrides_are_applied_and_snapshotted(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    seed_fixture_employees(db, company)
    content = (
        "员工工号,姓名,部门,考勤日期,刷卡时刻,打卡结果\n"
        "E101,冯芷茵,生产部,2026-09-01,2026-09-01 08:18,正常\n"
    ).encode()

    rejected = preview_file(
        client,
        superuser_token_headers,
        company_id=company.id,
        data_type="punch",
        content=content,
        file_name="punch.csv",
    )
    assert rejected.status_code == 409
    assert error_detail(rejected)["code"] == "missing_required_column"
    assert error_detail(rejected)["field_errors"] == {"punch_time": "缺少必填列"}
    assert batch_count(db) == 0

    accepted = preview_file(
        client,
        superuser_token_headers,
        company_id=company.id,
        data_type="punch",
        content=content,
        file_name="punch.csv",
        column_mapping={"punch_time": "刷卡时刻"},
    )
    assert accepted.status_code == 200, accepted.text
    body = accepted.json()
    assert body["batch"]["column_mapping"]["punch_time"] == {
        "column": "刷卡时刻",
        "index": 4,
    }
    assert body["batch"]["header_columns"][4] == "刷卡时刻"
    assert body["stats"]["valid_records"] == 1


def test_duplicate_column_mapping_is_fatal(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    seed_fixture_employees(db, company)
    content = (
        "工号,考勤日期,打卡时间,打卡结果,打卡地址\n"
        "E101,2026-09-01,2026-09-01 08:18,正常,一号门\n"
    ).encode()

    response = preview_file(
        client,
        superuser_token_headers,
        company_id=company.id,
        data_type="punch",
        content=content,
        file_name="punch.csv",
        column_mapping={"device_raw": "打卡地址"},
    )

    assert response.status_code == 409
    detail = error_detail(response)
    assert detail["code"] == "missing_required_column"
    assert "device_raw" in detail["field_errors"]
    assert "address_raw" in detail["field_errors"]
    assert batch_count(db) == 0


def test_invalid_column_mapping_json_is_fatal(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    response = client.post(
        PREVIEW_URL,
        headers=superuser_token_headers,
        data={
            "company_id": str(company.id),
            "data_type": "punch",
            "month": MONTH,
            "text": "工号,考勤日期,打卡时间,打卡结果\n",
            "column_mapping": "{not json",
        },
    )

    assert response.status_code == 409
    assert error_detail(response)["field_errors"] == {
        "column_mapping": "列映射格式不正确"
    }


def xlsx_bytes(sheets: list[tuple[str, list[list[Any]]]]) -> bytes:
    workbook = Workbook()
    workbook.remove(workbook.active)
    for title, rows in sheets:
        sheet = workbook.create_sheet(title)
        for row in rows:
            sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


PUNCH_HEADER = ["工号", "考勤日期", "打卡时间", "打卡结果"]


def test_multiple_non_empty_sheets_require_sheet_name(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    seed_fixture_employees(db, company)
    content = xlsx_bytes(
        [
            (
                "九月",
                [PUNCH_HEADER, ["E101", "2026-09-01", "2026-09-01 08:18", "正常"]],
            ),
            (
                "十月",
                [PUNCH_HEADER, ["E101", "2026-09-02", "2026-09-02 08:18", "正常"]],
            ),
            ("空表", [[None], [None]]),
        ]
    )

    response = preview_file(
        client,
        superuser_token_headers,
        company_id=company.id,
        data_type="punch",
        content=content,
        file_name="punch.xlsx",
    )

    assert response.status_code == 409
    detail = error_detail(response)
    assert detail["code"] == "sheet_required"
    assert detail["field_errors"] == {"sheet_name": "九月,十月"}
    assert batch_count(db) == 0

    accepted = preview_file(
        client,
        superuser_token_headers,
        company_id=company.id,
        data_type="punch",
        content=content,
        file_name="punch.xlsx",
        sheet_name="十月",
    )

    assert accepted.status_code == 200, accepted.text
    body = accepted.json()
    assert body["batch"]["sheet_name"] == "十月"
    assert body["stats"]["valid_records"] == 1
    assert body["samples"][0]["attendance_date"] == "2026-09-02"


def test_paste_preview_uses_the_paste_source(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    seed_fixture_employees(db, company)
    text = (
        "工号\t考勤日期\t打卡时间\t打卡结果\nE101\t2026-09-01\t2026-09-01 08:18\t正常\n"
    )

    response = preview_text(
        client,
        superuser_token_headers,
        company_id=company.id,
        data_type="punch",
        text=text,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["batch"]["source"] == "paste"
    assert body["batch"]["file_name"] is None
    assert body["batch"]["file_size"] == len(text.encode())
    assert len(body["batch"]["file_sha256"]) == 64
    assert body["stats"]["valid_records"] == 1


def test_both_file_and_text_are_rejected(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    response = client.post(
        PREVIEW_URL,
        headers=superuser_token_headers,
        data={
            "company_id": str(company.id),
            "data_type": "punch",
            "month": MONTH,
            "text": "工号,考勤日期,打卡时间,打卡结果\n",
        },
        files={"file": ("punch.csv", b"x", "text/csv")},
    )

    assert response.status_code == 409
    assert error_detail(response)["code"] == "import_parse_failed"
    assert batch_count(db) == 0


def test_neither_file_nor_text_is_rejected(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    response = client.post(
        PREVIEW_URL,
        headers=superuser_token_headers,
        data={
            "company_id": str(company.id),
            "data_type": "punch",
            "month": MONTH,
        },
    )

    assert response.status_code == 409
    assert error_detail(response)["code"] == "import_parse_failed"
    assert batch_count(db) == 0


def test_legacy_and_macro_files_return_415(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    for file_name in ("legacy.xls", "macro.xlsm", "data.txt"):
        response = preview_file(
            client,
            superuser_token_headers,
            company_id=company.id,
            data_type="punch",
            content=b"data",
            file_name=file_name,
        )
        assert response.status_code == 415, file_name
        assert error_detail(response)["code"] == "unsupported_file_type"
    assert batch_count(db) == 0


def test_files_over_ten_megabytes_return_413(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    response = preview_file(
        client,
        superuser_token_headers,
        company_id=company.id,
        data_type="punch",
        content=b"a" * (10 * 1024 * 1024 + 1),
        file_name="big.csv",
    )

    assert response.status_code == 413
    assert error_detail(response)["code"] == "file_too_large"
    assert batch_count(db) == 0


def test_gb18030_upload_falls_back_after_utf8(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    seed_fixture_employees(db, company)
    text = (
        "工号,姓名,部门,考勤日期,打卡时间,打卡结果\n"
        "E101,冯芷茵,生产部,2026-09-01,2026-09-01 08:18,正常\n"
    )

    response = preview_file(
        client,
        superuser_token_headers,
        company_id=company.id,
        data_type="punch",
        content=text.encode("gb18030"),
        file_name="punch.csv",
    )

    assert response.status_code == 200, response.text
    assert response.json()["stats"]["valid_records"] == 1


def test_preview_errors_are_capped_at_one_hundred(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    header = "工号,考勤日期,打卡时间,打卡结果\n"
    rows = "".join(
        f"E{index:04d},2026-09-01,2026-09-01 08:00,正常\n" for index in range(105)
    )

    response = preview_text(
        client,
        superuser_token_headers,
        company_id=company.id,
        data_type="punch",
        text=header + rows,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["stats"]["source_rows"] == 105
    assert body["stats"]["skipped_records"] == 105
    assert body["error_total"] == 105
    assert len(body["errors"]) == 100
    assert [error["source_row_number"] for error in body["errors"]] == list(
        range(2, 102)
    )


def test_preview_matches_employees_within_the_requested_company(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    other_company = create_company(db)
    dept = create_department(db, company=other_company)
    position = create_position(db, company=other_company)
    create_employee(
        db,
        dept=dept,
        position=position,
        employee_no="E900",
        name="外司员工",
        hire_date=date(2020, 1, 1),
    )
    content = (
        "工号,考勤日期,打卡时间,打卡结果\nE900,2026-09-01,2026-09-01 08:00,正常\n"
    ).encode()

    foreign = preview_file(
        client,
        superuser_token_headers,
        company_id=company.id,
        data_type="punch",
        content=content,
        file_name="punch.csv",
    )
    own = preview_file(
        client,
        superuser_token_headers,
        company_id=other_company.id,
        data_type="punch",
        content=content,
        file_name="punch.csv",
    )

    assert foreign.status_code == 200, foreign.text
    assert foreign.json()["stats"]["valid_records"] == 0
    assert foreign.json()["stats"]["skip_counts"] == {"unknown_employee": 1}
    assert own.status_code == 200, own.text
    assert own.json()["stats"]["valid_records"] == 1


def test_oa_name_matching_is_scoped_to_the_company(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    other_company = create_company(db)
    for target in (company, other_company):
        dept = create_department(db, company=target)
        position = create_position(db, company=target)
        create_employee(
            db,
            dept=dept,
            position=position,
            employee_no=random_upper_code("E"),
            name="张三",
            hire_date=date(2020, 1, 1),
        )
    content = (
        "创建人,请假类型,请假天数,休息开始时间,休息结束时间,审批结果\n"
        "张三,事假,1,2026-09-10 08:00,2026-09-10 18:00,审批通过\n"
    ).encode()

    response = preview_file(
        client,
        superuser_token_headers,
        company_id=company.id,
        data_type="leave",
        content=content,
        file_name="leave.csv",
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["stats"]["valid_records"] == 1
    assert body["employees"]["duplicate_name"] == 0
    sample_id = body["samples"][0]["employee_id"]
    db.expire_all()
    leave = db.exec(select(OaLeave)).one()
    assert str(leave.employee_id) == sample_id


def test_mapping_template_returns_the_saved_mapping(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    from app.models import ImportMappingTemplate, User

    company = create_company(db)
    user = db.exec(select(User)).first()
    assert user is not None
    template = ImportMappingTemplate(
        company_id=company.id,
        data_type=ImportDataType.PUNCH,
        mapping={"employee_no": {"column": "工号", "index": 0}},
        header_columns=["工号", "考勤日期", "打卡时间", "打卡结果"],
        updated_by=user.id,
    )
    db.add(template)
    db.commit()

    response = client.get(
        TEMPLATE_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "data_type": "punch"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["data_type"] == "punch"
    assert body["mapping"]["employee_no"]["column"] == "工号"
    assert body["header_columns"] == ["工号", "考勤日期", "打卡时间", "打卡结果"]


def test_mapping_template_is_404_when_absent_or_cross_company(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    create_company(db)
    other_company = create_company(db)

    absent = client.get(
        TEMPLATE_URL,
        headers=superuser_token_headers,
        params={"company_id": str(other_company.id), "data_type": "punch"},
    )
    assert absent.status_code == 404
    assert error_detail(absent)["code"] == "not_found"

    unknown_company = client.get(
        TEMPLATE_URL,
        headers=superuser_token_headers,
        params={"company_id": str(uuid.uuid7()), "data_type": "punch"},
    )
    assert unknown_company.status_code == 404


def test_impact_compares_against_the_active_committed_batch(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    employees = seed_fixture_employees(db, company)
    from app.models import User

    user = db.exec(select(User)).first()
    assert user is not None
    old_batch = ImportBatch(
        company_id=company.id,
        data_type=ImportDataType.PUNCH,
        month=date(2026, 9, 1),
        status=ImportBatchStatus.COMMITTED,
        source=ImportSource.UPLOAD,
        file_name="old.csv",
        header_columns=[],
        column_mapping={},
        parser_version=PARSER_VERSION,
        source_rows=10,
        valid_records=10,
        operator_id=user.id,
        committed_at=datetime.now(UTC),
    )
    db.add(old_batch)
    db.commit()
    db.refresh(old_batch)
    from app.models import PunchRecord

    for index, employee_no in enumerate(("E101", "E102", "E103")):
        db.add(
            PunchRecord(
                company_id=company.id,
                batch_id=old_batch.id,
                source_row_number=index + 2,
                employee_id=employees[employee_no].id,
                employee_no_raw=employee_no,
                employee_name_raw="旧",
                department_raw="生产部",
                attendance_date=date(2026, 9, 1),
                punch_time=datetime(2026, 9, 1, 0, index, tzinfo=UTC),
                punch_result_raw="正常",
                raw_row={},
            )
        )
    db.commit()

    response = preview_fixture(
        client, superuser_token_headers, company.id, ImportDataType.PUNCH
    )

    assert response.status_code == 200, response.text
    impact = response.json()["impact"]
    assert impact["current_batch"]["id"] == str(old_batch.id)
    assert impact["current_batch"]["file_name"] == "old.csv"
    assert impact["current_batch"]["valid_records"] == 10
    assert impact["valid_records_delta"] == 27 - 10
    assert impact["employee_overlap"] == 3
    assert impact["employees_added"] == 6
    assert impact["employees_removed"] == 0


def test_preview_cleans_expired_previews_and_keeps_live_ones(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    employees = seed_fixture_employees(db, company)
    user = db.exec(select(User)).first()
    assert user is not None
    now = datetime.now(UTC)
    expired = create_import_batch(
        db,
        company_id=company.id,
        operator_id=user.id,
        expires_at=now - timedelta(hours=1),
        valid_records=1,
    )
    create_punch_record(
        db,
        company_id=company.id,
        batch_id=expired.id,
        employee_id=employees["E101"].id,
    )
    create_import_batch_error(db, batch_id=expired.id)
    live = create_import_batch(
        db,
        company_id=company.id,
        operator_id=user.id,
        expires_at=now + timedelta(hours=1),
    )
    create_punch_record(
        db,
        company_id=company.id,
        batch_id=live.id,
        employee_id=employees["E101"].id,
        source_row_number=3,
    )
    content = (
        "工号,考勤日期,打卡时间,打卡结果\nE101,2026-09-01,2026-09-01 08:18,正常\n"
    ).encode()

    response = preview_file(
        client,
        superuser_token_headers,
        company_id=company.id,
        data_type="punch",
        content=content,
        file_name="punch.csv",
    )

    assert response.status_code == 200, response.text
    db.expire_all()
    discarded = db.get(ImportBatch, expired.id)
    assert discarded is not None
    assert discarded.status.value == "discarded"
    assert discarded.discard_reason == "expired"
    assert discarded.discarded_at is not None
    assert (
        db.exec(
            select(func.count())
            .select_from(PunchRecord)
            .where(PunchRecord.batch_id == expired.id)
        ).one()
        == 0
    )
    assert (
        db.exec(
            select(func.count())
            .select_from(ImportBatchError)
            .where(ImportBatchError.batch_id == expired.id)
        ).one()
        == 0
    )
    untouched = db.get(ImportBatch, live.id)
    assert untouched is not None
    assert untouched.status.value == "preview"
    assert (
        db.exec(
            select(func.count())
            .select_from(PunchRecord)
            .where(PunchRecord.batch_id == live.id)
        ).one()
        == 1
    )
