"""Pydantic request/response schemas for the session endpoints.

Schema validation (shape, types) is allowed here; business validation is
not — that lives in the domain.
"""
from __future__ import annotations

from datetime import datetime
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


class SessionSummaryResponse(BaseModel):
    session_id: str
    location: Optional[str] = None
    distance: Optional[float] = None
    time_range: Optional[str] = None
    created_at: datetime
    ended_at: Optional[datetime] = None
    swipe_count: int
    yes_count: int


class SessionListResponse(BaseModel):
    # A user's past sessions, most recent first.
    sessions: List[SessionSummaryResponse]


class SessionDetailResponse(BaseModel):
    session_id: str
    location: Optional[str] = None
    distance: Optional[float] = None
    time_range: Optional[str] = None
    created_at: datetime
    ended_at: Optional[datetime] = None
    swipe_count: int
    # The compiled yes list: the cards the user swiped yes, in swipe order.
    yes: List[Dict[str, Any]]
