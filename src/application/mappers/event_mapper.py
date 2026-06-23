"""Mapper between Event domain entities and EventDTOs."""
from __future__ import annotations

from src.application.dtos.event_dtos import AvailabilityWindowDTO, EventDTO
from src.domain.entities.event import Event


class EventMapper:
    """Translates Event entities into transport-safe DTOs."""

    @staticmethod
    def to_dto(event: Event) -> EventDTO:
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
            card_type=event.card_type,
            availability_times=[
                AvailabilityWindowDTO(
                    starts_at=window.starts_at, ends_at=window.ends_at
                )
                for window in event.availability_times
            ],
        )
