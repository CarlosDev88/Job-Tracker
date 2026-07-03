import os
from dotenv import load_dotenv

from backend.llm.base import LLMConnector
from backend.llm.gemini_connector import GeminiConnector
from backend.llm.claude_connector import ClaudeConnector
from backend.llm.chatgpt_connector import ChatGPTConnector

load_dotenv()

CONNECTORS = {
    "gemini": GeminiConnector,
    "claude": ClaudeConnector,
    "chatgpt": ChatGPTConnector,
}


def get_connector() -> LLMConnector:
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    connector_cls = CONNECTORS.get(provider, GeminiConnector)
    return connector_cls()
