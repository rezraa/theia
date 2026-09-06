# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""Theia — Design Titan MCP server.

Thin wrappers that delegate to tool modules in theia/tools/.
Same pattern as Themis/Phoebe/Mnemos: server registers tools, modules do the work.
"""

from __future__ import annotations

from typing import Any, Union

from fastmcp import FastMCP

from theia.tools.audit_design import audit_design as _audit_design
from theia.tools.plan_design_system import plan_design_system as _plan_design_system
from theia.tools.spec_component import spec_component as _spec_component
from theia.tools.evaluate_accessibility import evaluate_accessibility as _evaluate_accessibility
from theia.tools.log_decision import log_decision as _log_decision
from theia.tools.get_signal_index import get_signal_index as _get_signal_index
from theia.tools._shared import coerce


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

mcp = FastMCP("theia", instructions=(
    "I am Theia, Titan of sight and brilliance. I see what others overlook. "
    "I design systems that are clear, consistent, and accessible. "
    "I don't decorate — I illuminate. Every pixel has a reason. "
    "I think in tokens, components, and design systems. "
    "Accessibility is not an afterthought — it is the foundation. "
    "If it can't be perceived, it doesn't exist."
))


# ---------------------------------------------------------------------------
# Tool registrations -- thin wrappers
# ---------------------------------------------------------------------------

@mcp.tool()
def audit_design(
    description: str,
    matched_signal_ids: Union[list[str], str],
    constraints: Union[str, dict, None] = None,
    k: int = 10,
    conn: Any = None,
) -> dict:
    """Audit an interface design: name each retrieved component's issues from its
    own fields (common_mistakes, anatomy, states) and surface its accessibility
    requirements.

    Retrieval is driven by the signal ids the caller recognised against
    ``get_signal_index`` (the proven Shape-C path), NOT by prose keyword matching.

    Args:
        description: Free-text description of the interface — context/telemetry
            only (retrieval is driven by ``matched_signal_ids``).
        matched_signal_ids: Signal ids recognised against ``get_signal_index``,
            e.g. ["sig-19487c3e3fa0", ...]. The prose ``structural_signals`` param
            is retired.
        constraints: Optional dict, e.g. {"platform": "mobile"} (dormant facet
            gate).
        k: Number of retrieved components to reason over (engine-clamped 1..50).
        conn: Kuzu/LadybugDB connection for graph mode (injected by Othrys).

    Returns: {constraints_analyzed, design_issues: [...], recommendations: [...],
              accessibility_flags: [...], retrieval_state, unmatched, dangling}
    """
    return _audit_design(
        description=description,
        matched_signal_ids=coerce(matched_signal_ids, list),
        constraints=coerce(constraints, dict),
        k=k,
        conn=conn,
    )


@mcp.tool()
def plan_design_system(
    product_description: str,
    platforms: Union[list[str], str, None] = None,
    brand_attributes: Union[list[str], str, None] = None,
    existing_system: Union[str, None] = None,
    matched_signal_ids: Union[list[str], str, None] = None,
    conn: Any = None,
) -> dict:
    """Plan a design system architecture with tokens, component hierarchy,
    and responsive strategy.

    The base-system foundation is retrieved through the shared Shape-C engine over
    the design_systems signal index: the caller recognises the product's structural
    signals against ``get_signal_index.system_signals`` and passes the matched ids; the
    nearest existing system is hydrated and fanned out over its ``related_systems``,
    or the tool abstains to an honest custom foundation with a reason (never a silent
    always-'custom'). The token / hierarchy / responsive / theming scaffolding is
    generative and unchanged.

    Args:
        product_description: Description of the product or product line
            the design system will serve (context/telemetry only — the base-system
            match is driven by ``matched_signal_ids``).
        platforms: Target platforms, e.g. ["web", "mobile", "desktop"].
            Defaults to ["web"].
        brand_attributes: Optional brand personality keywords, e.g.
            ["professional", "warm", "accessible"].
        existing_system: Optional ID of an existing design system in the
            knowledge base to use as a starting point (explicit-id path).
        matched_signal_ids: Signal ids recognised against ``get_signal_index.system_signals``,
            e.g. ["sig-...", ...]; drives the base-system match when
            ``existing_system`` is not supplied.
        conn: Kuzu/LadybugDB connection for graph mode (injected by Othrys).

    Returns: {recommended_foundation: {..., retrieval_state, unmatched, dangling,
              related_systems}, token_architecture: {...}, component_hierarchy: [...],
              responsive_strategy: {...}, theming_approach: {...}}
    """
    return _plan_design_system(
        product_description=product_description,
        platforms=coerce(platforms, list),
        brand_attributes=coerce(brand_attributes, list),
        existing_system=existing_system,
        matched_signal_ids=coerce(matched_signal_ids, list),
        conn=conn,
    )


@mcp.tool()
def spec_component(
    component_type: str,
    context: str = "",
    variants_needed: Union[list[str], str, None] = None,
    matched_signal_ids: Union[list[str], str, None] = None,
    conn: Any = None,
) -> dict:
    """Generate a component specification from the component's OWN corpus fields.

    Resolves ``component_type`` to a corpus id and SEEDS retrieval from that
    component's own signals (one hydrate, one-hop fan-out over related_patterns),
    returning its own anatomy/states/variants/accessibility_requirements/
    common_mistakes/responsive_behavior/design_tokens_needed. A non-resolving type
    retrieves the nearest component from the caller's recognised
    ``matched_signal_ids`` (flagged ``nearest``); a true miss fails closed through the
    retrieval envelope, never the ['container','content'] husk.

    Args:
        component_type: The component to spec, e.g. "navbar", "modal", "data-table".
        context: Optional usage context — context/telemetry only, never surfaced.
        variants_needed: Optional variant names; filters the component's own variants.
            If None, all own variants are returned.
        matched_signal_ids: Signal ids recognised against ``get_signal_index``, used
            ONLY when ``component_type`` does not resolve (nearest path).
        conn: Kuzu/LadybugDB connection for graph mode (injected by Othrys).

    Returns: {component, component_id, component_name, description, anatomy, states,
              variants, accessibility_requirements, common_mistakes,
              responsive_behavior, design_tokens_needed, related_components,
              from_knowledge_base, nearest, retrieval_state, unmatched, dangling}
    """
    return _spec_component(
        component_type=component_type,
        context=context,
        variants_needed=coerce(variants_needed, list),
        matched_signal_ids=coerce(matched_signal_ids, list),
        conn=conn,
    )


@mcp.tool()
def evaluate_accessibility(
    component_or_page_description: str,
    target_level: str = "AA",
    current_implementation: Union[str, None] = None,
    conn: Any = None,
) -> dict:
    """Evaluate accessibility compliance against WCAG standards.

    Analyses a component or page description for accessibility signals,
    checks against WCAG criteria at the target level, and identifies
    potential violations.

    Args:
        component_or_page_description: Description of the component,
            page, or interface to evaluate.
        target_level: WCAG conformance target -- "A", "AA", or "AAA".
            Defaults to "AA".
        current_implementation: Optional description of the current
            implementation details for more specific analysis.
        conn: Kuzu/LadybugDB connection for graph mode (injected by Othrys).

    Returns: {target_level: "...", criteria_checked: [...],
              violations: [...], passes: [...], recommendations: [...],
              automated_checks: [...], compliance_score: 0.0-1.0}
    """
    return _evaluate_accessibility(
        component_or_page_description=component_or_page_description,
        target_level=target_level,
        current_implementation=current_implementation,
        conn=conn,
    )


@mcp.tool()
def log_decision(
    decision_type: str,
    context: str,
    choice_made: str,
    alternatives_considered: Union[list[str], str, None] = None,
    rationale: str = "",
    conn: Any = None,
) -> dict:
    """Record a design decision with rationale and alternatives considered.

    Every design decision is logged permanently. The log is append-only.
    Supports dual-mode storage: Kuzu graph or local JSONL file.

    Args:
        decision_type: Category of the decision, e.g. "component",
            "layout", "typography", "color", "accessibility", "pattern".
        context: Description of the situation or problem that prompted
            the decision.
        choice_made: The option that was selected.
        alternatives_considered: Other options that were evaluated
            but not chosen.
        rationale: Reasoning behind the choice.
        conn: Kuzu/LadybugDB connection for graph mode (injected by Othrys).

    Returns: {decision_id: "...", decision_type: "...", recorded: true,
              timestamp: "..."}
    """
    return _log_decision(
        decision_type=decision_type,
        context=context,
        choice_made=choice_made,
        alternatives_considered=coerce(alternatives_considered, list),
        rationale=rationale,
        conn=conn,
    )


@mcp.tool()
def get_signal_index(conn: Any = None) -> dict:
    """Return both deterministic Shape-C signal-index views in ONE nested composite.

    The single read-only signal-index accessor. Exposes every structural signal in
    BOTH corpora as two labelled surfaces: ``component_signals`` (component corpus)
    and ``system_signals`` (design_systems corpus). The agent recognises a problem's
    signals against the relevant surface in working memory and passes the matched
    signal ids to the concern tools (``component_signals`` -> audit_design /
    spec_component; ``system_signals`` -> plan_design_system). This tool performs no
    matching itself. ONE public tool by design: the filename-keyed seed mints one
    graph tool per file, so a single accessor is the reachability guarantee.

    Args:
        conn: Kuzu/LadybugDB connection for graph mode (injected by Othrys).

    Returns: {component_signals: [{signal_id, signal_text, component_ids}, ...],
              system_signals: [{signal_id, signal_text, system_ids}, ...]}
        — each view sorted by signal_id with sorted id-lists so the composite
        serialises identically on every call.
    """
    return _get_signal_index(conn=conn)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    mcp.run()


if __name__ == "__main__":
    main()
