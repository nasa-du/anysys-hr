"""Canonical attendance import column mappings and aliases (6.2).

The four attendance data types share one detection pipeline supplied by
``app.services.importing.header``: normalize header text, match aliases to
canonical fields, apply explicit overrides, list ignored columns, and treat a
missing required column or a source column assigned to two fields as a fatal
preview error. There is no positional fallback.

This module only supplies the attendance field registries and keeps the
attendance-facing names stable.
"""

from app.enums import ImportDataType
from app.services.importing import header
from app.services.importing.header import (
    COLUMN_MISSING,
    DUPLICATE_COLUMN,
    HEADER_MATCH,
    HEADER_SCAN_ROWS,
    NO_HEADER_MESSAGE,
    ColumnRef,
    DetectedTable,
    FieldSpec,
    normalize_overrides,
)
from app.services.importing.parsing import ParsedSheet

__all__ = [
    "CANONICAL_MAPPINGS",
    "COLUMN_MISSING",
    "DUPLICATE_COLUMN",
    "HEADER_MATCH",
    "HEADER_SCAN_ROWS",
    "NO_HEADER_MESSAGE",
    "ColumnRef",
    "DetectedTable",
    "FieldSpec",
    "detect_header",
    "normalize_overrides",
]

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


def detect_header(
    sheet: ParsedSheet,
    data_type: ImportDataType,
    *,
    overrides: dict[str, str | int | None] | None = None,
) -> DetectedTable:
    """Detect the header row using the attendance registry for ``data_type``."""
    return header.detect_header(
        sheet, CANONICAL_MAPPINGS[data_type], overrides=overrides
    )
