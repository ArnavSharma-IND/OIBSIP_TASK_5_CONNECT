"""
Unit tests for password hashing, verification, and session management.
"""

from server.auth import SessionManager, hash_password, verify_password


def test_hash_password_and_verify():
    password = "SuperSecretPassword123"
    hash_hex, salt_hex = hash_password(password, iterations=1000)
    
    assert hash_hex is not None
    assert salt_hex is not None
    assert len(salt_hex) == 32  # 16 bytes in hex = 32 hex chars
    
    # Correct verification
    assert verify_password(password, hash_hex, salt_hex, iterations=1000) is True
    
    # Wrong password verification
    assert verify_password("WrongPassword123", hash_hex, salt_hex, iterations=1000) is False


def test_unique_salts_for_same_password():
    password = "SamePassword123"
    hash1, salt1 = hash_password(password, iterations=1000)
    hash2, salt2 = hash_password(password, iterations=1000)
    
    assert salt1 != salt2
    assert hash1 != hash2


def test_session_manager_duplicate_prevention():
    mgr = SessionManager()
    handler_1 = object()
    handler_2 = object()
    
    # First login succeeds
    assert mgr.register_session("Alice", handler_1) is True
    assert mgr.is_user_online("alice") is True
    assert mgr.is_user_online("ALICE") is True  # Case-insensitive
    
    # Duplicate login for same user fails
    assert mgr.register_session("alice", handler_2) is False
    assert mgr.register_session("ALICE", handler_2) is False
    
    # Different user succeeds
    assert mgr.register_session("Bob", handler_2) is True
    assert len(mgr.get_online_users()) == 2
    
    # Unregister session
    logged_out = mgr.unregister_session(handler_1)
    assert logged_out == "alice"
    assert mgr.is_user_online("alice") is False
    
    # Now Alice can log in again
    assert mgr.register_session("alice", handler_1) is True
