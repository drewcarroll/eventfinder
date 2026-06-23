"""Pydantic request/response schemas for session and swipe endpoints.

Schema validation (shape, types) is allowed here; business validation is
not — that lives in the domain.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class StartSessionRequest(BaseModel):
    location: Optional[str] = Field(
        None, description="Where the user is searching"
    )
    distance: Optional[float] = Field(
        None, gt=0, description="Max search radius in kilometres"
    )
    time_range: Optional[str] = Field(
        None, description="The time window the feed was built for"
    )


class StartSessionResponse(BaseModel):
    session_id: str


class SwipeRequest(BaseModel):
    card_data: Dict[str, Any] = Field(
        ..., description="Snapshot of the card the user acted on"
    )
    decision: str = Field(..., description="like | pass | super_like")


class SwipeResponse(BaseModel):
    swipe_id: str
    interested: bool


class EndSessionResponse(BaseModel):
    session_id: str
    ended_at: datetime
    swipe_count: int
