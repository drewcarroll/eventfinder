from datetime import datetime

from src.application.mappers.event_mapper import EventMapper
from src.domain.entities.event import Event
from src.domain.value_objects.geo_location import GeoLocation


def _event(**overrides) -> Event:
    base = dict(
        id="e1",
        title="Jazz Night",
        description="Live jazz",
        category="music",
        starts_at=datetime(2030, 1, 1, 20, 0),
        source_url="https://example.com",
    )
    base.update(overrides)
    return Event(**base)


def test_distance_km_is_none_without_origin():
    dto = EventMapper.to_dto(
        _event(location=GeoLocation(latitude=30.2672, longitude=-97.7431))
    )
    assert dto.distance_km is None


def test_distance_km_is_none_when_card_has_no_location():
    origin = GeoLocation(latitude=30.2672, longitude=-97.7431)
    dto = EventMapper.to_dto(_event(location=None), origin=origin)
    assert dto.distance_km is None


def test_distance_km_computed_from_origin():
    origin = GeoLocation(latitude=30.2672, longitude=-97.7431)
    card_loc = GeoLocation(latitude=29.7604, longitude=-95.3698)
    dto = EventMapper.to_dto(_event(location=card_loc), origin=origin)
    assert dto.distance_km == origin.distance_km_to(card_loc)
