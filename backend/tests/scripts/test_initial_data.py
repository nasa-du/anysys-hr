from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine
from app.initial_data import main
from app.models import User


def test_initial_data_creates_the_superuser() -> None:
    main()

    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.email == settings.FIRST_SUPERUSER)
        ).first()

    assert user is not None
    assert user.is_superuser is True
