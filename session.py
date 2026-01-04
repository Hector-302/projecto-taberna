from collections import deque


class Session:
    def __init__(self, max_turns=12):
        self.max_turns = max_turns
        self.histories = {}  # npc_key -> deque

    def reset(self):
        self.histories.clear()

    def history_for(self, npc_key: str):
        if npc_key not in self.histories:
            self.histories[npc_key] = deque(maxlen=self.max_turns * 2)
        return self.histories[npc_key]

    def add_user(self, npc_key: str, text: str):
        self.history_for(npc_key).append({"role": "user", "content": text})

    def add_assistant(self, npc_key: str, text: str):
        self.history_for(npc_key).append({"role": "assistant", "content": text})

    def get_messages(self, npc_key: str):
        return list(self.history_for(npc_key))
