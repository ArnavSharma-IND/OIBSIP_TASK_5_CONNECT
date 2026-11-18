"""
Room and member management module.
Tracks active room subscriptions and active members for message routing.
"""

import threading
from typing import Any, Dict, List, Set
from utils.logger import get_logger

logger = get_logger(__name__)


class RoomManager:
    """Manages active rooms and client subscriptions in memory with thread safety."""

    def __init__(self, default_room: str = "general"):
        self.default_room = default_room.strip().lower()
        self._lock = threading.Lock()
        
        # Maps lowercase room_name -> Set[ClientHandler]
        self._room_subscribers: Dict[str, Set[Any]] = {
            self.default_room: set()
        }
        
        # Maps ClientHandler -> Set[lowercase room_name]
        self._client_rooms: Dict[Any, Set[str]] = {}

    def ensure_room_exists(self, room_name: str) -> str:
        """Ensures the room key is tracked in memory. Returns normalized room key."""
        key = room_name.strip().lower()
        with self._lock:
            if key not in self._room_subscribers:
                self._room_subscribers[key] = set()
        return key

    def join_room(self, room_name: str, handler: Any) -> bool:
        """
        Subscribes a client to a room.
        Returns True if newly joined, False if already in room.
        """
        key = room_name.strip().lower()
        with self._lock:
            if key not in self._room_subscribers:
                self._room_subscribers[key] = set()
                
            if handler in self._room_subscribers[key]:
                return False  # Already joined
                
            self._room_subscribers[key].add(handler)
            
            if handler not in self._client_rooms:
                self._client_rooms[handler] = set()
            self._client_rooms[handler].add(key)
            return True

    def leave_room(self, room_name: str, handler: Any) -> bool:
        """
        Unsubscribes a client from a room.
        Returns True if removed, False if was not in room.
        """
        key = room_name.strip().lower()
        with self._lock:
            if key in self._room_subscribers and handler in self._room_subscribers[key]:
                self._room_subscribers[key].remove(handler)
                if handler in self._client_rooms:
                    self._client_rooms[handler].discard(key)
                return True
            return False

    def leave_all_rooms(self, handler: Any) -> List[str]:
        """
        Removes a client handler from all rooms they subscribed to.
        Returns the list of room names the client was in.
        """
        left_rooms = []
        with self._lock:
            rooms = self._client_rooms.pop(handler, set())
            for room_key in rooms:
                if room_key in self._room_subscribers:
                    self._room_subscribers[room_key].discard(handler)
                    left_rooms.append(room_key)
        return left_rooms

    def get_room_subscribers(self, room_name: str) -> List[Any]:
        """Returns a snapshot list of client handlers currently subscribed to the room."""
        key = room_name.strip().lower()
        with self._lock:
            if key in self._room_subscribers:
                return list(self._room_subscribers[key])
            return []

    def get_room_member_usernames(self, room_name: str) -> List[str]:
        """Returns list of usernames of all active subscribers in the room."""
        handlers = self.get_room_subscribers(room_name)
        usernames = []
        for h in handlers:
            name = getattr(h, "username", None)
            if name:
                usernames.append(name)
        return sorted(list(set(usernames)))

    def is_client_in_room(self, room_name: str, handler: Any) -> bool:
        """Checks if a client handler is subscribed to a room."""
        key = room_name.strip().lower()
        with self._lock:
            return key in self._client_rooms.get(handler, set())

    def get_client_rooms(self, handler: Any) -> List[str]:
        """Returns the list of room names the client is currently subscribed to."""
        with self._lock:
            return list(self._client_rooms.get(handler, set()))
