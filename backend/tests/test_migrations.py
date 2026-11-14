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
import alembic.script
import psycopg
import pytest
import sqlalchemy as sa
from psycopg import sql
from sqlalchemy.engine import URL, make_url

from app.core.config import settings
from tests.utils.attendance_tables import (
    ATTENDANCE_TABLES,
    CORE_TABLES,
    IMPORT_TABLES,
    RESULT_TABLES,
    SCHEDULING_TABLES,
)

BACKEND_DIR = Path(__file__).resolve().parents[1]
ALEMBIC_CONFIG = BACKEND_DIR / "alembic.ini"
BASIC_MANAGEMENT_TABLES = {
    "company",
    "department",
    "position",
    "cost_center",
    "employee",
}
ATTENDANCE_MIGRATION_TABLES: dict[str, tuple[str, ...]] = {
    "attendance_core": CORE_TABLES,
    "attendance_scheduling": SCHEDULING_TABLES,
    "attendance_imports": IMPORT_TABLES,
    "attendance_results": RESULT_TABLES,
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

    tables_after_base = _tables(throwaway_database)
    assert not (BASIC_MANAGEMENT_TABLES & tables_after_base)
    assert not (set(ATTENDANCE_TABLES) & tables_after_base)

    _run_alembic(throwaway_database, alembic.command.upgrade, "head")

    tables = _tables(throwaway_database)

    assert BASIC_MANAGEMENT_TABLES <= tables
    assert set(ATTENDANCE_TABLES) <= tables
    assert "item" not in tables


def _attendance_revisions() -> list[tuple[str, str, tuple[str, ...]]]:
    """Return the four attendance migrations oldest-first, by file slug."""
    config = alembic.config.Config(str(ALEMBIC_CONFIG))
    config.set_main_option("script_location", str(BACKEND_DIR / "app" / "alembic"))
    script = alembic.script.ScriptDirectory.from_config(config)

    found: dict[str, list[tuple[str, str, tuple[str, ...]]]] = {
        slug: [] for slug in ATTENDANCE_MIGRATION_TABLES
    }
    for revision in script.walk_revisions():
        filename = Path(revision.path).name if revision.path else ""
        for slug, tables in ATTENDANCE_MIGRATION_TABLES.items():
            # Match the exact migration filename suffix so a future
            # ``attendance_core_fix`` migration cannot shadow the original.
            if filename.endswith(f"{slug}.py"):
                down_revision = revision.down_revision
                assert isinstance(down_revision, str), (
                    f"{slug} must have exactly one down revision"
                )
                found[slug].append((revision.revision, down_revision, tables))

    for slug, revisions in found.items():
        assert len(revisions) == 1, f"Expected one {slug} migration, got {revisions}"
    return [found[slug][0] for slug in ATTENDANCE_MIGRATION_TABLES]


def test_each_attendance_migration_round_trips_individually(
    throwaway_database: URL,
) -> None:
    for revision, down_revision, tables in _attendance_revisions():
        _run_alembic(throwaway_database, alembic.command.upgrade, down_revision)
        _run_alembic(throwaway_database, alembic.command.upgrade, revision)
        assert set(tables) <= _tables(throwaway_database)

        _run_alembic(throwaway_database, alembic.command.downgrade, down_revision)
        remaining = _tables(throwaway_database)
        assert not (set(tables) & remaining)

        _run_alembic(throwaway_database, alembic.command.upgrade, revision)
        assert set(tables) <= _tables(throwaway_database)


def test_attendance_migrations_insert_no_rows(throwaway_database: URL) -> None:
    _run_alembic(throwaway_database, alembic.command.upgrade, "head")

    def attendance_counts(engine: sa.Engine) -> dict[str, int]:
        with engine.connect() as connection:
            return {
                table: connection.execute(
                    sa.text(f'SELECT count(*) FROM "{table}"')
                ).scalar_one()
                for table in ATTENDANCE_TABLES
            }

    counts = _inspect(
        throwaway_database, lambda _inspector, engine: attendance_counts(engine)
    )

    assert counts == dict.fromkeys(ATTENDANCE_TABLES, 0)


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
