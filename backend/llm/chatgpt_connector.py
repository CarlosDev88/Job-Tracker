import os
from dotenv import load_dotenv

from backend.llm.base import LLMConnector

load_dotenv()


class ChatGPTConnector(LLMConnector):
    """Placeholder — implementar con el SDK de OpenAI."""

    def __init__(self):
        self.enabled = bool(os.getenv("OPENAI_API_KEY"))

    def generar(self, prompt: str) -> str:
        raise NotImplementedError("Conector ChatGPT pendiente de implementar")
