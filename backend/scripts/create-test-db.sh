#! /usr/bin/env bash
set -e
set -x

# Create the isolated test database if it does not exist yet.
# Safe to run repeatedly; it never touches the development database.
python - <<'PY'
import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

from app.core.config import settings

if settings.TEST_DATABASE_URL is None:
    raise SystemExit(
        "TEST_DATABASE_URL is not set; it must point to a database whose name ends with '_test'."
    )

test_url = make_url(str(settings.TEST_DATABASE_URL))
database_name = test_url.database
if not database_name or not database_name.endswith("_test"):
    raise SystemExit(
        f"Refusing to create database {database_name!r}: the name must end with '_test'."
    )

admin_url = test_url.set(database="postgres", drivername="postgresql")
with psycopg.connect(
    admin_url.render_as_string(hide_password=False), autocommit=True
) as connection:
    exists = connection.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s", (database_name,)
    ).fetchone()
    if exists:
        print(f"Test database {database_name} already exists")
    else:
        connection.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name))
        )
        print(f"Created test database {database_name}")
PY
