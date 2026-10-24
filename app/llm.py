"""
LLM interface providing unified completion access via Meterless
with transparent local reasoning fallback when in sample mode or offline.
"""

from __future__ import annotations

from typing import List, Dict, Optional
from .adapters.meterless import MeterlessAdapter
from .config import settings


class LLMClient:
    def __init__(self):
        self.meterless = MeterlessAdapter()

    def generate(
        self,
        prompt: str,
        system_prompt: str = "You are an expert software architect providing verifiable code decision analysis.",
        force_local: bool = False
    ) -> Optional[str]:
        if not force_local and self.meterless.is_available():
            try:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]
                return self.meterless.chat_completion(messages)
            except Exception as e:
                # Log and fallback gracefully
                print(f"[LLM] Meterless call failed, falling back to local reasoning: {e}")
                return None
        return None


llm_client = LLMClient()
