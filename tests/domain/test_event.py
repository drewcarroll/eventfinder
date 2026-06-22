from datetime import datetime, timedelta

import pytest

from src.domain.entities.event import Event
from src.domain.exceptions import BusinessRuleViolation


def _event(**overrides):
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


def test_event_requires_title():
    with pytest.raises(BusinessRuleViolation):
        _event(title="  ")


def test_event_cannot_end_before_start():
    with pytest.raises(BusinessRuleViolation):
        _event(ends_at=datetime(2029, 1, 1))


def test_is_upcoming():
    event = _event()
    assert event.is_upcoming(datetime(2029, 12, 31))
    assert not event.is_upcoming(datetime(2030, 1, 2))


def test_matches_category_is_case_insensitive():
    assert _event().matches_category("MUSIC")
