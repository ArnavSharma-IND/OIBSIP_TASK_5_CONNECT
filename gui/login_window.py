"""
Login and Authentication screen for Connect Chat Application.
Provides user authentication, server host/port configuration, and navigation to registration.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional
from utils.validators import validate_password, validate_username
from gui.theme import ThemeManager


class LoginFrame(tk.Frame):
    """Modern, minimalist login view."""

    def __init__(
        self,
        parent: tk.Widget,
        theme_manager: ThemeManager,
        on_login_attempt: Callable[[str, str, str, int], None],
        on_switch_to_register: Callable[[], None],
        default_host: str = "127.0.0.1",
        default_port: int = 5000,
        saved_username: str = ""
    ):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.on_login_attempt = on_login_attempt
        self.on_switch_to_register = on_switch_to_register
        
        self.default_host = default_host
        self.default_port = default_port
        self.saved_username = saved_username
        
        self._build_ui()
        self.apply_theme()

    def _build_ui(self) -> None:
        colors = self.theme_manager.get_colors()
        
        # Center card container
        self.card = tk.Frame(self, bg=colors.surface, bd=1, relief="solid")
        self.card.place(relx=0.5, rely=0.5, anchor="center", width=420, height=520)
        
        # App Title & Subtitle
        self.lbl_brand = tk.Label(
            self.card,
            text="CONNECT",
            font=(self.theme_manager.font_family, 20, "bold"),
            bg=colors.surface,
            fg=colors.accent
        )
        self.lbl_brand.pack(pady=(30, 4))
        
        self.lbl_subtitle = tk.Label(
            self.card,
            text="Real-Time Desktop Messaging",
            font=self.theme_manager.font_small,
            bg=colors.surface,
            fg=colors.text_muted
        )
        self.lbl_subtitle.pack(pady=(0, 20))
        
        # Error/Status Banner
        self.lbl_error = tk.Label(
            self.card,
            text="",
            font=self.theme_manager.font_small,
            bg=colors.surface,
            fg=colors.danger,
            wraplength=360
        )
        self.lbl_error.pack(pady=(0, 10))
        
        # Form Container
        form_frame = tk.Frame(self.card, bg=colors.surface)
        form_frame.pack(fill="x", padx=36)
        
        # Username Input
        lbl_user = tk.Label(form_frame, text="Username", font=self.theme_manager.font_small, bg=colors.surface, fg=colors.text)
        lbl_user.pack(anchor="w", pady=(0, 2))
        
        self.entry_username = tk.Entry(
            form_frame,
            font=self.theme_manager.font_body,
            bg=colors.surface_secondary,
            fg=colors.text,
            insertbackground=colors.text,
            relief="flat",
            bd=6
        )
        self.entry_username.pack(fill="x", pady=(0, 12))
        if self.saved_username:
            self.entry_username.insert(0, self.saved_username)
            
        # Password Input
        lbl_pwd = tk.Label(form_frame, text="Password", font=self.theme_manager.font_small, bg=colors.surface, fg=colors.text)
        lbl_pwd.pack(anchor="w", pady=(0, 2))
        
        self.entry_password = tk.Entry(
            form_frame,
            font=self.theme_manager.font_body,
            show="•",
            bg=colors.surface_secondary,
            fg=colors.text,
            insertbackground=colors.text,
            relief="flat",
            bd=6
        )
        self.entry_password.pack(fill="x", pady=(0, 14))
        self.entry_password.bind("<Return>", lambda e: self._on_submit())
        
        # Server Connection Details (Host / Port)
        server_box = tk.Frame(form_frame, bg=colors.surface)
        server_box.pack(fill="x", pady=(0, 18))
        
        lbl_host = tk.Label(server_box, text="Host", font=self.theme_manager.font_timestamp, bg=colors.surface, fg=colors.text_muted)
        lbl_host.grid(row=0, column=0, sticky="w")
        self.entry_host = tk.Entry(
            server_box,
            font=self.theme_manager.font_small,
            width=16,
            bg=colors.surface_secondary,
            fg=colors.text,
            insertbackground=colors.text,
            relief="flat",
            bd=4
        )
        self.entry_host.insert(0, self.default_host)
        self.entry_host.grid(row=1, column=0, sticky="w", padx=(0, 10))
        
        lbl_port = tk.Label(server_box, text="Port", font=self.theme_manager.font_timestamp, bg=colors.surface, fg=colors.text_muted)
        lbl_port.grid(row=0, column=1, sticky="w")
        self.entry_port = tk.Entry(
            server_box,
            font=self.theme_manager.font_small,
            width=8,
            bg=colors.surface_secondary,
            fg=colors.text,
            insertbackground=colors.text,
            relief="flat",
            bd=4
        )
        self.entry_port.insert(0, str(self.default_port))
        self.entry_port.grid(row=1, column=1, sticky="w")
        
        # Login Button
        self.btn_login = tk.Button(
            form_frame,
            text="Log In",
            font=self.theme_manager.font_body_bold,
            bg=colors.accent,
            fg="#FFFFFF",
            activebackground=colors.border,
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self._on_submit
        )
        self.btn_login.pack(fill="x", ipady=8, pady=(0, 14))
        
        # Switch to Register Link
        switch_frame = tk.Frame(self.card, bg=colors.surface)
        switch_frame.pack()
        
        lbl_switch = tk.Label(
            switch_frame,
            text="Don't have an account?",
            font=self.theme_manager.font_small,
            bg=colors.surface,
            fg=colors.text_muted
        )
        lbl_switch.pack(side="left", padx=(0, 4))
        
        btn_switch = tk.Button(
            switch_frame,
            text="Register",
            font=self.theme_manager.font_small,
            bg=colors.surface,
            fg=colors.accent,
            activebackground=colors.surface,
            activeforeground=colors.text,
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self.on_switch_to_register
        )
        btn_switch.pack(side="left")

    def _on_submit(self) -> None:
        """Validates inputs and triggers the login callback."""
        username = self.entry_username.get().strip()
        password = self.entry_password.get()
        host = self.entry_host.get().strip()
        port_str = self.entry_port.get().strip()
        
        if not username:
            self.show_error("Please enter your username.")
            return
        if not password:
            self.show_error("Please enter your password.")
            return
        if not host:
            self.show_error("Please enter server host.")
            return
        try:
            port = int(port_str)
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            self.show_error("Port must be a number between 1 and 65535.")
            return
            
        self.show_error("")
        self.set_loading(True)
        self.on_login_attempt(username, password, host, port)

    def show_error(self, message: str) -> None:
        """Displays error message on card."""
        self.lbl_error.config(text=message)

    def set_loading(self, loading: bool) -> None:
        """Disables/enables button during network call."""
        if loading:
            self.btn_login.config(text="Connecting...", state="disabled")
        else:
            self.btn_login.config(text="Log In", state="normal")

    def apply_theme(self) -> None:
        """Re-applies colors from ThemeManager."""
        colors = self.theme_manager.get_colors()
        self.config(bg=colors.bg)
        self.card.config(bg=colors.surface, highlightbackground=colors.border, highlightcolor=colors.border)
        self.lbl_brand.config(bg=colors.surface, fg=colors.accent)
        self.lbl_subtitle.config(bg=colors.surface, fg=colors.text_muted)
        self.lbl_error.config(bg=colors.surface, fg=colors.danger)
        self.btn_login.config(bg=colors.accent)
        self.entry_username.config(bg=colors.surface_secondary, fg=colors.text, insertbackground=colors.text)
        self.entry_password.config(bg=colors.surface_secondary, fg=colors.text, insertbackground=colors.text)
        self.entry_host.config(bg=colors.surface_secondary, fg=colors.text, insertbackground=colors.text)
        self.entry_port.config(bg=colors.surface_secondary, fg=colors.text, insertbackground=colors.text)
