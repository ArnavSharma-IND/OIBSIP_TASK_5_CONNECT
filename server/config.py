"""
Server configuration module.
Loads settings from environment, optional config JSON, or sane defaults.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 5000
    db_path: str = "data/connect.db"
    default_room: str = "general"
    pbkdf2_iterations: int = 100_000
    salt_bytes: int = 16
    max_packet_size: int = 65_536  # 64 KB
    max_message_length: int = 2000
    history_default_limit: int = 50
    history_max_limit: int = 100
    client_timeout: float = 300.0  # 5 minutes socket timeout
    log_level: str = "INFO"
    log_file: Optional[str] = None


def load_server_config(config_path: Optional[str] = None) -> ServerConfig:
    """Loads configuration from file if provided/existing, otherwise returns defaults."""
    cfg = ServerConfig()
    
    # Priority: explicit path -> 'config.json' if exists
    path_to_check = config_path or "config.json"
    if os.path.isfile(path_to_check):
        try:
            with open(path_to_check, "r", encoding="utf-8") as f:
                data = json.load(f)
                server_data = data.get("server", data)
                if "host" in server_data:
                    cfg.host = str(server_data["host"])
                if "port" in server_data:
                    cfg.port = int(server_data["port"])
                if "db_path" in server_data:
                    cfg.db_path = str(server_data["db_path"])
                if "default_room" in server_data:
                    cfg.default_room = str(server_data["default_room"])
                if "pbkdf2_iterations" in server_data:
                    cfg.pbkdf2_iterations = int(server_data["pbkdf2_iterations"])
                if "max_packet_size" in server_data:
                    cfg.max_packet_size = int(server_data["max_packet_size"])
                if "max_message_length" in server_data:
                    cfg.max_message_length = int(server_data["max_message_length"])
                if "history_default_limit" in server_data:
                    cfg.history_default_limit = int(server_data["history_default_limit"])
                if "history_max_limit" in server_data:
                    cfg.history_max_limit = int(server_data["history_max_limit"])
                if "client_timeout" in server_data:
                    cfg.client_timeout = float(server_data["client_timeout"])
                if "log_level" in server_data:
                    cfg.log_level = str(server_data["log_level"])
        except Exception:
            pass  # Fallback to default
            
    # Ensure db directory exists
    db_dir = os.path.dirname(cfg.db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
        
    return cfg
