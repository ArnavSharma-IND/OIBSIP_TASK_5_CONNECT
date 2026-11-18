"""
Unit tests for SQLite database operations.
"""

from server.auth import hash_password


def test_database_initialization(db):
    # Verify default room was created
    room = db.get_room_by_name("general")
    assert room is not None
    assert room["room_name"] == "general"


def test_create_and_get_user(db):
    pwd_hash, salt = hash_password("ValidPassword1", iterations=1000)
    user_id = db.create_user("Alice", pwd_hash, salt)
    assert user_id is not None
    
    # Retrieve user
    user = db.get_user_by_username("alice")
    assert user is not None
    assert user["id"] == user_id
    assert user["username"] == "Alice"
    assert user["password_hash"] == pwd_hash
    assert user["salt"] == salt
    
    # Duplicate username prevention (case-insensitive)
    dup_id = db.create_user("ALICE", pwd_hash, salt)
    assert dup_id is None


def test_create_and_get_room(db):
    pwd_hash, salt = hash_password("ValidPassword1", iterations=1000)
    user_id = db.create_user("Bob", pwd_hash, salt)
    
    room_id = db.create_room("engineering", created_by_id=user_id)
    assert room_id is not None
    
    room = db.get_room_by_name("engineering")
    assert room is not None
    assert room["id"] == room_id
    assert room["room_name"] == "engineering"
    assert room["created_by"] == user_id
    
    # Duplicate room prevention
    dup_room_id = db.create_room("ENGINEERING", created_by_id=user_id)
    assert dup_room_id is None


def test_save_and_retrieve_messages(db):
    pwd_hash, salt = hash_password("ValidPassword1", iterations=1000)
    db.create_user("Alice", pwd_hash, salt)
    db.create_user("Bob", pwd_hash, salt)
    db.create_room("dev", created_by_id=1)
    
    # Save messages
    msg_id1 = db.save_message("dev", "Alice", "Hello Dev Team!", "2026-11-18 10:00:00")
    msg_id2 = db.save_message("dev", "Bob", "Hey Alice, welcome! 🚀", "2026-11-18 10:01:00")
    
    assert msg_id1 is not None
    assert msg_id2 is not None
    assert msg_id2 > msg_id1
    
    # Retrieve messages
    history = db.get_room_messages("dev", limit=10)
    assert len(history) == 2
    assert history[0]["sender"] == "Alice"
    assert history[0]["content"] == "Hello Dev Team!"
    assert history[1]["sender"] == "Bob"
    assert history[1]["content"] == "Hey Alice, welcome! 🚀"


def test_message_pagination(db):
    pwd_hash, salt = hash_password("ValidPassword1", iterations=1000)
    db.create_user("Alice", pwd_hash, salt)
    
    # Insert 10 messages
    for i in range(1, 11):
        db.save_message("general", "Alice", f"Message #{i}")
        
    # Get last 5 messages
    recent_5 = db.get_room_messages("general", limit=5)
    assert len(recent_5) == 5
    assert recent_5[-1]["content"] == "Message #10"
    assert recent_5[0]["content"] == "Message #6"
    
    # Get older 5 messages before the oldest one in recent_5
    oldest_id = recent_5[0]["id"]
    older_5 = db.get_room_messages("general", limit=5, before_id=oldest_id)
    assert len(older_5) == 5
    assert older_5[-1]["content"] == "Message #5"
    assert older_5[0]["content"] == "Message #1"


def test_audit_logging(db):
    # Ensure audit log insertion succeeds without error
    db.log_audit_event(user_id=1, event_type="login_success", ip_address="127.0.0.1")
    db.log_audit_event(user_id=None, event_type="server_start", ip_address=None)
