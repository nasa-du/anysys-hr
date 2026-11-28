"""Shared import parser and header detection (payroll spec 7.3).

Seam: ``app.services.importing``. The shared module owns file/format/encoding/
limit handling and generic header detection so attendance uses it today and
payroll uses it later; it imports neither module's code and carries no
module-specific column registry.
"""

from types import ModuleType

import pytest

from app.core.errors import DomainError
from app.services.attendance.errors import AttendanceErrorCode
from app.services.importing import header, parsing
from app.services.importing.errors import ImportErrorCode
from tests.utils.source_imports import imported_modules

PAYROLL_FIELDS = {
    "employee_no": header.FieldSpec(required=True, aliases=("工号",)),
    "employee_name": header.FieldSpec(required=False, aliases=("姓名",)),
    "phone_allowance": header.FieldSpec(required=False, aliases=("话费", "电话补贴")),
    "tax": header.FieldSpec(required=False, aliases=("本期个税", "个税")),
}


def test_shared_parser_detects_a_header_from_a_caller_supplied_field_registry() -> None:
    parsed = parsing.parse_paste(
        text="工号,姓名,话费,本期个税\nE101,冯芷茵,100.00,-20.00\n"
    )

    table = header.detect_header(parsed, PAYROLL_FIELDS)

    assert table.header_columns == ["工号", "姓名", "话费", "本期个税"]
    assert table.header_row_number == 1
    assert table.mapping["phone_allowance"].index == 2
    assert table.data_rows[0].cells == ["E101", "冯芷茵", "100.00", "-20.00"]


def test_shared_header_detection_reports_missing_required_columns() -> None:
    parsed = parsing.parse_paste(text="姓名\n冯芷茵\n")

    with pytest.raises(DomainError) as exc_info:
        header.detect_header(parsed, PAYROLL_FIELDS)

    assert exc_info.value.code == "missing_required_column"
    assert exc_info.value.field_errors == {"employee_no": "缺少必填列"}


def test_shared_parser_keeps_the_documented_file_and_row_limits() -> None:
    assert parsing.MAX_FILE_BYTES == 10 * 1024 * 1024
    assert parsing.MAX_DATA_ROWS == 100_000
    assert header.HEADER_SCAN_ROWS == 10

    with pytest.raises(DomainError) as exc_info:
        parsing.parse_upload(
            content=b"a" * (parsing.MAX_FILE_BYTES + 1), file_name="data.csv"
        )

    assert exc_info.value.code == "file_too_large"


def test_shared_import_codes_stay_compatible_with_the_attendance_vocabulary() -> None:
    attendance_codes = {code.value for code in AttendanceErrorCode}

    assert {code.value for code in ImportErrorCode} <= attendance_codes


@pytest.mark.parametrize("module", [parsing, header])
def test_shared_import_modules_import_no_feature_module(module: ModuleType) -> None:
    imported = imported_modules(module)

    assert not any(
        name.startswith(("app.services.attendance", "app.services.payroll"))
        for name in imported
    ), imported
