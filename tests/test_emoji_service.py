"""test_emoji_service.py — emoji_service testlari."""
from __future__ import annotations

from unittest.mock import MagicMock

from services.emoji_service import _utf16_slice, extract_custom_emoji_from_message


class TestUtf16Slice:
    def test_ascii_text(self):
        assert _utf16_slice("Hello World", 0, 5) == "Hello"

    def test_simple_emoji(self):
        assert _utf16_slice("Prize 🏆 here", 6, 2) == "🏆"

    def test_zwj_sequence(self):
        assert _utf16_slice("Family: 👨‍👩‍👧 end", 8, 8) == "👨‍👩‍👧"

    def test_out_of_bounds(self):
        assert _utf16_slice("Short", 100, 5) == ""

    def test_empty_text(self):
        assert _utf16_slice("", 0, 5) == ""


class TestExtractCustomEmoji:
    def _make_message(self, text=None, entities=None, caption=None, caption_entities=None):
        msg = MagicMock()
        msg.text = text
        msg.entities = entities
        msg.caption = caption
        msg.caption_entities = caption_entities
        return msg

    def _make_entity(self, offset, length, custom_id, type_="custom_emoji"):
        e = MagicMock()
        e.type = type_
        e.offset = offset
        e.length = length
        e.custom_emoji_id = custom_id
        return e

    def test_no_entities_returns_none(self):
        msg = self._make_message(text="Salom")
        assert extract_custom_emoji_from_message(msg) is None

    def test_extract_from_text(self):
        entity = self._make_entity(0, 2, "5368324170671202286")
        msg = self._make_message(text="🏆", entities=[entity])
        result = extract_custom_emoji_from_message(msg)
        assert result is not None
        assert result[0] == "🏆"
        assert result[1] == "5368324170671202286"

    def test_ignores_non_custom_emoji_entities(self):
        entity = self._make_entity(0, 5, None, type_="bold")
        msg = self._make_message(text="Hello", entities=[entity])
        assert extract_custom_emoji_from_message(msg) is None
