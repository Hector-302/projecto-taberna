import os
from datetime import datetime


class GameLogger:
    def __init__(self, log_path: str):
        self.log_path = log_path
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

    def log_turn(self, user_input: str, raw_response: str, parse_ok: bool, format_ok: bool, error: str = ""):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        block = (
            f"\n----- {ts} -----\n"
            f"USER: {user_input}\n"
            f"PARSE_OK: {parse_ok}\n"
            f"FORMAT_OK: {format_ok}\n"
        )
        if error:
            block += f"ERROR: {error}\n"
        block += f"RAW:\n{raw_response}\n"

        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(block)
        except Exception:
            # El log no debe tumbar la app
            pass
