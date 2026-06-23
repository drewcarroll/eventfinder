from datetime import datetime

import pytest

from src.domain.exceptions import InvalidValueError
from src.domain.value_objects.availability_window import AvailabilityWindow


def _window(start_hour: int, end_hour: int) -> AvailabilityWindow:
    return AvailabilityWindow(
        starts_at=datetime(2030, 6, 15, start_hour),
        ends_at=datetime(2030, 6, 15, end_hour),
    )


def test_rejects_window_ending_before_it_starts():
    with pytest.raises(InvalidValueError):
        AvailabilityWindow(
            starts_at=datetime(2030, 6, 15, 22),
            ends_at=datetime(2030, 6, 15, 18),
        )


def test_overlaps_when_ranges_intersect():
    window = _window(18, 22)
    assert window.overlaps(
        datetime(2030, 6, 15, 20), datetime(2030, 6, 15, 23)
    )


def test_overlaps_is_inclusive_at_the_boundary():
    window = _window(18, 22)
    # Range that just touches the window's end.
    assert window.overlaps(
        datetime(2030, 6, 15, 22), datetime(2030, 6, 15, 23)
    )


def test_does_not_overlap_disjoint_range():
    window = _window(18, 22)
    assert not window.overlaps(
        datetime(2030, 6, 16, 18), datetime(2030, 6, 16, 22)
    )
