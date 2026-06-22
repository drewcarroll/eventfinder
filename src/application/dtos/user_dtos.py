"""DTOs for user-related use cases."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class SyncUserInput:
    """Identity extracted from a verified Firebase ID token."""

    uid: str
    email: str
    display_name: Optional[str] = None


@dataclass(frozen=True)
class SyncUserOutput:
    """The user record after an upsert, plus whether it was just created."""

    uid: str
    email: str
    display_name: Optional[str]
    created_at: datetime
    is_new: bool
