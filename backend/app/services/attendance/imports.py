"""Import preview: parse, map, match, persist, and report (6.1-6.7.1).

Preview is the parse-and-preview phase: fatal file or column problems raise
before a batch exists, while row-level problems are stored as errors/warnings
and only skip their own row. Normalized rows land in the final tables under a
``preview`` batch with a 24-hour expiry (ADR-0005); calculation ignores them
until a later commit flips the batch to ``committed``.
"""

import hashlib
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, func
from sqlmodel import Session, col, select

from app.core.errors import DomainError
from app.enums import (
    AttendanceMonthStatus,
    ImportBatchStatus,
    ImportDataType,
    ImportSource,
)
from app.models import (
    AttendanceMonth,
    Department,
    Employee,
    ImportBatch,
    ImportBatchError,
    ImportMappingTemplate,
    OaLeave,
    OaOvertime,
    OaOvertimeDay,
    OaTrip,
    PunchRecord,
    User,
    get_datetime_utc,
)
from app.schemas_attendance.imports import (
    ImportBatchErrorPublic,
    ImportBatchPublic,
    ImportEmployeeStats,
    ImportImpact,
    ImportImpactBatch,
    ImportMappingTemplatePublic,
    ImportPreviewPublic,
    ImportStats,
)
from app.services.attendance import import_mapping, import_normalize, import_parsing
from app.services.attendance.errors import AttendanceErrorCode
from app.services.attendance.month_state import existing_month
from app.services.companies import get_company_or_404

PARSER_VERSION = "attendance-import-v1"
PREVIEW_TTL = timedelta(hours=24)
MAX_PREVIEW_ERRORS = 100
MAX_SAMPLES = 20
# Spec 6.6: lazy cleanup deletes at most 5,000 rows per entry-point call.
CLEANUP_ROW_BUDGET = 5_000

TEMPLATE_NOT_FOUND_MESSAGE = "未找到列映射模板"
FILE_OR_TEXT_MESSAGE = "请上传文件或粘贴内容"

__all__ = [
    "PARSER_VERSION",
    "preview_import",
    "read_mapping_template",
]


def preview_import(
    session: Session,
    *,
    company_id: uuid.UUID,
    data_type: ImportDataType,
    month: date,
    operator: User,
    content: bytes | None = None,
    text: str | None = None,
    file_name: str | None = None,
    sheet_name: str | None = None,
    column_mapping: dict[str, str | int | None] | None = None,
) -> ImportPreviewPublic:
    """Parse an upload or paste and persist a committable preview batch."""
    get_company_or_404(session, company_id)
    _cleanup_expired_previews(session, get_datetime_utc())
    session.commit()
    if (content is None) == (text is None):
        raise DomainError(AttendanceErrorCode.IMPORT_PARSE_FAILED, FILE_OR_TEXT_MESSAGE)

    if content is not None:
        source = ImportSource.UPLOAD
        parsed = import_parsing.parse_upload(
            content=content, file_name=file_name or "", sheet_name=sheet_name
        )
        file_size = len(content)
        file_sha256 = hashlib.sha256(content).hexdigest()
        resolved_name = file_name
    else:
        assert text is not None
        source = ImportSource.PASTE
        parsed = import_parsing.parse_paste(text=text)
        payload = text.encode("utf-8")
        file_size = len(payload)
        file_sha256 = hashlib.sha256(payload).hexdigest()
        resolved_name = None

    table = import_mapping.detect_header(parsed, data_type, overrides=column_mapping)
    employees = list(
        session.exec(
            select(Employee)
            .join(Department, col(Employee.dept_id) == col(Department.id))
            .where(Department.company_id == company_id)
        ).all()
    )
    outcome = import_normalize.normalize_rows(
        table, data_type=data_type, month=month, employees=employees
    )

    now = get_datetime_utc()
    batch = ImportBatch(
        company_id=company_id,
        data_type=data_type,
        month=month,
        status=ImportBatchStatus.PREVIEW,
        source=source,
        file_name=resolved_name,
        file_size=file_size,
        file_sha256=file_sha256,
        sheet_name=parsed.sheet_name,
        header_row_number=table.header_row_number,
        header_columns=table.header_columns,
        column_mapping=table.mapping_snapshot,
        parser_version=PARSER_VERSION,
        source_rows=outcome.source_rows,
        valid_records=outcome.valid_records,
        skipped_records=outcome.skipped_records,
        error_records=outcome.error_records,
        warning_records=outcome.warning_records,
        skip_counts=dict(outcome.skip_counts),
        warning_counts=dict(outcome.warning_counts),
        operator_id=operator.id,
        created_at=now,
        expires_at=now + PREVIEW_TTL,
    )
    session.add(batch)
    session.flush()

    error_rows = _persist_issues(session, batch.id, outcome.issues)
    _persist_records(session, batch.id, company_id, outcome.records)
    session.commit()
    session.refresh(batch)

    month_status = existing_month(session, company_id, month)
    can_commit, blocked_reason = _commit_gate(month_status, outcome.valid_records)
    return ImportPreviewPublic(
        batch=ImportBatchPublic.model_validate(batch),
        stats=ImportStats(
            source_rows=outcome.source_rows,
            valid_records=outcome.valid_records,
            skipped_records=outcome.skipped_records,
            error_records=outcome.error_records,
            warning_records=outcome.warning_records,
            skip_counts=dict(outcome.skip_counts),
            warning_counts=dict(outcome.warning_counts),
        ),
        employees=ImportEmployeeStats(
            matched=len(outcome.matched_employee_ids),
            unknown=len(outcome.unknown_keys),
            duplicate_name=len(outcome.duplicate_name_keys),
            affected=len(outcome.affected_employee_ids),
        ),
        errors=[
            ImportBatchErrorPublic.model_validate(row)
            for row in error_rows[:MAX_PREVIEW_ERRORS]
        ],
        error_total=len(outcome.issues),
        samples=[_sample(record) for record in outcome.records[:MAX_SAMPLES]],
        impact=_impact(
            session,
            company_id=company_id,
            data_type=data_type,
            month=month,
            valid_records=outcome.valid_records,
            affected_employee_ids=outcome.affected_employee_ids,
        ),
        can_commit=can_commit,
        commit_blocked_reason=blocked_reason,
    )


def read_mapping_template(
    session: Session, *, company_id: uuid.UUID, data_type: ImportDataType
) -> ImportMappingTemplatePublic:
    get_company_or_404(session, company_id)
    template = session.exec(
        select(ImportMappingTemplate).where(
            col(ImportMappingTemplate.company_id) == company_id,
            col(ImportMappingTemplate.data_type) == data_type,
        )
    ).first()
    if template is None:
        raise DomainError(AttendanceErrorCode.NOT_FOUND, TEMPLATE_NOT_FOUND_MESSAGE)
    return ImportMappingTemplatePublic.model_validate(template)


def _cleanup_expired_previews(session: Session, now: datetime) -> int:
    """Discard expired previews, deleting their rows and errors immediately.

    Whole batches are discarded until the 5,000-row budget is reached so a
    batch's audit trail is never partially deleted. Batch metadata remains
    (status ``discarded``, reason ``expired``); a later retention slice
    hard-deletes it after 90 days (spec 6.6).
    """
    expired = list(
        session.exec(
            select(ImportBatch)
            .where(
                col(ImportBatch.status) == ImportBatchStatus.PREVIEW,
                col(ImportBatch.expires_at).is_not(None),
                col(ImportBatch.expires_at) <= now,
            )
            .order_by(col(ImportBatch.expires_at).asc())
        ).all()
    )
    deleted = 0
    for batch in expired:
        if deleted >= CLEANUP_ROW_BUDGET:
            break
        deleted += _discard_preview_batch(session, batch, now)
    return deleted


def _discard_preview_batch(session: Session, batch: ImportBatch, now: datetime) -> int:
    deleted = 0
    for model in (PunchRecord, OaTrip, OaOvertime, OaLeave):
        deleted += session.exec(
            select(func.count())
            .select_from(model)
            .where(col(model.batch_id) == batch.id)
        ).one()
        session.exec(delete(model).where(col(model.batch_id) == batch.id))
    deleted += session.exec(
        select(func.count())
        .select_from(ImportBatchError)
        .where(col(ImportBatchError.batch_id) == batch.id)
    ).one()
    session.exec(
        delete(ImportBatchError).where(col(ImportBatchError.batch_id) == batch.id)
    )
    batch.status = ImportBatchStatus.DISCARDED
    batch.discarded_at = now
    batch.discard_reason = "expired"
    return deleted


def _commit_gate(
    month: AttendanceMonth | None, valid_records: int
) -> tuple[bool, str | None]:
    if month is not None:
        if month.status == AttendanceMonthStatus.CONFIRMED:
            return False, AttendanceErrorCode.MONTH_CONFIRMED
        if month.status == AttendanceMonthStatus.LOCKED:
            return False, AttendanceErrorCode.MONTH_LOCKED
    if valid_records == 0:
        return False, AttendanceErrorCode.NO_VALID_ROWS
    return True, None


def _persist_issues(
    session: Session, batch_id: uuid.UUID, issues: list[import_normalize.ImportIssue]
) -> list[ImportBatchError]:
    rows: list[ImportBatchError] = []
    for issue in issues:
        row = ImportBatchError(
            batch_id=batch_id,
            source_row_number=issue.source_row_number,
            column_name=issue.column_name,
            code=issue.code,
            message=issue.message,
            severity=issue.severity,
            raw_row=issue.raw_row,
        )
        session.add(row)
        rows.append(row)
    session.flush()
    return rows


def _persist_records(
    session: Session,
    batch_id: uuid.UUID,
    company_id: uuid.UUID,
    records: list[import_normalize.RecordData],
) -> None:
    for record in records:
        if isinstance(record, import_normalize.PunchData):
            session.add(
                PunchRecord(
                    company_id=company_id,
                    batch_id=batch_id,
                    source_row_number=record.source_row_number,
                    employee_id=record.employee_id,
                    employee_no_raw=record.employee_no_raw,
                    employee_name_raw=record.employee_name_raw,
                    department_raw=record.department_raw,
                    attendance_date=record.attendance_date,
                    punch_time=record.punch_time,
                    punch_result_raw=record.punch_result_raw,
                    device_raw=record.device_raw,
                    address_raw=record.address_raw,
                    raw_row=record.raw_row,
                )
            )
        elif isinstance(record, import_normalize.OaTripData):
            session.add(
                OaTrip(
                    company_id=company_id,
                    batch_id=batch_id,
                    source_row_number=record.source_row_number,
                    split_index=record.split_index,
                    employee_id=record.employee_id,
                    approval_no=record.approval_no,
                    employee_name_raw=record.employee_name_raw,
                    department_raw=record.department_raw,
                    application_type_raw=record.application_type_raw,
                    approval_result_raw=record.approval_result_raw,
                    approval_status_raw=record.approval_status_raw,
                    start_at=record.start_at,
                    end_at=record.end_at,
                    start_date=record.start_date,
                    end_date=record.end_date,
                    days_declared=record.days_declared,
                    reason=record.reason,
                    raw_row=record.raw_row,
                )
            )
        elif isinstance(record, import_normalize.OaOvertimeData):
            overtime = OaOvertime(
                company_id=company_id,
                batch_id=batch_id,
                source_row_number=record.source_row_number,
                employee_id=record.employee_id,
                approval_no=record.approval_no,
                employee_name_raw=record.employee_name_raw,
                department_raw=record.department_raw,
                approval_result_raw=record.approval_result_raw,
                approval_status_raw=record.approval_status_raw,
                start_at=record.start_at,
                end_at=record.end_at,
                declared_raw=record.declared_raw,
                reason=record.reason,
                raw_row=record.raw_row,
            )
            session.add(overtime)
            session.flush()
            for work_date, minutes in record.days:
                session.add(
                    OaOvertimeDay(
                        company_id=company_id,
                        overtime_id=overtime.id,
                        work_date=work_date,
                        minutes=minutes,
                    )
                )
        else:
            assert isinstance(record, import_normalize.OaLeaveData)
            session.add(
                OaLeave(
                    company_id=company_id,
                    batch_id=batch_id,
                    source_row_number=record.source_row_number,
                    employee_id=record.employee_id,
                    approval_no=record.approval_no,
                    employee_name_raw=record.employee_name_raw,
                    department_raw=record.department_raw,
                    leave_type_raw=record.leave_type_raw,
                    leave_kind=record.leave_kind,
                    days=record.days,
                    rest_start_at=record.rest_start_at,
                    rest_end_at=record.rest_end_at,
                    rest_start_date=record.rest_start_date,
                    rest_end_date=record.rest_end_date,
                    work_start_at=record.work_start_at,
                    work_end_at=record.work_end_at,
                    work_start_date=record.work_start_date,
                    work_end_date=record.work_end_date,
                    balance_days_declared=record.balance_days_declared,
                    reason=record.reason,
                    approval_result_raw=record.approval_result_raw,
                    approval_status_raw=record.approval_status_raw,
                    raw_row=record.raw_row,
                )
            )
    session.flush()


def _batch_employee_ids(
    session: Session, data_type: ImportDataType, batch_id: uuid.UUID
) -> set[uuid.UUID]:
    if data_type is ImportDataType.PUNCH:
        statement = select(PunchRecord.employee_id).where(
            col(PunchRecord.batch_id) == batch_id
        )
    elif data_type is ImportDataType.TRIP:
        statement = select(OaTrip.employee_id).where(col(OaTrip.batch_id) == batch_id)
    elif data_type is ImportDataType.OT:
        statement = select(OaOvertime.employee_id).where(
            col(OaOvertime.batch_id) == batch_id
        )
    else:
        statement = select(OaLeave.employee_id).where(col(OaLeave.batch_id) == batch_id)
    return set(session.exec(statement.distinct()).all())


def _impact(
    session: Session,
    *,
    company_id: uuid.UUID,
    data_type: ImportDataType,
    month: date,
    valid_records: int,
    affected_employee_ids: set[uuid.UUID],
) -> ImportImpact:
    current = session.exec(
        select(ImportBatch).where(
            col(ImportBatch.company_id) == company_id,
            col(ImportBatch.data_type) == data_type,
            col(ImportBatch.month) == month,
            col(ImportBatch.status) == ImportBatchStatus.COMMITTED,
        )
    ).first()
    if current is None:
        return ImportImpact(
            current_batch=None,
            valid_records_delta=valid_records,
            employee_overlap=0,
            employees_added=len(affected_employee_ids),
            employees_removed=0,
        )
    old_ids = _batch_employee_ids(session, data_type, current.id)
    overlap = affected_employee_ids & old_ids
    return ImportImpact(
        current_batch=ImportImpactBatch(
            id=current.id,
            committed_at=current.committed_at or current.created_at,
            file_name=current.file_name,
            source_rows=current.source_rows,
            valid_records=current.valid_records,
        ),
        valid_records_delta=valid_records - current.valid_records,
        employee_overlap=len(overlap),
        employees_added=len(affected_employee_ids - old_ids),
        employees_removed=len(old_ids - affected_employee_ids),
    )


def _iso(value: datetime | None) -> str | None:
    return value.isoformat().replace("+00:00", "Z") if value else None


def _sample(record: import_normalize.RecordData) -> dict[str, Any]:
    if isinstance(record, import_normalize.PunchData):
        return {
            "source_row_number": record.source_row_number,
            "employee_id": str(record.employee_id),
            "employee_no": record.employee_no_raw,
            "employee_name": record.employee_name_raw,
            "department": record.department_raw,
            "attendance_date": record.attendance_date.isoformat(),
            "punch_time": _iso(record.punch_time),
            "punch_result": record.punch_result_raw,
            "device": record.device_raw,
            "address": record.address_raw,
        }
    if isinstance(record, import_normalize.OaTripData):
        return {
            "source_row_number": record.source_row_number,
            "split_index": record.split_index,
            "employee_id": str(record.employee_id),
            "employee_name": record.employee_name_raw,
            "department": record.department_raw,
            "approval_no": record.approval_no,
            "start_at": _iso(record.start_at),
            "end_at": _iso(record.end_at),
            "days_declared": _decimal(record.days_declared),
        }
    if isinstance(record, import_normalize.OaOvertimeData):
        return {
            "source_row_number": record.source_row_number,
            "employee_id": str(record.employee_id),
            "employee_name": record.employee_name_raw,
            "department": record.department_raw,
            "approval_no": record.approval_no,
            "start_at": _iso(record.start_at),
            "end_at": _iso(record.end_at),
            "declared_raw": record.declared_raw,
            "days": [
                {"work_date": work_date.isoformat(), "minutes": minutes}
                for work_date, minutes in record.days
            ],
        }
    return {
        "source_row_number": record.source_row_number,
        "employee_id": str(record.employee_id),
        "employee_name": record.employee_name_raw,
        "department": record.department_raw,
        "approval_no": record.approval_no,
        "leave_type": record.leave_type_raw,
        "leave_kind": record.leave_kind.value,
        "days": str(record.days),
        "rest_start_at": _iso(record.rest_start_at),
        "rest_end_at": _iso(record.rest_end_at),
        "work_start_at": _iso(record.work_start_at),
        "work_end_at": _iso(record.work_end_at),
    }


def _decimal(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None
