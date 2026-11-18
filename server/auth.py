"""
Authentication and session management module.
Uses PBKDF2-HMAC-SHA256 with unique cryptographically random salts
and constant-time verification. Enforces single-session logins.
"""

import hashlib
import hmac
import secrets
import threading
from typing import Any, Dict, List, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


def hash_password(password: str, salt: Optional[str] = None, iterations: int = 100_000) -> tuple[str, str]:
    """
    Hashes a password using PBKDF2-HMAC-SHA256.
    
    Args:
        password: Plaintext password string.
        salt: Hex-encoded salt string. If None, a new random salt is generated.
        iterations: Number of PBKDF2 iterations (default: 100,000).
        
    Returns:
        Tuple of (hash_hex, salt_hex).
    """
    if salt is None:
        salt_bytes = secrets.token_bytes(16)
        salt_hex = salt_bytes.hex()
    else:
        salt_bytes = bytes.fromhex(salt)
        salt_hex = salt
        
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        iterations
    )
    return dk.hex(), salt_hex


def verify_password(password: str, stored_hash: str, salt: str, iterations: int = 100_000) -> bool:
    """
    Verifies a password against the stored hash in constant time.
    
    Args:
        password: Candidate plaintext password.
        stored_hash: Hex-encoded stored hash.
        salt: Hex-encoded salt.
        iterations: Iteration count.
        
    Returns:
        True if password matches, False otherwise.
    """
    try:
        candidate_hash, _ = hash_password(password, salt=salt, iterations=iterations)
        return hmac.compare_digest(candidate_hash, stored_hash)
    except Exception as e:
        logger.error(f"Error during password verification: {e}")
        return False


class SessionManager:
    """
    Thread-safe tracker for authenticated client sessions.
    Prevents duplicate logins for the same account.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # Maps lowercase username -> client handler instance
        self._active_sessions: Dict[str, Any] = {}
        # Maps client handler -> lowercase username
        self._handler_to_username: Dict[Any, str] = {}

    def register_session(self, username: str, handler: Any) -> bool:
        """
        Registers a new active session for the given username.
        Fails if user is already logged in elsewhere.
        """
        key = username.strip().lower()
        with self._lock:
            if key in self._active_sessions:
                return False
            self._active_sessions[key] = handler
            self._handler_to_username[handler] = key
            return True

    def unregister_session(self, handler: Any) -> Optional[str]:
        """
        Removes the active session associated with the handler.
        Returns the username that was logged out, or None.
        """
        with self._lock:
            username = self._handler_to_username.pop(handler, None)
            if username and username in self._active_sessions:
                del self._active_sessions[username]
            return username

    def is_user_online(self, username: str) -> bool:
        """Checks if a username is currently logged in."""
        key = username.strip().lower()
        with self._lock:
            return key in self._active_sessions

    def get_online_users(self) -> List[str]:
        """Returns list of currently online usernames."""
        with self._lock:
            return list(self._active_sessions.keys())

    def get_handler_for_user(self, username: str) -> Optional[Any]:
        """Returns the client handler for an active username, if online."""
        key = username.strip().lower()
        with self._lock:
            return self._active_sessions.get(key)
