"""Payroll export worker skeleton: polls the database without claiming jobs.

Phase 0 establishes the worker process, the shared export directory, and the
database polling loop. Job semantics (claiming, rendering, TTL, timeout) land
with the payslip slice, so these tests pin the skeleton contract: a poll
reports what is queued, and it never mutates a job.
"""

from sqlmodel import Session, select

from app.enums import PayrollExportStatus
from app.models import PayrollExport
from app.worker.main import ensure_exports_dir, poll_once, run_worker
from tests.utils.payroll_factories import create_payroll_export


def _queued_export(db: Session) -> PayrollExport:
    return create_payroll_export(db)


def test_poll_reports_queued_jobs_without_claiming_them(db: Session, tmp_path) -> None:
    job = _queued_export(db)

    queued = poll_once(db, tmp_path)

    assert queued == 1
    db.refresh(job)
    assert job.status is PayrollExportStatus.QUEUED
    assert job.started_at is None
    assert job.artifact_path is None
    assert job.error_code is None


def test_poll_reports_zero_when_no_job_is_queued(db: Session, tmp_path) -> None:
    assert poll_once(db, tmp_path) == 0


def test_run_worker_polls_until_stopped_and_creates_the_export_directory(
    db: Session, tmp_path
) -> None:
    job = _queued_export(db)
    exports_dir = tmp_path / "exports"

    run_worker(
        exports_dir=exports_dir,
        poll_seconds=0,
        max_polls=2,
    )

    assert exports_dir.is_dir()
    db.refresh(job)
    assert job.status is PayrollExportStatus.QUEUED
    assert (
        db.exec(select(PayrollExport).where(PayrollExport.id == job.id)).one().status
        is PayrollExportStatus.QUEUED
    )


def test_ensure_exports_dir_creates_nested_directories(tmp_path) -> None:
    exports_dir = tmp_path / "volumes" / "payroll-exports"

    ensure_exports_dir(exports_dir)

    assert exports_dir.is_dir()
