"""Event HTTP controller.

Thin adapter: validate input -> call use case -> serialize output.
No business logic, no infrastructure access.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from src.application.dtos.event_dtos import GetEventFeedInput
from src.application.dtos.swipe_dtos import RecordSwipeInput
from src.application.exceptions import (
    ConflictError,
    ResourceNotFoundError,
)
from src.interfaces.http.dependencies import RequestScope, ScopeDep
from src.interfaces.http.schemas.event_schemas import (
    EventFeedResponse,
    EventResponse,
    SwipeRequest,
    SwipeResponse,
)

router = APIRouter(prefix="/api/v1", tags=["events"])


@router.get("/feed", response_model=EventFeedResponse)
async def get_feed(
    query: str = Query(..., min_length=1, description="What to search for"),
    limit: int = Query(20, ge=1, le=50),
    radius_km: Optional[float] = Query(
        None, gt=0, description="Max search radius in kilometres"
    ),
    starts_after: Optional[datetime] = Query(
        None, description="Only events starting at/after this instant"
    ),
    starts_before: Optional[datetime] = Query(
        None, description="Only events starting at/before this instant"
    ),
    scope: RequestScope = ScopeDep,
) -> EventFeedResponse:
    try:
        result = await scope.get_event_feed.execute(
            GetEventFeedInput(
                user_id=scope.user_id,
                query=query,
                limit=limit,
                radius_km=radius_km,
                starts_after=starts_after,
                starts_before=starts_before,
            )
        )
        await scope.commit()
    except ResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return EventFeedResponse(
        events=[
            EventResponse(
                id=e.id,
                title=e.title,
                description=e.description,
                category=e.category,
                starts_at=e.starts_at,
                source_url=e.source_url,
                image_url=e.image_url,
                latitude=e.latitude,
                longitude=e.longitude,
            )
            for e in result.events
        ]
    )


@router.post(
    "/swipes",
    response_model=SwipeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_swipe(
    body: SwipeRequest,
    scope: RequestScope = ScopeDep,
) -> SwipeResponse:
    try:
        result = await scope.record_swipe.execute(
            RecordSwipeInput(
                user_id=scope.user_id,
                event_id=body.event_id,
                direction=body.direction,
            )
        )
        await scope.commit()
    except ResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc

    return SwipeResponse(
        swipe_id=result.swipe_id, interested=result.interested
    )
