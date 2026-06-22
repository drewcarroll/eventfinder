"""ClockPort.

Abstracts the current time so use cases and the domain can be tested
deterministically. The system clock implementation lives in infrastructure.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime


class ClockPort(ABC):
    @abstractmethod
    def now(self) -> datetime:
        """Return the current UTC time."""
