"""
Sidebar navigation component for Connect Chat Application.
Displays brand, user profile, rooms list with unread badges, active members,
and action buttons for creating rooms, settings, and logging out.
"""

import tkinter as tk
from tkinter import simpledialog, ttk
from typing import Callable, Dict, List, Optional
from utils.validators import sanitize_room_name, validate_room_name
from gui.theme import ThemeManager


class RoomSidebar(tk.Frame):
    """Modern floating sidebar for room navigation and member listing."""

    def __init__(
        self,
        parent: tk.Widget,
        theme_manager: ThemeManager,
        on_room_selected: Callable[[str], None],
        on_create_room: Callable[[str], None],
        on_open_settings: Callable[[], None],
        on_logout: Callable[[], None]
    ):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.on_room_selected = on_room_selected
        self.on_create_room = on_create_room
        self.on_open_settings = on_open_settings
        self.on_logout = on_logout

        self.current_username = ""
        self.active_room = "general"
        self.rooms: List[str] = ["general"]
        self.room_unreads: Dict[str, int] = {}
        self.members: List[str] = []

        self._room_buttons: Dict[str, tk.Button] = {}

        self._build_ui()
        self.apply_theme()

    def _build_ui(self) -> None:
        colors = self.theme_manager.get_colors()

        # Top App Brand
        self.brand_frame = tk.Frame(self, bg=colors.surface, padx=16, pady=16)
        self.brand_frame.pack(fill="x")

        self.lbl_brand = tk.Label(
            self.brand_frame,
            text="CONNECT",
            font=(self.theme_manager.font_family, 14, "bold"),
            bg=colors.surface,
            fg=colors.accent
        )
        self.lbl_brand.pack(anchor="w")

        # User Status Pill
        self.user_frame = tk.Frame(self.brand_frame, bg=colors.surface_secondary, padx=8, pady=4)
        self.user_frame.pack(fill="x", pady=(10, 0))

        self.dot_status = tk.Label(self.user_frame, text="●", font=self.theme_manager.font_small, bg=colors.surface_secondary, fg=colors.success)
        self.dot_status.pack(side="left", padx=(0, 6))

        self.lbl_user = tk.Label(
            self.user_frame,
            text="User",
            font=self.theme_manager.font_body_bold,
            bg=colors.surface_secondary,
            fg=colors.text
        )
        self.lbl_user.pack(side="left")

        # Divider
        self.div1 = tk.Frame(self, height=1, bg=colors.border)
        self.div1.pack(fill="x")

        # ROOMS Header Frame
        self.rooms_header_frame = tk.Frame(self, bg=colors.surface, padx=16, pady=10)
        self.rooms_header_frame.pack(fill="x")

        self.lbl_rooms_header = tk.Label(
            self.rooms_header_frame,
            text="ROOMS",
            font=self.theme_manager.font_timestamp,
            bg=colors.surface,
            fg=colors.text_muted
        )
        self.lbl_rooms_header.pack(side="left")

        self.btn_new_room = tk.Button(
            self.rooms_header_frame,
            text="+ New",
            font=self.theme_manager.font_timestamp,
            bg=colors.surface_secondary,
            fg=colors.accent,
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=6,
            pady=2,
            command=self._prompt_create_room
        )
        self.btn_new_room.pack(side="right")

        # Scrollable Rooms Container
        self.rooms_container = tk.Frame(self, bg=colors.surface, padx=8)
        self.rooms_container.pack(fill="x", pady=(0, 10))

        # Divider
        self.div2 = tk.Frame(self, height=1, bg=colors.border)
        self.div2.pack(fill="x")

        # MEMBERS Header
        self.members_header_frame = tk.Frame(self, bg=colors.surface, padx=16, pady=10)
        self.members_header_frame.pack(fill="x")

        self.lbl_members_header = tk.Label(
            self.members_header_frame,
            text="ONLINE MEMBERS (0)",
            font=self.theme_manager.font_timestamp,
            bg=colors.surface,
            fg=colors.text_muted
        )
        self.lbl_members_header.pack(anchor="w")

        # Members Listbox Frame
        self.members_frame = tk.Frame(self, bg=colors.surface, padx=12)
        self.members_frame.pack(fill="both", expand=True)

        self.members_listbox = tk.Listbox(
            self.members_frame,
            bg=colors.surface,
            fg=colors.text,
            selectbackground=colors.surface_secondary,
            selectforeground=colors.text,
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=self.theme_manager.font_small,
            activestyle="none"
        )
        self.members_listbox.pack(fill="both", expand=True)

        # Bottom Actions Frame (Settings & Logout)
        self.bottom_frame = tk.Frame(self, bg=colors.surface, padx=16, pady=12)
        self.bottom_frame.pack(fill="x", side="bottom")

        self.btn_settings = tk.Button(
            self.bottom_frame,
            text="⚙ Preferences",
            font=self.theme_manager.font_small,
            bg=colors.surface_secondary,
            fg=colors.text,
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self.on_open_settings
        )
        self.btn_settings.pack(side="left", fill="x", expand=True, padx=(0, 4), ipady=4)

        self.btn_logout = tk.Button(
            self.bottom_frame,
            text="Logout",
            font=self.theme_manager.font_small,
            bg=colors.surface_secondary,
            fg=colors.danger,
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self.on_logout
        )
        self.btn_logout.pack(side="right", padx=(4, 0), ipady=4)

    def set_user(self, username: str) -> None:
        """Updates user badge."""
        self.current_username = username
        self.lbl_user.config(text=username)

    def set_rooms(self, rooms: List[str], active_room: str) -> None:
        """Refreshes the room list buttons."""
        self.rooms = rooms
        self.active_room = active_room
        self._render_rooms()

    def set_members(self, members: List[str]) -> None:
        """Updates the active members listbox."""
        self.members = members
        self.lbl_members_header.config(text=f"ONLINE MEMBERS ({len(members)})")
        self.members_listbox.delete(0, tk.END)
        for m in sorted(members):
            prefix = "★ " if m == self.current_username else "• "
            self.members_listbox.insert(tk.END, f"{prefix}{m}")

    def mark_unread(self, room_name: str) -> None:
        """Increments unread count for a non-active room."""
        if room_name.lower() != self.active_room.lower():
            self.room_unreads[room_name] = self.room_unreads.get(room_name, 0) + 1
            self._render_rooms()

    def clear_unread(self, room_name: str) -> None:
        """Resets unread count for a room."""
        if room_name in self.room_unreads:
            del self.room_unreads[room_name]
            self._render_rooms()

    def _render_rooms(self) -> None:
        """Rebuilds room item buttons."""
        for child in self.rooms_container.winfo_children():
            child.destroy()
        self._room_buttons.clear()

        colors = self.theme_manager.get_colors()

        for room in self.rooms:
            is_active = (room.lower() == self.active_room.lower())
            unread = self.room_unreads.get(room, 0)

            # Room item frame
            item_frame = tk.Frame(
                self.rooms_container,
                bg=colors.surface_secondary if is_active else colors.surface,
                padx=8,
                pady=4
            )
            item_frame.pack(fill="x", pady=1)

            display_name = f"#{room}"
            lbl_name = tk.Label(
                item_frame,
                text=display_name,
                font=self.theme_manager.font_body_bold if is_active else self.theme_manager.font_body,
                bg=colors.surface_secondary if is_active else colors.surface,
                fg=colors.accent if is_active else colors.text,
                cursor="hand2"
            )
            lbl_name.pack(side="left")

            if unread > 0 and not is_active:
                lbl_badge = tk.Label(
                    item_frame,
                    text=f"● {unread}",
                    font=self.theme_manager.font_timestamp,
                    bg=colors.surface,
                    fg=colors.accent
                )
                lbl_badge.pack(side="right")
                lbl_badge.bind("<Button-1>", lambda e, r=room: self._on_select_room(r))

            # Bind clicks
            item_frame.bind("<Button-1>", lambda e, r=room: self._on_select_room(r))
            lbl_name.bind("<Button-1>", lambda e, r=room: self._on_select_room(r))

    def _on_select_room(self, room: str) -> None:
        """Handles user clicking a room."""
        if room.lower() == self.active_room.lower():
            return
        self.clear_unread(room)
        self.active_room = room
        self._render_rooms()
        self.on_room_selected(room)

    def _prompt_create_room(self) -> None:
        """Shows modal dialog to input new room name."""
        name = simpledialog.askstring("Create Room", "Enter room name (letters, numbers, underscores):", parent=self)
        if not name:
            return
        valid, err = validate_room_name(name)
        if not valid:
            from tkinter import messagebox
            messagebox.showwarning("Invalid Room Name", err, parent=self)
            return
        cleaned = sanitize_room_name(name)
        self.on_create_room(cleaned)

    def apply_theme(self) -> None:
        """Updates sidebar colors to match active theme."""
        colors = self.theme_manager.get_colors()
        self.config(bg=colors.surface)
        self.brand_frame.config(bg=colors.surface)
        self.lbl_brand.config(bg=colors.surface, fg=colors.accent)
        self.user_frame.config(bg=colors.surface_secondary)
        self.dot_status.config(bg=colors.surface_secondary, fg=colors.success)
        self.lbl_user.config(bg=colors.surface_secondary, fg=colors.text)
        self.div1.config(bg=colors.border)
        self.div2.config(bg=colors.border)
        self.rooms_header_frame.config(bg=colors.surface)
        self.lbl_rooms_header.config(bg=colors.surface, fg=colors.text_muted)
        self.btn_new_room.config(bg=colors.surface_secondary, fg=colors.accent)
        self.rooms_container.config(bg=colors.surface)
        self.members_header_frame.config(bg=colors.surface)
        self.lbl_members_header.config(bg=colors.surface, fg=colors.text_muted)
        self.members_frame.config(bg=colors.surface)
        self.members_listbox.config(bg=colors.surface, fg=colors.text, selectbackground=colors.surface_secondary)
        self.bottom_frame.config(bg=colors.surface)
        self.btn_settings.config(bg=colors.surface_secondary, fg=colors.text)
        self.btn_logout.config(bg=colors.surface_secondary, fg=colors.danger)
        self._render_rooms()
