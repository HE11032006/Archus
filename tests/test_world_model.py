"""
World Model tests.
Part 1 ports the official conformance checks (engines/world-model/conformance/runner.ts) to Python.
Part 2 proves the Build-rule behaviour: agents share one state without losing each other's changes.
Part 3 runs the real Archus pipeline in Sample Mode and checks the lineage it leaves behind.

Run: python -m unittest discover -s tests -v
"""

from __future__ import annotations

import sys
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.world_model import (  # noqa: E402
    ConflictError,
    ProvenanceError,
    WorldModel,
    decide,
    entity_id_from_name,
    normalize_name,
)

OBSERVATIONS = [
    {"externalId": "a1", "title": "Fed holds rates", "at": "2026-05-17T14:00:00.000Z",
     "source": {"kind": "rss", "at": "2026-05-17T14:00:00.000Z"}, "entities": [{"type": "person", "name": "Jerome Powell"}]},
    {"externalId": "a2", "title": "Powell signals patience", "at": "2026-05-17T16:30:00.000Z",
     "source": {"kind": "rss", "at": "2026-05-17T16:30:00.000Z"}, "entities": [{"type": "person", "name": "Jerome Powell"}]},
]


def clock() -> datetime:
    return datetime(2026, 5, 18, tzinfo=timezone.utc)


def at(ts: str) -> dict:
    return {"kind": "manual", "at": ts}


class ConformanceTests(unittest.TestCase):
    """One test per check in the official World Model conformance runner."""

    def test_sid_001_diacritics_and_nbsp_normalize_identically(self):
        self.assertEqual(normalize_name("José  García"), normalize_name("Jose Garcia"))
        self.assertEqual(entity_id_from_name("person", "José García"), entity_id_from_name("person", "jose garcia"))

    def test_sid_002_distinct_names_stay_distinct(self):
        self.assertNotEqual(entity_id_from_name("org", "Acme Corp"), entity_id_from_name("org", "Acme Corporation"))
        self.assertNotEqual(entity_id_from_name("person", "x"), entity_id_from_name("org", "x"))

    def test_band_001_merge_bands_at_the_boundaries(self):
        self.assertEqual(decide(0.85), "auto-merge")
        self.assertEqual(decide(0.84), "review")
        self.assertEqual(decide(0.82), "review")
        self.assertEqual(decide(0.81), "new")

    def test_prov_001_writes_without_provenance_are_rejected(self):
        world = WorldModel(namespace="conf")
        with self.assertRaises(ProvenanceError):
            world.upsert_entity("person", name="No Provenance", source=None)

    def test_idem_001_same_batch_twice_produces_an_empty_diff(self):
        world = WorldModel(namespace="conf", clock=clock)
        world.ingest(OBSERVATIONS)
        shape1 = world.state_shape_canonical()
        second = world.ingest(OBSERVATIONS)
        self.assertFalse(second["changed"])
        self.assertEqual(world.state_shape_canonical(), shape1)

    def test_idem_002_a_mutated_batch_changes_the_shape(self):
        world = WorldModel(namespace="conf", clock=clock)
        world.ingest(OBSERVATIONS)
        shape1 = world.state_shape_canonical()
        mutated = [{**OBSERVATIONS[0], "title": OBSERVATIONS[0]["title"] + " (edited)"}, OBSERVATIONS[1]]
        run = world.ingest(mutated)
        self.assertTrue(run["changed"])
        self.assertNotEqual(world.state_shape_canonical(), shape1)

    def test_bitemp_001_superseding_edge_closes_the_old_one(self):
        world = WorldModel(namespace="conf")
        world.upsert_entity("player", external_key={"system": "g", "id": "p1"}, attrs={}, source=at("2087-01-01T00:00:00.000Z"))
        world.upsert_entity("team", external_key={"system": "g", "id": "a"}, attrs={}, source=at("2087-01-01T00:00:00.000Z"))
        world.upsert_entity("team", external_key={"system": "g", "id": "b"}, attrs={}, source=at("2088-03-01T00:00:00.000Z"))
        world.relate("player:g:p1", "plays-for", "team:g:a", valid_from="2087-01-01T00:00:00.000Z", source=at("2087-01-01T00:00:00.000Z"))
        world.relate("player:g:p1", "plays-for", "team:g:b", valid_from="2088-03-01T00:00:00.000Z", source=at("2088-03-01T00:00:00.000Z"))
        now = world.view("graph").neighbors_of("player:g:p1", via="plays-for")
        self.assertEqual([e["id"] for e in now], ["team:g:b"])
        then = world.view("graph").neighbors_of("player:g:p1", via="plays-for", at="2087-06-01T00:00:00.000Z")
        self.assertEqual([e["id"] for e in then], ["team:g:a"])

    def test_audit_001_every_mutation_writes_an_audit_entry_in_order(self):
        world = WorldModel(namespace="conf")
        world.upsert_entity("x", name="Audit One", source=at("2026-01-01T00:00:00.000Z"))
        world.upsert_entity("x", name="Audit Two", source=at("2026-01-02T00:00:00.000Z"))
        audit = world.audit()
        self.assertGreaterEqual(len(audit), 2)
        for prev, cur in zip(audit, audit[1:]):
            self.assertGreater(cur["seq"], prev["seq"])


class SharedStateTests(unittest.TestCase):
    """Two agents read and update a common state without losing one another's changes."""

    def test_concurrent_writers_on_one_claim_keep_both_sets_of_fields(self):
        world = WorldModel()
        key = {"system": "django_app/accounts", "id": "complexity_max"}
        world.upsert_entity("claim", external_key=key, attrs={"text": "seed"}, source=at("2026-01-01T00:00:00.000Z"))

        def analyst():
            for i in range(200):
                world.upsert_entity("claim", external_key=key, attrs={"expected_value": i},
                                    source={"kind": "AnalystAgent", "at": "2026-01-01T00:00:01.000Z"})

        def evaluator():
            for i in range(200):
                world.upsert_entity("claim", external_key=key, attrs={"actual_value": i, "verified": i % 2 == 0},
                                    source={"kind": "EvidenceEvaluatorAgent", "at": "2026-01-01T00:00:01.000Z"})

        threads = [threading.Thread(target=analyst), threading.Thread(target=evaluator)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        claim = world.get("claim:django_app/accounts:complexity_max")
        self.assertEqual(claim["attrs"]["text"], "seed")
        self.assertEqual(claim["attrs"]["expected_value"], 199)
        self.assertEqual(claim["attrs"]["actual_value"], 199)
        self.assertFalse(claim["attrs"]["verified"])
        self.assertEqual(claim["rev"], 1 + 200 + 200)  # every write landed, none was lost
        seqs = [a["seq"] for a in world.audit()]
        self.assertEqual(seqs, sorted(set(seqs)))

    def test_stale_writer_is_refused_instead_of_overwriting(self):
        world = WorldModel()
        key = {"system": "legacy_service/billing", "id": "coverage_estimate"}
        claim = world.upsert_entity("claim", external_key=key, attrs={"expected_value": 12.0},
                                    source={"kind": "AnalystAgent", "at": "2026-01-01T00:00:00.000Z"})
        read_rev = claim["rev"]  # the Evaluator reads the claim...
        world.upsert_entity("claim", external_key=key, attrs={"expected_value": 14.0},
                            source={"kind": "AnalystAgent", "at": "2026-01-01T00:00:01.000Z"})  # ...the Analyst revises it
        with self.assertRaises(ConflictError):
            world.upsert_entity("claim", external_key=key, attrs={"verified": True}, expected_rev=read_rev,
                                source={"kind": "EvidenceEvaluatorAgent", "at": "2026-01-01T00:00:02.000Z"})
        self.assertNotIn("verified", world.get(claim["id"])["attrs"])

    def test_state_survives_restart_by_replaying_the_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "world.db"
            world = WorldModel(db_path=db, clock=clock)
            world.ingest(OBSERVATIONS)
            world.relate("observation:rss:a1", "follows", "observation:rss:a2", source=at("2026-05-18T00:00:00.000Z"))
            shape, audit_len = world.state_shape_canonical(), len(world.audit())
            world.close()

            reopened = WorldModel(db_path=db, clock=clock)
            self.assertEqual(reopened.state_shape_canonical(), shape)
            self.assertEqual(len(reopened.audit()), audit_len)
            self.assertFalse(reopened.ingest(OBSERVATIONS)["changed"])
            reopened.close()


class ArchusIntegrationTests(unittest.TestCase):
    """The real 5-agent pipeline in Sample Mode, writing to an in-memory World Model."""

    @classmethod
    def setUpClass(cls):
        from app.orchestration.graph import OrchestrationGraph
        cls.world = WorldModel()
        cls.graph = OrchestrationGraph(force_sample_mode=True, world=cls.world)

    def test_every_evidence_item_links_to_its_claim_and_verifying_query(self):
        from app.world_state import run_lineage
        res = self.graph.execute_run("Should we refactor or maintain accounts?", "django_app", "accounts", True, "none")
        self.assertEqual(res.output.decision, "refactor")
        self.assertGreaterEqual(len(res.output.evidence), 3)
        for item in res.output.evidence:
            self.assertTrue(item.claim_id, item.claim)
            self.assertTrue(item.verified_by_query_id, item.claim)
            self.assertTrue(item.cited_query_ids, item.claim)
            claim = self.world.get(item.claim_id)
            self.assertEqual(claim["attrs"]["status"], "verified")
            self.assertEqual(str(claim["attrs"]["actual_value"]), str(item.value))
            verify_query = self.world.get(item.verified_by_query_id)
            self.assertEqual(verify_query["attrs"]["sql"], item.sql_query)

        lineage = run_lineage(self.world, res.run_id)
        self.assertEqual(lineage["decision"], "refactor")
        self.assertEqual(lineage["status"], "success")
        self.assertTrue(all(c["status"] == "verified" for c in lineage["claims"]))

    def test_claims_keep_stable_ids_across_runs(self):
        first = self.graph.execute_run("Should we migrate legacy billing?", "legacy_service", "billing", True, "none")
        second = self.graph.execute_run("Should we migrate legacy billing?", "legacy_service", "billing", True, "none")
        self.assertEqual(first.output.decision, "migrate")
        self.assertEqual(
            sorted(e.claim_id for e in first.output.evidence),
            sorted(e.claim_id for e in second.output.evidence),
        )
        # The verification history is kept: only the newest verified_by edge is open
        claim_id = first.output.evidence[0].claim_id
        open_edges = self.world.edges_of(claim_id, via="verified_by")
        self.assertEqual(len(open_edges), 1)
        self.assertEqual(open_edges[0]["props"]["run_id"], second.run_id)

    def test_abstention_is_recorded_without_verified_claims(self):
        from app.world_state import run_lineage
        res = self.graph.execute_run("Can we conclude on mystery module?", "sparse_repo", "unmeasured_module", True, "none")
        self.assertEqual(res.status, "insufficient_evidence")
        lineage = run_lineage(self.world, res.run_id)
        self.assertEqual(lineage["status"], "insufficient_evidence")
        self.assertFalse(any(c["status"] == "verified" for c in lineage["claims"]))


if __name__ == "__main__":
    unittest.main()
