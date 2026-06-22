"""Tavily-backed implementation of EventDiscoveryPort.

Wraps the Tavily search API and maps raw results into Event domain
entities. All external-API knowledge is confined to this adapter.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from typing import List

import httpx

from src.application.ports.event_discovery_port import EventDiscoveryPort
from src.domain.entities.event import Event


class TavilyEventDiscovery(EventDiscoveryPort):
    """Discovers events via the Tavily search API."""

    BASE_URL = "https://api.tavily.com/search"

    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None):
        self._api_key = api_key
        self._client = client or httpx.AsyncClient(timeout=20.0)

    async def discover(self, query: str, limit: int) -> List[Event]:
        payload = {
            "api_key": self._api_key,
            "query": f"upcoming events: {query}",
            "search_depth": "advanced",
            "max_results": limit,
            "include_answer": False,
        }
        response = await self._client.post(self.BASE_URL, json=payload)
        response.raise_for_status()
        data = response.json()

        events: List[Event] = []
        starts_at = datetime.utcnow() + timedelta(days=1)
        for result in data.get("results", []):
            title = result.get("title", "").strip()
            url = result.get("url", "")
            if not title or not url:
                continue
            event_id = hashlib.sha1(url.encode("utf-8")).hexdigest()
            events.append(
                Event(
                    id=event_id,
                    title=title,
                    description=result.get("content", ""),
                    category=self._infer_category(query),
                    starts_at=starts_at,
                    source_url=url,
                )
            )
        return events

    @staticmethod
    def _infer_category(query: str) -> str:
        return query.strip().lower() or "general"
