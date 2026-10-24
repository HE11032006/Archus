"""
World Model: Persistent, queryable shared state for the agents (Meterless World Model engine).
Implements the spec at github.com/Meterless/Meterless/tree/main/engines/world-model:
stable content-derived IDs, provenance on every write, append-only event log with
derived views rebuilt by replay, idempotent ingest, bitemporal edges and an ordered audit.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

SCHEMA_VERSION = 1

# Entity-resolution merge bands (spec boundary rulings: 0.85 exactly auto-merges, 0.82 exactly queues)
AUTO_MERGE_THRESHOLD = 0.85
REVIEW_THRESHOLD = 0.82


class ProvenanceError(ValueError):
    """Raised when a write carries no source. No provenance, no write."""


class ConflictError(RuntimeError):
    """Raised when a writer's expected revision no longer matches the stored entity."""


# ==========================================
# Stable IDs
# ==========================================

def normalize_name(name: str) -> str:
    """lowercase -> NFKD -> strip combining marks -> collapse whitespace -> trim"""
    text = unicodedata.normalize("NFKD", name.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text).strip()


def entity_id_from_name(entity_type: str, name: str) -> str:
    digest = hashlib.sha256(f"{entity_type}:{normalize_name(name)}".encode("utf-8")).hexdigest()
    return f"ent_{digest[:16]}"


def entity_id_from_key(entity_type: str, system: str, external_id: str) -> str:
    return f"{entity_type}:{system}:{external_id}"


def decide(similarity: float) -> str:
    """Merge banding for entity resolution."""
    if similarity >= AUTO_MERGE_THRESHOLD:
        return "auto-merge"
    if similarity >= REVIEW_THRESHOLD:
        return "review"
    return "new"


def _hash_id(prefix: str, *parts: Any) -> str:
    raw = "|".join("" if p is None else str(p) for p in parts)
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


# ==========================================
# Read surface
# ==========================================

class GraphView:
    def __init__(self, world: "WorldModel"):
        self.world = world

    def neighbors_of(
        self,
        entity_id: str,
        via: Optional[str] = None,
        at: Optional[str] = None,
        direction: str = "out",
    ) -> List[Dict[str, Any]]:
        """Entities linked to entity_id by edges valid now (or at the given instant)."""
        result = []
        for edge in self.world.edges_of(entity_id, via=via, at=at, direction=direction):
            other_id = edge["to"] if edge["from"] == entity_id else edge["from"]
            other = self.world.get(other_id)
            if other is not None:
                result.append(other)
        return result


# ==========================================
# Canonical store
# ==========================================

class WorldModel:
    def __init__(
        self,
        namespace: str = "archus",
        db_path: Optional[Path] = None,
        clock: Optional[Callable[[], datetime]] = None,
    ):
        self.namespace = namespace
        self.clock = clock or _default_clock
        self._lock = threading.RLock()
        self._entities: Dict[str, Dict[str, Any]] = {}
        self._edges: Dict[str, Dict[str, Any]] = {}
        self._audit: List[Dict[str, Any]] = []
        self._seq = 0
        self._db: Optional[sqlite3.Connection] = None

        if db_path is not None:
            db_path = Path(db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self._db = sqlite3.connect(str(db_path), check_same_thread=False)
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS events ("
                "seq INTEGER NOT NULL, namespace TEXT NOT NULL, op TEXT NOT NULL, "
                "record TEXT NOT NULL, recorded_at TEXT NOT NULL, PRIMARY KEY (namespace, seq))"
            )
            self._db.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            self._db.execute(
                "INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', ?)", (str(SCHEMA_VERSION),)
            )
            self._db.commit()
            self._replay()

    # ---------- persistence ----------

    def _replay(self) -> None:
        """Rebuild every derived view from the append-only log."""
        assert self._db is not None
        rows = self._db.execute(
            "SELECT seq, op, record FROM events WHERE namespace = ? ORDER BY seq", (self.namespace,)
        ).fetchall()
        for seq, op, record_json in rows:
            record = json.loads(record_json)
            self._apply(op, record)
            self._seq = seq

    def _apply(self, op: str, record: Dict[str, Any]) -> None:
        if op == "entity":
            self._entities[record["id"]] = record
        elif op == "edge":
            self._edges[record["id"]] = record
        self._audit.append({
            "seq": record["_seq"],
            "op": op,
            "id": record["id"],
            "actor": record["_source"]["kind"],
            "at": record["_recorded_at"],
        })

    def _append(self, op: str, record: Dict[str, Any], source: Dict[str, Any]) -> None:
        self._seq += 1
        record["_seq"] = self._seq
        record["_source"] = source
        record["_recorded_at"] = _iso(self.clock())
        if self._db is not None:
            self._db.execute(
                "INSERT INTO events (seq, namespace, op, record, recorded_at) VALUES (?, ?, ?, ?, ?)",
                (self._seq, self.namespace, op, json.dumps(record, default=str), record["_recorded_at"]),
            )
            self._db.commit()
        self._apply(op, record)

    @staticmethod
    def _check_source(source: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not source or not source.get("kind") or not source.get("at"):
            raise ProvenanceError("Every write needs a source with 'kind' and 'at'.")
        return dict(source)

    # ---------- writes ----------

    def upsert_entity(
        self,
        entity_type: str,
        *,
        source: Optional[Dict[str, Any]],
        name: Optional[str] = None,
        external_key: Optional[Dict[str, str]] = None,
        attrs: Optional[Dict[str, Any]] = None,
        expected_rev: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create or update an entity. Attributes merge field by field (latest wins per field),
        so two writers touching different fields never erase each other.
        Pass expected_rev to refuse the write if someone else changed the entity since you read it.
        """
        source = self._check_source(source)
        if external_key:
            entity_id = entity_id_from_key(entity_type, external_key["system"], str(external_key["id"]))
        elif name:
            entity_id = entity_id_from_name(entity_type, name)
        else:
            raise ValueError("An entity needs a name or an external_key.")

        with self._lock:
            current = self._entities.get(entity_id)
            current_rev = current["rev"] if current else 0
            if expected_rev is not None and expected_rev != current_rev:
                raise ConflictError(
                    f"{entity_id} is at rev {current_rev}, writer expected rev {expected_rev}."
                )

            merged_attrs = dict(current["attrs"]) if current else {}
            merged_attrs.update(attrs or {})
            if current and merged_attrs == current["attrs"] and (name is None or current.get("name") == name):
                return current  # idempotent: nothing changed, nothing written

            record = {
                "id": entity_id,
                "type": entity_type,
                "name": name if name is not None else (current or {}).get("name"),
                "attrs": merged_attrs,
                "rev": current_rev + 1,
                "first_seen_at": (current or {}).get("first_seen_at", source["at"]),
                "last_seen_at": source["at"],
            }
            self._append("entity", record, source)
            return record

    def relate(
        self,
        from_id: str,
        edge_type: str,
        to_id: str,
        *,
        source: Optional[Dict[str, Any]],
        valid_from: Optional[str] = None,
        props: Optional[Dict[str, Any]] = None,
        cardinality: str = "one",
    ) -> Dict[str, Any]:
        """
        Add a directed edge. With cardinality "one", a newer edge of the same type from the
        same entity supersedes the open one (its valid_to is closed), keeping history queryable.
        """
        source = self._check_source(source)
        valid_from = valid_from or source["at"]
        edge_id = _hash_id("edge", from_id, edge_type, to_id, valid_from)

        with self._lock:
            existing = self._edges.get(edge_id)
            if existing and existing["props"] == (props or {}):
                return existing  # same edge twice is a no-op

            if cardinality == "one":
                for edge in list(self._edges.values()):
                    if (
                        edge["from"] == from_id
                        and edge["type"] == edge_type
                        and edge["id"] != edge_id
                        and edge["valid_to"] is None
                        and _parse_ts(edge["valid_from"]) < _parse_ts(valid_from)
                    ):
                        closed = {k: v for k, v in edge.items() if not k.startswith("_")}
                        closed["valid_to"] = valid_from
                        self._append("edge", closed, source)

            record = {
                "id": edge_id,
                "from": from_id,
                "type": edge_type,
                "to": to_id,
                "props": props or {},
                "valid_from": valid_from,
                "valid_to": None,
            }
            self._append("edge", record, source)
            return record

    def ingest(self, observations: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Idempotent batch ingest. Each observation needs externalId/external_id, source and
        optional title, at and entities [{type, name}]. Re-running the same batch changes nothing.
        """
        with self._lock:
            seq_before = self._seq
            for obs in observations:
                source = self._check_source(obs.get("source"))
                external_id = obs.get("external_id") or obs.get("externalId")
                observation = self.upsert_entity(
                    "observation",
                    external_key={"system": source["kind"], "id": external_id},
                    attrs={"title": obs.get("title"), "at": obs.get("at")},
                    source=source,
                )
                for ref in obs.get("entities", []):
                    entity = self.upsert_entity(ref["type"], name=ref["name"], source=source)
                    self.relate(
                        observation["id"], "mentions", entity["id"],
                        source=source, valid_from=obs.get("at") or source["at"], cardinality="many",
                    )
            return {"changed": self._seq != seq_before, "events_written": self._seq - seq_before}

    # ---------- reads ----------

    def get(self, entity_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            entity = self._entities.get(entity_id)
            return dict(entity) if entity else None

    def entities(self, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(e) for e in self._entities.values() if entity_type is None or e["type"] == entity_type]

    def edges_of(
        self,
        entity_id: str,
        via: Optional[str] = None,
        at: Optional[str] = None,
        direction: str = "out",
    ) -> List[Dict[str, Any]]:
        moment = _parse_ts(at) if at else None
        with self._lock:
            result = []
            for edge in self._edges.values():
                if via and edge["type"] != via:
                    continue
                if direction == "out" and edge["from"] != entity_id:
                    continue
                if direction == "in" and edge["to"] != entity_id:
                    continue
                if direction == "both" and entity_id not in (edge["from"], edge["to"]):
                    continue
                if moment is None:
                    if edge["valid_to"] is not None:
                        continue
                else:
                    if _parse_ts(edge["valid_from"]) > moment:
                        continue
                    if edge["valid_to"] is not None and _parse_ts(edge["valid_to"]) <= moment:
                        continue
                result.append(dict(edge))
            return sorted(result, key=lambda e: e["_seq"])

    def view(self, name: str) -> GraphView:
        if name != "graph":
            raise ValueError(f"Unknown view '{name}'.")
        return GraphView(self)

    def audit(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._audit)

    def state_shape_canonical(self) -> str:
        """Deterministic serialization of world state, ignoring write timestamps and sequence numbers."""
        with self._lock:
            entities = sorted(
                ({"id": e["id"], "type": e["type"], "name": e["name"], "attrs": e["attrs"]} for e in self._entities.values()),
                key=lambda e: e["id"],
            )
            edges = sorted(
                ({k: v for k, v in e.items() if not k.startswith("_")} for e in self._edges.values()),
                key=lambda e: e["id"],
            )
            return json.dumps({"entities": entities, "edges": edges}, sort_keys=True, default=str)

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            by_type: Dict[str, int] = {}
            for e in self._entities.values():
                by_type[e["type"]] = by_type.get(e["type"], 0) + 1
            linked = {e["from"] for e in self._edges.values()} | {e["to"] for e in self._edges.values()}
            return {
                "namespace": self.namespace,
                "schema_version": SCHEMA_VERSION,
                "entities": len(self._entities),
                "entities_by_type": by_type,
                "edges": len(self._edges),
                "open_edges": sum(1 for e in self._edges.values() if e["valid_to"] is None),
                "audit_entries": len(self._audit),
                "orphans": sum(1 for eid in self._entities if eid not in linked),
                "persistent": self._db is not None,
            }

    def close(self) -> None:
        if self._db is not None:
            self._db.close()
            self._db = None
