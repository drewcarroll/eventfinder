"""Pydantic request/response schemas for the HTTP boundary.

Schema validation (shape, types) is allowed here. Business validation is
not — that lives in the domain.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AvailabilityWindowResponse(BaseModel):
    starts_at: datetime
    ends_at: datetime


class EventResponse(BaseModel):
    id: str
    title: str
    description: str
    category: str
    starts_at: datetime
    source_url: str
    image_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance_km: Optional[float] = None
    card_type: str = "event"
    availability_times: List[AvailabilityWindowResponse] = Field(
        default_factory=list
    )


class EventFeedResponse(BaseModel):
    events: List[EventResponse]


class SwipeRequest(BaseModel):
    event_id: str = Field(..., min_length=1)
    direction: str = Field(..., description="like | pass | super_like")


class SwipeResponse(BaseModel):
    swipe_id: str
    interested: bool
