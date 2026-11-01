import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import SessionDep, get_current_user
from app.core.errors import ErrorResponse
from app.models import Message
from app.schemas_basic import (
    CompaniesPublic,
    CompanyCreate,
    CompanyPublic,
    CompanyUpdate,
)
from app.services import companies as company_service

router = APIRouter(
    prefix="/companies",
    tags=["companies"],
    dependencies=[Depends(get_current_user)],
)

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
}

Skip = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=500)]
Keyword = Annotated[str | None, Query(max_length=100)]


@router.get("/", response_model=CompaniesPublic, responses=ERROR_RESPONSES)
def read_companies(
    session: SessionDep,
    skip: Skip = 0,
    limit: Limit = 100,
    keyword: Keyword = None,
    is_active: bool | None = None,
) -> Any:
    """List companies ordered by business code."""
    return company_service.list_companies(
        session,
        skip=skip,
        limit=limit,
        keyword=keyword,
        is_active=is_active,
    )


@router.post(
    "/",
    response_model=CompanyPublic,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
def create_company(session: SessionDep, company_in: CompanyCreate) -> Any:
    """Create a company; business codes are uppercased and immutable."""
    return company_service.create_company(session, company_in)


@router.get("/{company_id}", response_model=CompanyPublic, responses=ERROR_RESPONSES)
def read_company(session: SessionDep, company_id: uuid.UUID) -> Any:
    """Get one company by id."""
    return company_service.get_company_or_404(session, company_id)


@router.patch("/{company_id}", response_model=CompanyPublic, responses=ERROR_RESPONSES)
def update_company(
    session: SessionDep, company_id: uuid.UUID, company_in: CompanyUpdate
) -> Any:
    """Update a company; the business code cannot change."""
    return company_service.update_company(session, company_id, company_in)


@router.delete("/{company_id}", response_model=Message, responses=ERROR_RESPONSES)
def delete_company(session: SessionDep, company_id: uuid.UUID) -> Any:
    """Hard delete an unreferenced company."""
    return company_service.delete_company(session, company_id)
