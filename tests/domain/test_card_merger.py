"""Domain tests for the unified card schema and merging.

Covers the AvailabilityWindow value object, Event identity/availability
behavior, and the CardMerger deduplication rule — all pure domain logic.
"""
from datetime import datetime

import pytest

from src.domain.entities.event import (
    CARD_TYPE_ACTIVITY,
    CARD_TYPE_EVENT,
    Event,
)
from src.domain.exceptions import InvalidValueError
from src.domain.services.card_merger import CardMerger
from src.domain.value_objects.availability_window import AvailabilityWindow


def _card(
    event_id: str,
    title: str,
    *,
    card_type: str = CARD_TYPE_EVENT,
    windows=None,
) -> Event:
    return Event(
        id=event_id,
        title=title,
        description="",
        category="music",
        starts_at=datetime(2030, 1, 1),
        source_url="https://x.com",
        card_type=card_type,
        availability_times=windows or [],
    )


def test_availability_window_rejects_end_before_start():
    with pytest.raises(InvalidValueError):
        AvailabilityWindow(
            starts_at=datetime(2030, 1, 2), ends_at=datetime(2030, 1, 1)
        )


def test_identity_key_normalizes_title():
    a = _card("1", "  Jazz   Night  ")
    b = _card("2", "jazz night")
    assert a.identity_key() == b.identity_key() == "jazz night"


def test_add_availability_windows_ignores_duplicates():
    window = AvailabilityWindow(datetime(2030, 1, 1), datetime(2030, 1, 1, 2))
    event = _card("1", "Show", windows=[window])
    event.add_availability_windows([window])
    assert event.availability_times == [window]


def test_merge_deduplicates_by_identity_key_keeping_first():
    web = _card("web", "Pottery Class")
    activity = _card("act", "pottery class", card_type=CARD_TYPE_ACTIVITY)
    other = _card("other", "Live Music")

    merged = CardMerger().merge([web, activity], [other])

    ids = [c.id for c in merged]
    assert ids == ["web", "other"]  # first occurrence wins


def test_merge_folds_availability_windows_into_survivor():
    win_a = AvailabilityWindow(datetime(2030, 1, 1), datetime(2030, 1, 1, 2))
    win_b = AvailabilityWindow(datetime(2030, 1, 2), datetime(2030, 1, 2, 2))
    primary = _card("p", "Gallery Opening", windows=[win_a])
    duplicate = _card("d", "gallery opening", windows=[win_b])

    merged = CardMerger().merge([primary], [duplicate])

    assert len(merged) == 1
    assert merged[0].availability_times == [win_a, win_b]
