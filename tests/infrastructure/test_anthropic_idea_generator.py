"""Tests for the idea generator's per-card image handling.

Each generated card gets a relevant photo URL (LoremFlickr) derived from the
model's visual keyword, with deterministic fallbacks so no card is left
without a picture. These cover the pure URL building and the field plumbing in
``_build_idea`` without invoking the LLM.
"""
from src.infrastructure.llm.anthropic_idea_generator import (
    AnthropicIdeaGenerator,
    _image_url_for,
)


def _build(entry: dict):
    # _build_idea uses no instance state, so an uninitialized instance is fine.
    generator = object.__new__(AnthropicIdeaGenerator)
    return AnthropicIdeaGenerator._build_idea(generator, entry)


def test_image_url_uses_keyword_words_as_tags():
    url = _image_url_for("Late-night Tacos!", "seed")
    assert url is not None
    assert url.startswith("https://loremflickr.com/800/600/late,night,tacos?")


def test_image_url_caps_at_three_tags():
    url = _image_url_for("a b c d e", "seed")
    assert "/a,b,c?" in url


def test_image_url_is_stable_for_a_card_but_varies_by_card():
    assert _image_url_for("hiking", "id1") == _image_url_for("hiking", "id1")
    assert _image_url_for("hiking", "id1") != _image_url_for("hiking", "id2")


def test_image_url_none_when_no_usable_words():
    assert _image_url_for("   --- !!!  ", "seed") is None


def test_build_idea_prefers_image_query():
    event = _build(
        {
            "title": "Catch Don Toliver at Shoreline",
            "category": "music",
            "image_query": "live concert",
        }
    )
    assert event.image_url == _image_url_for("live concert", event.id)


def test_build_idea_falls_back_to_category_then_title():
    from_category = _build({"title": "Walk Cuesta Park", "category": "park"})
    assert from_category.image_url == _image_url_for("park", from_category.id)

    # Blank category + blank query falls back to the default category word.
    fallback = _build(
        {
            "title": "Sunset at Twin Peaks",
            "category": "  ",
            "image_query": "  ",
        }
    )
    assert fallback.image_url is not None


def test_every_built_idea_has_an_image():
    event = _build({"title": "Late-night tacos at La Bamba"})
    assert event.image_url is not None
