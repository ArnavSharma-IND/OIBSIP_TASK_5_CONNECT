"""
Emoji mapping and processing utilities.
Supports emoji shortcode expansion and seamless native Unicode emoji handling.
"""

import re
from typing import Dict

# Common standard shortcode to Unicode emoji mapping
EMOJI_SHORTCODES: Dict[str, str] = {
    ":smile:": "😄",
    ":smiley:": "😃",
    ":grinning:": "😀",
    ":blush:": "😊",
    ":wink:": "😉",
    ":heart_eyes:": "😍",
    ":kissing_heart:": "😘",
    ":stuck_out_tongue:": "😛",
    ":joy:": "😂",
    ":rofl:": "🤣",
    ":sob:": "😭",
    ":sweat_smile:": "😅",
    ":thinking:": "🤔",
    ":neutral_face:": "😐",
    ":sunglasses:": "😎",
    ":nerd:": "🤓",
    ":confused:": "😕",
    ":disappointed:": "😞",
    ":angry:": "😠",
    ":rage:": "😡",
    ":thumbsup:": "👍",
    ":thumbsdown:": "👎",
    ":clap:": "👏",
    ":wave:": "👋",
    ":ok_hand:": "👌",
    ":pray:": "🙏",
    ":muscle:": "💪",
    ":heart:": "❤️",
    ":broken_heart:": "💔",
    ":sparkles:": "✨",
    ":star:": "⭐",
    ":fire:": "🔥",
    ":100:": "💯",
    ":rocket:": "🚀",
    ":tada:": "🎉",
    ":check:": "✅",
    ":x:": "❌",
    ":warning:": "⚠️",
    ":bulb:": "💡",
    ":coffee:": "☕",
    ":pizza:": "🍕",
    ":beer:": "🍺",
    ":eyes:": "👀",
    ":pin:": "📌",
}

# Regex matching shortcodes like :smile:, :heart:, etc.
SHORTCODE_PATTERN = re.compile(r":([a-zA-Z0-9_+-]+):")


def replace_shortcodes(text: str) -> str:
    """
    Replaces registered :shortcode: tokens in text with their Unicode emoji counterparts.
    Native emojis typed via system keyboards (e.g. Win + .) are untouched.
    
    Args:
        text: Input string potentially containing shortcodes.
        
    Returns:
        String with shortcodes replaced.
    """
    if not text:
        return ""

    def _replace_match(match: re.Match) -> str:
        code = match.group(0)
        return EMOJI_SHORTCODES.get(code, code)

    return SHORTCODE_PATTERN.sub(_replace_match, text)


def get_available_shortcodes() -> Dict[str, str]:
    """Returns a copy of the available emoji shortcode dictionary."""
    return dict(EMOJI_SHORTCODES)
