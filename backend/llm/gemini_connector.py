import os
import time
import threading
from collections import deque
import google.generativeai as genai
from dotenv import load_dotenv

from backend.llm.base import LLMConnector

load_dotenv()

# Capa gratuita de Gemini: 15 requests por minuto. El throttle es a nivel de
# módulo (no de instancia) porque get_connector() crea una instancia nueva en
# cada llamada dentro de los loops de pipeline.py/normalizador.py — una cola
# compartida es la única forma de que el límite persista entre esas llamadas.
_RPM_LIMIT = 15
_request_times = deque()
_lock = threading.Lock()


def _esperar_turno():
    with _lock:
        while True:
            ahora = time.time()
            while _request_times and ahora - _request_times[0] >= 60:
                _request_times.popleft()
            if len(_request_times) < _RPM_LIMIT:
                _request_times.append(ahora)
                return
            time.sleep(60 - (ahora - _request_times[0]) + 0.1)


class GeminiConnector(LLMConnector):
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        self.enabled = bool(api_key and api_key != "your_gemini_api_key_here")
        if self.enabled:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-2.5-flash")

    def generar(self, prompt: str) -> str:
        _esperar_turno()
        response = self.model.generate_content(prompt)
        return response.text.strip()
