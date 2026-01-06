import os
import queue
import threading
from typing import Any, Dict, Tuple

import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont

from llm_service import LLMService
from parser import ResponseParser
from logger import GameLogger
from renderer import ChatRenderer, CharacterColors


class ChatUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Chat con IA")
        self.geometry("820x520")
        self.minsize(740, 460)

        self.result_q: "queue.Queue[Tuple[str, str, str]]" = queue.Queue()

        self.llm = LLMService(prompt_path="prompts/predefined_prompt.txt")
        self.parser = ResponseParser()
        self.logger = GameLogger(log_path=os.path.join("outputs", "log_partida.txt"))

        palette = ["#f59e0b", "#22d3ee", "#b54a8a", "#9333ea", "#10b981", "#ef4444"]
        self.character_colors = CharacterColors(palette)

        # Colores base (oscuro en grises, sin negro puro)
        self.colors = {
            "bg": "#2b2f36",
            "panel": "#323844",
            "text": "#e6e8ee",
            "muted": "#b7beca",
            "border": "#444b59",
            "accent": "#7aa2f7",
            "error": "#ef4444",
            "select": "#3a4252",
            "insert": "#e6e8ee",
        }

        # Fuente ajustable para toda la UI
        self.base_font_size = 12
        self.min_font_size = 10
        self.max_font_size = 20
        self.ui_font = tkfont.nametofont("TkDefaultFont").copy()
        self.ui_font.configure(size=self.base_font_size)

        self._configure_theme()
        self._build_ui()

        self.renderer = ChatRenderer(self.chat, self.character_colors, base_font=self.ui_font)

        self._display_greeting()

        self._bind_zoom_shortcuts()
        self.after(100, self._poll_results)

    def _display_greeting(self):
        try:
            with open("greetings.txt", "r", encoding="utf-8") as f:
                greeting = f.read()
            self.renderer.append_narration(greeting)
        except FileNotFoundError:
            self.renderer.append_error("No se encontró el archivo de bienvenida (greetings.txt).")
        except Exception as e:
            self.renderer.append_error(f"Error al leer el archivo de bienvenida: {e}")

    def _configure_theme(self):
        # Estilos ttk (mejor con "clam" para respetar colores)
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        self.configure(bg=self.colors["bg"])

        style.configure(
            ".",
            background=self.colors["bg"],
            foreground=self.colors["text"],
            font=self.ui_font,
        )

        style.configure(
            "Main.TFrame",
            background=self.colors["bg"],
        )

        style.configure(
            "Panel.TFrame",
            background=self.colors["panel"],
        )

        style.configure(
            "TButton",
            background=self.colors["panel"],
            foreground=self.colors["text"],
            bordercolor=self.colors["border"],
            lightcolor=self.colors["border"],
            darkcolor=self.colors["border"],
            padding=(10, 6),
        )
        style.map(
            "TButton",
            background=[("active", "#3a4150"), ("disabled", "#2a2f39")],
            foreground=[("disabled", "#8b93a3")],
        )

        style.configure(
            "TEntry",
            fieldbackground="#262a31",
            background=self.colors["panel"],
            foreground=self.colors["text"],
            insertcolor=self.colors["insert"],
            padding=(10, 6),
        )
        style.map(
            "TEntry",
            fieldbackground=[("disabled", "#1f232b")],
            foreground=[("disabled", "#8b93a3")],
        )

        style.configure(
            "TScrollbar",
            background=self.colors["panel"],
            troughcolor=self.colors["bg"],
            bordercolor=self.colors["border"],
            arrowcolor=self.colors["muted"],
        )

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        main_frame = ttk.Frame(self, padding=10, style="Main.TFrame")
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.rowconfigure(1, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # Barra superior con controles de tamaño de letra
        topbar = ttk.Frame(main_frame, style="Main.TFrame")
        topbar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        topbar.columnconfigure(0, weight=1)

        zoom_box = ttk.Frame(topbar, style="Main.TFrame")
        zoom_box.grid(row=0, column=1, sticky="e")

        self.zoom_out_btn = ttk.Button(zoom_box, text="A-", width=4, command=lambda: self._zoom(-1))
        self.zoom_out_btn.grid(row=0, column=0, padx=(0, 6))

        self.zoom_in_btn = ttk.Button(zoom_box, text="A+", width=4, command=lambda: self._zoom(+1))
        self.zoom_in_btn.grid(row=0, column=1, padx=(0, 8))

        self.font_size_lbl = ttk.Label(zoom_box, text=f"{self.base_font_size} pt")
        self.font_size_lbl.grid(row=0, column=2)

        # Chat (Text) con colores grises y buena legibilidad
        self.chat = tk.Text(
            main_frame,
            wrap="word",
            state="disabled",
            bg="#262a31",
            fg=self.colors["text"],
            insertbackground=self.colors["insert"],
            selectbackground=self.colors["select"],
            relief="flat",
            padx=10,
            pady=10,
            font=self.ui_font,
        )
        self.chat.grid(row=1, column=0, sticky="nsew")

        scroll = ttk.Scrollbar(main_frame, command=self.chat.yview)
        scroll.grid(row=1, column=1, sticky="ns")
        self.chat["yscrollcommand"] = scroll.set

        bottom = ttk.Frame(self, padding=10, style="Main.TFrame")
        bottom.grid(row=1, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)

        self.entry = ttk.Entry(bottom)
        self.entry.grid(row=0, column=0, sticky="ew")
        self.entry.bind("<Return>", lambda _e: self.on_send())

        self.send_btn = ttk.Button(bottom, text="Enviar", command=self.on_send)
        self.send_btn.grid(row=0, column=1, padx=(10, 0))

    def _bind_zoom_shortcuts(self):
        # Atajos de zoom (según teclado, el + suele venir como "equal")
        self.bind("<Control-plus>", lambda _e: self._zoom(+1))
        self.bind("<Control-equal>", lambda _e: self._zoom(+1))
        self.bind("<Control-minus>", lambda _e: self._zoom(-1))
        self.bind("<Control-0>", lambda _e: self._set_font_size(12))

        # Ctrl + rueda (Windows/macOS)
        self.bind("<Control-MouseWheel>", self._on_ctrl_wheel)

        # Ctrl + rueda (Linux suele usar Button-4/5)
        self.bind("<Control-Button-4>", lambda _e: self._zoom(+1))
        self.bind("<Control-Button-5>", lambda _e: self._zoom(-1))

    def _on_ctrl_wheel(self, event):
        # En Windows el delta suele ser múltiplo de 120
        if getattr(event, "delta", 0) > 0:
            self._zoom(+1)
        else:
            self._zoom(-1)

    def _zoom(self, step: int):
        self._set_font_size(self.base_font_size + step)

    def _set_font_size(self, size: int):
        size = max(self.min_font_size, min(self.max_font_size, int(size)))
        if size == self.base_font_size:
            return

        self.base_font_size = size
        self.ui_font.configure(size=self.base_font_size)
        self.font_size_lbl.configure(text=f"{self.base_font_size} pt")

        self.chat.configure(font=self.ui_font)
        self.entry.configure(font=self.ui_font)

        if hasattr(self, "renderer"):
            self.renderer.set_font_size(self.base_font_size)

    def _set_busy(self, busy: bool):
        # Bloquea input mientras llega la respuesta
        if busy:
            self.send_btn.configure(state="disabled")
            self.entry.configure(state="disabled")
        else:
            self.send_btn.configure(state="normal")
            self.entry.configure(state="normal")
            self.entry.focus_set()

    def on_send(self):
        user_text = self.entry.get().strip()
        if not user_text:
            return

        self.entry.delete(0, "end")
        self.renderer.append_user(user_text)

        self._set_busy(True)
        self._ask_llm_async(user_text)

    def _ask_llm_async(self, user_input: str):
        # Hilo para no bloquear la interfaz
        def worker():
            try:
                raw = self.llm.chat(user_input, temperature=0.7, max_tokens=1024)
                self.result_q.put(("ok", user_input, raw))
            except Exception as e:
                self.result_q.put(("err", user_input, str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _render_new_format(self, data: Dict[str, Any]):
        eventos = data.get("eventos", [])
        for ev in eventos:
            if not isinstance(ev, dict):
                continue
            tipo = (ev.get("tipo") or "").strip().lower()
            texto = ev.get("texto", "")
            if tipo == "narracion" and isinstance(texto, str):
                self.renderer.append_narration(texto)
            elif tipo == "dialogo":
                nombre = ev.get("nombre", "")
                if isinstance(nombre, str) and isinstance(texto, str):
                    self.renderer.append_character(nombre, texto)

        self.renderer.append_choices(data.get("opciones"))

    def _poll_results(self):
        try:
            while True:
                status, user_input, payload = self.result_q.get_nowait()

                if status == "ok":
                    raw = payload
                    outcome = self.parser.parse(raw)

                    if outcome.parse_ok and outcome.format_ok and outcome.data:
                        self._render_new_format(outcome.data)
                    else:
                        self.renderer.append_raw_ai(raw)

                    self.logger.log_turn(
                        user_input=user_input,
                        raw_response=raw,
                        parse_ok=outcome.parse_ok,
                        format_ok=outcome.format_ok,
                        error=outcome.error,
                    )

                else:
                    err = payload
                    self.renderer.append_error(err)
                    self.logger.log_turn(
                        user_input=user_input,
                        raw_response=f"[ERROR] {err}",
                        parse_ok=False,
                        format_ok=False,
                        error=err,
                    )

                self._set_busy(False)

        except queue.Empty:
            pass

        self.after(100, self._poll_results)
