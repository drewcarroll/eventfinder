"""Pydantic schemas for the user HTTP boundary."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class UserResponse(BaseModel):
    uid: str
    email: str
    display_name: Optional[str] = None
    username: str
    name: Optional[str] = None
    preferred_activities: str = ""
    created_at: datetime


class UpdateProfileRequest(BaseModel):
    """The user-editable profile fields submitted from the profile tab.

    ``name`` is optional; omit it to leave the stored name unchanged, or
    send an empty string to clear it.
    """

    username: str
    preferred_activities: str = ""
    name: Optional[str] = None

    @field_validator("username")
    @classmethod
    def _username_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("username cannot be blank")
        return cleaned


class UserStatsResponse(BaseModel):
    liked_ideas: int


class UserAccountResponse(BaseModel):
    """The authenticated user's profile plus their activity stats."""

    uid: str
    email: str
    username: str
    name: Optional[str] = None
    preferred_activities: str = ""
    created_at: datetime
    stats: UserStatsResponse
