"""Company API contract tests.

Seam: the HTTP API under ``/api/v1/companies``. The tests assert the approved
contract from ``docs/specs/basic-management.md``: request/response shapes,
pagination, fixed sorting, filters, authentication, and error envelopes.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.enums import EmployeeStatus
from app.models import Company
from tests.utils.factories import (
    create_company,
    create_cost_center,
    create_department,
    create_employee,
    create_position,
)
from tests.utils.utils import random_upper_code

COMPANIES_URL = f"{settings.API_V1_STR}/companies/"


def company_url(company_id: uuid.UUID | str) -> str:
    return f"{COMPANIES_URL}{company_id}"


def _create_company(
    client: TestClient,
    headers: dict[str, str],
    *,
    company_code: str | None = None,
    company_name: str = "荣新建设",
    is_active: bool = True,
    note: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "company_code": company_code or random_upper_code("C"),
        "company_name": company_name,
        "is_active": is_active,
        "note": note,
    }
    response = client.post(COMPANIES_URL, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_company_endpoints_require_authentication(client: TestClient) -> None:
    for method, url in (
        ("get", COMPANIES_URL),
        ("post", COMPANIES_URL),
        ("get", company_url(uuid.uuid7())),
        ("patch", company_url(uuid.uuid7())),
        ("delete", company_url(uuid.uuid7())),
    ):
        kwargs = {"json": {}} if method in {"post", "patch"} else {}
        response = getattr(client, method)(url, **kwargs)
        assert response.status_code == 401, (method, response.text)
        assert response.json() == {"detail": "未登录或登录状态已过期"}


def test_any_logged_in_user_can_list_companies(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    response = client.get(COMPANIES_URL, headers=normal_user_token_headers)

    assert response.status_code == 200
    assert response.json() == {"data": [], "count": 0}


def test_create_company_normalizes_the_code_and_returns_public_fields(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.post(
        COMPANIES_URL,
        headers=superuser_token_headers,
        json={"company_code": "  rx-1  ", "company_name": "荣新建设", "note": ""},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["company_code"] == "RX-1"
    assert body["company_name"] == "荣新建设"
    assert body["is_active"] is True
    assert body["note"] is None
    assert uuid.UUID(body["id"]).version == 7
    created_at = datetime.fromisoformat(body["created_at"].replace("Z", "+00:00"))
    updated_at = datetime.fromisoformat(body["updated_at"].replace("Z", "+00:00"))
    assert created_at.tzinfo is not None
    assert updated_at.tzinfo is not None


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({}, "company_code"),
        ({"company_code": "VALID", "company_name": ""}, "company_name"),
        ({"company_code": "bad code", "company_name": "荣新建设"}, "company_code"),
        ({"company_code": "A" * 33, "company_name": "荣新建设"}, "company_code"),
        ({"company_code": "VALID", "company_name": "荣" * 101}, "company_name"),
        (
            {"company_code": "VALID", "company_name": "荣新建设", "note": "备" * 501},
            "note",
        ),
    ],
)
def test_create_company_returns_chinese_validation_errors(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    payload: dict[str, Any],
    field: str,
) -> None:
    response = client.post(COMPANIES_URL, headers=superuser_token_headers, json=payload)

    assert response.status_code == 422, response.text
    errors = response.json()["detail"]
    assert isinstance(errors, list) and errors
    matching = [error for error in errors if error["loc"] == ["body", field]]
    assert matching, errors
    message = matching[0]["msg"]
    assert any("一" <= char <= "鿿" for char in message), message


def test_duplicate_company_code_returns_409_duplicate_code(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    code = random_upper_code("C")
    _create_company(client, superuser_token_headers, company_code=code)

    response = client.post(
        COMPANIES_URL,
        headers=superuser_token_headers,
        json={"company_code": code.lower(), "company_name": "另一家公司"},
    )

    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert detail["code"] == "duplicate_code"
    assert detail["message"] == "公司编码已存在"
    assert detail["field_errors"] == {"company_code": "公司编码已存在"}
    assert "blockers" not in detail
    assert "blocker_count" not in detail


def test_get_company_returns_404_not_found_envelope(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(company_url(uuid.uuid7()), headers=superuser_token_headers)

    assert response.status_code == 404
    assert response.json() == {"detail": {"code": "not_found", "message": "公司不存在"}}


def test_get_company_returns_the_created_company(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    created = _create_company(
        client, superuser_token_headers, company_name="荣新科技", note="备注"
    )

    response = client.get(company_url(created["id"]), headers=superuser_token_headers)

    assert response.status_code == 200
    assert response.json() == created


def test_update_company_changes_fields_and_refreshes_updated_at(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    created = _create_company(
        client, superuser_token_headers, company_name="旧名称", note="旧备注"
    )

    response = client.patch(
        company_url(created["id"]),
        headers=superuser_token_headers,
        json={"company_name": "新名称", "note": None},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["company_code"] == created["company_code"]
    assert body["company_name"] == "新名称"
    assert body["note"] is None
    assert body["created_at"] == created["created_at"]
    assert body["updated_at"] > created["updated_at"]


def test_update_company_rejects_immutable_code_with_422(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    created = _create_company(client, superuser_token_headers)

    response = client.patch(
        company_url(created["id"]),
        headers=superuser_token_headers,
        json={"company_code": "NEWCODE"},
    )

    assert response.status_code == 422, response.text
    errors = response.json()["detail"]
    assert errors[0]["type"] == "extra_forbidden"
    assert errors[0]["loc"] == ["body", "company_code"]
    assert errors[0]["msg"] == "该字段不可修改"


def test_update_company_rejects_null_for_non_nullable_fields(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    created = _create_company(client, superuser_token_headers)

    response = client.patch(
        company_url(created["id"]),
        headers=superuser_token_headers,
        json={"company_name": None},
    )

    assert response.status_code == 422, response.text
    assert "company_name" in {error["loc"][-1] for error in response.json()["detail"]}


def test_update_missing_company_returns_404(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.patch(
        company_url(uuid.uuid7()),
        headers=superuser_token_headers,
        json={"company_name": "新名称"},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "not_found"


def test_list_companies_uses_fixed_code_order_and_returns_count(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    _create_company(client, superuser_token_headers, company_code="C3")
    _create_company(client, superuser_token_headers, company_code="C1")
    _create_company(client, superuser_token_headers, company_code="C2")

    response = client.get(COMPANIES_URL, headers=superuser_token_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 3
    assert [company["company_code"] for company in body["data"]] == ["C1", "C2", "C3"]


def test_list_companies_filters_by_keyword_and_active_state(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    _create_company(
        client,
        superuser_token_headers,
        company_code="RXJZ",
        company_name="荣新建设",
        is_active=True,
    )
    _create_company(
        client,
        superuser_token_headers,
        company_code="RXKJ",
        company_name="荣新科技",
        is_active=False,
    )
    _create_company(
        client,
        superuser_token_headers,
        company_code="OTH",
        company_name="其他公司",
        is_active=True,
    )

    keyword_response = client.get(
        COMPANIES_URL,
        headers=superuser_token_headers,
        params={"keyword": "荣新"},
    )
    assert keyword_response.status_code == 200
    assert {company["company_code"] for company in keyword_response.json()["data"]} == {
        "RXJZ",
        "RXKJ",
    }

    code_response = client.get(
        COMPANIES_URL,
        headers=superuser_token_headers,
        params={"keyword": "rxkj"},
    )
    assert [c["company_code"] for c in code_response.json()["data"]] == ["RXKJ"]

    active_response = client.get(
        COMPANIES_URL,
        headers=superuser_token_headers,
        params={"is_active": True},
    )
    assert {company["company_code"] for company in active_response.json()["data"]} == {
        "RXJZ",
        "OTH",
    }

    inactive_response = client.get(
        COMPANIES_URL,
        headers=superuser_token_headers,
        params={"is_active": False},
    )
    assert [c["company_code"] for c in inactive_response.json()["data"]] == ["RXKJ"]


def test_list_companies_paginates_with_count_after_filters(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    for code in ("C1", "C2", "C3"):
        _create_company(client, superuser_token_headers, company_code=code)

    response = client.get(
        COMPANIES_URL,
        headers=superuser_token_headers,
        params={"skip": 1, "limit": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 3
    assert [company["company_code"] for company in body["data"]] == ["C2"]


@pytest.mark.parametrize(
    "params",
    [{"skip": -1}, {"limit": 0}, {"limit": 501}, {"keyword": "字" * 101}],
)
def test_list_companies_rejects_out_of_range_query_parameters(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    params: dict[str, Any],
) -> None:
    response = client.get(COMPANIES_URL, headers=superuser_token_headers, params=params)

    assert response.status_code == 422, response.text
    errors = response.json()["detail"]
    assert isinstance(errors, list)
    assert all(any("一" <= char <= "鿿" for char in error["msg"]) for error in errors)


def _organization_graph(
    db: Session,
    *,
    company: Company,
    include_department: bool = True,
    include_position: bool = True,
    include_cost_center: bool = True,
    employee_status: str = "active",
) -> dict[str, Any]:
    graph: dict[str, Any] = {}
    dept = create_department(db, company=company) if include_department else None
    position = create_position(db, company=company) if include_position else None
    cost_center = (
        create_cost_center(db, company=company) if include_cost_center else None
    )
    graph.update(dept=dept, position=position, cost_center=cost_center)
    if dept is not None and position is not None:
        graph["employee"] = create_employee(
            db,
            dept=dept,
            position=position,
            cost_org=cost_center,
            status=EmployeeStatus(employee_status),
        )
    return graph


@pytest.mark.parametrize(
    ("included", "blocker_type"),
    [
        (
            {
                "include_department": True,
                "include_position": False,
                "include_cost_center": False,
            },
            "department",
        ),
        (
            {
                "include_department": False,
                "include_position": True,
                "include_cost_center": False,
            },
            "position",
        ),
        (
            {
                "include_department": False,
                "include_position": False,
                "include_cost_center": True,
            },
            "cost_center",
        ),
    ],
)
def test_delete_company_is_blocked_by_organization_references(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    included: dict[str, bool],
    blocker_type: str,
) -> None:
    company = create_company(db)
    _organization_graph(
        db,
        company=company,
        include_department=included["include_department"],
        include_position=included["include_position"],
        include_cost_center=included["include_cost_center"],
    )

    response = client.delete(company_url(company.id), headers=superuser_token_headers)

    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert detail["code"] == "referenced"
    assert "无法删除" in detail["message"]
    assert detail["blocker_count"] == 1
    assert [blocker["type"] for blocker in detail["blockers"]] == [blocker_type]
    assert detail["blockers"][0]["label"].startswith(detail["blockers"][0]["code"])

    assert (
        client.get(company_url(company.id), headers=superuser_token_headers).status_code
        == 200
    )


def test_delete_company_is_blocked_by_an_employee(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    _organization_graph(db, company=company)

    response = client.delete(company_url(company.id), headers=superuser_token_headers)

    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert detail["code"] == "referenced"
    assert detail["blocker_count"] == 4
    assert [blocker["type"] for blocker in detail["blockers"]] == [
        "department",
        "position",
        "cost_center",
        "employee",
    ]


def test_delete_company_truncates_blockers_but_reports_the_total(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    for _ in range(25):
        create_department(db, company=company)

    response = client.delete(company_url(company.id), headers=superuser_token_headers)

    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert detail["blocker_count"] == 25
    assert len(detail["blockers"]) == 20


def test_delete_unreferenced_company_hard_deletes_it(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    created = _create_company(client, superuser_token_headers)

    response = client.delete(
        company_url(created["id"]), headers=superuser_token_headers
    )

    assert response.status_code == 200
    assert response.json() == {"message": "公司删除成功"}
    assert (
        client.get(
            company_url(created["id"]), headers=superuser_token_headers
        ).status_code
        == 404
    )


def test_deactivate_company_is_blocked_by_active_organization_and_employee(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    _organization_graph(db, company=company, employee_status="probation")

    response = client.patch(
        company_url(company.id),
        headers=superuser_token_headers,
        json={"is_active": False},
    )

    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert detail["code"] == "deactivate_blocked"
    assert "无法停用" in detail["message"]
    assert detail["field_errors"] == {
        "is_active": "存在启用中的下级部门、岗位、成本中心或在职/试用期员工"
    }
    assert detail["blocker_count"] == 4
    assert [blocker["type"] for blocker in detail["blockers"]] == [
        "department",
        "position",
        "cost_center",
        "employee",
    ]

    still_active = client.get(
        company_url(company.id), headers=superuser_token_headers
    ).json()
    assert still_active["is_active"] is True


def test_deactivate_company_allows_inactive_organization_and_resigned_employees(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    dept = create_department(db, company=company, is_active=False)
    position = create_position(db, company=company, is_active=False)
    cost_center = create_cost_center(db, company=company, is_active=False)
    create_employee(
        db,
        dept=dept,
        position=position,
        cost_org=cost_center,
        status=EmployeeStatus.RESIGNED,
        hire_date=datetime(2025, 1, 6, tzinfo=UTC).date(),
        resign_date=datetime(2025, 12, 31, tzinfo=UTC).date(),
    )

    response = client.patch(
        company_url(company.id),
        headers=superuser_token_headers,
        json={"is_active": False},
    )

    assert response.status_code == 200, response.text
    assert response.json()["is_active"] is False


def test_reactivating_a_company_succeeds(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    created = _create_company(client, superuser_token_headers, is_active=False)

    response = client.patch(
        company_url(created["id"]),
        headers=superuser_token_headers,
        json={"is_active": True},
    )

    assert response.status_code == 200, response.text
    assert response.json()["is_active"] is True
