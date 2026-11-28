"""Payroll route access and foundation boundaries."""

from app.api.deps import get_current_user, payroll_access
from app.main import app


def test_payroll_access_is_the_logged_in_user_dependency() -> None:
    assert payroll_access is get_current_user


def test_this_ticket_adds_no_payroll_business_endpoint() -> None:
    payroll_paths = [
        path for path in app.openapi()["paths"] if path.startswith("/api/v1/payroll")
    ]

    assert payroll_paths == []
