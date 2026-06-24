"""Tests for the Anthropic card ranker.

A fake Anthropic client is injected so the LLM call path runs without
hitting the network. These cover the acceptance criteria: a pool of
candidates comes back as an ordered list, the prompt judges quality /
novelty / fit to the user's preferred categories, and any error or partial
result raises so the use case can fall back.
"""
import json
from datetime import datetime

import pytest

from src.application.ports.card_ranker_port import RankingUnavailableError
from src.domain.entities.event import CARD_TYPE_ACTIVITY, Event
from src.domain.entities.user import User
from src.infrastructure.llm.anthropic_card_ranker import AnthropicCardRanker


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


def _ranker(responder) -> tuple[AnthropicCardRanker, FakeAnthropic]:
    fake = FakeAnthropic(responder)
    ranker = AnthropicCardRanker(
        api_key="test", model="claude-test", client=fake
    )
    return ranker, fake


def _user() -> User:
    return User(id="u1", email="a@b.com", preferred_categories=["jazz"])


def _card(index: int, title: str | None = None) -> Event:
    return Event(
        id=f"c{index}",
        title=title or f"Candidate {index}",
        description="A thing to do.",
        category="music",
        starts_at=datetime(2030, 6, 15, 20, 0),
        source_url="https://x.com",
        card_type=CARD_TYPE_ACTIVITY,
    )


@pytest.mark.asyncio
async def test_pool_of_candidates_comes_back_ordered():
    cards = [_card(i) for i in range(40)]
    # The model returns the candidates in reverse order.
    order = list(reversed(range(40)))
    ranker, _ = _ranker(lambda _: _Message(json.dumps(order)))

    ranked = await ranker.rank(cards, _user())

    assert len(ranked) == 40
    assert [c.id for c in ranked] == [f"c{i}" for i in reversed(range(40))]


@pytest.mark.asyncio
async def test_prompt_judges_quality_novelty_and_fit():
    cards = [_card(i) for i in range(3)]
    ranker, fake = _ranker(lambda _: _Message("[0, 1, 2]"))

    await ranker.rank(cards, _user())

    prompt = fake.messages.calls[0]["messages"][0]["content"]
    assert "quality" in prompt
    assert "novelty" in prompt
    assert "fit" in prompt
    # The user's preferred categories steer the "fit" judgement.
    assert "jazz" in prompt
    # Candidates are sent in the compact schema.
    assert '"card_type"' in prompt


@pytest.mark.asyncio
async def test_compact_candidates_carry_the_expected_fields():
    cards = [_card(0)]
    ranker, fake = _ranker(lambda _: _Message("[0]"))

    await ranker.rank(cards, _user())

    prompt = fake.messages.calls[0]["messages"][0]["content"]
    payload = json.loads(prompt.split("Candidates:\n", 1)[1])
    assert payload[0].keys() == {
        "index",
        "title",
        "description",
        "category",
        "card_type",
    }


@pytest.mark.asyncio
async def test_window_context_is_included_when_supplied():
    cards = [_card(0)]
    ranker, fake = _ranker(lambda _: _Message("[0]"))

    await ranker.rank(
        cards,
        _user(),
        window=(datetime(2030, 6, 10), datetime(2030, 6, 20)),
    )

    prompt = fake.messages.calls[0]["messages"][0]["content"]
    assert "2030-06-10T00:00:00" in prompt
    assert "2030-06-20T00:00:00" in prompt


@pytest.mark.asyncio
async def test_duplicates_collapse_to_one():
    # Two candidates describing the same offering (same identity key).
    cards = [_card(0, "Jazz Night"), _card(1, "jazz night")]
    ranker, _ = _ranker(lambda _: _Message("[0, 1]"))

    ranked = await ranker.rank(cards, _user())

    # The duplicate collapses; one distinct offering in, one out.
    assert len(ranked) == 1
    assert ranked[0].id == "c0"


@pytest.mark.asyncio
async def test_empty_input_returns_empty_without_calling_the_model():
    ranker, fake = _ranker(lambda _: _Message("[]"))

    ranked = await ranker.rank([], _user())

    assert ranked == []
    assert fake.messages.calls == []


@pytest.mark.asyncio
async def test_provider_error_signals_fallback():
    def boom(_):
        raise RuntimeError("API down")

    cards = [_card(0)]
    ranker, _ = _ranker(boom)

    with pytest.raises(RankingUnavailableError):
        await ranker.rank(cards, _user())


@pytest.mark.asyncio
async def test_unparseable_response_signals_fallback():
    cards = [_card(0)]
    ranker, _ = _ranker(lambda _: _Message("not json"))

    with pytest.raises(RankingUnavailableError):
        await ranker.rank(cards, _user())


@pytest.mark.asyncio
async def test_partial_ordering_signals_fallback():
    # Three distinct candidates but the model only ranks one of them.
    cards = [_card(0), _card(1), _card(2)]
    ranker, _ = _ranker(lambda _: _Message("[2]"))

    with pytest.raises(RankingUnavailableError):
        await ranker.rank(cards, _user())


@pytest.mark.asyncio
async def test_invalid_indices_are_ignored_but_must_still_cover_candidates():
    cards = [_card(0), _card(1)]
    # Out-of-range and repeated indices are dropped; the valid ones still
    # cover both distinct candidates, so this succeeds.
    ranker, _ = _ranker(lambda _: _Message("[99, 1, 1, 0]"))

    ranked = await ranker.rank(cards, _user())

    assert [c.id for c in ranked] == ["c1", "c0"]
