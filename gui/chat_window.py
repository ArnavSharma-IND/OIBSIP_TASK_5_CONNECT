"""
Main Chat Window orchestrating Sidebar, Message View, Composer, and Network events.
Handles thread-safe queue polling via root.after() and window focus tracking.
"""

import queue
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict, List, Optional
from utils.logger import get_logger
from client.config import ClientConfig
from client.message_handler import MessageHandler
from client.network import NetworkClient
from client.notifications import NotificationManager
from gui.login_window import LoginFrame
from gui.message_composer import MessageComposer
from gui.message_view import MessageView
from gui.register_window import RegisterFrame
from gui.room_sidebar import RoomSidebar
from gui.settings import SettingsDialog
from gui.theme import ThemeManager

logger = get_logger(__name__)


class ConnectApp(tk.Tk):
    """Main Application Window for Connect."""

    def __init__(self, config_path: str = "client_config.json"):
        super().__init__()
        self.title("Connect — Real-Time Chat")
        self.geometry("1000x700")
        self.minsize(800, 550)

        self.client_config = ClientConfig.load(config_path)
        self.theme_manager = ThemeManager(self.client_config.theme)
        self.network = NetworkClient()
        self.msg_handler = MessageHandler()
        self.notifications = NotificationManager(
            sound_enabled=self.client_config.sound_notifications,
            desktop_enabled=self.client_config.desktop_notifications
        )
        self.notifications.set_root(self)

        self.authenticated = False
        self.username = ""
        self.active_room = "general"
        self.is_window_focused = True

        self._setup_network_callbacks()
        self._bind_window_events()

        # Container for swappable screens (Login, Register, Chat)
        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self.login_view: Optional[LoginFrame] = None
        self.register_view: Optional[RegisterFrame] = None
        self.chat_frame: Optional[tk.Frame] = None

        self.show_login()
        self.theme_manager.apply_style(self)

        # Start periodic queue polling (50ms interval)
        self.after(50, self._poll_network_queue)

    def _bind_window_events(self) -> None:
        """Tracks window focus state for background notification logic."""
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_focus_in(self, event: tk.Event) -> None:
        self.is_window_focused = True
        self.notifications.clear_unread()

    def _on_focus_out(self, event: tk.Event) -> None:
        self.is_window_focused = False

    def _on_close(self) -> None:
        """Graceful window close."""
        if self.network.is_connected:
            try:
                self.network.send_request("logout")
            except Exception:
                pass
            self.network.disconnect()
        self.destroy()

    # ==================== Screen Navigation ====================

    def _clear_container(self) -> None:
        """Destroys current active screen widgets."""
        for child in self.container.winfo_children():
            child.destroy()
        self.login_view = None
        self.register_view = None
        self.chat_frame = None

    def show_login(self) -> None:
        """Displays login view."""
        self._clear_container()
        self.login_view = LoginFrame(
            parent=self.container,
            theme_manager=self.theme_manager,
            on_login_attempt=self._handle_login_attempt,
            on_switch_to_register=self.show_register,
            default_host=self.client_config.host,
            default_port=self.client_config.port,
            saved_username=self.client_config.saved_username
        )
        self.login_view.pack(fill="both", expand=True)

    def show_register(self) -> None:
        """Displays registration view."""
        self._clear_container()
        self.register_view = RegisterFrame(
            parent=self.container,
            theme_manager=self.theme_manager,
            on_register_attempt=self._handle_register_attempt,
            on_switch_to_login=self.show_login,
            default_host=self.client_config.host,
            default_port=self.client_config.port
        )
        self.register_view.pack(fill="both", expand=True)

    def show_chat(self, initial_data: Dict[str, Any]) -> None:
        """Displays main chat view."""
        self._clear_container()
        colors = self.theme_manager.get_colors()

        self.chat_frame = tk.Frame(self.container, bg=colors.bg)
        self.chat_frame.pack(fill="both", expand=True)

        # Left Sidebar (fixed width)
        self.sidebar = RoomSidebar(
            parent=self.chat_frame,
            theme_manager=self.theme_manager,
            on_room_selected=self._handle_switch_room,
            on_create_room=self._handle_create_room,
            on_open_settings=self._open_settings_dialog,
            on_logout=self._handle_logout
        )
        self.sidebar.pack(side="left", fill="y", ipadx=10)

        # Vertical Divider between sidebar and conversation
        self.v_divider = tk.Frame(self.chat_frame, width=1, bg=colors.border)
        self.v_divider.pack(side="left", fill="y")

        # Right Conversation Container
        self.right_container = tk.Frame(self.chat_frame, bg=colors.bg)
        self.right_container.pack(side="right", fill="both", expand=True)

        # Message History View
        self.message_view = MessageView(
            parent=self.right_container,
            theme_manager=self.theme_manager,
            on_load_older=self._handle_load_older_history
        )
        self.message_view.pack(fill="both", expand=True)

        # Message Composer
        self.composer = MessageComposer(
            parent=self.right_container,
            theme_manager=self.theme_manager,
            on_send_message=self._handle_send_message
        )
        self.composer.pack(fill="x", side="bottom")

        # Initialize Data
        self.username = initial_data.get("username", "")
        self.active_room = initial_data.get("current_room", "general")
        rooms_list = [r["room_name"] for r in initial_data.get("rooms", [])]
        if self.active_room not in rooms_list:
            rooms_list.append(self.active_room)
            
        members = initial_data.get("members", [])
        history = initial_data.get("history", [])

        self.sidebar.set_user(self.username)
        self.sidebar.set_rooms(rooms_list, self.active_room)
        self.sidebar.set_members(members)

        self.message_view.current_username = self.username
        self.message_view.set_room_info(self.active_room, len(members))
        self.message_view.load_history(history, has_more=(len(history) >= 50))

        self.composer.focus()

    # ==================== Network Callbacks Setup ====================

    def _setup_network_callbacks(self) -> None:
        """Registers handlers for broadcast events."""
        self.msg_handler.on_new_message = self._on_new_message_event
        self.msg_handler.on_user_joined = self._on_user_joined_event
        self.msg_handler.on_user_left = self._on_user_left_event
        self.msg_handler.on_room_created = self._on_room_created_event
        self.msg_handler.on_room_members_updated = self._on_room_members_updated_event
        self.msg_handler.on_server_shutdown = self._on_server_shutdown_event
        self.msg_handler.on_connection_lost = self._on_connection_lost_event

    def _poll_network_queue(self) -> None:
        """Safe GUI thread poller reading incoming socket packets."""
        try:
            while True:
                packet = self.network.incoming_queue.get_nowait()
                self.msg_handler.process_packet(packet)
        except queue.Empty:
            pass
        finally:
            self.after(50, self._poll_network_queue)

    # ==================== Authentication Logic ====================

    def _handle_login_attempt(self, username: str, password: str, host: str, port: int) -> None:
        """Connects to server if needed and sends login request."""
        self.client_config.host = host
        self.client_config.port = port
        self.client_config.saved_username = username
        self.client_config.save()

        # Connect if not connected
        if not self.network.is_connected:
            success, err = self.network.connect(host, port)
            if not success:
                if self.login_view:
                    self.login_view.set_loading(False)
                    self.login_view.show_error(err)
                return

        def _login_callback(response: Dict[str, Any]) -> None:
            if self.login_view:
                self.login_view.set_loading(False)
            if response.get("status") == "success":
                self.authenticated = True
                self.show_chat(response.get("data", {}))
            else:
                err_msg = response.get("error", "Login failed.")
                if self.login_view:
                    self.login_view.show_error(err_msg)

        success, req_id = self.network.send_request("login", {
            "username": username,
            "password": password
        })
        if success:
            self.msg_handler.register_pending_request(req_id, _login_callback)
        else:
            if self.login_view:
                self.login_view.set_loading(False)
                self.login_view.show_error("Could not send login request to server.")

    def _handle_register_attempt(self, username: str, password: str, host: str, port: int) -> None:
        """Connects to server and registers new user account."""
        self.client_config.host = host
        self.client_config.port = port
        self.client_config.save()

        if not self.network.is_connected:
            success, err = self.network.connect(host, port)
            if not success:
                if self.register_view:
                    self.register_view.set_loading(False)
                    self.register_view.show_error(err)
                return

        def _register_callback(response: Dict[str, Any]) -> None:
            if self.register_view:
                self.register_view.set_loading(False)
            if response.get("status") == "success":
                messagebox.showinfo(
                    "Registration Successful",
                    f"Account '{username}' created successfully! You can now log in.",
                    parent=self
                )
                self.show_login()
                if self.login_view:
                    self.login_view.entry_username.delete(0, tk.END)
                    self.login_view.entry_username.insert(0, username)
                    self.login_view.entry_password.focus_set()
            else:
                err_msg = response.get("error", "Registration failed.")
                if self.register_view:
                    self.register_view.show_error(err_msg)

        success, req_id = self.network.send_request("register", {
            "username": username,
            "password": password
        })
        if success:
            self.msg_handler.register_pending_request(req_id, _register_callback)
        else:
            if self.register_view:
                self.register_view.set_loading(False)
                self.register_view.show_error("Could not send registration request.")

    # ==================== Chat Actions ====================

    def _handle_send_message(self, content: str) -> None:
        """Sends message for current room to server."""
        if not self.authenticated or not self.chat_frame:
            return
        self.network.send_request("send_message", {
            "room_name": self.active_room,
            "content": content
        })

    def _handle_switch_room(self, room_name: str) -> None:
        """Switches active channel and fetches history."""
        if not self.authenticated:
            return

        def _join_callback(response: Dict[str, Any]) -> None:
            if response.get("status") == "success":
                data = response.get("data", {})
                self.active_room = data.get("room_name", room_name)
                history = data.get("history", [])
                members = data.get("members", [])
                
                if self.chat_frame:
                    self.message_view.set_room_info(self.active_room, len(members))
                    self.message_view.load_history(history, has_more=(len(history) >= 50))
                    self.sidebar.set_members(members)
                    self.sidebar.clear_unread(self.active_room)
                    self.composer.focus()
            else:
                messagebox.showwarning("Failed to join room", response.get("error", "Error joining room."))

        success, req_id = self.network.send_request("join_room", {"room_name": room_name})
        if success:
            self.msg_handler.register_pending_request(req_id, _join_callback)

    def _handle_create_room(self, room_name: str) -> None:
        """Requests creation of a new room."""
        def _create_callback(response: Dict[str, Any]) -> None:
            if response.get("status") == "success":
                # Automatically join the newly created room
                self._handle_switch_room(room_name)
            else:
                messagebox.showwarning("Room Creation Failed", response.get("error", "Failed to create room."))

        success, req_id = self.network.send_request("create_room", {"room_name": room_name})
        if success:
            self.msg_handler.register_pending_request(req_id, _create_callback)

    def _handle_load_older_history(self) -> None:
        """Fetches earlier page of messages before oldest_message_id."""
        if not self.chat_frame or not self.message_view.oldest_message_id:
            return

        def _history_callback(response: Dict[str, Any]) -> None:
            if response.get("status") == "success":
                older = response.get("data", {}).get("history", [])
                has_more = (len(older) >= 50)
                if self.chat_frame:
                    self.message_view.prepend_older_history(older, has_more=has_more)

        success, req_id = self.network.send_request("get_history", {
            "room_name": self.active_room,
            "before_id": self.message_view.oldest_message_id,
            "limit": 50
        })
        if success:
            self.msg_handler.register_pending_request(req_id, _history_callback)

    def _handle_logout(self) -> None:
        """Logs out and returns to login screen."""
        self.authenticated = False
        self.network.send_request("logout")
        self.network.disconnect()
        self.show_login()

    def _open_settings_dialog(self) -> None:
        """Opens Preferences dialog."""
        SettingsDialog(
            parent=self,
            theme_manager=self.theme_manager,
            client_config=self.client_config,
            on_save_callback=self._apply_updated_settings
        )

    def _apply_updated_settings(self) -> None:
        """Applies theme and notification settings across all active views."""
        self.notifications.sound_enabled = self.client_config.sound_notifications
        self.notifications.desktop_enabled = self.client_config.desktop_notifications
        self.theme_manager.apply_style(self)

        colors = self.theme_manager.get_colors()
        self.config(bg=colors.bg)
        self.container.config(bg=colors.bg)

        if self.login_view:
            self.login_view.apply_theme()
        if self.register_view:
            self.register_view.apply_theme()
        if self.chat_frame:
            self.chat_frame.config(bg=colors.bg)
            self.v_divider.config(bg=colors.border)
            self.right_container.config(bg=colors.bg)
            self.sidebar.apply_theme()
            self.message_view.apply_theme()
            self.composer.apply_theme()

    # ==================== Real-Time Broadcast Events ====================

    def _on_new_message_event(self, data: Dict[str, Any]) -> None:
        """Handles incoming real-time message."""
        room_name = data.get("room_name", "")
        sender = data.get("sender", "")
        content = data.get("content", "")

        is_active_room = (room_name.lower() == self.active_room.lower())
        is_self = (sender.lower() == self.username.lower())

        if is_active_room and self.chat_frame:
            self.message_view.add_message(data)
        elif self.chat_frame:
            self.sidebar.mark_unread(room_name)

        if not is_self:
            self.notifications.notify_new_message(
                sender=sender,
                room_name=room_name,
                message=content,
                is_active_room=is_active_room,
                is_window_focused=self.is_window_focused
            )

    def _on_user_joined_event(self, data: Dict[str, Any]) -> None:
        """Displays system message when another user joins room."""
        room_name = data.get("room_name", "")
        user = data.get("username", "")
        if room_name.lower() == self.active_room.lower() and self.chat_frame:
            self.message_view.add_system_event(f"{user} joined #{room_name}")

    def _on_user_left_event(self, data: Dict[str, Any]) -> None:
        """Displays system message when user leaves room."""
        room_name = data.get("room_name", "")
        user = data.get("username", "")
        if room_name.lower() == self.active_room.lower() and self.chat_frame:
            self.message_view.add_system_event(f"{user} left #{room_name}")

    def _on_room_created_event(self, data: Dict[str, Any]) -> None:
        """Adds newly created room to sidebar room list."""
        room_name = data.get("room_name", "")
        if self.chat_frame and room_name not in self.sidebar.rooms:
            updated_rooms = list(self.sidebar.rooms) + [room_name]
            self.sidebar.set_rooms(updated_rooms, self.active_room)

    def _on_room_members_updated_event(self, data: Dict[str, Any]) -> None:
        """Updates active member count and list."""
        room_name = data.get("room_name", "")
        members = data.get("members", [])
        if room_name.lower() == self.active_room.lower() and self.chat_frame:
            self.sidebar.set_members(members)
            self.message_view.set_room_info(self.active_room, len(members))

    def _on_server_shutdown_event(self, data: Dict[str, Any]) -> None:
        """Notifies user that server has stopped."""
        msg = data.get("message", "The chat server has shut down.")
        messagebox.showinfo("Server Shutdown", msg, parent=self)
        self._handle_logout()

    def _on_connection_lost_event(self, reason: str) -> None:
        """Handles unexpected disconnection."""
        if self.authenticated:
            messagebox.showwarning("Disconnected", f"Lost connection to server: {reason}", parent=self)
            self._handle_logout()
