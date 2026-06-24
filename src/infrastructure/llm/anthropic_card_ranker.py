"""Anthropic Claude implementation of CardRankerPort.

Ranks a pool of candidate cards in a single LLM call: Claude scores each
compact candidate on quality, novelty, and fit to the user's preferred
categories, collapses duplicates, and returns the order to show them in.
All LLM and parsing detail is confined to this adapter. Any failure — a
provider error, unparseable output, or a partial ordering that drops
candidates — is re-raised as ``RankingUnavailableError`` so the use case
can fall back to its own deterministic scoring.
"""
from __future__ import annotations

import json
import logging
from typing import Any, List, Optional

from anthropic import AsyncAnthropic

from src.application.ports.card_ranker_port import (
    CardRankerPort,
    RankingUnavailableError,
    TimeWindow,
)
from src.domain.entities.event import Event
from src.domain.entities.user import User

_logger = logging.getLogger(__name__)

# Keep each candidate compact so ~40 cards rank in one call without risking
# a truncated response.
_MAX_DESCRIPTION = 200


class AnthropicCardRanker(CardRankerPort):
    """Ranks and de-duplicates candidate cards with Claude."""

    def __init__(
        self,
        api_key: str,
        model: str,
        client: Optional[AsyncAnthropic] = None,
    ):
        self._client = client or AsyncAnthropic(api_key=api_key)
        self._model = model

    async def rank(
        self,
        cards: List[Event],
        user: User,
        window: Optional[TimeWindow] = None,
    ) -> List[Event]:
        if not cards:
            return []

        prompt = self._build_prompt(cards, user, window)
        order = await self._request_ranking(prompt)
        ranked = self._reorder(cards, order)

        # A correct ranking reorders and may collapse duplicates, but never
        # silently loses a distinct offering. If the model's ordering covers
        # fewer distinct cards than we sent, treat it as a partial failure
        # and let the caller fall back rather than ship a thinned feed.
        expected = len({card.identity_key() for card in cards})
        if len(ranked) < expected:
            _logger.warning(
                "Ranking covered %d of %d distinct candidates; treating as "
                "a partial failure.",
                len(ranked),
                expected,
            )
            raise RankingUnavailableError(
                "ranking did not cover all candidates"
            )
        return ranked

    # -- Prompt ---------------------------------------------------------

    def _build_prompt(
        self,
        cards: List[Event],
        user: User,
        window: Optional[TimeWindow],
    ) -> str:
        candidates = [
            {
                "index": i,
                "title": card.title,
                "description": card.description[:_MAX_DESCRIPTION],
                "category": card.category,
                "card_type": card.card_type,
            }
            for i, card in enumerate(cards)
        ]
        interests = (
            ", ".join(user.preferred_categories)
            or "no stated preferences"
        )
        return (
            "You rank candidate cards for a personalized activity feed. "
            f"The user is interested in: {interests}. "
            f"{self._describe_window(window)}"
            "Order the candidates below from best to worst, judging each "
            "on:\n"
            "- quality: how appealing and well-formed the offering is;\n"
            "- novelty: prefer a varied feed over near-duplicate ideas;\n"
            "- fit: how well it matches the user's interests above.\n"
            "Collapse duplicates — when two candidates describe the same "
            "real-world offering, keep only the better one.\n\n"
            "Respond with ONLY a JSON array of the candidate index integers, "
            "best first, each index appearing at most once. Example: "
            "[3, 0, 7].\n\n"
            f"Candidates:\n{json.dumps(candidates)}"
        )

    @staticmethod
    def _describe_window(window: Optional[TimeWindow]) -> str:
        if not window:
            return ""
        starts_after, starts_before = window
        if starts_after is not None and starts_before is not None:
            return (
                "These cards are available between "
                f"{starts_after.isoformat()} and "
                f"{starts_before.isoformat()}. "
            )
        if starts_after is not None:
            return (
                "These cards are available on or after "
                f"{starts_after.isoformat()}. "
            )
        if starts_before is not None:
            return (
                "These cards are available on or before "
                f"{starts_before.isoformat()}. "
            )
        return ""

    # -- LLM call -------------------------------------------------------

    async def _request_ranking(self, prompt: str) -> List[Any]:
        """Call Claude and parse its JSON array of candidate indices.

        Re-raises any provider or parsing failure as
        ``RankingUnavailableError`` (logging a warning first) so failures are
        visible and the caller can fall back."""
        try:
            message = await self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:
            _logger.warning("Anthropic ranking request failed", exc_info=True)
            raise RankingUnavailableError("ranking request failed") from exc

        try:
            text = self._strip_fences(
                "".join(
                    block.text
                    for block in message.content
                    if getattr(block, "type", None) == "text"
                ).strip()
            )
            parsed = json.loads(text)
        except Exception as exc:
            _logger.warning(
                "Could not parse ranking response", exc_info=True
            )
            raise RankingUnavailableError(
                "unparseable ranking response"
            ) from exc

        if not isinstance(parsed, list) or not parsed:
            _logger.warning("Ranking response was not a non-empty list")
            raise RankingUnavailableError("ranking response was not a list")
        return parsed

    # -- Mapping --------------------------------------------------------

    def _reorder(self, cards: List[Event], order: List[Any]) -> List[Event]:
        """Map the model's index ordering back to Events, dropping invalid
        and repeated indices and collapsing cards that share an identity."""
        ranked: List[Event] = []
        seen_index: set[int] = set()
        seen_identity: set[str] = set()
        for raw_index in order:
            # ``bool`` is an ``int`` subclass — exclude it explicitly.
            if not isinstance(raw_index, int) or isinstance(raw_index, bool):
                continue
            if not 0 <= raw_index < len(cards):
                continue
            if raw_index in seen_index:
                continue
            seen_index.add(raw_index)
            card = cards[raw_index]
            identity = card.identity_key()
            if identity in seen_identity:
                continue
            seen_identity.add(identity)
            ranked.append(card)
        return ranked

    @staticmethod
    def _strip_fences(text: str) -> str:
        """Drop a leading ```json / ``` fence if the model wrapped its
        JSON in a Markdown code block."""
        if text.startswith("```"):
            lines = text.splitlines()
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            return "\n".join(lines).strip()
        return text
