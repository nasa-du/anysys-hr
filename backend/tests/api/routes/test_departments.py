"""Department API contract tests.

Seam: the HTTP API under ``/api/v1/departments``. The tests assert the approved
contract from ``docs/specs/basic-management.md``: request/response shapes,
company-scoped codes, parent and manager rules, tree reads, blockers, and the
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
from app.models import Department, Position
from tests.utils.factories import (
    create_company,
    create_department,
    create_employee,
    create_position,
)
from tests.utils.utils import random_upper_code

DEPARTMENTS_URL = f"{settings.API_V1_STR}/departments/"
TREE_URL = f"{DEPARTMENTS_URL}tree"


def department_url(department_id: uuid.UUID | str) -> str:
    return f"{DEPARTMENTS_URL}{department_id}"


def _create_department(
    client: TestClient,
    headers: dict[str, str],
    company_id: uuid.UUID | str,
    *,
    dept_code: str | None = None,
    dept_name: str = "生产部",
    parent_id: uuid.UUID | str | None = None,
    manager_id: uuid.UUID | str | None = None,
    order_no: int = 0,
    is_active: bool = True,
    note: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "dept_code": dept_code or random_upper_code("D"),
        "dept_name": dept_name,
        "company_id": str(company_id),
        "parent_id": str(parent_id) if parent_id else None,
        "manager_id": str(manager_id) if manager_id else None,
        "order_no": order_no,
        "is_active": is_active,
        "note": note,
    }
    response = client.post(DEPARTMENTS_URL, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def session_department(db: Session, department_id: uuid.UUID | str) -> Department:
    department = db.get(Department, uuid.UUID(str(department_id)))
    assert department is not None
    return department


def _error(response: Any) -> dict[str, Any]:
    body = response.json()
    assert isinstance(body["detail"], dict), body
    return body["detail"]


def test_department_endpoints_require_authentication(client: TestClient) -> None:
    company_id = uuid.uuid7()
    for method, url, kwargs in (
        ("get", DEPARTMENTS_URL, {"params": {"company_id": str(company_id)}}),
        ("get", TREE_URL, {"params": {"company_id": str(company_id)}}),
        ("post", DEPARTMENTS_URL, {"json": {}}),
        ("get", department_url(uuid.uuid7()), {}),
        ("patch", department_url(uuid.uuid7()), {"json": {}}),
        ("delete", department_url(uuid.uuid7()), {}),
    ):
        response = getattr(client, method)(url, **kwargs)
        assert response.status_code == 401, (method, response.text)
        assert response.json() == {"detail": "未登录或登录状态已过期"}


def test_any_logged_in_user_can_list_departments(
    client: TestClient,
    db: Session,
    normal_user_token_headers: dict[str, str],
) -> None:
    company = create_company(db)

    response = client.get(
        DEPARTMENTS_URL,
        headers=normal_user_token_headers,
        params={"company_id": str(company.id)},
    )

    assert response.status_code == 200
    assert response.json() == {"data": [], "count": 0}


def test_create_department_normalizes_the_code_and_returns_public_fields(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db, company_name="荣新建设")

    response = client.post(
        DEPARTMENTS_URL,
        headers=superuser_token_headers,
        json={
            "dept_code": "  d-1  ",
            "dept_name": "总部",
            "company_id": str(company.id),
            "note": "",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["dept_code"] == "D-1"
    assert body["dept_name"] == "总部"
    assert body["company_id"] == str(company.id)
    assert body["company_name"] == "荣新建设"
    assert body["parent_id"] is None
    assert body["parent_name"] is None
    assert body["manager_id"] is None
    assert body["manager_name"] is None
    assert body["manager_status"] is None
    assert body["order_no"] == 0
    assert body["is_active"] is True
    assert body["note"] is None
    assert uuid.UUID(body["id"]).version == 7
    created_at = datetime.fromisoformat(body["created_at"].replace("Z", "+00:00"))
    assert created_at.tzinfo is not None


def test_create_child_department_returns_the_parent_name(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    parent = _create_department(
        client, superuser_token_headers, company.id, dept_code="D1", dept_name="总部"
    )

    child = _create_department(
        client,
        superuser_token_headers,
        company.id,
        dept_code="D2",
        dept_name="生产部",
        parent_id=parent["id"],
    )

    assert child["parent_id"] == parent["id"]
    assert child["parent_name"] == "总部"


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"dept_name": "生产部"}, "dept_code"),
        ({"dept_code": "VALID", "dept_name": ""}, "dept_name"),
        ({"dept_code": "bad code", "dept_name": "生产部"}, "dept_code"),
        ({"dept_code": "D" * 33, "dept_name": "生产部"}, "dept_code"),
        ({"dept_code": "VALID", "dept_name": "部" * 101}, "dept_name"),
        (
            {"dept_code": "VALID", "dept_name": "生产部", "note": "备" * 501},
            "note",
        ),
    ],
)
def test_create_department_returns_chinese_validation_errors(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    payload: dict[str, Any],
    field: str,
) -> None:
    company = create_company(db)

    response = client.post(
        DEPARTMENTS_URL,
        headers=superuser_token_headers,
        json={"company_id": str(company.id), **payload},
    )

    assert response.status_code == 422, response.text
    errors = response.json()["detail"]
    matching = [error for error in errors if error["loc"] == ["body", field]]
    assert matching, errors
    message = matching[0]["msg"]
    assert any("一" <= char <= "鿿" for char in message), message


def test_department_codes_are_unique_within_a_company_only(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    first_company = create_company(db)
    second_company = create_company(db)
    _create_department(
        client, superuser_token_headers, first_company.id, dept_code="D1"
    )

    duplicate = client.post(
        DEPARTMENTS_URL,
        headers=superuser_token_headers,
        json={
            "dept_code": "d1",
            "dept_name": "另一个部门",
            "company_id": str(first_company.id),
        },
    )
    other_company = client.post(
        DEPARTMENTS_URL,
        headers=superuser_token_headers,
        json={
            "dept_code": "D1",
            "dept_name": "同名编码",
            "company_id": str(second_company.id),
        },
    )

    assert duplicate.status_code == 409, duplicate.text
    detail = _error(duplicate)
    assert detail["code"] == "duplicate_code"
    assert detail["message"] == "部门编码已存在"
    assert detail["field_errors"] == {"dept_code": "部门编码已存在"}
    assert "blockers" not in detail
    assert other_company.status_code == 201, other_company.text


def test_update_department_changes_fields_and_refreshes_updated_at(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    created = _create_department(
        client, superuser_token_headers, company.id, dept_name="旧名称", note="旧备注"
    )

    response = client.patch(
        department_url(created["id"]),
        headers=superuser_token_headers,
        json={"dept_name": "新名称", "order_no": 3, "note": None},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["dept_code"] == created["dept_code"]
    assert body["dept_name"] == "新名称"
    assert body["order_no"] == 3
    assert body["note"] is None
    assert body["created_at"] == created["created_at"]
    assert body["updated_at"] > created["updated_at"]


@pytest.mark.parametrize("field", ["dept_code", "company_id"])
def test_update_department_rejects_immutable_fields_with_422(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    field: str,
) -> None:
    company = create_company(db)
    created = _create_department(client, superuser_token_headers, company.id)
    value = "NEWCODE" if field == "dept_code" else str(uuid.uuid7())

    response = client.patch(
        department_url(created["id"]),
        headers=superuser_token_headers,
        json={field: value},
    )

    assert response.status_code == 422, response.text
    errors = response.json()["detail"]
    assert errors[0]["type"] == "extra_forbidden"
    assert errors[0]["loc"] == ["body", field]
    assert errors[0]["msg"] == "该字段不可修改"


@pytest.mark.parametrize("field", ["dept_name", "order_no", "is_active"])
def test_update_department_rejects_null_for_non_nullable_fields(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    field: str,
) -> None:
    company = create_company(db)
    created = _create_department(client, superuser_token_headers, company.id)

    response = client.patch(
        department_url(created["id"]),
        headers=superuser_token_headers,
        json={field: None},
    )

    assert response.status_code == 422, response.text
    assert field in {error["loc"][-1] for error in response.json()["detail"]}


def test_update_department_clears_nullable_fields_explicitly(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    parent = _create_department(client, superuser_token_headers, company.id)
    created = _create_department(
        client,
        superuser_token_headers,
        company.id,
        parent_id=parent["id"],
        note="备注",
    )

    response = client.patch(
        department_url(created["id"]),
        headers=superuser_token_headers,
        json={"parent_id": None, "note": None},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["parent_id"] is None
    assert body["parent_name"] is None
    assert body["note"] is None


def test_missing_department_returns_404_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    missing = uuid.uuid7()

    for method, url, kwargs in (
        ("get", department_url(missing), {}),
        ("patch", department_url(missing), {"json": {"dept_name": "新名称"}}),
        ("delete", department_url(missing), {}),
    ):
        response = getattr(client, method)(
            url, headers=superuser_token_headers, **kwargs
        )
        assert response.status_code == 404, (method, response.text)
        assert response.json() == {
            "detail": {"code": "not_found", "message": "部门不存在"}
        }


def test_create_department_rejects_a_missing_company(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.post(
        DEPARTMENTS_URL,
        headers=superuser_token_headers,
        json={
            "dept_code": "D1",
            "dept_name": "总部",
            "company_id": str(uuid.uuid7()),
        },
    )

    assert response.status_code == 409, response.text
    detail = _error(response)
    assert detail["code"] == "invalid_reference"
    assert detail["field_errors"] == {"company_id": "公司不存在"}


def test_create_department_rejects_an_inactive_company(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db, is_active=False)

    response = client.post(
        DEPARTMENTS_URL,
        headers=superuser_token_headers,
        json={
            "dept_code": "D1",
            "dept_name": "总部",
            "company_id": str(company.id),
        },
    )

    assert response.status_code == 409, response.text
    detail = _error(response)
    assert detail["code"] == "inactive_reference"
    assert detail["field_errors"] == {"company_id": "公司已停用，无法创建部门"}


def test_create_department_rejects_a_missing_parent(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)

    response = client.post(
        DEPARTMENTS_URL,
        headers=superuser_token_headers,
        json={
            "dept_code": "D1",
            "dept_name": "总部",
            "company_id": str(company.id),
            "parent_id": str(uuid.uuid7()),
        },
    )

    assert response.status_code == 409, response.text
    detail = _error(response)
    assert detail["code"] == "invalid_reference"
    assert detail["field_errors"] == {"parent_id": "上级部门不存在"}


def test_create_department_rejects_a_cross_company_parent(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    other_company = create_company(db)
    foreign_parent = _create_department(
        client, superuser_token_headers, other_company.id
    )

    response = client.post(
        DEPARTMENTS_URL,
        headers=superuser_token_headers,
        json={
            "dept_code": "D1",
            "dept_name": "总部",
            "company_id": str(company.id),
            "parent_id": foreign_parent["id"],
        },
    )

    assert response.status_code == 409, response.text
    detail = _error(response)
    assert detail["code"] == "cross_company"
    assert detail["field_errors"] == {"parent_id": "上级部门必须属于同一公司"}


def test_create_department_rejects_an_inactive_parent(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    parent = _create_department(
        client, superuser_token_headers, company.id, is_active=False
    )

    response = client.post(
        DEPARTMENTS_URL,
        headers=superuser_token_headers,
        json={
            "dept_code": "D2",
            "dept_name": "生产部",
            "company_id": str(company.id),
            "parent_id": parent["id"],
        },
    )

    assert response.status_code == 409, response.text
    detail = _error(response)
    assert detail["code"] == "inactive_reference"
    assert detail["field_errors"] == {"parent_id": "上级部门已停用"}


def test_update_department_rejects_self_as_parent(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    created = _create_department(client, superuser_token_headers, company.id)

    response = client.patch(
        department_url(created["id"]),
        headers=superuser_token_headers,
        json={"parent_id": created["id"]},
    )

    assert response.status_code == 409, response.text
    detail = _error(response)
    assert detail["code"] == "cycle"
    assert detail["message"] == "上级部门不能是自身或下级部门"
    assert detail["field_errors"] == {"parent_id": "上级部门不能是自身或下级部门"}


def test_update_department_rejects_a_descendant_as_parent(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    root = _create_department(client, superuser_token_headers, company.id)
    child = _create_department(
        client,
        superuser_token_headers,
        company.id,
        parent_id=root["id"],
    )
    grandchild = _create_department(
        client,
        superuser_token_headers,
        company.id,
        parent_id=child["id"],
    )

    response = client.patch(
        department_url(root["id"]),
        headers=superuser_token_headers,
        json={"parent_id": grandchild["id"]},
    )

    assert response.status_code == 409, response.text
    assert _error(response)["code"] == "cycle"


def test_update_department_moves_a_department_between_parents(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    first_parent = _create_department(client, superuser_token_headers, company.id)
    second_parent = _create_department(client, superuser_token_headers, company.id)
    moved = _create_department(
        client,
        superuser_token_headers,
        company.id,
        parent_id=first_parent["id"],
    )

    response = client.patch(
        department_url(moved["id"]),
        headers=superuser_token_headers,
        json={"parent_id": second_parent["id"]},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["parent_id"] == second_parent["id"]
    assert body["parent_name"] == second_parent["dept_name"]


def test_update_department_rejects_a_cross_company_parent(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    other_company = create_company(db)
    department = _create_department(client, superuser_token_headers, company.id)
    foreign_parent = _create_department(
        client, superuser_token_headers, other_company.id
    )

    response = client.patch(
        department_url(department["id"]),
        headers=superuser_token_headers,
        json={"parent_id": foreign_parent["id"]},
    )

    assert response.status_code == 409, response.text
    detail = _error(response)
    assert detail["code"] == "cross_company"
    assert detail["field_errors"] == {"parent_id": "上级部门必须属于同一公司"}


def test_update_department_rejects_an_inactive_parent(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    department = _create_department(client, superuser_token_headers, company.id)
    inactive_parent = _create_department(
        client, superuser_token_headers, company.id, is_active=False
    )

    response = client.patch(
        department_url(department["id"]),
        headers=superuser_token_headers,
        json={"parent_id": inactive_parent["id"]},
    )

    assert response.status_code == 409, response.text
    detail = _error(response)
    assert detail["code"] == "inactive_reference"
    assert detail["field_errors"] == {"parent_id": "上级部门已停用"}


def test_update_department_clears_the_manager_explicitly(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    manager_dept = create_department(db, company=company)
    position = create_position(db, company=company)
    manager = create_employee(db, dept=manager_dept, position=position, name="李四")
    department = _create_department(
        client, superuser_token_headers, company.id, manager_id=manager.id
    )
    assert department["manager_name"] == "李四"

    response = client.patch(
        department_url(department["id"]),
        headers=superuser_token_headers,
        json={"manager_id": None},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["manager_id"] is None
    assert body["manager_name"] is None
    assert body["manager_status"] is None


def test_create_department_rejects_a_cross_company_manager(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    other_company = create_company(db)
    foreign_dept = create_department(db, company=other_company)
    foreign_position = create_position(db, company=other_company)
    foreign_manager = create_employee(db, dept=foreign_dept, position=foreign_position)

    response = client.post(
        DEPARTMENTS_URL,
        headers=superuser_token_headers,
        json={
            "dept_code": "D1",
            "dept_name": "总部",
            "company_id": str(company.id),
            "manager_id": str(foreign_manager.id),
        },
    )

    assert response.status_code == 409, response.text
    detail = _error(response)
    assert detail["code"] == "cross_company"
    assert detail["field_errors"] == {"manager_id": "直属上级必须属于同一公司"}


def test_create_department_rejects_a_missing_manager(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)

    response = client.post(
        DEPARTMENTS_URL,
        headers=superuser_token_headers,
        json={
            "dept_code": "D1",
            "dept_name": "总部",
            "company_id": str(company.id),
            "manager_id": str(uuid.uuid7()),
        },
    )

    assert response.status_code == 409, response.text
    detail = _error(response)
    assert detail["code"] == "invalid_reference"
    assert detail["field_errors"] == {"manager_id": "直属上级不存在"}


def test_create_department_rejects_a_resigned_manager(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    dept = create_department(db, company=company)
    position = create_position(db, company=company)
    resigned = create_employee(
        db,
        dept=dept,
        position=position,
        status=EmployeeStatus.RESIGNED,
        hire_date=datetime(2025, 1, 6, tzinfo=UTC).date(),
        resign_date=datetime(2025, 12, 31, tzinfo=UTC).date(),
    )

    response = client.post(
        DEPARTMENTS_URL,
        headers=superuser_token_headers,
        json={
            "dept_code": "D2",
            "dept_name": "生产部",
            "company_id": str(company.id),
            "manager_id": str(resigned.id),
        },
    )

    assert response.status_code == 409, response.text
    detail = _error(response)
    assert detail["code"] == "inactive_reference"
    assert detail["field_errors"] == {"manager_id": "直属上级必须是在职或试用期员工"}


def test_update_department_accepts_a_probation_manager(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    manager_dept = create_department(db, company=company)
    position = create_position(db, company=company)
    manager = create_employee(
        db,
        dept=manager_dept,
        position=position,
        name="李四",
        status=EmployeeStatus.PROBATION,
    )
    target = _create_department(client, superuser_token_headers, company.id)

    response = client.patch(
        department_url(target["id"]),
        headers=superuser_token_headers,
        json={"manager_id": str(manager.id)},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["manager_id"] == str(manager.id)
    assert body["manager_name"] == "李四"
    assert body["manager_status"] == "probation"


def test_resigned_manager_remains_visible_with_its_status(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    dept = create_department(db, company=company)
    position = create_position(db, company=company)
    manager = create_employee(
        db,
        dept=dept,
        position=position,
        name="王五",
        status=EmployeeStatus.RESIGNED,
        hire_date=datetime(2025, 1, 6, tzinfo=UTC).date(),
        resign_date=datetime(2025, 12, 31, tzinfo=UTC).date(),
    )
    dept.manager_id = manager.id
    db.add(dept)
    db.commit()

    response = client.get(department_url(dept.id), headers=superuser_token_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["manager_id"] == str(manager.id)
    assert body["manager_name"] == "王五"
    assert body["manager_status"] == "resigned"


def test_delete_department_is_blocked_by_child_departments(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    parent = _create_department(
        client, superuser_token_headers, company.id, dept_code="D1"
    )
    _create_department(
        client,
        superuser_token_headers,
        company.id,
        dept_code="D2",
        parent_id=parent["id"],
        is_active=False,
    )

    response = client.delete(
        department_url(parent["id"]), headers=superuser_token_headers
    )

    assert response.status_code == 409, response.text
    detail = _error(response)
    assert detail["code"] == "referenced"
    assert "无法删除" in detail["message"]
    assert detail["blocker_count"] == 1
    assert [blocker["type"] for blocker in detail["blockers"]] == ["department"]
    assert detail["blockers"][0]["code"] == "D2"
    assert detail["blockers"][0]["label"] == "D2 生产部"
    assert (
        client.get(
            department_url(parent["id"]), headers=superuser_token_headers
        ).status_code
        == 200
    )


@pytest.mark.parametrize(
    "status", [EmployeeStatus.ACTIVE, EmployeeStatus.PROBATION, EmployeeStatus.RESIGNED]
)
def test_delete_department_is_blocked_by_any_employee(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    status: EmployeeStatus,
) -> None:
    company = create_company(db)
    dept = _create_department(client, superuser_token_headers, company.id)
    position = create_position(db, company=company)
    employee = create_employee(
        db,
        dept=session_department(db, dept["id"]),
        position=position,
        status=status,
        hire_date=datetime(2025, 1, 6, tzinfo=UTC).date(),
        resign_date=datetime(2025, 12, 31, tzinfo=UTC).date()
        if status is EmployeeStatus.RESIGNED
        else None,
    )

    response = client.delete(
        department_url(dept["id"]), headers=superuser_token_headers
    )

    assert response.status_code == 409, response.text
    detail = _error(response)
    assert detail["code"] == "referenced"
    assert detail["blocker_count"] == 1
    assert [blocker["type"] for blocker in detail["blockers"]] == ["employee"]
    assert detail["blockers"][0]["code"] == employee.employee_no
    assert detail["blockers"][0]["label"] == f"{employee.employee_no} {employee.name}"


def test_delete_department_truncates_blockers_but_reports_the_total(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    parent = _create_department(client, superuser_token_headers, company.id)
    for index in range(25):
        db.add(
            Department(
                dept_code=f"D{index:02d}",
                dept_name=f"子部门{index}",
                company_id=company.id,
                parent_id=uuid.UUID(parent["id"]),
            )
        )
    db.commit()

    response = client.delete(
        department_url(parent["id"]), headers=superuser_token_headers
    )

    assert response.status_code == 409, response.text
    detail = _error(response)
    assert detail["blocker_count"] == 25
    assert len(detail["blockers"]) == 20


def test_delete_unreferenced_department_clears_position_defaults_and_deletes_it(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    dept = _create_department(client, superuser_token_headers, company.id)
    position = create_position(
        db, company=company, dept=session_department(db, dept["id"])
    )

    response = client.delete(
        department_url(dept["id"]), headers=superuser_token_headers
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"message": "部门删除成功"}
    db.expire_all()
    assert db.get(Position, position.id).dept_id is None
    assert (
        client.get(
            department_url(dept["id"]), headers=superuser_token_headers
        ).status_code
        == 404
    )


def test_deactivate_department_is_blocked_by_active_children_and_employees(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    dept = _create_department(
        client, superuser_token_headers, company.id, dept_code="D1"
    )
    _create_department(
        client,
        superuser_token_headers,
        company.id,
        dept_code="D2",
        parent_id=dept["id"],
    )
    position = create_position(db, company=company)
    create_employee(
        db,
        dept=session_department(db, dept["id"]),
        position=position,
        status=EmployeeStatus.PROBATION,
    )

    response = client.patch(
        department_url(dept["id"]),
        headers=superuser_token_headers,
        json={"is_active": False},
    )

    assert response.status_code == 409, response.text
    detail = _error(response)
    assert detail["code"] == "deactivate_blocked"
    assert "无法停用" in detail["message"]
    assert detail["field_errors"] == {
        "is_active": "存在启用中的下级部门或在职/试用期员工"
    }
    assert detail["blocker_count"] == 2
    assert [blocker["type"] for blocker in detail["blockers"]] == [
        "department",
        "employee",
    ]
    still_active = client.get(
        department_url(dept["id"]), headers=superuser_token_headers
    ).json()
    assert still_active["is_active"] is True


def test_deactivate_department_allows_inactive_children_and_resigned_employees(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    dept = _create_department(client, superuser_token_headers, company.id)
    _create_department(
        client,
        superuser_token_headers,
        company.id,
        parent_id=dept["id"],
        is_active=False,
    )
    position = create_position(db, company=company)
    create_employee(
        db,
        dept=session_department(db, dept["id"]),
        position=position,
        status=EmployeeStatus.RESIGNED,
        hire_date=datetime(2025, 1, 6, tzinfo=UTC).date(),
        resign_date=datetime(2025, 12, 31, tzinfo=UTC).date(),
    )

    response = client.patch(
        department_url(dept["id"]),
        headers=superuser_token_headers,
        json={"is_active": False},
    )

    assert response.status_code == 200, response.text
    assert response.json()["is_active"] is False


def test_inactive_department_rejects_structural_edits(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    dept = _create_department(
        client, superuser_token_headers, company.id, is_active=False
    )

    response = client.patch(
        department_url(dept["id"]),
        headers=superuser_token_headers,
        json={"parent_id": None},
    )

    assert response.status_code == 409, response.text
    detail = _error(response)
    assert detail["code"] == "inactive_entity"
    assert detail["field_errors"] == {"parent_id": "部门已停用，无法修改上级部门"}

    non_structural = client.patch(
        department_url(dept["id"]),
        headers=superuser_token_headers,
        json={"dept_name": "新名称", "order_no": 5, "note": "备注"},
    )
    assert non_structural.status_code == 200, non_structural.text
    assert non_structural.json()["dept_name"] == "新名称"


def test_reactivation_requires_the_company_and_all_ancestors_to_be_active(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    inactive_company = create_company(db, is_active=False)
    company_dept = create_department(db, company=inactive_company, is_active=False)

    company_blocked = client.patch(
        department_url(company_dept.id),
        headers=superuser_token_headers,
        json={"is_active": True},
    )
    assert company_blocked.status_code == 409, company_blocked.text
    assert _error(company_blocked)["code"] == "activation_blocked"
    assert _error(company_blocked)["field_errors"] == {
        "is_active": "公司或上级部门已停用，无法启用"
    }

    company = create_company(db)
    inactive_parent = _create_department(
        client, superuser_token_headers, company.id, is_active=False
    )
    # A child of an inactive department can only exist in already-stored data;
    # the API refuses to create it, so use the factory to build that state.
    child = create_department(
        db,
        company=company,
        parent=session_department(db, inactive_parent["id"]),
        is_active=False,
    )
    ancestor_blocked = client.patch(
        department_url(child.id),
        headers=superuser_token_headers,
        json={"is_active": True},
    )
    assert ancestor_blocked.status_code == 409, ancestor_blocked.text
    assert _error(ancestor_blocked)["code"] == "activation_blocked"

    # Activating the inactive parent first makes the child activatable.
    parent_activated = client.patch(
        department_url(inactive_parent["id"]),
        headers=superuser_token_headers,
        json={"is_active": True},
    )
    assert parent_activated.status_code == 200, parent_activated.text
    child_activated = client.patch(
        department_url(child.id),
        headers=superuser_token_headers,
        json={"is_active": True},
    )
    assert child_activated.status_code == 200, child_activated.text
    assert child_activated.json()["is_active"] is True


def test_list_departments_uses_fixed_order_and_scopes_to_the_company(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    other_company = create_company(db)
    _create_department(
        client, superuser_token_headers, company.id, dept_code="D3", order_no=2
    )
    _create_department(
        client, superuser_token_headers, company.id, dept_code="D2", order_no=1
    )
    _create_department(
        client, superuser_token_headers, company.id, dept_code="D1", order_no=1
    )
    _create_department(
        client, superuser_token_headers, other_company.id, dept_code="D0"
    )

    response = client.get(
        DEPARTMENTS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 3
    assert [department["dept_code"] for department in body["data"]] == [
        "D1",
        "D2",
        "D3",
    ]


def test_list_departments_filters_by_parent_keyword_and_active_state(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    parent = _create_department(
        client,
        superuser_token_headers,
        company.id,
        dept_code="D1",
        dept_name="总部",
    )
    _create_department(
        client,
        superuser_token_headers,
        company.id,
        dept_code="D2",
        dept_name="生产部",
        parent_id=parent["id"],
    )
    _create_department(
        client,
        superuser_token_headers,
        company.id,
        dept_code="D3",
        dept_name="市场部",
        parent_id=parent["id"],
        is_active=False,
    )
    _create_department(
        client,
        superuser_token_headers,
        company.id,
        dept_code="D4",
        dept_name="研发部",
    )

    child_response = client.get(
        DEPARTMENTS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "parent_id": parent["id"]},
    )
    assert child_response.status_code == 200
    assert [d["dept_code"] for d in child_response.json()["data"]] == ["D2", "D3"]

    keyword_response = client.get(
        DEPARTMENTS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "keyword": "生产"},
    )
    assert [d["dept_code"] for d in keyword_response.json()["data"]] == ["D2"]

    code_response = client.get(
        DEPARTMENTS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "keyword": "d4"},
    )
    assert [d["dept_code"] for d in code_response.json()["data"]] == ["D4"]

    active_response = client.get(
        DEPARTMENTS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "is_active": True},
    )
    assert {
        department["dept_code"] for department in active_response.json()["data"]
    } == {"D1", "D2", "D4"}

    inactive_response = client.get(
        DEPARTMENTS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "is_active": False},
    )
    assert [d["dept_code"] for d in inactive_response.json()["data"]] == ["D3"]


def test_list_departments_paginates_with_count_after_filters(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    for code in ("D1", "D2", "D3"):
        _create_department(client, superuser_token_headers, company.id, dept_code=code)

    response = client.get(
        DEPARTMENTS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "skip": 1, "limit": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 3
    assert [department["dept_code"] for department in body["data"]] == ["D2"]


def test_list_departments_returns_404_for_unknown_filter_ids(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)

    missing_company = client.get(
        DEPARTMENTS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(uuid.uuid7())},
    )
    assert missing_company.status_code == 404
    assert missing_company.json() == {
        "detail": {"code": "not_found", "message": "公司不存在"}
    }

    missing_parent = client.get(
        DEPARTMENTS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "parent_id": str(uuid.uuid7())},
    )
    assert missing_parent.status_code == 404
    assert missing_parent.json() == {
        "detail": {"code": "not_found", "message": "上级部门不存在"}
    }


@pytest.mark.parametrize("params", [{"skip": -1}, {"limit": 0}, {"limit": 501}])
def test_list_departments_rejects_out_of_range_pagination(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    params: dict[str, Any],
) -> None:
    company = create_company(db)

    response = client.get(
        DEPARTMENTS_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), **params},
    )

    assert response.status_code == 422, response.text


def test_list_departments_requires_the_company_id(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(DEPARTMENTS_URL, headers=superuser_token_headers)

    assert response.status_code == 422, response.text
    errors = response.json()["detail"]
    assert any(error["loc"] == ["query", "company_id"] for error in errors)


def test_tree_returns_nested_nodes_sorted_per_level(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    second_root = _create_department(
        client, superuser_token_headers, company.id, dept_code="R2", order_no=1
    )
    first_root = _create_department(
        client, superuser_token_headers, company.id, dept_code="R1", order_no=0
    )
    _create_department(
        client,
        superuser_token_headers,
        company.id,
        dept_code="C2",
        order_no=1,
        parent_id=first_root["id"],
    )
    _create_department(
        client,
        superuser_token_headers,
        company.id,
        dept_code="C1",
        order_no=0,
        parent_id=first_root["id"],
    )

    response = client.get(
        TREE_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    roots = body["data"]
    assert [node["dept_code"] for node in roots] == ["R1", "R2"]
    assert [node["dept_code"] for node in roots[0]["children"]] == ["C1", "C2"]
    assert roots[0]["children"][0]["children"] == []
    assert roots[1]["children"] == []
    assert roots[1]["id"] == second_root["id"]
    assert roots[0]["company_name"] == company.company_name


def test_tree_prunes_inactive_nodes_when_active_only(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    active = _create_department(
        client, superuser_token_headers, company.id, dept_code="D1"
    )
    _create_department(
        client,
        superuser_token_headers,
        company.id,
        dept_code="D2",
        parent_id=active["id"],
        is_active=False,
    )
    _create_department(
        client, superuser_token_headers, company.id, dept_code="D3", is_active=False
    )

    response = client.get(
        TREE_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "is_active": True},
    )

    assert response.status_code == 200, response.text
    roots = response.json()["data"]
    assert [node["dept_code"] for node in roots] == ["D1"]
    assert roots[0]["children"] == []


def test_tree_returns_404_for_an_unknown_company(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(
        TREE_URL,
        headers=superuser_token_headers,
        params={"company_id": str(uuid.uuid7())},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": {"code": "not_found", "message": "公司不存在"}}


def test_tree_requires_the_company_id(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(TREE_URL, headers=superuser_token_headers)

    assert response.status_code == 422, response.text
    assert any(
        error["loc"] == ["query", "company_id"] for error in response.json()["detail"]
    )


def test_department_created_by_factory_is_returned_with_display_fields(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db, company_name="荣新科技")
    parent = create_department(db, company=company, dept_name="总部")
    dept = create_department(db, company=company, parent=parent, dept_name="生产部")

    response = client.get(department_url(dept.id), headers=superuser_token_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["company_name"] == "荣新科技"
    assert body["parent_name"] == "总部"
    assert body["manager_name"] is None
    assert body["manager_status"] is None
