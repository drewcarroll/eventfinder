"""Pydantic request/response schemas for location endpoints.

Schema validation (shape, types) is allowed here. Business validation is
not — that lives in the domain.
"""
from __future__ import annotations

from typing import List

from pydantic import BaseModel


class ResolveLocationResponse(BaseModel):
    latitude: float
    longitude: float
    display_name: str


class LocationSuggestionResponse(BaseModel):
    latitude: float
    longitude: float
    display_name: str


class LocationSuggestionsResponse(BaseModel):
    suggestions: List[LocationSuggestionResponse]
