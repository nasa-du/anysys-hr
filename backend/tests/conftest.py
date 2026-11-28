import os
import subprocess
import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import PostgresDsn, TypeAdapter
from sqlalchemy import text
from sqlmodel import Session, delete

from app.core.config import settings
from tests.utils.attendance_tables import ATTENDANCE_TABLES
from tests.utils.database import ensure_test_database
from tests.utils.payroll_tables import (
    PAYROLL_STARTING_COUNTS,
    PAYROLL_TABLES,
    truncate_payroll_system_tables,
)

BACKEND_DIR = Path(__file__).resolve().parents[1]

test_database_url = TypeAdapter(PostgresDsn).validate_python(
    ensure_test_database(
        str(settings.TEST_DATABASE_URL) if settings.TEST_DATABASE_URL else None
    )
)
os.environ["DATABASE_URL"] = str(test_database_url)
settings.DATABASE_URL = test_database_url

# Import the application only after DATABASE_URL points at the isolated test
# database: app.core.db builds its engine at import time.
from app.core.db import engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.services.payroll.defaults import ensure_payroll_defaults  # noqa: E402
from tests.utils.user import authentication_token_from_email  # noqa: E402
from tests.utils.utils import get_superuser_token_headers  # noqa: E402


def _migrate_test_database() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env={**os.environ, "DATABASE_URL": str(test_database_url)},
        check=False,
    )
    if completed.returncode != 0:
        pytest.exit(
            "Could not prepare the test database. Run "
            "`uv run bash scripts/create-test-db.sh` from the backend directory "
            "and make sure TEST_DATABASE_URL points at it.",
            returncode=1,
        )


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session]:
    _migrate_test_database()
    with Session(engine) as session:
        init_db(session)
        yield session
        # Attendance and payroll rows can block user deletion through RESTRICT
        # audit references; clear them before the final user cleanup.
        session.execute(text("TRUNCATE TABLE company CASCADE"))
        truncate_payroll_system_tables(session)
        statement = delete(User)
        session.execute(statement)
        session.commit()


@pytest.fixture(autouse=True)
def _clean_database(db: Session) -> Generator[None]:
    """Start every test with empty organizations, the seeded payroll defaults,
    and only the first superuser.

    ``TRUNCATE company CASCADE`` also empties department, position,
    cost_center, employee, and every attendance and payroll table that reaches
    ``company`` through a foreign key. Payroll's system-owned tables have no
    company foreign key and are truncated explicitly, then
    ``ensure_payroll_defaults`` restores the 32 system fields and 6 global
    parameters. The first superuser is retained so login fixtures keep
    working.
    """
    db.execute(text("TRUNCATE TABLE company CASCADE"))
    # ``TRUNCATE company CASCADE`` already clears every company-scoped payroll
    # table; the system-owned tables have no company foreign key and need an
    # explicit truncate.
    truncate_payroll_system_tables(db)
    db.execute(delete(User).where(User.email != settings.FIRST_SUPERUSER))
    db.commit()
    ensure_payroll_defaults(db)

    checked_tables = (*ATTENDANCE_TABLES, *PAYROLL_TABLES)
    counts_sql = " UNION ALL ".join(
        f'SELECT {index} AS table_index, count(*) AS row_count FROM "{table}"'
        for index, table in enumerate(checked_tables)
    )
    counts = {
        checked_tables[index]: row_count
        for index, row_count in db.execute(text(counts_sql)).all()
    }
    expected_counts = {
        **dict.fromkeys(ATTENDANCE_TABLES, 0),
        **PAYROLL_STARTING_COUNTS,
    }
    unexpected = {
        table: (counts[table], expected_counts[table])
        for table in checked_tables
        if counts[table] != expected_counts[table]
    }
    assert not unexpected, (
        f"Unexpected row counts after isolation (actual, expected): {unexpected}"
    )
    yield


@pytest.fixture(scope="module")
def client() -> Generator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def superuser_token_headers(client: TestClient) -> dict[str, str]:
    return get_superuser_token_headers(client)


@pytest.fixture
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )
