from sqlalchemy.engine import make_url


def ensure_test_database(database_url: str | None) -> str:
    if not database_url:
        raise ValueError(
            "TEST_DATABASE_URL is not set. Set it to a dedicated test database "
            "whose name ends with '_test'."
        )

    name = make_url(database_url).database
    if not name:
        raise ValueError(
            f"The database URL {database_url!r} does not include a database name"
        )
    if not name.endswith("_test"):
        raise ValueError(
            f"Refusing to run tests against database {name!r}: "
            "the database name must end with '_test'."
        )
    return database_url
