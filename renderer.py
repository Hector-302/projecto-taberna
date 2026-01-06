import re
from typing import Any, Dict, List, Tuple, Optional

import tkinter as tk
from tkinter import font as tkfont


class CharacterColors:
    def __init__(self, palette: List[str]):
        self.palette = palette
        self.map: Dict[str, str] = {}

    def get(self, name: str) -> str:
        name = (name or "").strip()
        if not name:
            return "#e6e8ee"
        if name in self.map:
            return self.map[name]
        color = self.palette[len(self.map) % len(self.palette)]
        self.map[name] = color
        return color


class ChatRenderer:
    def __init__(
        self,
        text_widget: tk.Text,
        character_colors: CharacterColors,
        *,
        base_font: Optional[tkfont.Font] = None,
    ):
        self.chat = text_widget
        self.colors = character_colors

        # Fuente base: si no se pasa, se toma la del widget
        self.base_font = base_font or tkfont.nametofont(self.chat.cget("font"))

        # Fuentes derivadas (se actualizan cuando cambie el tamaño)
        self.body_font = self.base_font.copy()
        self.body_font.configure(weight="normal", slant="roman")

        self.body_italic_font = self.base_font.copy()
        self.body_italic_font.configure(weight="normal", slant="italic")

        self.speaker_font = self.base_font.copy()
        self.speaker_font.configure(weight="bold", slant="roman")

        self._font_size = int(self.base_font.cget("size"))

    def set_font_size(self, size: int):
        # Ajusta tamaño de fuentes usadas por todos los tags
        size = int(size)
        if size == self._font_size:
            return
        self._font_size = size

        self.base_font.configure(size=size)
        self.body_font.configure(size=size)
        self.body_italic_font.configure(size=size)
        self.speaker_font.configure(size=size)

    def _ensure_tags(
        self,
        speaker: str,
        speaker_color: str,
        body_color: str,
        italic: bool,
    ) -> Tuple[str, str]:
        speaker_key = (speaker or "anon").replace(" ", "-")
        speaker_tag = f"speaker-{speaker_key}"
        if speaker_tag not in self.chat.tag_names():
            self.chat.tag_configure(
                speaker_tag,
                foreground=speaker_color,
                font=self.speaker_font,
            )
        else:
            # Por si el color cambiara (raro, pero evita inconsistencias)
            self.chat.tag_configure(speaker_tag, foreground=speaker_color)

        body_tag = f"body-{body_color.replace('#', '')}-{'i' if italic else 'n'}"
        if body_tag not in self.chat.tag_names():
            self.chat.tag_configure(
                body_tag,
                foreground=body_color,
                font=self.body_italic_font if italic else self.body_font,
            )

        return speaker_tag, body_tag

    def _insert_with_asterisk_italics(self, text: str, normal_tag: str, italic_tag: str):
        s = text or ""
        last = 0
        for m in re.finditer(r"\*(.+?)\*", s):
            start, end = m.span()
            if start > last:
                self.chat.insert("end", s[last:start], normal_tag)
            self.chat.insert("end", m.group(1), italic_tag)
            last = end
        if last < len(s):
            self.chat.insert("end", s[last:], normal_tag)

    def append(
        self,
        speaker: str,
        text: str,
        *,
        speaker_color: str = "#e6e8ee",
        body_color: str = "#e6e8ee",
        italic: bool = False,
        show_speaker: bool = True,
        italicize_asterisks: bool = False,
    ):
        self.chat.configure(state="normal")

        speaker_tag, body_tag = self._ensure_tags(speaker, speaker_color, body_color, italic)
        _, body_italic_tag = self._ensure_tags(speaker, speaker_color, body_color, True)

        if show_speaker and speaker:
            self.chat.insert("end", f"{speaker}: ", speaker_tag)

        if italicize_asterisks and not italic:
            self._insert_with_asterisk_italics(text, body_tag, body_italic_tag)
            self.chat.insert("end", "\n\n", body_tag)
        else:
            self.chat.insert("end", f"{text}\n\n", body_tag)

        self.chat.configure(state="disabled")
        self.chat.see("end")

    def append_user(self, user_text: str):
        self.append(
            "Usuario",
            user_text,
            speaker_color="#7aa2f7",
            body_color="#e6e8ee",
            italic=False,
            italicize_asterisks=True,
        )

    def append_narration(self, narration: str):
        narration = (narration or "").strip()
        if narration:
            self.append(
                "Narrador",
                narration,
                speaker_color="#b7beca",
                body_color="#b7beca",
                italic=True,
            )

    def append_character(self, name: str, dialog: str):
        name = (name or "").strip() or "Personaje"
        dialog = (dialog or "").strip()
        if not dialog:
            return
        color = self.colors.get(name)
        self.append(name, dialog, speaker_color=color, body_color=color, italic=False)

    def append_choices(self, choices: Any):
        if not isinstance(choices, list):
            return
        clean = [c.strip() for c in choices if isinstance(c, str) and c.strip()]
        if not clean:
            return

        header = "Opciones sugeridas a continuación"
        self.append(header, "", speaker_color="#a78bfa", body_color="#a78bfa", italic=False, show_speaker=True)

        lines = "\n".join(f"- {opt}" for opt in clean)
        self.append("", lines, speaker_color="#a78bfa", body_color="#a78bfa", italic=False, show_speaker=False)

    def append_raw_ai(self, raw: str):
        self.append("IA", raw.strip(), speaker_color="#f59e0b", body_color="#e6e8ee")

    def append_error(self, err: str):
        self.append("Error", err, speaker_color="#ef4444", body_color="#ef4444")
