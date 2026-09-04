# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""MCP tools: get_signal_index / get_system_signal_index

Thin, read-only accessors over the Shape-C signal indices — one per corpus, the
SAME engine. :func:`get_signal_index` returns the byte-reproducible view of every
structural signal in the COMPONENT corpus (``{signal_id, signal_text,
component_ids}``); :func:`get_system_signal_index` returns the same over the
DESIGN_SYSTEMS corpus (``{signal_id, signal_text, system_ids}``, S5).

The agent (LLM) recognises a problem's structural signals against the relevant view
in working memory, then passes the matched ``signal_id``s to the retrieval engine
(``loader.hydrate`` for components -> audit_design/spec_component;
``loader.hydrate_systems`` for design systems -> plan_design_system). These tools
only expose the index; they perform no matching themselves (matching is the LLM's
job / the frozen benchmark recognizer, never a fuzzy keyword pass in shipping code).
Both are ZERO-ARG — they reach no untrusted caller input, so the caller-boundary
ceilings (theia.tools._shared) do not apply to them.
"""

from __future__ import annotations

from theia.tools._shared import get_knowledge


def get_signal_index(conn: object = None) -> dict:
    """Return the deterministic component signal-index view.

    Args:
        conn: Optional Kuzu/LadybugDB connection. ``None`` -> JSON singleton
            loader; a connection -> the graph-backed loader (same engine, both
            modes).

    Returns:
        ``{"signals": [{signal_id, signal_text, component_ids}, ...], "count": N}``
        — sorted by ``signal_id`` with sorted ``component_ids`` so it serialises
        identically on every call.
    """
    kb = get_knowledge(conn)
    signals = kb.get_signal_index()
    return {"signals": signals, "count": len(signals)}


def get_system_signal_index(conn: object = None) -> dict:
    """Return the deterministic design_systems signal-index view.

    The design-system analogue of :func:`get_signal_index` (same engine, second
    corpus — no matching performed here). The agent recognises a product's
    structural signals against this view in working memory, then passes the matched
    ``signal_id``s to ``plan_design_system``, which hydrates the nearest existing
    system through ``loader.hydrate_systems`` and fans out over ``related_systems``.

    Args:
        conn: Optional Kuzu/LadybugDB connection. ``None`` -> JSON singleton
            loader; a connection -> the graph-backed loader.

    Returns:
        ``{"signals": [{signal_id, signal_text, system_ids}, ...], "count": N}`` —
        sorted by ``signal_id`` with sorted ``system_ids`` so it serialises
        identically on every call.
    """
    kb = get_knowledge(conn)
    signals = kb.get_system_signal_index()
    return {"signals": signals, "count": len(signals)}
