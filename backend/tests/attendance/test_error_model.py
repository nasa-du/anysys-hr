"""Shared error envelope extensions for attendance."""

import asyncio
import json
import uuid
from typing import Any

import pytest
from pydantic import ValidationError
from starlette.requests import Request

from app.core.errors import (
    Blocker,
    DomainError,
    domain_error_handler,
    translate_validation_error,
)
from app.services.attendance.errors import AttendanceErrorCode

SPEC_CODES = {
    "not_found",
    "cross_company",
    "invalid_reference",
    "inactive_reference",
    "referenced",
    "deactivate_blocked",
    "activation_blocked",
    "duplicate_code",
    "invalid_time_range",
    "invalid_scope",
    "schedule_conflict",
    "schedule_expansion_blocked",
    "plan_archived",
    "employee_out_of_range",
    "roster_entry_not_manual",
    "roster_batch_invalid",
    "month_confirmed",
    "month_locked",
    "month_not_calculated",
    "month_stale",
    "invalid_month_transition",
    "calc_in_progress",
    "calc_run_failed",
    "adjustment_conflict",
    "duplicate_holiday",
    "holiday_conflict",
    "import_parse_failed",
    "missing_required_column",
    "sheet_required",
    "preview_expired",
    "import_commit_conflict",
    "no_valid_rows",
    "batch_not_preview",
    "batch_not_revocable",
    "file_too_large",
    "unsupported_file_type",
}


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/attendance/imports",
            "headers": [],
            "query_string": b"",
        }
    )


def _response_body(response: Any) -> dict[str, Any]:
    return json.loads(response.body)


def test_attendance_error_codes_match_the_contract() -> None:
    assert {code.value for code in AttendanceErrorCode} == SPEC_CODES


def test_blocker_type_covers_attendance_references() -> None:
    for blocker_type in ("shift", "schedule_plan", "roster_entry"):
        blocker = Blocker(
            type=blocker_type,
            id=uuid.uuid7(),
            code="ADM",
            label="ADM 行政班",
        )
        assert blocker.type == blocker_type

    with pytest.raises(ValidationError):
        Blocker(type="item", id=uuid.uuid7(), code="X", label="不存在")


def test_extra_forbidden_stays_translated_to_chinese() -> None:
    assert (
        translate_validation_error(
            {"type": "extra_forbidden", "msg": "Extra inputs are not permitted"}
        )
        == "该字段不可修改"
    )


@pytest.mark.parametrize(
    ("code", "expected_status"),
    [
        ("not_found", 404),
        ("file_too_large", 413),
        ("unsupported_file_type", 415),
        ("import_parse_failed", 409),
        ("calc_in_progress", 409),
    ],
)
def test_domain_error_status_codes(code: str, expected_status: int) -> None:
    assert DomainError(code, "提示").status_code == expected_status


def test_attendance_error_enum_interoperates_with_domain_error() -> None:
    error = DomainError(AttendanceErrorCode.FILE_TOO_LARGE, "文件过大")

    assert error.code == "file_too_large"
    assert error.status_code == 413


@pytest.mark.parametrize(
    ("code", "expected_status"),
    [("file_too_large", 413), ("unsupported_file_type", 415)],
)
def test_upload_errors_use_the_error_envelope(code: str, expected_status: int) -> None:
    response = asyncio.run(
        domain_error_handler(_request(), DomainError(code, "文件不符合要求"))
    )

    assert response.status_code == expected_status
    assert _response_body(response) == {
        "detail": {"code": code, "message": "文件不符合要求"}
    }
