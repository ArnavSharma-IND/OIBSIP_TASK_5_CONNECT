"""
Client configuration manager.
Stores preferences such as server host, port, theme choice, and notification settings.
"""

import json
import os
from dataclasses import asdict, dataclass


@dataclass
class ClientConfig:
    host: str = "127.0.0.1"
    port: int = 5000
    saved_username: str = ""
    theme: str = "dark"
    sound_notifications: bool = True
    desktop_notifications: bool = True
    config_file: str = "client_config.json"

    @classmethod
    def load(cls, config_path: str = "client_config.json") -> "ClientConfig":
        """Loads client configuration from disk or returns default configuration."""
        cfg = cls(config_file=config_path)
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "host" in data:
                        cfg.host = str(data["host"])
                    if "port" in data:
                        cfg.port = int(data["port"])
                    if "saved_username" in data:
                        cfg.saved_username = str(data["saved_username"])
                    if "theme" in data:
                        cfg.theme = str(data["theme"]).lower()
                    if "sound_notifications" in data:
                        cfg.sound_notifications = bool(data["sound_notifications"])
                    if "desktop_notifications" in data:
                        cfg.desktop_notifications = bool(data["desktop_notifications"])
            except Exception:
                pass
        return cfg

    def save(self) -> None:
        """Persists current configuration to disk."""
        try:
            data = {
                "host": self.host,
                "port": self.port,
                "saved_username": self.saved_username,
                "theme": self.theme,
                "sound_notifications": self.sound_notifications,
                "desktop_notifications": self.desktop_notifications,
            }
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass
