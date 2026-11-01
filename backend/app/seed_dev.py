"""Development-only seed data.

Run manually from the backend directory with ``uv run python -m app.seed_dev``.
The script refuses to run unless ``FASTAPI_ENV=development`` and only inserts
rows that are missing by business code, so user edits are never overwritten.
"""

import logging
from typing import Any

from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine
from app.models import Company

logger = logging.getLogger(__name__)

COMPANIES: list[dict[str, Any]] = [
    {"company_code": "C1", "company_name": "荣新建设", "note": "完整组织示例"},
    {"company_code": "C2", "company_name": "荣新科技", "note": "小型组织示例"},
    {"company_code": "C3", "company_name": "荣新物流", "note": "空公司示例"},
]


def seed(session: Session) -> None:
    for data in COMPANIES:
        existing = session.exec(
            select(Company).where(Company.company_code == data["company_code"])
        ).first()
        if existing is None:
            session.add(Company(**data))
    session.commit()


def main() -> None:
    if settings.FASTAPI_ENV != "development":
        raise SystemExit("Refusing to seed: FASTAPI_ENV must be 'development'.")
    with Session(engine) as session:
        seed(session)
    logger.info("Development seed data is up to date")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
