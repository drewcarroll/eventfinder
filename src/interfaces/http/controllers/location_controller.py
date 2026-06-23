"""Location HTTP controller.

Thin adapter: validate input -> call use case -> serialize output.
No business logic, no infrastructure access.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from src.application.dtos.location_dtos import ResolveLocationInput
from src.application.exceptions import ResourceNotFoundError
from src.interfaces.http.dependencies import RequestScope, ScopeDep
from src.interfaces.http.schemas.location_schemas import (
    ResolveLocationResponse,
)

router = APIRouter(prefix="/api/v1", tags=["locations"])


@router.get("/locations/resolve", response_model=ResolveLocationResponse)
async def resolve_location(
    q: str = Query(
        ..., min_length=1, description="Free-text location to resolve"
    ),
    scope: RequestScope = ScopeDep,
) -> ResolveLocationResponse:
    try:
        result = await scope.resolve_location.execute(
            ResolveLocationInput(query=q)
        )
    except ResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return ResolveLocationResponse(
        latitude=result.latitude,
        longitude=result.longitude,
        display_name=result.display_name,
    )
