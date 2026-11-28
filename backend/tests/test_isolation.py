"""Per-test isolation: each test starts with empty organizations, only the
first superuser in the user table, and the seeded system payroll defaults.

The phases are intentionally ordered: each phase observes what the cleanup
fixture did to the state left by the phase before it.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlmodel import Session, select

from app.core.config import settings
from app.enums import PayrollConfigEntityType, PayrollGlobalParamType
from app.models import (
    Company,
    PayrollConfigRevision,
    PayrollGlobalParam,
    PayrollMonth,
    SalaryFieldDef,
    User,
)
from tests.utils.factories import create_company
from tests.utils.user import create_random_user


def test_isolation_phase_one_creates_organization_data(db: Session) -> None:
    create_company(db)

    assert db.exec(select(Company)).first() is not None


def test_isolation_phase_two_starts_with_an_empty_organization(
    db: Session,
) -> None:
    assert db.exec(select(Company)).all() == []


def test_isolation_phase_three_creates_a_non_superuser(db: Session) -> None:
    create_random_user(db)

    assert (
        db.exec(select(User).where(User.email != settings.FIRST_SUPERUSER)).all() != []
    )


def test_isolation_phase_four_keeps_only_the_superuser(db: Session) -> None:
    users = db.exec(select(User)).all()

    assert [user.email for user in users] == [settings.FIRST_SUPERUSER]


def test_isolation_phase_five_starts_with_the_system_defaults(db: Session) -> None:
    fields = db.exec(select(SalaryFieldDef)).all()
    params = db.exec(select(PayrollGlobalParam)).all()

    assert len(fields) == 32
    assert len(params) == 6
    assert db.exec(select(PayrollConfigRevision)).all() == []


def test_isolation_phase_six_mutates_defaults_and_creates_company_data(
    db: Session,
) -> None:
    field = db.exec(
        select(SalaryFieldDef).where(SalaryFieldDef.field_key == "base_pay")
    ).one()
    field.label = "已修改的工资字段"
    param = db.exec(
        select(PayrollGlobalParam).where(PayrollGlobalParam.key == "tax_threshold")
    ).one()
    param.numeric_value = Decimal("1")
    db.add(field)
    db.add(param)
    db.add(
        PayrollGlobalParam(
            key="custom_param",
            label="自定义参数",
            category="tax",
            value_type=PayrollGlobalParamType.NUMBER,
            numeric_value=Decimal("1"),
        )
    )
    db.add(
        PayrollConfigRevision(
            entity_type=PayrollConfigEntityType.PAYROLL_GLOBAL_PARAM,
            entity_id=param.id,
            version_no=1,
            snapshot={},
            changed_at=datetime.now(UTC),
        )
    )
    company = create_company(db)
    db.add(PayrollMonth(company_id=company.id, month=date(2026, 9, 1)))
    db.commit()


def test_isolation_phase_seven_restores_defaults_and_clears_company_data(
    db: Session,
) -> None:
    fields = db.exec(select(SalaryFieldDef)).all()
    params = db.exec(select(PayrollGlobalParam)).all()

    assert len(fields) == 32
    assert len(params) == 6
    assert db.exec(select(Company)).all() == []
    assert db.exec(select(PayrollMonth)).all() == []
    assert db.exec(select(PayrollConfigRevision)).all() == []
    base_pay = next(field for field in fields if field.field_key == "base_pay")
    assert base_pay.label == "基本工资(实)"
    assert base_pay.default_formula == (
        "ROUND(base_salary / weekday_full * weekday_attended, 2)"
    )
    tax_threshold = next(param for param in params if param.key == "tax_threshold")
    assert tax_threshold.numeric_value == Decimal("5000")
    assert {param.key for param in params} == {
        "tax_threshold",
        "tax_rate",
        "social_rate",
        "confidentiality_tier",
        "hightemp_tier",
        "tax_brackets",
    }
