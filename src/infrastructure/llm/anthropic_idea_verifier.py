"""Anthropic Claude implementation of IdeaVerifierPort.

A single, token-light LLM call that acts as the feed's final correctness
gate: Claude is given the candidate cards and the requested time window and
returns the indices of the ones a person could genuinely do in that window,
applying real-world knowledge the deterministic filter lacks (typical
opening hours, whether a time-bound happening really lands in the window).

All LLM and parsing detail is confined to this adapter. It is best-effort:
on any provider error or unparseable response it returns the cards unchanged
so a flaky verifier never empties the feed.
"""
from __future__ import annotations

import json
import logging
from typing import Any, List, Optional

from anthropic import AsyncAnthropic

from src.application.ports.idea_verifier_port import (
    IdeaVerifierPort,
    TimeWindow,
)
from src.domain.entities.event import Event

_logger = logging.getLogger(__name__)

# Keep each candidate compact so the whole deck verifies in one call without
# risking a truncated response.
_MAX_DESCRIPTION = 160


class AnthropicIdeaVerifier(IdeaVerifierPort):
    """Confirms cards are doable within the window, with Claude."""

    def __init__(
        self,
        api_key: str,
        model: str,
        client: Optional[AsyncAnthropic] = None,
    ):
        self._client = client or AsyncAnthropic(api_key=api_key)
        self._model = model

    async def verify(
        self, cards: List[Event], window: TimeWindow
    ) -> List[Event]:
        starts_after, starts_before = window
        # Nothing to check, or no window to check against: pass through.
        if not cards or (starts_after is None and starts_before is None):
            return list(cards)

        prompt = self._build_prompt(cards, starts_after, starts_before)
        keep = await self._request_verdict(prompt)
        if keep is None:
            # Degrade: a failed verifier must not thin the feed.
            return list(cards)

        kept = [cards[i] for i in keep if 0 <= i < len(cards)]

        # Safety net against an over-eager verdict: the verifier is meant to
        # trim a few clear mismatches, not gut the feed. If it would drop more
        # than half of a non-trivial pool, distrust it and keep everything —
        # too few ideas is a worse failure than a couple of off-hours ones.
        if len(cards) >= 8 and len(kept) < len(cards) / 2:
            _logger.warning(
                "Verifier kept only %d of %d candidates — distrusting an "
                "over-aggressive verdict and keeping all.",
                len(kept),
                len(cards),
            )
            return list(cards)

        _logger.info(
            "Verifier kept %d of %d candidate(s) for the window.",
            len(kept),
            len(cards),
        )
        return kept

    # -- Prompt ---------------------------------------------------------

    def _build_prompt(
        self,
        cards: List[Event],
        starts_after: Any,
        starts_before: Any,
    ) -> str:
        candidates = [
            {
                "index": i,
                "title": card.title,
                "description": card.description[:_MAX_DESCRIPTION],
                "category": card.category,
                "availability_times": [
                    {
                        "starts_at": w.starts_at.isoformat(),
                        "ends_at": w.ends_at.isoformat(),
                    }
                    for w in card.availability_times
                ],
            }
            for i, card in enumerate(cards)
        ]
        after = starts_after.isoformat() if starts_after else "now"
        before = starts_before.isoformat() if starts_before else "the cutoff"
        return (
            "You are a light sanity check on a 'what can I do today?' feed. "
            "The window is local time from "
            f"{after} to {before} (later today into the early morning). "
            "Times are LOCAL ISO-8601 (no timezone).\n\n"
            "KEEP almost everything. Only drop a card when, by ordinary "
            "real-world knowledge, it is CLEARLY impossible in that window — "
            "e.g. a specific time-bound event whose stated date is plainly a "
            "different day, or a place that is unmistakably closed the entire "
            "window (a museum listed 9–5 when the window is 10 PM–4 AM). "
            "Everyday, flexible ideas (parks, walks, dessert, casual eats, "
            "bars at night) should almost always be KEPT. When in any doubt, "
            "KEEP it — dropping a good idea is worse than keeping a marginal "
            "one.\n\n"
            "Respond with ONLY a JSON array of the index integers to KEEP, "
            "each at most once. Example: [0, 1, 2, 4, 5].\n\n"
            f"Candidates:\n{json.dumps(candidates)}"
        )

    # -- LLM call -------------------------------------------------------

    async def _request_verdict(self, prompt: str) -> Optional[List[int]]:
        """Call Claude and parse its JSON array of indices to keep.

        Returns ``None`` (logging a warning first) on any provider or parsing
        failure so the caller can pass the cards through unchanged."""
        try:
            message = await self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception:
            _logger.warning(
                "Anthropic verification request failed", exc_info=True
            )
            return None

        try:
            text = self._strip_fences(
                "".join(
                    block.text
                    for block in message.content
                    if getattr(block, "type", None) == "text"
                ).strip()
            )
            parsed = json.loads(text)
        except Exception:
            _logger.warning(
                "Could not parse verification response", exc_info=True
            )
            return None

        if not isinstance(parsed, list):
            _logger.warning("Verification response was not a list")
            return None

        # ``bool`` is an ``int`` subclass — exclude it explicitly.
        keep: List[int] = []
        seen: set[int] = set()
        for raw in parsed:
            if not isinstance(raw, int) or isinstance(raw, bool):
                continue
            if raw in seen:
                continue
            seen.add(raw)
            keep.append(raw)
        return keep

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
