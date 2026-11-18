"""
Unit tests for RoomManager in-memory tracking.
"""

from server.room_manager import RoomManager


class MockHandler:
    def __init__(self, username: str):
        self.username = username


def test_room_manager_lifecycle():
    mgr = RoomManager(default_room="general")
    h1 = MockHandler("Alice")
    h2 = MockHandler("Bob")
    
    # Joining general
    assert mgr.join_room("general", h1) is True
    assert mgr.join_room("general", h1) is False  # Already joined
    assert mgr.join_room("general", h2) is True
    
    members = mgr.get_room_member_usernames("general")
    assert "Alice" in members
    assert "Bob" in members
    assert len(members) == 2
    
    # Alice joins another room
    assert mgr.join_room("dev", h1) is True
    assert mgr.is_client_in_room("dev", h1) is True
    assert mgr.is_client_in_room("dev", h2) is False
    
    # Check client rooms
    h1_rooms = mgr.get_client_rooms(h1)
    assert "general" in h1_rooms
    assert "dev" in h1_rooms
    
    # Alice leaves dev
    assert mgr.leave_room("dev", h1) is True
    assert mgr.is_client_in_room("dev", h1) is False
    
    # Bob leaves all rooms
    left = mgr.leave_all_rooms(h2)
    assert "general" in left
    assert len(mgr.get_room_member_usernames("general")) == 1
