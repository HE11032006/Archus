"""
Tracing module: Emits real-time JSONL traces to stdout and to logs/run_{run_id}.jsonl.
Provides full auditable evidence of agent collaboration and critique loops.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .config import settings


class Tracer:
    def __init__(self, run_id: str, trace_id: str):
        self.run_id = run_id
        self.trace_id = trace_id
        self.log_file_path = settings.logs_dir / f"run_{run_id}.jsonl"
        self._ensure_log_dir()

    def _ensure_log_dir(self) -> None:
        try:
            settings.logs_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def log(
        self,
        agent: str,
        event: str,
        status: str = "ok",
        payload: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Record and emit a structured event trace immediately.
        """
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": self.run_id,
            "trace_id": self.trace_id,
            "agent": agent,
            "event": event,
            "status": status,
            "payload": payload or {},
        }
        if duration_ms is not None:
            record["duration_ms"] = round(duration_ms, 2)

        line = json.dumps(record, ensure_ascii=False)

        # Print to stdout for real-time visibility
        print(f"[TRACE] {line}", file=sys.stdout, flush=True)

        # Append to run log file
        try:
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception as e:
            print(f"[WARN] Failed to write trace to file: {e}", file=sys.stderr)

        return record
