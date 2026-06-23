"""Anthropic Claude implementation of CardNormalizerPort.

Uses Claude to (1) normalize raw Tavily web results into the unified card
schema — inferring categories, start times, and availability windows — and
(2) generate complementary activity suggestions. All LLM and parsing
detail is confined to this adapter; the use case is unaware Claude is the
provider. Both operations are best-effort: on any failure they degrade
gracefully rather than breaking the feed.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

from anthropic import AsyncAnthropic

from src.application.ports.card_normalizer_port import CardNormalizerPort
from src.domain.entities.event import CARD_TYPE_ACTIVITY, Event
from src.domain.entities.user import User
from src.domain.value_objects.availability_window import AvailabilityWindow

_logger = logging.getLogger(__name__)

# Cap generated activity counts per call regardless of the requested feed
# size — activities complement web results, they don't replace them.
_MAX_ACTIVITIES = 20


class AnthropicCardNormalizer(CardNormalizerPort):
    """Normalizes web results and generates activities with Claude."""

    def __init__(
        self,
        api_key: str,
        model: str,
        client: Optional[AsyncAnthropic] = None,
    ):
        self._client = client or AsyncAnthropic(api_key=api_key)
        self._model = model

    async def normalize(self, raw: List[Event], user: User) -> List[Event]:
        if not raw:
            return raw

        items = [
            {
                "index": i,
                "title": event.title,
                "description": event.description[:500],
                "source_url": event.source_url,
            }
            for i, event in enumerate(raw)
        ]
        prompt = (
            "You normalize raw web search results into structured event "
            "cards. For each result below, infer a concise lowercase "
            "category, a start time in ISO 8601 if one can be determined, "
            "and availability_times: a list of {starts_at, ends_at} windows "
            "(ISO 8601) when the event or venue is available. Also write a "
            "clean one-sentence description (under 200 characters) that "
            "summarizes the offering in plain prose, rewritten from the "
            "scraped content — never copy raw page text, navigation, or "
            "boilerplate. Omit a field when it cannot be determined.\n\n"
            "Respond with ONLY a JSON array of objects with keys: index "
            "(int), category (string), description (string), starts_at "
            "(string or null), availability_times (array of {starts_at, "
            "ends_at}).\n\n"
            f"Results:\n{json.dumps(items)}"
        )

        # Up to ~20 results, each with category, start time, and availability
        # windows — give enough room that the JSON array isn't truncated
        # mid-object (which would fail to parse and silently skip enrichment).
        parsed = await self._complete_json(prompt, max_tokens=4096)
        if not isinstance(parsed, list):
            return raw

        for entry in parsed:
            if not isinstance(entry, dict):
                continue
            index = entry.get("index")
            if not isinstance(index, int) or not 0 <= index < len(raw):
                continue
            self._apply_normalization(raw[index], entry)
        return raw

    async def generate_activities(
        self,
        query: str,
        user: User,
        limit: int,
        starts_after: Optional[datetime] = None,
        starts_before: Optional[datetime] = None,
        radius_km: Optional[float] = None,
    ) -> List[Event]:
        count = max(0, min(limit, _MAX_ACTIVITIES))
        if count == 0:
            return []

        interests = ", ".join(user.preferred_categories) or "general"
        constraints = self._describe_constraints(
            starts_after, starts_before, radius_km
        )
        prompt = (
            f"Suggest up to {count} general things to do grounded in the "
            f'location described in "{query}". Favor durable, place-based '
            "activities a local could do on an ordinary day — parks, "
            "trails, scenic walks, gardens, viewpoints, museums, markets, "
            "and notable neighborhood spots. Do NOT suggest ticketed or "
            "one-off events; those are sourced separately and these should "
            f"complement them. Tailor choices to someone interested in "
            f"{interests}.\n\n"
            f"{constraints}"
            "For each, give a short title that names the "
            "specific place where possible, a one-sentence description, a "
            "lowercase category, and availability_times: a list of "
            "{starts_at, ends_at} windows (ISO 8601) when the activity is "
            "available.\n\n"
            "Respond with ONLY a JSON array of objects with keys: title "
            "(string), description (string), category (string), "
            "availability_times (array of {starts_at, ends_at})."
        )

        # Up to 20 activities with descriptions and availability windows; give
        # room to finish the JSON array rather than truncating mid-object.
        parsed = await self._complete_json(prompt, max_tokens=8192)
        if not isinstance(parsed, list):
            return []

        activities: List[Event] = []
        for entry in parsed[:count]:
            event = self._build_activity(entry)
            if event is not None:
                activities.append(event)
        return activities

    # -- Prompt helpers -------------------------------------------------

    @staticmethod
    def _describe_constraints(
        starts_after: Optional[datetime],
        starts_before: Optional[datetime],
        radius_km: Optional[float],
    ) -> str:
        """Render the distance + time-window constraints into a prompt
        fragment. Returns an empty string when nothing is constrained, or a
        sentence (or two) terminated by a blank line so it slots cleanly
        between the framing and the per-card instructions."""
        parts: List[str] = []
        if radius_km is not None:
            parts.append(
                f"Only suggest places within {radius_km:g} km of that "
                "location."
            )
        if starts_after is not None and starts_before is not None:
            parts.append(
                "Only suggest things available within the time window from "
                f"{starts_after.isoformat()} to {starts_before.isoformat()}, "
                "and emit availability_times that fall inside that window."
            )
        elif starts_after is not None:
            parts.append(
                "Only suggest things available on or after "
                f"{starts_after.isoformat()}, and emit availability_times "
                "that start at or after that time."
            )
        elif starts_before is not None:
            parts.append(
                "Only suggest things available on or before "
                f"{starts_before.isoformat()}, and emit availability_times "
                "that end at or before that time."
            )
        if not parts:
            return ""
        return " ".join(parts) + "\n\n"

    # -- LLM call -------------------------------------------------------

    async def _complete_json(self, prompt: str, max_tokens: int) -> Any:
        """Run a single completion and parse its JSON body, returning None
        when the response can't be used so callers can degrade gracefully.

        Degradation is never silent: a truncated JSON array is salvaged down
        to the objects that did arrive intact, and every other API or parse
        failure is logged at WARNING before returning None."""
        try:
            message = await self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception:
            _logger.warning("Anthropic completion request failed", exc_info=True)
            return None

        try:
            text = self._strip_fences(
                "".join(
                    block.text
                    for block in message.content
                    if getattr(block, "type", None) == "text"
                ).strip()
            )
        except Exception:
            _logger.warning(
                "Could not extract text from model response", exc_info=True
            )
            return None

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            salvaged = self._salvage_truncated_array(text)
            if salvaged is not None:
                _logger.warning(
                    "Model response was truncated; salvaged %d complete "
                    "object(s) and dropped the incomplete tail.",
                    len(salvaged),
                )
                return salvaged
            _logger.warning(
                "Could not parse JSON from model response (%d chars).",
                len(text),
            )
            return None

    @staticmethod
    def _salvage_truncated_array(text: str) -> Optional[list]:
        """Recover the complete objects from a truncated JSON array.

        Scans from the opening ``[``, tracking nesting depth (and ignoring
        braces inside strings), and trims back to the end of the last
        top-level element that closed cleanly, then re-closes the array.
        Returns the parsed list, or None if nothing whole can be recovered."""
        start = text.find("[")
        if start == -1:
            return None

        depth = 0
        in_string = False
        escaped = False
        last_complete = -1  # index just past the last fully-closed element
        for i in range(start, len(text)):
            ch = text[i]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch in "[{":
                depth += 1
            elif ch in "]}":
                depth -= 1
                # Back to depth 1 means a top-level element of the outer
                # array just closed; everything up to here is salvageable.
                if depth == 1:
                    last_complete = i + 1

        if last_complete == -1:
            return None
        candidate = text[start:last_complete] + "]"
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, list) else None

    # -- Mapping helpers ------------------------------------------------

    def _apply_normalization(self, event: Event, entry: dict[Any, Any]) -> None:
        category = entry.get("category")
        if isinstance(category, str) and category.strip():
            event.category = category.strip().lower()

        description = entry.get("description")
        if isinstance(description, str) and description.strip():
            event.description = description.strip()

        starts_at = self._parse_datetime(entry.get("starts_at"))
        if starts_at is not None:
            event.starts_at = starts_at

        event.add_availability_windows(
            self._parse_windows(entry.get("availability_times"))
        )

    def _build_activity(self, entry: Any) -> Optional[Event]:
        if not isinstance(entry, dict):
            return None
        title = entry.get("title")
        if not isinstance(title, str) or not title.strip():
            return None

        windows = self._parse_windows(entry.get("availability_times"))
        # Anchor the activity at its first availability window; fall back to
        # tomorrow so it still reads as upcoming when no window is known.
        starts_at = (
            windows[0].starts_at
            if windows
            else datetime.utcnow() + timedelta(days=1)
        )
        category = entry.get("category")
        description = entry.get("description")
        activity_id = hashlib.sha1(
            f"activity:{title.strip().lower()}".encode("utf-8")
        ).hexdigest()
        try:
            return Event(
                id=activity_id,
                title=title.strip(),
                description=(
                    description if isinstance(description, str) else ""
                ),
                category=(
                    category.strip().lower()
                    if isinstance(category, str) and category.strip()
                    else "activity"
                ),
                starts_at=starts_at,
                source_url="",
                card_type=CARD_TYPE_ACTIVITY,
                availability_times=windows,
            )
        except Exception:
            return None

    def _parse_windows(self, raw: Any) -> List[AvailabilityWindow]:
        if not isinstance(raw, list):
            return []
        windows: List[AvailabilityWindow] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            starts_at = self._parse_datetime(item.get("starts_at"))
            ends_at = self._parse_datetime(item.get("ends_at"))
            if starts_at is None or ends_at is None:
                continue
            try:
                windows.append(AvailabilityWindow(starts_at, ends_at))
            except Exception:
                continue
        return windows

    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        if not isinstance(value, str) or not value.strip():
            return None
        text = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        # Store naive UTC to match the convention used elsewhere for
        # stored event start times.
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed

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
