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

from theia.tools._shared import coerce, emit_event, get_knowledge

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
    conn: object = None,
) -> dict:
    """Plan a design system architecture.

    Args:
        product_description: Description of the product or product line
            the design system will serve.
        platforms: Target platforms, e.g. ["web", "mobile", "desktop"].
            Defaults to ["web"].
        brand_attributes: Optional brand personality keywords, e.g.
            ["professional", "warm", "accessible"].
        existing_system: Optional ID of an existing design system in the
            knowledge base to use as a starting point.
        conn: Kuzu/LadybugDB connection for graph mode, or None for JSON.

    Returns:
        Dict with keys: recommended_foundation, token_architecture,
        component_hierarchy, responsive_strategy, theming_approach.
    """
    platforms = coerce(platforms, list) or ["web"]
    brand_attributes = coerce(brand_attributes, list) or []

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
        # Match product description keywords against design system signals
        desc_lower = product_description.lower()
        categories = kb.list_design_system_categories()
        best_match: dict | None = None
        best_score = 0

        for cat in categories:
            systems = kb.get_design_systems_by_category(cat)
            for system in systems:
                score = 0
                sys_name = system.get("name", "").lower()
                sys_desc = system.get("description", "").lower()
                sys_keywords = [
                    kw.lower()
                    for kw in system.get("keywords", [])
                ]

                # Check keyword overlap with product description
                for kw in sys_keywords:
                    if kw in desc_lower:
                        score += 2
                if sys_name in desc_lower:
                    score += 1
                # Category match
                if cat.lower() in desc_lower:
                    score += 1

                if score > best_score:
                    best_score = score
                    best_match = system

        if best_match:
            recommended_foundation = {
                "base_system": best_match.get("id", ""),
                "name": best_match.get("name", ""),
                "description": best_match.get("description", ""),
                "rationale": "Matched based on product description keywords",
                "extend_or_fork": "fork",
                "match_confidence": min(best_score / 6.0, 1.0),
            }
        else:
            recommended_foundation = {
                "base_system": "custom",
                "name": "Custom Design System",
                "description": "No existing system matched; building from scratch",
                "rationale": "Product description did not match any existing system",
                "extend_or_fork": "create",
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
