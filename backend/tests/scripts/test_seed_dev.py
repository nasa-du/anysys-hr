"""Development seed script: guard and idempotency."""

import pytest
from sqlmodel import Session, select

from app import seed_dev
from app.core.db import engine
from app.models import Company

SEEDED_CODES = ["C1", "C2", "C3"]
SEEDED_NAMES = ["荣新建设", "荣新科技", "荣新物流"]


def _companies() -> list[Company]:
    with Session(engine) as session:
        return list(session.exec(select(Company).order_by(Company.company_code)).all())


@pytest.mark.parametrize("environment", ["production", None])
def test_seed_refuses_outside_development(
    monkeypatch: pytest.MonkeyPatch, environment: str | None
) -> None:
    monkeypatch.setattr(seed_dev.settings, "FASTAPI_ENV", environment)

    with pytest.raises(SystemExit, match="development"):
        seed_dev.main()

    assert _companies() == []


def test_seed_inserts_three_companies_once() -> None:
    seed_dev.main()
    seed_dev.main()

    companies = _companies()
    assert [company.company_code for company in companies] == SEEDED_CODES
    assert [company.company_name for company in companies] == SEEDED_NAMES
    assert all(company.is_active for company in companies)


def test_seed_does_not_overwrite_existing_edits() -> None:
    seed_dev.main()

    with Session(engine) as session:
        company = session.exec(
            select(Company).where(Company.company_code == "C1")
        ).one()
        company.company_name = "用户修改后的名称"
        company.note = "用户备注"
        session.add(company)
        session.commit()

    seed_dev.main()

    with Session(engine) as session:
        company = session.exec(
            select(Company).where(Company.company_code == "C1")
        ).one()
        assert company.company_name == "用户修改后的名称"
        assert company.note == "用户备注"
