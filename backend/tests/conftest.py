import os
import subprocess
import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import PostgresDsn, TypeAdapter
from sqlmodel import Session, delete

from app.core.config import settings
from tests.utils.database import ensure_test_database

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
        statement = delete(User)
        session.execute(statement)
        session.commit()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def superuser_token_headers(client: TestClient) -> dict[str, str]:
    return get_superuser_token_headers(client)


@pytest.fixture(scope="module")
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )
