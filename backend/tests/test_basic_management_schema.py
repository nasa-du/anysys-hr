"""Schema contract for the Basic Management persistence foundation.

These tests reflect the migrated PostgreSQL database. The migrations are the
deliverable, so the assertions are written from the approved specification in
``docs/specs/basic-management.md`` rather than from the SQLModel metadata.
"""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.core.db import engine
from tests.utils.utils import random_upper_code

TABLES = ("company", "department", "position", "cost_center", "employee")


@pytest.fixture(scope="module")
def inspector() -> sa.Inspector:
    return sa.inspect(engine)


def _uuid_type(value: sa.types.TypeEngine[Any]) -> bool:
    return isinstance(value, sa.Uuid) and value.as_uuid


def _varchar(length: int):
    def check(value: sa.types.TypeEngine[Any]) -> bool:
        return isinstance(value, sa.String) and value.length == length

    return check


def _numeric(precision: int, scale: int):
    def check(value: sa.types.TypeEngine[Any]) -> bool:
        return (
            isinstance(value, sa.Numeric)
            and value.precision == precision
            and value.scale == scale
        )

    return check


def _timestamp_type(value: sa.types.TypeEngine[Any]) -> bool:
    return isinstance(value, sa.DateTime) and value.timezone is True


def _date_type(value: sa.types.TypeEngine[Any]) -> bool:
    return isinstance(value, sa.Date) and not isinstance(value, sa.DateTime)


def _integer_type(value: sa.types.TypeEngine[Any]) -> bool:
    return isinstance(value, sa.Integer)


def _boolean_type(value: sa.types.TypeEngine[Any]) -> bool:
    return isinstance(value, sa.Boolean)


def _varchar_column(length: int, nullable: bool = False) -> tuple[Any, bool]:
    return (_varchar(length), nullable)


def _timestamp_column() -> tuple[Any, bool]:
    return (_timestamp_type, False)


UUID_COLUMN = (_uuid_type, False)

COLUMNS: dict[str, dict[str, tuple[Any, bool]]] = {
    "company": {
        "id": UUID_COLUMN,
        "company_code": _varchar_column(32),
        "company_name": _varchar_column(100),
        "is_active": (_boolean_type, False),
        "note": _varchar_column(500, nullable=True),
        "created_at": _timestamp_column(),
        "updated_at": _timestamp_column(),
    },
    "department": {
        "id": UUID_COLUMN,
        "dept_code": _varchar_column(32),
        "dept_name": _varchar_column(100),
        "company_id": UUID_COLUMN,
        "parent_id": (_uuid_type, True),
        "manager_id": (_uuid_type, True),
        "order_no": (_integer_type, False),
        "is_active": (_boolean_type, False),
        "note": _varchar_column(500, nullable=True),
        "created_at": _timestamp_column(),
        "updated_at": _timestamp_column(),
    },
    "position": {
        "id": UUID_COLUMN,
        "position_code": _varchar_column(32),
        "position_name": _varchar_column(100),
        "company_id": UUID_COLUMN,
        "dept_id": (_uuid_type, True),
        "order_no": (_integer_type, False),
        "is_active": (_boolean_type, False),
        "note": _varchar_column(500, nullable=True),
        "created_at": _timestamp_column(),
        "updated_at": _timestamp_column(),
    },
    "cost_center": {
        "id": UUID_COLUMN,
        "cost_org_code": _varchar_column(32),
        "cost_org_name": _varchar_column(100),
        "company_id": UUID_COLUMN,
        "parent_id": (_uuid_type, True),
        "manager_id": (_uuid_type, True),
        "budget": (_numeric(14, 2), False),
        "warn_pct": (_integer_type, False),
        "order_no": (_integer_type, False),
        "is_active": (_boolean_type, False),
        "note": _varchar_column(500, nullable=True),
        "created_at": _timestamp_column(),
        "updated_at": _timestamp_column(),
    },
    "employee": {
        "id": UUID_COLUMN,
        "employee_no": _varchar_column(32),
        "name": _varchar_column(100),
        "gender": _varchar_column(7, nullable=True),
        "dept_id": UUID_COLUMN,
        "position_id": UUID_COLUMN,
        "cost_org_id": (_uuid_type, True),
        "manager_id": (_uuid_type, True),
        "status": _varchar_column(9),
        "hire_date": (_date_type, False),
        "resign_date": (_date_type, True),
        "contract_type": _varchar_column(9),
        "daily_hours": (_numeric(4, 2), True),
        "monthly_rest": (_integer_type, True),
        "confidentiality_level": (_integer_type, True),
        "note": _varchar_column(500, nullable=True),
        "created_at": _timestamp_column(),
        "updated_at": _timestamp_column(),
    },
}

UNIQUE_CONSTRAINTS: dict[str, set[tuple[str, tuple[str, ...]]]] = {
    "company": {("uq_company_company_code", ("company_code",))},
    "department": {
        ("uq_department_company_dept_code", ("company_id", "dept_code")),
    },
    "position": {
        ("uq_position_company_position_code", ("company_id", "position_code")),
    },
    "cost_center": {
        (
            "uq_cost_center_company_cost_org_code",
            ("company_id", "cost_org_code"),
        ),
    },
    "employee": {("uq_employee_employee_no", ("employee_no",))},
}

INDEXES: dict[str, set[tuple[str, tuple[str, ...]]]] = {
    "company": set(),
    "department": {
        ("ix_department_company_id", ("company_id",)),
        ("ix_department_parent_id", ("parent_id",)),
        ("ix_department_manager_id", ("manager_id",)),
    },
    "position": {
        ("ix_position_company_id", ("company_id",)),
        ("ix_position_dept_id", ("dept_id",)),
    },
    "cost_center": {
        ("ix_cost_center_company_id", ("company_id",)),
        ("ix_cost_center_parent_id", ("parent_id",)),
        ("ix_cost_center_manager_id", ("manager_id",)),
    },
    "employee": {
        ("ix_employee_dept_id", ("dept_id",)),
        ("ix_employee_position_id", ("position_id",)),
        ("ix_employee_cost_org_id", ("cost_org_id",)),
        ("ix_employee_manager_id", ("manager_id",)),
        ("ix_employee_status", ("status",)),
    },
}

CHECK_CONSTRAINTS: dict[str, set[str]] = {
    "company": set(),
    "department": set(),
    "position": set(),
    "cost_center": {
        "ck_cost_center_budget_non_negative",
        "ck_cost_center_warn_pct_range",
    },
    "employee": {
        "ck_employee_daily_hours_range",
        "ck_employee_monthly_rest_non_negative",
        "ck_employee_confidentiality_level_range",
        "ck_employee_resign_date_after_hire",
        "ck_employee_resigned_date_required",
        "ck_employee_gender",
        "ck_employee_status",
        "ck_employee_contract_type",
    },
}

FOREIGN_KEYS: dict[str, set[tuple[str, str, str, str | None]]] = {
    "company": set(),
    "department": {
        (
            "fk_department_company_id_company",
            "company_id",
            "company",
            "RESTRICT",
        ),
        (
            "fk_department_parent_id_department",
            "parent_id",
            "department",
            "RESTRICT",
        ),
        (
            "fk_department_manager_id_employee",
            "manager_id",
            "employee",
            "SET NULL",
        ),
    },
    "position": {
        ("fk_position_company_id_company", "company_id", "company", "RESTRICT"),
        ("fk_position_dept_id_department", "dept_id", "department", "SET NULL"),
    },
    "cost_center": {
        (
            "fk_cost_center_company_id_company",
            "company_id",
            "company",
            "RESTRICT",
        ),
        (
            "fk_cost_center_parent_id_cost_center",
            "parent_id",
            "cost_center",
            "RESTRICT",
        ),
        (
            "fk_cost_center_manager_id_employee",
            "manager_id",
            "employee",
            "SET NULL",
        ),
    },
    "employee": {
        ("fk_employee_dept_id_department", "dept_id", "department", "RESTRICT"),
        (
            "fk_employee_position_id_position",
            "position_id",
            "position",
            "RESTRICT",
        ),
        (
            "fk_employee_cost_org_id_cost_center",
            "cost_org_id",
            "cost_center",
            "RESTRICT",
        ),
        (
            "fk_employee_manager_id_employee",
            "manager_id",
            "employee",
            "SET NULL",
        ),
    },
}


@pytest.mark.parametrize("table_name", TABLES)
def test_table_has_the_contract_columns(
    inspector: sa.Inspector, table_name: str
) -> None:
    columns = {column["name"]: column for column in inspector.get_columns(table_name)}
    expected = COLUMNS[table_name]

    assert set(columns) == set(expected)
    for name, (type_check, nullable) in expected.items():
        column = columns[name]
        assert type_check(column["type"]), (
            f"{table_name}.{name} has type {column['type']!r}"
        )
        assert column["nullable"] is nullable, (
            f"{table_name}.{name} nullable is {column['nullable']}, expected {nullable}"
        )


@pytest.mark.parametrize("table_name", TABLES)
def test_table_primary_key_is_id(inspector: sa.Inspector, table_name: str) -> None:
    primary_key = inspector.get_pk_constraint(table_name)

    assert primary_key["constrained_columns"] == ["id"]


@pytest.mark.parametrize("table_name", TABLES)
def test_table_has_the_contract_unique_constraints(
    inspector: sa.Inspector, table_name: str
) -> None:
    unique_constraints = {
        (constraint["name"], tuple(constraint["column_names"]))
        for constraint in inspector.get_unique_constraints(table_name)
    }

    assert unique_constraints == UNIQUE_CONSTRAINTS[table_name]


@pytest.mark.parametrize("table_name", TABLES)
def test_table_has_the_contract_indexes(
    inspector: sa.Inspector, table_name: str
) -> None:
    # PostgreSQL reports the indexes backing unique constraints here too;
    # those constraints are asserted by the unique-constraint test.
    indexes = {
        (index["name"], tuple(index["column_names"]))
        for index in inspector.get_indexes(table_name)
        if index.get("duplicates_constraint") is None
    }

    assert indexes == INDEXES[table_name]


@pytest.mark.parametrize("table_name", TABLES)
def test_table_has_the_contract_check_constraints(
    inspector: sa.Inspector, table_name: str
) -> None:
    check_constraints = {
        constraint["name"] for constraint in inspector.get_check_constraints(table_name)
    }

    assert check_constraints == CHECK_CONSTRAINTS[table_name]


def test_item_table_is_dropped(inspector: sa.Inspector) -> None:
    assert "item" not in inspector.get_table_names()


@pytest.mark.parametrize("table_name", TABLES)
def test_table_has_the_contract_foreign_keys(
    inspector: sa.Inspector, table_name: str
) -> None:
    foreign_keys = {
        (
            foreign_key["name"],
            foreign_key["constrained_columns"][0],
            foreign_key["referred_table"],
            foreign_key["options"].get("ondelete"),
        )
        for foreign_key in inspector.get_foreign_keys(table_name)
    }

    assert foreign_keys == FOREIGN_KEYS[table_name]


@pytest.fixture(scope="module")
def tables() -> dict[str, sa.Table]:
    metadata = sa.MetaData()
    return {name: sa.Table(name, metadata, autoload_with=engine) for name in TABLES}


def _base_row() -> dict[str, Any]:
    now = datetime.now(UTC)
    return {"id": uuid.uuid7(), "created_at": now, "updated_at": now}


def _company_row(**overrides: Any) -> dict[str, Any]:
    return {
        **_base_row(),
        "company_code": random_upper_code("C"),
        "company_name": "荣新建设",
        "is_active": True,
        "note": None,
        **overrides,
    }


def _department_row(company_id: uuid.UUID, **overrides: Any) -> dict[str, Any]:
    return {
        **_base_row(),
        "dept_code": random_upper_code("D"),
        "dept_name": "生产部",
        "company_id": company_id,
        "parent_id": None,
        "manager_id": None,
        "order_no": 0,
        "is_active": True,
        "note": None,
        **overrides,
    }


def _position_row(company_id: uuid.UUID, **overrides: Any) -> dict[str, Any]:
    return {
        **_base_row(),
        "position_code": random_upper_code("P"),
        "position_name": "项目经理",
        "company_id": company_id,
        "dept_id": None,
        "order_no": 0,
        "is_active": True,
        "note": None,
        **overrides,
    }


def _cost_center_row(company_id: uuid.UUID, **overrides: Any) -> dict[str, Any]:
    return {
        **_base_row(),
        "cost_org_code": random_upper_code("K"),
        "cost_org_name": "生产成本中心",
        "company_id": company_id,
        "parent_id": None,
        "manager_id": None,
        "budget": Decimal("0"),
        "warn_pct": 85,
        "order_no": 0,
        "is_active": True,
        "note": None,
        **overrides,
    }


def _employee_row(
    dept_id: uuid.UUID, position_id: uuid.UUID, **overrides: Any
) -> dict[str, Any]:
    return {
        **_base_row(),
        "employee_no": random_upper_code("E"),
        "name": "张三",
        "gender": None,
        "dept_id": dept_id,
        "position_id": position_id,
        "cost_org_id": None,
        "manager_id": None,
        "status": "active",
        "hire_date": datetime(2026, 3, 1, tzinfo=UTC).date(),
        "resign_date": None,
        "contract_type": "full_time",
        "daily_hours": None,
        "monthly_rest": None,
        "confidentiality_level": None,
        "note": None,
        **overrides,
    }


def _insert(
    db: Session, tables: dict[str, sa.Table], table_name: str, row: dict[str, Any]
) -> uuid.UUID:
    db.execute(sa.insert(tables[table_name]).values(**row))
    db.commit()
    return row["id"]


def _insert_company(
    db: Session, tables: dict[str, sa.Table], **overrides: Any
) -> uuid.UUID:
    return _insert(db, tables, "company", _company_row(**overrides))


def _insert_department(
    db: Session, tables: dict[str, sa.Table], company_id: uuid.UUID, **overrides: Any
) -> uuid.UUID:
    return _insert(db, tables, "department", _department_row(company_id, **overrides))


def _insert_position(
    db: Session, tables: dict[str, sa.Table], company_id: uuid.UUID, **overrides: Any
) -> uuid.UUID:
    return _insert(db, tables, "position", _position_row(company_id, **overrides))


def _insert_cost_center(
    db: Session, tables: dict[str, sa.Table], company_id: uuid.UUID, **overrides: Any
) -> uuid.UUID:
    return _insert(db, tables, "cost_center", _cost_center_row(company_id, **overrides))


def _insert_employee(
    db: Session,
    tables: dict[str, sa.Table],
    dept_id: uuid.UUID,
    position_id: uuid.UUID,
    **overrides: Any,
) -> uuid.UUID:
    return _insert(
        db,
        tables,
        "employee",
        _employee_row(dept_id, position_id, **overrides),
    )


@contextmanager
def _integrity_error(db: Session) -> Iterator[None]:
    try:
        with pytest.raises(IntegrityError):
            yield
    finally:
        db.rollback()


def _scalar(db: Session, table: sa.Table, column: str, row_id: uuid.UUID) -> Any:
    return db.execute(
        sa.select(table.c[column]).where(table.c.id == row_id)
    ).scalar_one()


def test_company_codes_are_globally_unique(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    code = random_upper_code("C")
    _insert_company(db, tables, company_code=code)

    with _integrity_error(db):
        _insert_company(db, tables, company_code=code)


def test_department_codes_are_unique_within_a_company(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    first_company = _insert_company(db, tables)
    second_company = _insert_company(db, tables)
    code = random_upper_code("D")
    _insert_department(db, tables, first_company, dept_code=code)
    _insert_department(db, tables, second_company, dept_code=code)

    with _integrity_error(db):
        _insert_department(db, tables, first_company, dept_code=code)


def test_position_codes_are_unique_within_a_company(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    first_company = _insert_company(db, tables)
    second_company = _insert_company(db, tables)
    code = random_upper_code("P")
    _insert_position(db, tables, first_company, position_code=code)
    _insert_position(db, tables, second_company, position_code=code)

    with _integrity_error(db):
        _insert_position(db, tables, first_company, position_code=code)


def test_cost_center_codes_are_unique_within_a_company(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    first_company = _insert_company(db, tables)
    second_company = _insert_company(db, tables)
    code = random_upper_code("K")
    _insert_cost_center(db, tables, first_company, cost_org_code=code)
    _insert_cost_center(db, tables, second_company, cost_org_code=code)

    with _integrity_error(db):
        _insert_cost_center(db, tables, first_company, cost_org_code=code)


def test_employee_numbers_are_globally_unique(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    first_company = _insert_company(db, tables)
    second_company = _insert_company(db, tables)
    first_dept = _insert_department(db, tables, first_company)
    first_position = _insert_position(db, tables, first_company)
    second_dept = _insert_department(db, tables, second_company)
    second_position = _insert_position(db, tables, second_company)
    employee_no = random_upper_code("E")
    _insert_employee(db, tables, first_dept, first_position, employee_no=employee_no)

    with _integrity_error(db):
        _insert_employee(
            db, tables, second_dept, second_position, employee_no=employee_no
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"budget": Decimal("-0.01")},
        {"warn_pct": 0},
        {"warn_pct": 101},
    ],
)
def test_cost_center_check_constraints_reject_invalid_values(
    db: Session, tables: dict[str, sa.Table], overrides: dict[str, Any]
) -> None:
    company = _insert_company(db, tables)

    with _integrity_error(db):
        _insert_cost_center(db, tables, company, **overrides)


@pytest.mark.parametrize(
    "overrides",
    [
        {"daily_hours": Decimal("0")},
        {"daily_hours": Decimal("24.01")},
        {"monthly_rest": -1},
        {"confidentiality_level": 0},
        {"confidentiality_level": 6},
        {
            "status": "resigned",
            "resign_date": datetime(2026, 2, 28, tzinfo=UTC).date(),
        },
        {"status": "resigned", "resign_date": None},
        {"status": "active", "resign_date": datetime(2026, 3, 2).date()},
        {"gender": "other"},
        {"status": "retired"},
        {"contract_type": "contract"},
    ],
)
def test_employee_check_constraints_reject_invalid_values(
    db: Session, tables: dict[str, sa.Table], overrides: dict[str, Any]
) -> None:
    company = _insert_company(db, tables)
    dept = _insert_department(db, tables, company)
    position = _insert_position(db, tables, company)

    with _integrity_error(db):
        _insert_employee(db, tables, dept, position, **overrides)


def test_cost_center_boundary_values_are_accepted(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    company = _insert_company(db, tables)

    _insert_cost_center(db, tables, company, budget=Decimal("0"), warn_pct=1)
    _insert_cost_center(
        db, tables, company, budget=Decimal("999999999999.99"), warn_pct=100
    )


def test_employee_boundary_values_are_accepted(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    company = _insert_company(db, tables)
    dept = _insert_department(db, tables, company)
    position = _insert_position(db, tables, company)
    hire_date = datetime(2026, 3, 1, tzinfo=UTC).date()

    _insert_employee(
        db,
        tables,
        dept,
        position,
        daily_hours=Decimal("0.01"),
        monthly_rest=0,
        confidentiality_level=1,
    )
    _insert_employee(
        db,
        tables,
        dept,
        position,
        daily_hours=Decimal("24.00"),
        confidentiality_level=5,
        status="resigned",
        resign_date=hire_date,
    )


def test_restrict_foreign_keys_block_deleting_an_owned_company(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    company = _insert_company(db, tables)
    _insert_department(db, tables, company)

    with _integrity_error(db):
        db.execute(
            sa.delete(tables["company"]).where(tables["company"].c.id == company)
        )
        db.commit()


def test_restrict_foreign_keys_block_deleting_a_company_with_positions(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    company = _insert_company(db, tables)
    _insert_position(db, tables, company)

    with _integrity_error(db):
        db.execute(
            sa.delete(tables["company"]).where(tables["company"].c.id == company)
        )
        db.commit()


def test_restrict_foreign_keys_block_deleting_a_company_with_cost_centers(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    company = _insert_company(db, tables)
    _insert_cost_center(db, tables, company)

    with _integrity_error(db):
        db.execute(
            sa.delete(tables["company"]).where(tables["company"].c.id == company)
        )
        db.commit()


def test_restrict_foreign_keys_block_deleting_a_department_with_children(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    company = _insert_company(db, tables)
    parent = _insert_department(db, tables, company)
    _insert_department(db, tables, company, parent_id=parent)

    with _integrity_error(db):
        db.execute(
            sa.delete(tables["department"]).where(tables["department"].c.id == parent)
        )
        db.commit()


def test_restrict_foreign_keys_block_deleting_a_department_with_employees(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    company = _insert_company(db, tables)
    dept = _insert_department(db, tables, company)
    position = _insert_position(db, tables, company)
    _insert_employee(db, tables, dept, position)

    with _integrity_error(db):
        db.execute(
            sa.delete(tables["department"]).where(tables["department"].c.id == dept)
        )
        db.commit()


def test_restrict_foreign_keys_block_deleting_a_position_with_employees(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    company = _insert_company(db, tables)
    dept = _insert_department(db, tables, company)
    position = _insert_position(db, tables, company)
    _insert_employee(db, tables, dept, position)

    with _integrity_error(db):
        db.execute(
            sa.delete(tables["position"]).where(tables["position"].c.id == position)
        )
        db.commit()


def test_restrict_foreign_keys_block_deleting_a_cost_center_with_children(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    company = _insert_company(db, tables)
    parent = _insert_cost_center(db, tables, company)
    _insert_cost_center(db, tables, company, parent_id=parent)

    with _integrity_error(db):
        db.execute(
            sa.delete(tables["cost_center"]).where(tables["cost_center"].c.id == parent)
        )
        db.commit()


def test_restrict_foreign_keys_block_deleting_a_cost_center_with_employees(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    company = _insert_company(db, tables)
    dept = _insert_department(db, tables, company)
    position = _insert_position(db, tables, company)
    cost_center = _insert_cost_center(db, tables, company)
    _insert_employee(db, tables, dept, position, cost_org_id=cost_center)

    with _integrity_error(db):
        db.execute(
            sa.delete(tables["cost_center"]).where(
                tables["cost_center"].c.id == cost_center
            )
        )
        db.commit()


def test_deleting_a_department_clears_the_position_default_department(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    company = _insert_company(db, tables)
    dept = _insert_department(db, tables, company)
    position = _insert_position(db, tables, company, dept_id=dept)

    db.execute(sa.delete(tables["department"]).where(tables["department"].c.id == dept))
    db.commit()

    assert _scalar(db, tables["position"], "dept_id", position) is None


def test_deleting_an_employee_clears_manager_references(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    company = _insert_company(db, tables)
    dept = _insert_department(db, tables, company)
    position = _insert_position(db, tables, company)
    cost_center = _insert_cost_center(db, tables, company)
    manager = _insert_employee(db, tables, dept, position)
    report = _insert_employee(db, tables, dept, position, manager_id=manager)
    db.execute(
        sa.update(tables["department"])
        .where(tables["department"].c.id == dept)
        .values(manager_id=manager)
    )
    db.execute(
        sa.update(tables["cost_center"])
        .where(tables["cost_center"].c.id == cost_center)
        .values(manager_id=manager)
    )
    db.commit()

    db.execute(sa.delete(tables["employee"]).where(tables["employee"].c.id == manager))
    db.commit()

    assert _scalar(db, tables["department"], "manager_id", dept) is None
    assert _scalar(db, tables["cost_center"], "manager_id", cost_center) is None
    assert _scalar(db, tables["employee"], "manager_id", report) is None
