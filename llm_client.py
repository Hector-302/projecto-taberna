import os
from openai import OpenAI

class LLMClient:
    def __init__(self):
        self.base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:10000/v1")
        self.api_key = os.getenv("OPENAI_API_KEY", "local")
        self.model = os.getenv("OPENAI_MODEL", "anything")

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
        )

    def chat(self, messages, temperature=0.7, max_tokens=260, character=None) -> str:
        request_messages = list(messages)
        metadata = None
        if isinstance(character, dict):
            metadata = {
                "player": character.get("name"),
                "color": character.get("color"),
            }

        completion_kwargs = {
            "model": self.model,
            "messages": request_messages,
            "temperature": float(temperature),
            "max_tokens": int(max_tokens),
        }
        if metadata:
            completion_kwargs["metadata"] = metadata

        resp = self.client.chat.completions.create(**completion_kwargs)
        return resp.choices[0].message.content
