"""SQLAlchemy implementation of EventRepository."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.event import Event
from src.domain.repositories.event_repository import EventRepository
from src.domain.value_objects.availability_window import AvailabilityWindow
from src.domain.value_objects.geo_location import GeoLocation
from src.infrastructure.persistence.models import EventModel, SwipeModel


class SqlEventRepository(EventRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, event: Event) -> None:
        model = await self._session.get(EventModel, event.id)
        if model is None:
            self._session.add(self._to_model(event))
        else:
            self._apply(model, event)
        await self._session.flush()

    async def get_by_id(self, event_id: str) -> Optional[Event]:
        result = await self._session.execute(
            select(EventModel).where(EventModel.id == event_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_unseen_for_user(
        self, user_id: str, limit: int
    ) -> List[Event]:
        swiped_subq = (
            select(SwipeModel.event_id)
            .where(SwipeModel.user_id == user_id)
            .scalar_subquery()
        )
        result = await self._session.execute(
            select(EventModel)
            .where(EventModel.id.not_in(swiped_subq))
            .limit(limit)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    @staticmethod
    def _to_model(event: Event) -> EventModel:
        return EventModel(
            id=event.id,
            title=event.title,
            description=event.description,
            category=event.category,
            starts_at=event.starts_at,
            ends_at=event.ends_at,
            source_url=event.source_url,
            image_url=event.image_url,
            latitude=event.location.latitude if event.location else None,
            longitude=event.location.longitude if event.location else None,
            card_type=event.card_type,
            availability_times=SqlEventRepository._dump_windows(
                event.availability_times
            ),
        )

    @staticmethod
    def _apply(model: EventModel, event: Event) -> None:
        model.title = event.title
        model.description = event.description
        model.category = event.category
        model.starts_at = event.starts_at
        model.ends_at = event.ends_at
        model.source_url = event.source_url
        model.image_url = event.image_url
        model.card_type = event.card_type
        model.availability_times = SqlEventRepository._dump_windows(
            event.availability_times
        )
        if event.location:
            model.latitude = event.location.latitude
            model.longitude = event.location.longitude

    @staticmethod
    def _to_entity(model: EventModel) -> Event:
        location = None
        if model.latitude is not None and model.longitude is not None:
            location = GeoLocation(model.latitude, model.longitude)
        return Event(
            id=model.id,
            title=model.title,
            description=model.description,
            category=model.category,
            starts_at=model.starts_at,
            ends_at=model.ends_at,
            source_url=model.source_url,
            image_url=model.image_url,
            location=location,
            card_type=model.card_type,
            availability_times=SqlEventRepository._load_windows(
                model.availability_times
            ),
        )

    @staticmethod
    def _dump_windows(windows: List[AvailabilityWindow]) -> str:
        return json.dumps(
            [
                {
                    "starts_at": w.starts_at.isoformat(),
                    "ends_at": w.ends_at.isoformat(),
                }
                for w in windows
            ]
        )

    @staticmethod
    def _load_windows(raw: Optional[str]) -> List[AvailabilityWindow]:
        if not raw:
            return []
        try:
            data: Any = json.loads(raw)
        except (ValueError, TypeError):
            return []
        if not isinstance(data, list):
            return []
        windows: List[AvailabilityWindow] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            try:
                windows.append(
                    AvailabilityWindow(
                        datetime.fromisoformat(item["starts_at"]),
                        datetime.fromisoformat(item["ends_at"]),
                    )
                )
            except (KeyError, ValueError, TypeError):
                continue
        return windows
