# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""MCP tool: plan_design_system

Plan a design system architecture with tokens, component hierarchy,
and responsive strategy.

The agent (LLM) provides a product description and platform targets.
This tool matches against the knowledge base to recommend foundation
patterns, token architecture, and component hierarchy.
"""

from __future__ import annotations

import copy
from typing import Any

from theia.knowledge.loader import DANGLING, NO_MATCH
from theia.tools._shared import (
    _MAX_MATCHED_SIGNALS,
    _resolved_edge,
    coerce,
    emit_event,
    get_knowledge,
)

# ---------------------------------------------------------------------------
# Token architecture templates — keyed by platform constraints
# ---------------------------------------------------------------------------

_BASE_TOKENS: dict[str, dict[str, Any]] = {
    "spacing": {
        "scale": [0, 2, 4, 8, 12, 16, 24, 32, 48, 64, 96],
        "unit": "px",
        "naming": "space-{index}",
    },
    "type_scale": {
        "scale": [12, 14, 16, 18, 20, 24, 30, 36, 48, 60],
        "unit": "px",
        "naming": "text-{size}",
        "line_heights": [1.2, 1.4, 1.5, 1.6],
    },
    "color": {
        "system": "semantic",
        "tiers": ["primitive", "semantic", "component"],
        "modes": ["light", "dark"],
    },
    "elevation": {
        "levels": [0, 1, 2, 3, 4, 5],
        "naming": "elevation-{level}",
    },
    "motion": {
        "durations": [100, 150, 200, 300, 500],
        "easings": ["ease-in", "ease-out", "ease-in-out", "spring"],
        "naming": "motion-{type}-{speed}",
    },
}

_PLATFORM_ADJUSTMENTS: dict[str, dict[str, Any]] = {
    "mobile": {
        "spacing_multiplier": 1.0,
        "min_touch_target": 48,
        "type_scale_floor": 14,
        "considerations": [
            "Thumb-zone ergonomics for bottom navigation",
            "Swipe gestures with fallback tap actions",
            "System font stack for performance",
            "Safe area insets for notch/dynamic island",
        ],
    },
    "web": {
        "spacing_multiplier": 1.0,
        "min_touch_target": 44,
        "type_scale_floor": 14,
        "considerations": [
            "CSS custom properties for token delivery",
            "Container queries for component-level responsiveness",
            "Reduced motion media query support",
            "Focus-visible for keyboard-only focus styles",
        ],
    },
    "desktop": {
        "spacing_multiplier": 1.0,
        "min_touch_target": 32,
        "type_scale_floor": 12,
        "considerations": [
            "Dense information display with compact spacing option",
            "Keyboard shortcuts and accelerators",
            "Window resize and multi-monitor support",
            "Right-click context menus",
        ],
    },
    "tablet": {
        "spacing_multiplier": 1.0,
        "min_touch_target": 44,
        "type_scale_floor": 14,
        "considerations": [
            "Landscape and portrait orientations",
            "Split-view and slide-over support",
            "Stylus input alongside touch",
            "Flexible grid that adapts between phone and desktop layouts",
        ],
    },
}

# ---------------------------------------------------------------------------
# Atomic design hierarchy
# ---------------------------------------------------------------------------

_COMPONENT_HIERARCHY: dict[str, dict[str, Any]] = {
    "atoms": {
        "description": "Smallest indivisible UI elements",
        "examples": ["button", "input", "label", "icon", "badge", "avatar", "tag"],
        "guidelines": "Each atom wraps a single HTML element or primitive control",
    },
    "molecules": {
        "description": "Groups of atoms working together as a unit",
        "examples": [
            "search-field", "form-field", "menu-item", "card-header",
            "list-item", "breadcrumb-item",
        ],
        "guidelines": "Molecules compose 2-4 atoms with a single responsibility",
    },
    "organisms": {
        "description": "Complex UI sections composed of molecules and atoms",
        "examples": [
            "navigation-bar", "data-table", "form", "card",
            "dialog", "sidebar", "toolbar",
        ],
        "guidelines": "Organisms are self-contained sections that can function independently",
    },
    "templates": {
        "description": "Page-level layouts that arrange organisms",
        "examples": [
            "dashboard-layout", "detail-layout", "list-layout",
            "auth-layout", "settings-layout",
        ],
        "guidelines": "Templates define content structure without real data",
    },
    "pages": {
        "description": "Specific instances of templates with real content",
        "examples": [
            "user-dashboard", "product-detail", "order-list",
            "login-page", "profile-settings",
        ],
        "guidelines": "Pages are the highest fidelity, showing real data and states",
    },
}

# ---------------------------------------------------------------------------
# Responsive strategies
# ---------------------------------------------------------------------------

_RESPONSIVE_STRATEGIES: dict[str, dict[str, Any]] = {
    "mobile-first": {
        "approach": "Design for smallest viewport first, enhance upward",
        "breakpoints": {"sm": 640, "md": 768, "lg": 1024, "xl": 1280, "2xl": 1536},
        "best_for": ["consumer apps", "content-heavy sites", "e-commerce"],
    },
    "desktop-first": {
        "approach": "Design for desktop, adapt down to mobile",
        "breakpoints": {"2xl": 1536, "xl": 1280, "lg": 1024, "md": 768, "sm": 640},
        "best_for": ["enterprise tools", "data dashboards", "admin panels"],
    },
    "component-driven": {
        "approach": "Components respond to their container, not the viewport",
        "breakpoints": {},
        "best_for": ["design systems", "widget libraries", "embeddable components"],
    },
    "adaptive": {
        "approach": "Serve distinct layouts per device class",
        "breakpoints": {"phone": 480, "tablet": 768, "desktop": 1024},
        "best_for": ["native-feel web apps", "platform-specific UX"],
    },
}


# ---------------------------------------------------------------------------
# Main tool
# ---------------------------------------------------------------------------

def plan_design_system(
    product_description: str,
    platforms: list[str] | None = None,
    brand_attributes: list[str] | None = None,
    existing_system: str | None = None,
    matched_signal_ids: list[str] | None = None,
    conn: object = None,
) -> dict:
    """Plan a design system architecture.

    The base-system foundation is retrieved through the shared Shape-C engine over
    the design_systems signal index: the caller (the LLM) recognises the product's
    structural signals against ``get_system_signal_index`` and passes the matched
    ids; the nearest existing system is hydrated and fanned out over its
    ``related_systems``, or the tool ABSTAINS to an honest custom foundation with a
    reason. The generative token / hierarchy / responsive / theming scaffolding below
    is unchanged.

    Args:
        product_description: Description of the product or product line
            the design system will serve. Context/telemetry only — the base-system
            match is driven by ``matched_signal_ids``, not this free text.
        platforms: Target platforms, e.g. ["web", "mobile", "desktop"].
            Defaults to ["web"].
        brand_attributes: Optional brand personality keywords, e.g.
            ["professional", "warm", "accessible"].
        existing_system: Optional ID of an existing design system in the
            knowledge base to use as a starting point (explicit-id path).
        matched_signal_ids: Signal ids the caller recognised against
            ``get_system_signal_index`` (problem-language -> sig-id). Drives the
            base-system match when ``existing_system`` is not supplied; bounded at
            the caller boundary before hydrate.
        conn: Kuzu/LadybugDB connection for graph mode, or None for JSON.

    Returns:
        Dict with keys: recommended_foundation, token_architecture,
        component_hierarchy, responsive_strategy, theming_approach.
        ``recommended_foundation`` carries the retrieval envelope
        (``retrieval_state`` / ``unmatched`` / ``dangling``) and, on a match, the
        nearest system's ``related_systems`` fan-out; a true miss abstains to the
        honest ``custom`` / ``create`` foundation with a reason (never a silent husk).
    """
    platforms = coerce(platforms, list) or ["web"]
    brand_attributes = coerce(brand_attributes, list) or []
    matched_signal_ids = coerce(matched_signal_ids, list) or []

    kb = get_knowledge(conn)

    # 1. Determine foundation — check existing system or match from KB
    recommended_foundation: dict[str, Any] = {}

    if existing_system:
        system = kb.get_design_system(existing_system)
        if system:
            recommended_foundation = {
                "base_system": system.get("id", ""),
                "name": system.get("name", ""),
                "description": system.get("description", ""),
                "rationale": f"Building on existing system: {system.get('name', existing_system)}",
                "extend_or_fork": "extend",
            }

    if not recommended_foundation:
        # Base-system match via the shared Shape-C engine over the design_systems
        # signal index (signal field ``signals``, live fan-out edge ``related_systems``)
        # — the SAME parameterized primitives the component index uses, zero new engine
        # code. This REPLACES the degenerate keyword scorer that read a ``keywords``
        # field no system carries, so best_score stayed 0 and every product defaulted
        # to 'custom'. The caller recognised the product's signals against
        # ``get_system_signal_index``; we hydrate the nearest existing system and fan
        # out over its related_systems, or ABSTAIN with a reason (four-state envelope).
        res = kb.hydrate_systems(matched_signal_ids[:_MAX_MATCHED_SIGNALS])
        envelope = {
            "retrieval_state": res.state,
            "unmatched": list(res.unmatched_signals),
            "dangling": list(res.dangling),
        }
        if res.state in (NO_MATCH, DANGLING) or not res.patterns:
            # Correct ABSTENTION, not a husk: the honest custom/create foundation with
            # a reason naming why no existing system was hydrated. Distinguishable from
            # a real match by the retrieval envelope the silent legacy 'custom' lacked.
            recommended_foundation = {
                "base_system": "custom",
                "name": "Custom Design System",
                "description": "No existing system matched; building from scratch",
                "rationale": (
                    "No recognised product signal mapped to an existing design system "
                    f"(retrieval_state={res.state}); building a custom foundation."
                ),
                "extend_or_fork": "create",
                "related_systems": [],
                **envelope,
            }
        else:
            # HIT / LOW_CONFIDENCE: hydrate the nearest existing system (the top-ranked
            # direct-vote seed) and surface its own related_systems fan-out. The
            # envelope's state flags a low-confidence (single-vote) match honestly.
            nearest = res.patterns[0]
            related_systems = [
                {"system_id": e["id"], "system_name": e["name"]}
                for e in _resolved_edge(kb.get_design_system, nearest, "related_systems")
            ]
            recommended_foundation = {
                "base_system": nearest["id"],
                "name": nearest.get("name", nearest["id"]),
                "description": nearest.get("description", ""),
                "rationale": (
                    "Matched on recognised product signals; nearest existing system "
                    "hydrated through the design_systems index and fanned out over its "
                    "related_systems."
                ),
                "extend_or_fork": "fork",
                "related_systems": related_systems,
                "retrieval": dict(nearest["retrieval"]),
                **envelope,
            }

    # 2. Build token architecture based on platforms
    token_architecture: dict[str, Any] = copy.deepcopy(_BASE_TOKENS)

    platform_considerations: list[str] = []
    min_touch_target = 44
    type_scale_floor = 14

    for platform in platforms:
        p_lower = platform.lower()
        adj = _PLATFORM_ADJUSTMENTS.get(p_lower)
        if adj:
            platform_considerations.extend(adj["considerations"])
            min_touch_target = max(min_touch_target, adj["min_touch_target"])
            type_scale_floor = max(type_scale_floor, adj["type_scale_floor"])

    token_architecture["platform_considerations"] = platform_considerations
    token_architecture["min_touch_target"] = min_touch_target
    token_architecture["type_scale_floor"] = type_scale_floor

    # Brand-influenced theming
    theming_approach: dict[str, Any] = {
        "modes": ["light", "dark"],
        "token_tiers": ["primitive", "semantic", "component"],
        "brand_attributes": brand_attributes,
        "customisation_points": [
            "Color primitives (brand palette)",
            "Typography scale and font families",
            "Border radius (sharp vs rounded)",
            "Spacing density (compact / default / comfortable)",
            "Motion intensity (reduced / default / expressive)",
        ],
    }

    if brand_attributes:
        # Infer theming hints from brand attributes
        attrs_lower = [a.lower() for a in brand_attributes]
        if any(a in attrs_lower for a in ["playful", "fun", "friendly"]):
            theming_approach["radius_style"] = "rounded"
            theming_approach["motion_style"] = "expressive"
        elif any(a in attrs_lower for a in ["professional", "enterprise", "corporate"]):
            theming_approach["radius_style"] = "subtle"
            theming_approach["motion_style"] = "minimal"
        elif any(a in attrs_lower for a in ["minimal", "clean", "modern"]):
            theming_approach["radius_style"] = "sharp"
            theming_approach["motion_style"] = "reduced"

    # 3. Component hierarchy
    component_hierarchy: dict[str, Any] = copy.deepcopy(_COMPONENT_HIERARCHY)

    # 4. Responsive strategy selection
    platforms_lower = [p.lower() for p in platforms]
    if len(platforms) == 1 and platforms_lower[0] == "web":
        responsive_key = "mobile-first"
    elif "mobile" in platforms_lower and "desktop" in platforms_lower:
        responsive_key = "adaptive"
    elif "desktop" in platforms_lower and "mobile" not in platforms_lower:
        responsive_key = "desktop-first"
    else:
        responsive_key = "component-driven"

    responsive_strategy: dict[str, Any] = {
        "selected": responsive_key,
        **_RESPONSIVE_STRATEGIES[responsive_key],
        "target_platforms": platforms,
    }

    # 5. Build result
    result: dict[str, Any] = {
        "recommended_foundation": recommended_foundation,
        "token_architecture": token_architecture,
        "component_hierarchy": component_hierarchy,
        "responsive_strategy": responsive_strategy,
        "theming_approach": theming_approach,
    }

    emit_event("plan_design_system", {
        "product_description": product_description[:120],
        "platforms": platforms,
        "foundation": recommended_foundation.get("base_system", ""),
        "responsive_strategy": responsive_key,
    })

    return result
