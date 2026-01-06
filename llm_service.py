from typing import Dict, List
from llm_client import LLMClient


class LLMService:
    def __init__(self, prompt_path: str = "prompts/predefined_prompt.txt"):
        self.client = LLMClient()
        self.prompt_path = prompt_path

    def build_messages(self, user_input: str) -> List[Dict[str, str]]:
        with open(self.prompt_path, "r", encoding="utf-8") as f:
            predefined_prompt = f.read()
        final_prompt = predefined_prompt + user_input
        return [{"role": "user", "content": final_prompt}]

    def chat(self, user_input: str, temperature: float = 0.7, max_tokens: int = 1024) -> str:
        messages = self.build_messages(user_input)
        return self.client.chat(messages, temperature=temperature, max_tokens=max_tokens)
