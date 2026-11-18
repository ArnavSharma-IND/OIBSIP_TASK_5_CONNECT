"""
Client-side protocol helpers and packet builders.
"""

import json
import uuid
from typing import Any, Dict, List, Optional, Tuple


class ClientProtocol:
    """Provides client request builders and stream parsing."""

    DELIMITER = "\n"

    @classmethod
    def encode(cls, payload: Dict[str, Any]) -> bytes:
        """Serializes dictionary to UTF-8 encoded newline-delimited bytes."""
        json_str = json.dumps(payload, ensure_ascii=False)
        return (json_str + cls.DELIMITER).encode("utf-8")

    @classmethod
    def parse_stream(
        cls,
        buffer: str,
        max_packet_size: int = 65_536
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Extracts complete packets from string buffer.
        Returns (packets, remaining_buffer).
        """
        packets: List[Dict[str, Any]] = []
        while cls.DELIMITER in buffer:
            line, buffer = buffer.split(cls.DELIMITER, 1)
            line = line.strip()
            if not line:
                continue
            if len(line) > max_packet_size:
                continue
            try:
                data = json.loads(line)
                if isinstance(data, dict):
                    packets.append(data)
            except json.JSONDecodeError:
                continue
        return packets, buffer

    @staticmethod
    def new_req_id() -> str:
        """Generates a unique request identifier."""
        return str(uuid.uuid4())[:8]

    @classmethod
    def make_request(cls, action: str, params: Optional[Dict[str, Any]] = None, req_id: Optional[str] = None) -> Dict[str, Any]:
        """Constructs a standard request payload."""
        req: Dict[str, Any] = {
            "action": action,
            "request_id": req_id or cls.new_req_id()
        }
        if params:
            req.update(params)
        return req
