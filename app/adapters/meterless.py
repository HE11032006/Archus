"""
Meterless Adapter: Orchestrates LLM calls through Meterless routing.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple
from openai import OpenAI
from ..config import settings


class MeterlessAdapter:
    def __init__(self):
        self.base_url = settings.model_base_url
        self.api_key = settings.model_api_key
        self.model = settings.model_name
        self.timeout = settings.model_timeout_seconds

    def is_available(self) -> bool:
        return bool(self.base_url and self.api_key)

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1500
    ) -> Optional[str]:
        return self.chat_with_meta(messages, temperature=temperature, max_tokens=max_tokens)[0]

    def chat_with_meta(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500
    ) -> Tuple[Optional[str], Optional[str]]:
        """(reply text, model the endpoint reports it served)."""
        if not self.is_available():
            return None, None

        client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout
        )

        response = client.chat.completions.create(
            model=model or self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        served = getattr(response, "model", None)
        if response.choices and len(response.choices) > 0:
            return response.choices[0].message.content, served
        return None, served
