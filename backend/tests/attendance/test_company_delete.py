"""A company referenced only by attendance data returns a clear 409."""

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from tests.utils.attendance_factories import create_shift
from tests.utils.factories import create_company


def test_company_referenced_only_by_attendance_returns_a_clear_409(
    db: Session, client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    company = create_company(db)
    create_shift(db, company_id=company.id)

    response = client.delete(
        f"{settings.API_V1_STR}/companies/{company.id}",
        headers=superuser_token_headers,
    )

    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert detail["code"] == "referenced"
    assert detail["message"] == "无法删除：公司仍被考勤数据引用"
    assert "0 个" not in detail["message"]
