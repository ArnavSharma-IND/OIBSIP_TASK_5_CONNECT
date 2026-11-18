"""
Message history display component.
Renders message bubbles, timestamps, sender badges, system notifications,
and supports pagination for loading older messages.
"""

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, List, Optional
from utils.timestamps import format_display_time
from gui.theme import ThemeManager


class MessageView(tk.Frame):
    """Scrollable conversation view with rich message formatting."""

    def __init__(
        self,
        parent: tk.Widget,
        theme_manager: ThemeManager,
        on_load_older: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.on_load_older = on_load_older
        
        self.current_username = ""
        self.current_room = "general"
        self.has_older_messages = False
        self.oldest_message_id: Optional[int] = None

        self._build_ui()
        self.apply_theme()

    def _build_ui(self) -> None:
        colors = self.theme_manager.get_colors()

        # Room Header Bar
        self.header_frame = tk.Frame(self, bg=colors.surface, height=54, padx=20)
        self.header_frame.pack(fill="x", side="top")
        self.header_frame.pack_propagate(False)

        self.lbl_room_title = tk.Label(
            self.header_frame,
            text="#general",
            font=self.theme_manager.font_subtitle,
            bg=colors.surface,
            fg=colors.text
        )
        self.lbl_room_title.pack(side="left", pady=12)

        self.lbl_room_info = tk.Label(
            self.header_frame,
            text="Channel",
            font=self.theme_manager.font_small,
            bg=colors.surface,
            fg=colors.text_muted
        )
        self.lbl_room_info.pack(side="left", padx=(10, 0), pady=14)

        # Header bottom border
        self.header_divider = tk.Frame(self, height=1, bg=colors.border)
        self.header_divider.pack(fill="x", side="top")

        # Scrollable Text Container
        self.text_container = tk.Frame(self, bg=colors.bg)
        self.text_container.pack(fill="both", expand=True)

        self.scrollbar = tk.Scrollbar(self.text_container, orient="vertical")
        self.scrollbar.pack(side="right", fill="y")

        self.text_widget = tk.Text(
            self.text_container,
            wrap="word",
            state="disabled",
            bg=colors.bg,
            fg=colors.text,
            relief="flat",
            bd=0,
            padx=20,
            pady=16,
            font=self.theme_manager.font_body,
            yscrollcommand=self.scrollbar.set
        )
        self.text_widget.pack(fill="both", expand=True, side="left")
        self.scrollbar.config(command=self.text_widget.yview)

        # Pagination Button Header inside Text Widget
        self.btn_older = tk.Button(
            self.text_widget,
            text="↑ Load older messages",
            font=self.theme_manager.font_timestamp,
            bg=colors.surface_secondary,
            fg=colors.accent,
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=10,
            pady=4,
            command=self._on_load_older_clicked
        )

        self._configure_tags()

    def _configure_tags(self) -> None:
        """Sets up tag styling for sender, timestamps, self vs other messages."""
        colors = self.theme_manager.get_colors()
        
        # Tags for Others
        self.text_widget.tag_config(
            "sender_other",
            foreground=colors.accent,
            font=self.theme_manager.font_body_bold,
            lmargin1=10,
            lmargin2=10
        )
        self.text_widget.tag_config(
            "time_other",
            foreground=colors.text_muted,
            font=self.theme_manager.font_timestamp
        )
        self.text_widget.tag_config(
            "content_other",
            foreground=colors.text,
            font=self.theme_manager.font_body,
            lmargin1=10,
            lmargin2=10,
            spacing3=8
        )

        # Tags for Self (Sent messages)
        self.text_widget.tag_config(
            "sender_self",
            foreground=colors.accent,
            font=self.theme_manager.font_body_bold,
            justify="right",
            rmargin=10
        )
        self.text_widget.tag_config(
            "time_self",
            foreground=colors.text_muted,
            font=self.theme_manager.font_timestamp,
            justify="right",
            rmargin=10
        )
        self.text_widget.tag_config(
            "content_self",
            foreground=colors.text,
            font=self.theme_manager.font_body,
            justify="right",
            rmargin=10,
            spacing3=8
        )

        # System Event Tag
        self.text_widget.tag_config(
            "system_event",
            foreground=colors.text_muted,
            font=self.theme_manager.font_small,
            justify="center",
            spacing1=6,
            spacing3=6
        )

    def set_room_info(self, room_name: str, member_count: int = 1) -> None:
        """Updates room title and member count."""
        self.current_room = room_name
        self.lbl_room_title.config(text=f"#{room_name}")
        self.lbl_room_info.config(text=f"{member_count} member{'s' if member_count != 1 else ''}")

    def clear(self) -> None:
        """Clears all text from view."""
        self.text_widget.config(state="normal")
        self.text_widget.delete("1.0", tk.END)
        self.text_widget.config(state="disabled")
        self.oldest_message_id = None

    def load_history(self, messages: List[Dict[str, Any]], has_more: bool = False) -> None:
        """Loads and displays a list of message history dicts."""
        self.clear()
        self.has_older_messages = has_more
        
        self.text_widget.config(state="normal")
        if self.has_older_messages and self.on_load_older:
            self.text_widget.window_create("1.0", window=self.btn_older)
            self.text_widget.insert("2.0", "\n\n")

        for msg in messages:
            self._append_message_internal(msg, scroll=False)
            if self.oldest_message_id is None or (msg.get("id") and msg["id"] < self.oldest_message_id):
                self.oldest_message_id = msg.get("id")

        self.text_widget.config(state="disabled")
        self.scroll_to_bottom()

    def prepend_older_history(self, older_messages: List[Dict[str, Any]], has_more: bool = False) -> None:
        """Inserts older historical messages at the top."""
        if not older_messages:
            return
            
        self.has_older_messages = has_more
        self.text_widget.config(state="normal")

        # Save scroll position
        for msg in reversed(older_messages):
            sender = msg.get("sender", "Unknown")
            content = msg.get("content", "")
            raw_ts = msg.get("timestamp")
            time_display = format_display_time(raw_ts)
            is_self = (sender.lower() == self.current_username.lower())

            # Insert at beginning
            insert_pos = "2.0" if self.has_older_messages else "1.0"
            if is_self:
                self.text_widget.insert(insert_pos, f"{content}\n", "content_self")
                self.text_widget.insert(insert_pos, f"You  {time_display}\n", ("sender_self", "time_self"))
            else:
                self.text_widget.insert(insert_pos, f"{content}\n", "content_other")
                self.text_widget.insert(insert_pos, f"{sender}  {time_display}\n", ("sender_other", "time_other"))

            if self.oldest_message_id is None or (msg.get("id") and msg["id"] < self.oldest_message_id):
                self.oldest_message_id = msg.get("id")

        self.text_widget.config(state="disabled")

    def add_message(self, msg: Dict[str, Any]) -> None:
        """Appends a new real-time message and scrolls to bottom."""
        self.text_widget.config(state="normal")
        self._append_message_internal(msg, scroll=True)
        self.text_widget.config(state="disabled")
        self.scroll_to_bottom()

    def _append_message_internal(self, msg: Dict[str, Any], scroll: bool = True) -> None:
        """Internal helper to insert a message into text widget."""
        sender = msg.get("sender", "Unknown")
        content = msg.get("content", "")
        raw_ts = msg.get("timestamp")
        time_display = format_display_time(raw_ts)
        is_self = (sender.lower() == self.current_username.lower())

        if is_self:
            self.text_widget.insert(tk.END, f"You  ", "sender_self")
            self.text_widget.insert(tk.END, f"{time_display}\n", "time_self")
            self.text_widget.insert(tk.END, f"{content}\n\n", "content_self")
        else:
            self.text_widget.insert(tk.END, f"{sender}  ", "sender_other")
            self.text_widget.insert(tk.END, f"{time_display}\n", "time_other")
            self.text_widget.insert(tk.END, f"{content}\n\n", "content_other")

    def add_system_event(self, text: str) -> None:
        """Appends a centered system event message (e.g. user joined or left)."""
        self.text_widget.config(state="normal")
        self.text_widget.insert(tk.END, f"— {text} —\n\n", "system_event")
        self.text_widget.config(state="disabled")
        self.scroll_to_bottom()

    def scroll_to_bottom(self) -> None:
        """Scrolls text widget to very end."""
        self.text_widget.see(tk.END)

    def _on_load_older_clicked(self) -> None:
        """Callback when user clicks load older messages."""
        if self.on_load_older:
            self.on_load_older()

    def apply_theme(self) -> None:
        """Updates colors according to ThemeManager."""
        colors = self.theme_manager.get_colors()
        self.config(bg=colors.bg)
        self.header_frame.config(bg=colors.surface)
        self.lbl_room_title.config(bg=colors.surface, fg=colors.text)
        self.lbl_room_info.config(bg=colors.surface, fg=colors.text_muted)
        self.header_divider.config(bg=colors.border)
        self.text_container.config(bg=colors.bg)
        self.text_widget.config(bg=colors.bg, fg=colors.text)
        self.btn_older.config(bg=colors.surface_secondary, fg=colors.accent)
        self._configure_tags()
