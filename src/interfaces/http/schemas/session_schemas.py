"""Pydantic request/response schemas for the session save endpoint.

Schema validation (shape, types) is allowed here; business validation is
not — that lives in the domain.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SwipeDecisionRequest(BaseModel):
    card_data: Dict[str, Any] = Field(
        ..., description="Snapshot of the card the user acted on"
    )
    decision: str = Field(..., description="like | pass | super_like")


class SaveSessionRequest(BaseModel):
    location: Optional[str] = Field(
        None, description="Where the user was searching"
    )
    distance: Optional[float] = Field(
        None, gt=0, description="Search radius in kilometres"
    )
    time_range: Optional[str] = Field(
        None, description="The time window the feed was built for"
    )
    swipes: List[SwipeDecisionRequest] = Field(
        default_factory=list, description="Every decision made this run"
    )


class SaveSessionResponse(BaseModel):
    session_id: str
    # The compiled yes list: the cards the user swiped yes, in swipe order.
    yes: List[Dict[str, Any]]
