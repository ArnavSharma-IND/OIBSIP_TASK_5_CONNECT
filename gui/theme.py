"""
Theme design tokens, colors, and TTK styling for Connect Chat Application.
Adheres strictly to the specification for Light and Dark themes.
"""

import sys
import tkinter as tk
from tkinter import ttk
from typing import Dict


class ThemeColors:
    """Design tokens for a theme."""
    def __init__(
        self,
        name: str,
        bg: str,
        surface: str,
        surface_secondary: str,
        accent: str,
        text: str,
        text_muted: str,
        border: str,
        bubble_self: str,
        bubble_other: str,
        danger: str = "#E05D52",
        success: str = "#4E9F6E"
    ):
        self.name = name
        self.bg = bg
        self.surface = surface
        self.surface_secondary = surface_secondary
        self.accent = accent
        self.text = text
        self.text_muted = text_muted
        self.border = border
        self.bubble_self = bubble_self
        self.bubble_other = bubble_other
        self.danger = danger
        self.success = success


LIGHT_THEME = ThemeColors(
    name="light",
    bg="#F3EDE3",
    surface="#FAF7F1",
    surface_secondary="#E9DFD0",
    accent="#C8793C",
    text="#29251F",
    text_muted="#81776A",
    border="#DED5C9",
    bubble_self="#E6D6C4",
    bubble_other="#FAF7F1"
)

DARK_THEME = ThemeColors(
    name="dark",
    bg="#111014",
    surface="#1B1820",
    surface_secondary="#211D27",
    accent="#A987F5",
    text="#F2EFF7",
    text_muted="#A69BAF",
    border="#37303F",
    bubble_self="#2F2542",
    bubble_other="#1B1820"
)

THEMES: Dict[str, ThemeColors] = {
    "light": LIGHT_THEME,
    "dark": DARK_THEME
}


class ThemeManager:
    """Manages active theme state and applies ttk styling."""

    def __init__(self, default_theme: str = "dark"):
        self.current_theme = THEMES.get(default_theme.lower(), DARK_THEME)
        self.font_family = "Segoe UI" if sys.platform == "win32" else "Helvetica"
        
        self.font_title = (self.font_family, 16, "bold")
        self.font_subtitle = (self.font_family, 12, "bold")
        self.font_body = (self.font_family, 10)
        self.font_body_bold = (self.font_family, 10, "bold")
        self.font_small = (self.font_family, 9)
        self.font_code = ("Consolas" if sys.platform == "win32" else "Courier", 9)
        self.font_timestamp = (self.font_family, 8)

    def set_theme(self, theme_name: str) -> ThemeColors:
        """Sets active theme and returns ThemeColors object."""
        self.current_theme = THEMES.get(theme_name.lower(), DARK_THEME)
        return self.current_theme

    def get_colors(self) -> ThemeColors:
        """Returns the current ThemeColors object."""
        return self.current_theme

    def apply_style(self, root: tk.Tk) -> None:
        """Configures ttk styles for consistent appearance across the application."""
        colors = self.current_theme
        style = ttk.Style(root)
        
        # Use clam theme as base for best customizability
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # Configure defaults
        style.configure(".",
            background=colors.bg,
            foreground=colors.text,
            font=self.font_body,
            borderwidth=0
        )
        
        # TFrame & Surface Frames
        style.configure("TFrame", background=colors.bg)
        style.configure("Surface.TFrame", background=colors.surface)
        style.configure("Secondary.TFrame", background=colors.surface_secondary)
        
        # TLabel
        style.configure("TLabel", background=colors.bg, foreground=colors.text, font=self.font_body)
        style.configure("Surface.TLabel", background=colors.surface, foreground=colors.text, font=self.font_body)
        style.configure("Muted.TLabel", background=colors.bg, foreground=colors.text_muted, font=self.font_small)
        style.configure("SurfaceMuted.TLabel", background=colors.surface, foreground=colors.text_muted, font=self.font_small)
        style.configure("Title.TLabel", background=colors.bg, foreground=colors.text, font=self.font_title)
        style.configure("SurfaceTitle.TLabel", background=colors.surface, foreground=colors.text, font=self.font_subtitle)
        style.configure("Accent.TLabel", background=colors.surface, foreground=colors.accent, font=self.font_body_bold)
        
        # TButton
        style.configure("TButton",
            background=colors.surface_secondary,
            foreground=colors.text,
            font=self.font_body_bold,
            padding=6,
            relief="flat"
        )
        style.map("TButton",
            background=[("active", colors.border), ("disabled", colors.surface)],
            foreground=[("disabled", colors.text_muted)]
        )

        # Primary Accent Button
        style.configure("Accent.TButton",
            background=colors.accent,
            foreground="#FFFFFF" if colors.name == "dark" else "#FFFFFF",
            font=self.font_body_bold,
            padding=8,
            relief="flat"
        )
        style.map("Accent.TButton",
            background=[("active", colors.border), ("disabled", colors.surface_secondary)],
            foreground=[("disabled", colors.text_muted)]
        )

        # TEntry
        style.configure("TEntry",
            fieldbackground=colors.surface,
            foreground=colors.text,
            insertcolor=colors.text,
            bordercolor=colors.border,
            lightcolor=colors.border,
            darkcolor=colors.border,
            padding=6
        )
        
        # Scrollbars
        style.configure("Vertical.TScrollbar",
            background=colors.surface_secondary,
            troughcolor=colors.bg,
            bordercolor=colors.bg,
            arrowcolor=colors.text_muted
        )
