# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""MCP tool: spec_component

Generate detailed component specification with states, variants,
accessibility, and responsive behavior.

The agent (LLM) identifies a component type and context.  This tool
looks up the component in the knowledge base and returns a full
specification enriched with accessibility requirements.
"""

from __future__ import annotations

from typing import Any

from theia.tools._shared import coerce, emit_event, get_knowledge

# ---------------------------------------------------------------------------
# Default states and responsive breakpoints for components
# ---------------------------------------------------------------------------

_DEFAULT_STATES: list[str] = [
    "default",
    "hover",
    "active",
    "focus",
    "disabled",
    "loading",
]

_INTERACTIVE_STATES: list[str] = [
    "default",
    "hover",
    "active",
    "focus",
    "focus-visible",
    "disabled",
    "loading",
    "error",
    "success",
]

_RESPONSIVE_BREAKPOINTS: dict[str, dict[str, Any]] = {
    "web": {
        "breakpoints": ["sm (640px)", "md (768px)", "lg (1024px)", "xl (1280px)"],
        "strategy": "Fluid with breakpoint adjustments",
    },
    "mobile": {
        "breakpoints": ["compact (320px)", "medium (375px)", "expanded (428px)"],
        "strategy": "Full-width with padding adjustments",
    },
    "desktop": {
        "breakpoints": ["compact (1024px)", "medium (1280px)", "expanded (1440px+)"],
        "strategy": "Fixed or fluid within application chrome",
    },
}

# ---------------------------------------------------------------------------
# Common component archetypes — fallback when not in KB
# ---------------------------------------------------------------------------

_COMPONENT_ARCHETYPES: dict[str, dict[str, Any]] = {
    "button": {
        "anatomy": ["container", "label", "icon (optional)", "loading-indicator (optional)"],
        "states": _INTERACTIVE_STATES,
        "default_variants": ["primary", "secondary", "tertiary", "destructive", "ghost"],
        "a11y_role": "button",
        "common_mistakes": [
            "Using <div> instead of <button> element",
            "Missing disabled state announcement",
            "Icon-only button without accessible label",
            "Touch target smaller than 44x44px",
        ],
    },
    "input": {
        "anatomy": ["container", "label", "input-field", "helper-text", "error-text", "prefix (optional)", "suffix (optional)"],
        "states": ["default", "hover", "focus", "filled", "disabled", "read-only", "error", "success"],
        "default_variants": ["text", "password", "email", "number", "search", "textarea"],
        "a11y_role": "textbox",
        "common_mistakes": [
            "Placeholder text used as label",
            "Error state communicated only by color",
            "Missing aria-describedby for helper/error text",
            "No visible focus indicator",
        ],
    },
    "modal": {
        "anatomy": ["overlay", "container", "header", "close-button", "body", "footer (optional)"],
        "states": ["closed", "opening", "open", "closing"],
        "default_variants": ["default", "full-screen", "drawer", "alert"],
        "a11y_role": "dialog",
        "common_mistakes": [
            "Focus not trapped inside modal",
            "No return focus to trigger element on close",
            "Missing aria-modal attribute",
            "Escape key does not close modal",
            "Background content still scrollable",
        ],
    },
    "card": {
        "anatomy": ["container", "media (optional)", "header", "body", "footer (optional)", "actions (optional)"],
        "states": ["default", "hover", "focus", "selected", "disabled"],
        "default_variants": ["default", "outlined", "elevated", "interactive"],
        "a11y_role": "article",
        "common_mistakes": [
            "Entire card as link but with nested interactive elements",
            "Missing heading hierarchy within card",
            "Images without alt text",
            "Inconsistent action placement",
        ],
    },
    "data-table": {
        "anatomy": ["container", "header-row", "header-cell", "body-row", "body-cell", "sort-indicator", "pagination", "toolbar (optional)"],
        "states": ["default", "loading", "empty", "error", "row-selected", "row-hover"],
        "default_variants": ["default", "compact", "striped", "bordered"],
        "a11y_role": "table",
        "common_mistakes": [
            "Missing <th> scope attributes",
            "Sort state not announced to screen readers",
            "Pagination not keyboard accessible",
            "No caption or accessible name for the table",
            "Responsive table loses row context on small screens",
        ],
    },
    "navigation": {
        "anatomy": ["container", "nav-item", "active-indicator", "group-label (optional)", "collapse-toggle (optional)"],
        "states": ["default", "hover", "active", "focus", "expanded", "collapsed"],
        "default_variants": ["horizontal", "vertical", "sidebar", "bottom-bar", "breadcrumb"],
        "a11y_role": "navigation",
        "common_mistakes": [
            "Missing nav landmark with aria-label",
            "Current page not indicated with aria-current",
            "Dropdown menus not keyboard accessible",
            "Mobile navigation not reachable without JavaScript",
        ],
    },
    "select": {
        "anatomy": ["trigger", "label", "selected-value", "dropdown", "option", "option-group (optional)", "search (optional)"],
        "states": ["default", "hover", "focus", "open", "disabled", "error"],
        "default_variants": ["single", "multi", "searchable", "grouped"],
        "a11y_role": "listbox",
        "common_mistakes": [
            "Custom select not keyboard navigable",
            "Options not announced by screen readers",
            "Missing association between label and control",
            "Type-ahead search not implemented",
        ],
    },
    "toast": {
        "anatomy": ["container", "icon (optional)", "message", "action (optional)", "dismiss-button"],
        "states": ["entering", "visible", "exiting", "dismissed"],
        "default_variants": ["info", "success", "warning", "error"],
        "a11y_role": "status",
        "common_mistakes": [
            "Not using aria-live region",
            "Auto-dismiss too fast for screen reader users",
            "Stacking toasts that obscure content",
            "Action button in toast not keyboard accessible",
        ],
    },
}


# ---------------------------------------------------------------------------
# Main tool
# ---------------------------------------------------------------------------

def spec_component(
    component_type: str,
    context: str = "",
    variants_needed: list[str] | None = None,
    platform: str = "web",
    conn: object = None,
) -> dict:
    """Generate a detailed component specification.

    Args:
        component_type: The type of component, e.g. "button", "modal",
            "data-table", "card".
        context: Optional context for how the component will be used.
        variants_needed: Optional list of specific variants to include.
            If None, all default variants are returned.
        platform: Target platform ("web", "mobile", "desktop").
            Defaults to "web".
        conn: Kuzu/LadybugDB connection for graph mode, or None for JSON.

    Returns:
        Dict with keys: component, anatomy, states, variants,
        accessibility, responsive_behavior, design_tokens, common_mistakes.
    """
    variants_needed = coerce(variants_needed, list)
    platform = platform or "web"

    kb = get_knowledge(conn)

    # 1. Look up component in KB
    component_lower = component_type.lower().strip()
    kb_pattern = kb.get_component_pattern(component_lower)

    # Also try with hyphens replaced by underscores and vice versa
    if not kb_pattern:
        alt_id = component_lower.replace("-", "_")
        kb_pattern = kb.get_component_pattern(alt_id)
    if not kb_pattern:
        alt_id = component_lower.replace("_", "-")
        kb_pattern = kb.get_component_pattern(alt_id)

    # 2. Build base spec from KB or archetype fallback
    archetype = _COMPONENT_ARCHETYPES.get(component_lower)

    if kb_pattern:
        anatomy = kb_pattern.get("anatomy", archetype["anatomy"] if archetype else [])
        states = kb_pattern.get("states", archetype["states"] if archetype else _DEFAULT_STATES)
        all_variants = kb_pattern.get("variants", archetype["default_variants"] if archetype else [])
        a11y_role = kb_pattern.get("a11y_role", archetype["a11y_role"] if archetype else "")
        common_mistakes = kb_pattern.get("common_mistakes", archetype["common_mistakes"] if archetype else [])
        description = kb_pattern.get("description", "")
    elif archetype:
        anatomy = archetype["anatomy"]
        states = archetype["states"]
        all_variants = archetype["default_variants"]
        a11y_role = archetype["a11y_role"]
        common_mistakes = archetype["common_mistakes"]
        description = f"Standard {component_type} component"
    else:
        # Completely unknown component — return structural skeleton
        anatomy = ["container", "content"]
        states = list(_DEFAULT_STATES)
        all_variants = ["default"]
        a11y_role = ""
        common_mistakes = []
        description = f"Custom {component_type} component"

    # Filter variants if specific ones requested
    if variants_needed:
        variants = [v for v in all_variants if v in variants_needed]
        # Include any requested variants not in the default set
        for v in variants_needed:
            if v not in variants:
                variants.append(v)
    else:
        variants = list(all_variants)

    # 3. Enrich with accessibility requirements from KB
    accessibility: dict[str, Any] = {
        "role": a11y_role,
        "keyboard_interaction": [],
        "aria_attributes": [],
        "focus_management": "",
        "screen_reader_announcements": [],
    }

    # Look up relevant WCAG criteria
    relevant_criteria: list[dict[str, Any]] = []

    # Always check Level A
    a_criteria = kb.get_criteria_by_level("A")
    relevant_criteria.extend(a_criteria)

    # Add AA for standard compliance
    aa_criteria = kb.get_criteria_by_level("AA")
    relevant_criteria.extend(aa_criteria)

    # Extract relevant accessibility guidance based on component role
    a11y_requirements: list[str] = []
    for criterion in relevant_criteria:
        criterion_desc = criterion.get("description", "").lower()
        criterion_name = criterion.get("name", "").lower()

        # Check if the criterion is relevant to this component type
        if a11y_role == "button" and any(
            kw in criterion_desc for kw in ["keyboard", "focus", "name", "role"]
        ):
            a11y_requirements.append(
                f"{criterion.get('id', '')}: {criterion.get('name', '')}"
            )
        elif a11y_role == "textbox" and any(
            kw in criterion_desc for kw in ["label", "input", "error", "instruction"]
        ):
            a11y_requirements.append(
                f"{criterion.get('id', '')}: {criterion.get('name', '')}"
            )
        elif a11y_role == "dialog" and any(
            kw in criterion_desc for kw in ["focus", "keyboard", "trap", "modal"]
        ):
            a11y_requirements.append(
                f"{criterion.get('id', '')}: {criterion.get('name', '')}"
            )
        elif a11y_role == "navigation" and any(
            kw in criterion_desc for kw in ["navigation", "landmark", "heading", "link"]
        ):
            a11y_requirements.append(
                f"{criterion.get('id', '')}: {criterion.get('name', '')}"
            )
        elif a11y_role == "table" and any(
            kw in criterion_desc for kw in ["table", "header", "data", "relationship"]
        ):
            a11y_requirements.append(
                f"{criterion.get('id', '')}: {criterion.get('name', '')}"
            )
        elif a11y_role and any(
            kw in criterion_desc for kw in ["keyboard", "focus", "name", "role", "state"]
        ):
            a11y_requirements.append(
                f"{criterion.get('id', '')}: {criterion.get('name', '')}"
            )

    accessibility["wcag_requirements"] = a11y_requirements

    # Standard keyboard interactions based on role
    keyboard_map: dict[str, list[str]] = {
        "button": ["Enter/Space to activate", "Tab to move focus"],
        "textbox": ["Tab to focus", "Type to input", "Escape to clear/cancel"],
        "dialog": ["Escape to close", "Tab cycles through focusable elements", "Focus trapped within dialog"],
        "listbox": ["Arrow keys to navigate options", "Enter to select", "Type-ahead to filter", "Escape to close"],
        "navigation": ["Tab/Arrow keys to navigate items", "Enter to activate", "Escape to close submenus"],
        "table": ["Arrow keys to navigate cells", "Tab to move between interactive elements"],
        "status": ["Announced automatically by screen readers via aria-live"],
        "article": ["Tab to move between interactive elements within card"],
    }

    accessibility["keyboard_interaction"] = keyboard_map.get(a11y_role, ["Tab to focus", "Enter to activate"])

    # 4. Responsive behavior
    resp = _RESPONSIVE_BREAKPOINTS.get(platform.lower(), _RESPONSIVE_BREAKPOINTS["web"])
    responsive_behavior: list[dict[str, Any]] = [
        {
            "platform": platform,
            "breakpoints": resp["breakpoints"],
            "strategy": resp["strategy"],
            "adaptations": [],
        }
    ]

    # 5. Design tokens relevant to this component
    design_tokens: list[str] = [
        f"{component_lower}-background",
        f"{component_lower}-foreground",
        f"{component_lower}-border",
        f"{component_lower}-border-radius",
        f"{component_lower}-padding",
        f"{component_lower}-font-size",
        f"{component_lower}-font-weight",
        f"{component_lower}-min-height",
    ]

    # Add state-specific tokens
    for state in states:
        if state not in ("default", "loading"):
            design_tokens.append(f"{component_lower}-{state}-background")
            design_tokens.append(f"{component_lower}-{state}-foreground")

    # 6. Build result
    result: dict[str, Any] = {
        "component": component_type,
        "description": description,
        "anatomy": anatomy,
        "states": states,
        "variants": variants,
        "accessibility": accessibility,
        "responsive_behavior": responsive_behavior,
        "design_tokens": design_tokens,
        "common_mistakes": common_mistakes,
    }

    emit_event("spec_component", {
        "component_type": component_type,
        "platform": platform,
        "variants_count": len(variants),
        "from_knowledge_base": kb_pattern is not None,
        "context": context[:120] if context else "",
    })

    return result
