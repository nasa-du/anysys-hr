import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import SessionDep, get_current_user
from app.core.errors import ErrorResponse
from app.models import Message
from app.schemas_basic import (
    PositionCreate,
    PositionPublic,
    PositionsPublic,
    PositionUpdate,
)
from app.services import positions as position_service

router = APIRouter(
    prefix="/positions",
    tags=["positions"],
    dependencies=[Depends(get_current_user)],
)

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
}

Skip = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=500)]
Keyword = Annotated[str | None, Query(max_length=100)]


@router.get("/", response_model=PositionsPublic, responses=ERROR_RESPONSES)
def read_positions(
    session: SessionDep,
    company_id: uuid.UUID,
    dept_id: uuid.UUID | None = None,
    keyword: Keyword = None,
    is_active: bool | None = None,
    skip: Skip = 0,
    limit: Limit = 100,
) -> Any:
    """List the company's positions ordered by order number and code."""
    return position_service.list_positions(
        session,
        company_id=company_id,
        dept_id=dept_id,
        keyword=keyword,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/",
    response_model=PositionPublic,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
def create_position(session: SessionDep, position_in: PositionCreate) -> Any:
    """Create a position; the code and company cannot change afterwards."""
    return position_service.create_position(session, position_in)


@router.get("/{position_id}", response_model=PositionPublic, responses=ERROR_RESPONSES)
def read_position(session: SessionDep, position_id: uuid.UUID) -> Any:
    """Get one position by id."""
    return position_service.get_position(session, position_id)


@router.patch(
    "/{position_id}", response_model=PositionPublic, responses=ERROR_RESPONSES
)
def update_position(
    session: SessionDep,
    position_id: uuid.UUID,
    position_in: PositionUpdate,
) -> Any:
    """Update a position; default-department changes follow the active rules."""
    return position_service.update_position(session, position_id, position_in)


@router.delete("/{position_id}", response_model=Message, responses=ERROR_RESPONSES)
def delete_position(session: SessionDep, position_id: uuid.UUID) -> Any:
    """Hard delete a position without employee references."""
    return position_service.delete_position(session, position_id)
