"""Tavily-backed implementation of EventDiscoveryPort.

Wraps the Tavily search API and maps raw results into Event domain entities
ready for downstream normalization. All external-API knowledge — endpoint,
payload shape, and query phrasing — is confined to this adapter.

Discovery is best-effort: on any API failure it degrades gracefully,
returning no results rather than breaking the feed (generated activities
can still fill it).
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any, List, Optional

import httpx

from src.application.ports.event_discovery_port import (
    DiscoveryQuery,
    EventDiscoveryPort,
)
from src.domain.entities.event import Event

logger = logging.getLogger(__name__)


class TavilyEventDiscovery(EventDiscoveryPort):
    """Discovers events via the Tavily search API."""

    BASE_URL = "https://api.tavily.com/search"

    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None):
        self._api_key = api_key
        self._client = client or httpx.AsyncClient(timeout=20.0)

    async def discover(self, query: DiscoveryQuery) -> List[Event]:
        if not self._api_key:
            # No credentials configured: skip discovery instead of issuing a
            # guaranteed-to-fail request with an empty key.
            logger.warning("Tavily API key not configured; skipping discovery")
            return []

        payload = {
            "api_key": self._api_key,
            "query": self._build_search_query(query),
            "search_depth": "advanced",
            "max_results": query.limit,
            "include_answer": False,
        }
        try:
            response = await self._client.post(self.BASE_URL, json=payload)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            # Network error, timeout, non-2xx status, or malformed JSON.
            # Degrade gracefully so the feed still works.
            logger.warning("Tavily discovery failed: %s", exc)
            return []

        return self._to_events(data, query)

    # -- query construction --------------------------------------------

    def _build_search_query(self, query: DiscoveryQuery) -> str:
        """Compose a Tavily search string from the interest/location text, an
        optional proximity radius, and an optional time range."""
        parts = [f"events and things to do: {query.query}"]
        if query.radius_km is not None:
            parts.append(f"within {int(query.radius_km)} km")
        window = self._format_time_range(
            query.starts_after, query.starts_before
        )
        if window:
            parts.append(window)
        return " ".join(parts)

    # A window no wider than this is treated as a single "today/tonight"
    # search. The app's "today" window runs from now until the early hours of
    # the next morning, so it can straddle two calendar dates.
    _SAME_DAY_MAX_HOURS = 30

    @classmethod
    def _format_time_range(
        cls,
        starts_after: Optional[datetime],
        starts_before: Optional[datetime],
    ) -> str:
        # A narrow window is "today/tonight": bias the search toward what's
        # happening right now rather than scattering across future dates.
        if starts_after is not None and starts_before is not None:
            span = starts_before - starts_after
            if span.total_seconds() <= cls._SAME_DAY_MAX_HOURS * 3600:
                day = starts_after.date().isoformat()
                return f"happening today or tonight on {day}"

        after = starts_after.date().isoformat() if starts_after else None
        before = starts_before.date().isoformat() if starts_before else None
        if after and before:
            return f"between {after} and {before}"
        if after:
            return f"on or after {after}"
        if before:
            return f"on or before {before}"
        return ""

    # -- result mapping ------------------------------------------------

    def _to_events(self, data: Any, query: DiscoveryQuery) -> List[Event]:
        if not isinstance(data, dict):
            return []
        results = data.get("results", [])
        if not isinstance(results, list):
            return []

        category = self._infer_category(query.query)
        # Placeholder start time; the normalizer refines this downstream.
        starts_at = datetime.utcnow() + timedelta(days=1)

        events: List[Event] = []
        for result in results:
            if not isinstance(result, dict):
                continue
            title = str(result.get("title", "")).strip()
            url = str(result.get("url", "")).strip()
            if not title or not url:
                continue
            try:
                events.append(
                    Event(
                        id=hashlib.sha1(url.encode("utf-8")).hexdigest(),
                        title=title,
                        description=str(result.get("content", "")),
                        category=category,
                        starts_at=starts_at,
                        source_url=url,
                    )
                )
            except Exception:  # noqa: BLE001 - skip a malformed result
                continue
        return events

    @staticmethod
    def _infer_category(query: str) -> str:
        return query.strip().lower() or "general"
