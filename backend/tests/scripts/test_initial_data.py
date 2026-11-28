from decimal import Decimal

from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine
from app.initial_data import main
from app.models import PayrollGlobalParam, SalaryFieldDef, User
from tests.utils.payroll_tables import truncate_payroll_system_tables


def test_initial_data_creates_the_superuser() -> None:
    main()

    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.email == settings.FIRST_SUPERUSER)
        ).first()

    assert user is not None
    assert user.is_superuser is True


def test_initial_data_seeds_payroll_defaults_idempotently(db: Session) -> None:
    truncate_payroll_system_tables(db)
    db.commit()

    main()

    field = db.exec(
        select(SalaryFieldDef).where(SalaryFieldDef.field_key == "base_pay")
    ).one()
    field.label = "自定义基本工资"
    param = db.exec(
        select(PayrollGlobalParam).where(PayrollGlobalParam.key == "tax_threshold")
    ).one()
    param.numeric_value = Decimal("6000")
    db.add(field)
    db.add(param)
    db.commit()

    main()

    with Session(engine) as session:
        assert len(session.exec(select(SalaryFieldDef)).all()) == 32
        assert len(session.exec(select(PayrollGlobalParam)).all()) == 6
    db.refresh(field)
    db.refresh(param)
    assert field.label == "自定义基本工资"
    assert param.numeric_value == Decimal("6000")
