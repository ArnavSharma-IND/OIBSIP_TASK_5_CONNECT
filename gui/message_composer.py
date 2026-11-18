"""
Message composer component for Connect Chat Application.
Features multiline input, Enter-to-send, Shift+Enter newline, char counter,
and native emoji keyboard support.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable
from utils.validators import MESSAGE_MAX_LENGTH, validate_message_content
from gui.theme import ThemeManager


class MessageComposer(tk.Frame):
    """Modern input composer with Enter-to-send and character counter."""

    def __init__(
        self,
        parent: tk.Widget,
        theme_manager: ThemeManager,
        on_send_message: Callable[[str], None]
    ):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.on_send_message = on_send_message

        self._build_ui()
        self.apply_theme()

    def _build_ui(self) -> None:
        colors = self.theme_manager.get_colors()

        # Top border divider
        self.divider = tk.Frame(self, height=1, bg=colors.border)
        self.divider.pack(fill="x", side="top")

        # Inner container
        self.inner_frame = tk.Frame(self, bg=colors.surface, padx=20, pady=12)
        self.inner_frame.pack(fill="x")

        # Top bar in composer: Hint & Character Counter
        self.counter_bar = tk.Frame(self.inner_frame, bg=colors.surface)
        self.counter_bar.pack(fill="x", pady=(0, 6))

        self.lbl_hint = tk.Label(
            self.counter_bar,
            text="Press Enter to send, Shift+Enter for new line • Native emoji: Win + .",
            font=self.theme_manager.font_timestamp,
            bg=colors.surface,
            fg=colors.text_muted
        )
        self.lbl_hint.pack(side="left")

        self.lbl_counter = tk.Label(
            self.counter_bar,
            text=f"0 / {MESSAGE_MAX_LENGTH}",
            font=self.theme_manager.font_timestamp,
            bg=colors.surface,
            fg=colors.text_muted
        )
        self.lbl_counter.pack(side="right")

        # Input & Button Row
        self.input_row = tk.Frame(self.inner_frame, bg=colors.surface)
        self.input_row.pack(fill="x")

        # Input Text widget (2-3 lines height)
        self.text_input = tk.Text(
            self.input_row,
            height=3,
            wrap="word",
            font=self.theme_manager.font_body,
            bg=colors.surface_secondary,
            fg=colors.text,
            insertbackground=colors.text,
            relief="flat",
            bd=0,
            padx=10,
            pady=8
        )
        self.text_input.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # Send Button
        self.btn_send = tk.Button(
            self.input_row,
            text="Send",
            font=self.theme_manager.font_body_bold,
            bg=colors.accent,
            fg="#FFFFFF",
            activebackground=colors.border,
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=18,
            command=self._on_send_click
        )
        self.btn_send.pack(side="right", fill="y")

        # Keybindings
        self.text_input.bind("<Return>", self._on_return_pressed)
        self.text_input.bind("<Shift-Return>", self._on_shift_return_pressed)
        self.text_input.bind("<KeyRelease>", self._on_key_release)

    def _on_return_pressed(self, event: tk.Event) -> str:
        """Sends message on plain Enter press."""
        self._on_send_click()
        return "break"  # Prevent newline from being inserted

    def _on_shift_return_pressed(self, event: tk.Event) -> None:
        """Allows Shift+Enter to insert a genuine newline."""
        self.text_input.insert(tk.INSERT, "\n")
        self._update_counter()
        return "break"

    def _on_key_release(self, event: tk.Event) -> None:
        """Updates character counter dynamically."""
        self._update_counter()

    def _update_counter(self) -> None:
        """Calculates current length and warns if nearing limit."""
        content = self.text_input.get("1.0", "end-1c")
        length = len(content)
        self.lbl_counter.config(text=f"{length} / {MESSAGE_MAX_LENGTH}")
        
        colors = self.theme_manager.get_colors()
        if length > MESSAGE_MAX_LENGTH:
            self.lbl_counter.config(fg=colors.danger)
        elif length > MESSAGE_MAX_LENGTH - 200:
            self.lbl_counter.config(fg=colors.accent)
        else:
            self.lbl_counter.config(fg=colors.text_muted)

    def _on_send_click(self) -> None:
        """Extracts text, validates, and dispatches on_send_message."""
        content = self.text_input.get("1.0", "end-1c")
        valid, _ = validate_message_content(content)
        if not valid:
            return  # Prevent sending empty or oversized messages
            
        self.text_input.delete("1.0", tk.END)
        self._update_counter()
        self.on_send_message(content)

    def focus(self) -> None:
        """Focuses the message input field."""
        self.text_input.focus_set()

    def apply_theme(self) -> None:
        """Updates colors matching ThemeManager."""
        colors = self.theme_manager.get_colors()
        self.config(bg=colors.surface)
        self.divider.config(bg=colors.border)
        self.inner_frame.config(bg=colors.surface)
        self.counter_bar.config(bg=colors.surface)
        self.lbl_hint.config(bg=colors.surface, fg=colors.text_muted)
        self.lbl_counter.config(bg=colors.surface)
        self.input_row.config(bg=colors.surface)
        self.text_input.config(
            bg=colors.surface_secondary,
            fg=colors.text,
            insertbackground=colors.text
        )
        self.btn_send.config(bg=colors.accent)
        self._update_counter()
