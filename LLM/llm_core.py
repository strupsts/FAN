# CategoryBrain/llm_core.py

from __future__ import annotations

from typing import List, Dict, Any
from openai import OpenAI


class LLMCore:
    """
    Базовый клиент для LLM (Qwen3 через Ollama).
    Здесь НЕТ логики домена (чеки/категории), только:
      - подключение к серверу
      - вызов chat completions
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        api_key: str = "ollama",
        model_name: str = "qwen3:8b",
    ) -> None:
        # Один клиент OpenAI, но с base_url = Ollama
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model_name = model_name

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 256,
    ) -> str:
        """
        Общий метод: отправляем список сообщений и возвращаем content ответа.
        Никакого JSON-парсинга здесь нет — это забота верхнего слоя.
        """
        resp = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        # Берём только текст ответа ассистента
        return resp.choices[0].message.content
