"""Payroll extensions to the shared error envelope."""

import asyncio
import json
import uuid
from typing import Any

import pytest
from pydantic import ValidationError
from starlette.requests import Request

from app.core.errors import (
    DOMAIN_STATUS_CODES,
    Blocker,
    DomainError,
    domain_error_handler,
)
from app.schemas_payroll.common import (
    ConsistencyViolationPublic,
    FormulaErrorPublic,
)
from app.services.common import (
    MAX_BLOCKERS,
    PAYROLL_MAX_BLOCKERS,
    BlockerQuery,
    collect_blockers,
)


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/payroll/months/2026-09/calculate",
            "headers": [],
            "query_string": b"",
        }
    )


def _response_body(response: Any) -> dict[str, Any]:
    return json.loads(response.body)


def test_blocker_type_covers_payroll_references() -> None:
    for blocker_type in (
        "compensation_composition",
        "calc_scheme",
        "workday_param",
        "salary_field_def",
        "payroll_global_param",
        "payroll_month",
        "payroll_import_batch",
    ):
        blocker = Blocker(
            type=blocker_type,
            id=uuid.uuid7(),
            code="C1",
            label="C1 示例",
        )
        assert blocker.type == blocker_type

    with pytest.raises(ValidationError):
        Blocker(type="item", id=uuid.uuid7(), code="X", label="不存在")


@pytest.mark.parametrize(
    ("code", "expected_status"),
    [
        ("not_found", 404),
        ("export_job_not_found", 404),
        ("export_expired", 410),
        ("file_too_large", 413),
        ("unsupported_file_type", 415),
        ("config_revision_conflict", 409),
    ],
)
def test_domain_error_status_codes(code: str, expected_status: int) -> None:
    assert DomainError(code, "提示").status_code == expected_status


def test_payroll_status_codes_are_registered() -> None:
    assert DOMAIN_STATUS_CODES["export_expired"] == 410
    assert DOMAIN_STATUS_CODES["export_job_not_found"] == 404


def test_error_detail_carries_formula_errors_and_violations() -> None:
    formula_error = FormulaErrorPublic(
        code="formula_syntax_error",
        message="公式语法不正确",
        field_key="net",
        position=2,
    )
    violation = ConsistencyViolationPublic(
        employee_id=uuid.uuid7(),
        employee_no="E001",
        employee_name="张三",
        field_key="net",
        check="net",
        expected="5000.00",
        actual="4900.00",
    )
    error = DomainError(
        "formula_invalid",
        "公式校验未通过",
        formula_errors=[formula_error],
        violations=[violation],
    )

    response = asyncio.run(domain_error_handler(_request(), error))
    body = _response_body(response)

    assert response.status_code == 409
    assert body["detail"]["formula_errors"][0]["code"] == "formula_syntax_error"
    assert body["detail"]["violations"][0]["expected"] == "5000.00"
    assert body["detail"]["violations"][0]["actual"] == "4900.00"


def test_error_envelope_omits_empty_payroll_lists() -> None:
    response = asyncio.run(
        domain_error_handler(
            _request(), DomainError("config_revision_conflict", "冲突")
        )
    )

    assert _response_body(response) == {
        "detail": {"code": "config_revision_conflict", "message": "冲突"}
    }


class _Result:
    def __init__(self, value: Any) -> None:
        self._value = value

    def one(self) -> Any:
        return self._value

    def all(self) -> Any:
        return self._value


class _CountStatement:
    def __init__(self, total: int) -> None:
        self.total = total


class _RowsStatement:
    def __init__(self, rows: list[tuple[uuid.UUID, str, str]]) -> None:
        self._rows = rows
        self._limit: int | None = None

    def limit(self, value: int) -> _RowsStatement:
        self._limit = value
        return self

    def all(self) -> list[tuple[uuid.UUID, str, str]]:
        if self._limit is None:
            return self._rows
        return self._rows[: self._limit]


class _FakeSession:
    def exec(self, statement: Any) -> _Result:
        if isinstance(statement, _CountStatement):
            return _Result(statement.total)
        assert isinstance(statement, _RowsStatement)
        return _Result(statement.all())


def _blocker_rows(count: int) -> list[tuple[uuid.UUID, str, str]]:
    return [(uuid.uuid7(), f"E{index:03d}", f"员工{index}") for index in range(count)]


def _blocker_query(blocker_type: str, count: int) -> BlockerQuery:
    return BlockerQuery(
        type=blocker_type,  # type: ignore[arg-type]
        count_statement=_CountStatement(count),  # type: ignore[arg-type]
        rows_statement=_RowsStatement(_blocker_rows(count)),
    )


def test_collect_blockers_defaults_to_twenty_entries() -> None:
    query = _blocker_query("employee", 25)

    total, blockers = collect_blockers(_FakeSession(), [query])  # type: ignore[arg-type]

    assert MAX_BLOCKERS == 20
    assert total == 25
    assert len(blockers) == 20


def test_collect_blockers_accepts_a_payroll_max_entries() -> None:
    assert PAYROLL_MAX_BLOCKERS == 100
    query = _blocker_query("employee", 150)

    total, blockers = collect_blockers(
        _FakeSession(),  # type: ignore[arg-type]
        [query],
        max_entries=100,
    )

    assert total == 150
    assert len(blockers) == 100


def test_collect_blockers_stops_across_query_types() -> None:
    queries = [
        _blocker_query("employee", 10),
        _blocker_query("payroll_month", 20),
    ]

    total, blockers = collect_blockers(
        _FakeSession(),  # type: ignore[arg-type]
        queries,
        max_entries=25,
    )

    assert total == 30
    assert len(blockers) == 25
    assert [blocker.type for blocker in blockers[:10]] == ["employee"] * 10
    assert [blocker.type for blocker in blockers[10:]] == ["payroll_month"] * 15
