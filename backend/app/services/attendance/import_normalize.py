"""Row normalization, employee matching, filters, and dedupe (6.3-6.5).

Normalization is pure: it takes the detected table plus the company's
employees and returns typed record data and row-level issues. The preview
service owns persistence. Counts follow the spec: ``source_rows`` counts data
rows, while valid/skipped/error/warning records count split request records.
"""

import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

from openpyxl.utils.datetime import from_excel

from app.enums import ImportDataType, ImportSeverity, LeaveKind
from app.models import Employee
from app.services.attendance import import_parsing
from app.services.attendance.import_mapping import DetectedTable

SHANGHAI = ZoneInfo("Asia/Shanghai")

PUNCH_INVALID_MARKERS = ("打卡无效", "已被更新", "需审批")
PUNCH_KNOWN_RESULTS = {
    "正常",
    "迟到",
    "早退",
    "补卡审批通过",
    "外勤",
    "旷工迟到",
}
APPROVED = "审批通过"
MISSING_MARKERS = {"", "无", "--", "—", "-"}
MULTI_PERSON_SEPARATORS = re.compile(r"[;；、,，]")
DAY_CAP_MINUTES = 480
AMOUNT_MISMATCH_RATIO = Decimal("0.2")

_SAFE_SERIAL = re.compile(r"\d{5}(?:\.\d+)?")
_TIME_ONLY = re.compile(r"(\d{1,2}):(\d{2})(?::(\d{2}))?")

MESSAGES = {
    "unknown_employee": "员工不存在",
    "duplicate_name": "员工姓名重名，请使用工号导入",
    "out_of_employment": "日期不在任职期间内",
    "missing_required": "缺少必填内容",
    "invalid_time": "时间格式不正确",
    "invalid_range": "时间范围不正确",
    "invalid_leave_type": "无法识别的请假类型",
    "missing_punch_time": "缺少打卡时间",
    "invalid_punch": "打卡结果无效",
    "not_in_month": "不在目标月份内",
    "duplicate_punch": "重复打卡",
    "duplicate_approval": "重复审批单",
    "pending": "审批中",
    "terminated": "审批已终止",
    "rejected": "审批未通过",
    "unknown_approval": "审批结果无法识别",
    "empty_result": "打卡结果为空",
    "unknown_result": "未知打卡结果",
    "name_mismatch": "姓名与工号不一致",
    "date_mismatch": "考勤日期与打卡日期相差较大",
    "result_conflict": "同一时刻打卡结果不一致",
    "amount_mismatch": "填报时长与计算时长相差较大",
    "missing_work_start": "补休缺少上班开始时间",
}


@dataclass(frozen=True)
class ImportIssue:
    source_row_number: int
    code: str
    message: str
    severity: ImportSeverity
    column_name: str | None = None
    raw_row: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PunchData:
    source_row_number: int
    employee_id: uuid.UUID
    employee_no_raw: str
    employee_name_raw: str
    department_raw: str
    attendance_date: date
    punch_time: datetime
    punch_result_raw: str
    device_raw: str | None
    address_raw: str | None
    raw_row: dict[str, Any]


@dataclass(frozen=True)
class OaTripData:
    source_row_number: int
    split_index: int
    employee_id: uuid.UUID
    approval_no: str | None
    employee_name_raw: str
    department_raw: str
    application_type_raw: str | None
    approval_result_raw: str
    approval_status_raw: str
    start_at: datetime
    end_at: datetime
    start_date: date
    end_date: date
    days_declared: Decimal | None
    reason: str | None
    raw_row: dict[str, Any]


@dataclass(frozen=True)
class OaOvertimeData:
    source_row_number: int
    employee_id: uuid.UUID
    approval_no: str | None
    employee_name_raw: str
    department_raw: str
    approval_result_raw: str
    approval_status_raw: str
    start_at: datetime
    end_at: datetime
    declared_raw: str | None
    reason: str | None
    days: tuple[tuple[date, int], ...]
    raw_row: dict[str, Any]


@dataclass(frozen=True)
class OaLeaveData:
    source_row_number: int
    employee_id: uuid.UUID
    approval_no: str | None
    employee_name_raw: str
    department_raw: str
    leave_type_raw: str
    leave_kind: LeaveKind
    days: Decimal
    rest_start_at: datetime
    rest_end_at: datetime
    rest_start_date: date
    rest_end_date: date
    work_start_at: datetime | None
    work_end_at: datetime | None
    work_start_date: date | None
    work_end_date: date | None
    balance_days_declared: Decimal | None
    reason: str | None
    approval_result_raw: str
    approval_status_raw: str
    raw_row: dict[str, Any]


RecordData = PunchData | OaTripData | OaOvertimeData | OaLeaveData


@dataclass
class NormalizationOutcome:
    records: list[RecordData] = field(default_factory=list)
    issues: list[ImportIssue] = field(default_factory=list)
    source_rows: int = 0
    valid_records: int = 0
    skipped_records: int = 0
    error_records: int = 0
    warning_records: int = 0
    skip_counts: dict[str, int] = field(default_factory=dict)
    warning_counts: dict[str, int] = field(default_factory=dict)
    matched_employee_ids: set[uuid.UUID] = field(default_factory=set)
    unknown_keys: set[str] = field(default_factory=set)
    duplicate_name_keys: set[str] = field(default_factory=set)
    affected_employee_ids: set[uuid.UUID] = field(default_factory=set)


class _Tally:
    def __init__(self) -> None:
        self.outcome = NormalizationOutcome()
        self._warned_current = False

    def start_record(self) -> None:
        self._warned_current = False

    def skip(self, code: str) -> None:
        self.outcome.skipped_records += 1
        self.outcome.skip_counts[code] = self.outcome.skip_counts.get(code, 0) + 1
        self._finish()

    def error(
        self,
        *,
        source_row_number: int,
        code: str,
        raw_row: dict[str, Any],
        column_name: str | None = None,
        message: str | None = None,
    ) -> None:
        self.outcome.issues.append(
            ImportIssue(
                source_row_number=source_row_number,
                code=code,
                message=message or MESSAGES[code],
                severity=ImportSeverity.ERROR,
                column_name=column_name,
                raw_row=raw_row,
            )
        )
        self.outcome.error_records += 1
        self.skip(code)

    def warn(
        self,
        *,
        source_row_number: int,
        code: str,
        raw_row: dict[str, Any],
        column_name: str | None = None,
        message: str | None = None,
    ) -> None:
        self.outcome.issues.append(
            ImportIssue(
                source_row_number=source_row_number,
                code=code,
                message=message or MESSAGES[code],
                severity=ImportSeverity.WARNING,
                column_name=column_name,
                raw_row=raw_row,
            )
        )
        self.outcome.warning_counts[code] = self.outcome.warning_counts.get(code, 0) + 1
        self._warned_current = True

    def imported(self, record: RecordData) -> None:
        self.outcome.records.append(record)
        self.outcome.valid_records += 1
        self.outcome.affected_employee_ids.add(record.employee_id)
        self._finish()

    def _finish(self) -> None:
        if self._warned_current:
            self.outcome.warning_records += 1
        self._warned_current = False


def normalize_rows(
    table: DetectedTable,
    *,
    data_type: ImportDataType,
    month: date,
    employees: Sequence[Employee],
) -> NormalizationOutcome:
    tally = _Tally()
    tally.outcome.source_rows = len(table.data_rows)
    normalizer = _Normalizer(
        table=table,
        month=month,
        employees=list(employees),
        tally=tally,
    )
    if data_type is ImportDataType.PUNCH:
        normalizer.normalize_punch()
    elif data_type is ImportDataType.TRIP:
        normalizer.normalize_trip()
    elif data_type is ImportDataType.OT:
        normalizer.normalize_overtime()
    else:
        normalizer.normalize_leave()
    return tally.outcome


@dataclass
class _Normalizer:
    table: DetectedTable
    month: date
    employees: list[Employee]
    tally: _Tally

    def __post_init__(self) -> None:
        self.by_no = {
            _normalize_code(employee.employee_no): employee
            for employee in self.employees
        }
        self.by_name: dict[str, list[Employee]] = {}
        for employee in self.employees:
            self.by_name.setdefault(employee.name.strip(), []).append(employee)
        self.month_start = self.month.replace(day=1)
        self.month_end = _month_end(self.month_start)

    # -- shared helpers -------------------------------------------------
    def cell(self, row: import_parsing.SourceRow, field_name: str) -> str:
        ref = self.table.mapping.get(field_name)
        if ref is None or ref.index >= len(row.cells):
            return ""
        return row.cells[ref.index].strip()

    def full_raw(self, row: import_parsing.SourceRow) -> dict[str, Any]:
        return _full_raw_row(row, self.table.header_columns)

    def mapped_raw(self, row: import_parsing.SourceRow) -> dict[str, Any]:
        raw: dict[str, Any] = {}
        for ref in self.table.mapping.values():
            key = ref.column
            if key in raw:
                key = f"{key} ({ref.index + 1})"
            raw[key] = row.cells[ref.index] if ref.index < len(row.cells) else ""
        return raw

    def employee_error_code(self, name: str) -> str:
        """The row error for a name that did not resolve to one employee."""
        if name in self.tally.outcome.duplicate_name_keys:
            return "duplicate_name"
        return "unknown_employee"

    def match_name(self, name: str) -> Employee | None:
        candidates = self.by_name.get(name)
        if not candidates:
            self.tally.outcome.unknown_keys.add(name)
            return None
        if len(candidates) > 1:
            self.tally.outcome.duplicate_name_keys.add(name)
            return None
        employee = candidates[0]
        self.tally.outcome.matched_employee_ids.add(employee.id)
        return employee

    def in_employment(self, employee: Employee, work_date: date) -> bool:
        if work_date < employee.hire_date:
            return False
        return employee.resign_date is None or work_date <= employee.resign_date

    def in_month(self, start: date, end: date) -> bool:
        return start <= self.month_end and end >= self.month_start

    # -- punch ----------------------------------------------------------
    def normalize_punch(self) -> None:
        seen: dict[tuple[uuid.UUID, date, datetime], str] = {}
        for row in self.table.data_rows:
            self.tally.start_record()
            raw = self.full_raw(row)
            employee_no = self.cell(row, "employee_no")
            if not employee_no:
                self.tally.error(
                    source_row_number=row.row_number,
                    code="missing_required",
                    column_name="工号",
                    raw_row=raw,
                    message="缺少工号",
                )
                continue
            employee = self.by_no.get(_normalize_code(employee_no))
            if employee is None:
                self.tally.outcome.unknown_keys.add(employee_no)
                self.tally.error(
                    source_row_number=row.row_number,
                    code="unknown_employee",
                    column_name="工号",
                    raw_row=raw,
                )
                continue
            self.tally.outcome.matched_employee_ids.add(employee.id)

            attendance_date_raw = self.cell(row, "attendance_date")
            if not attendance_date_raw:
                self.tally.error(
                    source_row_number=row.row_number,
                    code="missing_required",
                    column_name="考勤日期",
                    raw_row=raw,
                    message="缺少考勤日期",
                )
                continue
            attendance_date = _parse_date(attendance_date_raw)
            if attendance_date is None:
                self.tally.error(
                    source_row_number=row.row_number,
                    code="invalid_time",
                    column_name="考勤日期",
                    raw_row=raw,
                )
                continue

            punch_time_raw = self.cell(row, "punch_time")
            if not punch_time_raw:
                self.tally.error(
                    source_row_number=row.row_number,
                    code="missing_punch_time",
                    column_name="打卡时间",
                    raw_row=raw,
                )
                continue
            punch_time = _parse_datetime(punch_time_raw, date_hint=attendance_date)
            if punch_time is None:
                self.tally.error(
                    source_row_number=row.row_number,
                    code="invalid_time",
                    column_name="打卡时间",
                    raw_row=raw,
                )
                continue
            punch_time = punch_time.replace(second=0, microsecond=0)

            if not self.in_employment(employee, attendance_date):
                self.tally.error(
                    source_row_number=row.row_number,
                    code="out_of_employment",
                    column_name="考勤日期",
                    raw_row=raw,
                )
                continue
            if not self.in_month(attendance_date, attendance_date):
                self.tally.skip("not_in_month")
                continue

            result = self.cell(row, "punch_result")
            if any(marker in result for marker in PUNCH_INVALID_MARKERS):
                self.tally.skip("invalid_punch")
                continue

            name = self.cell(row, "employee_name")
            if name and name != employee.name:
                self.tally.warn(
                    source_row_number=row.row_number,
                    code="name_mismatch",
                    column_name="姓名",
                    raw_row=raw,
                )
            if not result:
                self.tally.warn(
                    source_row_number=row.row_number,
                    code="empty_result",
                    column_name="打卡结果",
                    raw_row=raw,
                )
            elif result not in PUNCH_KNOWN_RESULTS:
                self.tally.warn(
                    source_row_number=row.row_number,
                    code="unknown_result",
                    column_name="打卡结果",
                    raw_row=raw,
                )
            if abs((_local_date(punch_time) - attendance_date).days) > 1:
                self.tally.warn(
                    source_row_number=row.row_number,
                    code="date_mismatch",
                    column_name="考勤日期",
                    raw_row=raw,
                )

            key = (employee.id, attendance_date, punch_time)
            if key in seen:
                if seen[key] != result:
                    self.tally.warn(
                        source_row_number=row.row_number,
                        code="result_conflict",
                        column_name="打卡结果",
                        raw_row=raw,
                    )
                self.tally.skip("duplicate_punch")
                continue
            seen[key] = result

            self.tally.imported(
                PunchData(
                    source_row_number=row.row_number,
                    employee_id=employee.id,
                    employee_no_raw=employee_no,
                    employee_name_raw=name,
                    department_raw=self.cell(row, "department_raw"),
                    attendance_date=attendance_date,
                    punch_time=punch_time,
                    punch_result_raw=result,
                    device_raw=self.cell(row, "device_raw") or None,
                    address_raw=self.cell(row, "address_raw") or None,
                    raw_row=self.mapped_raw(row),
                )
            )

    # -- OA shared ------------------------------------------------------
    def approval_outcome(self, row: import_parsing.SourceRow) -> str | None:
        """Return the skip reason for a non-approved request, else None."""
        result = self.cell(row, "approval_result")
        status = self.cell(row, "approval_status")
        if result == APPROVED:
            return None
        if result == "审批中" or status == "审批中":
            return "pending"
        if result == "审批未通过":
            return "rejected"
        if result == "终止" or status == "终止" or result in {"--", "—"}:
            return "terminated"
        return "unknown_approval"

    def approval_no(self, row: import_parsing.SourceRow) -> str | None:
        return self.cell(row, "approval_no") or None

    def employee_names(self, row: import_parsing.SourceRow) -> list[str]:
        cell = self.cell(row, "employee_name")
        if cell in MISSING_MARKERS:
            return []
        return [
            part
            for part in (part.strip() for part in MULTI_PERSON_SEPARATORS.split(cell))
            if part not in MISSING_MARKERS
        ]

    # -- trip -----------------------------------------------------------
    def normalize_trip(self) -> None:
        seen: set[tuple[str, uuid.UUID]] = set()
        for row in self.table.data_rows:
            self.tally.start_record()
            raw = self.full_raw(row)
            skip_reason = self.approval_outcome(row)
            if skip_reason is not None:
                self.tally.skip(skip_reason)
                continue
            names = self.employee_names(row)
            if not names:
                self.tally.error(
                    source_row_number=row.row_number,
                    code="missing_required",
                    column_name="出差人",
                    raw_row=raw,
                    message="缺少出差人",
                )
                continue
            start_raw = self.cell(row, "start_at")
            end_raw = self.cell(row, "end_at")
            start_at = _parse_datetime(start_raw)
            end_at = _parse_datetime(end_raw)
            start_date = _local_date(start_at) if start_at else None
            end_date = _local_date(end_at) if end_at else None
            if not start_raw:
                self.tally.error(
                    source_row_number=row.row_number,
                    code="missing_required",
                    column_name="开始时间",
                    raw_row=raw,
                    message="缺少开始时间",
                )
                continue
            if not end_raw:
                self.tally.error(
                    source_row_number=row.row_number,
                    code="missing_required",
                    column_name="结束时间",
                    raw_row=raw,
                    message="缺少结束时间",
                )
                continue
            if (
                start_at is None
                or end_at is None
                or start_date is None
                or end_date is None
            ):
                self.tally.error(
                    source_row_number=row.row_number,
                    code="invalid_time",
                    column_name="开始时间",
                    raw_row=raw,
                )
                continue
            for split_index, name in enumerate(names):
                self.tally.start_record()
                employee = self.match_name(name)
                if employee is None:
                    code = self.employee_error_code(name)
                    self.tally.error(
                        source_row_number=row.row_number,
                        code=code,
                        column_name="出差人",
                        raw_row=raw,
                    )
                    continue
                if not self.in_employment(employee, start_date):
                    self.tally.error(
                        source_row_number=row.row_number,
                        code="out_of_employment",
                        column_name="开始时间",
                        raw_row=raw,
                    )
                    continue
                if end_at <= start_at:
                    self.tally.error(
                        source_row_number=row.row_number,
                        code="invalid_range",
                        column_name="结束时间",
                        raw_row=raw,
                    )
                    continue
                if not self.in_month(start_date, end_date):
                    self.tally.skip("not_in_month")
                    continue
                approval_no = self.approval_no(row)
                dedupe_key = (approval_no or f"row:{row.row_number}", employee.id)
                if approval_no is not None and dedupe_key in seen:
                    self.tally.skip("duplicate_approval")
                    continue
                if approval_no is not None:
                    seen.add(dedupe_key)
                self.tally.imported(
                    OaTripData(
                        source_row_number=row.row_number,
                        split_index=split_index,
                        employee_id=employee.id,
                        approval_no=approval_no,
                        employee_name_raw=name,
                        department_raw=self.cell(row, "department_raw"),
                        application_type_raw=self.cell(row, "application_type_raw")
                        or None,
                        approval_result_raw=self.cell(row, "approval_result"),
                        approval_status_raw=self.cell(row, "approval_status"),
                        start_at=start_at,
                        end_at=end_at,
                        start_date=start_date,
                        end_date=end_date,
                        days_declared=_parse_decimal(self.cell(row, "days_declared")),
                        reason=self.cell(row, "reason") or None,
                        raw_row=self.mapped_raw(row),
                    )
                )

    # -- overtime -------------------------------------------------------
    def normalize_overtime(self) -> None:
        seen: set[tuple[str, uuid.UUID]] = set()
        for row in self.table.data_rows:
            self.tally.start_record()
            raw = self.full_raw(row)
            skip_reason = self.approval_outcome(row)
            if skip_reason is not None:
                self.tally.skip(skip_reason)
                continue
            name = self.cell(row, "employee_name")
            if name in MISSING_MARKERS:
                self.tally.error(
                    source_row_number=row.row_number,
                    code="missing_required",
                    column_name="创建人",
                    raw_row=raw,
                    message="缺少创建人",
                )
                continue
            start_raw = self.cell(row, "start_at")
            end_raw = self.cell(row, "end_at")
            start_at = _parse_datetime(start_raw)
            end_at = _parse_datetime(end_raw)
            if not start_raw:
                self.tally.error(
                    source_row_number=row.row_number,
                    code="missing_required",
                    column_name="开始时间",
                    raw_row=raw,
                    message="缺少开始时间",
                )
                continue
            if not end_raw:
                self.tally.error(
                    source_row_number=row.row_number,
                    code="missing_required",
                    column_name="结束时间",
                    raw_row=raw,
                    message="缺少结束时间",
                )
                continue
            if start_at is None or end_at is None:
                self.tally.error(
                    source_row_number=row.row_number,
                    code="invalid_time",
                    column_name="开始时间",
                    raw_row=raw,
                )
                continue
            employee = self.match_name(name)
            if employee is None:
                code = self.employee_error_code(name)
                self.tally.error(
                    source_row_number=row.row_number,
                    code=code,
                    column_name="创建人",
                    raw_row=raw,
                )
                continue
            if not self.in_employment(employee, _local_date(start_at)):
                self.tally.error(
                    source_row_number=row.row_number,
                    code="out_of_employment",
                    column_name="开始时间",
                    raw_row=raw,
                )
                continue
            if end_at <= start_at:
                self.tally.error(
                    source_row_number=row.row_number,
                    code="invalid_range",
                    column_name="结束时间",
                    raw_row=raw,
                )
                continue
            if not self.in_month(_local_date(start_at), _local_date(end_at)):
                self.tally.skip("not_in_month")
                continue
            approval_no = self.approval_no(row)
            dedupe_key = (approval_no or f"row:{row.row_number}", employee.id)
            if approval_no is not None and dedupe_key in seen:
                self.tally.skip("duplicate_approval")
                continue
            if approval_no is not None:
                seen.add(dedupe_key)

            declared_raw = self.cell(row, "declared_raw") or None
            all_days = _overtime_days(start_at, end_at)
            computed_hours = Decimal(sum(minutes for _, minutes in all_days)) / 60
            declared_hours = _parse_decimal(declared_raw)
            if (
                declared_hours is not None
                and computed_hours > 0
                and abs(computed_hours - declared_hours) / computed_hours
                > AMOUNT_MISMATCH_RATIO
            ):
                self.tally.warn(
                    source_row_number=row.row_number,
                    code="amount_mismatch",
                    column_name="加班时长（天/小时）",
                    raw_row=raw,
                )
            month_days = tuple(
                (work_date, min(minutes, DAY_CAP_MINUTES))
                for work_date, minutes in all_days
                if self.month_start <= work_date <= self.month_end and minutes > 0
            )
            self.tally.imported(
                OaOvertimeData(
                    source_row_number=row.row_number,
                    employee_id=employee.id,
                    approval_no=approval_no,
                    employee_name_raw=name,
                    department_raw=self.cell(row, "department_raw"),
                    approval_result_raw=self.cell(row, "approval_result"),
                    approval_status_raw=self.cell(row, "approval_status"),
                    start_at=start_at,
                    end_at=end_at,
                    declared_raw=declared_raw,
                    reason=self.cell(row, "reason") or None,
                    days=month_days,
                    raw_row=self.mapped_raw(row),
                )
            )

    # -- leave ----------------------------------------------------------
    def normalize_leave(self) -> None:
        seen: set[tuple[str, uuid.UUID]] = set()
        for row in self.table.data_rows:
            self.tally.start_record()
            raw = self.full_raw(row)
            skip_reason = self.approval_outcome(row)
            if skip_reason is not None:
                self.tally.skip(skip_reason)
                continue
            name = self.cell(row, "employee_name")
            if name in MISSING_MARKERS:
                self.tally.error(
                    source_row_number=row.row_number,
                    code="missing_required",
                    column_name="创建人",
                    raw_row=raw,
                    message="缺少创建人",
                )
                continue
            leave_type = self.cell(row, "leave_type_raw")
            leave_kind = _leave_kind(leave_type)
            if leave_kind is None:
                self.tally.error(
                    source_row_number=row.row_number,
                    code="invalid_leave_type",
                    column_name="请假类型",
                    raw_row=raw,
                )
                continue
            days_raw = self.cell(row, "days")
            if not days_raw:
                self.tally.error(
                    source_row_number=row.row_number,
                    code="missing_required",
                    column_name="请假天数",
                    raw_row=raw,
                    message="缺少请假天数",
                )
                continue
            days = _parse_decimal(days_raw)
            if days is None or days <= 0:
                self.tally.error(
                    source_row_number=row.row_number,
                    code="invalid_range",
                    column_name="请假天数",
                    raw_row=raw,
                    message="请假天数必须大于 0",
                )
                continue

            rest_start_raw = self.cell(row, "rest_start_at")
            rest_end_raw = self.cell(row, "rest_end_at")
            rest_start_at = _parse_datetime(rest_start_raw)
            rest_end_at = _parse_datetime(rest_end_raw)
            if not rest_start_raw or not rest_end_raw:
                self.tally.error(
                    source_row_number=row.row_number,
                    code="missing_required",
                    column_name="休息开始时间"
                    if not rest_start_raw
                    else "休息结束时间",
                    raw_row=raw,
                    message="缺少休息时间",
                )
                continue
            if rest_start_at is None or rest_end_at is None:
                self.tally.error(
                    source_row_number=row.row_number,
                    code="invalid_time",
                    column_name="休息开始时间",
                    raw_row=raw,
                )
                continue

            work_start_raw = self.cell(row, "work_start_at")
            work_end_raw = self.cell(row, "work_end_at")
            work_start_at = _parse_datetime(work_start_raw) if work_start_raw else None
            work_end_at = _parse_datetime(work_end_raw) if work_end_raw else None
            if (work_start_raw and work_start_at is None) or (
                work_end_raw and work_end_at is None
            ):
                self.tally.error(
                    source_row_number=row.row_number,
                    code="invalid_time",
                    column_name="上班开始时间",
                    raw_row=raw,
                )
                continue

            employee = self.match_name(name)
            if employee is None:
                code = self.employee_error_code(name)
                self.tally.error(
                    source_row_number=row.row_number,
                    code=code,
                    column_name="创建人",
                    raw_row=raw,
                )
                continue
            if not self.in_employment(employee, _local_date(rest_start_at)):
                self.tally.error(
                    source_row_number=row.row_number,
                    code="out_of_employment",
                    column_name="休息开始时间",
                    raw_row=raw,
                )
                continue
            if rest_end_at <= rest_start_at or (
                work_start_at is not None
                and work_end_at is not None
                and work_end_at <= work_start_at
            ):
                self.tally.error(
                    source_row_number=row.row_number,
                    code="invalid_range",
                    column_name="休息结束时间",
                    raw_row=raw,
                )
                continue
            work_start_date = _local_date(work_start_at) if work_start_at else None
            work_end_date = _local_date(work_end_at) if work_end_at else None
            rest_in_month = self.in_month(
                _local_date(rest_start_at), _local_date(rest_end_at)
            )
            work_in_month = work_start_date is not None and self.in_month(
                work_start_date, work_end_date or work_start_date
            )
            if not rest_in_month and not work_in_month:
                self.tally.skip("not_in_month")
                continue
            if leave_kind is LeaveKind.COMP and work_start_at is None:
                self.tally.warn(
                    source_row_number=row.row_number,
                    code="missing_work_start",
                    column_name="上班开始时间",
                    raw_row=raw,
                )
            approval_no = self.approval_no(row)
            dedupe_key = (approval_no or f"row:{row.row_number}", employee.id)
            if approval_no is not None and dedupe_key in seen:
                self.tally.skip("duplicate_approval")
                continue
            if approval_no is not None:
                seen.add(dedupe_key)
            self.tally.imported(
                OaLeaveData(
                    source_row_number=row.row_number,
                    employee_id=employee.id,
                    approval_no=approval_no,
                    employee_name_raw=name,
                    department_raw=self.cell(row, "department_raw"),
                    leave_type_raw=leave_type,
                    leave_kind=leave_kind,
                    days=days,
                    rest_start_at=rest_start_at,
                    rest_end_at=rest_end_at,
                    rest_start_date=_local_date(rest_start_at),
                    rest_end_date=_local_date(rest_end_at),
                    work_start_at=work_start_at,
                    work_end_at=work_end_at,
                    work_start_date=work_start_date,
                    work_end_date=work_end_date,
                    balance_days_declared=_parse_decimal(
                        self.cell(row, "balance_days_declared")
                    ),
                    reason=self.cell(row, "reason") or None,
                    approval_result_raw=self.cell(row, "approval_result"),
                    approval_status_raw=self.cell(row, "approval_status"),
                    raw_row=self.mapped_raw(row),
                )
            )


def _normalize_code(value: str) -> str:
    return value.strip().upper()


def _month_end(month_start: date) -> date:
    if month_start.month == 12:
        return date(month_start.year, 12, 31)
    return date(month_start.year, month_start.month + 1, 1) - timedelta(days=1)


def _full_raw_row(
    row: import_parsing.SourceRow, header_columns: list[str]
) -> dict[str, Any]:
    raw: dict[str, Any] = {}
    for index, column in enumerate(header_columns):
        key = column or f"column_{index + 1}"
        if key in raw:
            key = f"{key} ({index + 1})"
        raw[key] = row.cells[index] if index < len(row.cells) else ""
    return raw


def _parse_datetime(raw: str, *, date_hint: date | None = None) -> datetime | None:
    value = raw.strip()
    if not value:
        return None
    time_only = _TIME_ONLY.fullmatch(value)
    if time_only and date_hint is not None:
        hour, minute = int(time_only.group(1)), int(time_only.group(2))
        second = int(time_only.group(3) or 0)
        if hour > 23 or minute > 59 or second > 59:
            return None
        return _to_utc(datetime.combine(date_hint, time(hour, minute, second)))
    serial = _SAFE_SERIAL.fullmatch(value)
    if serial:
        try:
            converted = from_excel(float(value))
        except ValueError, OverflowError:
            return None
        if isinstance(converted, datetime):
            return _to_utc(converted)
        return None
    normalized = value.replace("/", "-").replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return _to_utc(datetime.strptime(normalized, fmt))
        except ValueError:
            continue
    return None


def _parse_date(raw: str) -> date | None:
    parsed = _parse_datetime(raw)
    return _local_date(parsed) if parsed else None


def _to_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=SHANGHAI).astimezone(UTC)


def _local_date(value: datetime) -> date:
    """The Asia/Shanghai calendar date of an instant."""
    return value.astimezone(SHANGHAI).date()


def _parse_decimal(raw: str | None) -> Decimal | None:
    if raw is None:
        return None
    value = raw.strip().replace(",", "")
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _leave_kind(leave_type: str) -> LeaveKind | None:
    if "补休" in leave_type or "调休" in leave_type:
        return LeaveKind.COMP
    if "带薪" in leave_type:
        return LeaveKind.PAID
    if "事假" in leave_type:
        return LeaveKind.UNPAID
    return None


def _overtime_days(start_at: datetime, end_at: datetime) -> list[tuple[date, int]]:
    """Split a range by natural day (Asia/Shanghai) and cap each day."""
    local_start = start_at.astimezone(SHANGHAI)
    local_end = end_at.astimezone(SHANGHAI)
    days: list[tuple[date, int]] = []
    current = local_start.date()
    while current <= local_end.date():
        day_start = datetime.combine(current, time.min, tzinfo=SHANGHAI)
        day_end = day_start + timedelta(days=1)
        overlap_start = max(local_start, day_start)
        overlap_end = min(local_end, day_end)
        if overlap_end > overlap_start:
            minutes = int((overlap_end - overlap_start).total_seconds() // 60)
            if minutes > 0:
                days.append((current, min(minutes, DAY_CAP_MINUTES)))
        current += timedelta(days=1)
    return days
