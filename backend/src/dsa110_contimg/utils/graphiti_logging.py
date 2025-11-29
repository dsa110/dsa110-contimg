from __future__ import annotations

import json
import os
from contextlib import AbstractContextManager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _events_path() -> Path:
    # Default inside repo state directory unless overridden
    path = os.getenv(
        "GRAPHITI_EVENTS_FILE",
        "/data/dsa110-contimg/state/graphiti_events.jsonl",
    )
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


class GraphitiRunLogger(AbstractContextManager["GraphitiRunLogger"]):
    """Minimal, dependency-free logger for Graphiti run lineage events.

    Writes JSONL events that can be imported into Neo4j via a separate step.

    Events:
      - run_start {run, group_id, ts}
      - consumes  {run, dataset, ts}
      - produces  {run, product, ts}
      - run_finish{run, status, error?, ts}
    """

    def __init__(self, run_name: str, *, group_id: Optional[str] = None) -> None:
        self.run = run_name
        self.group_id = group_id or os.getenv("GRAPHITI_GROUP_ID", "dsa110-contimg")
        self.file = _events_path()
        self._opened = False

    def _append(self, rec: dict) -> None:
        rec.setdefault("run", self.run)
        rec.setdefault("group_id", self.group_id)
        rec.setdefault("ts", _now_iso())
        line = json.dumps(rec, ensure_ascii=False)
        with self.file.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def __enter__(self) -> "GraphitiRunLogger":
        self._append({"type": "run_start"})
        self._opened = True
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        status = "ok" if exc is None else "error"
        rec = {"type": "run_finish", "status": status}
        if exc is not None:
            rec["error"] = str(exc)
        self._append(rec)
        # Do not suppress exceptions
        return False

    # API
    def log_consumes(self, dataset: str) -> None:
        self._append({"type": "consumes", "dataset": dataset})

    def log_produces(self, product: str) -> None:
        self._append({"type": "produces", "product": product})
