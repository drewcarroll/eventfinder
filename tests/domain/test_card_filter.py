from datetime import datetime

from src.domain.entities.event import Event
from src.domain.services.card_filter import CardFilter
from src.domain.value_objects.availability_window import AvailabilityWindow
from src.domain.value_objects.geo_location import GeoLocation

AUSTIN = GeoLocation(latitude=30.2672, longitude=-97.7431)


def _card(card_id, *, location=None, windows=None, starts_at=None):
    return Event(
        id=card_id,
        title=f"Card {card_id}",
        description="",
        category="music",
        starts_at=starts_at or datetime(2030, 6, 15, 20),
        source_url="https://x.com",
        location=location,
        availability_times=windows or [],
    )


def test_excludes_cards_beyond_max_distance():
    near = _card("near", location=GeoLocation(30.27, -97.74))
    far = _card("far", location=GeoLocation(29.76, -95.37))  # ~235 km

    kept = CardFilter().filter(
        [near, far], origin=AUSTIN, max_distance_km=50
    )

    assert [c.id for c in kept] == ["near"]


def test_location_less_cards_survive_distance_filter():
    # Distance is unknown for a card with no location; it is not excluded.
    located = _card("located", location=GeoLocation(29.76, -95.37))
    no_location = _card("activity", location=None)

    kept = CardFilter().filter(
        [located, no_location], origin=AUSTIN, max_distance_km=50
    )

    assert [c.id for c in kept] == ["activity"]


def test_distance_filter_skipped_without_origin_or_radius():
    far = _card("far", location=GeoLocation(29.76, -95.37))

    # No origin: nothing to measure from.
    assert CardFilter().filter([far], max_distance_km=50) == [far]
    # No radius: no bound to apply.
    assert CardFilter().filter([far], origin=AUSTIN) == [far]


def test_excludes_cards_with_no_window_in_time_range():
    in_range = _card(
        "in",
        windows=[
            AvailabilityWindow(
                datetime(2030, 6, 15, 9), datetime(2030, 6, 15, 17)
            )
        ],
    )
    out_of_range = _card(
        "out",
        windows=[
            AvailabilityWindow(
                datetime(2030, 7, 1, 9), datetime(2030, 7, 1, 17)
            )
        ],
    )

    kept = CardFilter().filter(
        [in_range, out_of_range],
        starts_after=datetime(2030, 6, 10),
        starts_before=datetime(2030, 6, 20),
    )

    assert [c.id for c in kept] == ["in"]


def test_window_less_card_falls_back_to_start_time():
    inside = _card("inside", starts_at=datetime(2030, 6, 15))
    outside = _card("outside", starts_at=datetime(2030, 7, 15))

    kept = CardFilter().filter(
        [inside, outside],
        starts_after=datetime(2030, 6, 10),
        starts_before=datetime(2030, 6, 20),
    )

    assert [c.id for c in kept] == ["inside"]


def test_open_ended_lower_bound_only():
    early = _card("early", starts_at=datetime(2030, 1, 1))
    late = _card("late", starts_at=datetime(2030, 12, 1))

    kept = CardFilter().filter(
        [early, late], starts_after=datetime(2030, 6, 1)
    )

    assert [c.id for c in kept] == ["late"]


def test_no_filters_returns_all():
    cards = [_card("a"), _card("b", location=GeoLocation(29.76, -95.37))]
    assert CardFilter().filter(cards) == cards


def test_distance_and_time_filters_combine():
    keep = _card(
        "keep",
        location=GeoLocation(30.27, -97.74),
        windows=[
            AvailabilityWindow(
                datetime(2030, 6, 15, 9), datetime(2030, 6, 15, 17)
            )
        ],
    )
    too_far = _card(
        "far",
        location=GeoLocation(29.76, -95.37),
        windows=[
            AvailabilityWindow(
                datetime(2030, 6, 15, 9), datetime(2030, 6, 15, 17)
            )
        ],
    )
    wrong_time = _card(
        "late",
        location=GeoLocation(30.27, -97.74),
        windows=[
            AvailabilityWindow(
                datetime(2030, 7, 1, 9), datetime(2030, 7, 1, 17)
            )
        ],
    )

    kept = CardFilter().filter(
        [keep, too_far, wrong_time],
        origin=AUSTIN,
        max_distance_km=50,
        starts_after=datetime(2030, 6, 10),
        starts_before=datetime(2030, 6, 20),
    )

    assert [c.id for c in kept] == ["keep"]
