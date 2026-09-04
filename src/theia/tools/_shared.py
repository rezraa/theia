# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""Shared state and utilities for all Theia tools.

Every tool module imports from here to get access to the singleton
KnowledgeLoader and dual-mode support (standalone JSON vs Othrys graph).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from theia.knowledge.loader import KnowledgeLoader

# ---------------------------------------------------------------------------
# Singletons — shared across all tool modules
# ---------------------------------------------------------------------------

_knowledge: KnowledgeLoader | None = None


def get_knowledge(conn: Any = None) -> KnowledgeLoader:
    """Return the appropriate knowledge loader for the current mode.

    Args:
        conn: If provided, returns a GraphKnowledgeLoader backed by this
              Kuzu/LadybugDB connection.  If None, returns the JSON singleton.
    """
    if conn is not None:
        from theia.knowledge.graph_loader import GraphKnowledgeLoader
        return GraphKnowledgeLoader(conn)
    global _knowledge
    if _knowledge is None:
        _knowledge = KnowledgeLoader()
    return _knowledge


# ---------------------------------------------------------------------------
# Caller-boundary ceilings — one source of truth, shared by every Shape-C tool
# ---------------------------------------------------------------------------
# The retrieval engine bounds its own fan-out (_SEED_CAP/_TOPK_CAP in
# theia.knowledge.loader); these bound the UNTRUSTED caller input BEFORE that
# engine is reached, applied where the cost is incurred. Declared once here so a
# second Shape-C tool cannot drift a second copy. Mirror of the shipped
# coeus.tools._shared ceilings (kept faithful by the firewall drift test).
#
# ENFORCEMENT is forward-staged to S3-S5, where the concern tools pass
# caller-supplied signal ids / constraints into ``hydrate``. The only Shape-C tool
# wired at S1 — ``get_signal_index`` — is ZERO-ARG and reaches no caller input, so
# nothing consumes these yet; they are the named ceiling the S3-S5 wiring binds to
# (council 3e6eeeab, explicit S1 scope: land the constants, stage the enforcement).
_MAX_MATCHED_SIGNALS = 256       # cap on caller-supplied signal ids, bound BEFORE hydrate
_MAX_CONSTRAINTS = 64            # cap on constraint-dict cardinality
_MAX_CONSTRAINT_VALUE_LEN = 256  # cap on each constraint value used in comparison
_MAX_DESCRIPTION_LEN = 4096      # cap on free-text description (context/telemetry only)


def _bounded_constraints(constraints: dict) -> dict:
    """Bound an untrusted constraints dict at the caller boundary.

    Keeps at most ``_MAX_CONSTRAINTS`` entries and clips each string value to
    ``_MAX_CONSTRAINT_VALUE_LEN`` characters so an unbounded dict cannot amplify
    the per-facet comparison cost. Pure sanitisation — never interpretation.
    Mirror of the shipped coeus.tools._shared helper (firewall: theia.* only).
    """
    bounded: dict[str, Any] = {}
    for key, val in list(constraints.items())[:_MAX_CONSTRAINTS]:
        bounded[key] = val[:_MAX_CONSTRAINT_VALUE_LEN] if isinstance(val, str) else val
    return bounded


# ---------------------------------------------------------------------------
# Shared output primitive — the derived related-pattern surface. Every concern
# tool re-sources each retrieved component's OWN ``related_patterns`` (the
# remediation / alternatives surface); one resolver and one cap live here so a
# second concern tool (S4/S5) cannot drift a second copy. Mirror of the shipped
# coeus.tools._shared helper, adapted to Theia's public loader accessor
# (``get_component_pattern`` — Theia's flat id->component index).
# ---------------------------------------------------------------------------
_MAX_RELATED_OUTPUT = 50   # cap on the deduped related-pattern cross-product a tool
                           # derives across its k retrieved components (output size, not
                           # a relevance score — corpus fan-out over k components)


def _resolved_edge(
    getter: Callable[[str], dict | None], node: dict, edge_field: str
) -> list[dict[str, Any]]:
    """Resolve a node's edge-list field to ``[{"id", "name"}, ...]``, in corpus order.

    The single edge-resolution core, shared across corpora: each id in
    ``node[edge_field]`` is resolved via *getter* — the corpus accessor
    (``get_component_pattern`` for the component index's ``related_patterns``,
    ``get_design_system`` for the design_systems index's ``related_systems``). A
    truly-absent id is skipped (it is already surfaced in the retrieval envelope's
    ``dangling`` field), never a husk. Every per-corpus related surface is a thin
    adapter over this ONE function, so a second corpus's fan-out is not a drifted
    second copy — one source of truth per concept (DRY doctrine, binding).
    """
    out: list[dict[str, Any]] = []
    for rid in node.get(edge_field, []):
        resolved = getter(rid)
        if resolved is None:
            continue
        out.append({"id": resolved["id"], "name": resolved.get("name", rid)})
    return out


def _resolved_related(kb: Any, component: dict) -> list[dict[str, Any]]:
    """Resolve a component's OWN ``related_patterns`` into ``{pattern_id, pattern_name}``.

    Thin adapter over :func:`_resolved_edge` (the shared edge-resolution core), naming
    the component-surface keys. The single shared resolver for the related-component
    surface every concern tool derives from a retrieved component's own field — one
    source of truth, not one copy per tool.
    """
    return [
        {"pattern_id": e["id"], "pattern_name": e["name"]}
        for e in _resolved_edge(kb.get_component_pattern, component, "related_patterns")
    ]


# ---------------------------------------------------------------------------
# Unmatched signal logging — seeds future knowledge base entries
# ---------------------------------------------------------------------------

def log_unmatched_signals(
    signals: list[str],
    tool_name: str,
    titan: str = "theia",
) -> None:
    """Append unmatched structural signals to ~/.othrys/unmatched_signals.jsonl."""
    from pathlib import Path
    log_path = Path.home() / ".othrys" / "unmatched_signals.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = json.dumps({
        "titan": titan,
        "tool": tool_name,
        "signals": signals,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    with open(log_path, "a") as f:
        f.write(entry + "\n")


# ---------------------------------------------------------------------------
# Data directory — local storage for standalone mode
# ---------------------------------------------------------------------------

def _data_dir() -> Path:
    """Return the path to the Theia data directory."""
    env = os.environ.get("THEIA_DATA_DIR")
    base = Path(env) if env else Path.home() / ".theia" / "data"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _decisions_file() -> Path:
    """Return the path to the local decisions JSONL file."""
    return _data_dir() / "decisions.jsonl"


def _events_file() -> Path:
    """Return the path to the shared events JSONL file."""
    return _data_dir() / "events.jsonl"


# ---------------------------------------------------------------------------
# Decision log — local JSONL for standalone mode
# ---------------------------------------------------------------------------

def append_decision(record: dict[str, Any]) -> str:
    """Append a design decision record to the local JSONL log.

    Returns the decision_id.
    """
    import hashlib

    ts = datetime.now(timezone.utc).isoformat()
    record["timestamp"] = ts
    raw = json.dumps(record, sort_keys=True)
    decision_id = "d-" + hashlib.sha256(raw.encode()).hexdigest()[:12]
    record["decision_id"] = decision_id

    df = _decisions_file()
    df.parent.mkdir(parents=True, exist_ok=True)
    with open(df, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    return decision_id


# ---------------------------------------------------------------------------
# Event system — file-based for cross-process dashboard communication
# ---------------------------------------------------------------------------

_event_listeners: list[Callable[[str, dict], None]] = []


def on_event(callback: Callable[[str, dict], None]) -> None:
    """Register a callback that receives (event_name, payload) on every emit."""
    _event_listeners.append(callback)


def emit_event(event_name: str, payload: dict[str, Any]) -> None:
    """Fire an event to all registered listeners and append to events file.

    The events file (events.jsonl) is the cross-process bridge between the
    MCP server (which emits events) and the dashboard (which reads them).
    """
    for cb in _event_listeners:
        try:
            cb(event_name, payload)
        except Exception:
            pass

    try:
        event = {
            "type": event_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        ef = _events_file()
        ef.parent.mkdir(parents=True, exist_ok=True)
        with open(ef, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except Exception:
        pass  # best-effort — never break tool execution


# ---------------------------------------------------------------------------
# Coercion utility — MCP clients sometimes send JSON as strings
# ---------------------------------------------------------------------------

def coerce(val: Any, expected_type: type | None = None, default: Any = None) -> Any:
    """Coerce MCP-supplied values to a native type, else return *default*.

    MCP clients sometimes send JSON containers as strings. This decodes a
    str into the expected list/dict when possible. On any irreconcilable
    type mismatch the *default* is returned, so callers never receive a
    truthy wrong-type value that survives ``coerce(...) or {}`` and crashes
    a later ``.get()``.
    """
    if val is None:
        return default
    if isinstance(val, str) and expected_type in (list, dict):
        try:
            parsed = json.loads(val)
        except (ValueError, TypeError):
            return default
        return parsed if isinstance(parsed, expected_type) else default
    if expected_type is not None and not isinstance(val, expected_type):
        return default
    return val


def coerce_or_raise(
    val: Any, expected_type: type, empty_default: Any
) -> Any:
    """Like :func:`coerce`, but for values that get PERSISTED.

    ``coerce`` returns its default on any irreconcilable mismatch, which is
    correct for transient/optional fields but dangerous for a field that is
    then written to storage: a non-empty wrong-type value (e.g. a list where
    a dict is expected) would be silently replaced by an empty default and
    persisted, dropping caller data without a sound.

    This stricter variant:
      - ``None`` -> ``empty_default`` (the caller supplied nothing).
      - a value already of ``expected_type`` -> used as-is.
      - a ``str`` that JSON-decodes to ``expected_type`` -> the decoded value.
      - anything else (a non-None wrong-type that cannot be coerced) ->
        ``TypeError``. We refuse to silently persist an empty default in
        place of meaningful but mistyped data.
    """
    if val is None:
        return empty_default
    if isinstance(val, expected_type):
        return val
    if isinstance(val, str) and expected_type in (list, dict):
        try:
            parsed = json.loads(val)
        except (ValueError, TypeError):
            parsed = None
        if isinstance(parsed, expected_type):
            return parsed
    raise TypeError(
        f"expected {expected_type.__name__} "
        f"(or JSON {expected_type.__name__} string); got {type(val).__name__}"
    )
