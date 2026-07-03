import os
from anthropic import Anthropic
from dotenv import load_dotenv

from backend.llm.base import LLMConnector

load_dotenv()

MODEL = "claude-sonnet-5"


class ClaudeConnector(LLMConnector):
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.enabled = bool(api_key)
        if self.enabled:
            self.client = Anthropic(api_key=api_key)

    def generar(self, prompt: str) -> str:
        response = self.client.messages.create(
            model=MODEL,
            max_tokens=1024,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": prompt}],
        )
        for block in response.content:
            if block.type == "text":
                return block.text
        return ""
