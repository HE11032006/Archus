"""
Meterless Runtime provider tests (provider contract v4).
Runs against tests/meterless_stub.py, a local stand-in that enforces the contract; not the real runtime.

Run: python -m unittest tests.test_meterless_runtime -v
"""

from __future__ import annotations

import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from app.adapters.meterless_runtime import (  # noqa: E402
    APP_ID,
    MODEL_KEY,
    TOKEN_KEY,
    MeterlessModeError,
    MeterlessRuntimeProvider,
    MeterlessTokenError,
    SettingsStore,
    normalize_base_url,
    parse_connect_link,
)
from app.config import settings  # noqa: E402
from meterless_stub import start_stub  # noqa: E402


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class IsolatedProviderTest(unittest.TestCase):
    """Each test gets its own settings file and no token from the environment."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for name, value in (("meterless_runtime_token", ""), ("meterless_state_dir", ""),
                            ("meterless_base_url", ""), ("meterless_model", "meterless/auto")):
            patcher = mock.patch.object(settings, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.store = SettingsStore(Path(self.tmp.name) / "provider_settings.json")
        self.provider = MeterlessRuntimeProvider(store=self.store)

    def stub(self, **kwargs):
        server, state = start_stub(**kwargs)
        self.addCleanup(server.shutdown)
        return f"http://127.0.0.1:{server.server_address[1]}/v1", state


class UrlTests(unittest.TestCase):
    def test_every_pasted_form_normalises_to_host_v1(self):
        cases = {
            "127.0.0.1:8088": "http://127.0.0.1:8088/v1",
            "http://127.0.0.1:8088": "http://127.0.0.1:8088/v1",
            "http://127.0.0.1:8088/": "http://127.0.0.1:8088/v1",
            "http://127.0.0.1:8088/v1": "http://127.0.0.1:8088/v1",
            "http://127.0.0.1:8088/v1/": "http://127.0.0.1:8088/v1",
            "http://127.0.0.1:8088/v1/chat/completions": "http://127.0.0.1:8088/v1",
            "127.0.0.1:8088/v1/models": "http://127.0.0.1:8088/v1",
            "http://localhost:8090/healthz": "http://localhost:8090/v1",
            "http://127.0.0.1:8088/v1/v1": "http://127.0.0.1:8088/v1",
            "[::1]:8787": "http://[::1]:8787/v1",
            "https://box.local:11434/v1/models/": "https://box.local:11434/v1",
            "  http://127.0.0.1:8088/v1  ": "http://127.0.0.1:8088/v1",
            "": "http://127.0.0.1:8088/v1",
        }
        for pasted, expected in cases.items():
            with self.subTest(pasted=pasted):
                self.assertEqual(normalize_base_url(pasted), expected)
                self.assertNotIn("/v1/v1", normalize_base_url(pasted))

    def test_connect_link_gives_origin_v1_and_key(self):
        self.assertEqual(parse_connect_link("http://192.168.1.20:8088/connect#k=abc123"),
                         ("http://192.168.1.20:8088/v1", "abc123"))
        self.assertEqual(parse_connect_link("127.0.0.1:8090/connect#k=xyz"), ("http://127.0.0.1:8090/v1", "xyz"))
        self.assertIsNone(parse_connect_link("http://127.0.0.1:8088/v1"))
        self.assertIsNone(parse_connect_link("http://127.0.0.1:8088/connect"))


class TokenTests(IsolatedProviderTest):
    def test_placeholder_rt_local_is_rejected(self):
        with self.assertRaises(MeterlessTokenError):
            self.provider.set_token("rt-local")
        self.assertIsNone(self.store.get(TOKEN_KEY))
        self.store.set(TOKEN_KEY, "rt-local")  # even if written by hand, it never counts
        self.assertIsNone(self.provider.token)

    def test_token_is_stored_under_meterless_runtime_token_and_never_shown(self):
        self.provider.set_token("secret-value-123")
        self.assertEqual(self.store.get("meterless_runtime_token"), "secret-value-123")
        self.assertNotIn("secret-value-123", repr(self.provider))
        self.assertNotIn("secret-value-123", str(self.provider.status()))

    def test_token_is_read_from_state_dir_proxy_token(self):
        state_dir = Path(self.tmp.name) / "state"
        state_dir.mkdir()
        (state_dir / "proxy-token").write_text("from-runtime\n", encoding="utf-8")
        with mock.patch.object(settings, "meterless_state_dir", str(state_dir)):
            self.assertEqual(self.provider.token, "from-runtime")


class StatusTests(IsolatedProviderTest):
    def test_wrong_token_is_unauthorized_not_offline(self):
        base_url, _ = self.stub(token="the-real-token")
        self.provider.set_base_url(base_url)
        self.provider.set_token("a-wrong-token")
        status = self.provider.status()
        self.assertEqual(status["status"], "unauthorized")
        self.assertTrue(status["needs_token"])
        self.assertEqual(status["token_field"], TOKEN_KEY)

    def test_missing_token_is_unauthorized(self):
        base_url, _ = self.stub(token="the-real-token")
        self.provider.set_base_url(base_url)
        self.assertEqual(self.provider.status()["status"], "unauthorized")

    def test_right_token_is_online_with_routing_modes_unknown_ones_kept(self):
        base_url, state = self.stub(token="the-real-token")
        self.provider.set_base_url(base_url + "/models")  # pasted with /models on purpose
        self.provider.set_token("the-real-token")
        status = self.provider.status()
        self.assertEqual(status["status"], "online")
        self.assertIn("meterless/auto", status["models"])
        self.assertIn("meterless/vision-xl.deep", status["models"])  # unrecognised meterless/* id kept
        self.assertNotIn("not-a-routing-mode", status["models"])
        last = state.requests[-1]
        self.assertTrue(last["authorized"])
        self.assertEqual(last["meterless_app"], APP_ID)

    def test_nothing_listening_is_offline(self):
        self.provider.set_base_url(f"http://127.0.0.1:{free_port()}")
        self.provider.set_token("whatever")
        status = self.provider.status()
        self.assertEqual(status["status"], "offline")
        self.assertFalse(status["process_up"])

    def test_healthz_up_but_models_failing_is_offline(self):
        base_url, _ = self.stub(token="t", models_status=500)
        self.provider.set_base_url(base_url)
        self.provider.set_token("t")
        self.assertEqual(self.provider.status()["status"], "offline")


class AutoDetectTests(IsolatedProviderTest):
    def test_auto_detect_saves_the_first_online_or_unauthorized_hit(self):
        base_url, _ = self.stub(token="tok")
        port = int(base_url.split(":")[-1].split("/")[0])
        hit = self.provider.auto_detect(ports=(free_port(), port))
        self.assertIsNotNone(hit)
        self.assertEqual(hit["status"], "unauthorized")  # no token yet: still a hit
        self.assertEqual(self.store.get("meterless_runtime_base_url"), hit["base_url"])
        self.assertTrue(hit["base_url"].endswith(f":{port}/v1"))

    def test_auto_detect_finds_nothing_when_nothing_listens(self):
        self.assertIsNone(self.provider.auto_detect(hosts=("127.0.0.1",), ports=(free_port(),)))
        self.assertIsNone(self.store.get("meterless_runtime_base_url"))


class ChatTests(IsolatedProviderTest):
    def test_plain_text_on_meterless_auto_returns_a_string(self):
        base_url, state = self.stub(token="tok")
        self.provider.set_base_url(base_url)
        self.provider.set_token("tok")
        reply = self.provider.chat_completion([{"role": "user", "content": "Say hello"}], model="meterless/auto")
        self.assertIsInstance(reply, str)
        self.assertEqual(reply, "Stub reply to: Say hello")
        last = state.requests[-1]
        self.assertEqual(last["path"], "/v1/chat/completions")
        self.assertEqual(last["meterless_app"], APP_ID)
        self.assertEqual(last["meterless_scope"], "user")
        self.assertEqual(last["body"]["model"], "meterless/auto")
        self.assertIsInstance(last["body"]["messages"][0]["content"], str)

    def test_connect_link_sets_url_and_key_then_chat_works(self):
        base_url, _ = self.stub(token="link-key")
        origin = base_url[: -len("/v1")]
        status = self.provider.connect(f"{origin}/connect#k=link-key")
        self.assertEqual(status["status"], "online")
        self.assertNotIn("link-key", str(status))
        self.assertIsInstance(self.provider.chat_completion([{"role": "user", "content": "hi"}]), str)

    def test_chat_without_token_refuses_before_calling(self):
        with self.assertRaises(MeterlessTokenError):
            self.provider.chat_completion([{"role": "user", "content": "hi"}])

    def test_reasoning_text_is_stripped_from_replies(self):
        from app.adapters.meterless_runtime import strip_reasoning
        self.assertEqual(strip_reasoning("The user wants one sentence.</think>Connection confirmed."), "Connection confirmed.")
        self.assertEqual(strip_reasoning("<think>plan\nmore</think>\n\nFinal answer."), "Final answer.")
        self.assertEqual(strip_reasoning("No thinking here."), "No thinking here.")
        self.assertIsNone(strip_reasoning("only thinking</think>   "))
        self.assertIsNone(strip_reasoning(None))

    def test_timeout_is_180_seconds(self):
        self.assertEqual(self.provider.timeout, 180)


class RoutingModeTests(IsolatedProviderTest):
    def test_default_mode_is_meterless_auto_and_env_overrides_it(self):
        self.assertEqual(self.provider.model, "meterless/auto")
        with mock.patch.object(settings, "meterless_model", "meterless/fast"):
            self.assertEqual(self.provider.model, "meterless/fast")

    def test_saved_mode_wins_over_env_and_shows_in_status(self):
        base_url, _ = self.stub(token="tok")
        self.provider.set_base_url(base_url)
        self.provider.set_token("tok")
        result = self.provider.set_model("meterless/deep")
        self.assertEqual(self.store.get(MODEL_KEY), "meterless/deep")
        self.assertTrue(result["offered_by_runtime"])
        with mock.patch.object(settings, "meterless_model", "meterless/fast"):
            self.assertEqual(self.provider.model, "meterless/deep")
        self.assertEqual(self.provider.status()["model"], "meterless/deep")

    def test_unknown_meterless_mode_is_accepted_but_flagged(self):
        base_url, _ = self.stub(token="tok")
        self.provider.set_base_url(base_url)
        self.provider.set_token("tok")
        result = self.provider.set_model("meterless/brand-new.deep")
        self.assertEqual(self.store.get(MODEL_KEY), "meterless/brand-new.deep")
        self.assertFalse(result["offered_by_runtime"])

    def test_mode_can_be_saved_while_runtime_is_offline(self):
        self.provider.set_base_url(f"http://127.0.0.1:{free_port()}")
        result = self.provider.set_model("meterless/cheap")
        self.assertIsNone(result["offered_by_runtime"])
        self.assertEqual(result["runtime_status"], "offline")

    def test_non_meterless_ids_are_rejected(self):
        for bad in ("gpt-4o", "nvidia/nemotron", "meterless/", "meterless", "meterless/ deep", ""):
            with self.subTest(mode=bad):
                with self.assertRaises(MeterlessModeError):
                    self.provider.set_model(bad)
        self.assertIsNone(self.store.get(MODEL_KEY))

    def test_chat_uses_the_saved_mode(self):
        base_url, state = self.stub(token="tok")
        self.provider.set_base_url(base_url)
        self.provider.set_token("tok")
        self.provider.set_model("meterless/text.fast")
        self.provider.chat_completion([{"role": "user", "content": "hi"}])
        self.assertEqual(state.requests[-1]["body"]["model"], "meterless/text.fast")


if __name__ == "__main__":
    unittest.main()
