from llm_client import LLMClient


class LLMService:
    def __init__(self, prompt_path: str = "prompts/predefined_prompt.txt"):
        self.client = LLMClient()
        self.prompt_path = prompt_path

    def build_prompt(self, user_input: str) -> str:
        with open(self.prompt_path, "r", encoding="utf-8") as f:
            predefined_prompt = f.read()
        return f"{predefined_prompt}{user_input}"

    def chat(self, user_input: str, temperature: float = 0.7, max_tokens: int = 1024) -> str:
        prompt = self.build_prompt(user_input)
        return self.client.complete_with_grammar(prompt, temperature=temperature, max_tokens=max_tokens)
