import pytest

from src.domain.exceptions import InvalidValueError
from src.domain.value_objects.geo_location import GeoLocation


def test_rejects_out_of_range_latitude():
    with pytest.raises(InvalidValueError):
        GeoLocation(latitude=91.0, longitude=0.0)


def test_distance_to_self_is_zero():
    here = GeoLocation(latitude=30.2672, longitude=-97.7431)
    assert here.distance_km_to(here) == pytest.approx(0.0, abs=1e-9)


def test_distance_between_known_points():
    # Austin, TX -> Houston, TX is ~235 km.
    austin = GeoLocation(latitude=30.2672, longitude=-97.7431)
    houston = GeoLocation(latitude=29.7604, longitude=-95.3698)
    assert austin.distance_km_to(houston) == pytest.approx(235.0, abs=5.0)


def test_distance_is_symmetric():
    a = GeoLocation(latitude=51.5074, longitude=-0.1278)
    b = GeoLocation(latitude=48.8566, longitude=2.3522)
    assert a.distance_km_to(b) == pytest.approx(b.distance_km_to(a))
