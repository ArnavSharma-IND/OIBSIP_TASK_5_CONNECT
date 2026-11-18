"""
Settings dialog for Connect Chat Application.
Allows switching themes (Light/Dark), toggling notification sounds, and updating defaults.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable
from client.config import ClientConfig
from gui.theme import ThemeManager


class SettingsDialog(tk.Toplevel):
    """Modal dialog for application preferences."""

    def __init__(
        self,
        parent: tk.Widget,
        theme_manager: ThemeManager,
        client_config: ClientConfig,
        on_save_callback: Callable[[], None]
    ):
        super().__init__(parent)
        self.title("Settings — Connect")
        self.geometry("380x420")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.theme_manager = theme_manager
        self.client_config = client_config
        self.on_save_callback = on_save_callback

        self._build_ui()
        self.apply_theme()

    def _build_ui(self) -> None:
        colors = self.theme_manager.get_colors()

        # Header
        self.header_frame = tk.Frame(self, bg=colors.surface, pady=16)
        self.header_frame.pack(fill="x")
        
        self.lbl_title = tk.Label(
            self.header_frame,
            text="Preferences",
            font=self.theme_manager.font_subtitle,
            bg=colors.surface,
            fg=colors.text
        )
        self.lbl_title.pack(padx=20, anchor="w")

        # Main Body
        self.body_frame = tk.Frame(self, bg=colors.bg, padx=20, pady=16)
        self.body_frame.pack(fill="both", expand=True)

        # 1. Appearance / Theme
        self.lbl_theme_section = tk.Label(
            self.body_frame,
            text="APPEARANCE",
            font=self.theme_manager.font_timestamp,
            bg=colors.bg,
            fg=colors.text_muted
        )
        self.lbl_theme_section.pack(anchor="w", pady=(0, 6))

        self.theme_var = tk.StringVar(value=self.client_config.theme)
        theme_options_frame = tk.Frame(self.body_frame, bg=colors.surface, padx=12, pady=10)
        theme_options_frame.pack(fill="x", pady=(0, 16))

        self.radio_dark = tk.Radiobutton(
            theme_options_frame,
            text="Dark Theme",
            variable=self.theme_var,
            value="dark",
            font=self.theme_manager.font_body,
            bg=colors.surface,
            fg=colors.text,
            selectcolor=colors.surface_secondary,
            activebackground=colors.surface,
            activeforeground=colors.text,
            command=self._on_theme_changed
        )
        self.radio_dark.pack(anchor="w", pady=2)

        self.radio_light = tk.Radiobutton(
            theme_options_frame,
            text="Light Theme",
            variable=self.theme_var,
            value="light",
            font=self.theme_manager.font_body,
            bg=colors.surface,
            fg=colors.text,
            selectcolor=colors.surface_secondary,
            activebackground=colors.surface,
            activeforeground=colors.text,
            command=self._on_theme_changed
        )
        self.radio_light.pack(anchor="w", pady=2)

        # 2. Notifications
        self.lbl_notif_section = tk.Label(
            self.body_frame,
            text="NOTIFICATIONS",
            font=self.theme_manager.font_timestamp,
            bg=colors.bg,
            fg=colors.text_muted
        )
        self.lbl_notif_section.pack(anchor="w", pady=(0, 6))

        notif_frame = tk.Frame(self.body_frame, bg=colors.surface, padx=12, pady=10)
        notif_frame.pack(fill="x", pady=(0, 16))

        self.sound_var = tk.BooleanVar(value=self.client_config.sound_notifications)
        self.chk_sound = tk.Checkbutton(
            notif_frame,
            text="Play audio alert on new messages",
            variable=self.sound_var,
            font=self.theme_manager.font_body,
            bg=colors.surface,
            fg=colors.text,
            selectcolor=colors.surface_secondary,
            activebackground=colors.surface,
            activeforeground=colors.text
        )
        self.chk_sound.pack(anchor="w", pady=2)

        self.desktop_var = tk.BooleanVar(value=self.client_config.desktop_notifications)
        self.chk_desktop = tk.Checkbutton(
            notif_frame,
            text="Show window title / badge notifications",
            variable=self.desktop_var,
            font=self.theme_manager.font_body,
            bg=colors.surface,
            fg=colors.text,
            selectcolor=colors.surface_secondary,
            activebackground=colors.surface,
            activeforeground=colors.text
        )
        self.chk_desktop.pack(anchor="w", pady=2)

        # Footer Actions
        self.footer_frame = tk.Frame(self, bg=colors.surface, pady=12, padx=20)
        self.footer_frame.pack(fill="x", side="bottom")

        self.btn_save = tk.Button(
            self.footer_frame,
            text="Save Preferences",
            font=self.theme_manager.font_body_bold,
            bg=colors.accent,
            fg="#FFFFFF",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=14,
            pady=6,
            command=self._save
        )
        self.btn_save.pack(side="right")

        self.btn_cancel = tk.Button(
            self.footer_frame,
            text="Cancel",
            font=self.theme_manager.font_body,
            bg=colors.surface_secondary,
            fg=colors.text,
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=12,
            pady=6,
            command=self.destroy
        )
        self.btn_cancel.pack(side="right", padx=(0, 10))

    def _on_theme_changed(self) -> None:
        """Live preview of theme when radio button clicked."""
        new_theme = self.theme_var.get()
        self.theme_manager.set_theme(new_theme)
        self.apply_theme()
        if self.on_save_callback:
            self.on_save_callback()

    def _save(self) -> None:
        """Persists settings and closes dialog."""
        self.client_config.theme = self.theme_var.get()
        self.client_config.sound_notifications = self.sound_var.get()
        self.client_config.desktop_notifications = self.desktop_var.get()
        self.client_config.save()
        
        self.theme_manager.set_theme(self.client_config.theme)
        if self.on_save_callback:
            self.on_save_callback()
        self.destroy()

    def apply_theme(self) -> None:
        """Updates dialog colors based on ThemeManager."""
        colors = self.theme_manager.get_colors()
        self.config(bg=colors.bg)
        self.header_frame.config(bg=colors.surface)
        self.lbl_title.config(bg=colors.surface, fg=colors.text)
        self.body_frame.config(bg=colors.bg)
        self.lbl_theme_section.config(bg=colors.bg, fg=colors.text_muted)
        self.lbl_notif_section.config(bg=colors.bg, fg=colors.text_muted)
        self.footer_frame.config(bg=colors.surface)
        self.btn_save.config(bg=colors.accent)
        self.btn_cancel.config(bg=colors.surface_secondary, fg=colors.text)
