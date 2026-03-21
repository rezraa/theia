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
    structural_signals: Union[list[str], str],
    constraints: Union[str, dict, None] = None,
    conn: Any = None,
) -> dict:
    """Audit an interface or system design for issues, pattern mismatches,
    and accessibility concerns.

    Given a description and structural signals about the design, returns
    matched rules, identified issues, and accessibility flags.

    Args:
        description: Description of the interface or system design to audit.
        structural_signals: Agent-identified signals about the design, e.g.
            ["color-only", "no-labels", "modal-dialog", "data-table"].
        constraints: Optional dict of constraints for filtering, e.g.
            {"platform": "mobile", "audience": "enterprise"}.
        conn: Kuzu/LadybugDB connection for graph mode (injected by Othrys).

    Returns: {matched_rules: [...], design_issues: [...],
              recommendations: [...], accessibility_flags: [...]}
    """
    return _audit_design(
        description=description,
        structural_signals=coerce(structural_signals, list),
        constraints=coerce(constraints, dict),
        conn=conn,
    )


@mcp.tool()
def plan_design_system(
    product_description: str,
    platforms: Union[list[str], str, None] = None,
    brand_attributes: Union[list[str], str, None] = None,
    existing_system: Union[str, None] = None,
    conn: Any = None,
) -> dict:
    """Plan a design system architecture with tokens, component hierarchy,
    and responsive strategy.

    Given a product description and platform targets, recommends foundation
    patterns, token architecture, and component hierarchy.

    Args:
        product_description: Description of the product or product line
            the design system will serve.
        platforms: Target platforms, e.g. ["web", "mobile", "desktop"].
            Defaults to ["web"].
        brand_attributes: Optional brand personality keywords, e.g.
            ["professional", "warm", "accessible"].
        existing_system: Optional ID of an existing design system in the
            knowledge base to use as a starting point.
        conn: Kuzu/LadybugDB connection for graph mode (injected by Othrys).

    Returns: {recommended_foundation: {...}, token_architecture: {...},
              component_hierarchy: [...], responsive_strategy: {...},
              theming_approach: {...}}
    """
    return _plan_design_system(
        product_description=product_description,
        platforms=coerce(platforms, list),
        brand_attributes=coerce(brand_attributes, list),
        existing_system=existing_system,
        conn=conn,
    )


@mcp.tool()
def spec_component(
    component_type: str,
    context: str = "",
    variants_needed: Union[list[str], str, None] = None,
    platform: str = "web",
    conn: Any = None,
) -> dict:
    """Generate a detailed component specification with states, variants,
    accessibility requirements, and responsive behavior.

    Given a component type and usage context, returns a full specification
    enriched with accessibility requirements and design tokens.

    Args:
        component_type: The type of component, e.g. "button", "modal",
            "data-table", "card".
        context: Optional context for how the component will be used.
        variants_needed: Optional list of specific variants to include.
            If None, all default variants are returned.
        platform: Target platform ("web", "mobile", "desktop").
            Defaults to "web".
        conn: Kuzu/LadybugDB connection for graph mode (injected by Othrys).

    Returns: {component: "...", anatomy: [...], states: [...],
              variants: [...], accessibility: {...},
              responsive_behavior: {...}, design_tokens: {...},
              common_mistakes: [...]}
    """
    return _spec_component(
        component_type=component_type,
        context=context,
        variants_needed=coerce(variants_needed, list),
        platform=platform,
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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    mcp.run()


if __name__ == "__main__":
    main()
