"""
Provider selection tests: Meterless Runtime is the primary provider, selectable per run,
with the OpenAI-compatible provider and the deterministic rules as fallbacks.
Meterless calls go to tests/meterless_stub.py (a local stand-in, not the real runtime).

Run: python -m unittest tests.test_provider_selection -v
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from app.adapters.meterless_runtime import MeterlessRuntimeProvider, SettingsStore  # noqa: E402
from app.config import settings  # noqa: E402
from app.llm import LLMClient  # noqa: E402
from app.orchestration.graph import OrchestrationGraph  # noqa: E402
from app.world_model import WorldModel  # noqa: E402
from meterless_stub import start_stub  # noqa: E402


class ProviderSelectionTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for name, value in (("llm_provider", ""), ("meterless_runtime_token", ""),
                            ("meterless_state_dir", ""), ("meterless_base_url", ""),
                            ("meterless_model", "meterless/auto")):
            patcher = mock.patch.object(settings, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

        self.client = LLMClient()
        self.runtime = MeterlessRuntimeProvider(store=SettingsStore(Path(tmp.name) / "settings.json"))
        self.client.runtime = self.runtime
        self.client.providers["meterless"] = self.runtime
        # The OpenAI-compatible provider is off unless a test turns it on (no network in tests)
        self.openai_available = mock.patch.object(self.client.meterless, "is_available", return_value=False)
        self.openai_available.start()
        self.addCleanup(self.openai_available.stop)

        reporter_patch = mock.patch("app.agents.reporter.llm_client", self.client)
        reporter_patch.start()
        self.addCleanup(reporter_patch.stop)
        self.graph = OrchestrationGraph(force_sample_mode=True, world=WorldModel())

    def connect_stub(self, token="tok"):
        server, state = start_stub(token=token)
        self.addCleanup(server.shutdown)
        self.runtime.set_base_url(f"127.0.0.1:{server.server_address[1]}")
        self.runtime.set_token(token)
        return state

    def run_accounts(self, provider=None, model=None):
        return self.graph.execute_run("Should we refactor or maintain accounts?", "django_app", "accounts", True,
                                      provider, model)

    def test_meterless_is_the_default_provider(self):
        self.assertEqual(self.client.provider_id, "meterless")

    def test_demo_run_summary_comes_from_meterless_auto(self):
        stub = self.connect_stub()
        res = self.run_accounts()
        self.assertEqual(res.output.decision, "refactor")  # decision never depends on the model
        mp = res.output.model_provider
        self.assertEqual(mp["provider"], "meterless")
        self.assertEqual(mp["model_requested"], "meterless/auto")
        self.assertEqual(mp["model_served"], "meterless/auto")
        self.assertFalse(mp["fallback"])
        self.assertTrue(res.output.summary.startswith("Stub reply to: Question: Should we refactor"))
        chat = [r for r in stub.requests if r["path"] == "/v1/chat/completions"][-1]
        self.assertEqual(chat["meterless_app"], "archus")
        self.assertEqual(chat["meterless_scope"], "user")

    def test_routing_mode_is_configurable(self):
        self.connect_stub()
        with mock.patch.object(settings, "meterless_model", "meterless/deep"):
            res = self.run_accounts()
        self.assertEqual(res.output.model_provider["model_requested"], "meterless/deep")

    def test_provider_none_keeps_the_rules_text(self):
        stub = self.connect_stub()
        res = self.run_accounts(provider="none")
        self.assertEqual(res.output.model_provider["provider"], "rules")
        self.assertTrue(res.output.summary.startswith("Decision: REFACTOR"))
        self.assertFalse(any(r["path"] == "/v1/chat/completions" for r in stub.requests))

    def test_meterless_failing_falls_back_to_openai_compatible(self):
        self.connect_stub(token="tok")
        self.runtime.set_token("wrong-token")  # the runtime answers 401 on chat
        with mock.patch.object(self.client.meterless, "is_available", return_value=True), \
             mock.patch.object(self.client.meterless, "chat_with_meta",
                               return_value=("Fallback summary from the OpenAI-compatible provider.", "nvidia/test")):
            res = self.run_accounts()
        mp = res.output.model_provider
        self.assertEqual(mp["provider"], "openai_compatible")
        self.assertTrue(mp["fallback"])
        self.assertEqual([a["provider"] for a in mp["attempts"]], ["meterless", "openai_compatible"])
        self.assertFalse(mp["attempts"][0]["ok"])

    def test_nothing_available_falls_back_to_rules(self):
        res = self.run_accounts()
        self.assertEqual(res.output.decision, "refactor")
        self.assertEqual(res.output.model_provider["provider"], "rules")
        self.assertTrue(res.output.summary.startswith("Decision: REFACTOR"))

    def test_openai_compatible_can_be_selected_per_run(self):
        self.connect_stub()
        with mock.patch.object(self.client.meterless, "is_available", return_value=True), \
             mock.patch.object(self.client.meterless, "chat_with_meta",
                               return_value=("Summary written by the OpenAI-compatible provider.", "nvidia/test")):
            res = self.run_accounts(provider="openai_compatible")
        self.assertEqual(res.output.model_provider["provider"], "openai_compatible")
        self.assertFalse(res.output.model_provider["fallback"])


    def test_saved_routing_mode_is_used_by_runs(self):
        stub = self.connect_stub()
        self.runtime.set_model("meterless/deep")
        res = self.run_accounts()
        self.assertEqual(res.output.model_provider["model_requested"], "meterless/deep")
        chat = [r for r in stub.requests if r["path"] == "/v1/chat/completions"][-1]
        self.assertEqual(chat["body"]["model"], "meterless/deep")

    def test_per_run_model_overrides_the_saved_mode(self):
        stub = self.connect_stub()
        self.runtime.set_model("meterless/deep")
        res = self.run_accounts(model="meterless/fast")
        self.assertEqual(res.output.model_provider["model_requested"], "meterless/fast")
        self.assertEqual(self.runtime.model, "meterless/deep")  # the saved mode is left alone
        chat = [r for r in stub.requests if r["path"] == "/v1/chat/completions"][-1]
        self.assertEqual(chat["body"]["model"], "meterless/fast")

    def test_post_run_accepts_options_model_and_rejects_non_meterless(self):
        from fastapi.testclient import TestClient
        import run as run_module
        self.connect_stub()
        payload = {"input": {"query": "Should we migrate legacy billing?", "repo": "legacy_service",
                             "module_path": "billing"},
                   "options": {"sample_mode": True, "provider": "meterless", "model": "meterless/cheap"}}
        with mock.patch.object(run_module, "graph", self.graph):
            client = TestClient(run_module.app)
            ok = client.post("/run", json=payload).json()
            payload["options"]["model"] = "gpt-4o"
            bad = client.post("/run", json=payload)
        self.assertEqual(ok["output"]["decision"], "migrate")
        self.assertEqual(ok["output"]["model_provider"]["model_requested"], "meterless/cheap")
        self.assertEqual(bad.status_code, 422)

    def test_settings_api_stays_read_only(self):
        from fastapi.testclient import TestClient
        import run as run_module
        client = TestClient(run_module.app)
        for path in ("/providers", "/providers/meterless/status"):
            self.assertEqual(client.post(path, json={"model": "meterless/deep"}).status_code, 405)


if __name__ == "__main__":
    unittest.main()
