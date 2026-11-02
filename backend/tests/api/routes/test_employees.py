"""Employee API contract tests.

Seam: the HTTP API under ``/api/v1/employees``. The tests assert the approved
contract from ``docs/specs/basic-management.md``: request/response shapes, the
global employee number, assignments, manager rules, the status machine, date
rules, filters, display fields, and the absence of a delete endpoint.
"""

import uuid
from datetime import date, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.enums import EmployeeStatus
from app.models import Employee
from tests.utils.factories import (
    create_company,
    create_cost_center,
    create_department,
    create_employee,
    create_position,
)
from tests.utils.utils import random_upper_code

EMPLOYEES_URL = f"{settings.API_V1_STR}/employees/"


def employee_url(employee_id: uuid.UUID | str) -> str:
    return f"{EMPLOYEES_URL}{employee_id}"


def _create_employee(
    client: TestClient,
    headers: dict[str, str],
    *,
    dept_id: uuid.UUID | str,
    position_id: uuid.UUID | str,
    employee_no: str | None = None,
    name: str = "张三",
    gender: str | None = None,
    cost_org_id: uuid.UUID | str | None = None,
    manager_id: uuid.UUID | str | None = None,
    status: str = "active",
    hire_date: str | None = None,
    contract_type: str = "full_time",
    daily_hours: Any = None,
    monthly_rest: int | None = None,
    confidentiality_level: int | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "employee_no": employee_no or random_upper_code("E"),
        "name": name,
        "gender": gender,
        "dept_id": str(dept_id),
        "position_id": str(position_id),
        "cost_org_id": str(cost_org_id) if cost_org_id else None,
        "manager_id": str(manager_id) if manager_id else None,
        "status": status,
        "hire_date": hire_date or (date.today() - timedelta(days=30)).isoformat(),
        "contract_type": contract_type,
        "daily_hours": daily_hours,
        "monthly_rest": monthly_rest,
        "confidentiality_level": confidentiality_level,
        "note": note,
    }
    response = client.post(EMPLOYEES_URL, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def session_employee(db: Session, employee_id: uuid.UUID | str) -> Employee:
    employee = db.get(Employee, uuid.UUID(str(employee_id)))
    assert employee is not None
    return employee


def _error(response: Any) -> dict[str, Any]:
    body = response.json()
    assert isinstance(body["detail"], dict), body
    return body["detail"]


def _setup_org(db: Session) -> tuple[Any, Any, Any]:
    """A company with one department and one position ready for employees."""
    company = create_company(db, company_name="荣新建设")
    department = create_department(db, company=company, dept_name="生产部")
    position = create_position(db, company=company, position_name="项目经理")
    return company, department, position


def test_employee_endpoints_require_authentication(client: TestClient) -> None:
    for method, url, kwargs in (
        ("get", EMPLOYEES_URL, {}),
        ("post", EMPLOYEES_URL, {"json": {}}),
        ("get", employee_url(uuid.uuid7()), {}),
        ("patch", employee_url(uuid.uuid7()), {"json": {}}),
    ):
        response = getattr(client, method)(url, **kwargs)
        assert response.status_code == 401, (method, response.text)
        assert response.json() == {"detail": "未登录或登录状态已过期"}


def test_create_employee_normalizes_the_number_and_returns_public_fields(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company, department, position = _setup_org(db)
    hire_date = date.today() - timedelta(days=30)

    response = client.post(
        EMPLOYEES_URL,
        headers=superuser_token_headers,
        json={
            "employee_no": "  e-1001  ",
            "name": "张三",
            "dept_id": str(department.id),
            "position_id": str(position.id),
            "hire_date": hire_date.isoformat(),
            "contract_type": "full_time",
            "note": "",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["employee_no"] == "E-1001"
    assert body["name"] == "张三"
    assert body["gender"] is None
    assert body["dept_id"] == str(department.id)
    assert body["position_id"] == str(position.id)
    assert body["cost_org_id"] is None
    assert body["manager_id"] is None
    assert body["status"] == "active"
    assert body["hire_date"] == hire_date.isoformat()
    assert body["resign_date"] is None
    assert body["contract_type"] == "full_time"
    assert body["daily_hours"] is None
    assert body["monthly_rest"] is None
    assert body["confidentiality_level"] is None
    assert body["note"] is None
    assert body["company_id"] == str(company.id)
    assert body["company_name"] == "荣新建设"
    assert body["dept_name"] == "生产部"
    assert body["position_name"] == "项目经理"
    assert body["cost_org_name"] is None
    assert body["manager_name"] is None
    assert body["manager_status"] is None
    assert uuid.UUID(body["id"]).version == 7


def test_create_employee_rejects_a_resigned_status(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    _, department, position = _setup_org(db)

    response = client.post(
        EMPLOYEES_URL,
        headers=superuser_token_headers,
        json={
            "employee_no": "E1",
            "name": "张三",
            "dept_id": str(department.id),
            "position_id": str(position.id),
            "status": "resigned",
            "hire_date": date.today().isoformat(),
            "contract_type": "full_time",
        },
    )

    assert response.status_code == 409, response.text
    detail = _error(response)
    assert detail["code"] == "invalid_status_transition"
    assert "status" in detail["field_errors"]


def test_employee_numbers_are_globally_unique_and_names_may_repeat(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    first_company = create_company(db, company_name="甲公司")
    first_dept = create_department(db, company=first_company)
    first_position = create_position(db, company=first_company)
    second_company = create_company(db, company_name="乙公司")
    second_dept = create_department(db, company=second_company)
    second_position = create_position(db, company=second_company)

    _create_employee(
        client,
        superuser_token_headers,
        dept_id=first_dept.id,
        position_id=first_position.id,
        employee_no="E1001",
        name="张三",
    )
    _create_employee(
        client,
        superuser_token_headers,
        dept_id=second_dept.id,
        position_id=second_position.id,
        employee_no="E1002",
        name="张三",
    )

    duplicate = client.post(
        EMPLOYEES_URL,
        headers=superuser_token_headers,
        json={
            "employee_no": "e1001",
            "name": "李四",
            "dept_id": str(second_dept.id),
            "position_id": str(second_position.id),
            "hire_date": date.today().isoformat(),
            "contract_type": "full_time",
        },
    )

    assert duplicate.status_code == 409, duplicate.text
    detail = _error(duplicate)
    assert detail["code"] == "duplicate_code"
    assert detail["field_errors"]["employee_no"] == "工号已存在"


def test_create_employee_validates_profile_fields_and_dates(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    _, department, position = _setup_org(db)
    base = {
        "employee_no": "E1",
        "name": "张三",
        "dept_id": str(department.id),
        "position_id": str(position.id),
        "hire_date": date.today().isoformat(),
        "contract_type": "full_time",
    }

    future = client.post(
        EMPLOYEES_URL,
        headers=superuser_token_headers,
        json={**base, "hire_date": (date.today() + timedelta(days=1)).isoformat()},
    )
    assert future.status_code == 422
    assert future.json()["detail"][0]["msg"] == "入职日期不能晚于今天"

    for field, value, message in (
        ("daily_hours", 0, "必须大于 0"),
        ("daily_hours", 24.5, "不能大于 24"),
        ("monthly_rest", -1, "不能小于 0"),
        ("confidentiality_level", 0, "不能小于 1"),
        ("confidentiality_level", 6, "不能大于 5"),
        ("gender", "other", "输入值无效"),
        ("contract_type", "contractor", "输入值无效"),
    ):
        response = client.post(
            EMPLOYEES_URL,
            headers=superuser_token_headers,
            json={**base, field: value},
        )
        assert response.status_code == 422, (field, value, response.text)
        assert message in response.json()["detail"][0]["msg"], (field, value)


def test_create_employee_rejects_a_resign_date(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    _, department, position = _setup_org(db)

    response = client.post(
        EMPLOYEES_URL,
        headers=superuser_token_headers,
        json={
            "employee_no": "E1",
            "name": "张三",
            "dept_id": str(department.id),
            "position_id": str(position.id),
            "hire_date": date.today().isoformat(),
            "resign_date": date.today().isoformat(),
            "contract_type": "full_time",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "该字段不可修改"


def test_create_employee_requires_same_company_active_references(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company, department, position = _setup_org(db)
    other_company = create_company(db, company_name="乙公司")
    other_position = create_position(db, company=other_company)
    other_cost_center = create_cost_center(db, company=other_company)
    inactive_department = create_department(db, company=company, is_active=False)
    inactive_position = create_position(db, company=company, is_active=False)
    inactive_cost_center = create_cost_center(db, company=company, is_active=False)

    cases = (
        ("dept_id", uuid.uuid7(), "invalid_reference"),
        ("dept_id", inactive_department.id, "inactive_reference"),
        ("position_id", uuid.uuid7(), "invalid_reference"),
        ("position_id", other_position.id, "cross_company"),
        ("position_id", inactive_position.id, "inactive_reference"),
        ("cost_org_id", uuid.uuid7(), "invalid_reference"),
        ("cost_org_id", other_cost_center.id, "cross_company"),
        ("cost_org_id", inactive_cost_center.id, "inactive_reference"),
    )

    for field, value, expected_code in cases:
        payload = {
            "employee_no": random_upper_code("E"),
            "name": "张三",
            "dept_id": str(department.id),
            "position_id": str(position.id),
            "hire_date": date.today().isoformat(),
            "contract_type": "full_time",
            field: str(value),
        }
        response = client.post(
            EMPLOYEES_URL, headers=superuser_token_headers, json=payload
        )
        assert response.status_code == 409, (field, value, response.text)
        detail = _error(response)
        assert detail["code"] == expected_code, (field, value, detail)
        assert field in detail["field_errors"]


def test_create_employee_manager_must_be_same_company_and_active(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company, department, position = _setup_org(db)
    manager = create_employee(db, dept=department, position=position, name="经理")
    other_company = create_company(db, company_name="乙公司")
    other_department = create_department(db, company=other_company)
    other_position = create_position(db, company=other_company)
    other_manager = create_employee(
        db, dept=other_department, position=other_position, name="外部经理"
    )
    resigned_manager = create_employee(
        db,
        dept=department,
        position=position,
        name="离职经理",
        status=EmployeeStatus.RESIGNED,
    )

    cases = (
        (uuid.uuid7(), "invalid_reference"),
        (other_manager.id, "cross_company"),
        (resigned_manager.id, "inactive_reference"),
    )
    for manager_id, expected_code in cases:
        response = client.post(
            EMPLOYEES_URL,
            headers=superuser_token_headers,
            json={
                "employee_no": random_upper_code("E"),
                "name": "张三",
                "dept_id": str(department.id),
                "position_id": str(position.id),
                "manager_id": str(manager_id),
                "hire_date": date.today().isoformat(),
                "contract_type": "full_time",
            },
        )
        assert response.status_code == 409, (manager_id, response.text)
        assert _error(response)["code"] == expected_code

    created = _create_employee(
        client,
        superuser_token_headers,
        dept_id=department.id,
        position_id=position.id,
        manager_id=manager.id,
        name="下属",
    )
    assert created["manager_id"] == str(manager.id)
    assert created["manager_name"] == "经理"
    assert created["manager_status"] == "active"


def test_employee_company_is_derived_from_the_department(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    first_company, first_department, first_position = _setup_org(db)
    second_company = create_company(db, company_name="乙公司")
    second_department = create_department(db, company=second_company)
    second_position = create_position(db, company=second_company)

    first = _create_employee(
        client,
        superuser_token_headers,
        dept_id=first_department.id,
        position_id=first_position.id,
    )
    second = _create_employee(
        client,
        superuser_token_headers,
        dept_id=second_department.id,
        position_id=second_position.id,
    )

    assert first["company_id"] == str(first_company.id)
    assert second["company_id"] == str(second_company.id)
    assert second["company_name"] == "乙公司"


def test_any_logged_in_user_can_list_employees(
    client: TestClient,
    db: Session,
    normal_user_token_headers: dict[str, str],
) -> None:
    _, department, position = _setup_org(db)
    create_employee(db, dept=department, position=position)

    response = client.get(EMPLOYEES_URL, headers=normal_user_token_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["data"][0]["employee_no"]


def test_list_employees_defaults_to_active_and_probation(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    _, department, position = _setup_org(db)
    create_employee(
        db, dept=department, position=position, employee_no="E1", name="在职"
    )
    create_employee(
        db,
        dept=department,
        position=position,
        employee_no="E2",
        name="试用",
        status=EmployeeStatus.PROBATION,
    )
    create_employee(
        db,
        dept=department,
        position=position,
        employee_no="E3",
        name="离职",
        status=EmployeeStatus.RESIGNED,
    )

    response = client.get(EMPLOYEES_URL, headers=superuser_token_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert [item["employee_no"] for item in body["data"]] == ["E1", "E2"]
    assert body["count"] == 2

    all_statuses = client.get(
        EMPLOYEES_URL,
        headers=superuser_token_headers,
        params=[("status", "active"), ("status", "probation"), ("status", "resigned")],
    )
    assert all_statuses.status_code == 200
    assert [item["employee_no"] for item in all_statuses.json()["data"]] == [
        "E1",
        "E2",
        "E3",
    ]

    resigned_only = client.get(
        EMPLOYEES_URL,
        headers=superuser_token_headers,
        params={"status": "resigned"},
    )
    assert [item["employee_no"] for item in resigned_only.json()["data"]] == ["E3"]


def test_list_employees_filters_by_company_department_subtree_and_position(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company = create_company(db)
    root = create_department(db, company=company, dept_name="总部")
    child = create_department(db, company=company, parent=root, dept_name="生产部")
    grandchild = create_department(
        db, company=company, parent=child, dept_name="一车间"
    )
    other_root = create_department(db, company=company, dept_name="财务部")
    position = create_position(db, company=company, position_name="工人")
    other_position = create_position(db, company=company, position_name="会计")
    other_company = create_company(db, company_name="乙公司")
    other_department = create_department(db, company=other_company)

    create_employee(db, dept=root, position=position, employee_no="E1")
    create_employee(db, dept=child, position=position, employee_no="E2")
    create_employee(db, dept=grandchild, position=other_position, employee_no="E3")
    create_employee(db, dept=other_root, position=other_position, employee_no="E4")
    create_employee(db, dept=other_department, position=position, employee_no="E5")

    subtree = client.get(
        EMPLOYEES_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "dept_id": str(root.id)},
    )
    assert subtree.status_code == 200
    assert [item["employee_no"] for item in subtree.json()["data"]] == [
        "E1",
        "E2",
        "E3",
    ]

    by_position = client.get(
        EMPLOYEES_URL,
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "position_id": str(other_position.id)},
    )
    assert [item["employee_no"] for item in by_position.json()["data"]] == [
        "E3",
        "E4",
    ]

    other_scope = client.get(
        EMPLOYEES_URL,
        headers=superuser_token_headers,
        params={"company_id": str(other_company.id)},
    )
    assert [item["employee_no"] for item in other_scope.json()["data"]] == ["E5"]


def test_list_employees_filters_by_cost_center_and_unassigned(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company, department, position = _setup_org(db)
    cost_center = create_cost_center(db, company=company)
    other_cost_center = create_cost_center(db, company=company, cost_org_code="K2")
    create_employee(
        db,
        dept=department,
        position=position,
        employee_no="E1",
        cost_org=cost_center,
    )
    create_employee(
        db,
        dept=department,
        position=position,
        employee_no="E2",
        cost_org=other_cost_center,
    )
    create_employee(db, dept=department, position=position, employee_no="E3")

    by_cost = client.get(
        EMPLOYEES_URL,
        headers=superuser_token_headers,
        params={"cost_org_id": str(cost_center.id)},
    )
    assert [item["employee_no"] for item in by_cost.json()["data"]] == ["E1"]

    unassigned = client.get(
        EMPLOYEES_URL,
        headers=superuser_token_headers,
        params={"unassigned_cost_org": True},
    )
    assert unassigned.status_code == 200
    assert [item["employee_no"] for item in unassigned.json()["data"]] == ["E3"]
    assert unassigned.json()["data"][0]["cost_org_name"] is None

    conflict = client.get(
        EMPLOYEES_URL,
        headers=superuser_token_headers,
        params={
            "unassigned_cost_org": True,
            "cost_org_id": str(cost_center.id),
        },
    )
    assert conflict.status_code == 422, conflict.text
    assert (
        "未分配成本中心与指定成本中心不能同时使用"
        in conflict.json()["detail"][0]["msg"]
    )


def test_list_employees_searches_and_sorts_by_number_then_name(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    _, department, position = _setup_org(db)
    create_employee(
        db, dept=department, position=position, employee_no="E2", name="李四"
    )
    create_employee(
        db, dept=department, position=position, employee_no="E1", name="张三"
    )
    create_employee(
        db, dept=department, position=position, employee_no="E3", name="张三丰"
    )

    response = client.get(EMPLOYEES_URL, headers=superuser_token_headers)

    assert [item["employee_no"] for item in response.json()["data"]] == [
        "E1",
        "E2",
        "E3",
    ]
    assert [item["name"] for item in response.json()["data"]] == [
        "张三",
        "李四",
        "张三丰",
    ]

    keyword = client.get(
        EMPLOYEES_URL,
        headers=superuser_token_headers,
        params={"keyword": "张三"},
    )
    assert [item["employee_no"] for item in keyword.json()["data"]] == ["E1", "E3"]

    by_number = client.get(
        EMPLOYEES_URL,
        headers=superuser_token_headers,
        params={"keyword": "e2"},
    )
    assert [item["employee_no"] for item in by_number.json()["data"]] == ["E2"]


def test_list_employees_paginates_and_validates_query_ids(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    _, department, position = _setup_org(db)
    for index in range(3):
        create_employee(
            db,
            dept=department,
            position=position,
            employee_no=f"E{index + 1}",
        )

    page = client.get(
        EMPLOYEES_URL,
        headers=superuser_token_headers,
        params={"skip": 1, "limit": 1},
    )
    assert page.json()["count"] == 3
    assert [item["employee_no"] for item in page.json()["data"]] == ["E2"]

    assert (
        client.get(
            EMPLOYEES_URL,
            headers=superuser_token_headers,
            params={"skip": -1},
        ).status_code
        == 422
    )
    assert (
        client.get(
            EMPLOYEES_URL,
            headers=superuser_token_headers,
            params={"limit": 0},
        ).status_code
        == 422
    )
    assert (
        client.get(
            EMPLOYEES_URL,
            headers=superuser_token_headers,
            params={"limit": 501},
        ).status_code
        == 422
    )

    for parameter in ("company_id", "dept_id", "position_id", "cost_org_id"):
        response = client.get(
            EMPLOYEES_URL,
            headers=superuser_token_headers,
            params={parameter: str(uuid.uuid7())},
        )
        assert response.status_code == 404, (parameter, response.text)
        assert _error(response)["code"] == "not_found"

    invalid_status = client.get(
        EMPLOYEES_URL,
        headers=superuser_token_headers,
        params={"status": "unknown"},
    )
    assert invalid_status.status_code == 422


def test_employee_list_returns_display_fields_with_a_resigned_manager(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company, department, position = _setup_org(db)
    cost_center = create_cost_center(db, company=company, cost_org_name="生产成本中心")
    manager = create_employee(
        db, dept=department, position=position, employee_no="E1", name="经理"
    )
    employee = _create_employee(
        client,
        superuser_token_headers,
        dept_id=department.id,
        position_id=position.id,
        cost_org_id=cost_center.id,
        manager_id=manager.id,
        employee_no="E2",
        name="下属",
        gender="female",
        daily_hours="8.00",
        monthly_rest=8,
        confidentiality_level=3,
    )

    assert employee["company_name"] == "荣新建设"
    assert employee["dept_name"] == "生产部"
    assert employee["position_name"] == "项目经理"
    assert employee["cost_org_name"] == "生产成本中心"
    assert employee["manager_name"] == "经理"
    assert employee["manager_status"] == "active"
    assert employee["daily_hours"] == "8.00"
    assert employee["monthly_rest"] == 8
    assert employee["confidentiality_level"] == 3

    resigned = client.patch(
        employee_url(manager.id),
        headers=superuser_token_headers,
        json={
            "status": "resigned",
            "resign_date": date.today().isoformat(),
        },
    )
    assert resigned.status_code == 200, resigned.text

    listing = client.get(EMPLOYEES_URL, headers=superuser_token_headers)
    row = next(item for item in listing.json()["data"] if item["employee_no"] == "E2")
    assert row["manager_id"] == str(manager.id)
    assert row["manager_name"] == "经理"
    assert row["manager_status"] == "resigned"


def test_update_employee_changes_fields_and_refreshes_updated_at(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company, department, position = _setup_org(db)
    cost_center = create_cost_center(db, company=company)
    manager = create_employee(db, dept=department, position=position, name="经理")
    created = _create_employee(
        client,
        superuser_token_headers,
        dept_id=department.id,
        position_id=position.id,
        name="旧名字",
        note="旧备注",
    )

    response = client.patch(
        employee_url(created["id"]),
        headers=superuser_token_headers,
        json={
            "name": "新名字",
            "gender": "female",
            "cost_org_id": str(cost_center.id),
            "manager_id": str(manager.id),
            "contract_type": "part_time",
            "daily_hours": "7.50",
            "monthly_rest": 6,
            "confidentiality_level": 2,
            "note": None,
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["employee_no"] == created["employee_no"]
    assert body["name"] == "新名字"
    assert body["gender"] == "female"
    assert body["cost_org_id"] == str(cost_center.id)
    assert body["cost_org_name"] == "生产成本中心"
    assert body["manager_name"] == "经理"
    assert body["contract_type"] == "part_time"
    assert body["daily_hours"] == "7.50"
    assert body["monthly_rest"] == 6
    assert body["confidentiality_level"] == 2
    assert body["note"] is None
    assert body["created_at"] == created["created_at"]
    assert body["updated_at"] > created["updated_at"]


@pytest.mark.parametrize("field", ["employee_no", "company_id"])
def test_update_employee_rejects_immutable_fields_with_422(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    field: str,
) -> None:
    _, department, position = _setup_org(db)
    created = _create_employee(
        client,
        superuser_token_headers,
        dept_id=department.id,
        position_id=position.id,
    )

    response = client.patch(
        employee_url(created["id"]),
        headers=superuser_token_headers,
        json={field: "NEWVALUE"},
    )

    assert response.status_code == 422, response.text
    errors = response.json()["detail"]
    assert errors[0]["type"] == "extra_forbidden"
    assert errors[0]["loc"] == ["body", field]
    assert errors[0]["msg"] == "该字段不可修改"


@pytest.mark.parametrize(
    "field",
    ["name", "dept_id", "position_id", "status", "hire_date", "contract_type"],
)
def test_update_employee_rejects_null_for_non_nullable_fields(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    field: str,
) -> None:
    _, department, position = _setup_org(db)
    created = _create_employee(
        client,
        superuser_token_headers,
        dept_id=department.id,
        position_id=position.id,
    )

    response = client.patch(
        employee_url(created["id"]),
        headers=superuser_token_headers,
        json={field: None},
    )

    assert response.status_code == 422, response.text
    assert field in {error["loc"][-1] for error in response.json()["detail"]}


def test_update_employee_can_clear_nullable_assignments(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company, department, position = _setup_org(db)
    cost_center = create_cost_center(db, company=company)
    manager = create_employee(db, dept=department, position=position)
    created = _create_employee(
        client,
        superuser_token_headers,
        dept_id=department.id,
        position_id=position.id,
        cost_org_id=cost_center.id,
        manager_id=manager.id,
        gender="male",
        note="备注",
    )

    response = client.patch(
        employee_url(created["id"]),
        headers=superuser_token_headers,
        json={
            "cost_org_id": None,
            "manager_id": None,
            "gender": None,
            "note": "",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["cost_org_id"] is None
    assert body["cost_org_name"] is None
    assert body["manager_id"] is None
    assert body["manager_name"] is None
    assert body["gender"] is None
    assert body["note"] is None


def test_missing_employee_returns_404_and_delete_is_not_available(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    _, department, position = _setup_org(db)
    created = _create_employee(
        client,
        superuser_token_headers,
        dept_id=department.id,
        position_id=position.id,
    )

    missing = client.get(employee_url(uuid.uuid7()), headers=superuser_token_headers)
    assert missing.status_code == 404
    assert _error(missing)["code"] == "not_found"

    deleted = client.delete(
        employee_url(created["id"]), headers=superuser_token_headers
    )
    assert deleted.status_code == 405, deleted.text

    schema = client.get(f"{settings.API_V1_STR}/openapi.json").json()
    assert "/api/v1/employees/{employee_id}" in schema["paths"]
    assert "delete" not in schema["paths"]["/api/v1/employees/{employee_id}"]


def test_update_employee_validates_assignments_and_cross_company_department(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company, department, position = _setup_org(db)
    other_department = create_department(db, company=company)
    inactive_department = create_department(db, company=company, is_active=False)
    other_company = create_company(db, company_name="乙公司")
    cross_department = create_department(db, company=other_company)
    cross_position = create_position(db, company=other_company)
    cross_cost_center = create_cost_center(db, company=other_company)
    inactive_position = create_position(db, company=company, is_active=False)
    inactive_cost_center = create_cost_center(db, company=company, is_active=False)
    created = _create_employee(
        client,
        superuser_token_headers,
        dept_id=department.id,
        position_id=position.id,
    )

    cases = (
        ("dept_id", uuid.uuid7(), "invalid_reference"),
        ("dept_id", inactive_department.id, "inactive_reference"),
        ("dept_id", cross_department.id, "cross_company"),
        ("position_id", uuid.uuid7(), "invalid_reference"),
        ("position_id", inactive_position.id, "inactive_reference"),
        ("position_id", cross_position.id, "cross_company"),
        ("cost_org_id", uuid.uuid7(), "invalid_reference"),
        ("cost_org_id", inactive_cost_center.id, "inactive_reference"),
        ("cost_org_id", cross_cost_center.id, "cross_company"),
    )
    for field, value, expected_code in cases:
        response = client.patch(
            employee_url(created["id"]),
            headers=superuser_token_headers,
            json={field: str(value)},
        )
        assert response.status_code == 409, (field, value, response.text)
        detail = _error(response)
        assert detail["code"] == expected_code, (field, value, detail)
        assert field in detail["field_errors"]

    moved = client.patch(
        employee_url(created["id"]),
        headers=superuser_token_headers,
        json={"dept_id": str(other_department.id)},
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["dept_name"] == other_department.dept_name
    assert moved.json()["company_id"] == str(company.id)


def test_manager_assignment_rejects_self_and_reporting_cycles(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    _, department, position = _setup_org(db)
    boss = _create_employee(
        client,
        superuser_token_headers,
        dept_id=department.id,
        position_id=position.id,
        employee_no="E1",
        name="老板",
    )
    middle = _create_employee(
        client,
        superuser_token_headers,
        dept_id=department.id,
        position_id=position.id,
        employee_no="E2",
        name="主管",
        manager_id=boss["id"],
    )
    leaf = _create_employee(
        client,
        superuser_token_headers,
        dept_id=department.id,
        position_id=position.id,
        employee_no="E3",
        name="员工",
        manager_id=middle["id"],
    )

    self_reference = client.patch(
        employee_url(boss["id"]),
        headers=superuser_token_headers,
        json={"manager_id": boss["id"]},
    )
    assert self_reference.status_code == 409
    assert _error(self_reference)["code"] == "cycle"
    assert _error(self_reference)["field_errors"]["manager_id"]

    cycle = client.patch(
        employee_url(boss["id"]),
        headers=superuser_token_headers,
        json={"manager_id": leaf["id"]},
    )
    assert cycle.status_code == 409
    assert _error(cycle)["code"] == "cycle"

    resigned_manager = client.patch(
        employee_url(leaf["id"]),
        headers=superuser_token_headers,
        json={
            "status": "resigned",
            "resign_date": date.today().isoformat(),
        },
    )
    assert resigned_manager.status_code == 200, resigned_manager.text

    assign_resigned = client.patch(
        employee_url(boss["id"]),
        headers=superuser_token_headers,
        json={"manager_id": leaf["id"]},
    )
    assert assign_resigned.status_code == 409
    assert _error(assign_resigned)["code"] == "inactive_reference"


def test_probation_can_become_active_with_other_edits(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    company, department, position = _setup_org(db)
    other_position = create_position(db, company=company)
    created = _create_employee(
        client,
        superuser_token_headers,
        dept_id=department.id,
        position_id=position.id,
        status="probation",
    )

    response = client.patch(
        employee_url(created["id"]),
        headers=superuser_token_headers,
        json={
            "status": "active",
            "name": "转正员工",
            "position_id": str(other_position.id),
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "active"
    assert response.json()["name"] == "转正员工"
    assert response.json()["position_id"] == str(other_position.id)


def test_active_cannot_return_to_probation(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    _, department, position = _setup_org(db)
    created = _create_employee(
        client,
        superuser_token_headers,
        dept_id=department.id,
        position_id=position.id,
    )

    response = client.patch(
        employee_url(created["id"]),
        headers=superuser_token_headers,
        json={"status": "probation"},
    )

    assert response.status_code == 409
    detail = _error(response)
    assert detail["code"] == "invalid_status_transition"
    assert "status" in detail["field_errors"]


def test_resignation_requires_a_date_and_locks_other_fields(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    _, department, position = _setup_org(db)
    created = _create_employee(
        client,
        superuser_token_headers,
        dept_id=department.id,
        position_id=position.id,
    )

    without_date = client.patch(
        employee_url(created["id"]),
        headers=superuser_token_headers,
        json={"status": "resigned"},
    )
    assert without_date.status_code == 409
    assert _error(without_date)["code"] == "invalid_status_transition"
    assert "resign_date" in _error(without_date)["field_errors"]

    with_extra = client.patch(
        employee_url(created["id"]),
        headers=superuser_token_headers,
        json={
            "status": "resigned",
            "resign_date": date.today().isoformat(),
            "name": "改名",
        },
    )
    assert with_extra.status_code == 409
    detail = _error(with_extra)
    assert detail["code"] == "locked_field"
    assert "name" in detail["field_errors"]

    resigned = client.patch(
        employee_url(created["id"]),
        headers=superuser_token_headers,
        json={
            "status": "resigned",
            "resign_date": date.today().isoformat(),
            "note": "离职备注",
        },
    )
    assert resigned.status_code == 200, resigned.text
    assert resigned.json()["status"] == "resigned"
    assert resigned.json()["resign_date"] == date.today().isoformat()
    assert resigned.json()["note"] == "离职备注"


def test_resigned_employee_can_only_correct_note_and_resign_date(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    _, department, position = _setup_org(db)
    created = _create_employee(
        client,
        superuser_token_headers,
        dept_id=department.id,
        position_id=position.id,
    )
    resigned = client.patch(
        employee_url(created["id"]),
        headers=superuser_token_headers,
        json={
            "status": "resigned",
            "resign_date": date.today().isoformat(),
        },
    )
    assert resigned.status_code == 200, resigned.text

    for payload in (
        {"name": "改名"},
        {"status": "active"},
        {"dept_id": str(department.id)},
        {"hire_date": created["hire_date"]},
    ):
        response = client.patch(
            employee_url(created["id"]),
            headers=superuser_token_headers,
            json=payload,
        )
        assert response.status_code == 409, (payload, response.text)
        assert _error(response)["code"] in {
            "locked_field",
            "invalid_status_transition",
        }, (payload, _error(response))

    corrected = client.patch(
        employee_url(created["id"]),
        headers=superuser_token_headers,
        json={
            "resign_date": created["hire_date"],
            "note": "修正备注",
        },
    )
    assert corrected.status_code == 200, corrected.text
    assert corrected.json()["resign_date"] == created["hire_date"]
    assert corrected.json()["note"] == "修正备注"


def test_employee_date_rules(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    _, department, position = _setup_org(db)
    hire_date = date.today() - timedelta(days=10)
    created = _create_employee(
        client,
        superuser_token_headers,
        dept_id=department.id,
        position_id=position.id,
        hire_date=hire_date.isoformat(),
    )

    future_hire = client.patch(
        employee_url(created["id"]),
        headers=superuser_token_headers,
        json={"hire_date": (date.today() + timedelta(days=1)).isoformat()},
    )
    assert future_hire.status_code == 422
    assert future_hire.json()["detail"][0]["msg"] == "日期不能晚于今天"

    future_resign = client.patch(
        employee_url(created["id"]),
        headers=superuser_token_headers,
        json={
            "status": "resigned",
            "resign_date": (date.today() + timedelta(days=1)).isoformat(),
        },
    )
    assert future_resign.status_code == 422
    assert future_resign.json()["detail"][0]["msg"] == "日期不能晚于今天"

    early_resign = client.patch(
        employee_url(created["id"]),
        headers=superuser_token_headers,
        json={
            "status": "resigned",
            "resign_date": (hire_date - timedelta(days=1)).isoformat(),
        },
    )
    assert early_resign.status_code == 409
    detail = _error(early_resign)
    assert detail["code"] == "invalid_status_transition"
    assert "resign_date" in detail["field_errors"]

    on_non_resigned = client.patch(
        employee_url(created["id"]),
        headers=superuser_token_headers,
        json={"resign_date": date.today().isoformat()},
    )
    assert on_non_resigned.status_code == 409
    assert _error(on_non_resigned)["code"] == "invalid_status_transition"
