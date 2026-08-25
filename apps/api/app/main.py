from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.routes.agent import router as agent_router
from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.provider_health import router as provider_health_router
from app.api.routes.trips import router as trips_router
from app.auth.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
)
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    app.include_router(health_router)
    app.include_router(provider_health_router, prefix=settings.api_prefix)
    app.include_router(auth_router, prefix=settings.api_prefix)
    app.include_router(trips_router, prefix=settings.api_prefix)
    app.include_router(agent_router, prefix=settings.api_prefix)

    @app.exception_handler(AuthenticationError)
    async def authentication_error_handler(
        _request: object,
        exc: AuthenticationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={"detail": str(exc)},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(AuthorizationError)
    async def authorization_error_handler(
        _request: object,
        exc: AuthorizationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=403,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ResourceNotFoundError)
    async def resource_not_found_handler(
        _request: object,
        exc: ResourceNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"detail": str(exc)},
        )

    return app


app = create_app()
