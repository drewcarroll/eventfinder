"""Anthropic Claude implementation of EventEnricherPort.

Uses the Anthropic SDK to generate concise, user-tailored descriptions.
The use case is unaware that Claude is the provider.
"""
from __future__ import annotations

from typing import List

from anthropic import AsyncAnthropic

from src.application.ports.event_enricher_port import EventEnricherPort
from src.domain.entities.event import Event
from src.domain.entities.user import User


class AnthropicEventEnricher(EventEnricherPort):
    """Enriches event descriptions with Claude."""

    def __init__(self, api_key: str, model: str):
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def enrich(self, events: List[Event], user: User) -> List[Event]:
        if not events:
            return events

        interests = ", ".join(user.preferred_categories) or "general events"
        for event in events:
            try:
                message = await self._client.messages.create(
                    model=self._model,
                    max_tokens=120,
                    messages=[
                        {
                            "role": "user",
                            "content": (
                                "Rewrite this event description in one "
                                f"engaging sentence for someone interested "
                                f"in {interests}.\n\n"
                                f"Title: {event.title}\n"
                                f"Description: {event.description}"
                            ),
                        }
                    ],
                )
                text = "".join(
                    block.text
                    for block in message.content
                    if getattr(block, "type", None) == "text"
                ).strip()
                if text:
                    event.description = text
            except Exception:
                # Enrichment is best-effort; never fail the feed on LLM error.
                continue
        return events
