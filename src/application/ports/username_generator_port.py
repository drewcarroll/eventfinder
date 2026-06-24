"""UsernameGeneratorPort.

Abstracts generation of a random, human-friendly username so use cases do
not depend on a concrete randomness source. Mirrors IdGeneratorPort.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class UsernameGeneratorPort(ABC):
    @abstractmethod
    def generate(self) -> str:
        """Return a new random username (e.g. "BraveOtter42")."""
