from abc import ABC, abstractmethod


class LLMConnector(ABC):
    """Interfaz común para cualquier proveedor de LLM (Gemini, Claude, ChatGPT, ...)."""

    enabled: bool = False

    @abstractmethod
    def generar(self, prompt: str) -> str:
        """Envía el prompt al proveedor y retorna el texto crudo de la respuesta."""
        raise NotImplementedError
