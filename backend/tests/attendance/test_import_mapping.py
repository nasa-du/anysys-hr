"""Column mapping and alias detection (spec section 6.2).

Seam: ``app.services.attendance.import_mapping``. Detection maps canonical
fields to source columns, applies overrides, lists ignored columns, and treats
missing required columns or duplicate assignments as fatal preview errors.
"""

import pytest

from app.core.errors import DomainError
from app.enums import ImportDataType
from app.services.attendance import import_mapping, import_parsing

PUNCH_HEADER = ["工号", "姓名", "部门", "考勤日期", "打卡时间", "打卡结果", "打卡设备", "打卡地址", "考勤时间"]

TRIP_HEADER = [
    "序号",
    "申请类型",
    "出差人部门",
    "出差人",
    "开始时间",
    "结束时间",
    "出差天数",
    "外出事由",
    "审批编号",
    "审批结果",
    "审批状态",
]

OT_HEADER = [
    "序号",
    "部门",
    "加班开始时间",
    "加班结束时间",
    "加班时长（天/小时）",
    "加班原因",
    "审批编号",
    "创建人",
    "审批结果",
    "审批状态",
    "创建人部门",
]

LEAVE_HEADER = [
    "部门",
    "请假类型",
    "请假天数",
    "休息开始时间",
    "休息结束时间",
    "上班开始时间",
    "上班结束时间",
    "结余补休天数",
    "请假说明",
    "审批编号",
    "创建人",
    "审批结果",
    "审批状态",
    "创建人部门",
]


def detect(
    header: list[str],
    data_type: ImportDataType,
    overrides: dict[str, str | int | None] | None = None,
):
    parsed = import_parsing.parse_paste(text=",".join(header))
    return import_mapping.detect_header(parsed, data_type, overrides=overrides)


def test_punch_aliases_map_every_canonical_field() -> None:
    table = detect(PUNCH_HEADER, ImportDataType.PUNCH)

    assert table.mapping["employee_no"].index == 0
    assert table.mapping["employee_name"].index == 1
    assert table.mapping["department_raw"].index == 2
    assert table.mapping["attendance_date"].index == 3
    assert table.mapping["punch_time"].index == 4
    assert table.mapping["punch_result"].index == 5
    assert table.mapping["device_raw"].index == 6
    assert table.mapping["address_raw"].index == 7
    assert table.mapping["scheduled_time"].index == 8


def test_trip_aliases_map_every_canonical_field() -> None:
    table = detect(TRIP_HEADER, ImportDataType.TRIP)

    assert table.mapping["employee_name"].index == 3
    assert table.mapping["department_raw"].index == 2
    assert table.mapping["start_at"].index == 4
    assert table.mapping["end_at"].index == 5
    assert table.mapping["days_declared"].index == 6
    assert table.mapping["reason"].index == 7
    assert table.mapping["approval_no"].index == 8
    assert table.mapping["approval_result"].index == 9
    assert table.mapping["approval_status"].index == 10
    assert table.ignored_columns == ["序号"]


def test_overtime_aliases_map_every_canonical_field() -> None:
    table = detect(OT_HEADER, ImportDataType.OT)

    assert table.mapping["employee_name"].index == 7
    assert table.mapping["department_raw"].index == 1
    assert table.mapping["start_at"].index == 2
    assert table.mapping["end_at"].index == 3
    assert table.mapping["declared_raw"].index == 4
    assert table.mapping["reason"].index == 5
    assert table.mapping["approval_no"].index == 6
    assert table.mapping["approval_result"].index == 8
    assert table.mapping["approval_status"].index == 9
    assert table.ignored_columns == ["序号", "创建人部门"]


def test_leave_aliases_map_every_canonical_field() -> None:
    table = detect(LEAVE_HEADER, ImportDataType.LEAVE)

    assert table.mapping["employee_name"].index == 10
    assert table.mapping["leave_type_raw"].index == 1
    assert table.mapping["days"].index == 2
    assert table.mapping["rest_start_at"].index == 3
    assert table.mapping["rest_end_at"].index == 4
    assert table.mapping["work_start_at"].index == 5
    assert table.mapping["work_end_at"].index == 6
    assert table.mapping["balance_days_declared"].index == 7
    assert table.mapping["reason"].index == 8
    assert table.mapping["approval_no"].index == 9
    assert table.mapping["approval_result"].index == 11
    assert table.mapping["approval_status"].index == 12
    assert table.ignored_columns == ["创建人部门"]


def test_override_by_column_name_and_index() -> None:
    header = ["工号", "姓名", "部门", "考勤日期", "实际打卡时间", "打卡结果", "额外"]
    table = detect(
        header,
        ImportDataType.PUNCH,
        overrides={"punch_time": "实际打卡时间", "device_raw": 6},
    )

    assert table.mapping["punch_time"].index == 4
    assert table.mapping["device_raw"].index == 6
    assert table.mapping["punch_time"].column == "实际打卡时间"
    assert table.ignored_columns == []


def test_override_to_null_removes_an_optional_mapping() -> None:
    table = detect(PUNCH_HEADER, ImportDataType.PUNCH, overrides={"device_raw": None})

    assert "device_raw" not in table.mapping
    assert table.mapping["address_raw"].index == 7
    assert table.ignored_columns == ["打卡设备"]


def test_missing_required_column_is_fatal_and_names_the_columns() -> None:
    header = ["工号", "姓名", "部门", "考勤日期", "打卡时间"]
    with pytest.raises(DomainError) as exc_info:
        detect(header, ImportDataType.PUNCH)

    assert exc_info.value.code == "missing_required_column"
    assert exc_info.value.field_errors == {"punch_result": "缺少必填列"}
    assert "打卡结果" in exc_info.value.message


def test_two_canonical_fields_on_one_source_column_is_fatal() -> None:
    with pytest.raises(DomainError) as exc_info:
        detect(PUNCH_HEADER, ImportDataType.PUNCH, overrides={"device_raw": "打卡地址"})

    assert exc_info.value.code == "missing_required_column"
    assert "device_raw" in exc_info.value.field_errors
    assert "address_raw" in exc_info.value.field_errors


def test_override_referencing_an_unknown_column_is_fatal() -> None:
    with pytest.raises(DomainError) as exc_info:
        detect(PUNCH_HEADER, ImportDataType.PUNCH, overrides={"punch_time": "不存在"})

    assert exc_info.value.code == "missing_required_column"
    assert exc_info.value.field_errors == {"punch_time": "列不存在"}


def test_unknown_canonical_field_in_overrides_is_fatal() -> None:
    with pytest.raises(DomainError) as exc_info:
        detect(PUNCH_HEADER, ImportDataType.PUNCH, overrides={"unknown_field": "工号"})

    assert exc_info.value.code == "import_parse_failed"
    assert exc_info.value.field_errors == {"column_mapping": "未知列映射字段：unknown_field"}


def test_duplicate_header_names_resolve_to_the_first_column() -> None:
    header = ["工号", "姓名", "部门", "考勤日期", "打卡时间", "打卡结果", "打卡结果"]
    table = detect(header, ImportDataType.PUNCH)

    assert table.mapping["punch_result"].index == 5
    assert table.ignored_columns == ["打卡结果"]


def test_extra_columns_are_listed_as_ignored() -> None:
    header = [*PUNCH_HEADER, "备注", "序号"]
    table = detect(header, ImportDataType.PUNCH)

    assert table.ignored_columns == ["备注", "序号"]
