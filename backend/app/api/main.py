from fastapi import APIRouter

from app.api.routes import (
    companies,
    cost_centers,
    departments,
    employees,
    login,
    positions,
    private,
    users,
    utils,
)
from app.api.routes.attendance import (
    holidays,
    months,
    rules,
    schedule_plans,
    shifts,
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(companies.router)
api_router.include_router(departments.router)
api_router.include_router(positions.router)
api_router.include_router(cost_centers.router)
api_router.include_router(employees.router)
api_router.include_router(shifts.router)
api_router.include_router(rules.router)
api_router.include_router(holidays.router)
api_router.include_router(months.router)
api_router.include_router(schedule_plans.router)
api_router.include_router(utils.router)


if settings.FASTAPI_ENV == "development":
    api_router.include_router(private.router)
