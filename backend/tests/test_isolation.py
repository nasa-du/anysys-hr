"""Per-test isolation: each test starts with empty organizations and only the
first superuser in the user table.

The phases are intentionally ordered: each phase observes what the cleanup
fixture did to the state left by the phase before it.
"""

from sqlmodel import Session, select

from app.core.config import settings
from app.models import Company, User
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
