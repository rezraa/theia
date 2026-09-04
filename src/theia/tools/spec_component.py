# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""MCP tool: spec_component — wired onto the Shape-C retrieval engine (SEED-FROM-NODE).

The SECOND Theia concern tool retrofitted onto the shared engine (audit_design is the
S3 sibling; council 3e6eeeab). Where audit_design drives recognize-then-retrieve from
caller-supplied signal ids, spec_component SEEDS retrieval from a resolved component's
OWN signals (the suggest_refactor precedent, m-10b6fbf1 / 7cd08a1f-decision-0):

1. RESOLVE ``component_type`` -> a known corpus id (exact, then hyphen<->underscore
   normalisation). On a hit, SEED retrieval from that component's OWN signals —
   ``kb.signal_ids_for(id)`` -> ONE ``kb.hydrate`` whose one-hop fan-out expands over
   the component's ``related_patterns`` edge (S2). The seed always outranks its
   propagated-only neighbours (the engine's direct-vote tier), so the resolved
   component is the spec's primary.
2. On a NON-resolving type (e.g. 'parking-space-tile') accept an OPTIONAL
   ``matched_signal_ids`` so the agent drives recognize-then-retrieve against
   ``get_signal_index`` -> nearest component(s), flagged ``nearest`` on the result.
   Caller-supplied ids are bounded at the shared ``_MAX_MATCHED_SIGNALS`` ceiling
   BEFORE hydrate; seed ids on the resolved path are derived internally (no caller
   attack surface).
3. On no_match/dangling (neither a known id nor recognised signals) FAIL LOUD: an
   empty spec + the retrieval envelope, NEVER the ['container','content'] husk.
4. RETURN the primary component's OWN corpus fields — anatomy, states, variants
   (``variants_needed`` filters the component's OWN variants, not a husk append),
   accessibility_requirements, common_mistakes, responsive_behavior,
   design_tokens_needed — plus the deduped related-component surface and the retrieval
   envelope (``retrieval_state``/``from_knowledge_base``/``unmatched``/``dangling``) on
   the RESULT (370e7443-decision-6).

Every field is READ from the resolved component's corpus record — the accessibility
surface is that component's own ``accessibility_requirements`` list, and states /
responsive_behavior / design_tokens_needed are its own corpus fields — so a spec is
exactly the component's recorded design, never a computed or hardcoded stand-in.

Firewall: imports theia.* only.
"""

from __future__ import annotations

from typing import Any

from theia.knowledge.loader import DANGLING, NO_MATCH
from theia.tools._shared import (
    _MAX_DESCRIPTION_LEN,
    _MAX_MATCHED_SIGNALS,
    _MAX_RELATED_OUTPUT,
    _resolved_related,
    coerce,
    emit_event,
    get_knowledge,
)

# The output keys carried by both the populated spec and the fail-closed abstention,
# so a caller sees one stable shape whatever the retrieval state (one source of truth
# for the empty spec, never a husk).
_SPEC_FIELDS: tuple[str, ...] = (
    "anatomy",
    "states",
    "variants",
    "accessibility_requirements",
    "common_mistakes",
    "responsive_behavior",
    "design_tokens_needed",
)


def _resolve_component_id(kb: Any, component_type: str) -> str | None:
    """Resolve a caller ``component_type`` to a known corpus id, else ``None``.

    Exact id first, then the hyphen<->underscore normalisation the legacy tool used
    (``data-table`` <-> ``data_table``). Returns the component's own ``id`` (never the
    caller string), so the seed is always a real corpus node.
    """
    cl = component_type.lower().strip()
    for cand in (cl, cl.replace("-", "_"), cl.replace("_", "-")):
        node = kb.get_component_pattern(cand)
        if node is not None:
            return node["id"]
    return None


def _empty_spec(component_type: str, envelope: dict, *, nearest: bool) -> dict:
    """The fail-closed spec: the component echo + the envelope, every field empty.

    The single abstention shape (no_match/dangling) — a populated envelope stating
    WHY, never the ['container','content'] husk that narrated a miss as an answer.
    """
    result: dict[str, Any] = {
        "component": component_type,
        "component_id": None,
        "component_name": "",
        "description": "",
        "related_components": [],
        "from_knowledge_base": False,
        "nearest": nearest,
        **{field: [] for field in _SPEC_FIELDS},
        **envelope,
    }
    return result


def spec_component(
    component_type: str,
    context: str = "",
    variants_needed: list[str] | None = None,
    matched_signal_ids: list[str] | None = None,
    conn: object = None,
) -> dict:
    """Generate a component specification from the component's OWN corpus fields.

    Args:
        component_type: The component to spec, e.g. "navbar", "modal", "data-table".
            Resolved to a corpus id (exact + hyphen/underscore normalisation).
        context: Optional usage context — context/telemetry only (bounded at the
            caller boundary, never surfaced), mirroring audit_design's description.
        variants_needed: Optional variant names to keep; filters the component's OWN
            variants (a filter, never a husk append). None -> all own variants.
        matched_signal_ids: OPTIONAL signal ids the caller recognised against
            ``get_signal_index`` — used ONLY when ``component_type`` does not resolve,
            to retrieve the nearest component(s) (flagged ``nearest``). Bounded at the
            caller boundary. Ignored on a resolving type (the seed is derived
            internally from the resolved component's own signals).
        conn: Kuzu/LadybugDB connection for graph mode, or None for JSON.

    Returns:
        Dict with the component echo (``component``/``component_id``/``component_name``/
        ``description``), the primary component's OWN fields (``anatomy``/``states``/
        ``variants``/``accessibility_requirements``/``common_mistakes``/
        ``responsive_behavior``/``design_tokens_needed``), the deduped
        ``related_components`` fan-out, and the retrieval envelope
        (``from_knowledge_base``/``nearest``/``retrieval_state``/``unmatched``/
        ``dangling``). Fail-closed: a true miss returns the empty spec + envelope,
        never a husk.
    """
    context = context[:_MAX_DESCRIPTION_LEN] if isinstance(context, str) else ""
    variants_needed = coerce(variants_needed, list) or []
    matched_signal_ids = coerce(matched_signal_ids, list) or []

    kb = get_knowledge(conn)

    # 1. Resolve the component_type to a known corpus id (exact + normalisation).
    resolved_id = _resolve_component_id(kb, component_type)

    # 2. Seed selection. Resolved -> seed from the component's OWN signals (derived
    #    internally, no caller attack surface). Non-resolving -> the caller's
    #    recognised signal ids, bounded at the shared ceiling BEFORE hydrate; that
    #    path is the NEAREST match, flagged as such on the result.
    if resolved_id is not None:
        seed_ids = kb.signal_ids_for(resolved_id)
        nearest = False
    else:
        seed_ids = matched_signal_ids[:_MAX_MATCHED_SIGNALS]
        nearest = bool(seed_ids)

    # 3. Retrieve through ONE hydrate call (the proven four-state fail-closed envelope).
    res = kb.hydrate(seed_ids)
    envelope = {
        "retrieval_state": res.state,
        "unmatched": list(res.unmatched_signals),
        "dangling": list(res.dangling),
    }

    # 4. Fail LOUD on a true miss — empty spec + retrieval_state, NEVER the husk.
    #    (no seed at all -> NO_MATCH from an empty hydrate; recognised-but-empty ->
    #    NO_MATCH; ids resolving only to absent nodes -> DANGLING.)
    if res.state in (NO_MATCH, DANGLING) or not res.patterns:
        result = _empty_spec(component_type, envelope, nearest=nearest)
        emit_event("spec_component", {
            "component_type": component_type,
            "from_knowledge_base": False,
            "retrieval_state": res.state,
            "nearest": nearest,
            "variants_count": 0,
            "context": context[:120],
        })
        return result

    # 5. Primary = the resolved seed (located by id; it outranks its propagated-only
    #    neighbours by the engine's direct-vote tier) or, on the nearest path, the
    #    top-ranked hydrated component.
    if resolved_id is not None:
        primary = next((p for p in res.patterns if p["id"] == resolved_id), res.patterns[0])
    else:
        primary = res.patterns[0]

    # 6. Filter the primary's OWN variants by variants_needed — a filter over its own
    #    {name, when_to_use} variants, never a husk append of unknown names.
    own_variants = [dict(v) for v in primary.get("variants", [])]
    if variants_needed:
        wanted = {str(v).strip().lower() for v in variants_needed}
        variants = [v for v in own_variants if str(v.get("name", "")).strip().lower() in wanted]
    else:
        variants = own_variants

    # 7. Build the spec from the primary's OWN corpus fields + the deduped related-
    #    component fan-out (the shared _resolved_related primitive), surfacing the
    #    envelope + from_knowledge_base on the RESULT.
    result = {
        "component": component_type,
        "component_id": primary["id"],
        "component_name": primary.get("name", primary["id"]),
        "description": primary.get("description", ""),
        "anatomy": list(primary.get("anatomy", [])),
        "states": list(primary.get("states", [])),
        "variants": variants,
        "accessibility_requirements": list(primary.get("accessibility_requirements", [])),
        "common_mistakes": list(primary.get("common_mistakes", [])),
        "responsive_behavior": list(primary.get("responsive_behavior", [])),
        "design_tokens_needed": list(primary.get("design_tokens_needed", [])),
        "related_components": _resolved_related(kb, primary)[:_MAX_RELATED_OUTPUT],
        "from_knowledge_base": True,
        "nearest": nearest,
        **envelope,
    }

    emit_event("spec_component", {
        "component_type": component_type,
        "from_knowledge_base": True,
        "retrieval_state": res.state,
        "nearest": nearest,
        "variants_count": len(variants),
        "context": context[:120],
    })

    return result
