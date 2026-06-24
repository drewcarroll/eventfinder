"""DTOs for location-related use cases.

DTOs are the input/output contracts of use cases. They are plain data
holders and never expose domain entities directly to the interfaces layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class ResolveLocationInput:
    """Input for resolving a manually entered location."""

    query: str


@dataclass(frozen=True)
class ResolveLocationOutput:
    """Output: the coordinates a manual location resolved to."""

    latitude: float
    longitude: float
    display_name: str


@dataclass(frozen=True)
class LocationSuggestion:
    """One candidate place for the city type-ahead."""

    latitude: float
    longitude: float
    display_name: str


@dataclass(frozen=True)
class SearchLocationsInput:
    """Input for the city type-ahead: the partial text and a result cap."""

    query: str
    limit: int = 5


@dataclass(frozen=True)
class SearchLocationsOutput:
    """Output: the candidate places matching the query, best match first."""

    suggestions: List[LocationSuggestion] = field(default_factory=list)
