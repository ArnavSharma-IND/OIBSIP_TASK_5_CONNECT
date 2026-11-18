"""
Validation utilities for usernames, passwords, room names, and messages.
Authoritative validation used by both server and client.
"""

import re
from typing import Tuple

# Validation Constants
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 20
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_-]+$")

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128

ROOM_NAME_MIN_LENGTH = 2
ROOM_NAME_MAX_LENGTH = 30
ROOM_NAME_REGEX = re.compile(r"^[a-zA-Z0-9_-]+$")

MESSAGE_MAX_LENGTH = 2000


def validate_username(username: str) -> Tuple[bool, str]:
    """
    Validates username rules:
    - Must be a string
    - Length between 3 and 20 characters
    - Only alphanumeric, underscores, and hyphens
    """
    if not isinstance(username, str):
        return False, "Username must be a string."
    
    cleaned = username.strip()
    if len(cleaned) < USERNAME_MIN_LENGTH:
        return False, f"Username must be at least {USERNAME_MIN_LENGTH} characters."
    if len(cleaned) > USERNAME_MAX_LENGTH:
        return False, f"Username cannot exceed {USERNAME_MAX_LENGTH} characters."
    if not USERNAME_REGEX.match(cleaned):
        return False, "Username can only contain letters, numbers, underscores, and hyphens."
    
    return True, ""


def validate_password(password: str) -> Tuple[bool, str]:
    """
    Validates password strength rules:
    - Min 8, Max 128 chars
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    """
    if not isinstance(password, str):
        return False, "Password must be a string."
    
    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {PASSWORD_MIN_LENGTH} characters long."
    if len(password) > PASSWORD_MAX_LENGTH:
        return False, f"Password cannot exceed {PASSWORD_MAX_LENGTH} characters."
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number."
    
    return True, ""


def validate_password_confirmation(password: str, confirm_password: str) -> Tuple[bool, str]:
    """Validates that password matches confirmation and passes strength validation."""
    valid, err = validate_password(password)
    if not valid:
        return False, err
    if password != confirm_password:
        return False, "Passwords do not match."
    return True, ""


def sanitize_room_name(room_name: str) -> str:
    """Normalizes room name by stripping leading '#' or whitespace."""
    if not room_name:
        return ""
    name = room_name.strip()
    if name.startswith("#"):
        name = name[1:]
    return name.strip()


def validate_room_name(room_name: str) -> Tuple[bool, str]:
    """
    Validates room name rules:
    - Normalized name length between 2 and 30 characters
    - Alphanumeric, underscores, hyphens
    """
    if not isinstance(room_name, str):
        return False, "Room name must be a string."
    
    cleaned = sanitize_room_name(room_name)
    if len(cleaned) < ROOM_NAME_MIN_LENGTH:
        return False, f"Room name must be at least {ROOM_NAME_MIN_LENGTH} characters long."
    if len(cleaned) > ROOM_NAME_MAX_LENGTH:
        return False, f"Room name cannot exceed {ROOM_NAME_MAX_LENGTH} characters."
    if not ROOM_NAME_REGEX.match(cleaned):
        return False, "Room name can only contain letters, numbers, underscores, and hyphens."
    
    return True, ""


def validate_message_content(content: str) -> Tuple[bool, str]:
    """
    Validates message content rules:
    - Must be non-empty after stripping
    - Length must not exceed MESSAGE_MAX_LENGTH
    """
    if not isinstance(content, str):
        return False, "Message must be text."
    
    stripped = content.strip()
    if not stripped:
        return False, "Message cannot be empty."
    if len(content) > MESSAGE_MAX_LENGTH:
        return False, f"Message cannot exceed {MESSAGE_MAX_LENGTH} characters."
    
    return True, ""
