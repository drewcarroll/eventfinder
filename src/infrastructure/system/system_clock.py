"""System clock implementation of ClockPort."""
from __future__ import annotations

from datetime import datetime

from src.application.ports.clock_port import ClockPort


class SystemClock(ClockPort):
    def now(self) -> datetime:
        return datetime.utcnow()
