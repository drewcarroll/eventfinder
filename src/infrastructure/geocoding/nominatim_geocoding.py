"""Nominatim-backed implementation of GeocodingPort.

Wraps the OpenStreetMap Nominatim geocoding API and maps the top result
into a domain GeoLocation. All external-API knowledge is confined to this
adapter. Nominatim is keyless but requires an identifying User-Agent.
"""
from __future__ import annotations

from typing import Optional

import httpx

from src.application.ports.geocoding_port import (
    GeocodingPort,
    GeocodingResult,
)
from src.domain.exceptions import InvalidValueError
from src.domain.value_objects.geo_location import GeoLocation


class NominatimGeocoding(GeocodingPort):
    """Resolves locations via the OpenStreetMap Nominatim API."""

    BASE_URL = "https://nominatim.openstreetmap.org/search"

    def __init__(
        self,
        user_agent: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._user_agent = user_agent
        self._client = client or httpx.AsyncClient(timeout=20.0)

    async def geocode(self, query: str) -> Optional[GeocodingResult]:
        response = await self._client.get(
            self.BASE_URL,
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": self._user_agent},
        )
        response.raise_for_status()
        results = response.json()
        if not results:
            return None

        top = results[0]
        try:
            location = GeoLocation(
                latitude=float(top["lat"]),
                longitude=float(top["lon"]),
            )
        except (KeyError, ValueError, InvalidValueError):
            # Malformed or out-of-range coordinates: treat as unresolved.
            return None

        return GeocodingResult(
            location=location,
            display_name=top.get("display_name", query),
        )
