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

    def chat(self, messages, temperature=0.7, max_tokens=260) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=float(temperature),
            max_tokens=int(max_tokens),
        )
        return resp.choices[0].message.content
