"""
Client networking layer.
Runs socket I/O on a dedicated background thread and passes packets into
a thread-safe queue for the GUI thread.
"""

import queue
import socket
import threading
from typing import Any, Dict, Optional, Tuple
from utils.logger import get_logger
from client.protocol import ClientProtocol

logger = get_logger(__name__)


class NetworkClient:
    """Manages TCP socket connection, stream buffering, and background reception."""

    def __init__(self):
        self.sock: Optional[socket.socket] = None
        self.is_connected = False
        self._running = False
        self._recv_thread: Optional[threading.Thread] = None
        self._send_lock = threading.Lock()
        
        # Thread-safe queue for incoming parsed packets & connection events
        self.incoming_queue: queue.Queue = queue.Queue()

    def connect(self, host: str, port: int, timeout: float = 6.0) -> Tuple[bool, str]:
        """
        Connects to the chat server on host:port.
        Returns (success, error_message).
        """
        self.disconnect()
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(timeout)
            self.sock.connect((host, port))
            # Switch to blocking mode with timeout for reception loop
            self.sock.settimeout(1.0)
            
            self.is_connected = True
            self._running = True
            
            self._recv_thread = threading.Thread(
                target=self._receive_loop,
                daemon=True,
                name="ClientRecvThread"
            )
            self._recv_thread.start()
            
            logger.info(f"Connected to chat server at {host}:{port}")
            return True, ""
        except socket.timeout:
            self.disconnect()
            return False, f"Connection to {host}:{port} timed out."
        except ConnectionRefusedError:
            self.disconnect()
            return False, f"Connection refused at {host}:{port}. Is the server running?"
        except Exception as e:
            self.disconnect()
            return False, f"Failed to connect: {e}"

    def send_request(self, action: str, params: Optional[Dict[str, Any]] = None, req_id: Optional[str] = None) -> Tuple[bool, str]:
        """
        Builds and sends a request packet.
        Returns (success, request_id).
        """
        req = ClientProtocol.make_request(action, params, req_id)
        success = self.send_packet(req)
        return success, req["request_id"]

    def send_packet(self, payload: Dict[str, Any]) -> bool:
        """Serializes and sends a dictionary over the TCP socket."""
        with self._send_lock:
            if not self.is_connected or not self.sock:
                return False
            try:
                data = ClientProtocol.encode(payload)
                self.sock.sendall(data)
                return True
            except Exception as e:
                logger.error(f"Error sending packet: {e}")
                self._handle_disconnect("Network write error")
                return False

    def _receive_loop(self) -> None:
        """Background thread receiving and framing incoming packets."""
        buffer = ""
        while self._running and self.sock:
            try:
                chunk = self.sock.recv(4096)
                if not chunk:
                    # Server closed connection
                    self._handle_disconnect("Server closed the connection.")
                    break
                    
                text = chunk.decode("utf-8", errors="replace")
                buffer += text
                
                packets, buffer = ClientProtocol.parse_stream(buffer)
                for packet in packets:
                    self.incoming_queue.put(packet)
                    
            except socket.timeout:
                # Normal read timeout, keep looping
                continue
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                self._handle_disconnect("Connection lost unexpectedly.")
                break
            except Exception as e:
                if self._running:
                    logger.error(f"Error in receive loop: {e}")
                    self._handle_disconnect(f"Network error: {e}")
                break

    def _handle_disconnect(self, reason: str) -> None:
        """Internal handler when connection drops."""
        if not self.is_connected:
            return
        logger.warning(f"Disconnected from server: {reason}")
        self.is_connected = False
        self._running = False
        
        # Notify GUI via queue
        self.incoming_queue.put({
            "type": "connection_event",
            "event": "disconnected",
            "reason": reason
        })
        
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def disconnect(self) -> None:
        """Disconnects socket and terminates background thread."""
        self._running = False
        self.is_connected = False
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
        if self._recv_thread and self._recv_thread.is_alive():
            self._recv_thread.join(timeout=0.5)
        self._recv_thread = None
