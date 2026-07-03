import os
from dotenv import load_dotenv

from backend.llm.base import LLMConnector

load_dotenv()


class ClaudeConnector(LLMConnector):
    """Placeholder — implementar con el SDK de Anthropic."""

    def __init__(self):
        self.enabled = bool(os.getenv("ANTHROPIC_API_KEY"))

    def generar(self, prompt: str) -> str:
        raise NotImplementedError("Conector Claude pendiente de implementar")
