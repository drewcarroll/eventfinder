"""Session HTTP controller.

Saves a completed swiping run: the session and every swipe decision are
persisted in one request, and the compiled yes list is returned. Thin
adapter — validate input, call the use case, serialize output.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, status

from src.application.dtos.session_dtos import (
    SaveSessionInput,
    SwipeDecisionInput,
)
from src.application.exceptions import ResourceNotFoundError
from src.interfaces.http.dependencies import RequestScope, ScopeDep
from src.interfaces.http.schemas.session_schemas import (
    SaveSessionRequest,
    SaveSessionResponse,
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
