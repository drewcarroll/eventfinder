"""Nominatim-backed implementation of GeocodingPort.

Wraps the OpenStreetMap Nominatim geocoding API and maps the top result
into a domain GeoLocation. All external-API knowledge is confined to this
adapter. Nominatim is keyless but requires an identifying User-Agent.
"""
from __future__ import annotations

from typing import Any, List, Optional

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
        results = await self.search(query, limit=1)
        return results[0] if results else None

    async def search(
        self, query: str, limit: int = 5
    ) -> List[GeocodingResult]:
        response = await self._client.get(
            self.BASE_URL,
            params={
                "q": query,
                "format": "json",
                "limit": limit,
                # Bias the type-ahead to US cities/towns: restrict to the US
                # and to place-level results (city, town, village) so a few
                # typed letters surface real municipalities, not streets.
                "countrycodes": "us",
                "featuretype": "city",
                "addressdetails": 1,
            },
            headers={"User-Agent": self._user_agent},
        )
        response.raise_for_status()
        raw = response.json()
        if not isinstance(raw, list):
            return []

        out: List[GeocodingResult] = []
        for item in raw:
            result = self._to_result(item)
            if result is not None:
                out.append(result)
        return out

    @staticmethod
    def _to_result(item: Any) -> Optional[GeocodingResult]:
        if not isinstance(item, dict):
            return None
        try:
            location = GeoLocation(
                latitude=float(item["lat"]),
                longitude=float(item["lon"]),
            )
        except (KeyError, ValueError, TypeError, InvalidValueError):
            # Malformed or out-of-range coordinates: skip this candidate.
            return None
        return GeocodingResult(
            location=location,
            display_name=item.get("display_name", ""),
        )
