"""Tests for the Anthropic idea verifier.

A fake Anthropic client is injected so the LLM call path runs without
hitting the network. These cover the contract: the model returns the indices
to keep, the verifier maps them back to cards (preserving order), and any
provider/parse failure degrades to returning the cards unchanged so the feed
never empties.
"""
import json
from datetime import datetime

import pytest

from src.domain.entities.event import CARD_TYPE_ACTIVITY, Event
from src.domain.value_objects.availability_window import AvailabilityWindow
from src.infrastructure.llm.anthropic_idea_verifier import (
    AnthropicIdeaVerifier,
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


def _verifier(responder) -> tuple[AnthropicIdeaVerifier, FakeAnthropic]:
    fake = FakeAnthropic(responder)
    verifier = AnthropicIdeaVerifier(
        api_key="test", model="claude-test", client=fake
    )
    return verifier, fake


_WINDOW = (datetime(2030, 6, 15, 18, 0), datetime(2030, 6, 16, 4, 0))


def _card(index: int) -> Event:
    return Event(
        id=f"c{index}",
        title=f"Idea {index}",
        description="A thing to do.",
        category="music",
        starts_at=datetime(2030, 6, 15, 20, 0),
        source_url="",
        card_type=CARD_TYPE_ACTIVITY,
        availability_times=[
            AvailabilityWindow(
                datetime(2030, 6, 15, 20, 0), datetime(2030, 6, 15, 23, 0)
            )
        ],
    )


@pytest.mark.asyncio
async def test_keeps_only_the_indices_the_model_returns():
    cards = [_card(i) for i in range(4)]
    verifier, _ = _verifier(lambda _: _Message(json.dumps([0, 2])))

    kept = await verifier.verify(cards, _WINDOW)

    assert [c.id for c in kept] == ["c0", "c2"]


@pytest.mark.asyncio
async def test_an_empty_keep_list_prunes_everything_for_a_small_pool():
    # Below the safety-floor threshold (8), an empty verdict is honored.
    cards = [_card(i) for i in range(3)]
    verifier, _ = _verifier(lambda _: _Message("[]"))

    kept = await verifier.verify(cards, _WINDOW)

    assert kept == []


@pytest.mark.asyncio
async def test_safety_floor_keeps_all_when_verdict_guts_a_large_pool():
    # Dropping more than half of a non-trivial pool is distrusted: keep all
    # rather than ship a near-empty feed.
    cards = [_card(i) for i in range(10)]
    verifier, _ = _verifier(lambda _: _Message(json.dumps([0, 1])))

    kept = await verifier.verify(cards, _WINDOW)

    assert [c.id for c in kept] == [f"c{i}" for i in range(10)]


@pytest.mark.asyncio
async def test_a_moderate_trim_of_a_large_pool_is_honored():
    cards = [_card(i) for i in range(10)]
    keep = json.dumps([0, 1, 2, 3, 4, 5, 6])
    verifier, _ = _verifier(lambda _: _Message(keep))

    kept = await verifier.verify(cards, _WINDOW)

    assert [c.id for c in kept] == [f"c{i}" for i in range(7)]


@pytest.mark.asyncio
async def test_out_of_range_and_duplicate_indices_are_ignored():
    cards = [_card(i) for i in range(2)]
    verifier, _ = _verifier(lambda _: _Message(json.dumps([0, 0, 9, -1])))

    kept = await verifier.verify(cards, _WINDOW)

    assert [c.id for c in kept] == ["c0"]


@pytest.mark.asyncio
async def test_provider_error_degrades_to_unchanged():
    cards = [_card(i) for i in range(3)]

    def boom(_):
        raise RuntimeError("provider down")

    verifier, _ = _verifier(boom)

    kept = await verifier.verify(cards, _WINDOW)

    assert [c.id for c in kept] == ["c0", "c1", "c2"]


@pytest.mark.asyncio
async def test_unparseable_response_degrades_to_unchanged():
    cards = [_card(i) for i in range(2)]
    verifier, _ = _verifier(lambda _: _Message("not json"))

    kept = await verifier.verify(cards, _WINDOW)

    assert [c.id for c in kept] == ["c0", "c1"]


@pytest.mark.asyncio
async def test_no_window_passes_through_without_calling_the_model():
    cards = [_card(i) for i in range(2)]

    def fail(_):  # pragma: no cover - must not be invoked
        raise AssertionError("model should not be called without a window")

    verifier, fake = _verifier(fail)

    kept = await verifier.verify(cards, (None, None))

    assert [c.id for c in kept] == ["c0", "c1"]
    assert fake.messages.calls == []


@pytest.mark.asyncio
async def test_empty_cards_pass_through_without_calling_the_model():
    def fail(_):  # pragma: no cover - must not be invoked
        raise AssertionError("model should not be called with no cards")

    verifier, fake = _verifier(fail)

    assert await verifier.verify([], _WINDOW) == []
    assert fake.messages.calls == []
