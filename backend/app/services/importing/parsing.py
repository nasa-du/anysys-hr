"""Shared import file parsing: delimited text and safe XLSX reading.

Parsing is server-side and returns cleaned source rows only; it never touches
the database and never retains the original bytes. Fatal file problems raise
``DomainError`` before a preview batch is created. XLSX archives are inspected
before openpyxl sees them: encrypted or macro workbooks, oversized archives,
too many zip entries, DTDs, and external entities are rejected.

The module is feature-neutral: it imports shared import error codes only, so
attendance and payroll can use the same parser and safety behavior.
"""

import csv
import io
import re
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, time
from enum import StrEnum
from typing import Any

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from app.core.errors import DomainError
from app.services.importing.errors import ImportErrorCode

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_DATA_ROWS = 100_000
# Data rows plus the header/preamble scan window; the exact data-row cap is
# enforced after the header row is known.
MAX_PARSED_ROWS = MAX_DATA_ROWS + 10
TOO_MANY_ROWS_MESSAGE = "数据行超过 100,000 行限制"
MAX_XLSX_ENTRIES = 2_000
MAX_XLSX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
PASTE_DELIMITERS = ("\t", ",", "|")

ZIP_MAGIC = b"PK\x03\x04"
OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_DTD_PATTERN = re.compile(rb"<!(?:DOCTYPE|ENTITY)", re.IGNORECASE)


class FileKind(StrEnum):
    CSV = "csv"
    TSV = "tsv"
    XLSX = "xlsx"


@dataclass(frozen=True)
class SourceRow:
    """One non-empty source row; ``row_number`` is 1-based including the header."""

    row_number: int
    cells: list[str]


@dataclass(frozen=True)
class ParsedSheet:
    """Cleaned rows from one sheet plus the sheet it came from."""

    rows: list[SourceRow]
    sheet_name: str | None = None


def _parse_error(message: str) -> DomainError:
    return DomainError(ImportErrorCode.IMPORT_PARSE_FAILED, message)


def _check_row_budget(row_count: int) -> None:
    if row_count > MAX_PARSED_ROWS:
        raise _parse_error(TOO_MANY_ROWS_MESSAGE)


def _unsupported(message: str = "仅支持 .csv、.tsv、.xlsx 文件") -> DomainError:
    return DomainError(ImportErrorCode.UNSUPPORTED_FILE_TYPE, message)


def detect_file_kind(file_name: str) -> FileKind:
    """Return the parser for a supported extension; legacy and macro files 415."""
    lowered = file_name.strip().lower()
    if lowered.endswith(".csv"):
        return FileKind.CSV
    if lowered.endswith(".tsv"):
        return FileKind.TSV
    if lowered.endswith(".xlsx"):
        return FileKind.XLSX
    if lowered.endswith((".xls", ".xlsm", ".xlsb", ".xltx", ".xltm")):
        raise _unsupported(
            "不支持旧版 .xls 或启用宏的 Excel 文件，请另存为 .xlsx 后重试"
        )
    raise _unsupported()


def parse_upload(
    *, content: bytes, file_name: str, sheet_name: str | None = None
) -> ParsedSheet:
    """Parse an uploaded file after size, extension, and archive checks."""
    if len(content) > MAX_FILE_BYTES:
        raise DomainError(ImportErrorCode.FILE_TOO_LARGE, "文件大小超过 10 MB 限制")
    kind = detect_file_kind(file_name)
    if not content:
        raise _parse_error("文件内容为空")
    if content.startswith(OLE_MAGIC):
        raise _unsupported("不支持旧版 .xls 或加密的 Excel 文件，请另存为 .xlsx 后重试")
    if kind is FileKind.XLSX:
        return _parse_xlsx(content, sheet_name=sheet_name)
    return _parse_delimited(_decode(content), _file_delimiter(kind))


def parse_paste(*, text: str) -> ParsedSheet:
    """Parse pasted text; tab, comma, and pipe are auto-detected."""
    if len(text.encode("utf-8")) > MAX_FILE_BYTES:
        raise DomainError(ImportErrorCode.FILE_TOO_LARGE, "粘贴内容超过 10 MB 限制")
    if not text.strip():
        raise _parse_error("粘贴内容为空")
    return _parse_delimited(text, _paste_delimiter(text))


def _file_delimiter(kind: FileKind) -> str:
    return "\t" if kind is FileKind.TSV else ","


def _decode(content: bytes) -> str:
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            text = content.decode(encoding)
        except UnicodeDecodeError:
            continue
        if "\x00" in text:
            break
        return text
    raise _parse_error("文件编码无法识别，请使用 UTF-8 或 GB18030 编码")


def _paste_delimiter(text: str) -> str:
    """Pick the delimiter with the most occurrences in the first ten lines."""
    lines = [line for line in text.splitlines() if line.strip()][:10]
    scored = [
        (sum(line.count(delimiter) for line in lines), index, delimiter)
        for index, delimiter in enumerate(PASTE_DELIMITERS)
    ]
    count, _, delimiter = max(scored, key=lambda item: (item[0], -item[1]))
    return delimiter if count else ","


def _parse_delimited(text: str, delimiter: str) -> ParsedSheet:
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows: list[SourceRow] = []
    for row_number, raw_cells in enumerate(reader, start=1):
        cells = [cell.strip() for cell in raw_cells]
        if any(cells):
            rows.append(SourceRow(row_number=row_number, cells=cells))
            _check_row_budget(len(rows))
    if not rows:
        raise _parse_error("文件中没有数据")
    return ParsedSheet(rows=_drop_empty_columns(rows))


def _drop_empty_columns(rows: list[SourceRow]) -> list[SourceRow]:
    width = max(len(row.cells) for row in rows)
    padded = [row.cells + [""] * (width - len(row.cells)) for row in rows]
    keep = [index for index in range(width) if any(cells[index] for cells in padded)]
    return [
        SourceRow(
            row_number=row.row_number,
            cells=[cells[index] for index in keep],
        )
        for row, cells in zip(rows, padded, strict=True)
    ]


def _cell_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, time):
        return value.strftime("%H:%M:%S")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _check_archive(content: bytes) -> None:
    """Validate the zip container before openpyxl parses any XML."""
    if not content.startswith(ZIP_MAGIC):
        raise _parse_error("文件不是有效的 XLSX")
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_XLSX_ENTRIES:
                raise _parse_error("XLSX 压缩包条目过多")
            if sum(info.file_size for info in infos) > MAX_XLSX_UNCOMPRESSED_BYTES:
                raise _parse_error("XLSX 解压后体积超过 50 MB 限制")
            for info in infos:
                if info.flag_bits & 0x1:
                    raise _unsupported("不支持加密的 Excel 文件")
                name = info.filename.lower()
                if name.endswith("vbaproject.bin"):
                    raise _unsupported("不支持启用宏的 Excel 文件")
                if name.endswith((".xml", ".rels")) and _DTD_PATTERN.search(
                    archive.read(info)
                ):
                    raise _parse_error("XLSX 包含不允许的 DTD 或外部实体声明")
    except DomainError:
        raise
    except zipfile.BadZipFile, zipfile.LargeZipFile, RuntimeError, NotImplementedError:
        raise _parse_error("文件不是有效的 XLSX")


def _open_workbook(content: bytes) -> Any:
    try:
        return load_workbook(
            io.BytesIO(content), read_only=True, data_only=True, keep_links=False
        )
    except DomainError:
        raise
    except Exception as exc:  # openpyxl raises several XML/zip exceptions
        raise _parse_error("文件不是有效的 XLSX") from exc


def _sheet_is_non_empty(sheet: Worksheet) -> bool:
    for row in sheet.iter_rows(values_only=True):
        if any(_cell_text(value) for value in row):
            return True
    return False


def _parse_xlsx(content: bytes, *, sheet_name: str | None) -> ParsedSheet:
    _check_archive(content)
    workbook = _open_workbook(content)
    try:
        titles = list(workbook.sheetnames)
        non_empty = [title for title in titles if _sheet_is_non_empty(workbook[title])]
    finally:
        workbook.close()

    if sheet_name is not None and sheet_name not in titles:
        raise _parse_error(f"工作表不存在：{sheet_name}")
    if sheet_name is None:
        if not non_empty:
            raise _parse_error("工作表中没有数据")
        if len(non_empty) > 1:
            raise DomainError(
                ImportErrorCode.SHEET_REQUIRED,
                "文件包含多个非空工作表，请指定 sheet_name",
                field_errors={"sheet_name": ",".join(non_empty)},
            )
        chosen = non_empty[0]
    else:
        chosen = sheet_name

    workbook = _open_workbook(content)
    try:
        sheet = workbook[chosen]
        rows: list[SourceRow] = []
        for row_number, values in enumerate(sheet.iter_rows(values_only=True), start=1):
            cells = [_cell_text(value) for value in values]
            if any(cells):
                rows.append(SourceRow(row_number=row_number, cells=cells))
                _check_row_budget(len(rows))
    finally:
        workbook.close()

    if not rows:
        raise _parse_error("工作表中没有数据")
    return ParsedSheet(rows=_drop_empty_columns(rows), sheet_name=chosen)
