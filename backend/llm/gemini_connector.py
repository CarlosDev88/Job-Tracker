import os
import google.generativeai as genai
from dotenv import load_dotenv

from backend.llm.base import LLMConnector

load_dotenv()


class GeminiConnector(LLMConnector):
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        self.enabled = bool(api_key and api_key != "your_gemini_api_key_here")
        if self.enabled:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-2.5-flash")

    def generar(self, prompt: str) -> str:
        response = self.model.generate_content(prompt)
        return response.text.strip()
