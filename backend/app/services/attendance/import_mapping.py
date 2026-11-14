"""Canonical import column mappings, aliases, and header detection (6.2).

The four data types share one detection pipeline: normalize header text, match
aliases to canonical fields, apply explicit overrides, list ignored columns,
and treat a missing required column or a source column assigned to two fields
as a fatal preview error. There is no positional fallback.
"""

import unicodedata
from dataclasses import dataclass
from typing import Any

from app.core.errors import DomainError
from app.enums import ImportDataType
from app.services.attendance import import_parsing
from app.services.attendance.errors import AttendanceErrorCode

HEADER_SCAN_ROWS = 10
HEADER_MATCH = "缺少必填列"
COLUMN_MISSING = "列不存在"
DUPLICATE_COLUMN = "列重复映射"
UNKNOWN_FIELD_TEMPLATE = "未知列映射字段：{field}"
NO_HEADER_MESSAGE = "无法识别表头，请确认文件包含规范的中文列名"
MISSING_COLUMNS_MESSAGE = "缺少必填列：{columns}"
DUPLICATE_MAPPING_MESSAGE = "同一列不能映射到多个字段：{columns}"


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
    data_rows: list[import_parsing.SourceRow]
    mapping: dict[str, ColumnRef]
    ignored_columns: list[str]

    @property
    def mapping_snapshot(self) -> dict[str, dict[str, Any]]:
        return {
            field: {"column": ref.column, "index": ref.index}
            for field, ref in self.mapping.items()
        }


CANONICAL_MAPPINGS: dict[ImportDataType, dict[str, FieldSpec]] = {
    ImportDataType.PUNCH: {
        "employee_no": FieldSpec(True, ("工号", "员工工号", "员工编号")),
        "employee_name": FieldSpec(False, ("姓名", "员工姓名")),
        "department_raw": FieldSpec(False, ("部门", "考勤部门")),
        "attendance_date": FieldSpec(True, ("考勤日期", "日期")),
        "punch_time": FieldSpec(True, ("打卡时间", "实际打卡时间")),
        "scheduled_time": FieldSpec(False, ("考勤时间", "应打卡时间")),
        "punch_result": FieldSpec(True, ("打卡结果", "结果")),
        "device_raw": FieldSpec(False, ("打卡设备", "设备")),
        "address_raw": FieldSpec(False, ("打卡地址", "地址")),
    },
    ImportDataType.TRIP: {
        "employee_name": FieldSpec(True, ("出差人",)),
        "application_type_raw": FieldSpec(False, ("申请类型",)),
        "department_raw": FieldSpec(False, ("出差人部门", "部门")),
        "start_at": FieldSpec(True, ("开始时间", "出差开始时间")),
        "end_at": FieldSpec(True, ("结束时间", "出差结束时间")),
        "days_declared": FieldSpec(False, ("出差天数",)),
        "reason": FieldSpec(False, ("外出事由", "事由")),
        "approval_result": FieldSpec(True, ("审批结果",)),
        "approval_status": FieldSpec(False, ("审批状态",)),
        "approval_no": FieldSpec(False, ("审批编号", "单号")),
    },
    ImportDataType.OT: {
        "employee_name": FieldSpec(True, ("创建人",)),
        "department_raw": FieldSpec(False, ("部门", "创建人部门")),
        "start_at": FieldSpec(True, ("加班开始时间", "开始时间")),
        "end_at": FieldSpec(True, ("加班结束时间", "结束时间")),
        "declared_raw": FieldSpec(
            False, ("加班时长（天/小时）", "加班时长(天/小时)", "加班时长")
        ),
        "reason": FieldSpec(False, ("加班原因",)),
        "approval_result": FieldSpec(True, ("审批结果",)),
        "approval_status": FieldSpec(False, ("审批状态",)),
        "approval_no": FieldSpec(False, ("审批编号", "单号")),
    },
    ImportDataType.LEAVE: {
        "employee_name": FieldSpec(True, ("创建人",)),
        "department_raw": FieldSpec(False, ("部门", "创建人部门")),
        "leave_type_raw": FieldSpec(True, ("请假类型",)),
        "days": FieldSpec(True, ("请假天数",)),
        "rest_start_at": FieldSpec(True, ("休息开始时间",)),
        "rest_end_at": FieldSpec(True, ("休息结束时间",)),
        "work_start_at": FieldSpec(False, ("上班开始时间",)),
        "work_end_at": FieldSpec(False, ("上班结束时间",)),
        "balance_days_declared": FieldSpec(False, ("结余补休天数",)),
        "reason": FieldSpec(False, ("请假说明", "说明")),
        "approval_result": FieldSpec(True, ("审批结果",)),
        "approval_status": FieldSpec(False, ("审批状态",)),
        "approval_no": FieldSpec(False, ("审批编号", "单号")),
    },
}


def _normalize_header(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return "".join(normalized.split()).lower()


_NORMALIZED_ALIASES: dict[ImportDataType, dict[str, tuple[str, ...]]] = {
    data_type: {
        field: tuple(_normalize_header(alias) for alias in spec.aliases)
        for field, spec in fields.items()
    }
    for data_type, fields in CANONICAL_MAPPINGS.items()
}


def _required_fields(data_type: ImportDataType) -> list[str]:
    return [
        field for field, spec in CANONICAL_MAPPINGS[data_type].items() if spec.required
    ]


def _field_label(data_type: ImportDataType, field: str) -> str:
    return CANONICAL_MAPPINGS[data_type][field].aliases[0]


def _missing_required_error(
    data_type: ImportDataType, fields: list[str]
) -> DomainError:
    return DomainError(
        AttendanceErrorCode.MISSING_REQUIRED_COLUMN,
        MISSING_COLUMNS_MESSAGE.format(
            columns="、".join(_field_label(data_type, field) for field in fields)
        ),
        field_errors=dict.fromkeys(fields, HEADER_MATCH),
    )


def detect_header(
    sheet: import_parsing.ParsedSheet,
    data_type: ImportDataType,
    *,
    overrides: dict[str, str | int | None] | None = None,
) -> DetectedTable:
    """Detect the header row, resolve the mapping, and split off data rows."""
    if not sheet.rows:
        raise _missing_required_error(data_type, _required_fields(data_type))

    aliases = _NORMALIZED_ALIASES[data_type]
    scan = sheet.rows[:HEADER_SCAN_ROWS]
    scores = [_row_match_count(row.cells, aliases) for row in scan]
    best = max(scores)
    if best == 0:
        raise DomainError(
            AttendanceErrorCode.MISSING_REQUIRED_COLUMN,
            NO_HEADER_MESSAGE,
            field_errors=dict.fromkeys(_required_fields(data_type), HEADER_MATCH),
        )
    header_index = scores.index(best)
    header_row = sheet.rows[header_index]
    data_rows = sheet.rows[header_index + 1 :]
    if len(data_rows) > import_parsing.MAX_DATA_ROWS:
        raise DomainError(
            AttendanceErrorCode.IMPORT_PARSE_FAILED,
            import_parsing.TOO_MANY_ROWS_MESSAGE,
        )

    header_columns = list(header_row.cells)
    mapping = _detect_mapping(header_columns, data_type)
    if overrides:
        mapping = _apply_overrides(header_columns, data_type, mapping, overrides)
    _validate_mapping(header_columns, data_type, mapping)

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
    normalized = [_normalize_header(cell) for cell in cells]
    return sum(
        1
        for field_aliases in aliases.values()
        if any(alias in normalized for alias in field_aliases)
    )


def _detect_mapping(
    header_columns: list[str], data_type: ImportDataType
) -> dict[str, ColumnRef]:
    normalized = [_normalize_header(column) for column in header_columns]
    mapping: dict[str, ColumnRef] = {}
    for field, aliases in _NORMALIZED_ALIASES[data_type].items():
        for index, column in enumerate(normalized):
            if column in aliases:
                mapping[field] = ColumnRef(column=header_columns[index], index=index)
                break
    return mapping


def _apply_overrides(
    header_columns: list[str],
    data_type: ImportDataType,
    mapping: dict[str, ColumnRef],
    overrides: dict[str, str | int | None],
) -> dict[str, ColumnRef]:
    fields = CANONICAL_MAPPINGS[data_type]
    for field in overrides:
        if field not in fields:
            raise DomainError(
                AttendanceErrorCode.IMPORT_PARSE_FAILED,
                f"未知列映射字段：{field}",
                field_errors={
                    "column_mapping": UNKNOWN_FIELD_TEMPLATE.format(field=field)
                },
            )

    normalized = [_normalize_header(column) for column in header_columns]
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
            AttendanceErrorCode.MISSING_REQUIRED_COLUMN,
            COLUMN_MISSING,
            field_errors={field: COLUMN_MISSING},
        )
    if isinstance(value, str):
        target = _normalize_header(value)
        for index, column in enumerate(normalized):
            if column == target:
                return index
        raise DomainError(
            AttendanceErrorCode.MISSING_REQUIRED_COLUMN,
            COLUMN_MISSING,
            field_errors={field: COLUMN_MISSING},
        )
    raise _invalid_override(field)


def _invalid_override(field: str) -> DomainError:
    message = f"列映射值无效：{field}"
    return DomainError(
        AttendanceErrorCode.IMPORT_PARSE_FAILED,
        message,
        field_errors={"column_mapping": message},
    )


def _validate_mapping(
    header_columns: list[str],
    data_type: ImportDataType,
    mapping: dict[str, ColumnRef],
) -> None:
    fields = CANONICAL_MAPPINGS[data_type]
    missing = [
        field
        for field, spec in fields.items()
        if spec.required and field not in mapping
    ]
    if missing:
        raise _missing_required_error(data_type, missing)

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
            AttendanceErrorCode.MISSING_REQUIRED_COLUMN,
            DUPLICATE_MAPPING_MESSAGE.format(columns=columns),
            field_errors=duplicated,
        )


def normalize_overrides(raw: Any) -> dict[str, str | int | None]:
    """Validate the shape of a decoded ``column_mapping`` form field."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        message = "列映射格式不正确"
        raise DomainError(
            AttendanceErrorCode.IMPORT_PARSE_FAILED,
            message,
            field_errors={"column_mapping": message},
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
