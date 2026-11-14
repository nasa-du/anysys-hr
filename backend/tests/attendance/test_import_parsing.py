"""Import file parsing contracts (spec sections 6.1 and 8.8).

Seam: ``app.services.attendance.import_parsing``. Parsing turns uploaded bytes
or pasted text into cleaned source rows and detects the header row; it never
touches the database. Fatal problems raise ``DomainError`` so the preview
endpoint can return 4xx without creating a batch.
"""

import io
from typing import Any

import pytest
from openpyxl import Workbook

from app.core.errors import DomainError
from app.enums import ImportDataType
from app.services.attendance import import_mapping, import_parsing


def parse_csv(content: str, *, file_name: str = "punch.csv") -> Any:
    parsed = import_parsing.parse_upload(
        content=content.encode("utf-8"), file_name=file_name
    )
    return import_mapping.detect_header(parsed, ImportDataType.PUNCH)


def xlsx_bytes(rows: list[list[Any]], *, sheet_name: str = "Sheet1") -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_name
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


PUNCH_HEADER = ["工号", "姓名", "部门", "考勤日期", "打卡时间", "打卡结果"]


def test_utf8_bom_is_stripped_from_the_header() -> None:
    content = (
        "﻿"
        + ",".join(PUNCH_HEADER)
        + "\nE101,冯芷茵,生产部,2026-09-01,2026-09-01 08:18,正常\n"
    )

    table = parse_csv(content)

    assert table.header_columns[0] == "工号"
    assert table.data_rows[0].cells[0] == "E101"


def test_gb18030_is_the_encoding_fallback() -> None:
    text = (
        ",".join(PUNCH_HEADER)
        + "\nE101,冯芷茵,生产部,2026-09-01,2026-09-01 08:18,正常\n"
    )
    content = text.encode("gb18030")

    parsed = import_parsing.parse_upload(content=content, file_name="punch.csv")
    table = import_mapping.detect_header(parsed, ImportDataType.PUNCH)

    assert table.header_columns[1] == "姓名"
    assert table.data_rows[0].cells[1] == "冯芷茵"


def test_tsv_uses_the_tab_delimiter() -> None:
    content = (
        "\t".join(PUNCH_HEADER)
        + "\nE101\t冯芷茵\t生产部\t2026-09-01\t2026-09-01 08:18\t正常\n"
    )

    parsed = import_parsing.parse_upload(
        content=content.encode("utf-8"), file_name="punch.tsv"
    )
    table = import_mapping.detect_header(parsed, ImportDataType.PUNCH)

    assert table.data_rows[0].cells[5] == "正常"


def test_paste_accepts_tab_comma_and_pipe_delimiters() -> None:
    for delimiter in ("\t", ",", "|"):
        text = (
            delimiter.join(PUNCH_HEADER)
            + "\n"
            + delimiter.join(
                ["E101", "冯芷茵", "生产部", "2026-09-01", "2026-09-01 08:18", "正常"]
            )
            + "\n"
        )

        parsed = import_parsing.parse_paste(text=text)
        table = import_mapping.detect_header(parsed, ImportDataType.PUNCH)

        assert table.data_rows[0].cells[0] == "E101", delimiter


def test_header_is_detected_within_the_first_ten_non_empty_rows() -> None:
    content = "\n".join(
        [
            "某公司考勤导出",
            "",
            "\t".join(PUNCH_HEADER),
            "\t".join(
                ["E101", "冯芷茵", "生产部", "2026-09-01", "2026-09-01 08:18", "正常"]
            ),
        ]
    )

    parsed = import_parsing.parse_paste(text=content)
    table = import_mapping.detect_header(parsed, ImportDataType.PUNCH)

    assert table.header_row_number == 3
    assert table.data_rows[0].row_number == 4
    assert table.header_columns == PUNCH_HEADER


def test_fully_empty_rows_and_columns_are_dropped() -> None:
    content = "\n".join(
        [
            "工号,,姓名,,部门,考勤日期,打卡时间,打卡结果",
            ",,,,,,,",
            "E101,,冯芷茵,,生产部,2026-09-01,2026-09-01 08:18,正常",
            ",,,,,,,",
        ]
    )

    parsed = import_parsing.parse_paste(text=content)
    table = import_mapping.detect_header(parsed, ImportDataType.PUNCH)

    assert table.header_columns == [
        "工号",
        "姓名",
        "部门",
        "考勤日期",
        "打卡时间",
        "打卡结果",
    ]
    assert table.data_rows[0].cells == [
        "E101",
        "冯芷茵",
        "生产部",
        "2026-09-01",
        "2026-09-01 08:18",
        "正常",
    ]
    assert table.data_rows[0].row_number == 3


def test_cells_are_trimmed_and_headers_are_full_width_normalized() -> None:
    content = "\n".join(
        [
            " 工号 ,　姓名　,部门,考勤日期,打卡时间,打卡结果 ",
            " E101 , 冯芷茵 ,生产部,2026-09-01,2026-09-01 08:18,正常 ",
        ]
    )

    parsed = import_parsing.parse_paste(text=content)
    table = import_mapping.detect_header(parsed, ImportDataType.PUNCH)

    assert table.header_columns == PUNCH_HEADER
    assert table.data_rows[0].cells[0] == "E101"


def test_full_width_brackets_in_headers_still_match_aliases() -> None:
    header = [
        "创建人",
        "部门",
        "加班开始时间",
        "加班结束时间",
        "加班时长(天/小时)",
        "审批结果",
    ]
    content = "\n".join(
        [
            ",".join(header),
            "黄国锋,生产部,2026-09-14 08:00,2026-09-14 17:30,8,审批通过",
        ]
    )

    parsed = import_parsing.parse_paste(text=content)
    table = import_mapping.detect_header(parsed, ImportDataType.OT)

    assert table.mapping["declared_raw"].column == "加班时长(天/小时)"


def test_unsupported_extensions_are_rejected() -> None:
    for file_name in ("legacy.xls", "macro.xlsm", "notes.txt", "noext"):
        with pytest.raises(DomainError) as exc_info:
            import_parsing.parse_upload(content=b"data", file_name=file_name)
        assert exc_info.value.code == "unsupported_file_type", file_name


def test_files_over_ten_megabytes_are_rejected() -> None:
    content = b"a" * (import_parsing.MAX_FILE_BYTES + 1)

    with pytest.raises(DomainError) as exc_info:
        import_parsing.parse_upload(content=content, file_name="big.csv")

    assert exc_info.value.code == "file_too_large"


def test_paste_over_ten_megabytes_is_rejected() -> None:
    with pytest.raises(DomainError) as exc_info:
        import_parsing.parse_paste(text="a" * (import_parsing.MAX_FILE_BYTES + 1))

    assert exc_info.value.code == "file_too_large"


def test_more_than_100_000_data_rows_are_rejected() -> None:
    header = ",".join(PUNCH_HEADER) + "\n"
    row = "E101,冯芷茵,生产部,2026-09-01,2026-09-01 08:18,正常\n"
    content = (header + row * (import_parsing.MAX_DATA_ROWS + 1)).encode("utf-8")

    parsed = import_parsing.parse_upload(content=content, file_name="punch.csv")
    with pytest.raises(DomainError) as exc_info:
        import_mapping.detect_header(parsed, ImportDataType.PUNCH)

    assert exc_info.value.code == "import_parse_failed"


def test_far_more_than_100_000_rows_are_rejected_before_header_detection() -> None:
    header = ",".join(PUNCH_HEADER) + "\n"
    row = "E101,冯芷茵,生产部,2026-09-01,2026-09-01 08:18,正常\n"
    content = (header + row * (import_parsing.MAX_PARSED_ROWS + 1)).encode("utf-8")

    with pytest.raises(DomainError) as exc_info:
        import_parsing.parse_upload(content=content, file_name="punch.csv")

    assert exc_info.value.code == "import_parse_failed"


def test_a_file_without_a_recognizable_header_is_fatal() -> None:
    content = "name,age\nAlice,30\n"

    parsed = import_parsing.parse_paste(text=content)
    with pytest.raises(DomainError) as exc_info:
        import_mapping.detect_header(parsed, ImportDataType.PUNCH)

    assert exc_info.value.code == "missing_required_column"
    assert exc_info.value.field_errors["employee_no"] == "缺少必填列"


def test_xlsx_parses_the_single_non_empty_sheet() -> None:
    content = xlsx_bytes(
        [
            ["考勤导出"],
            PUNCH_HEADER,
            ["E101", "冯芷茵", "生产部", "2026-09-01", "2026-09-01 08:18", "正常"],
        ]
    )

    parsed = import_parsing.parse_upload(content=content, file_name="punch.xlsx")
    table = import_mapping.detect_header(parsed, ImportDataType.PUNCH)

    assert parsed.sheet_name == "Sheet1"
    assert table.header_row_number == 2
    assert table.data_rows[0].cells[0] == "E101"


def test_xlsx_skips_empty_sheets_and_requires_sheet_name_when_ambiguous() -> None:
    workbook = Workbook()
    empty = workbook.active
    empty.title = "空表"
    empty.append([None, None])
    first = workbook.create_sheet("九月")
    first.append(PUNCH_HEADER)
    first.append(["E101", "冯芷茵", "生产部", "2026-09-01", "2026-09-01 08:18", "正常"])
    second = workbook.create_sheet("十月")
    second.append(PUNCH_HEADER)
    second.append(
        ["E101", "冯芷茵", "生产部", "2026-10-01", "2026-10-01 08:18", "正常"]
    )
    buffer = io.BytesIO()
    workbook.save(buffer)
    content = buffer.getvalue()

    with pytest.raises(DomainError) as exc_info:
        import_parsing.parse_upload(content=content, file_name="punch.xlsx")
    assert exc_info.value.code == "sheet_required"
    assert exc_info.value.field_errors["sheet_name"] == "九月,十月"

    parsed = import_parsing.parse_upload(
        content=content, file_name="punch.xlsx", sheet_name="十月"
    )
    table = import_mapping.detect_header(parsed, ImportDataType.PUNCH)
    assert parsed.sheet_name == "十月"
    assert table.data_rows[0].cells[3] == "2026-10-01"


def test_unknown_sheet_name_is_fatal() -> None:
    content = xlsx_bytes([PUNCH_HEADER])

    with pytest.raises(DomainError) as exc_info:
        import_parsing.parse_upload(
            content=content, file_name="punch.xlsx", sheet_name="不存在"
        )

    assert exc_info.value.code == "import_parse_failed"
