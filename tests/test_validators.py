"""
Unit tests for validation functions.
"""

from utils.validators import (
    sanitize_room_name,
    validate_message_content,
    validate_password,
    validate_password_confirmation,
    validate_room_name,
    validate_username,
)


def test_validate_username():
    # Valid usernames
    assert validate_username("alice")[0] is True
    assert validate_username("Bob_123")[0] is True
    assert validate_username("user-name")[0] is True
    assert validate_username("a" * 20)[0] is True

    # Invalid usernames
    assert validate_username("al")[0] is False  # Too short
    assert validate_username("a" * 21)[0] is False  # Too long
    assert validate_username("alice@")[0] is False  # Invalid character
    assert validate_username("user name")[0] is False  # Spaces not allowed
    assert validate_username("")[0] is False
    assert validate_username(None)[0] is False


def test_validate_password():
    # Valid passwords (min 8 chars, 1 uppercase, 1 lowercase, 1 digit)
    assert validate_password("SecurePass123")[0] is True
    assert validate_password("Abcdefg1")[0] is True

    # Invalid passwords
    assert validate_password("Short1A")[0] is False  # < 8 chars
    assert validate_password("alllowercase1")[0] is False  # No uppercase
    assert validate_password("ALLUPPERCASE1")[0] is False  # No lowercase
    assert validate_password("NoDigitsHerePass")[0] is False  # No digit
    assert validate_password("")[0] is False
    assert validate_password(12345678)[0] is False


def test_validate_password_confirmation():
    assert validate_password_confirmation("ValidPass1", "ValidPass1")[0] is True
    assert validate_password_confirmation("ValidPass1", "MismatchPass1")[0] is False
    assert validate_password_confirmation("weak", "weak")[0] is False


def test_sanitize_and_validate_room_name():
    assert sanitize_room_name("#general") == "general"
    assert sanitize_room_name("  random  ") == "random"

    # Valid room names
    assert validate_room_name("general")[0] is True
    assert validate_room_name("#dev_team")[0] is True
    assert validate_room_name("gaming-101")[0] is True

    # Invalid room names
    assert validate_room_name("a")[0] is False  # Too short (< 2)
    assert validate_room_name("a" * 31)[0] is False  # Too long (> 30)
    assert validate_room_name("dev room")[0] is False  # Space
    assert validate_room_name("!invalid")[0] is False


def test_validate_message_content():
    assert validate_message_content("Hello world!")[0] is True
    assert validate_message_content("😊 Unicode emoji")[0] is True
    assert validate_message_content("   ")[0] is False  # Whitespace only
    assert validate_message_content("")[0] is False
    assert validate_message_content("a" * 2000)[0] is True
    assert validate_message_content("a" * 2001)[0] is False  # Exceeds max length
