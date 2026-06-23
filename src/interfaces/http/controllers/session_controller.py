"""Session HTTP controller.

Drives the swiping-run lifecycle: open a session, record swipes against it,
then close it. Thin adapter — validate input, call use case, serialize output.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, status

from src.application.dtos.session_dtos import (
    EndSessionInput,
    StartSessionInput,
)
from src.application.dtos.swipe_dtos import RecordSwipeInput
from src.application.exceptions import ConflictError, ResourceNotFoundError
from src.interfaces.http.dependencies import RequestScope, ScopeDep
from src.interfaces.http.schemas.session_schemas import (
    EndSessionResponse,
    StartSessionRequest,
    StartSessionResponse,
    SwipeRequest,
    SwipeResponse,
)

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.post(
    "",
    response_model=StartSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_session(
    body: StartSessionRequest,
    scope: RequestScope = ScopeDep,
) -> StartSessionResponse:
    try:
        result = await scope.start_session.execute(
            StartSessionInput(
                user_uid=scope.user_id,
                location=body.location,
                distance=body.distance,
                time_range=body.time_range,
            )
        )
        await scope.commit()
    except ResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return StartSessionResponse(session_id=result.session_id)


@router.post(
    "/{session_id}/swipes",
    response_model=SwipeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_swipe(
    session_id: str,
    body: SwipeRequest,
    scope: RequestScope = ScopeDep,
) -> SwipeResponse:
    try:
        result = await scope.record_swipe.execute(
            RecordSwipeInput(
                session_id=session_id,
                card_data=json.dumps(body.card_data),
                decision=body.decision,
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


@router.post("/{session_id}/end", response_model=EndSessionResponse)
async def end_session(
    session_id: str,
    scope: RequestScope = ScopeDep,
) -> EndSessionResponse:
    try:
        result = await scope.end_session.execute(
            EndSessionInput(session_id=session_id)
        )
        await scope.commit()
    except ResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return EndSessionResponse(
        session_id=result.session_id,
        ended_at=result.ended_at,
        swipe_count=result.swipe_count,
    )
