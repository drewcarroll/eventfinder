"""Pydantic response schemas for the user HTTP boundary."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UserResponse(BaseModel):
    uid: str
    email: str
    display_name: Optional[str] = None
    created_at: datetime
