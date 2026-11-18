"""
Protocol serialization and stream framing for Connect Chat Application.
Implements newline-delimited JSON stream framing over TCP sockets.
"""

import json
from typing import Any, Dict, List, Optional, Tuple


class ProtocolError(Exception):
    """Raised when a protocol violation occurs."""
    pass


class Protocol:
    """Handles JSON serialization, framing, and packet generation."""

    DELIMITER = "\n"

    @classmethod
    def encode(cls, payload: Dict[str, Any]) -> bytes:
        """
        Serializes a Python dict into newline-delimited UTF-8 bytes.
        """
        json_str = json.dumps(payload, ensure_ascii=False)
        return (json_str + cls.DELIMITER).encode("utf-8")

    @classmethod
    def parse_stream(
        cls,
        buffer: str,
        max_packet_size: int = 65_536
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Parses complete JSON packets from a stream buffer.
        
        Args:
            buffer: Current unparsed string buffer.
            max_packet_size: Maximum allowed length for a single packet line.
            
        Returns:
            Tuple of (list_of_parsed_dicts, remaining_unparsed_buffer).
            
        Raises:
            ProtocolError: If an individual packet exceeds max_packet_size.
        """
        packets: List[Dict[str, Any]] = []
        
        while cls.DELIMITER in buffer:
            line, buffer = buffer.split(cls.DELIMITER, 1)
            
            # Check maximum size constraint
            if len(line) > max_packet_size:
                raise ProtocolError(f"Packet exceeded max size limit of {max_packet_size} bytes.")
            
            line = line.strip()
            if not line:
                continue  # Skip empty lines
                
            try:
                data = json.loads(line)
                if isinstance(data, dict):
                    packets.append(data)
                else:
                    # Non-dictionary payload received
                    continue
            except json.JSONDecodeError:
                # Malformed JSON packet - skip safely without crashing
                continue
                
        # If the incomplete remnant exceeds max_packet_size without a delimiter, abort
        if len(buffer) > max_packet_size:
            raise ProtocolError(f"Incomplete packet buffer exceeded {max_packet_size} bytes.")
            
        return packets, buffer

    # ==================== Packet Builders ====================

    @staticmethod
    def success_response(
        action: str,
        data: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Builds a success response packet."""
        res = {
            "type": "response",
            "action": action,
            "status": "success",
            "data": data or {}
        }
        if request_id:
            res["request_id"] = request_id
        return res

    @staticmethod
    def error_response(
        action: str,
        error_message: str,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Builds an error response packet."""
        res = {
            "type": "response",
            "action": action,
            "status": "error",
            "error": error_message
        }
        if request_id:
            res["request_id"] = request_id
        return res

    @staticmethod
    def broadcast_event(event: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Builds a real-time broadcast event packet."""
        return {
            "type": "broadcast",
            "event": event,
            "data": data
        }

    @staticmethod
    def notification(message: str, level: str = "info") -> Dict[str, Any]:
        """Builds a system notification packet."""
        return {
            "type": "notification",
            "level": level,
            "message": message
        }
