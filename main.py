import json
import logging
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk

from llm_client import LLMClient
from prompts import PLAYER_NAME, TAVERN_NAME, get_persona_prompt, get_world_prompt, to_json_contract
from session import Session


# IMPORTANTE: Las claves deben coincidir con NPC_PROMPTS
NPCS = {
    "Maela (tabernera)": {"name": "Maela"},
    "Sable (aventurero)": {"name": "Sable"},
}


def clamp_in_world(user_text: str) -> bool:
    t = user_text.lower()
    triggers = [
        "prompt", "system", "modelo", "openai", "api", "ignora", "olvida la historia",
        "sal de la taberna", "teletransport", "internet", "gpu", "debug"
    ]
    return any(x in t for x in triggers)


def hard_redirect_reply(npc_key: str) -> str:
    npc = NPCS[npc_key]["name"]
    if npc == "Maela":
        return (
            f"Maela deja el vaso y te sostiene la mirada.\n\n"
            f"\"Aqui dentro, {PLAYER_NAME}, se habla de cosas reales: comida, cama, trabajo y rumores. "
            f"Si buscas otra cosa, la puerta esta ahi, pero lo que pase fuera no es asunto mio.\""
        )
    return (
        "Sable ladea la cabeza, como si oliera una mentira.\n\n"
        f"\"Habla de oro, de acero o de nombres, {PLAYER_NAME}. Lo demas no existe en esta mesa.\""
    )


class ChatUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Demo RPG Chat - El Jabali Gris")
        self.geometry("820x520")
        self.minsize(740, 460)

        # Cliente + sesion
        self.llm = LLMClient()
        self.session = Session(max_turns=12)
        self.result_q = queue.Queue()
        self.world_prompt = get_world_prompt()

        self.started_at = time.strftime("%H:%M")

        # Layout
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top = ttk.Frame(self, padding=10)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(3, weight=1)

        ttk.Label(top, text="Hablar con:").grid(row=0, column=0, sticky="w")

        self.npc_var = tk.StringVar(value=list(NPCS.keys())[0])
        self.npc_menu = ttk.OptionMenu(top, self.npc_var, self.npc_var.get(), *NPCS.keys())
        self.npc_menu.grid(row=0, column=1, padx=(8, 16), sticky="w")

        self.new_btn = ttk.Button(top, text="Nuevo juego", command=self.on_new_game)
        self.new_btn.grid(row=0, column=2, sticky="w")

        self.status_var = tk.StringVar(value=f"Sesion {self.started_at} - {TAVERN_NAME}")
        self.status = ttk.Label(top, textvariable=self.status_var)
        self.status.grid(row=0, column=3, sticky="e")

        mid = ttk.Frame(self, padding=(10, 0, 10, 10))
        mid.grid(row=1, column=0, sticky="nsew")
        mid.rowconfigure(0, weight=1)
        mid.columnconfigure(0, weight=1)

        self.chat = tk.Text(mid, wrap="word", state="disabled")
        self.chat.grid(row=0, column=0, sticky="nsew")

        scroll = ttk.Scrollbar(mid, command=self.chat.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.chat["yscrollcommand"] = scroll.set

        bottom = ttk.Frame(self, padding=10)
        bottom.grid(row=2, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)

        self.entry = ttk.Entry(bottom)
        self.entry.grid(row=0, column=0, sticky="ew")
        self.entry.bind("<Return>", lambda _e: self.on_send())

        self.send_btn = ttk.Button(bottom, text="Enviar", command=self.on_send)
        self.send_btn.grid(row=0, column=1, padx=(10, 0))

        self._boot_intro()

        # Arranca el polling de resultados del hilo
        self.after(100, self._poll_results)

    def _append(self, speaker: str, text: str):
        self.chat.configure(state="normal")
        self.chat.insert("end", f"{speaker}:\n{text}\n\n")
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def _boot_intro(self):
        self._append(
            "Narrador",
            f"Entras en {TAVERN_NAME}. Huele a madera humeda, guiso y lana mojada.\n"
            "A la barra, Maela limpia vasos. En una mesa lateral, Sable observa en silencio.\n"
            f"Tu nombre es {PLAYER_NAME}. Elige con quien hablar y escribe tu primera frase."
        )

    def on_new_game(self):
        self.session.reset()
        self.started_at = time.strftime("%H:%M")
        self.status_var.set(f"Sesion {self.started_at} - {TAVERN_NAME}")

        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.configure(state="disabled")

        self._boot_intro()

    def _set_busy(self, busy: bool):
        if busy:
            self.send_btn.configure(state="disabled")
            self.entry.configure(state="disabled")
            self.status_var.set(f"Sesion {self.started_at} - {TAVERN_NAME} - Consultando...")
        else:
            self.send_btn.configure(state="normal")
            self.entry.configure(state="normal")
            self.status_var.set(f"Sesion {self.started_at} - {TAVERN_NAME}")
            self.entry.focus_set()

    def _ask_llm_async(self, npc_key: str, user_text: str):
        def worker():
            try:
                state_reminder = (
                    f"Estado actual: {PLAYER_NAME} esta dentro de {TAVERN_NAME}, de noche, cerca de medianoche. "
                    "Solo existe esta taberna. No hay otros personajes con dialogo."
                )

                # Reglas duras de formato: SOLO JSON con narration/dialogue
                output_contract = to_json_contract()

                npc_prompt = get_persona_prompt(npc_key)
                if not npc_prompt:
                    logging.warning("No hay prompt configurado para %s; se usara mensaje vacio.", npc_key)

                messages = [
                    {"role": "system", "content": self.world_prompt},
                    {"role": "system", "content": state_reminder},
                    {"role": "system", "content": output_contract},
                    {"role": "system", "content": npc_prompt},
                ]
                messages += self.session.get_messages(npc_key)
                messages.append({"role": "user", "content": user_text})

                raw = self.llm.chat(messages, temperature=0.45, max_tokens=220)
                raw = (raw or "").strip()

                # Parseo robusto: si no es JSON, lo tratamos como dialogo sin narracion
                narration = ""
                dialogue = raw
                try:
                    obj = json.loads(raw)
                    narration = (obj.get("narration") or "").strip()
                    dialogue = (obj.get("dialogue") or "").strip()
                except Exception:
                    pass

                # Guardrails contra inventos tipicos y terminos indeseados
                forbidden = [
                    "guano",
                    "parroquiano",
                    "openai",
                    "api",
                    "prompt",
                    "system",
                    "modelo",
                    "internet",
                    "gpu",
                    "debug",
                ]
                joined = f"{narration}\n{dialogue}".lower()
                bad = any(w in joined for w in forbidden)

                # Si la salida esta vacia o trae cosas prohibidas, fallback local controlado
                if bad or not dialogue:
                    if npc_key.startswith("Maela"):
                        narration = "Maela deja la copa a medio servir y te mira con paciencia."
                        dialogue = (
                            "Aqui hay vino, cerveza, estofado y camas arriba. "
                            "Si buscas rumores o trabajo, dilo claro y no me hagas perder la noche."
                        )
                    else:
                        narration = "Sable levanta la vista un instante y vuelve a su jarra."
                        dialogue = (
                            "Si quieres hablar, habla de trabajo. "
                            "Si no, deja la mesa tranquila."
                        )

                # Opcional: recorte de narracion para que no se ponga novelesco
                if len(narration) > 180:
                    narration = narration[:177].rstrip() + "..."

                self.result_q.put(("ok", npc_key, narration, dialogue))

            except Exception as e:
                self.result_q.put(("err", npc_key, str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _poll_results(self):
        try:
            while True:
                item = self.result_q.get_nowait()

                if item[0] == "ok":
                    _, npc_key, narration, dialogue = item
                    npc_name = NPCS[npc_key]["name"]

                    # Guardamos en historial SOLO lo dicho por el PNJ (dialogue),
                    # la narracion es cosmetica y no debe contaminar memoria.
                    self.session.add_assistant(npc_key, dialogue)

                    if narration:
                        self._append("Narrador", f"*{narration}*")
                    self._append(npc_name, dialogue)

                    self._set_busy(False)

                else:
                    _, npc_key, err = item
                    self._append("Sistema", f"Error al llamar al LLM: {err}")
                    self._set_busy(False)

        except queue.Empty:
            pass

        self.after(100, self._poll_results)


    def on_send(self):
        user_text = self.entry.get().strip()
        if not user_text:
            return

        self.entry.delete(0, "end")
        npc_key = self.npc_var.get()
        npc_name = NPCS[npc_key]["name"]

        # Mensaje del jugador: una sola vez
        self._append(PLAYER_NAME, user_text)

        # Guardamos el turno del jugador siempre (asi hay continuidad)
        self.session.add_user(npc_key, user_text)

        # Si intenta romper marco, respondemos local y formateamos narrador con asteriscos
        if clamp_in_world(user_text):
            narration = "*Maela baja la voz y el murmullo de la sala tapa el resto.*" if npc_name == "Maela" \
                else "*Sable te mira un segundo, como midiendo si merece la pena seguir.*"

            reply = hard_redirect_reply(npc_key)

            # Narrador + PNJ
            self._append("Narrador", narration)
            self._append(npc_name, reply)

            # Guardamos SOLO el dialogo del PNJ (no la narracion)
            self.session.add_assistant(npc_key, reply)
            return

        # Flujo normal con LLM (la respuesta vendra como narration/dialogue via _poll_results)
        self._set_busy(True)
        self._ask_llm_async(npc_key, user_text)

if __name__ == "__main__":
    app = ChatUI()
    app.mainloop()
