import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import SessionDep, get_current_user
from app.core.errors import ErrorResponse
from app.models import Message
from app.schemas_basic import (
    CostCenterCreate,
    CostCenterPublic,
    CostCentersPublic,
    CostCenterTreePublic,
    CostCenterUpdate,
)
from app.services import cost_centers as cost_center_service

router = APIRouter(
    prefix="/cost-centers",
    tags=["cost-centers"],
    dependencies=[Depends(get_current_user)],
)

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
}

Skip = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=500)]
Keyword = Annotated[str | None, Query(max_length=100)]


@router.get("/", response_model=CostCentersPublic, responses=ERROR_RESPONSES)
def read_cost_centers(
    session: SessionDep,
    company_id: uuid.UUID,
    parent_id: uuid.UUID | None = None,
    keyword: Keyword = None,
    is_active: bool | None = None,
    skip: Skip = 0,
    limit: Limit = 100,
) -> Any:
    """List the company's cost centers ordered by order number and code."""
    return cost_center_service.list_cost_centers(
        session,
        company_id=company_id,
        parent_id=parent_id,
        keyword=keyword,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )


@router.get("/tree", response_model=CostCenterTreePublic, responses=ERROR_RESPONSES)
def read_cost_center_tree(
    session: SessionDep,
    company_id: uuid.UUID,
    is_active: bool | None = None,
) -> Any:
    """Return the company's cost center tree with nested ``children`` arrays."""
    return cost_center_service.tree_cost_centers(
        session, company_id=company_id, is_active=is_active
    )


@router.post(
    "/",
    response_model=CostCenterPublic,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
def create_cost_center(session: SessionDep, cost_center_in: CostCenterCreate) -> Any:
    """Create a cost center; the code and company cannot change afterwards."""
    return cost_center_service.create_cost_center(session, cost_center_in)


@router.get(
    "/{cost_center_id}", response_model=CostCenterPublic, responses=ERROR_RESPONSES
)
def read_cost_center(session: SessionDep, cost_center_id: uuid.UUID) -> Any:
    """Get one cost center by id."""
    return cost_center_service.get_cost_center(session, cost_center_id)


@router.patch(
    "/{cost_center_id}", response_model=CostCenterPublic, responses=ERROR_RESPONSES
)
def update_cost_center(
    session: SessionDep,
    cost_center_id: uuid.UUID,
    cost_center_in: CostCenterUpdate,
) -> Any:
    """Update a cost center; structural changes follow the active rules."""
    return cost_center_service.update_cost_center(
        session, cost_center_id, cost_center_in
    )


@router.delete("/{cost_center_id}", response_model=Message, responses=ERROR_RESPONSES)
def delete_cost_center(session: SessionDep, cost_center_id: uuid.UUID) -> Any:
    """Hard delete a cost center without children or employee references."""
    return cost_center_service.delete_cost_center(session, cost_center_id)
