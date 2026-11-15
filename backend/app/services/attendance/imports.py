"""Import preview: parse, map, match, persist, and report (6.1-6.7.1).

Preview is the parse-and-preview phase: fatal file or column problems raise
before a batch exists, while row-level problems are stored as errors/warnings
and only skip their own row. Normalized rows land in the final tables under a
``preview`` batch with a 24-hour expiry (ADR-0005); calculation ignores them
until a later commit flips the batch to ``committed``.
"""

import hashlib
import uuid
from collections import defaultdict
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, delete, func, update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.core.errors import DomainError
from app.enums import (
    AttendanceMonthStatus,
    ImportBatchStatus,
    ImportDataType,
    ImportSeverity,
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
    ImportBatchErrorsPublic,
    ImportBatchesPublic,
    ImportBatchPublic,
    ImportBatchRecordsPublic,
    ImportCommitPublic,
    ImportEmployeeStats,
    ImportImpact,
    ImportImpactBatch,
    ImportMappingTemplatePublic,
    ImportPreviewPublic,
    ImportRecordPublic,
    ImportStats,
    OaLeavePublic,
    OaOvertimeDayPublic,
    OaOvertimePublic,
    OaTripPublic,
    PunchRecordPublic,
)
from app.services.attendance import import_mapping, import_normalize, import_parsing
from app.services.attendance.errors import AttendanceErrorCode
from app.services.attendance.month_state import (
    ensure_month_editable,
    existing_month,
    get_or_create_month,
)
from app.services.attendance.staleness import mark_month_stale
from app.services.common import paginate
from app.services.companies import get_company_or_404

PARSER_VERSION = "attendance-import-v1"
PREVIEW_TTL = timedelta(hours=24)
MAX_PREVIEW_ERRORS = 100
MAX_SAMPLES = 20
# Spec 6.6: lazy cleanup deletes at most 5,000 rows per entry-point call.
CLEANUP_ROW_BUDGET = 5_000
SUPERSEDED_RAW_RETENTION = timedelta(days=90)
DISCARDED_METADATA_RETENTION = timedelta(days=90)
DISCARD_REASON_USER = "user"
DISCARD_REASON_EXPIRED = "expired"

TEMPLATE_NOT_FOUND_MESSAGE = "未找到列映射模板"
FILE_OR_TEXT_MESSAGE = "请上传文件或粘贴内容"
BATCH_NOT_FOUND_MESSAGE = "导入批次不存在"
PREVIEW_EXPIRED_MESSAGE = "预览已过期，请重新上传或粘贴内容后再提交"
NO_VALID_ROWS_MESSAGE = "没有有效记录，无法提交"
COMMIT_CONFLICT_MESSAGE = "批次已被其他操作更新，请刷新后重试"
BATCH_NOT_PREVIEW_MESSAGE = "只有预览批次可以丢弃"
BATCH_NOT_REVOCABLE_MESSAGE = "只有生效批次可以撤销"

__all__ = [
    "PARSER_VERSION",
    "commit_batch",
    "discard_batch",
    "get_batch",
    "list_batch_errors",
    "list_batch_records",
    "list_batches",
    "preview_import",
    "read_mapping_template",
    "revoke_batch",
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
    _cleanup_import_staging(session, get_datetime_utc())
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


def commit_batch(
    session: Session,
    batch_id: uuid.UUID,
    *,
    operator: User,
    save_mapping_template: bool = True,
) -> ImportCommitPublic:
    """Commit a preview, superseding the scope's current committed batch.

    One transaction flips the old batch to ``superseded``, flips this batch to
    ``committed``, saves the mapping template, and marks the attendance month
    stale (spec 6.7.2); the caller route owns the response. The development
    seed passes ``save_mapping_template=False`` when the company already has a
    user-maintained template, so re-seeding never overwrites that edit.
    """
    now = get_datetime_utc()
    _cleanup_import_staging(session, now)
    session.commit()
    batch = _get_batch_or_404(session, batch_id)

    if batch.status == ImportBatchStatus.COMMITTED:
        return _commit_result(session, batch)
    if (
        batch.status == ImportBatchStatus.DISCARDED
        and batch.discard_reason == DISCARD_REASON_EXPIRED
    ):
        raise DomainError(AttendanceErrorCode.PREVIEW_EXPIRED, PREVIEW_EXPIRED_MESSAGE)
    if batch.status != ImportBatchStatus.PREVIEW:
        raise DomainError(
            AttendanceErrorCode.IMPORT_COMMIT_CONFLICT, COMMIT_CONFLICT_MESSAGE
        )
    if batch.expires_at is not None and batch.expires_at <= now:
        raise DomainError(AttendanceErrorCode.PREVIEW_EXPIRED, PREVIEW_EXPIRED_MESSAGE)
    if batch.valid_records == 0:
        raise DomainError(AttendanceErrorCode.NO_VALID_ROWS, NO_VALID_ROWS_MESSAGE)

    # Snapshot the committed batch before waiting for the month lock. Two
    # commits for one scope that interleave here must not both win: the second
    # sees a different current batch after the lock and returns a conflict.
    prior_committed = _current_committed(session, batch)
    prior_committed_id = prior_committed.id if prior_committed is not None else None

    superseded_id: uuid.UUID | None = None
    try:
        month_row = get_or_create_month(session, batch.company_id, batch.month)
        ensure_month_editable(month_row)
        # Re-read under a row lock: the pre-lock status is stale, mypy keeps its
        # narrowing otherwise, and a concurrent discard/revoke must serialize.
        target_batch = _get_batch_for_update(session, batch.id)
        if target_batch.status == ImportBatchStatus.COMMITTED:
            return _commit_result(session, target_batch)
        if target_batch.status != ImportBatchStatus.PREVIEW:
            raise DomainError(
                AttendanceErrorCode.IMPORT_COMMIT_CONFLICT, COMMIT_CONFLICT_MESSAGE
            )

        current_committed = _current_committed(session, target_batch)
        current_committed_id = (
            current_committed.id if current_committed is not None else None
        )
        if current_committed_id != prior_committed_id:
            raise DomainError(
                AttendanceErrorCode.IMPORT_COMMIT_CONFLICT, COMMIT_CONFLICT_MESSAGE
            )
        if current_committed is not None:
            superseded_id = current_committed.id
            current_committed.status = ImportBatchStatus.SUPERSEDED
            current_committed.superseded_at = now
            current_committed.superseded_by_batch_id = target_batch.id
            session.add(current_committed)
            # Release the partial unique index before claiming it for this batch.
            session.flush()

        target_batch.status = ImportBatchStatus.COMMITTED
        target_batch.committed_at = now
        target_batch.expires_at = None
        session.add(target_batch)
        if save_mapping_template:
            _save_mapping_template(session, target_batch, operator=operator)
        mark_month_stale(month_row)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise DomainError(
            AttendanceErrorCode.IMPORT_COMMIT_CONFLICT, COMMIT_CONFLICT_MESSAGE
        )
    except DomainError:
        session.rollback()
        raise
    session.refresh(target_batch)
    return _commit_result(session, target_batch, superseded_batch_id=superseded_id)


def discard_batch(session: Session, batch_id: uuid.UUID) -> ImportBatchPublic:
    """Discard a preview, deleting its staged rows and errors immediately."""
    batch = _get_batch_for_update(session, batch_id)
    if batch.status != ImportBatchStatus.PREVIEW:
        raise DomainError(
            AttendanceErrorCode.BATCH_NOT_PREVIEW, BATCH_NOT_PREVIEW_MESSAGE
        )
    _delete_batch_payload(session, batch.id)
    batch.status = ImportBatchStatus.DISCARDED
    batch.discarded_at = get_datetime_utc()
    batch.discard_reason = DISCARD_REASON_USER
    batch.expires_at = None
    session.add(batch)
    session.commit()
    session.refresh(batch)
    return ImportBatchPublic.model_validate(batch)


def revoke_batch(session: Session, batch_id: uuid.UUID) -> ImportBatchPublic:
    """Revoke the active committed batch in an editable month.

    The previous superseded batch is never restored (spec 6.7.4); the scope
    simply has no committed batch until a new preview is committed.
    """
    batch = _get_batch_for_update(session, batch_id)
    if batch.status != ImportBatchStatus.COMMITTED:
        raise DomainError(
            AttendanceErrorCode.BATCH_NOT_REVOCABLE, BATCH_NOT_REVOCABLE_MESSAGE
        )
    try:
        month_row = get_or_create_month(session, batch.company_id, batch.month)
        ensure_month_editable(month_row)
        _delete_batch_payload(session, batch.id)
        batch.status = ImportBatchStatus.REVOKED
        batch.revoked_at = get_datetime_utc()
        batch.expires_at = None
        session.add(batch)
        mark_month_stale(month_row)
        session.commit()
    except DomainError:
        session.rollback()
        raise
    session.refresh(batch)
    return ImportBatchPublic.model_validate(batch)


def _delete_batch_payload(
    session: Session, batch_id: uuid.UUID, *, budget: int | None = None
) -> tuple[int, int]:
    """Delete a batch's rows and errors, optionally within a row budget.

    Returns ``(deleted, remaining)``. ``budget=None`` deletes everything; a
    limited call may leave some rows for the next lazy-cleanup entry point.
    """
    total = _batch_payload_count(session, batch_id)
    deleted = 0
    for model in (PunchRecord, OaTrip, OaOvertime, OaLeave):
        limit = None if budget is None else budget - deleted
        if limit is not None and limit <= 0:
            break
        statement = select(model.id).where(col(model.batch_id) == batch_id)
        if limit is not None:
            statement = statement.limit(limit)
        ids = list(session.exec(statement).all())
        if ids:
            session.exec(delete(model).where(col(model.id).in_(ids)))
            deleted += len(ids)
    limit = None if budget is None else budget - deleted
    if limit is None or limit > 0:
        statement = select(ImportBatchError.id).where(
            col(ImportBatchError.batch_id) == batch_id
        )
        if limit is not None:
            statement = statement.limit(limit)
        error_ids = list(session.exec(statement).all())
        if error_ids:
            session.exec(
                delete(ImportBatchError).where(col(ImportBatchError.id).in_(error_ids))
            )
            deleted += len(error_ids)
    return deleted, max(total - deleted, 0)


def _commit_result(
    session: Session,
    batch: ImportBatch,
    *,
    superseded_batch_id: uuid.UUID | None = None,
) -> ImportCommitPublic:
    if superseded_batch_id is None:
        superseded_batch_id = session.exec(
            select(ImportBatch.id).where(
                col(ImportBatch.superseded_by_batch_id) == batch.id
            )
        ).first()
    month_row = existing_month(session, batch.company_id, batch.month)
    return ImportCommitPublic(
        batch=ImportBatchPublic.model_validate(batch),
        superseded_batch_id=superseded_batch_id,
        month=batch.month.strftime("%Y-%m"),
        is_stale=month_row.is_stale if month_row is not None else True,
    )


def _get_batch_or_404(session: Session, batch_id: uuid.UUID) -> ImportBatch:
    batch = session.get(ImportBatch, batch_id)
    if batch is None:
        raise DomainError(AttendanceErrorCode.NOT_FOUND, BATCH_NOT_FOUND_MESSAGE)
    return batch


def _get_batch_for_update(session: Session, batch_id: uuid.UUID) -> ImportBatch:
    batch = session.exec(
        select(ImportBatch).where(col(ImportBatch.id) == batch_id).with_for_update()
    ).first()
    if batch is None:
        raise DomainError(AttendanceErrorCode.NOT_FOUND, BATCH_NOT_FOUND_MESSAGE)
    return batch


def _current_committed(session: Session, batch: ImportBatch) -> ImportBatch | None:
    return session.exec(
        select(ImportBatch).where(
            col(ImportBatch.company_id) == batch.company_id,
            col(ImportBatch.data_type) == batch.data_type,
            col(ImportBatch.month) == batch.month,
            col(ImportBatch.status) == ImportBatchStatus.COMMITTED,
        )
    ).first()


def _save_mapping_template(
    session: Session, batch: ImportBatch, *, operator: User
) -> None:
    template = session.exec(
        select(ImportMappingTemplate).where(
            col(ImportMappingTemplate.company_id) == batch.company_id,
            col(ImportMappingTemplate.data_type) == batch.data_type,
        )
    ).first()
    if template is None:
        template = ImportMappingTemplate(
            company_id=batch.company_id,
            data_type=batch.data_type,
            mapping=batch.column_mapping,
            header_columns=batch.header_columns,
            updated_by=operator.id,
        )
        try:
            # A concurrent first commit for the same company/data type can win
            # the unique insert; fall back to updating its row instead of
            # turning a valid commit into an import_commit_conflict.
            with session.begin_nested():
                session.add(template)
                session.flush()
        except IntegrityError:
            template = session.exec(
                select(ImportMappingTemplate).where(
                    col(ImportMappingTemplate.company_id) == batch.company_id,
                    col(ImportMappingTemplate.data_type) == batch.data_type,
                )
            ).one()
            template.mapping = batch.column_mapping
            template.header_columns = batch.header_columns
            template.updated_by = operator.id
            template.updated_at = get_datetime_utc()
            session.add(template)
        return
    template.mapping = batch.column_mapping
    template.header_columns = batch.header_columns
    template.updated_by = operator.id
    template.updated_at = get_datetime_utc()
    session.add(template)


def list_batches(
    session: Session,
    *,
    company_id: uuid.UUID,
    data_type: ImportDataType | None,
    month: date | None,
    status: ImportBatchStatus | None,
    skip: int,
    limit: int,
) -> ImportBatchesPublic:
    """Batch history for one company, newest first, with optional filters."""
    get_company_or_404(session, company_id)
    _cleanup_import_staging(session, get_datetime_utc())
    session.commit()

    filters: list[ColumnElement[bool]] = [col(ImportBatch.company_id) == company_id]
    if data_type is not None:
        filters.append(col(ImportBatch.data_type) == data_type)
    if month is not None:
        filters.append(col(ImportBatch.month) == month)
    if status is not None:
        filters.append(col(ImportBatch.status) == status)
    statement = (
        select(ImportBatch)
        .where(*filters)
        .order_by(col(ImportBatch.created_at).desc(), col(ImportBatch.id).desc())
    )
    count_statement = select(func.count()).select_from(ImportBatch).where(*filters)
    batches, count = paginate(
        session, statement, count_statement, skip=skip, limit=limit
    )
    return ImportBatchesPublic(
        data=[ImportBatchPublic.model_validate(batch) for batch in batches],
        count=count,
    )


def get_batch(session: Session, batch_id: uuid.UUID) -> ImportBatchPublic:
    """Batch detail with counts, mapping/header, and the first 20 samples."""
    batch = _get_batch_or_404(session, batch_id)
    public = ImportBatchPublic.model_validate(batch)
    public.samples = _batch_samples(session, batch)
    return public


def list_batch_errors(
    session: Session,
    batch_id: uuid.UUID,
    *,
    severity: ImportSeverity | None,
    skip: int,
    limit: int,
) -> ImportBatchErrorsPublic:
    _get_batch_or_404(session, batch_id)
    filters: list[ColumnElement[bool]] = [col(ImportBatchError.batch_id) == batch_id]
    if severity is not None:
        filters.append(col(ImportBatchError.severity) == severity)
    statement = (
        select(ImportBatchError)
        .where(*filters)
        .order_by(
            col(ImportBatchError.source_row_number).asc(),
            col(ImportBatchError.id).asc(),
        )
    )
    count_statement = select(func.count()).select_from(ImportBatchError).where(*filters)
    rows, count = paginate(session, statement, count_statement, skip=skip, limit=limit)
    return ImportBatchErrorsPublic(
        data=[ImportBatchErrorPublic.model_validate(row) for row in rows],
        count=count,
    )


def list_batch_records(
    session: Session,
    batch_id: uuid.UUID,
    *,
    skip: int,
    limit: int,
) -> ImportBatchRecordsPublic:
    """Page the normalized records for the batch's data type."""
    batch = _get_batch_or_404(session, batch_id)
    statement: Any
    count_statement: Any
    if batch.data_type == ImportDataType.PUNCH:
        statement = (
            select(PunchRecord)
            .where(col(PunchRecord.batch_id) == batch_id)
            .order_by(
                col(PunchRecord.source_row_number).asc(),
                col(PunchRecord.id).asc(),
            )
        )
        count_statement = (
            select(func.count())
            .select_from(PunchRecord)
            .where(col(PunchRecord.batch_id) == batch_id)
        )
        rows, count = paginate(
            session, statement, count_statement, skip=skip, limit=limit
        )
        records: list[ImportRecordPublic] = [
            PunchRecordPublic.model_validate(row) for row in rows
        ]
    elif batch.data_type == ImportDataType.TRIP:
        statement = (
            select(OaTrip)
            .where(col(OaTrip.batch_id) == batch_id)
            .order_by(
                col(OaTrip.source_row_number).asc(),
                col(OaTrip.split_index).asc(),
            )
        )
        count_statement = (
            select(func.count())
            .select_from(OaTrip)
            .where(col(OaTrip.batch_id) == batch_id)
        )
        rows, count = paginate(
            session, statement, count_statement, skip=skip, limit=limit
        )
        records = [OaTripPublic.model_validate(row) for row in rows]
    elif batch.data_type == ImportDataType.OT:
        statement = (
            select(OaOvertime)
            .where(col(OaOvertime.batch_id) == batch_id)
            .order_by(
                col(OaOvertime.source_row_number).asc(),
                col(OaOvertime.id).asc(),
            )
        )
        count_statement = (
            select(func.count())
            .select_from(OaOvertime)
            .where(col(OaOvertime.batch_id) == batch_id)
        )
        rows, count = paginate(
            session, statement, count_statement, skip=skip, limit=limit
        )
        days = _overtime_days(session, [row.id for row in rows])
        records = []
        for row in rows:
            public_overtime = OaOvertimePublic.model_validate(row)
            public_overtime.days = [
                OaOvertimeDayPublic.model_validate(day) for day in days.get(row.id, [])
            ]
            records.append(public_overtime)
    else:
        statement = (
            select(OaLeave)
            .where(col(OaLeave.batch_id) == batch_id)
            .order_by(
                col(OaLeave.source_row_number).asc(),
                col(OaLeave.id).asc(),
            )
        )
        count_statement = (
            select(func.count())
            .select_from(OaLeave)
            .where(col(OaLeave.batch_id) == batch_id)
        )
        rows, count = paginate(
            session, statement, count_statement, skip=skip, limit=limit
        )
        records = [OaLeavePublic.model_validate(row) for row in rows]
    return ImportBatchRecordsPublic(
        data_type=batch.data_type, records=records, count=count
    )


def _overtime_days(
    session: Session, overtime_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[OaOvertimeDay]]:
    if not overtime_ids:
        return {}
    rows = session.exec(
        select(OaOvertimeDay)
        .where(col(OaOvertimeDay.overtime_id).in_(overtime_ids))
        .order_by(
            col(OaOvertimeDay.overtime_id).asc(),
            col(OaOvertimeDay.work_date).asc(),
        )
    ).all()
    grouped: dict[uuid.UUID, list[OaOvertimeDay]] = defaultdict(list)
    for row in rows:
        grouped[row.overtime_id].append(row)
    return dict(grouped)


def _batch_samples(session: Session, batch: ImportBatch) -> list[dict[str, Any]]:
    """The first 20 normalized rows in the same shape as preview samples."""
    if batch.data_type == ImportDataType.PUNCH:
        rows = session.exec(
            select(PunchRecord)
            .where(col(PunchRecord.batch_id) == batch.id)
            .order_by(
                col(PunchRecord.source_row_number).asc(),
                col(PunchRecord.id).asc(),
            )
            .limit(MAX_SAMPLES)
        ).all()
        return [_punch_sample(row) for row in rows]
    if batch.data_type == ImportDataType.TRIP:
        trips = session.exec(
            select(OaTrip)
            .where(col(OaTrip.batch_id) == batch.id)
            .order_by(
                col(OaTrip.source_row_number).asc(),
                col(OaTrip.split_index).asc(),
            )
            .limit(MAX_SAMPLES)
        ).all()
        return [_trip_sample(row, row.days_declared) for row in trips]
    if batch.data_type == ImportDataType.OT:
        overtime_rows = session.exec(
            select(OaOvertime)
            .where(col(OaOvertime.batch_id) == batch.id)
            .order_by(
                col(OaOvertime.source_row_number).asc(),
                col(OaOvertime.id).asc(),
            )
            .limit(MAX_SAMPLES)
        ).all()
        days = _overtime_days(session, [row.id for row in overtime_rows])
        return [
            _ot_sample(
                row,
                [(day.work_date, day.minutes) for day in days.get(row.id, [])],
            )
            for row in overtime_rows
        ]
    leaves = session.exec(
        select(OaLeave)
        .where(col(OaLeave.batch_id) == batch.id)
        .order_by(
            col(OaLeave.source_row_number).asc(),
            col(OaLeave.id).asc(),
        )
        .limit(MAX_SAMPLES)
    ).all()
    return [_leave_sample(row) for row in leaves]


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


def _cleanup_import_staging(session: Session, now: datetime) -> int:
    """Lazily clean import staging within one 5,000-row budget.

    Runs on preview, commit, and list entry points: expired previews lose
    their rows/errors immediately, and superseded batches older than 90 days
    lose ``raw_row`` and error detail while keeping normalized rows (spec 6.6).
    """
    used = _cleanup_expired_previews(session, now, budget=CLEANUP_ROW_BUDGET)
    remaining = CLEANUP_ROW_BUDGET - used
    if remaining > 0:
        used += _cleanup_superseded_payloads(session, now, budget=remaining)
    remaining = CLEANUP_ROW_BUDGET - used
    if remaining > 0:
        used += _cleanup_discarded_metadata(session, now, budget=remaining)
    return used


def _cleanup_expired_previews(
    session: Session,
    now: datetime,
    *,
    budget: int,
    exclude_batch_id: uuid.UUID | None = None,
) -> int:
    """Discard expired previews, deleting their rows and errors immediately.

    Deletion never exceeds the caller's row budget. A preview larger than the
    budget is cleaned across entry points and only becomes ``discarded`` once
    its payload is gone; metadata remains for the 90-day retention window.
    """
    conditions: list[ColumnElement[bool]] = [
        col(ImportBatch.status) == ImportBatchStatus.PREVIEW,
        col(ImportBatch.expires_at).is_not(None),
        col(ImportBatch.expires_at) <= now,
    ]
    if exclude_batch_id is not None:
        conditions.append(col(ImportBatch.id) != exclude_batch_id)
    expired = list(
        session.exec(
            select(ImportBatch)
            .where(*conditions)
            .order_by(col(ImportBatch.expires_at).asc())
        ).all()
    )
    deleted = 0
    for batch in expired:
        remaining = budget - deleted
        if remaining <= 0:
            break
        deleted += _discard_preview_batch(session, batch, now, budget=remaining)
    return deleted


def _cleanup_superseded_payloads(
    session: Session, now: datetime, *, budget: int
) -> int:
    """Clear old superseded payloads while keeping the normalized rows."""
    if budget <= 0:
        return 0
    cutoff = now - SUPERSEDED_RAW_RETENTION
    batches = session.exec(
        select(ImportBatch)
        .where(
            col(ImportBatch.status) == ImportBatchStatus.SUPERSEDED,
            col(ImportBatch.superseded_at).is_not(None),
            col(ImportBatch.superseded_at) <= cutoff,
        )
        .order_by(col(ImportBatch.superseded_at).asc())
    ).all()
    cleared = 0
    for batch in batches:
        remaining = budget - cleared
        if remaining <= 0:
            break
        error_ids = list(
            session.exec(
                select(ImportBatchError.id)
                .where(col(ImportBatchError.batch_id) == batch.id)
                .limit(remaining)
            ).all()
        )
        if error_ids:
            session.exec(
                delete(ImportBatchError).where(col(ImportBatchError.id).in_(error_ids))
            )
            cleared += len(error_ids)
        for model in (PunchRecord, OaTrip, OaOvertime, OaLeave):
            remaining = budget - cleared
            if remaining <= 0:
                break
            record_ids = list(
                session.exec(
                    select(model.id)
                    .where(
                        col(model.batch_id) == batch.id,
                        col(model.raw_row) != {},
                    )
                    .limit(remaining)
                ).all()
            )
            if record_ids:
                session.exec(
                    update(model)
                    .where(col(model.id).in_(record_ids))
                    .values(raw_row={})
                )
                cleared += len(record_ids)
    return cleared


def _cleanup_discarded_metadata(session: Session, now: datetime, *, budget: int) -> int:
    """Hard-delete discarded preview metadata after its 90-day retention."""
    if budget <= 0:
        return 0
    cutoff = now - DISCARDED_METADATA_RETENTION
    batch_ids = list(
        session.exec(
            select(ImportBatch.id)
            .where(
                col(ImportBatch.status) == ImportBatchStatus.DISCARDED,
                col(ImportBatch.discarded_at).is_not(None),
                col(ImportBatch.discarded_at) <= cutoff,
            )
            .order_by(col(ImportBatch.discarded_at).asc())
            .limit(budget)
        ).all()
    )
    if not batch_ids:
        return 0
    session.exec(delete(ImportBatch).where(col(ImportBatch.id).in_(batch_ids)))
    return len(batch_ids)


def _batch_payload_count(session: Session, batch_id: uuid.UUID) -> int:
    total = 0
    for model in (PunchRecord, OaTrip, OaOvertime, OaLeave):
        total += session.exec(
            select(func.count())
            .select_from(model)
            .where(col(model.batch_id) == batch_id)
        ).one()
    total += session.exec(
        select(func.count())
        .select_from(ImportBatchError)
        .where(col(ImportBatchError.batch_id) == batch_id)
    ).one()
    return total


def _discard_preview_batch(
    session: Session, batch: ImportBatch, now: datetime, *, budget: int
) -> int:
    deleted, remaining = _delete_batch_payload(session, batch.id, budget=budget)
    if remaining == 0:
        batch.status = ImportBatchStatus.DISCARDED
        batch.discarded_at = now
        batch.discard_reason = DISCARD_REASON_EXPIRED
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
        return _punch_sample(record)
    if isinstance(record, import_normalize.OaTripData):
        return _trip_sample(record, record.days_declared)
    if isinstance(record, import_normalize.OaOvertimeData):
        return _ot_sample(record, record.days)
    return _leave_sample(record)


def _punch_sample(
    record: PunchRecord | import_normalize.PunchData,
) -> dict[str, Any]:
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


def _trip_sample(
    record: OaTrip | import_normalize.OaTripData,
    days_declared: Decimal | None,
) -> dict[str, Any]:
    return {
        "source_row_number": record.source_row_number,
        "split_index": record.split_index,
        "employee_id": str(record.employee_id),
        "employee_name": record.employee_name_raw,
        "department": record.department_raw,
        "approval_no": record.approval_no,
        "start_at": _iso(record.start_at),
        "end_at": _iso(record.end_at),
        "days_declared": _decimal(days_declared),
    }


def _ot_sample(
    record: OaOvertime | import_normalize.OaOvertimeData,
    days: Sequence[tuple[date, int]],
) -> dict[str, Any]:
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
            for work_date, minutes in days
        ],
    }


def _leave_sample(
    record: OaLeave | import_normalize.OaLeaveData,
) -> dict[str, Any]:
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
