"""Generic import header detection and column mapping.

The caller supplies a field registry (required flag and aliases); this module
finds the header row within the first ten non-empty rows, maps aliases to
columns, applies explicit overrides, and lists ignored columns. There is no
positional fallback. Fatal problems raise ``DomainError`` with shared import
codes, so each feature module keeps its own success-row vocabulary.

The module is feature-neutral: it carries no module's column registry and
imports no feature code.
"""

import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.core.errors import DomainError
from app.services.importing.errors import ImportErrorCode
from app.services.importing.parsing import (
    MAX_DATA_ROWS,
    TOO_MANY_ROWS_MESSAGE,
    ParsedSheet,
    SourceRow,
)

HEADER_SCAN_ROWS = 10
HEADER_MATCH = "缺少必填列"
COLUMN_MISSING = "列不存在"
DUPLICATE_COLUMN = "列重复映射"
UNKNOWN_FIELD_TEMPLATE = "未知列映射字段：{field}"
NO_HEADER_MESSAGE = "无法识别表头，请确认文件包含规范的中文列名"
MISSING_COLUMNS_MESSAGE = "缺少必填列：{columns}"
DUPLICATE_MAPPING_MESSAGE = "同一列不能映射到多个字段：{columns}"
INVALID_MAPPING_MESSAGE = "列映射格式不正确"


@dataclass(frozen=True)
class FieldSpec:
    required: bool
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class ColumnRef:
    column: str
    index: int


@dataclass(frozen=True)
class DetectedTable:
    header_columns: list[str]
    header_row_number: int
    data_rows: list[SourceRow]
    mapping: dict[str, ColumnRef]
    ignored_columns: list[str]

    @property
    def mapping_snapshot(self) -> dict[str, dict[str, Any]]:
        return {
            field: {"column": ref.column, "index": ref.index}
            for field, ref in self.mapping.items()
        }


def normalize_header(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return "".join(normalized.split()).lower()


def _normalized_aliases(
    fields: Mapping[str, FieldSpec],
) -> dict[str, tuple[str, ...]]:
    return {
        field: tuple(normalize_header(alias) for alias in spec.aliases)
        for field, spec in fields.items()
    }


def _required_fields(fields: Mapping[str, FieldSpec]) -> list[str]:
    return [field for field, spec in fields.items() if spec.required]


def _missing_required_error(
    fields: Mapping[str, FieldSpec], missing: list[str]
) -> DomainError:
    return DomainError(
        ImportErrorCode.MISSING_REQUIRED_COLUMN,
        MISSING_COLUMNS_MESSAGE.format(
            columns="、".join(fields[field].aliases[0] for field in missing)
        ),
        field_errors=dict.fromkeys(missing, HEADER_MATCH),
    )


def detect_header(
    sheet: ParsedSheet,
    fields: Mapping[str, FieldSpec],
    *,
    overrides: dict[str, str | int | None] | None = None,
) -> DetectedTable:
    """Detect the header row, resolve the mapping, and split off data rows."""
    if not sheet.rows:
        raise _missing_required_error(fields, _required_fields(fields))

    aliases = _normalized_aliases(fields)
    scan = sheet.rows[:HEADER_SCAN_ROWS]
    scores = [_row_match_count(row.cells, aliases) for row in scan]
    best = max(scores)
    if best == 0:
        raise DomainError(
            ImportErrorCode.MISSING_REQUIRED_COLUMN,
            NO_HEADER_MESSAGE,
            field_errors=dict.fromkeys(_required_fields(fields), HEADER_MATCH),
        )
    header_index = scores.index(best)
    header_row = sheet.rows[header_index]
    data_rows = sheet.rows[header_index + 1 :]
    if len(data_rows) > MAX_DATA_ROWS:
        raise DomainError(
            ImportErrorCode.IMPORT_PARSE_FAILED,
            TOO_MANY_ROWS_MESSAGE,
        )

    header_columns = list(header_row.cells)
    mapping = _detect_mapping(header_columns, aliases)
    if overrides:
        mapping = _apply_overrides(header_columns, fields, mapping, overrides)
    _validate_mapping(header_columns, fields, mapping)

    used = {ref.index for ref in mapping.values()}
    ignored = [
        column for index, column in enumerate(header_columns) if index not in used
    ]
    return DetectedTable(
        header_columns=header_columns,
        header_row_number=header_row.row_number,
        data_rows=data_rows,
        mapping=mapping,
        ignored_columns=ignored,
    )


def _row_match_count(cells: list[str], aliases: dict[str, tuple[str, ...]]) -> int:
    normalized = [normalize_header(cell) for cell in cells]
    return sum(
        1
        for field_aliases in aliases.values()
        if any(alias in normalized for alias in field_aliases)
    )


def _detect_mapping(
    header_columns: list[str], aliases: dict[str, tuple[str, ...]]
) -> dict[str, ColumnRef]:
    normalized = [normalize_header(column) for column in header_columns]
    mapping: dict[str, ColumnRef] = {}
    for field, field_aliases in aliases.items():
        for index, column in enumerate(normalized):
            if column in field_aliases:
                mapping[field] = ColumnRef(column=header_columns[index], index=index)
                break
    return mapping


def _apply_overrides(
    header_columns: list[str],
    fields: Mapping[str, FieldSpec],
    mapping: dict[str, ColumnRef],
    overrides: dict[str, str | int | None],
) -> dict[str, ColumnRef]:
    for field in overrides:
        if field not in fields:
            raise DomainError(
                ImportErrorCode.IMPORT_PARSE_FAILED,
                f"未知列映射字段：{field}",
                field_errors={
                    "column_mapping": UNKNOWN_FIELD_TEMPLATE.format(field=field)
                },
            )

    normalized = [normalize_header(column) for column in header_columns]
    resolved = dict(mapping)
    for field, value in overrides.items():
        if value is None:
            resolved.pop(field, None)
            continue
        index = _resolve_override(header_columns, normalized, field, value)
        resolved[field] = ColumnRef(column=header_columns[index], index=index)
    return resolved


def _resolve_override(
    header_columns: list[str],
    normalized: list[str],
    field: str,
    value: str | int,
) -> int:
    if isinstance(value, bool):
        raise _invalid_override(field)
    if isinstance(value, int):
        if 0 <= value < len(header_columns):
            return value
        raise DomainError(
            ImportErrorCode.MISSING_REQUIRED_COLUMN,
            COLUMN_MISSING,
            field_errors={field: COLUMN_MISSING},
        )
    if isinstance(value, str):
        target = normalize_header(value)
        for index, column in enumerate(normalized):
            if column == target:
                return index
        raise DomainError(
            ImportErrorCode.MISSING_REQUIRED_COLUMN,
            COLUMN_MISSING,
            field_errors={field: COLUMN_MISSING},
        )
    raise _invalid_override(field)


def _invalid_override(field: str) -> DomainError:
    message = f"列映射值无效：{field}"
    return DomainError(
        ImportErrorCode.IMPORT_PARSE_FAILED,
        message,
        field_errors={"column_mapping": message},
    )


def _validate_mapping(
    header_columns: list[str],
    fields: Mapping[str, FieldSpec],
    mapping: dict[str, ColumnRef],
) -> None:
    missing = [
        field
        for field, spec in fields.items()
        if spec.required and field not in mapping
    ]
    if missing:
        raise _missing_required_error(fields, missing)

    by_index: dict[int, list[str]] = {}
    for field, ref in mapping.items():
        by_index.setdefault(ref.index, []).append(field)
    duplicated = {
        field: DUPLICATE_COLUMN
        for assigned in by_index.values()
        if len(assigned) > 1
        for field in assigned
    }
    if duplicated:
        columns = "、".join(
            header_columns[index]
            for index, assigned in by_index.items()
            if len(assigned) > 1
        )
        raise DomainError(
            ImportErrorCode.MISSING_REQUIRED_COLUMN,
            DUPLICATE_MAPPING_MESSAGE.format(columns=columns),
            field_errors=duplicated,
        )


def normalize_overrides(raw: Any) -> dict[str, str | int | None]:
    """Validate the shape of a decoded ``column_mapping`` form field."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise DomainError(
            ImportErrorCode.IMPORT_PARSE_FAILED,
            INVALID_MAPPING_MESSAGE,
            field_errors={"column_mapping": INVALID_MAPPING_MESSAGE},
        )
    overrides: dict[str, str | int | None] = {}
    for field, value in raw.items():
        if not isinstance(field, str):
            raise _invalid_override(str(field))
        if value is None or isinstance(value, str):
            overrides[field] = value
        elif isinstance(value, int) and not isinstance(value, bool):
            overrides[field] = value
        else:
            raise _invalid_override(field)
    return overrides
