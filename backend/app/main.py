from pathlib import Path

import sentry_sdk
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings
from app.core.errors import validation_exception_handler

FRONTEND_DIR = Path(__file__).parent / "frontend"


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


is_development = settings.FASTAPI_ENV == "development"

if settings.SENTRY_DSN and not is_development:
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs" if is_development else None,
    redoc_url="/redoc" if is_development else None,
    generate_unique_id_function=custom_generate_unique_id,
)

app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_HOST],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

if not is_development:

    @app.get("/docs", include_in_schema=False, tags=["docs"])
    @app.get("/redoc", include_in_schema=False, tags=["docs"])
    def docs_not_found() -> None:
        raise HTTPException(status_code=404, detail="页面不存在")


app.frontend("/", directory=FRONTEND_DIR)
