import json
import os

SAVE_PATH = "savegame.json"

def save_session(session_obj):
    data = {k: list(v) for k, v in session_obj.histories.items()}
    with open(SAVE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_session(session_obj):
    if not os.path.exists(SAVE_PATH):
        return
    with open(SAVE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    session_obj.histories.clear()
    for k, msgs in data.items():
        # reconstruyes el deque usando history_for()
        h = session_obj.history_for(k)
        h.clear()
        for m in msgs:
            h.append(m)

def wipe_save():
    try:
        os.remove(SAVE_PATH)
    except FileNotFoundError:
        pass
