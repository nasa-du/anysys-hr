"""Position API contract tests.

Seam: the HTTP API under ``/api/v1/positions``. The tests assert the approved
contract from ``docs/specs/basic-management.md``: request/response shapes,
company-scoped codes, default-department rules, blockers, filters, and the
inactive rules. Employee factories stand in for the Employee slice.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.enums import EmployeeStatus
from app.models import Position
from tests.utils.factories import (
    create_company,
    create_department,
    create_employee,
    create_position,
)
from tests.utils.utils import random_upper_code

POSITIONS_URL = f"{settings.API_V1_STR}/positions/"


def position_url(position_id: uuid.UUID | str) -> str:
    return f"{POSITIONS_URL}{position_id}"


def _create_position(
    client: TestClient,
    headers: dict[str, str],
    company_id: uuid.UUID | str,
    *,
    position_code: str | None = None,
    position_name: str = "项目经理",
    dept_id: uuid.UUID | str | None = None,
    order_no: int = 0,
    is_active: bool = True,
    note: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "position_code": position_code or random_upper_code("P"),
        "position_name": position_name,
        "company_id": str(company_id),
        "dept_id": str(dept_id) if dept_id else None,
        "order_no": order_no,
        "is_active": is_active,
        "note": note,
    }
    response = client.post(POSITIONS_URL, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def session_position(db: Session, position_id: uuid.UUID | str) -> Position:
    position = db.get(Position, uuid.UUID(str(position_id)))
    assert position is not None
    return position


def _error(response: Any) -> dict[str, Any]:
    body = response.json()
    assert isinstance(body["detail"], dict), body
    return body["detail"]


def test_position_endpoints_require_authentication(client: TestClient) -> None:
    company_id = uuid.uuid7()
    for method, url, kwargs in (
        ("get", POSITIONS_URL, {"params": {"company_id": str(company_id)}}),
        ("post", POSITIONS_URL, {"json": {}}),
        ("get", position_url(uuid.uuid7()), {}),
        ("patch", position_url(uuid.uuid7()), {"json": {}}),
        ("delete", position_url(uuid.uuid7()), {}),
    ):
        response = getattr(client, method)(url, **kwargs)
        assert response.status_code == 401, (method, response.text)
        assert response.json() == {"detail": "未登录或登录状态已过期"}


def test_any_logged_in_user_can_list_positions(
    client: TestClient,
    db: Session,
    normal_user_token_headers: dict[str, str],
) -> None:
    company = create_company(db)

    response = client.get(
        POSITIONS_URL,
        headers=normal_user_token_headers,
        params={"company_id": str(company.id)},
    )

    assert response.status_code == 200
    assert response.json() == {"data": [], "count": 0}


def test_create_position_normalizes_the_code_and_returns_public_fields(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db, company_name="荣新建设")
    department = create_department(db, company=company, dept_name="生产部")

    response = client.post(
        POSITIONS_URL,
        headers=superuser_token_headers,
        json={
            "position_code": "  p-1  ",
            "position_name": "项目经理",
            "company_id": str(company.id),
            "dept_id": str(department.id),
            "note": "",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["position_code"] == "P-1"
    assert body["position_name"] == "项目经理"
    assert body["company_id"] == str(company.id)
    assert body["company_name"] == "荣新建设"
    assert body["dept_id"] == str(department.id)
    assert body["dept_name"] == "生产部"
    assert body["order_no"] == 0
    assert body["is_active"] is True
    assert body["note"] is None
    assert uuid.UUID(body["id"]).version == 7
    created_at = datetime.fromisoformat(body["created_at"].replace("Z", "+00:00"))
    assert created_at.tzinfo is not None


def test_create_inactive_position_is_allowed(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)

    created = _create_position(
        client, superuser_token_headers, company.id, is_active=False
    )

    assert created["is_active"] is False


def test_get_position_returns_the_public_fields(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db, company_name="荣新建设")
    department = create_department(db, company=company, dept_name="生产部")
    created = _create_position(
        client,
        superuser_token_headers,
        company.id,
        position_name="项目经理",
        dept_id=department.id,
        order_no=2,
        note="备注",
    )

    response = client.get(
        position_url(created["id"]), headers=superuser_token_headers
    )

    assert response.status_code == 200, response.text
    assert response.json() == created


def test_create_position_without_a_default_department(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)

    created = _create_position(
        client, superuser_token_headers, company.id, dept_id=None
    )

    assert created["dept_id"] is None
    assert created["dept_name"] is None


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"position_name": "项目经理"}, "position_code"),
        ({"position_code": "VALID", "position_name": ""}, "position_name"),
        ({"position_code": "bad code", "position_name": "项目经理"}, "position_code"),
        ({"position_code": "P" * 33, "position_name": "项目经理"}, "position_code"),
        ({"position_code": "VALID", "position_name": "岗" * 101}, "position_name"),
        (
            {
                "position_code": "VALID",
                "position_name": "项目经理",
                "note": "备" * 501,
            },
            "note",
        ),
    ],
)
def test_create_position_returns_chinese_validation_errors(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    payload: dict[str, Any],
    field: str,
) -> None:
    company = create_company(db)

    response = client.post(
        POSITIONS_URL,
        headers=superuser_token_headers,
        json={"company_id": str(company.id), **payload},
    )

    assert response.status_code == 422, response.text
    errors = response.json()["detail"]
    matching = [error for error in errors if error["loc"] == ["body", field]]
    assert matching, errors
    message = matching[0]["msg"]
    assert any("一" <= char <= "鿿" for char in message), message


def test_position_codes_are_unique_within_a_company_only(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    first_company = create_company(db)
    second_company = create_company(db)
    _create_position(
        client, superuser_token_headers, first_company.id, position_code="P1"
    )

    duplicate = client.post(
        POSITIONS_URL,
        headers=superuser_token_headers,
        json={
            "position_code": "p1",
            "position_name": "另一个岗位",
            "company_id": str(first_company.id),
        },
    )
    other_company = client.post(
        POSITIONS_URL,
        headers=superuser_token_headers,
        json={
            "position_code": "P1",
            "position_name": "同名编码",
            "company_id": str(second_company.id),
        },
    )

    assert duplicate.status_code == 409, duplicate.text
    detail = _error(duplicate)
    assert detail["code"] == "duplicate_code"
    assert detail["message"] == "岗位编码已存在"
    assert detail["field_errors"] == {"position_code": "岗位编码已存在"}
    assert "blockers" not in detail
    assert other_company.status_code == 201, other_company.text


def test_create_position_rejects_a_missing_company(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.post(
        POSITIONS_URL,
        headers=superuser_token_headers,
        json={
            "position_code": "P1",
            "position_name": "项目经理",
            "company_id": str(uuid.uuid7()),
        },
    )

    assert response.status_code == 409, response.text
    detail = _error(response)
    assert detail["code"] == "invalid_reference"
    assert detail["field_errors"] == {"company_id": "公司不存在"}


def test_create_position_rejects_an_inactive_company(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db, is_active=False)

    response = client.post(
        POSITIONS_URL,
        headers=superuser_token_headers,
        json={
            "position_code": "P1",
            "position_name": "项目经理",
            "company_id": str(company.id),
        },
    )

    assert response.status_code == 409, response.text
    detail = _error(response)
    assert detail["code"] == "inactive_reference"
    assert detail["field_errors"] == {"company_id": "公司已停用，无法创建岗位"}


def test_create_position_rejects_a_missing_default_department(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)

    response = client.post(
        POSITIONS_URL,
        headers=superuser_token_headers,
        json={
            "position_code": "P1",
            "position_name": "项目经理",
            "company_id": str(company.id),
            "dept_id": str(uuid.uuid7()),
        },
    )

    assert response.status_code == 409, response.text
    detail = _error(response)
    assert detail["code"] == "invalid_reference"
    assert detail["field_errors"] == {"dept_id": "默认部门不存在"}


def test_create_position_rejects_a_cross_company_default_department(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    other_company = create_company(db)
    foreign_department = create_department(db, company=other_company)

    response = client.post(
        POSITIONS_URL,
        headers=superuser_token_headers,
        json={
            "position_code": "P1",
            "position_name": "项目经理",
            "company_id": str(company.id),
            "dept_id": str(foreign_department.id),
        },
    )

    assert response.status_code == 409, response.text
    detail = _error(response)
    assert detail["code"] == "cross_company"
    assert detail["field_errors"] == {"dept_id": "默认部门必须属于同一公司"}


def test_create_position_rejects_an_inactive_default_department(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    inactive_department = create_department(db, company=company, is_active=False)

    response = client.post(
        POSITIONS_URL,
        headers=superuser_token_headers,
        json={
            "position_code": "P1",
            "position_name": "项目经理",
            "company_id": str(company.id),
            "dept_id": str(inactive_department.id),
        },
    )

    assert response.status_code == 409, response.text
    detail = _error(response)
    assert detail["code"] == "inactive_reference"
    assert detail["field_errors"] == {"dept_id": "默认部门已停用"}


def test_update_position_changes_fields_and_refreshes_updated_at(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    department = create_department(db, company=company, dept_name="生产部")
    created = _create_position(
        client,
        superuser_token_headers,
        company.id,
        position_name="旧岗位",
        note="旧备注",
    )

    response = client.patch(
        position_url(created["id"]),
        headers=superuser_token_headers,
        json={
            "position_name": "新岗位",
            "dept_id": str(department.id),
            "order_no": 3,
            "note": None,
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["position_code"] == created["position_code"]
    assert body["position_name"] == "新岗位"
    assert body["dept_id"] == str(department.id)
    assert body["dept_name"] == "生产部"
    assert body["order_no"] == 3
    assert body["note"] is None
    assert body["created_at"] == created["created_at"]
    assert body["updated_at"] > created["updated_at"]


def test_update_position_can_clear_the_default_department(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    department = create_department(db, company=company)
    created = _create_position(
        client, superuser_token_headers, company.id, dept_id=department.id
    )

    response = client.patch(
        position_url(created["id"]),
        headers=superuser_token_headers,
        json={"dept_id": None},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["dept_id"] is None
    assert body["dept_name"] is None


@pytest.mark.parametrize("field", ["position_code", "company_id"])
def test_update_position_rejects_immutable_fields_with_422(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    field: str,
) -> None:
    company = create_company(db)
    created = _create_position(client, superuser_token_headers, company.id)
    value = "NEWCODE" if field == "position_code" else str(uuid.uuid7())

    response = client.patch(
        position_url(created["id"]),
        headers=superuser_token_headers,
        json={field: value},
    )

    assert response.status_code == 422, response.text
    errors = response.json()["detail"]
    assert errors[0]["type"] == "extra_forbidden"
    assert errors[0]["loc"] == ["body", field]
    assert errors[0]["msg"] == "该字段不可修改"


@pytest.mark.parametrize("field", ["position_name", "order_no", "is_active"])
def test_update_position_rejects_null_for_non_nullable_fields(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    field: str,
) -> None:
    company = create_company(db)
    created = _create_position(client, superuser_token_headers, company.id)

    response = client.patch(
        position_url(created["id"]),
        headers=superuser_token_headers,
        json={field: None},
    )

    assert response.status_code == 422, response.text
    assert field in {error["loc"][-1] for error in response.json()["detail"]}


def test_update_position_rejects_cross_company_or_inactive_departments(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    other_company = create_company(db)
    foreign_department = create_department(db, company=other_company)
    inactive_department = create_department(db, company=company, is_active=False)
    created = _create_position(client, superuser_token_headers, company.id)

    cross_company = client.patch(
        position_url(created["id"]),
        headers=superuser_token_headers,
        json={"dept_id": str(foreign_department.id)},
    )
    inactive = client.patch(
        position_url(created["id"]),
        headers=superuser_token_headers,
        json={"dept_id": str(inactive_department.id)},
    )

    assert cross_company.status_code == 409, cross_company.text
    assert _error(cross_company)["field_errors"] == {
        "dept_id": "默认部门必须属于同一公司"
    }
    assert inactive.status_code == 409, inactive.text
    assert _error(inactive)["field_errors"] == {"dept_id": "默认部门已停用"}


def test_inactive_position_rejects_default_department_changes_only(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    first_department = create_department(db, company=company)
    second_department = create_department(db, company=company)
    created = _create_position(
        client,
        superuser_token_headers,
        company.id,
        position_name="旧岗位",
        dept_id=first_department.id,
    )
    deactivated = client.patch(
        position_url(created["id"]),
        headers=superuser_token_headers,
        json={"is_active": False},
    )
    assert deactivated.status_code == 200, deactivated.text

    structural = client.patch(
        position_url(created["id"]),
        headers=superuser_token_headers,
        json={"dept_id": str(second_department.id)},
    )
    non_structural = client.patch(
        position_url(created["id"]),
        headers=superuser_token_headers,
        json={"position_name": "新岗位", "order_no": 5},
    )

    assert structural.status_code == 409, structural.text
    detail = _error(structural)
    assert detail["code"] == "inactive_entity"
    assert detail["field_errors"] == {"dept_id": "岗位已停用，无法修改默认部门"}
    assert non_structural.status_code == 200, non_structural.text
    assert non_structural.json()["position_name"] == "新岗位"
    assert non_structural.json()["order_no"] == 5


@pytest.mark.parametrize(
    "status", [EmployeeStatus.ACTIVE, EmployeeStatus.PROBATION]
)
def test_deactivating_position_is_blocked_by_active_employees(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    status: EmployeeStatus,
) -> None:
    company = create_company(db)
    department = create_department(db, company=company)
    position = create_position(db, company=company, dept=department)
    employee = create_employee(
        db, dept=department, position=position, employee_no="E1001", name="张三", status=status
    )

    response = client.patch(
        position_url(position.id),
        headers=superuser_token_headers,
        json={"is_active": False},
    )

    assert response.status_code == 409, response.text
    detail = _error(response)
    assert detail["code"] == "deactivate_blocked"
    assert detail["message"] == "无法停用：仍有 1 名在职/试用期员工引用"
    assert detail["field_errors"] == {"is_active": "存在在职/试用期员工"}
    assert detail["blocker_count"] == 1
    assert detail["blockers"] == [
        {
            "type": "employee",
            "id": str(employee.id),
            "code": "E1001",
            "label": "E1001 张三",
        }
    ]
    assert session_position(db, position.id).is_active is True


def test_resigned_employees_do_not_block_deactivation(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    department = create_department(db, company=company)
    position = create_position(db, company=company, dept=department)
    create_employee(
        db,
        dept=department,
        position=position,
        status=EmployeeStatus.RESIGNED,
    )

    response = client.patch(
        position_url(position.id),
        headers=superuser_token_headers,
        json={"is_active": False},
    )

    assert response.status_code == 200, response.text
    assert response.json()["is_active"] is False


def test_reactivating_a_position_requires_an_active_company(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db, is_active=False)
    position = create_position(db, company=company, is_active=False)

    response = client.patch(
        position_url(position.id),
        headers=superuser_token_headers,
        json={"is_active": True},
    )

    assert response.status_code == 409, response.text
    detail = _error(response)
    assert detail["code"] == "activation_blocked"
    assert detail["message"] == "公司已停用，无法启用"
    assert detail["field_errors"] == {"is_active": "公司已停用，无法启用"}
    assert "blockers" not in detail


def test_reactivating_a_position_keeps_an_inactive_default_department(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    inactive_department = create_department(db, company=company, is_active=False)
    position = create_position(
        db, company=company, dept=inactive_department, is_active=False
    )

    response = client.patch(
        position_url(position.id),
        headers=superuser_token_headers,
        json={"is_active": True},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["is_active"] is True
    assert body["dept_id"] == str(inactive_department.id)
    assert body["dept_name"] == inactive_department.dept_name


@pytest.mark.parametrize(
    "status",
    [EmployeeStatus.ACTIVE, EmployeeStatus.PROBATION, EmployeeStatus.RESIGNED],
)
def test_delete_position_is_blocked_by_any_employee_reference(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    status: EmployeeStatus,
) -> None:
    company = create_company(db)
    department = create_department(db, company=company)
    position = create_position(db, company=company, dept=department)
    employee = create_employee(
        db,
        dept=department,
        position=position,
        employee_no="E1001",
        name="张三",
        status=status,
    )

    response = client.delete(
        position_url(position.id), headers=superuser_token_headers
    )

    assert response.status_code == 409, response.text
    detail = _error(response)
    assert detail["code"] == "referenced"
    assert detail["message"] == "无法删除：仍有 1 名员工引用"
    assert detail["blocker_count"] == 1
    assert detail["blockers"] == [
        {
            "type": "employee",
            "id": str(employee.id),
            "code": "E1001",
            "label": "E1001 张三",
        }
    ]
    assert session_position(db, position.id) is not None


def test_delete_position_succeeds_when_unreferenced(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    position = create_position(db, company=company)

    response = client.delete(
        position_url(position.id), headers=superuser_token_headers
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"message": "岗位删除成功"}
    db.expunge_all()
    assert db.get(Position, position.id) is None
    assert client.get(
        position_url(position.id), headers=superuser_token_headers
    ).status_code == 404


def test_list_positions_filters_by_company_department_keyword_and_active(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    other_company = create_company(db)
    production = create_department(db, company=company, dept_name="生产部")
    finance = create_department(db, company=company, dept_name="财务部")
    create_position(
        db,
        company=company,
        position_code="P1",
        position_name="生产主管",
        dept=production,
    )
    create_position(
        db,
        company=company,
        position_code="P2",
        position_name="财务会计",
        dept=finance,
        is_active=False,
    )
    create_position(
        db,
        company=company,
        position_code="P3",
        position_name="生产工人",
        dept=None,
    )
    create_position(
        db, company=other_company, position_code="X1", position_name="生产主管"
    )

    def list_positions(**params: Any) -> list[dict[str, Any]]:
        response = client.get(
            POSITIONS_URL,
            headers=superuser_token_headers,
            params={"company_id": str(company.id), **params},
        )
        assert response.status_code == 200, response.text
        return response.json()["data"]

    assert [item["position_code"] for item in list_positions()] == [
        "P1",
        "P2",
        "P3",
    ]
    assert [item["position_code"] for item in list_positions(dept_id=str(production.id))] == [
        "P1"
    ]
    assert [
        item["position_code"] for item in list_positions(keyword="生产")
    ] == ["P1", "P3"]
    assert [item["position_code"] for item in list_positions(keyword="p2")] == ["P2"]
    assert [item["position_code"] for item in list_positions(is_active=True)] == [
        "P1",
        "P3",
    ]
    assert [item["position_code"] for item in list_positions(is_active=False)] == [
        "P2"
    ]


def test_list_positions_uses_fixed_order_and_pagination(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    create_position(
        db, company=company, position_code="P3", position_name="丙", order_no=1
    )
    create_position(
        db, company=company, position_code="P2", position_name="乙", order_no=0
    )
    create_position(
        db, company=company, position_code="P1", position_name="甲", order_no=0
    )

    response = client.get(
        POSITIONS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "skip": 1, "limit": 1},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["count"] == 3
    assert [item["position_code"] for item in body["data"]] == ["P2"]


def test_list_positions_validates_query_parameters(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)

    missing_company = client.get(POSITIONS_URL, headers=superuser_token_headers)
    unknown_company = client.get(
        POSITIONS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(uuid.uuid7())},
    )
    unknown_department = client.get(
        POSITIONS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "dept_id": str(uuid.uuid7())},
    )
    invalid_limit = client.get(
        POSITIONS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "limit": 501},
    )
    zero_limit = client.get(
        POSITIONS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "limit": 0},
    )
    negative_skip = client.get(
        POSITIONS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "skip": -1},
    )
    long_keyword = client.get(
        POSITIONS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "keyword": "k" * 101},
    )

    assert missing_company.status_code == 422, missing_company.text
    assert unknown_company.status_code == 404, unknown_company.text
    assert unknown_company.json() == {
        "detail": {"code": "not_found", "message": "公司不存在"}
    }
    assert unknown_department.status_code == 404, unknown_department.text
    assert unknown_department.json() == {
        "detail": {"code": "not_found", "message": "部门不存在"}
    }
    assert invalid_limit.status_code == 422, invalid_limit.text
    assert zero_limit.status_code == 422, zero_limit.text
    assert negative_skip.status_code == 422, negative_skip.text
    assert long_keyword.status_code == 422, long_keyword.text


def test_missing_position_returns_404_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    missing = uuid.uuid7()

    for method, url, kwargs in (
        ("get", position_url(missing), {}),
        ("patch", position_url(missing), {"json": {"position_name": "新岗位"}}),
        ("delete", position_url(missing), {}),
    ):
        response = getattr(client, method)(
            url, headers=superuser_token_headers, **kwargs
        )
        assert response.status_code == 404, (method, response.text)
        assert response.json() == {
            "detail": {"code": "not_found", "message": "岗位不存在"}
        }
