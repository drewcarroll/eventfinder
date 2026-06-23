"""CardMerger domain service.

Merges card lists from multiple sources — normalized web events, generated
activities, and previously stored cards — into a single deduplicated list.

Duplicate detection is a business rule: two cards are the same offering
when they share an identity key. The first occurrence wins (callers pass
the freshest, richest source first), and availability windows from later
duplicates are folded into the survivor so no availability is lost.
"""
from __future__ import annotations

from typing import Dict, List

from src.domain.entities.event import Event


class CardMerger:
    """Combines and deduplicates swipeable cards."""

    def merge(self, *card_lists: List[Event]) -> List[Event]:
        """Concatenate the given lists in order and drop duplicates,
        keeping the first card seen for each identity key."""
        result: List[Event] = []
        by_key: Dict[str, Event] = {}
        for cards in card_lists:
            for card in cards:
                key = card.identity_key()
                survivor = by_key.get(key)
                if survivor is None:
                    by_key[key] = card
                    result.append(card)
                else:
                    survivor.add_availability_windows(card.availability_times)
        return result
