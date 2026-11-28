"""Factories for payroll test data.

Factories only build database state; business rules are exercised through the
service/API layer instead.
"""

import uuid
from datetime import date
from typing import Any

from sqlmodel import Session

from app.enums import PayrollExportStatus, PayrollExportType
from app.models import Company, PayrollExport
from tests.utils.factories import create_company

DEFAULT_EXPORT_MONTH = date(2026, 9, 1)


def build_payroll_export(
    *,
    company_id: uuid.UUID,
    status: PayrollExportStatus = PayrollExportStatus.QUEUED,
    month: date = DEFAULT_EXPORT_MONTH,
    export_type: PayrollExportType = PayrollExportType.PAYSLIP_ZIP,
    **overrides: Any,
) -> PayrollExport:
    """Build an unsaved export row; batch tests add many of these at once."""
    return PayrollExport(
        company_id=company_id,
        month=month,
        export_type=export_type,
        format="zip",
        status=status,
        **overrides,
    )


def create_payroll_export(
    db: Session,
    *,
    company: Company | None = None,
    status: PayrollExportStatus = PayrollExportStatus.QUEUED,
    **overrides: Any,
) -> PayrollExport:
    company = company or create_company(db)
    job = build_payroll_export(
        company_id=company.id,
        status=status,
        **overrides,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job
