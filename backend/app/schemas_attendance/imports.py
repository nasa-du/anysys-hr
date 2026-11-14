"""Import schemas: previews, batches, row errors, and typed records."""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import Field
from sqlmodel import SQLModel

from app.enums import (
    ImportBatchStatus,
    ImportDataType,
    ImportSeverity,
    ImportSource,
    LeaveKind,
)
from app.schemas_attendance.common import (
    DecimalString,
    MonthString,
    ReadModel,
)


class ImportStats(SQLModel):
    source_rows: int = 0
    valid_records: int = 0
    skipped_records: int = 0
    error_records: int = 0
    warning_records: int = 0
    skip_counts: dict[str, int] = {}
    warning_counts: dict[str, int] = {}


class ImportBatchPublic(ReadModel):
    id: uuid.UUID
    company_id: uuid.UUID
    data_type: ImportDataType
    month: MonthString
    status: ImportBatchStatus
    source: ImportSource
    file_name: str | None = None
    file_size: int | None = None
    file_sha256: str | None = None
    sheet_name: str | None = None
    header_row_number: int | None = None
    header_columns: list[Any] = []
    column_mapping: dict[str, Any] = {}
    parser_version: str
    source_rows: int
    valid_records: int
    skipped_records: int
    error_records: int
    warning_records: int
    skip_counts: dict[str, int] = {}
    warning_counts: dict[str, int] = {}
    operator_id: uuid.UUID
    operator_name: str | None = None
    created_at: datetime
    committed_at: datetime | None = None
    superseded_at: datetime | None = None
    discarded_at: datetime | None = None
    revoked_at: datetime | None = None
    expires_at: datetime | None = None
    superseded_by_batch_id: uuid.UUID | None = None
    discard_reason: str | None = None
    samples: list[dict[str, Any]] | None = None


class ImportBatchesPublic(SQLModel):
    data: list[ImportBatchPublic]
    count: int


class ImportBatchErrorPublic(ReadModel):
    id: uuid.UUID
    source_row_number: int
    column_name: str | None = None
    code: str
    message: str
    severity: ImportSeverity
    raw_row: dict[str, Any]


class ImportBatchErrorsPublic(SQLModel):
    data: list[ImportBatchErrorPublic]
    count: int


class PunchRecordPublic(ReadModel):
    id: uuid.UUID
    company_id: uuid.UUID
    batch_id: uuid.UUID
    source_row_number: int
    employee_id: uuid.UUID
    employee_no_raw: str
    employee_name_raw: str
    department_raw: str
    attendance_date: date
    punch_time: datetime
    punch_result_raw: str
    device_raw: str | None = None
    address_raw: str | None = None
    raw_row: dict[str, Any]
    created_at: datetime


class OaTripPublic(ReadModel):
    id: uuid.UUID
    company_id: uuid.UUID
    batch_id: uuid.UUID
    employee_id: uuid.UUID
    source_row_number: int
    split_index: int
    approval_no: str | None = None
    employee_name_raw: str
    department_raw: str
    application_type_raw: str | None = None
    approval_result_raw: str
    approval_status_raw: str
    start_at: datetime
    end_at: datetime
    start_date: date
    end_date: date
    days_declared: DecimalString | None = None
    reason: str | None = None
    raw_row: dict[str, Any]
    created_at: datetime


class OaOvertimePublic(ReadModel):
    id: uuid.UUID
    company_id: uuid.UUID
    batch_id: uuid.UUID
    employee_id: uuid.UUID
    source_row_number: int
    approval_no: str | None = None
    employee_name_raw: str
    department_raw: str
    approval_result_raw: str
    approval_status_raw: str
    start_at: datetime
    end_at: datetime
    declared_raw: str | None = None
    reason: str | None = None
    raw_row: dict[str, Any]
    created_at: datetime
    days: list[OaOvertimeDayPublic] = Field(default_factory=list)


class OaOvertimeDayPublic(ReadModel):
    id: uuid.UUID
    overtime_id: uuid.UUID
    work_date: date
    minutes: int
    created_at: datetime


class OaLeavePublic(ReadModel):
    id: uuid.UUID
    company_id: uuid.UUID
    batch_id: uuid.UUID
    employee_id: uuid.UUID
    source_row_number: int
    approval_no: str | None = None
    employee_name_raw: str
    department_raw: str
    leave_type_raw: str
    leave_kind: LeaveKind
    days: DecimalString
    rest_start_at: datetime
    rest_end_at: datetime
    rest_start_date: date
    rest_end_date: date
    work_start_at: datetime | None = None
    work_end_at: datetime | None = None
    work_start_date: date | None = None
    work_end_date: date | None = None
    balance_days_declared: DecimalString | None = None
    reason: str | None = None
    approval_result_raw: str
    approval_status_raw: str
    raw_row: dict[str, Any]
    created_at: datetime


ImportRecordPublic = PunchRecordPublic | OaTripPublic | OaOvertimePublic | OaLeavePublic


class ImportBatchRecordsPublic(SQLModel):
    data_type: ImportDataType
    records: list[ImportRecordPublic]
    count: int


class ImportMappingTemplatePublic(ReadModel):
    id: uuid.UUID
    company_id: uuid.UUID
    data_type: ImportDataType
    mapping: dict[str, Any]
    header_columns: list[Any]
    updated_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ImportPreviewPublic(SQLModel):
    batch: ImportBatchPublic
    stats: ImportStats
    employees: list[dict[str, Any]] = []
    errors: list[ImportBatchErrorPublic] = []
    samples: list[dict[str, Any]] = []
    impact: dict[str, Any] = {}
    can_commit: bool
    commit_blocked_reason: str | None = None


class ImportCommitPublic(SQLModel):
    batch: ImportBatchPublic
    superseded_batch_id: uuid.UUID | None = None
    month: MonthString
    is_stale: bool


# Keep the forward reference to OaOvertimeDayPublic resolvable.
OaOvertimePublic.model_rebuild()
