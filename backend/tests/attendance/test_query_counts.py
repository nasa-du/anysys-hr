"""Query-count guards for the key attendance list endpoints.

Spec section 14.9: batch-load employee and department display names so list
responses do not issue one query per row. Each guard compares a small page with
a large one; the statement count must not grow with the number of rows.
"""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, timedelta
from typing import Any

from sqlalchemy import event
from sqlmodel import Session

from app.services.attendance import results, roster
from tests.utils.attendance_factories import (
    create_attendance_day_result,
    create_attendance_month,
    create_attendance_month_summary,
    create_calc_run,
)
from tests.utils.factories import (
    create_company,
    create_department,
    create_employee,
    create_position,
)

MONTH = "2026-09"
WORK_DATES = [date(2026, 9, day) for day in (7, 8, 9)]


@contextmanager
def _count_selects(session: Session) -> Iterator[list[str]]:
    statements: list[str] = []
    engine = session.get_bind()

    def before_cursor_execute(
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        del conn, cursor, parameters, context, executemany
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)


def _seed_results(db: Session, people: int) -> uuid.UUID:
    company = create_company(db)
    department = create_department(db, company=company)
    position = create_position(db, company=company, dept=department)
    employees = [
        create_employee(db, dept=department, position=position) for _ in range(people)
    ]
    month = create_attendance_month(db, company_id=company.id)
    calc_run = create_calc_run(db, attendance_month_id=month.id)
    for employee in employees:
        for work_date in WORK_DATES:
            create_attendance_day_result(
                db,
                company_id=company.id,
                attendance_month_id=month.id,
                calc_run_id=calc_run.id,
                employee_id=employee.id,
                work_date=work_date,
            )
        create_attendance_month_summary(
            db,
            company_id=company.id,
            attendance_month_id=month.id,
            calc_run_id=calc_run.id,
            employee_id=employee.id,
        )
    return company.id


_DAY_RESULT_DEFAULTS: dict[str, Any] = {
    "month": MONTH,
    "employee_id": None,
    "dept_id": None,
    "date_from": None,
    "date_to": None,
    "day_type": None,
    "roster_state": None,
    "day_statuses": None,
    "flags": None,
    "is_abnormal": None,
    "has_adjustment": None,
    "keyword": None,
    "skip": 0,
    "limit": 500,
}


def _list_day_results(session: Session, company_id: uuid.UUID, **overrides: Any) -> Any:
    return results.list_day_results(
        session, company_id=company_id, **{**_DAY_RESULT_DEFAULTS, **overrides}
    )


def _day_results(session: Session, company_id: uuid.UUID) -> int:
    return _list_day_results(session, company_id).count


def _month_summaries(session: Session, company_id: uuid.UUID) -> int:
    return results.list_month_summaries(
        session,
        company_id=company_id,
        month=MONTH,
        employee_id=None,
        dept_id=None,
        keyword=None,
        skip=0,
        limit=500,
    ).count


def _roster_employees(session: Session, company_id: uuid.UUID) -> int:
    return roster.read_roster_employees(
        session,
        company_id=company_id,
        month=MONTH,
        dept_id=None,
        keyword=None,
        skip=0,
        limit=500,
    ).count


def _statement_counts(session: Session, company_id: uuid.UUID) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name, call in (
        ("days", _day_results),
        ("summaries", _month_summaries),
        ("roster", _roster_employees),
    ):
        with _count_selects(session) as statements:
            call(session, company_id)
        counts[name] = len(statements)
    return counts


def test_list_queries_do_not_grow_with_the_number_of_rows(db: Session) -> None:
    small_company = _seed_results(db, people=1)
    large_company = _seed_results(db, people=30)

    small = _statement_counts(db, small_company)
    large = _statement_counts(db, large_company)

    assert large == small
    assert large["days"] <= 6, large
    assert large["summaries"] <= 7, large
    assert large["roster"] <= 6, large


def test_day_result_filters_do_not_add_per_row_queries(db: Session) -> None:
    company_id = _seed_results(db, people=30)
    first_date = WORK_DATES[0]
    last_date = first_date + timedelta(days=1)

    with _count_selects(db) as statements:
        page = _list_day_results(
            db, company_id, date_from=first_date, date_to=last_date
        )

    assert page.count == 60
    assert len(statements) <= 6, statements
