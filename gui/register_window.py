"""
Registration screen for Connect Chat Application.
Enforces username syntax, password complexity, and confirmation checks.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable
from utils.validators import (
    validate_password_confirmation,
    validate_username,
)
from gui.theme import ThemeManager


class RegisterFrame(tk.Frame):
    """Modern, minimalist registration view."""

    def __init__(
        self,
        parent: tk.Widget,
        theme_manager: ThemeManager,
        on_register_attempt: Callable[[str, str, str, int], None],
        on_switch_to_login: Callable[[], None],
        default_host: str = "127.0.0.1",
        default_port: int = 5000
    ):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.on_register_attempt = on_register_attempt
        self.on_switch_to_login = on_switch_to_login
        
        self.default_host = default_host
        self.default_port = default_port
        
        self._build_ui()
        self.apply_theme()

    def _build_ui(self) -> None:
        colors = self.theme_manager.get_colors()
        
        # Center card container
        self.card = tk.Frame(self, bg=colors.surface, bd=1, relief="solid")
        self.card.place(relx=0.5, rely=0.5, anchor="center", width=420, height=580)
        
        # App Title & Subtitle
        self.lbl_brand = tk.Label(
            self.card,
            text="CREATE ACCOUNT",
            font=(self.theme_manager.font_family, 16, "bold"),
            bg=colors.surface,
            fg=colors.accent
        )
        self.lbl_brand.pack(pady=(24, 4))
        
        self.lbl_subtitle = tk.Label(
            self.card,
            text="Join the Connect real-time network",
            font=self.theme_manager.font_small,
            bg=colors.surface,
            fg=colors.text_muted
        )
        self.lbl_subtitle.pack(pady=(0, 16))
        
        # Error/Status Banner
        self.lbl_error = tk.Label(
            self.card,
            text="",
            font=self.theme_manager.font_small,
            bg=colors.surface,
            fg=colors.danger,
            wraplength=360
        )
        self.lbl_error.pack(pady=(0, 8))
        
        # Form Container
        form_frame = tk.Frame(self.card, bg=colors.surface)
        form_frame.pack(fill="x", padx=36)
        
        # Username Input
        lbl_user = tk.Label(form_frame, text="Username (3-20 chars)", font=self.theme_manager.font_small, bg=colors.surface, fg=colors.text)
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
        self.entry_username.pack(fill="x", pady=(0, 10))
        
        # Password Input
        lbl_pwd = tk.Label(form_frame, text="Password (min 8 chars, uppercase, lowercase, digit)", font=self.theme_manager.font_small, bg=colors.surface, fg=colors.text)
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
        self.entry_password.pack(fill="x", pady=(0, 10))
        
        # Confirm Password Input
        lbl_confirm = tk.Label(form_frame, text="Confirm Password", font=self.theme_manager.font_small, bg=colors.surface, fg=colors.text)
        lbl_confirm.pack(anchor="w", pady=(0, 2))
        
        self.entry_confirm = tk.Entry(
            form_frame,
            font=self.theme_manager.font_body,
            show="•",
            bg=colors.surface_secondary,
            fg=colors.text,
            insertbackground=colors.text,
            relief="flat",
            bd=6
        )
        self.entry_confirm.pack(fill="x", pady=(0, 12))
        self.entry_confirm.bind("<Return>", lambda e: self._on_submit())
        
        # Server details
        server_box = tk.Frame(form_frame, bg=colors.surface)
        server_box.pack(fill="x", pady=(0, 14))
        
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
        
        # Register Button
        self.btn_register = tk.Button(
            form_frame,
            text="Create Account",
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
        self.btn_register.pack(fill="x", ipady=8, pady=(0, 12))
        
        # Switch to Login Link
        switch_frame = tk.Frame(self.card, bg=colors.surface)
        switch_frame.pack()
        
        lbl_switch = tk.Label(
            switch_frame,
            text="Already have an account?",
            font=self.theme_manager.font_small,
            bg=colors.surface,
            fg=colors.text_muted
        )
        lbl_switch.pack(side="left", padx=(0, 4))
        
        btn_switch = tk.Button(
            switch_frame,
            text="Log In",
            font=self.theme_manager.font_small,
            bg=colors.surface,
            fg=colors.accent,
            activebackground=colors.surface,
            activeforeground=colors.text,
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self.on_switch_to_login
        )
        btn_switch.pack(side="left")

    def _on_submit(self) -> None:
        """Validates inputs and triggers registration callback."""
        username = self.entry_username.get().strip()
        password = self.entry_password.get()
        confirm = self.entry_confirm.get()
        host = self.entry_host.get().strip()
        port_str = self.entry_port.get().strip()
        
        valid_u, err_u = validate_username(username)
        if not valid_u:
            self.show_error(err_u)
            return
            
        valid_p, err_p = validate_password_confirmation(password, confirm)
        if not valid_p:
            self.show_error(err_p)
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
        self.on_register_attempt(username, password, host, port)

    def show_error(self, message: str) -> None:
        """Displays error banner."""
        self.lbl_error.config(text=message)

    def set_loading(self, loading: bool) -> None:
        """Disables/enables button during network call."""
        if loading:
            self.btn_register.config(text="Registering...", state="disabled")
        else:
            self.btn_register.config(text="Create Account", state="normal")

    def apply_theme(self) -> None:
        """Re-applies colors from ThemeManager."""
        colors = self.theme_manager.get_colors()
        self.config(bg=colors.bg)
        self.card.config(bg=colors.surface, highlightbackground=colors.border, highlightcolor=colors.border)
        self.lbl_brand.config(bg=colors.surface, fg=colors.accent)
        self.lbl_subtitle.config(bg=colors.surface, fg=colors.text_muted)
        self.lbl_error.config(bg=colors.surface, fg=colors.danger)
        self.btn_register.config(bg=colors.accent)
        self.entry_username.config(bg=colors.surface_secondary, fg=colors.text, insertbackground=colors.text)
        self.entry_password.config(bg=colors.surface_secondary, fg=colors.text, insertbackground=colors.text)
        self.entry_confirm.config(bg=colors.surface_secondary, fg=colors.text, insertbackground=colors.text)
        self.entry_host.config(bg=colors.surface_secondary, fg=colors.text, insertbackground=colors.text)
        self.entry_port.config(bg=colors.surface_secondary, fg=colors.text, insertbackground=colors.text)
