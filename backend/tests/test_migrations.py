"""Migration chain checks against a throwaway database.

The round-trip uses its own database so the session's test database is never
left without tables, and each test starts from an upgrade in a known state.
"""

import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import alembic.command
import alembic.config
import psycopg
import pytest
import sqlalchemy as sa
from psycopg import sql
from sqlalchemy.engine import URL, make_url

from app.core.config import settings

BACKEND_DIR = Path(__file__).resolve().parents[1]
ALEMBIC_CONFIG = BACKEND_DIR / "alembic.ini"
BASIC_MANAGEMENT_TABLES = {
    "company",
    "department",
    "position",
    "cost_center",
    "employee",
}


def _admin_dsn() -> str:
    test_url = make_url(str(settings.TEST_DATABASE_URL))
    admin_url = test_url.set(database="postgres", drivername="postgresql")
    return admin_url.render_as_string(hide_password=False)


@pytest.fixture
def throwaway_database() -> Iterator[URL]:
    test_url = make_url(str(settings.TEST_DATABASE_URL))
    database_name = f"migration_{uuid.uuid4().hex[:8]}_test"
    admin_dsn = _admin_dsn()

    with psycopg.connect(admin_dsn, autocommit=True) as connection:
        connection.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name))
        )

    try:
        yield test_url.set(database=database_name)
    finally:
        with psycopg.connect(admin_dsn, autocommit=True) as connection:
            connection.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                    sql.Identifier(database_name)
                )
            )


def _run_alembic(
    url: URL,
    command: Callable[[alembic.config.Config, str], None],
    target: str,
) -> None:
    original_url = settings.DATABASE_URL
    settings.DATABASE_URL = url.render_as_string(  # type: ignore[assignment]
        hide_password=False
    )
    try:
        config = alembic.config.Config(str(ALEMBIC_CONFIG))
        config.set_main_option("script_location", str(BACKEND_DIR / "app" / "alembic"))
        command(config, target)
    finally:
        settings.DATABASE_URL = original_url


def _inspect(url: URL, action: Any) -> Any:
    engine = sa.create_engine(url, poolclass=sa.pool.NullPool)
    try:
        return action(sa.inspect(engine), engine)
    finally:
        engine.dispose()


def _tables(url: URL) -> set[str]:
    return _inspect(url, lambda inspector, _engine: set(inspector.get_table_names()))


def test_migrations_round_trip_to_base_and_back(
    throwaway_database: URL,
) -> None:
    _run_alembic(throwaway_database, alembic.command.upgrade, "head")
    _run_alembic(throwaway_database, alembic.command.downgrade, "base")
    _run_alembic(throwaway_database, alembic.command.upgrade, "head")

    tables = _tables(throwaway_database)

    assert BASIC_MANAGEMENT_TABLES <= tables
    assert "item" not in tables


def test_dropping_items_downgrades_to_an_empty_item_table(
    throwaway_database: URL,
) -> None:
    _run_alembic(throwaway_database, alembic.command.upgrade, "head")
    assert "item" not in _tables(throwaway_database)

    _run_alembic(throwaway_database, alembic.command.downgrade, "fe56fa70289e")

    def inspect_item(inspector: sa.Inspector, engine: sa.Engine) -> Any:
        columns = {column["name"]: column for column in inspector.get_columns("item")}
        foreign_keys = inspector.get_foreign_keys("item")
        with engine.connect() as connection:
            row_count = connection.execute(
                sa.text("SELECT count(*) FROM item")
            ).scalar_one()
        return columns, foreign_keys, row_count

    columns, foreign_keys, row_count = _inspect(throwaway_database, inspect_item)

    assert set(columns) == {
        "id",
        "title",
        "description",
        "owner_id",
        "created_at",
    }
    assert isinstance(columns["id"]["type"], sa.Uuid)
    assert columns["id"]["nullable"] is False
    assert columns["title"]["type"].length == 255
    assert columns["title"]["nullable"] is False
    assert columns["description"]["type"].length == 255
    assert columns["description"]["nullable"] is True
    assert isinstance(columns["owner_id"]["type"], sa.Uuid)
    assert columns["owner_id"]["nullable"] is False
    assert isinstance(columns["created_at"]["type"], sa.DateTime)
    assert columns["created_at"]["type"].timezone is True
    assert columns["created_at"]["nullable"] is True

    assert len(foreign_keys) == 1
    assert foreign_keys[0]["constrained_columns"] == ["owner_id"]
    assert foreign_keys[0]["referred_table"] == "user"
    assert foreign_keys[0]["options"].get("ondelete") == "CASCADE"
    assert row_count == 0

    _run_alembic(throwaway_database, alembic.command.upgrade, "head")
    assert "item" not in _tables(throwaway_database)
