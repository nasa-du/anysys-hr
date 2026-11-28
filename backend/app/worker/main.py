"""Payroll export worker skeleton.

The worker is a separate process from the same image::

    python -m app.worker.main

Phase 0 only establishes the process contract: it verifies the shared
``payroll-exports`` directory, polls the database for queued exports, and
reports the queue depth. It deliberately does **not** claim or render jobs;
``FOR UPDATE SKIP LOCKED`` claiming, rendering, TTL, timeout, and housekeeping
land with the payslip/report slice. Until then a queued export stays queued.

The export directory is mounted read-write here and read-only in the backend.
``PAYROLL_EXPORTS_DIR`` overrides the container default for local runs and
tests.
"""

import logging
import os
import shutil
import signal
import threading
from pathlib import Path

from sqlalchemy import func
from sqlmodel import Session, select

from app.core.db import engine
from app.enums import PayrollExportStatus
from app.models import PayrollExport

logger = logging.getLogger("app.worker")

DEFAULT_EXPORTS_DIR = Path("/app/exports")
DEFAULT_POLL_SECONDS = 5.0
MIN_FREE_DISK_BYTES = 2 * 1024**3


def exports_dir_from_env() -> Path:
    """Return the configured export directory, defaulting to the volume path."""
    return Path(os.environ.get("PAYROLL_EXPORTS_DIR", str(DEFAULT_EXPORTS_DIR)))


def ensure_exports_dir(exports_dir: Path) -> None:
    """Create the shared export directory if the volume is not present yet."""
    exports_dir.mkdir(parents=True, exist_ok=True)


def free_disk_bytes(exports_dir: Path) -> int:
    """Free bytes on the filesystem that holds the export directory."""
    return shutil.disk_usage(exports_dir).free


def count_queued_exports(session: Session) -> int:
    """Number of exports waiting for the worker; nothing is claimed."""
    statement = (
        select(func.count())
        .select_from(PayrollExport)
        .where(PayrollExport.status == PayrollExportStatus.QUEUED)
    )
    return int(session.exec(statement).one())


def poll_once(session: Session, exports_dir: Path) -> int:
    """One polling cycle: report queue depth without consuming any job."""
    queued = count_queued_exports(session)
    logger.info(
        "Payroll worker poll: queued_exports=%d exports_dir=%s",
        queued,
        exports_dir,
    )
    return queued


def run_worker(
    *,
    poll_seconds: float = DEFAULT_POLL_SECONDS,
    exports_dir: Path | None = None,
    stop_event: threading.Event | None = None,
    max_polls: int | None = None,
) -> None:
    """Run the polling loop until stopped or ``max_polls`` cycles elapse."""
    directory = exports_dir or exports_dir_from_env()
    ensure_exports_dir(directory)
    free_bytes = free_disk_bytes(directory)
    if free_bytes < MIN_FREE_DISK_BYTES:
        logger.warning(
            "Payroll worker export volume has %.1f GiB free; jobs will fail "
            "with insufficient_disk once job semantics land.",
            free_bytes / 1024**3,
        )

    stop = stop_event or threading.Event()
    logger.info(
        "Payroll worker skeleton started: exports_dir=%s poll_seconds=%s "
        "job_consumption=disabled",
        directory,
        poll_seconds,
    )

    polls = 0
    while not stop.is_set():
        try:
            with Session(engine) as session:
                poll_once(session, directory)
        except Exception:
            # The database may still be starting; keep the process alive and
            # retry on the next cycle. Job semantics will add proper error
            # handling and worker_lost heartbeats.
            logger.exception("Payroll worker poll failed; retrying")

        polls += 1
        if max_polls is not None and polls >= max_polls:
            break
        stop.wait(poll_seconds)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    stop = threading.Event()

    def _request_stop(signum: int, _frame: object) -> None:
        logger.info("Payroll worker received signal %s; stopping", signum)
        stop.set()

    signal.signal(signal.SIGINT, _request_stop)
    signal.signal(signal.SIGTERM, _request_stop)

    run_worker(stop_event=stop)


if __name__ == "__main__":
    main()
