# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""MCP tool: get_signal_index

ONE read-only accessor over BOTH Shape-C signal indices, returning a NESTED typed
view — ``{component_signals: [{signal_id, signal_text, component_ids}],
system_signals: [{signal_id, signal_text, system_ids}]}`` — composed from the two
loader views (``kb.get_signal_index()`` over the 66 components and
``kb.get_system_signal_index()`` over the 54 design systems), the SAME engine, one
corpus per surface.

The agent (LLM) recognises a problem's structural signals against the relevant
labelled surface in working memory — ``component_signals`` for audit_design /
spec_component, ``system_signals`` for plan_design_system — then passes the matched
``signal_id``s to the retrieval engine (``loader.hydrate`` for components,
``loader.hydrate_systems`` for design systems). This tool only exposes the two
views; it performs no matching itself (matching is the LLM's job / the frozen
benchmark recognizer, never a fuzzy keyword pass in shipping code). Zero-arg — it
reaches no untrusted caller input, so the caller-boundary ceilings
(theia.tools._shared) do not apply to it.

WHY exactly ONE public top-level function (the reachability fix, council ae492280 /
m-5a5837da; root cause m-698d738c): Othrys' filename-keyed seed mints one graph tool
per file keyed by the file stem, so two co-located public functions collapse to a
single tool identity and the second is silently dropped — the system accessor had no
graph identity and every live summon raised LookupError. A single public function
makes that drop impossible by construction.

WHY nested (not a flat per-entry type tag): the id columns (``component_ids`` /
``system_ids``) already encode a signal's corpus, so nesting keeps that typing
without a redundant tag; it also avoids a cross-corpus ``signal_id`` collision were
two signal texts ever to coincide (each surface is a separate map), and the agent
still recognises against two clearly labelled surfaces. Routing stays unambiguous
with no new code: the id-spaces are disjoint, so a mis-typed id misses in the wrong
corpus and the downstream hydrate abstains via NO_MATCH + unmatched_signals, never a
silent custom.
"""

from __future__ import annotations

from theia.tools._shared import get_knowledge


def get_signal_index(conn: object = None) -> dict:
    """Return both deterministic signal-index views in ONE nested composite.

    Args:
        conn: Optional Kuzu/LadybugDB connection. ``None`` -> JSON singleton
            loader; a connection -> the graph-backed loader (same engine, both
            modes and both corpora).

    Returns:
        ``{"component_signals": [{signal_id, signal_text, component_ids}, ...],
           "system_signals": [{signal_id, signal_text, system_ids}, ...]}`` — each
        view sorted by ``signal_id`` with sorted id-lists (``component_ids`` /
        ``system_ids``), so the composite serialises identically on every call.
    """
    kb = get_knowledge(conn)
    return {
        "component_signals": kb.get_signal_index(),
        "system_signals": kb.get_system_signal_index(),
    }
