"""
TCP Chat Server for Connect Application.
Manages socket binding, client connection acceptance, and graceful shutdown.
"""

import socket
import threading
from typing import List, Optional, Set
from utils.logger import get_logger
from server.auth import SessionManager
from server.client_handler import ClientHandler
from server.config import ServerConfig, load_server_config
from server.database import DatabaseManager
from server.protocol import Protocol
from server.room_manager import RoomManager

logger = get_logger(__name__)


class TCPServer:
    """Main TCP Server orchestrating database, sessions, rooms, and client handlers."""

    def __init__(self, config: Optional[ServerConfig] = None):
        self.config = config or load_server_config()
        self.db = DatabaseManager(self.config.db_path, self.config.default_room)
        self.session_manager = SessionManager()
        self.room_manager = RoomManager(self.config.default_room)
        
        self.server_socket: Optional[socket.socket] = None
        self._handlers_lock = threading.Lock()
        self._handlers: Set[ClientHandler] = set()
        
        self.is_running = False
        self._accept_thread: Optional[threading.Thread] = None

    def start(self, block: bool = True) -> None:
        """
        Initializes TCP socket, binds to host and port, and starts accepting clients.
        If block is True, joins accept thread.
        """
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.config.host, self.config.port))
            self.server_socket.listen(128)
            self.is_running = True
            logger.info(f"=== Connect Chat Server running on {self.config.host}:{self.config.port} ===")
        except Exception as e:
            logger.error(f"Failed to bind server socket to {self.config.host}:{self.config.port}: {e}")
            raise
            
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True, name="AcceptLoop")
        self._accept_thread.start()
        
        if block:
            try:
                self._accept_thread.join()
            except KeyboardInterrupt:
                logger.info("Server received interrupt signal.")
                self.stop()

    def _accept_loop(self) -> None:
        """Continuously accepts incoming client connections."""
        while self.is_running:
            try:
                client_sock, client_addr = self.server_socket.accept()
                handler = ClientHandler(client_sock, client_addr, self)
                with self._handlers_lock:
                    self._handlers.add(handler)
                handler.start()
            except (socket.error, OSError) as e:
                if not self.is_running:
                    break
                logger.error(f"Accept error: {e}")

    def broadcast_all(self, payload: dict) -> None:
        """Broadcasts a packet to all connected clients."""
        with self._handlers_lock:
            handlers_copy = list(self._handlers)
        for h in handlers_copy:
            h.send_packet(payload)

    def remove_handler(self, handler: ClientHandler) -> None:
        """Removes a disconnected handler from the active registry."""
        with self._handlers_lock:
            self._handlers.discard(handler)

    def stop(self) -> None:
        """Gracefully terminates server, notifies connected clients, and cleans up sockets."""
        if not self.is_running:
            return
        logger.info("Stopping Connect Chat Server...")
        self.is_running = False
        
        # Notify clients about shutdown
        shutdown_packet = Protocol.broadcast_event("server_shutdown", {
            "message": "The chat server is shutting down. Please reconnect later."
        })
        self.broadcast_all(shutdown_packet)
        
        # Close listening socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
                
        # Disconnect all active client handlers
        with self._handlers_lock:
            handlers_copy = list(self._handlers)
        for h in handlers_copy:
            h.disconnect()
            
        logger.info("Connect Chat Server stopped successfully.")
