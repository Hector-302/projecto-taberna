import os
import queue
import threading
from typing import Any, Dict, Tuple

import tkinter as tk
from tkinter import ttk

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

        self._build_ui()
        self.renderer = ChatRenderer(self.chat, self.character_colors)

        self.after(100, self._poll_results)

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        main_frame = ttk.Frame(self, padding=10)
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

        self.chat = tk.Text(main_frame, wrap="word", state="disabled", bg="#0d1117", fg="#e5e7eb")
        self.chat.grid(row=0, column=0, sticky="nsew")

        scroll = ttk.Scrollbar(main_frame, command=self.chat.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.chat["yscrollcommand"] = scroll.set

        bottom = ttk.Frame(self, padding=10)
        bottom.grid(row=1, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)

        self.entry = ttk.Entry(bottom)
        self.entry.grid(row=0, column=0, sticky="ew")
        self.entry.bind("<Return>", lambda _e: self.on_send())

        self.send_btn = ttk.Button(bottom, text="Enviar", command=self.on_send)
        self.send_btn.grid(row=0, column=1, padx=(10, 0))

    def _set_busy(self, busy: bool):
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
