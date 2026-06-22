"""IdGeneratorPort.

Abstracts identifier generation so use cases do not depend on a concrete
UUID library directly.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class IdGeneratorPort(ABC):
    @abstractmethod
    def new_id(self) -> str:
        """Return a new unique identifier string."""
