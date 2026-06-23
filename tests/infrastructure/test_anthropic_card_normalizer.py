"""Tests for activity generation in the Anthropic card normalizer.

A fake Anthropic client is injected so the LLM call path runs without
hitting the network. These cover the two acceptance criteria for generated
activity ideas: they conform to the unified card schema, and their count is
bounded.
"""
import json
from datetime import datetime

import pytest

from src.domain.entities.event import CARD_TYPE_ACTIVITY
from src.domain.entities.user import User
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


@pytest.mark.asyncio
async def test_llm_failure_degrades_to_empty():
    def boom(_):
        raise RuntimeError("API down")

    normalizer, _ = _normalizer(boom)

    activities = await normalizer.generate_activities("x", _user(), 5)

    assert activities == []
