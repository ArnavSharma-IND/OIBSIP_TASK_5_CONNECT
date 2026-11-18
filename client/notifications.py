"""
Desktop and audio notifications manager.
Provides sound chimes, taskbar flash, and unread title updates.
"""

import sys
import time
from typing import Any, Optional
from utils.logger import get_logger

logger = get_logger(__name__)

# Try importing platform-specific sound
try:
    if sys.platform == "win32":
        import winsound
    else:
        winsound = None
except ImportError:
    winsound = None


class NotificationManager:
    """Manages audio alerts, window title badges, and notification cooldowns."""

    def __init__(self, sound_enabled: bool = True, desktop_enabled: bool = True):
        self.sound_enabled = sound_enabled
        self.desktop_enabled = desktop_enabled
        self.last_sound_time = 0.0
        self.sound_cooldown = 1.5  # Min seconds between audio alerts
        self._unread_count = 0
        self._root: Optional[Any] = None

    def set_root(self, root: Any) -> None:
        """Sets Tkinter root window reference for title updates and bell."""
        self._root = root

    def notify_new_message(
        self,
        sender: str,
        room_name: str,
        message: str,
        is_active_room: bool,
        is_window_focused: bool
    ) -> None:
        """
        Triggers notification if message arrived in background or window is unfocused.
        """
        # If user is in the active room and window is focused, do not notify
        if is_active_room and is_window_focused:
            return

        # Increment unread badge
        self._unread_count += 1
        self._update_window_title()

        # Play sound if enabled and cooldown passed
        if self.sound_enabled:
            now = time.time()
            if now - self.last_sound_time >= self.sound_cooldown:
                self.last_sound_time = now
                self._play_sound()

    def clear_unread(self) -> None:
        """Clears unread counter and resets window title."""
        self._unread_count = 0
        self._update_window_title()

    def _play_sound(self) -> None:
        """Plays subtle chime without blocking GUI."""
        try:
            if winsound and sys.platform == "win32":
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            elif self._root:
                self._root.bell()
        except Exception as e:
            logger.debug(f"Could not play audio alert: {e}")

    def _update_window_title(self) -> None:
        """Updates main application title with unread indicator."""
        if not self._root:
            return
        base_title = "Connect — Real-Time Chat"
        try:
            if self._unread_count > 0:
                self._root.title(f"({self._unread_count}) {base_title}")
            else:
                self._root.title(base_title)
        except Exception:
            pass
