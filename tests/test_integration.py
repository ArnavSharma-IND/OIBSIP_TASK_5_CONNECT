"""
Integration tests for real TCP socket communication between multiple clients and server.
Tests multi-user messaging, room isolation, persistence, and graceful disconnection.
"""

import queue
import socket
import threading
import time
from typing import Any, Dict, Optional
import pytest
from server.config import ServerConfig
from server.protocol import Protocol
from server.server import TCPServer


class SimpleTestClient:
    """Helper socket client for integration testing."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self.incoming = queue.Queue()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.sock.settimeout(0.5)
        self._running = True
        self._thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._thread.start()

    def _recv_loop(self) -> None:
        buffer = ""
        while self._running and self.sock:
            try:
                data = self.sock.recv(4096)
                if not data:
                    break
                buffer += data.decode("utf-8", errors="replace")
                packets, buffer = Protocol.parse_stream(buffer)
                for p in packets:
                    self.incoming.put(p)
            except socket.timeout:
                continue
            except Exception:
                break

    def send(self, payload: Dict[str, Any]) -> None:
        if self.sock:
            self.sock.sendall(Protocol.encode(payload))

    def wait_for_packet(self, timeout: float = 3.0, predicate=None) -> Dict[str, Any]:
        """Waits for an incoming packet matching optional predicate."""
        start = time.time()
        while time.time() - start < timeout:
            try:
                p = self.incoming.get(timeout=0.2)
                if predicate is None or predicate(p):
                    return p
            except queue.Empty:
                continue
        raise TimeoutError("Timed out waiting for expected packet.")

    def close(self) -> None:
        self._running = False
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
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)


@pytest.fixture
def running_server(test_server_config):
    """Starts a live TCPServer on a dynamic port in a background thread."""
    # Find free port
    temp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    temp_sock.bind(("127.0.0.1", 0))
    free_port = temp_sock.getsockname()[1]
    temp_sock.close()

    test_server_config.port = free_port
    server = TCPServer(test_server_config)
    server.start(block=False)

    time.sleep(0.1)  # Allow accept loop to spin up
    yield server

    server.stop()


def test_full_client_server_integration(running_server):
    host = running_server.config.host
    port = running_server.config.port

    # 1. Connect Client 1 (Alice) and Client 2 (Bob)
    client_a = SimpleTestClient(host, port)
    client_b = SimpleTestClient(host, port)

    client_a.connect()
    client_b.connect()

    try:
        # 2. Register Alice
        client_a.send({
            "action": "register",
            "username": "Alice",
            "password": "Password123"
        })
        resp = client_a.wait_for_packet(predicate=lambda p: p.get("action") == "register")
        assert resp["status"] == "success"

        # 3. Attempt duplicate registration of Alice (case-insensitive) -> should fail
        client_b.send({
            "action": "register",
            "username": "alice",
            "password": "Password123"
        })
        resp_dup = client_b.wait_for_packet(predicate=lambda p: p.get("action") == "register")
        assert resp_dup["status"] == "error"

        # 4. Register Bob
        client_b.send({
            "action": "register",
            "username": "Bob",
            "password": "Password123"
        })
        resp_bob = client_b.wait_for_packet(predicate=lambda p: p.get("action") == "register")
        assert resp_bob["status"] == "success"

        # 5. Login Alice with incorrect password -> should fail
        client_a.send({
            "action": "login",
            "username": "Alice",
            "password": "WrongPassword1"
        })
        resp_bad_login = client_a.wait_for_packet(predicate=lambda p: p.get("action") == "login")
        assert resp_bad_login["status"] == "error"

        # 6. Login Alice with correct password
        client_a.send({
            "action": "login",
            "username": "Alice",
            "password": "Password123"
        })
        resp_alice_login = client_a.wait_for_packet(predicate=lambda p: p.get("action") == "login")
        assert resp_alice_login["status"] == "success"
        assert resp_alice_login["data"]["current_room"] == "general"

        # 7. Login Bob
        client_b.send({
            "action": "login",
            "username": "Bob",
            "password": "Password123"
        })
        resp_bob_login = client_b.wait_for_packet(predicate=lambda p: p.get("action") == "login")
        assert resp_bob_login["status"] == "success"

        # Alice should receive a broadcast that Bob joined #general
        join_broadcast = client_a.wait_for_packet(
            predicate=lambda p: p.get("type") == "broadcast" and p.get("event") == "user_joined"
        )
        assert join_broadcast["data"]["username"] == "Bob"
        assert join_broadcast["data"]["room_name"] == "general"

        # 8. Real-time message exchange in #general with emoji shortcode
        client_a.send({
            "action": "send_message",
            "room_name": "general",
            "content": "Hello Bob! :rocket: :smile:"
        })
        
        # Bob receives the real-time broadcast message
        bob_msg = client_b.wait_for_packet(
            predicate=lambda p: p.get("type") == "broadcast" and p.get("event") == "new_message"
        )
        assert bob_msg["data"]["sender"] == "Alice"
        assert bob_msg["data"]["room_name"] == "general"
        assert "🚀" in bob_msg["data"]["content"]
        assert "😄" in bob_msg["data"]["content"]

        # 9. Create Room 'project-x' by Alice
        client_a.send({
            "action": "create_room",
            "room_name": "project-x"
        })
        room_created_resp = client_a.wait_for_packet(predicate=lambda p: p.get("action") == "create_room")
        assert room_created_resp["status"] == "success"

        # Bob receives room_created event
        bob_room_event = client_b.wait_for_packet(
            predicate=lambda p: p.get("type") == "broadcast" and p.get("event") == "room_created"
        )
        assert bob_room_event["data"]["room_name"] == "project-x"

        # 10. Alice joins project-x
        client_a.send({
            "action": "join_room",
            "room_name": "project-x"
        })
        join_a_resp = client_a.wait_for_packet(predicate=lambda p: p.get("action") == "join_room")
        assert join_a_resp["status"] == "success"

        # 11. Room Isolation: Alice sends message in 'project-x'.
        # Since Bob has NOT joined 'project-x', Bob must NOT receive this message!
        client_a.send({
            "action": "send_message",
            "room_name": "project-x",
            "content": "Confidential plans in project-x"
        })
        
        # Give a small window to ensure Bob's queue does NOT receive project-x message
        time.sleep(0.3)
        while not client_b.incoming.empty():
            item = client_b.incoming.get()
            if item.get("type") == "broadcast" and item.get("event") == "new_message":
                assert item["data"]["room_name"] != "project-x"

        # 12. Bob joins 'project-x'
        client_b.send({
            "action": "join_room",
            "room_name": "project-x"
        })
        join_b_resp = client_b.wait_for_packet(predicate=lambda p: p.get("action") == "join_room")
        assert join_b_resp["status"] == "success"
        # Bob's initial join response should contain the previous message from project-x in history!
        history = join_b_resp["data"]["history"]
        assert len(history) >= 1
        assert history[0]["content"] == "Confidential plans in project-x"

        # 13. Graceful Disconnection
        client_a.send({"action": "logout"})
        logout_resp = client_a.wait_for_packet(predicate=lambda p: p.get("action") == "logout")
        assert logout_resp["status"] == "success"

        # Bob should receive user_left broadcast
        left_broadcast = client_b.wait_for_packet(
            predicate=lambda p: p.get("type") == "broadcast" and p.get("event") == "user_left"
        )
        assert left_broadcast["data"]["username"] == "Alice"

    finally:
        client_a.close()
        client_b.close()


def test_validation_and_room_rules_over_network(running_server):
    host = running_server.config.host
    port = running_server.config.port

    client = SimpleTestClient(host, port)
    client.connect()

    try:
        # Register user
        client.send({"action": "register", "username": "Charlie", "password": "Password123"})
        r = client.wait_for_packet(predicate=lambda p: p.get("action") == "register")
        assert r["status"] == "success"

        # Login
        client.send({"action": "login", "username": "Charlie", "password": "Password123"})
        r = client.wait_for_packet(predicate=lambda p: p.get("action") == "login")
        assert r["status"] == "success"

        # 1. Reject empty message
        client.send({"action": "send_message", "room_name": "general", "content": "   "})
        r = client.wait_for_packet(predicate=lambda p: p.get("action") == "send_message")
        assert r["status"] == "error"
        assert "cannot be empty" in r["error"].lower()

        # 2. Reject sending message to room not joined
        client.send({"action": "send_message", "room_name": "random_unjoined", "content": "Hello"})
        r = client.wait_for_packet(predicate=lambda p: p.get("action") == "send_message")
        assert r["status"] == "error"

        # 3. Prevent leaving default #general room
        client.send({"action": "leave_room", "room_name": "general"})
        r = client.wait_for_packet(predicate=lambda p: p.get("action") == "leave_room")
        assert r["status"] == "error"

        # 4. Create and leave custom room
        client.send({"action": "create_room", "room_name": "temp-room"})
        client.wait_for_packet(predicate=lambda p: p.get("action") == "create_room")

        client.send({"action": "join_room", "room_name": "temp-room"})
        client.wait_for_packet(predicate=lambda p: p.get("action") == "join_room")

        client.send({"action": "leave_room", "room_name": "temp-room"})
        r_leave = client.wait_for_packet(predicate=lambda p: p.get("action") == "leave_room")
        assert r_leave["status"] == "success"

    finally:
        client.close()


def test_three_simultaneous_clients_broadcast(running_server):
    host = running_server.config.host
    port = running_server.config.port

    c1 = SimpleTestClient(host, port)
    c2 = SimpleTestClient(host, port)
    c3 = SimpleTestClient(host, port)

    c1.connect()
    c2.connect()
    c3.connect()

    try:
        # Register and login all 3
        for client, name in [(c1, "User1"), (c2, "User2"), (c3, "User3")]:
            client.send({"action": "register", "username": name, "password": "Password123"})
            client.wait_for_packet(predicate=lambda p: p.get("action") == "register")
            client.send({"action": "login", "username": name, "password": "Password123"})
            client.wait_for_packet(predicate=lambda p: p.get("action") == "login")

        # c1 sends message
        c1.send({"action": "send_message", "room_name": "general", "content": "Broadcast test!"})

        # All 3 clients should receive the message
        m1 = c1.wait_for_packet(predicate=lambda p: p.get("event") == "new_message")
        m2 = c2.wait_for_packet(predicate=lambda p: p.get("event") == "new_message")
        m3 = c3.wait_for_packet(predicate=lambda p: p.get("event") == "new_message")

        assert m1["data"]["content"] == "Broadcast test!"
        assert m2["data"]["content"] == "Broadcast test!"
        assert m3["data"]["content"] == "Broadcast test!"

    finally:
        c1.close()
        c2.close()
        c3.close()

