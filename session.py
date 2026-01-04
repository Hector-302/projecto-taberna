from collections import deque
from typing import Dict, Optional


class Session:
    def __init__(self, max_turns=12, characters: Optional[Dict[str, Dict]] = None, active_character: Optional[str] = None):
        self.max_turns = max_turns
        self.characters: Dict[str, Dict] = characters or {}
        self.active_character_key: Optional[str] = active_character or next(iter(self.characters), None)
        self.histories: Dict[str, deque] = {}  # (character|npc) -> deque

    def reset(self):
        self.histories.clear()
        # Conservar el personaje activo actual si es valido; si no, fallback al primero disponible.
        if self.active_character_key not in self.characters and self.characters:
            self.active_character_key = next(iter(self.characters))

    def _history_key(self, npc_key: str, character_key: Optional[str] = None) -> str:
        key = character_key or self.active_character_key
        if not key:
            raise ValueError("No hay personaje activo para recuperar historial.")
        return f"{key}::{npc_key}"

    def set_active_character(self, character_key: str):
        if character_key not in self.characters:
            raise KeyError(f"Personaje {character_key} no existe en la sesion.")
        self.active_character_key = character_key

    def get_active_character(self) -> Optional[Dict]:
        if not self.active_character_key:
            return None
        return self.characters.get(self.active_character_key)

    def history_for(self, npc_key: str, character_key: Optional[str] = None):
        key = self._history_key(npc_key, character_key)
        if key not in self.histories:
            self.histories[key] = deque(maxlen=self.max_turns * 2)
        return self.histories[key]

    def add_user(self, npc_key: str, text: str, character_key: Optional[str] = None, *, role: str = "user"):
        self.history_for(npc_key, character_key).append({"role": role, "content": text})

    def add_assistant(self, npc_key: str, text: str, character_key: Optional[str] = None):
        self.history_for(npc_key, character_key).append({"role": "assistant", "content": text})

    def get_messages(self, npc_key: str, character_key: Optional[str] = None):
        return list(self.history_for(npc_key, character_key))
