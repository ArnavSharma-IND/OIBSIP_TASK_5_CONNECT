"""
Unit tests for emoji shortcode mapping and Unicode preservation.
"""

from utils.emoji import get_available_shortcodes, replace_shortcodes


def test_replace_shortcodes():
    raw = "Hello :smile: How are you? :fire:"
    converted = replace_shortcodes(raw)
    assert "😄" in converted
    assert "🔥" in converted
    assert ":smile:" not in converted
    assert ":fire:" not in converted


def test_preserve_native_unicode_emojis():
    # Native emojis typed directly via Win + .
    raw = "Great work! 🚀🎉 Keep it up 👍"
    converted = replace_shortcodes(raw)
    assert converted == raw  # Native emojis remain completely intact


def test_unregistered_shortcodes_untouched():
    raw = "Check this :nonexistent_shortcode_xyz: token"
    converted = replace_shortcodes(raw)
    assert converted == raw


def test_empty_and_none_text():
    assert replace_shortcodes("") == ""
    assert replace_shortcodes(None) == ""


def test_get_available_shortcodes():
    codes = get_available_shortcodes()
    assert isinstance(codes, dict)
    assert ":heart:" in codes
    assert codes[":heart:"] == "❤️"
