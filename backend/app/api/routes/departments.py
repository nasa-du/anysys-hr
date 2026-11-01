import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import SessionDep, get_current_user
from app.core.errors import ErrorResponse
from app.models import Message
from app.schemas_basic import (
    DepartmentCreate,
    DepartmentPublic,
    DepartmentsPublic,
    DepartmentTreePublic,
    DepartmentUpdate,
)
from app.services import departments as department_service

router = APIRouter(
    prefix="/departments",
    tags=["departments"],
    dependencies=[Depends(get_current_user)],
)

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
}

Skip = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=500)]
Keyword = Annotated[str | None, Query(max_length=100)]


@router.get("/", response_model=DepartmentsPublic, responses=ERROR_RESPONSES)
def read_departments(
    session: SessionDep,
    company_id: uuid.UUID,
    parent_id: uuid.UUID | None = None,
    keyword: Keyword = None,
    is_active: bool | None = None,
    skip: Skip = 0,
    limit: Limit = 100,
) -> Any:
    """List the company's departments ordered by order number and code."""
    return department_service.list_departments(
        session,
        company_id=company_id,
        parent_id=parent_id,
        keyword=keyword,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )


@router.get("/tree", response_model=DepartmentTreePublic, responses=ERROR_RESPONSES)
def read_department_tree(
    session: SessionDep,
    company_id: uuid.UUID,
    is_active: bool | None = None,
) -> Any:
    """Return the company's department tree with nested ``children`` arrays."""
    return department_service.tree_departments(
        session, company_id=company_id, is_active=is_active
    )


@router.post(
    "/",
    response_model=DepartmentPublic,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
def create_department(session: SessionDep, department_in: DepartmentCreate) -> Any:
    """Create a department; the code and company cannot change afterwards."""
    return department_service.create_department(session, department_in)


@router.get(
    "/{department_id}", response_model=DepartmentPublic, responses=ERROR_RESPONSES
)
def read_department(session: SessionDep, department_id: uuid.UUID) -> Any:
    """Get one department by id."""
    return department_service.get_department(session, department_id)


@router.patch(
    "/{department_id}", response_model=DepartmentPublic, responses=ERROR_RESPONSES
)
def update_department(
    session: SessionDep,
    department_id: uuid.UUID,
    department_in: DepartmentUpdate,
) -> Any:
    """Update a department; structural changes follow the active rules."""
    return department_service.update_department(session, department_id, department_in)


@router.delete("/{department_id}", response_model=Message, responses=ERROR_RESPONSES)
def delete_department(session: SessionDep, department_id: uuid.UUID) -> Any:
    """Hard delete a department without children or employee references."""
    return department_service.delete_department(session, department_id)
