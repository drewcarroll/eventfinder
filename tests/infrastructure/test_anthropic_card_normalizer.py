"""Tests for activity generation in the Anthropic card normalizer.

A fake Anthropic client is injected so the LLM call path runs without
hitting the network. These cover the two acceptance criteria for generated
activity ideas: they conform to the unified card schema, and their count is
bounded.
"""
import json
import logging
from datetime import date, datetime

import pytest

from src.domain.entities.event import CARD_TYPE_ACTIVITY, Event
from src.domain.entities.user import User
from src.domain.services.card_filter import CardFilter
from src.domain.value_objects.availability_window import AvailabilityWindow
from src.infrastructure.llm.anthropic_card_normalizer import (
    _MAX_ACTIVITIES,
    AnthropicCardNormalizer,
)


class _Block:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _Message:
    def __init__(self, text: str) -> None:
        self.content = [_Block(text)]


class _Messages:
    def __init__(self, responder) -> None:
        self._responder = responder
        self.calls: list = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responder(kwargs)


class FakeAnthropic:
    """Minimal stand-in for AsyncAnthropic exposing ``messages.create``."""

    def __init__(self, responder) -> None:
        self.messages = _Messages(responder)


def _normalizer(responder) -> tuple[AnthropicCardNormalizer, FakeAnthropic]:
    fake = FakeAnthropic(responder)
    normalizer = AnthropicCardNormalizer(
        api_key="test", model="claude-test", client=fake
    )
    return normalizer, fake


def _activities_json(n: int) -> str:
    return json.dumps(
        [
            {
                "title": f"Zilker Park spot {i}",
                "description": "A pleasant green space.",
                "category": "outdoors",
                "availability_times": [
                    {
                        "starts_at": "2030-06-15T09:00:00",
                        "ends_at": "2030-06-15T17:00:00",
                    }
                ],
            }
            for i in range(n)
        ]
    )


def _user() -> User:
    return User(id="u1", email="a@b.com", preferred_categories=["outdoors"])


@pytest.mark.asyncio
async def test_generated_activities_conform_to_card_schema():
    normalizer, _ = _normalizer(lambda _: _Message(_activities_json(3)))

    activities = await normalizer.generate_activities(
        "parks in Austin", _user(), 5
    )

    assert len(activities) == 3
    for card in activities:
        # Unified card schema: typed as an activity, valid identity/title,
        # a category, no source URL, and parsed availability windows.
        assert card.card_type == CARD_TYPE_ACTIVITY
        assert card.id
        assert card.title.strip()
        assert card.category
        assert card.source_url == ""
        assert card.availability_times
        assert all(
            isinstance(w, AvailabilityWindow) for w in card.availability_times
        )


@pytest.mark.asyncio
async def test_count_is_bounded_by_requested_limit():
    normalizer, _ = _normalizer(lambda _: _Message(_activities_json(20)))

    activities = await normalizer.generate_activities(
        "things to do", _user(), 3
    )

    # Even though the model returned 20, the requested limit caps the output.
    assert len(activities) == 3


@pytest.mark.asyncio
async def test_count_is_bounded_by_global_maximum():
    normalizer, _ = _normalizer(lambda _: _Message(_activities_json(50)))

    activities = await normalizer.generate_activities(
        "things to do", _user(), 1000
    )

    assert len(activities) == _MAX_ACTIVITIES


@pytest.mark.asyncio
async def test_zero_limit_makes_no_llm_call():
    normalizer, fake = _normalizer(lambda _: _Message(_activities_json(5)))

    activities = await normalizer.generate_activities("x", _user(), 0)

    assert activities == []
    assert fake.messages.calls == []


@pytest.mark.asyncio
async def test_prompt_is_location_grounded():
    normalizer, fake = _normalizer(lambda _: _Message(_activities_json(1)))

    await normalizer.generate_activities("hiking near Boulder", _user(), 3)

    prompt = fake.messages.calls[0]["messages"][0]["content"]
    # Grounded in the caller's location text and steered toward place-based
    # "things to do" that complement events.
    assert "hiking near Boulder" in prompt
    assert "trails" in prompt
    assert "complement" in prompt


@pytest.mark.asyncio
async def test_prompt_includes_time_window_and_radius():
    normalizer, fake = _normalizer(lambda _: _Message(_activities_json(1)))

    await normalizer.generate_activities(
        "parks in Austin",
        _user(),
        5,
        starts_after=datetime(2030, 6, 10, 9, 0),
        starts_before=datetime(2030, 6, 20, 22, 0),
        radius_km=25,
    )

    prompt = fake.messages.calls[0]["messages"][0]["content"]
    # The concrete window bounds, the radius, and the instruction to keep
    # availability_times inside the window are all present.
    assert "2030-06-10T09:00:00" in prompt
    assert "2030-06-20T22:00:00" in prompt
    assert "25 km" in prompt
    assert "availability_times that fall inside that window" in prompt


@pytest.mark.asyncio
async def test_prompt_omits_constraints_when_unbounded():
    normalizer, fake = _normalizer(lambda _: _Message(_activities_json(1)))

    await normalizer.generate_activities("parks in Austin", _user(), 5)

    prompt = fake.messages.calls[0]["messages"][0]["content"]
    # With no window or radius supplied, no constraint clause is injected.
    assert "km of that location" not in prompt
    assert "time window from" not in prompt


def _raw_web_event() -> Event:
    return Event(
        id="web1",
        title="Jazz at the Continental Club",
        # Raw scraped text: noisy, truncated, full of boilerplate.
        description=(
            "HOME | TICKETS | CONTACT  Cookie notice: we use cookies. "
            "Doors 8pm. Lorem ipsum dolor sit amet, consectetur..."
        ),
        category="music",
        starts_at=datetime(2030, 6, 15, 20, 0),
        source_url="https://x.com",
    )


@pytest.mark.asyncio
async def test_normalize_rewrites_description_from_scraped_content():
    raw = _raw_web_event()
    original = raw.description
    payload = json.dumps(
        [
            {
                "index": 0,
                "category": "live music",
                "description": "Nightly live jazz at a storied Austin club.",
                "starts_at": "2030-06-15T20:00:00",
                "availability_times": [],
            }
        ]
    )
    normalizer, _ = _normalizer(lambda _: _Message(payload))

    result = await normalizer.normalize([raw], _user())

    # The card carries the clean rewritten sentence, not the raw page text.
    assert result[0].description == "Nightly live jazz at a storied Austin club."
    assert result[0].description != original


@pytest.mark.asyncio
async def test_normalize_prompt_requests_a_rewritten_description():
    normalizer, fake = _normalizer(lambda _: _Message("[]"))

    await normalizer.normalize([_raw_web_event()], _user())

    prompt = fake.messages.calls[0]["messages"][0]["content"]
    assert "description" in prompt
    assert "rewritten from the scraped content" in prompt


@pytest.mark.asyncio
async def test_normalize_keeps_original_description_when_omitted():
    raw = _raw_web_event()
    original = raw.description
    payload = json.dumps([{"index": 0, "category": "music"}])
    normalizer, _ = _normalizer(lambda _: _Message(payload))

    result = await normalizer.normalize([raw], _user())

    # No description in the model output → leave the existing one untouched.
    assert result[0].description == original


def test_salvage_recovers_complete_objects_from_truncation():
    # Two complete objects (one with nested structure) then a cut-off third.
    truncated = '[{"a": 1}, {"b": {"c": 2}}, {"d": '

    salvaged = AnthropicCardNormalizer._salvage_truncated_array(truncated)

    assert salvaged == [{"a": 1}, {"b": {"c": 2}}]


def test_salvage_returns_none_when_nothing_is_whole():
    # First object never closes — nothing complete to recover.
    assert AnthropicCardNormalizer._salvage_truncated_array('[{"a": ') is None
    assert AnthropicCardNormalizer._salvage_truncated_array("garbage") is None


@pytest.mark.asyncio
async def test_truncated_array_yields_complete_entries(caplog):
    # Two whole activity objects followed by a third cut off mid-object,
    # exactly how an over-length response gets clipped at max_tokens.
    truncated = (
        '[{"title": "Zilker Park", "description": "Green space.", '
        '"category": "outdoors", "availability_times": [{"starts_at": '
        '"2030-06-15T09:00:00", "ends_at": "2030-06-15T17:00:00"}]}, '
        '{"title": "Barton Springs", "description": "Cold pool.", '
        '"category": "outdoors", "availability_times": [{"starts_at": '
        '"2030-06-15T08:00:00", "ends_at": "2030-06-15T20:00:00"}]}, '
        '{"title": "Mount Bonnell", "description": "Scenic over'
    )
    normalizer, _ = _normalizer(lambda _: _Message(truncated))

    with caplog.at_level(logging.WARNING):
        activities = await normalizer.generate_activities("austin", _user(), 5)

    # The two intact objects are recovered instead of the whole call failing.
    assert [a.title for a in activities] == ["Zilker Park", "Barton Springs"]
    assert "salvaged" in caplog.text.lower()


@pytest.mark.asyncio
async def test_unparseable_response_logs_warning(caplog):
    normalizer, _ = _normalizer(lambda _: _Message("not json at all"))

    with caplog.at_level(logging.WARNING):
        activities = await normalizer.generate_activities("x", _user(), 5)

    assert activities == []
    assert "could not parse json" in caplog.text.lower()


def test_parse_datetime_handles_all_three_shapes():
    parse = AnthropicCardNormalizer._parse_datetime

    # Full ISO-8601 (with and without offset) is unchanged / normalized to
    # naive UTC.
    assert parse("2030-06-15T09:00:00") == datetime(2030, 6, 15, 9, 0)
    assert parse("2030-06-15T09:00:00+00:00") == datetime(2030, 6, 15, 9, 0)
    # Date-only anchors to midnight.
    assert parse("2030-06-15") == datetime(2030, 6, 15, 0, 0)
    # Time-only anchors to the supplied date.
    assert parse("18:00", date(2030, 6, 15)) == datetime(2030, 6, 15, 18, 0)
    assert parse("18:00:00", date(2030, 6, 15)) == datetime(2030, 6, 15, 18, 0)
    # Garbage is still rejected.
    assert parse("not a time") is None


def test_time_only_end_anchors_to_window_start_date():
    normalizer, _ = _normalizer(lambda _: _Message("[]"))

    windows = normalizer._parse_windows(
        [{"starts_at": "2030-06-15T09:00:00", "ends_at": "18:00"}]
    )

    assert len(windows) == 1
    assert windows[0].starts_at == datetime(2030, 6, 15, 9, 0)
    # "18:00" carries no date; it inherits the start's date rather than
    # being dropped (which previously collapsed the whole window).
    assert windows[0].ends_at == datetime(2030, 6, 15, 18, 0)


@pytest.mark.asyncio
async def test_activity_with_time_only_windows_survives_the_filter():
    payload = json.dumps(
        [
            {
                "title": "Zilker Park",
                "description": "Green space.",
                "category": "outdoors",
                "availability_times": [
                    {"starts_at": "2030-06-15T09:00:00", "ends_at": "18:00"}
                ],
            }
        ]
    )
    normalizer, _ = _normalizer(lambda _: _Message(payload))

    activities = await normalizer.generate_activities("austin", _user(), 5)

    card = activities[0]
    # The window parsed instead of being dropped, so the card anchors to it
    # rather than falling back to "tomorrow".
    assert card.availability_times
    assert card.starts_at == datetime(2030, 6, 15, 9, 0)

    survivors = CardFilter().filter(
        [card],
        starts_after=datetime(2030, 6, 10),
        starts_before=datetime(2030, 6, 20),
    )
    assert survivors == [card]


@pytest.mark.asyncio
async def test_llm_failure_degrades_to_empty(caplog):
    def boom(_):
        raise RuntimeError("API down")

    normalizer, _ = _normalizer(boom)

    with caplog.at_level(logging.WARNING):
        activities = await normalizer.generate_activities("x", _user(), 5)

    assert activities == []
    # A real API failure is surfaced as a warning, not silently swallowed.
    assert "completion request failed" in caplog.text.lower()
