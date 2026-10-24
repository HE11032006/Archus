"""
Meterless Runtime Provider: OpenAI-compatible provider for the local Meterless Runtime
(Nightshift), following provider contract v4 (Meterless Runtime 1.4).
Model ids are routing modes (meterless/auto, meterless/<class>.<disposition>), not model names.
The token and connect-link key are secrets: they are stored, sent as a Bearer header and never logged.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlsplit, parse_qs

import requests
from openai import OpenAI

from ..config import settings

PROVIDER_ID = "meterless"
PROVIDER_NAME = "Meterless Runtime"
DEFAULT_BASE_URL = "http://127.0.0.1:8088/v1"
APP_ID = "archus"  # stable lowercase id sent as meterless-app
TOKEN_KEY = "meterless_runtime_token"
BASE_URL_KEY = "meterless_runtime_base_url"
PLACEHOLDER_TOKEN = "rt-local"
DEFAULT_MODEL = "meterless/auto"
DISPOSITIONS = ("auto", "fast", "deep", "cheap", "local", "fusion")
REQUEST_TIMEOUT_SECONDS = 180  # a cold model load can take minutes
PROBE_TIMEOUT_SECONDS = 3
DETECT_HOSTS = ("127.0.0.1", "localhost", "[::1]")
DETECT_PORTS = (8088, 8090, 8787, 11434)

_KNOWN_SUFFIXES = ("/v1/chat/completions", "/v1/models", "/healthz", "/v1")


class MeterlessTokenError(ValueError):
    """Raised when a token is missing or is the rejected placeholder."""


# ==========================================
# URL handling
# ==========================================

def normalize_base_url(raw: str) -> str:
    """Turn whatever was pasted (scheme or not, /v1, /v1/models, /healthz...) into <host>/v1."""
    text = (raw or "").strip()
    if not text:
        return DEFAULT_BASE_URL
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", text):
        text = "http://" + text
    parts = urlsplit(text)
    path = parts.path.rstrip("/")
    stripped = True
    while stripped:
        stripped = False
        for suffix in _KNOWN_SUFFIXES:
            if path.endswith(suffix):
                path = path[: -len(suffix)].rstrip("/")
                stripped = True
    return f"{parts.scheme}://{parts.netloc}{path}/v1"


def parse_connect_link(raw: str) -> Optional[Tuple[str, str]]:
    """http://<host>:<port>/connect#k=<key> -> (<origin>/v1, key). None when it isn't a connect link."""
    text = (raw or "").strip()
    if not text:
        return None
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", text):
        text = "http://" + text
    parts = urlsplit(text)
    if parts.path.rstrip("/") != "/connect" or not parts.fragment:
        return None
    key = (parse_qs(parts.fragment).get("k") or [""])[0]
    if not key:
        return None
    return f"{parts.scheme}://{parts.netloc}/v1", key


# ==========================================
# Settings store (base URL + token), never logged
# ==========================================

class SettingsStore:
    """Small JSON key-value store on disk (gitignored). Values are never printed."""

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else settings.provider_settings_file

    def _read(self) -> Dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def get(self, key: str) -> Optional[str]:
        return self._read().get(key)

    def set(self, key: str, value: Optional[str]) -> None:
        data = self._read()
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass


def validate_token(token: Optional[str]) -> str:
    token = (token or "").strip()
    if not token:
        raise MeterlessTokenError("No Meterless Runtime token. Paste the token from the runtime's Console.")
    if token == PLACEHOLDER_TOKEN:
        raise MeterlessTokenError("'rt-local' is a placeholder the runtime rejects. Paste the real token.")
    return token


def _read_proxy_token(state_dir: Optional[str]) -> Optional[str]:
    if not state_dir:
        return None
    try:
        token = (Path(state_dir) / "proxy-token").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return token or None


# ==========================================
# Provider
# ==========================================

class MeterlessRuntimeProvider:
    id = PROVIDER_ID
    name = PROVIDER_NAME

    def __init__(self, store: Optional[SettingsStore] = None, model: Optional[str] = None):
        self.store = store or SettingsStore()
        self.model = model or settings.meterless_model or DEFAULT_MODEL
        self.timeout = REQUEST_TIMEOUT_SECONDS

    def __repr__(self) -> str:  # never expose the token
        return f"MeterlessRuntimeProvider(base_url={self.base_url!r}, token={'set' if self.token else 'missing'})"

    # ---------- configuration ----------

    @property
    def base_url(self) -> str:
        stored = self.store.get(BASE_URL_KEY) or settings.meterless_base_url
        return normalize_base_url(stored) if stored else DEFAULT_BASE_URL

    @property
    def token(self) -> Optional[str]:
        """Stored token first, then METERLESS_RUNTIME_TOKEN, then <stateDir>/proxy-token. rt-local never counts."""
        for candidate in (
            self.store.get(TOKEN_KEY),
            settings.meterless_runtime_token,
            _read_proxy_token(settings.meterless_state_dir),
        ):
            if candidate and candidate.strip() and candidate.strip() != PLACEHOLDER_TOKEN:
                return candidate.strip()
        return None

    def set_base_url(self, raw: str) -> str:
        url = normalize_base_url(raw)
        self.store.set(BASE_URL_KEY, url)
        return url

    def set_token(self, token: str) -> None:
        self.store.set(TOKEN_KEY, validate_token(token))

    def connect(self, pasted: str) -> Dict[str, Any]:
        """Accept a connect link (base URL + key) or a plain URL. Returns the status, never the key."""
        link = parse_connect_link(pasted)
        if link:
            base_url, key = link
            self.set_base_url(base_url)
            self.set_token(key)
        else:
            self.set_base_url(pasted)
        return self.status()

    def headers(self, chat: bool = False, token: Optional[str] = None) -> Dict[str, str]:
        result = {"meterless-app": APP_ID}
        bearer = token if token is not None else self.token
        if bearer:
            result["Authorization"] = f"Bearer {bearer}"
        if chat:
            result["meterless-scope"] = "user"
        return result

    # ---------- status & models ----------

    def probe(self, base_url: Optional[str] = None, token: Optional[str] = None) -> Dict[str, Any]:
        """GET /v1/models decides: 401/403 unauthorized, 200 with meterless ids online, anything else offline."""
        url = normalize_base_url(base_url) if base_url else self.base_url
        result: Dict[str, Any] = {"provider": self.id, "base_url": url, "status": "offline", "models": []}
        try:
            response = requests.get(f"{url}/models", headers=self.headers(token=token), timeout=PROBE_TIMEOUT_SECONDS)
        except requests.RequestException:
            result["process_up"] = self._healthz(url)
            return result

        result["process_up"] = True
        if response.status_code in (401, 403):
            result["status"] = "unauthorized"
            result["needs_token"] = True
            result["token_field"] = TOKEN_KEY
            return result
        if response.status_code == 200:
            models = self._meterless_ids(response)
            if models:
                result["status"] = "online"
                result["models"] = models
        return result

    def status(self) -> Dict[str, Any]:
        result = self.probe()
        result["token"] = "set" if self.token else "missing"
        return result

    def list_models(self) -> List[str]:
        return self.probe()["models"]

    def _healthz(self, base_url: str) -> bool:
        origin = base_url[: -len("/v1")]
        try:
            return requests.get(f"{origin}/healthz", headers=self.headers(), timeout=PROBE_TIMEOUT_SECONDS).ok
        except requests.RequestException:
            return False

    @staticmethod
    def _meterless_ids(response: requests.Response) -> List[str]:
        try:
            payload = response.json()
        except ValueError:
            return []
        entries = payload.get("data", []) if isinstance(payload, dict) else []
        ids = [e.get("id") for e in entries if isinstance(e, dict) and isinstance(e.get("id"), str)]
        # Keep every meterless/* id, including ones this app doesn't recognise
        return [i for i in ids if i.startswith("meterless/")]

    def auto_detect(
        self,
        hosts: Iterable[str] = DETECT_HOSTS,
        ports: Iterable[int] = DETECT_PORTS,
        save: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Try every host x port; save and return the first online or unauthorized hit."""
        for port in ports:
            for host in hosts:
                hit = self.probe(base_url=f"http://{host}:{port}/v1")
                if hit["status"] in ("online", "unauthorized"):
                    if save:
                        self.set_base_url(hit["base_url"])
                    return hit
        return None

    # ---------- chat ----------

    def is_available(self) -> bool:
        return bool(self.token)

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ) -> Optional[str]:
        """Plain text in (string content, exactly like OpenAI), plain text out."""
        return self.chat_with_meta(messages, model, temperature, max_tokens)[0]

    def chat_with_meta(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ) -> Tuple[Optional[str], Optional[str]]:
        """(reply text, model the runtime reports it served). The routing mode decides the model."""
        token = validate_token(self.token)
        client = OpenAI(
            base_url=self.base_url,
            api_key=token,
            timeout=self.timeout,
            default_headers={"meterless-app": APP_ID, "meterless-scope": "user"},
        )
        response = client.chat.completions.create(
            model=model or self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        served = getattr(response, "model", None)
        if response.choices:
            return response.choices[0].message.content, served
        return None, served
