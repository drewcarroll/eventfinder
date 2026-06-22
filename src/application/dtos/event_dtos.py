"""DTOs for event-related use cases.

DTOs are the input/output contracts of use cases. They are plain data
holders and never expose domain entities directly to the interfaces layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass(frozen=True)
class EventDTO:
    """Output representation of an event."""

    id: str
    title: str
    description: str
    category: str
    starts_at: datetime
    source_url: str
    image_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


@dataclass(frozen=True)
class GetEventFeedInput:
    """Input for retrieving a personalized event feed."""

    user_id: str
    query: str
    limit: int = 20


@dataclass(frozen=True)
class GetEventFeedOutput:
    """Output for the event feed use case."""

    events: List[EventDTO] = field(default_factory=list)
