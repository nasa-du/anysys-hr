"""Payroll foundation performance smoke.

Phase 0 has no calculation kernel yet, so the routine gate covers the two
foundation paths that run on every deployment: seeding the system defaults and
the worker's queue-count poll over the export audit table. Product calculation
and export budgets arrive with their slices.
"""

import time

import pytest
from sqlmodel import Session

from app.services.payroll.defaults import ensure_payroll_defaults
from app.worker.main import poll_once
from tests.utils.factories import create_company
from tests.utils.payroll_factories import build_payroll_export
from tests.utils.payroll_tables import truncate_payroll_system_tables

DEFAULT_SEED_BUDGET_SECONDS = 1.0
POLL_BUDGET_SECONDS = 0.5
QUEUED_EXPORTS = 1000


@pytest.mark.performance
def test_worker_poll_counts_one_thousand_queued_exports_within_budget(
    db: Session, tmp_path
) -> None:
    company = create_company(db)
    db.add_all(
        build_payroll_export(company_id=company.id) for _ in range(QUEUED_EXPORTS)
    )
    db.commit()

    started = time.perf_counter()
    queued = poll_once(db, tmp_path)
    elapsed = time.perf_counter() - started

    assert queued == QUEUED_EXPORTS
    assert elapsed < POLL_BUDGET_SECONDS, f"poll took {elapsed:.3f}s"


@pytest.mark.performance
def test_system_defaults_seed_within_budget(db: Session) -> None:
    truncate_payroll_system_tables(db)
    db.commit()

    started = time.perf_counter()
    ensure_payroll_defaults(db)
    elapsed = time.perf_counter() - started

    assert elapsed < DEFAULT_SEED_BUDGET_SECONDS, f"seed took {elapsed:.3f}s"
