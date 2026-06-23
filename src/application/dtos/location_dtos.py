"""DTOs for location-related use cases.

DTOs are the input/output contracts of use cases. They are plain data
holders and never expose domain entities directly to the interfaces layer.
"""
from __future__ import annotations

from dataclasses import dataclass


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
