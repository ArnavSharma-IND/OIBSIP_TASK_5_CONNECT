"""
Unit tests for protocol framing, serialization, and error handling.
"""

import pytest
from server.protocol import Protocol, ProtocolError


def test_encode_and_parse_single_packet():
    payload = {"action": "ping", "request_id": "1234"}
    encoded = Protocol.encode(payload)
    assert encoded.endswith(b"\n")
    
    text = encoded.decode("utf-8")
    packets, remaining = Protocol.parse_stream(text)
    assert len(packets) == 1
    assert packets[0] == payload
    assert remaining == ""


def test_parse_multiple_packets_in_stream():
    p1 = {"action": "login", "username": "alice"}
    p2 = {"action": "send_message", "content": "hi!"}
    
    stream = Protocol.encode(p1).decode("utf-8") + Protocol.encode(p2).decode("utf-8")
    packets, remaining = Protocol.parse_stream(stream)
    
    assert len(packets) == 2
    assert packets[0]["action"] == "login"
    assert packets[1]["action"] == "send_message"
    assert remaining == ""


def test_parse_partial_packet_buffering():
    full_str = '{"action": "ping"}\n{"action": "pong"}\n{"action": "partial"'
    packets, remaining = Protocol.parse_stream(full_str)
    
    assert len(packets) == 2
    assert packets[0]["action"] == "ping"
    assert packets[1]["action"] == "pong"
    assert remaining == '{"action": "partial"'
    
    # Complete the stream
    stream_continuation = remaining + '}\n'
    packets2, remaining2 = Protocol.parse_stream(stream_continuation)
    assert len(packets2) == 1
    assert packets2[0]["action"] == "partial"
    assert remaining2 == ""


def test_invalid_json_packet_handling():
    # Malformed packet line should be skipped without raising an unhandled exception
    stream = '{"invalid_json": broken}\n{"action": "valid"}\n'
    packets, remaining = Protocol.parse_stream(stream)
    assert len(packets) == 1
    assert packets[0]["action"] == "valid"


def test_max_packet_size_exceeded():
    huge_packet = "a" * 1000 + "\n"
    with pytest.raises(ProtocolError):
        Protocol.parse_stream(huge_packet, max_packet_size=500)


def test_packet_builders():
    success = Protocol.success_response("login", {"user_id": 1}, request_id="req1")
    assert success["type"] == "response"
    assert success["status"] == "success"
    assert success["data"]["user_id"] == 1
    assert success["request_id"] == "req1"

    err = Protocol.error_response("login", "Bad credentials", request_id="req2")
    assert err["type"] == "response"
    assert err["status"] == "error"
    assert err["error"] == "Bad credentials"

    bcast = Protocol.broadcast_event("user_joined", {"username": "Bob"})
    assert bcast["type"] == "broadcast"
    assert bcast["event"] == "user_joined"
