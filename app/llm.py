"""
LLM interface providing unified completion access through the selected provider
with transparent local reasoning fallback when offline or unconfigured.

Providers (selectable per run, or with LLM_PROVIDER):
- "meterless": Meterless Runtime (primary; local Nightshift, routing modes such as meterless/auto)
- "openai_compatible": any OpenAI-compatible endpoint set by MODEL_BASE_URL / MODEL_API_KEY
- "none": no model call; the deterministic rule-based text is kept
If the selected provider is unavailable or fails, the other one is tried, then the rules.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple
from .adapters.meterless import MeterlessAdapter
from .adapters.meterless_runtime import MeterlessRuntimeProvider
from .config import settings

PROVIDER_IDS = ("meterless", "openai_compatible", "none")
PRIMARY_PROVIDER = "meterless"


class LLMClient:
    def __init__(self):
        self.meterless = MeterlessAdapter()  # OpenAI-compatible endpoint from MODEL_* (kept for compatibility)
        self.runtime = MeterlessRuntimeProvider()
        self.providers: Dict[str, Any] = {
            "meterless": self.runtime,
            "openai_compatible": self.meterless,
        }

    @property
    def provider_id(self) -> str:
        """The configured provider: LLM_PROVIDER, else Meterless Runtime."""
        return settings.llm_provider if settings.llm_provider in PROVIDER_IDS else PRIMARY_PROVIDER

    @property
    def provider(self):
        return self.providers.get(self.provider_id)

    def resolve(self, provider_id: Optional[str] = None) -> List[str]:
        """Providers to try, in order: the selected one, then the other configured one."""
        selected = provider_id or self.provider_id
        if selected == "none":
            return []
        order = [selected] + [p for p in self.providers if p != selected]
        return [p for p in order if p in self.providers and self.providers[p].is_available()]

    def is_available(self, provider_id: Optional[str] = None) -> bool:
        return bool(self.resolve(provider_id))

    def _model_for(self, provider_id: str) -> str:
        return self.runtime.model if provider_id == "meterless" else settings.model_name

    def generate_with_meta(
        self,
        prompt: str,
        system_prompt: str = "You are an expert software architect providing verifiable code decision analysis.",
        provider_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """Returns (text or None, call record). The record never holds prompts, keys or tokens."""
        selected = provider_id or self.provider_id
        meta: Dict[str, Any] = {"selected": selected, "attempts": []}
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        for pid in self.resolve(selected):
            requested = model if (model and pid == "meterless") else self._model_for(pid)
            started = time.perf_counter()
            attempt: Dict[str, Any] = {"provider": pid, "model_requested": requested}
            try:
                text, served = self.providers[pid].chat_with_meta(messages, model=requested)
                attempt.update(ok=bool(text), model_served=served)
            except Exception as e:
                text = None
                attempt.update(ok=False, error=type(e).__name__)
            attempt["duration_ms"] = round((time.perf_counter() - started) * 1000, 1)
            meta["attempts"].append(attempt)
            if text:
                meta.update(provider=pid, model_requested=requested, model_served=attempt.get("model_served"),
                            fallback=pid != selected)
                return text, meta
            print(f"[LLM] {pid} unavailable for this call ({attempt.get('error', 'empty reply')}), trying next option.")
        meta.update(provider="rules", fallback=selected != "none")
        return None, meta

    def generate(
        self,
        prompt: str,
        system_prompt: str = "You are an expert software architect providing verifiable code decision analysis.",
        force_local: bool = False,
        provider_id: Optional[str] = None,
    ) -> Optional[str]:
        if force_local:
            return None
        text, _ = self.generate_with_meta(prompt, system_prompt, provider_id=provider_id)
        return text


llm_client = LLMClient()
