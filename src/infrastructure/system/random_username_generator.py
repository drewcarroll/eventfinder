"""Random username generator.

Produces friendly, readable handles like "BraveOtter42" by combining an
adjective, an animal noun, and a two-digit number. Implements
UsernameGeneratorPort; randomness is an infrastructure concern.
"""
from __future__ import annotations

import secrets

from src.application.ports.username_generator_port import (
    UsernameGeneratorPort,
)

_ADJECTIVES = (
    "Brave", "Calm", "Clever", "Cosmic", "Eager", "Gentle", "Happy",
    "Jolly", "Lucky", "Mellow", "Nimble", "Quiet", "Rapid", "Sunny",
    "Swift", "Witty", "Bold", "Bright", "Curious", "Daring",
)

_NOUNS = (
    "Otter", "Falcon", "Maple", "Comet", "Fox", "Heron", "Lynx",
    "Panda", "Raven", "Willow", "Badger", "Dolphin", "Ember", "Finch",
    "Koala", "Meadow", "Pebble", "Robin", "Tiger", "Wren",
)


class RandomUsernameGenerator(UsernameGeneratorPort):
    def generate(self) -> str:
        adjective = secrets.choice(_ADJECTIVES)
        noun = secrets.choice(_NOUNS)
        number = secrets.randbelow(90) + 10  # 10..99
        return f"{adjective}{noun}{number}"
