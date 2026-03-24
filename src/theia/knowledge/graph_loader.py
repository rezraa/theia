# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""Graph-backed knowledge loader for Theia.

Wraps the JSON-based KnowledgeLoader (data stays in JSON for speed) and adds
write_memory() for persisting design decisions to the Kuzu graph.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from theia.knowledge.loader import KnowledgeLoader


class GraphKnowledgeLoader(KnowledgeLoader):
    """KnowledgeLoader backed by a Kuzu/LadybugDB connection.

    Read path: delegates to the parent JSON-based KnowledgeLoader (the
    knowledge JSON files are the source of truth for design systems,
    component patterns, accessibility standards, and decision rules).

    Write path: ``write_memory()`` persists records as Memory nodes in the
    Kuzu graph so they can be queried by Othrys and other Titans.
    """

    def __init__(self, conn: Any) -> None:
        super().__init__()
        self._conn = conn
        self._ensure_schema()

    # ------------------------------------------------------------------
    # Schema bootstrap
    # ------------------------------------------------------------------

    def _ensure_schema(self) -> None:
        """Create the Memory node table if it does not already exist."""
        try:
            self._conn.execute(
                "CREATE NODE TABLE IF NOT EXISTS Memory("
                "id STRING, "
                "memory_type STRING, "
                "data STRING, "
                "created_at STRING, "
                "PRIMARY KEY (id))"
            )
        except Exception:
            pass  # table may already exist or conn may not support DDL

    # ------------------------------------------------------------------
    # Write path
    # ------------------------------------------------------------------

    def write_memory(
        self,
        memory_type: str,
        data: dict[str, Any],
    ) -> str:
        """Write a memory record to the Kuzu graph.

        Args:
            memory_type: Category of memory, e.g. "design_decision".
            data: Arbitrary dict payload to persist.

        Returns:
            The generated memory ID (``m-<hash>``).
        """
        ts = datetime.now(timezone.utc).isoformat()
        data_with_ts = {**data, "timestamp": ts}
        raw = json.dumps(data_with_ts, sort_keys=True)
        memory_id = "m-" + hashlib.sha256(raw.encode()).hexdigest()[:12]

        data_str = json.dumps(data_with_ts)

        self._conn.execute(
            "CREATE (m:memories {"
            "  id: $id,"
            "  memory_type: $memory_type,"
            "  content: $content,"
            "  agent: $agent,"
            "  timestamp: $ts,"
            "  status: $status,"
            "  outcome: $outcome,"
            "  project: $project,"
            "  confidence: $confidence"
            "})",
            parameters={
                "id": memory_id,
                "memory_type": memory_type,
                "content": data_str,
                "agent": "theia",
                "ts": ts,
                "status": "open",
                "outcome": "unknown",
                "project": "",
                "confidence": 0.8,
            },
        )

        return memory_id
