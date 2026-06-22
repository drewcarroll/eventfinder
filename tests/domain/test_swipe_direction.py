import pytest

from src.domain.exceptions import InvalidValueError
from src.domain.value_objects.swipe_direction import SwipeDirection


def test_from_str_parses_valid_value():
    assert SwipeDirection.from_str("LIKE") is SwipeDirection.LIKE


def test_from_str_rejects_invalid_value():
    with pytest.raises(InvalidValueError):
        SwipeDirection.from_str("maybe")


def test_like_and_super_like_are_positive():
    assert SwipeDirection.LIKE.is_positive
    assert SwipeDirection.SUPER_LIKE.is_positive
    assert not SwipeDirection.PASS.is_positive
