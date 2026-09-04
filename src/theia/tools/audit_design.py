# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""MCP tool: audit_design — wired onto the Shape-C retrieval engine.

The FIRST Theia concern tool retrofitted onto the shared engine, following the
analyze_architecture template (council 3e6eeeab; f1b39fbd-decision-3). Given the
signal ids the caller (the LLM) recognised against ``get_signal_index`` plus an
optional constraints dict, it:

1. RETRIEVES candidate components through one ``kb.hydrate`` call — the proven
   four-state, fail-closed envelope; ``no_match``/``dangling`` abstain to empty
   issues with a populated envelope, never a husk. The legacy measured-empty
   output on real problem-language is dead: it is replaced by an honest
   abstention state, not a silent ``[]``.
2. GATES (dormant on this corpus) each retrieved component by the shared
   ``is_gated`` facet predicate. Theia components carry NO ``avoid_when`` facet
   dict (0/66), so the gate never fires here — it is the S4/S5-ready seam kept
   faithful to the sibling template, identity-ordered today (a comment must not
   claim a control the code does not have: this tier is dormant BY DATA, and the
   tests assert every ``gated`` flag is False).
3. REASONS one entry per retrieved component over that component's OWN
   100%-populated fields — ``common_mistakes`` (the design issues), ``anatomy`` +
   ``states`` (the structural context), and ``accessibility_requirements`` (the
   accessibility flags) — NOT a hardcoded table. This FIXES the legacy
   ``pattern.get('accessibility')`` field-name bug: the corpus field is
   ``accessibility_requirements`` (``component.get('accessibility')`` is ``None``
   on 66/66 components, so the legacy read emitted empty flags even on a match).
4. SURFACES the retrieval envelope (``retrieval_state`` / ``unmatched`` /
   ``dangling``) on the RESULT.

Firewall: imports theia.* only.
"""

from __future__ import annotations

from typing import Any

from theia.knowledge.loader import DANGLING, NO_MATCH, is_gated
from theia.tools._shared import (
    _MAX_DESCRIPTION_LEN,
    _MAX_MATCHED_SIGNALS,
    _MAX_RELATED_OUTPUT,
    _bounded_constraints,
    _resolved_related,
    coerce,
    emit_event,
    get_knowledge,
)

# ---------------------------------------------------------------------------
# Main tool
# ---------------------------------------------------------------------------

def audit_design(
    description: str,
    matched_signal_ids: list[str],
    constraints: dict | None = None,
    k: int = 10,
    conn: object = None,
) -> dict:
    """Audit a design: name each retrieved component's issues from its own fields.

    Args:
        description: Free-text description of the interface — context/telemetry
            only (retrieval is driven by ``matched_signal_ids``, not this text).
            Bounded at the caller boundary.
        matched_signal_ids: Signal ids the caller recognised against
            ``get_signal_index`` (problem-language -> sig-id, the proven path).
            The prose ``structural_signals`` param is RETIRED (no alias shim).
        constraints: Optional dict (e.g. ``{"platform": "mobile"}``). Drives the
            dormant facet gate; sanitised at the caller boundary.
        k: Number of retrieved components to reason over (engine-clamped to 1..50).
        conn: Kuzu/LadybugDB connection for graph mode, or None for JSON.

    Returns:
        Dict with ``constraints_analyzed`` / ``design_issues`` (one entry per
        retrieved component, reasoning over its own common_mistakes + anatomy +
        states) / ``recommendations`` (deduped related-component remediation) /
        ``accessibility_flags`` (each component's own accessibility_requirements —
        the populated accessibility field) plus the retrieval envelope
        (``retrieval_state`` / ``unmatched`` / ``dangling``). Fail-closed: an
        abstaining envelope returns empty issues, never a husk.
    """
    description = description[:_MAX_DESCRIPTION_LEN] if isinstance(description, str) else ""
    matched_signal_ids = coerce(matched_signal_ids, list) or []
    constraints = _bounded_constraints(coerce(constraints, dict) or {})
    try:
        k = int(k)
    except (TypeError, ValueError):
        k = 10

    kb = get_knowledge(conn)

    # 1. RETRIEVE — one hydrate call; the caller-boundary cap is non-amplifying
    #    (the engine's own _SEED_CAP bounds fan-out downstream of it).
    res = kb.hydrate(matched_signal_ids[:_MAX_MATCHED_SIGNALS], k=k)

    envelope = {
        "retrieval_state": res.state,
        "unmatched": list(res.unmatched_signals),
        "dangling": list(res.dangling),
    }

    # 2. Fail closed: recognised-but-empty (no_match) or unresolvable (dangling)
    #    abstains structurally — no issues, never the nearest husk.
    if res.state in (NO_MATCH, DANGLING):
        result = {
            "constraints_analyzed": constraints,
            "design_issues": [],
            "recommendations": [],
            "accessibility_flags": [],
            **envelope,
        }
        emit_event("audit_design", {
            "description": description[:120],
            "n_signals": len(matched_signal_ids),
            "state": res.state,
            "design_issues_count": 0,
            "accessibility_flags_count": 0,
        })
        return result

    # 3. GATE (dormant) — the shared facet gate would demote a component the
    #    constraints say to AVOID (its own avoid_when facet). No Theia component
    #    carries an avoid_when facet dict, so nothing gates here; the tier is the
    #    S4/S5-ready seam, identity-ordered today. Total-order key (gated, rank)
    #    so a future gated component sinks deterministically without relying on
    #    sort stability.
    gated_flags = [is_gated(c, constraints) for c in res.patterns]
    order = sorted(range(len(res.patterns)), key=lambda i: (gated_flags[i], i))
    ordered = [res.patterns[i] for i in order]
    ordered_gated = [gated_flags[i] for i in order]

    # 4. REASON — one entry per retrieved component over its OWN fields:
    #    common_mistakes/anatomy/states = the design issue; accessibility_requirements
    #    = the accessibility flag (the field-name bug fix).
    design_issues: list[dict[str, Any]] = []
    accessibility_flags: list[dict[str, Any]] = []
    issue_component_ids: set[str] = set()
    for c, gated in zip(ordered, ordered_gated):
        cid = c["id"]
        issue_component_ids.add(cid)
        design_issues.append({
            "component_id": cid,
            "component_name": c.get("name", cid),
            "gated": gated,
            "common_mistakes": list(c.get("common_mistakes", [])),
            "anatomy": list(c.get("anatomy", [])),
            "states": list(c.get("states", [])),
            "retrieval": dict(c["retrieval"]),   # plain dict for the output surface
        })
        reqs = list(c.get("accessibility_requirements", []))
        if reqs:
            accessibility_flags.append({
                "component_id": cid,
                "component_name": c.get("name", cid),
                "requirements": reqs,
            })

    # 5. RECOMMENDATIONS — the deduped remediation set across the issue-components'
    #    OWN related_patterns, excluding what is already an issue component. One
    #    source of truth (_resolved_related).
    recommendations: list[dict[str, Any]] = []
    seen_recs: set[str] = set()
    for c in ordered:
        for rec in _resolved_related(kb, c):
            rid = rec["pattern_id"]
            if rid in issue_component_ids or rid in seen_recs:
                continue
            seen_recs.add(rid)
            recommendations.append(rec)
            if len(recommendations) >= _MAX_RELATED_OUTPUT:
                break
        if len(recommendations) >= _MAX_RELATED_OUTPUT:
            break

    result = {
        "constraints_analyzed": constraints,
        "design_issues": design_issues,
        "recommendations": recommendations,
        "accessibility_flags": accessibility_flags,
        **envelope,
    }

    emit_event("audit_design", {
        "description": description[:120],
        "n_signals": len(matched_signal_ids),
        "state": res.state,
        "design_issues_count": len(design_issues),
        "accessibility_flags_count": len(accessibility_flags),
    })

    return result
