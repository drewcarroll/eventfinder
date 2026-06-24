"""Location HTTP controller.

Thin adapter: validate input -> call use case -> serialize output.
No business logic, no infrastructure access.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from src.application.dtos.location_dtos import (
    ResolveLocationInput,
    SearchLocationsInput,
)
from src.application.exceptions import ResourceNotFoundError
from src.interfaces.http.dependencies import RequestScope, ScopeDep
from src.interfaces.http.schemas.location_schemas import (
    LocationSuggestionResponse,
    LocationSuggestionsResponse,
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


@router.get(
    "/locations/search", response_model=LocationSuggestionsResponse
)
async def search_locations(
    q: str = Query(
        ..., min_length=1, description="Partial location text to match"
    ),
    limit: int = Query(5, ge=1, le=10),
    scope: RequestScope = ScopeDep,
) -> LocationSuggestionsResponse:
    """Suggest candidate cities for the location type-ahead."""
    result = await scope.search_locations.execute(
        SearchLocationsInput(query=q, limit=limit)
    )
    return LocationSuggestionsResponse(
        suggestions=[
            LocationSuggestionResponse(
                latitude=s.latitude,
                longitude=s.longitude,
                display_name=s.display_name,
            )
            for s in result.suggestions
        ]
    )
