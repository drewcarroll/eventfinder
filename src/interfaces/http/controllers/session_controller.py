"""Session HTTP controller.

Saves a completed swiping run and serves a user's swiping history: the list
of past sessions and a single session's full detail. Thin adapter —
validate input, call the use case, serialize output.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, status

from src.application.dtos.session_dtos import (
    GetSessionDetailInput,
    ListSessionsInput,
    SaveSessionInput,
    SwipeDecisionInput,
)
from src.application.exceptions import ResourceNotFoundError
from src.interfaces.http.dependencies import RequestScope, ScopeDep
from src.interfaces.http.schemas.session_schemas import (
    SaveSessionRequest,
    SaveSessionResponse,
    SessionDetailResponse,
    SessionListResponse,
    SessionSummaryResponse,
)

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.post(
    "",
    response_model=SaveSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def save_session(
    body: SaveSessionRequest,
    scope: RequestScope = ScopeDep,
) -> SaveSessionResponse:
    """Persist a finished session for the authenticated user."""
    try:
        result = await scope.save_session.execute(
            SaveSessionInput(
                user_uid=scope.user_id,
                location=body.location,
                distance=body.distance,
                time_range=body.time_range,
                swipes=[
                    SwipeDecisionInput(
                        card_data=json.dumps(s.card_data),
                        decision=s.decision,
                    )
                    for s in body.swipes
                ],
            )
        )
        await scope.commit()
    except ResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return SaveSessionResponse(
        session_id=result.session_id,
        yes=[json.loads(card) for card in result.yes],
    )


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    scope: RequestScope = ScopeDep,
) -> SessionListResponse:
    """List the authenticated user's past sessions, most recent first."""
    result = await scope.list_sessions.execute(
        ListSessionsInput(user_uid=scope.user_id)
    )
    return SessionListResponse(
        sessions=[
            SessionSummaryResponse(
                session_id=s.session_id,
                location=s.location,
                distance=s.distance,
                time_range=s.time_range,
                created_at=s.created_at,
                ended_at=s.ended_at,
                swipe_count=s.swipe_count,
                yes_count=s.yes_count,
            )
            for s in result.sessions
        ]
    )


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: str,
    scope: RequestScope = ScopeDep,
) -> SessionDetailResponse:
    """Return one of the authenticated user's sessions in full."""
    try:
        result = await scope.get_session_detail.execute(
            GetSessionDetailInput(
                user_uid=scope.user_id, session_id=session_id
            )
        )
    except ResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return SessionDetailResponse(
        session_id=result.session_id,
        location=result.location,
        distance=result.distance,
        time_range=result.time_range,
        created_at=result.created_at,
        ended_at=result.ended_at,
        swipe_count=result.swipe_count,
        yes=[json.loads(card) for card in result.yes],
    )
