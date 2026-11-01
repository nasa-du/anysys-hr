import pytest
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.core.db import engine
from tests.utils.database import ensure_test_database


def test_accepts_database_whose_name_ends_with_test() -> None:
    url = "postgresql+psycopg://postgres:postgres@localhost:5432/app_test"

    assert ensure_test_database(url) == url


def test_rejects_development_database() -> None:
    url = "postgresql+psycopg://postgres:postgres@localhost:5432/app"

    with pytest.raises(ValueError, match="must end with '_test'"):
        ensure_test_database(url)


def test_rejects_a_name_that_merely_contains_test() -> None:
    url = "postgresql+psycopg://postgres:postgres@localhost:5432/my_test_db"

    with pytest.raises(ValueError, match="must end with '_test'"):
        ensure_test_database(url)


def test_rejects_a_missing_url() -> None:
    with pytest.raises(ValueError, match="TEST_DATABASE_URL is not set"):
        ensure_test_database(None)


def test_rejects_a_url_without_a_database_name() -> None:
    url = "postgresql+psycopg://postgres:postgres@localhost:5432"

    with pytest.raises(ValueError, match="does not include a database name"):
        ensure_test_database(url)


def test_the_application_engine_uses_the_isolated_test_database() -> None:
    assert settings.TEST_DATABASE_URL is not None

    engine_database = make_url(str(engine.url)).database
    test_database = make_url(str(settings.TEST_DATABASE_URL)).database

    assert engine_database == test_database
    assert engine_database is not None
    assert engine_database.endswith("_test")
