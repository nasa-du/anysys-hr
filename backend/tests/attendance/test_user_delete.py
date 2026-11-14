"""Attendance audit RESTRICT references must surface as a Chinese 409."""

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import User
from tests.utils.attendance_factories import (
    create_attendance_month,
    create_calc_run,
    create_month_snapshot,
)
from tests.utils.factories import create_company
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import random_email


def _referenced_user(db: Session, client: TestClient) -> tuple[User, dict[str, str]]:
    email = random_email()
    headers = authentication_token_from_email(client=client, email=email, db=db)
    user = db.exec(select(User).where(User.email == email)).one()

    company = create_company(db)
    month = create_attendance_month(db, company_id=company.id)
    calc_run = create_calc_run(db, attendance_month_id=month.id)
    create_month_snapshot(
        db,
        attendance_month_id=month.id,
        calc_run_id=calc_run.id,
        locked_by=user.id,
    )
    return user, headers


def test_deleting_a_user_referenced_by_attendance_returns_409(
    db: Session, client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    user, _headers = _referenced_user(db, client)

    response = client.delete(
        f"{settings.API_V1_STR}/users/{user.id}",
        headers=superuser_token_headers,
    )

    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert detail["code"] == "referenced"
    assert detail["message"] == "该用户已被考勤记录引用，无法删除"
    assert db.get(User, user.id) is not None


def test_deleting_my_account_when_referenced_returns_409(
    db: Session, client: TestClient
) -> None:
    user, headers = _referenced_user(db, client)

    response = client.delete(
        f"{settings.API_V1_STR}/users/me",
        headers=headers,
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == "referenced"
    assert db.get(User, user.id) is not None
