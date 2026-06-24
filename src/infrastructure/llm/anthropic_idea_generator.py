"""Anthropic Claude implementation of IdeaGeneratorPort.

A two-stage pipeline, both stages backed by Claude:

1. RESEARCH — condense the raw web results gathered for an area into two
   compact briefs: one of specific, time-bound happenings, one of durable
   named places & activities. Scraped boilerplate and listicle fluff are
   discarded; only concrete, named specifics survive.
2. IDEAS — turn those briefs into a large deck of cards where every card is
   ONE specific, do-able idea ("Grab a drink at Farley's"), never a
   category or a list ("Pubs near you"). Anything list-shaped is split into
   separate cards, and duplicates are dropped.

All LLM and parsing detail is confined to this adapter; the use case is
unaware Claude is the provider. Both stages are best-effort: on any failure
they degrade gracefully rather than breaking the feed.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, List, Optional, Tuple

from anthropic import AsyncAnthropic

from src.application.ports.idea_generator_port import IdeaGeneratorPort
from src.domain.entities.event import CARD_TYPE_ACTIVITY, Event
from src.domain.entities.user import User
from src.domain.value_objects.availability_window import AvailabilityWindow

_logger = logging.getLogger(__name__)

# Hard cap on how many ideas a single generation may emit, independent of
# the requested feed size, to bound token usage on a runaway response.
_MAX_IDEAS = 60

# How many raw research items to feed the condense step. More gives richer
# grounding but a longer prompt; the discovery stage already over-fetches.
_MAX_RESEARCH_ITEMS = 20


def _to_naive_utc(value: Optional[datetime]) -> Optional[datetime]:
    """Normalize an (optionally tz-aware) datetime to naive UTC, matching the
    convention used for stored card times. ``None`` passes through."""
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


class AnthropicIdeaGenerator(IdeaGeneratorPort):
    """Researches an area and generates specific, single-idea cards."""

    def __init__(
        self,
        api_key: str,
        model: str,
        client: Optional[AsyncAnthropic] = None,
    ):
        self._client = client or AsyncAnthropic(api_key=api_key)
        self._model = model

    async def generate(
        self,
        query: str,
        user: User,
        limit: int,
        research: List[Event],
        starts_after: Optional[datetime] = None,
        starts_before: Optional[datetime] = None,
        radius_km: Optional[float] = None,
    ) -> List[Event]:
        count = max(0, min(limit, _MAX_IDEAS))
        if count == 0:
            return []

        # Stage 1: condense the raw research into two briefs. Missing or
        # unusable research is fine — generation falls back to general
        # knowledge of the place named in the query.
        events_doc, places_doc = await self._research_docs(research, query)

        # Stage 2: generate specific, single-idea cards from the briefs.
        interests = ", ".join(user.preferred_categories) or "general"
        constraints = self._describe_constraints(
            starts_after, starts_before, radius_km
        )
        prompt = self._ideas_prompt(
            query, count, interests, constraints, events_doc, places_doc
        )

        # Up to ~60 cards with descriptions and availability windows needs
        # plenty of room; salvage recovers complete objects if it truncates.
        parsed = await self._complete_json(prompt, max_tokens=16000)
        if not isinstance(parsed, list):
            return []

        # Anchor for an idea the model returns without availability_times: the
        # window start (≈ now). It keeps such a card inside the "today" filter
        # without inventing a fake clock time to show — cards keep their empty
        # availability_times and the client simply renders no time for them.
        fallback_start = _to_naive_utc(starts_after)

        ideas: List[Event] = []
        seen: set[str] = set()
        for entry in parsed:
            event = self._build_idea(entry, fallback_start)
            if event is None:
                continue
            # Enforce uniqueness here too, so duplicates don't eat into the
            # requested count before the use case's merger dedupes.
            key = event.identity_key()
            if key in seen:
                continue
            seen.add(key)
            ideas.append(event)
            if len(ideas) >= count:
                break
        return ideas

    # -- Stage 1: research ----------------------------------------------

    async def _research_docs(
        self, research: List[Event], query: str
    ) -> Tuple[str, str]:
        """Condense raw web results into (events_doc, places_doc). Returns a
        pair of empty strings when there is nothing usable to condense."""
        items = [
            {
                "title": event.title,
                "content": event.description[:600],
                "source_url": event.source_url,
            }
            for event in research[:_MAX_RESEARCH_ITEMS]
        ]
        if not items:
            return "", ""

        prompt = (
            "You are researching what there is to do in or near the location "
            f'described in "{query}". Below are raw web search results. '
            "Extract the concrete, NAMED specifics and organize them into two "
            "research briefs. Preserve every concrete detail the source gives "
            "— especially exact names and exact times — and never invent "
            "them:\n"
            "- events_doc: specific, time-bound happenings — concerts, shows, "
            "games, festivals, screenings, DJ sets. For each, capture the "
            "exact act/event name, the venue, the DATE, and the START and END "
            "time (or door/showtime) WHENEVER the source states them, quoted "
            "exactly as written.\n"
            "- places_doc: durable, named places and activities — specific "
            "bars, restaurants, cafes, parks, trails, museums, shops, "
            "viewpoints. For each, capture the exact place name, what you'd "
            "actually do there, and its OPENING HOURS / today's hours when "
            "the source states them.\n"
            "Discard navigation, boilerplate, and vague listicle fluff. Keep "
            "only specifics a person could actually act on.\n\n"
            "Respond with ONLY a JSON object with keys: events_doc (string), "
            "places_doc (string).\n\n"
            f"Results:\n{json.dumps(items)}"
        )

        parsed = await self._complete_json(prompt, max_tokens=4096)
        if not isinstance(parsed, dict):
            return "", ""
        events_doc = parsed.get("events_doc")
        places_doc = parsed.get("places_doc")
        return (
            events_doc if isinstance(events_doc, str) else "",
            places_doc if isinstance(places_doc, str) else "",
        )

    # -- Stage 2: ideas prompt ------------------------------------------

    @staticmethod
    def _ideas_prompt(
        query: str,
        count: int,
        interests: str,
        constraints: str,
        events_doc: str,
        places_doc: str,
    ) -> str:
        if events_doc or places_doc:
            research_block = (
                "Use this research about the area to ground your ideas in "
                "real, named specifics:\n\n"
                f"EVENTS & HAPPENINGS:\n{events_doc or '(none found)'}\n\n"
                f"PLACES & ACTIVITIES:\n{places_doc or '(none found)'}\n\n"
            )
        else:
            research_block = (
                "No research was available, so draw on general knowledge of "
                "the place named in the query, still naming specific, real "
                "spots wherever you can.\n\n"
            )

        return (
            f"Propose a big, varied list of {count} things to do in or near "
            f'the location described in "{query}". Aim for the full {count} — '
            "give a generous, deep list, not a handful.\n\n"
            f"{research_block}"
            "MIX TWO KINDS of cards so the feed feels full and useful:\n"
            "1. Specific happenings from the research — concerts, shows, "
            "games, screenings, festivals — named exactly, with their real "
            "times.\n"
            "2. Everyday go-to ideas anyone could do right now — e.g. grab "
            "ice cream, walk a park, catch a sunset viewpoint, get a coffee, "
            "see a movie, shoot pool, late-night tacos. These are essential: "
            "include plenty of them, and name a real, specific spot for each "
            "when you can.\n\n"
            "EVERY card MUST be ONE single, specific, do-able idea:\n"
            "- A card names ONE specific place, event, or action — NEVER a "
            "category, a plural, or a list.\n"
            "- If the research mentions a category or several options, SPLIT "
            "them into separate cards: one card per specific place/idea.\n\n"
            "GOOD (do this):\n"
            '- "Grab a scoop at Rick\'s Ice Cream"\n'
            '- "Catch Don Toliver at Shoreline Amphitheatre"\n'
            '- "Walk the loop at Cuesta Park"\n'
            '- "Late-night tacos at La Bamba"\n'
            "BAD (never produce these):\n"
            '- "Pubs near you in Mountain View"  -> split into specific bars\n'
            '- "Check out a late-night event"  -> name the actual event\n'
            '- "Head to a park"  -> name the park and the activity\n\n'
            f"Tailor the mix to someone interested in {interests}, but still "
            "include broad, everyday crowd-pleasers. "
            f"{constraints} "
            "Make every card unique — no two cards may be the same idea.\n\n"
            "For each idea give:\n"
            "- title: the ONE specific, named thing to do, concrete and "
            "imperative (name the actual venue / act / place — never a "
            "generic placeholder like 'a late-night event').\n"
            "- description: one factual sentence saying what it actually IS — "
            "the act/genre, the kind of place, or what you'd do there. No "
            "vague hype.\n"
            "- category: a single lowercase word.\n"
            "- availability_times: a list of {starts_at, ends_at} windows as "
            "LOCAL date-times (full ISO 8601 date and time, NO timezone "
            "suffix) giving the REAL start and end the thing is available in "
            "today's window. Use the actual times from the research when it "
            "states them; for a venue, use its real opening hours for today. "
            "Every window MUST have BOTH a starts_at and an ends_at — if only "
            "a start is known, estimate a sensible end (about 2–3 hours "
            "later). Omit availability_times only when you truly have no time "
            "basis (e.g. an always-open outdoor spot); never invent a "
            "placeholder time.\n\n"
            "Respond with ONLY a JSON array of objects with keys: title "
            "(string), description (string), category (string), "
            "availability_times (array of {starts_at, ends_at})."
        )

    @staticmethod
    def _describe_constraints(
        starts_after: Optional[datetime],
        starts_before: Optional[datetime],
        radius_km: Optional[float],
    ) -> str:
        """Render the distance + time-window constraints into a prompt
        fragment. Returns an empty string when nothing is constrained, or a
        sentence (or two) terminated by a space so it slots cleanly into the
        surrounding instructions."""
        parts: List[str] = []
        if radius_km is not None:
            parts.append(
                f"Only suggest places within {radius_km:g} km of that "
                "location."
            )
        if starts_after is not None and starts_before is not None:
            parts.append(
                "This is a 'what can I do TODAY?' feed. All times here are "
                "LOCAL time (no timezone). Right now it is "
                f"{starts_after.isoformat()}; the window runs until "
                f"{starts_before.isoformat()} (later tonight / into the early "
                "morning). Only suggest things doable at some point in that "
                "window — nothing closed during these hours, nothing on "
                "another day. Give each availability window as LOCAL times "
                "inside this window, using the exact dates above and NO "
                "timezone suffix (never append 'Z' or an offset)."
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
        return " ".join(parts) + " "

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
            _logger.warning(
                "Anthropic completion request failed", exc_info=True
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

    def _build_idea(
        self,
        entry: Any,
        fallback_start: Optional[datetime] = None,
    ) -> Optional[Event]:
        if not isinstance(entry, dict):
            return None
        title = entry.get("title")
        if not isinstance(title, str) or not title.strip():
            return None

        windows = self._parse_windows(entry.get("availability_times"))
        # Anchor the card's primary time: its first availability window, else
        # the requested window's start (≈ now) so it still passes the "today"
        # filter, else tomorrow. We do NOT synthesize an availability window
        # here — a card with no real times keeps an empty list so the UI shows
        # no (misleading) clock time for it.
        if windows:
            starts_at = windows[0].starts_at
        elif fallback_start is not None:
            starts_at = fallback_start
        else:
            starts_at = datetime.utcnow() + timedelta(days=1)
        category = entry.get("category")
        description = entry.get("description")
        idea_id = hashlib.sha1(
            f"idea:{title.strip().lower()}".encode("utf-8")
        ).hexdigest()
        try:
            return Event(
                id=idea_id,
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
            # A time-only ``ends_at`` ("18:00") carries no date of its own;
            # anchor it to the start's date so an {open, close} pair forms a
            # single day's window instead of being dropped.
            anchor = starts_at.date() if starts_at is not None else None
            ends_at = self._parse_datetime(item.get("ends_at"), anchor)
            if starts_at is None or ends_at is None:
                continue
            try:
                windows.append(AvailabilityWindow(starts_at, ends_at))
            except Exception:
                continue
        return windows

    @staticmethod
    def _parse_datetime(
        value: Any, anchor_date: Optional[date] = None
    ) -> Optional[datetime]:
        """Parse a model-supplied timestamp into naive UTC.

        Accepts three shapes the model emits interchangeably:
        full ISO-8601 datetimes, bare dates ("YYYY-MM-DD", anchored at
        00:00), and bare times ("HH:MM[:SS]", anchored to ``anchor_date``
        — or today when none is given). Returns None if it's none of these."""
        if not isinstance(value, str) or not value.strip():
            return None
        text = value.strip().replace("Z", "+00:00")

        try:
            # Covers full datetimes and bare dates, which fromisoformat
            # already anchors at midnight.
            parsed = datetime.fromisoformat(text)
        except ValueError:
            # Time-only values raise above; pin them to a date so the
            # window survives instead of being silently dropped.
            try:
                parsed_time = time.fromisoformat(text)
            except ValueError:
                return None
            base = anchor_date or datetime.utcnow().date()
            parsed = datetime.combine(base, parsed_time)

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
