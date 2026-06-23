"""FastAPI application factory.

Builds the ASGI app and mounts controllers. The use-case factory (the
composition root that wires infrastructure) is injected from the outside
via `app.state.use_case_factory`, keeping this module free of
infrastructure imports.
"""
from __future__ import annotations

from typing import Awaitable, Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.interfaces.http.controllers import (
    event_controller,
    health_controller,
    location_controller,
    user_controller,
)
from src.interfaces.http.dependencies import RequestScope

UseCaseFactory = Callable[[str], Awaitable[RequestScope]]


def create_app(
    use_case_factory: UseCaseFactory,
    cors_origins: list[str] | None = None,
    title: str = "Event Swiper API",
) -> FastAPI:
    app = FastAPI(title=title)
    app.state.use_case_factory = use_case_factory

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_controller.router)
    app.include_router(user_controller.router)
    app.include_router(event_controller.router)
    app.include_router(location_controller.router)
    return app
