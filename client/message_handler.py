"""
Message handler and event dispatcher for the client.
Routes incoming socket packets to UI callbacks and resolves pending request promises.
"""

from typing import Any, Callable, Dict, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class MessageHandler:
    """Dispatches incoming packets to registered handlers and pending request callbacks."""

    def __init__(self):
        # Maps request_id -> Callback(response_dict)
        self._pending_requests: Dict[str, Callable[[Dict[str, Any]], None]] = {}
        
        # Broadcast event callbacks
        self.on_new_message: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_user_joined: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_user_left: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_room_created: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_room_members_updated: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_server_shutdown: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_connection_lost: Optional[Callable[[str], None]] = None

    def register_pending_request(self, req_id: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Associates a request_id with a callback to run upon response."""
        self._pending_requests[req_id] = callback

    def process_packet(self, packet: Dict[str, Any]) -> None:
        """Processes a single packet received from the network queue."""
        packet_type = packet.get("type")
        
        if packet_type == "response":
            req_id = packet.get("request_id")
            if req_id and req_id in self._pending_requests:
                callback = self._pending_requests.pop(req_id)
                try:
                    callback(packet)
                except Exception as e:
                    logger.error(f"Error executing callback for request {req_id}: {e}")
            else:
                logger.debug(f"Received response without pending callback: {packet}")
                
        elif packet_type == "broadcast":
            event = packet.get("event")
            data = packet.get("data", {})
            
            if event == "new_message" and self.on_new_message:
                self.on_new_message(data)
            elif event == "user_joined" and self.on_user_joined:
                self.on_user_joined(data)
            elif event == "user_left" and self.on_user_left:
                self.on_user_left(data)
            elif event == "room_created" and self.on_room_created:
                self.on_room_created(data)
            elif event == "room_members_updated" and self.on_room_members_updated:
                self.on_room_members_updated(data)
            elif event == "server_shutdown" and self.on_server_shutdown:
                self.on_server_shutdown(data)
                
        elif packet_type == "connection_event":
            event = packet.get("event")
            reason = packet.get("reason", "Connection lost")
            if event == "disconnected" and self.on_connection_lost:
                self.on_connection_lost(reason)
                
        elif packet_type == "notification":
            logger.info(f"System Notification: {packet.get('message')}")
