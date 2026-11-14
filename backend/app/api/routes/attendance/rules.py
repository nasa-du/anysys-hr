import uuid
from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import SessionDep, attendance_access
from app.core.errors import ErrorResponse
from app.schemas_attendance.core import AttendanceRulePublic, AttendanceRuleUpdate
from app.services.attendance import rules as rule_service

router = APIRouter(
    prefix="/attendance/rules",
    tags=["attendance-rules"],
    dependencies=[Depends(attendance_access)],
)

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
}


@router.get("/", response_model=AttendanceRulePublic, responses=ERROR_RESPONSES)
def read_company_rule(session: SessionDep, company_id: uuid.UUID) -> Any:
    """Read the company default rule; an absent row means system defaults."""
    return rule_service.get_company_rule(session, company_id)


@router.put("/", response_model=AttendanceRulePublic, responses=ERROR_RESPONSES)
def update_company_rule(
    session: SessionDep,
    company_id: uuid.UUID,
    rule_in: AttendanceRuleUpdate,
) -> Any:
    """Create the first company rule row or update the supplied fields."""
    return rule_service.update_company_rule(session, company_id, rule_in)
