"""User entity.

Identity is the Firebase UID. The User aggregates preference signals
derived from their swipe history.
"""
from __future__ import annotations

from typing import List, Optional

from src.domain.exceptions import BusinessRuleViolation


class User:
    """An authenticated application user."""

    def __init__(
        self,
        id: str,
        email: str,
        display_name: Optional[str] = None,
        preferred_categories: Optional[List[str]] = None,
    ) -> None:
        if not id:
            raise BusinessRuleViolation("User id (Firebase UID) is required")
        if not email or "@" not in email:
            raise BusinessRuleViolation("User must have a valid email")

        self.id = id
        self.email = email
        self.display_name = display_name
        self.preferred_categories = preferred_categories or []

    def add_preferred_category(self, category: str) -> None:
        normalized = category.strip().lower()
        if normalized and normalized not in self.preferred_categories:
            self.preferred_categories.append(normalized)
