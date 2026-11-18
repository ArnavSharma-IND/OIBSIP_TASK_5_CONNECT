"""
Client handler running on a dedicated thread per connection.
Manages socket lifecycle, protocol parsing, authentication, room subscriptions,
and real-time message routing.
"""

import socket
import threading
from typing import Any, Dict, List, Optional
from utils.emoji import replace_shortcodes
from utils.logger import get_logger
from utils.timestamps import get_current_timestamp_str
from utils.validators import (
    sanitize_room_name,
    validate_message_content,
    validate_password,
    validate_room_name,
    validate_username,
)
from server.auth import hash_password, verify_password
from server.protocol import Protocol, ProtocolError

logger = get_logger(__name__)


class ClientHandler(threading.Thread):
    """Handles an individual client connection in an independent thread."""

    def __init__(
        self,
        client_socket: socket.socket,
        client_address: tuple[str, int],
        server: Any
    ):
        super().__init__(daemon=True)
        self.sock = client_socket
        self.address = client_address
        self.server = server
        self.db = server.db
        self.session_manager = server.session_manager
        self.room_manager = server.room_manager
        self.config = server.config
        
        self.authenticated = False
        self.username: Optional[str] = None
        self.user_id: Optional[int] = None
        
        self._running = True
        self._send_lock = threading.Lock()

    def run(self) -> None:
        """Main reception loop for the client."""
        logger.info(f"Accepted connection from {self.address[0]}:{self.address[1]}")
        self.sock.settimeout(self.config.client_timeout)
        buffer = ""
        
        try:
            while self._running:
                try:
                    data_bytes = self.sock.recv(4096)
                except socket.timeout:
                    logger.debug(f"Socket timed out for {self.username or self.address}")
                    continue
                except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                    break
                    
                if not data_bytes:
                    # Connection closed by client
                    break
                    
                try:
                    chunk = data_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    # Ignore invalid byte sequences
                    continue
                    
                buffer += chunk
                
                try:
                    packets, buffer = Protocol.parse_stream(
                        buffer,
                        max_packet_size=self.config.max_packet_size
                    )
                except ProtocolError as pe:
                    logger.warning(f"Protocol error from {self.address}: {pe}")
                    self.send_packet(Protocol.error_response("protocol_error", str(pe)))
                    break
                    
                for packet in packets:
                    self._handle_packet(packet)
                    
        except Exception as e:
            logger.error(f"Unexpected error in client handler for {self.address}: {e}")
        finally:
            self.disconnect()

    def send_packet(self, payload: Dict[str, Any]) -> bool:
        """Thread-safe method to serialize and send a packet over the TCP socket."""
        with self._send_lock:
            if not self._running:
                return False
            try:
                data = Protocol.encode(payload)
                self.sock.sendall(data)
                return True
            except Exception as e:
                logger.debug(f"Failed to send packet to {self.username or self.address}: {e}")
                self._running = False
                return False

    def _handle_packet(self, packet: Dict[str, Any]) -> None:
        """Routes incoming packet to appropriate action handler."""
        action = packet.get("action")
        req_id = packet.get("request_id")
        
        if not action or not isinstance(action, str):
            self.send_packet(Protocol.error_response("unknown", "Action not specified.", req_id))
            return
            
        handler_method = getattr(self, f"_action_{action}", None)
        if not handler_method:
            self.send_packet(Protocol.error_response(action, f"Unknown action: '{action}'", req_id))
            return
            
        try:
            handler_method(packet, req_id)
        except Exception as e:
            logger.error(f"Error handling action '{action}' from {self.username or self.address}: {e}")
            self.send_packet(Protocol.error_response(action, "An internal server error occurred.", req_id))

    # ==================== Action Handlers ====================

    def _action_ping(self, packet: Dict[str, Any], req_id: Optional[str]) -> None:
        self.send_packet(Protocol.success_response("ping", {"status": "pong"}, req_id))

    def _action_register(self, packet: Dict[str, Any], req_id: Optional[str]) -> None:
        username = packet.get("username", "")
        password = packet.get("password", "")
        
        valid_u, err_u = validate_username(username)
        if not valid_u:
            self.send_packet(Protocol.error_response("register", err_u, req_id))
            return
            
        valid_p, err_p = validate_password(password)
        if not valid_p:
            self.send_packet(Protocol.error_response("register", err_p, req_id))
            return
            
        pwd_hash, salt = hash_password(password, iterations=self.config.pbkdf2_iterations)
        user_id = self.db.create_user(username, pwd_hash, salt)
        
        if not user_id:
            self.send_packet(Protocol.error_response("register", "Username already exists. Please choose another.", req_id))
            return
            
        self.db.log_audit_event(user_id, "user_registered", self.address[0])
        logger.info(f"User registered successfully: '{username}' (ID: {user_id})")
        self.send_packet(Protocol.success_response("register", {"username": username, "user_id": user_id}, req_id))

    def _action_login(self, packet: Dict[str, Any], req_id: Optional[str]) -> None:
        if self.authenticated:
            self.send_packet(Protocol.error_response("login", "Already logged in.", req_id))
            return
            
        username = packet.get("username", "")
        password = packet.get("password", "")
        
        if not username or not password:
            self.send_packet(Protocol.error_response("login", "Username and password required.", req_id))
            return
            
        user = self.db.get_user_by_username(username)
        if not user:
            self.send_packet(Protocol.error_response("login", "Invalid username or password.", req_id))
            return
            
        if not verify_password(password, user["password_hash"], user["salt"], iterations=self.config.pbkdf2_iterations):
            self.send_packet(Protocol.error_response("login", "Invalid username or password.", req_id))
            return
            
        # Prevent duplicate session
        if not self.session_manager.register_session(user["username"], self):
            self.send_packet(Protocol.error_response(
                "login",
                "This account is already logged in from another active session.",
                req_id
            ))
            return
            
        self.authenticated = True
        self.username = user["username"]
        self.user_id = user["id"]
        
        self.db.log_audit_event(self.user_id, "user_login", self.address[0])
        logger.info(f"User logged in: '{self.username}'")
        
        # Auto-join default room
        default_room = self.config.default_room
        self.room_manager.join_room(default_room, self)
        
        # Notify members in default room
        self._broadcast_to_room(
            default_room,
            Protocol.broadcast_event("user_joined", {
                "room_name": default_room,
                "username": self.username,
                "timestamp": get_current_timestamp_str()
            }),
            exclude_self=True
        )
        self._broadcast_room_members(default_room)
        
        # Retrieve rooms list
        all_rooms = self.db.get_all_rooms()
        
        # Retrieve default room history
        history = self.db.get_room_messages(default_room, limit=self.config.history_default_limit)
        
        self.send_packet(Protocol.success_response("login", {
            "username": self.username,
            "user_id": self.user_id,
            "current_room": default_room,
            "rooms": all_rooms,
            "history": history,
            "members": self.room_manager.get_room_member_usernames(default_room)
        }, req_id))

    def _action_create_room(self, packet: Dict[str, Any], req_id: Optional[str]) -> None:
        if not self.authenticated:
            self.send_packet(Protocol.error_response("create_room", "Authentication required.", req_id))
            return
            
        raw_name = packet.get("room_name", "")
        valid, err = validate_room_name(raw_name)
        if not valid:
            self.send_packet(Protocol.error_response("create_room", err, req_id))
            return
            
        room_name = sanitize_room_name(raw_name)
        room_id = self.db.create_room(room_name, self.user_id)
        
        if not room_id:
            self.send_packet(Protocol.error_response("create_room", f"Room '{room_name}' already exists.", req_id))
            return
            
        self.room_manager.ensure_room_exists(room_name)
        logger.info(f"Room '{room_name}' created by '{self.username}'")
        
        # Broadcast room creation to ALL active clients so sidebars update
        self.server.broadcast_all(Protocol.broadcast_event("room_created", {
            "id": room_id,
            "room_name": room_name,
            "created_by": self.username,
            "created_at": get_current_timestamp_str()
        }))
        
        self.send_packet(Protocol.success_response("create_room", {
            "id": room_id,
            "room_name": room_name
        }, req_id))

    def _action_join_room(self, packet: Dict[str, Any], req_id: Optional[str]) -> None:
        if not self.authenticated:
            self.send_packet(Protocol.error_response("join_room", "Authentication required.", req_id))
            return
            
        raw_name = packet.get("room_name", "")
        room_name = sanitize_room_name(raw_name)
        
        room_data = self.db.get_room_by_name(room_name)
        if not room_data:
            self.send_packet(Protocol.error_response("join_room", f"Room '{room_name}' does not exist.", req_id))
            return
            
        official_name = room_data["room_name"]
        is_new = self.room_manager.join_room(official_name, self)
        
        # Load history
        history = self.db.get_room_messages(official_name, limit=self.config.history_default_limit)
        members = self.room_manager.get_room_member_usernames(official_name)
        
        if is_new:
            # Broadcast user joined to other members in the room
            self._broadcast_to_room(
                official_name,
                Protocol.broadcast_event("user_joined", {
                    "room_name": official_name,
                    "username": self.username,
                    "timestamp": get_current_timestamp_str()
                }),
                exclude_self=True
            )
            self._broadcast_room_members(official_name)
            
        self.send_packet(Protocol.success_response("join_room", {
            "room_name": official_name,
            "history": history,
            "members": members
        }, req_id))

    def _action_leave_room(self, packet: Dict[str, Any], req_id: Optional[str]) -> None:
        if not self.authenticated:
            self.send_packet(Protocol.error_response("leave_room", "Authentication required.", req_id))
            return
            
        raw_name = packet.get("room_name", "")
        room_name = sanitize_room_name(raw_name)
        
        if room_name.lower() == self.config.default_room.lower():
            self.send_packet(Protocol.error_response("leave_room", f"Cannot leave the default #{self.config.default_room} room.", req_id))
            return
            
        removed = self.room_manager.leave_room(room_name, self)
        if removed:
            self._broadcast_to_room(
                room_name,
                Protocol.broadcast_event("user_left", {
                    "room_name": room_name,
                    "username": self.username,
                    "timestamp": get_current_timestamp_str()
                }),
                exclude_self=True
            )
            self._broadcast_room_members(room_name)
            
        self.send_packet(Protocol.success_response("leave_room", {"room_name": room_name}, req_id))

    def _action_send_message(self, packet: Dict[str, Any], req_id: Optional[str]) -> None:
        if not self.authenticated:
            self.send_packet(Protocol.error_response("send_message", "Authentication required.", req_id))
            return
            
        raw_room = packet.get("room_name", "")
        content = packet.get("content", "")
        
        valid_c, err_c = validate_message_content(content)
        if not valid_c:
            self.send_packet(Protocol.error_response("send_message", err_c, req_id))
            return
            
        room_name = sanitize_room_name(raw_room)
        
        # Verify client is actually subscribed to the room
        if not self.room_manager.is_client_in_room(room_name, self):
            self.send_packet(Protocol.error_response("send_message", f"You must join #{room_name} before sending messages.", req_id))
            return
            
        # Process shortcodes (e.g. :smile: -> 😄)
        processed_content = replace_shortcodes(content)
        timestamp = get_current_timestamp_str()
        
        # Save to DB
        msg_id = self.db.save_message(room_name, self.username, processed_content, timestamp)
        if not msg_id:
            self.send_packet(Protocol.error_response("send_message", "Failed to store message.", req_id))
            return
            
        msg_payload = {
            "id": msg_id,
            "room_name": room_name,
            "sender": self.username,
            "content": processed_content,
            "timestamp": timestamp
        }
        
        # Broadcast to everyone in the room (including sender)
        self._broadcast_to_room(
            room_name,
            Protocol.broadcast_event("new_message", msg_payload)
        )
        
        self.send_packet(Protocol.success_response("send_message", {"id": msg_id}, req_id))

    def _action_get_rooms(self, packet: Dict[str, Any], req_id: Optional[str]) -> None:
        if not self.authenticated:
            self.send_packet(Protocol.error_response("get_rooms", "Authentication required.", req_id))
            return
        rooms = self.db.get_all_rooms()
        self.send_packet(Protocol.success_response("get_rooms", {"rooms": rooms}, req_id))

    def _action_get_room_members(self, packet: Dict[str, Any], req_id: Optional[str]) -> None:
        if not self.authenticated:
            self.send_packet(Protocol.error_response("get_room_members", "Authentication required.", req_id))
            return
        raw_room = packet.get("room_name", "")
        room_name = sanitize_room_name(raw_room)
        members = self.room_manager.get_room_member_usernames(room_name)
        self.send_packet(Protocol.success_response("get_room_members", {
            "room_name": room_name,
            "members": members
        }, req_id))

    def _action_get_history(self, packet: Dict[str, Any], req_id: Optional[str]) -> None:
        if not self.authenticated:
            self.send_packet(Protocol.error_response("get_history", "Authentication required.", req_id))
            return
            
        raw_room = packet.get("room_name", "")
        room_name = sanitize_room_name(raw_room)
        limit = min(packet.get("limit", self.config.history_default_limit), self.config.history_max_limit)
        before_id = packet.get("before_id")
        
        history = self.db.get_room_messages(room_name, limit=limit, before_id=before_id)
        self.send_packet(Protocol.success_response("get_history", {
            "room_name": room_name,
            "history": history
        }, req_id))

    def _action_logout(self, packet: Dict[str, Any], req_id: Optional[str]) -> None:
        self.send_packet(Protocol.success_response("logout", {"status": "logged_out"}, req_id))
        self.disconnect()

    # ==================== Helpers & Disconnect ====================

    def _broadcast_to_room(self, room_name: str, payload: Dict[str, Any], exclude_self: bool = False) -> None:
        """Sends packet to all subscribers of room_name."""
        subscribers = self.room_manager.get_room_subscribers(room_name)
        for sub in subscribers:
            if exclude_self and sub == self:
                continue
            sub.send_packet(payload)

    def _broadcast_room_members(self, room_name: str) -> None:
        """Broadcasts updated member list to all room subscribers."""
        members = self.room_manager.get_room_member_usernames(room_name)
        self._broadcast_to_room(
            room_name,
            Protocol.broadcast_event("room_members_updated", {
                "room_name": room_name,
                "members": members
            })
        )

    def disconnect(self) -> None:
        """Cleans up client state, leaves rooms, unregisters session, and closes socket."""
        if not self._running:
            return
        self._running = False
        
        username = self.username
        if self.authenticated and username:
            self.session_manager.unregister_session(self)
            left_rooms = self.room_manager.leave_all_rooms(self)
            
            ts = get_current_timestamp_str()
            for room in left_rooms:
                self._broadcast_to_room(
                    room,
                    Protocol.broadcast_event("user_left", {
                        "room_name": room,
                        "username": username,
                        "timestamp": ts
                    })
                )
                self._broadcast_room_members(room)
                
            if self.user_id:
                self.db.log_audit_event(self.user_id, "user_disconnected", self.address[0])
            logger.info(f"User disconnected: '{username}' from {self.address}")
        else:
            logger.info(f"Connection closed for unauthenticated client {self.address}")
            
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass
            
        self.server.remove_handler(self)
