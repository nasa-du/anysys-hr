import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import SessionDep, get_current_user
from app.core.errors import ErrorResponse
from app.enums import EmployeeStatus
from app.schemas_basic import (
    EmployeeCreate,
    EmployeePublic,
    EmployeesPublic,
    EmployeeUpdate,
)
from app.services import employees as employee_service

router = APIRouter(
    prefix="/employees",
    tags=["employees"],
    dependencies=[Depends(get_current_user)],
)

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
}

Skip = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=500)]
Keyword = Annotated[str | None, Query(max_length=100)]


@router.get("/", response_model=EmployeesPublic, responses=ERROR_RESPONSES)
def read_employees(
    session: SessionDep,
    company_id: uuid.UUID | None = None,
    dept_id: uuid.UUID | None = None,
    position_id: uuid.UUID | None = None,
    cost_org_id: uuid.UUID | None = None,
    unassigned_cost_org: bool = False,
    status_filter: Annotated[list[EmployeeStatus] | None, Query(alias="status")] = None,
    keyword: Keyword = None,
    skip: Skip = 0,
    limit: Limit = 100,
) -> Any:
    """List employees ordered by employee number then name."""
    return employee_service.list_employees(
        session,
        company_id=company_id,
        dept_id=dept_id,
        position_id=position_id,
        cost_org_id=cost_org_id,
        unassigned_cost_org=unassigned_cost_org,
        statuses=status_filter,
        keyword=keyword,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/",
    response_model=EmployeePublic,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
def create_employee(session: SessionDep, employee_in: EmployeeCreate) -> Any:
    """Create an employee; the number is globally unique and immutable."""
    return employee_service.create_employee(session, employee_in)


@router.get("/{employee_id}", response_model=EmployeePublic, responses=ERROR_RESPONSES)
def read_employee(session: SessionDep, employee_id: uuid.UUID) -> Any:
    """Get one employee by id."""
    return employee_service.get_employee(session, employee_id)


@router.patch(
    "/{employee_id}", response_model=EmployeePublic, responses=ERROR_RESPONSES
)
def update_employee(
    session: SessionDep, employee_id: uuid.UUID, employee_in: EmployeeUpdate
) -> Any:
    """Update an employee, enforcing the lifecycle and assignment rules."""
    return employee_service.update_employee(session, employee_id, employee_in)
