"""Mapper between Event domain entities and EventDTOs."""
from __future__ import annotations

from typing import Optional

from src.application.dtos.event_dtos import AvailabilityWindowDTO, EventDTO
from src.domain.entities.event import Event
from src.domain.value_objects.geo_location import GeoLocation


class EventMapper:
    """Translates Event entities into transport-safe DTOs."""

    @staticmethod
    def to_dto(
        event: Event, origin: Optional[GeoLocation] = None
    ) -> EventDTO:
        """Map an Event to its DTO. When ``origin`` (the user's search
        location) and the card's location are both known, the card's
        ``distance_km`` is computed; otherwise it is left ``None``."""
        distance_km: Optional[float] = None
        if origin is not None and event.location is not None:
            distance_km = origin.distance_km_to(event.location)
        return EventDTO(
            id=event.id,
            title=event.title,
            description=event.description,
            category=event.category,
            starts_at=event.starts_at,
            source_url=event.source_url,
            image_url=event.image_url,
            latitude=event.location.latitude if event.location else None,
            longitude=event.location.longitude if event.location else None,
            distance_km=distance_km,
            card_type=event.card_type,
            availability_times=[
                AvailabilityWindowDTO(
                    starts_at=window.starts_at, ends_at=window.ends_at
                )
                for window in event.availability_times
            ],
        )
