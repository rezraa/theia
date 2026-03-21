# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""MCP tool: evaluate_accessibility

Evaluate accessibility compliance against WCAG standards.

The agent (LLM) describes a component, page, or interface.  This tool
analyses the description for accessibility signals, checks against
WCAG criteria at the target level, and identifies potential violations.
"""

from __future__ import annotations

from typing import Any

from theia.tools._shared import coerce, emit_event, get_knowledge

# ---------------------------------------------------------------------------
# Accessibility signal detectors — keywords in description → potential issues
# ---------------------------------------------------------------------------

_A11Y_SIGNAL_CHECKS: list[dict[str, Any]] = [
    {
        "signal_keywords": ["color only", "colour only", "color-coded", "colour-coded", "red and green"],
        "issue": "Color used as sole means of conveying information",
        "wcag": "1.4.1",
        "level": "A",
        "category": "perceivable",
        "check": "Verify non-color indicators (icons, patterns, text) are present",
    },
    {
        "signal_keywords": ["no alt", "missing alt", "decorative image", "background image"],
        "issue": "Images may lack appropriate alternative text",
        "wcag": "1.1.1",
        "level": "A",
        "category": "perceivable",
        "check": "Verify all meaningful images have descriptive alt text; decorative images have empty alt",
    },
    {
        "signal_keywords": ["no label", "missing label", "placeholder only", "placeholder as label", "unlabeled", "unlabelled"],
        "issue": "Form controls may lack accessible labels",
        "wcag": "1.3.1",
        "level": "A",
        "category": "perceivable",
        "check": "Verify all form controls have visible, programmatically associated labels",
    },
    {
        "signal_keywords": ["keyboard", "tab order", "focus order", "not focusable", "keyboard trap"],
        "issue": "Keyboard accessibility may be compromised",
        "wcag": "2.1.1",
        "level": "A",
        "category": "operable",
        "check": "Verify all interactive elements are keyboard accessible with logical tab order",
    },
    {
        "signal_keywords": ["small target", "tiny button", "small click", "touch target", "tap target", "hard to tap"],
        "issue": "Touch/click targets may be below minimum size",
        "wcag": "2.5.8",
        "level": "AA",
        "category": "operable",
        "check": "Verify touch targets are at least 44x44px (Level AA) or 48x48px (recommended)",
    },
    {
        "signal_keywords": ["animation", "motion", "parallax", "scroll effect", "transition", "auto-play"],
        "issue": "Motion may cause issues for vestibular disorder users",
        "wcag": "2.3.3",
        "level": "AAA",
        "category": "operable",
        "check": "Verify prefers-reduced-motion is honoured and pause controls are available",
    },
    {
        "signal_keywords": ["contrast", "light text", "grey text", "gray text", "faded", "low contrast"],
        "issue": "Text contrast may be insufficient",
        "wcag": "1.4.3",
        "level": "AA",
        "category": "perceivable",
        "check": "Verify 4.5:1 contrast ratio for normal text, 3:1 for large text (18pt+ or 14pt+ bold)",
    },
    {
        "signal_keywords": ["modal", "dialog", "popup", "overlay", "lightbox"],
        "issue": "Modal/dialog may have focus management issues",
        "wcag": "2.4.3",
        "level": "A",
        "category": "operable",
        "check": "Verify focus is trapped in modal, Escape closes it, focus returns to trigger on dismiss",
    },
    {
        "signal_keywords": ["error", "validation", "form error", "required field", "invalid"],
        "issue": "Error messaging may not be accessible",
        "wcag": "3.3.1",
        "level": "A",
        "category": "understandable",
        "check": "Verify errors are described in text, associated with fields via aria-describedby, and announced",
    },
    {
        "signal_keywords": ["heading", "no heading", "heading order", "skip heading", "h1 h3"],
        "issue": "Heading hierarchy may be incorrect",
        "wcag": "1.3.1",
        "level": "A",
        "category": "perceivable",
        "check": "Verify heading levels are sequential (no skipping) and correctly nest content",
    },
    {
        "signal_keywords": ["video", "audio", "media", "podcast", "stream"],
        "issue": "Media content may lack captions or transcripts",
        "wcag": "1.2.1",
        "level": "A",
        "category": "perceivable",
        "check": "Verify video has captions, audio has transcripts, and media player controls are accessible",
    },
    {
        "signal_keywords": ["timeout", "time limit", "session expire", "auto logout", "countdown"],
        "issue": "Time limits may not accommodate all users",
        "wcag": "2.2.1",
        "level": "A",
        "category": "operable",
        "check": "Verify users can extend or disable time limits; warn before session expiry",
    },
    {
        "signal_keywords": ["language", "multilingual", "rtl", "right-to-left", "i18n"],
        "issue": "Language and directionality may not be properly declared",
        "wcag": "3.1.1",
        "level": "A",
        "category": "understandable",
        "check": "Verify lang attribute on html element and dir attribute for RTL content",
    },
    {
        "signal_keywords": ["table", "data table", "grid", "spreadsheet"],
        "issue": "Data tables may lack proper semantic structure",
        "wcag": "1.3.1",
        "level": "A",
        "category": "perceivable",
        "check": "Verify <th> elements with scope, <caption> or aria-label, and proper header association",
    },
    {
        "signal_keywords": ["drag", "drag and drop", "sortable", "reorder", "draggable"],
        "issue": "Drag interactions may not have keyboard alternatives",
        "wcag": "2.5.7",
        "level": "AA",
        "category": "operable",
        "check": "Verify all drag operations have a keyboard-accessible alternative (e.g. arrow keys, move menu)",
    },
]

# ---------------------------------------------------------------------------
# Automated checks that can be suggested
# ---------------------------------------------------------------------------

_AUTOMATED_CHECKS: list[dict[str, str]] = [
    {"tool": "axe-core", "description": "Automated accessibility testing engine (browser)"},
    {"tool": "Lighthouse", "description": "Chrome DevTools accessibility audit"},
    {"tool": "WAVE", "description": "Web accessibility evaluation tool"},
    {"tool": "pa11y", "description": "CLI accessibility testing tool"},
    {"tool": "colour-contrast-checker", "description": "Manual contrast ratio verification"},
    {"tool": "screen-reader", "description": "Manual testing with VoiceOver / NVDA / JAWS"},
    {"tool": "keyboard-only", "description": "Manual testing: navigate entire interface with keyboard only"},
]


# ---------------------------------------------------------------------------
# Main tool
# ---------------------------------------------------------------------------

def evaluate_accessibility(
    component_or_page_description: str,
    target_level: str = "AA",
    current_implementation: str | None = None,
    conn: object = None,
) -> dict:
    """Evaluate accessibility compliance against WCAG standards.

    Args:
        component_or_page_description: Description of the component,
            page, or interface to evaluate.
        target_level: WCAG conformance target — "A", "AA", or "AAA".
            Defaults to "AA".
        current_implementation: Optional description of the current
            implementation details for more specific analysis.
        conn: Kuzu/LadybugDB connection for graph mode, or None for JSON.

    Returns:
        Dict with keys: target_level, criteria_checked, violations,
        passes, recommendations, automated_checks, compliance_score.
    """
    target_level = (target_level or "AA").upper()
    if target_level not in ("A", "AA", "AAA"):
        target_level = "AA"

    kb = get_knowledge(conn)

    # 1. Get all criteria for target level and below
    applicable_criteria: list[dict[str, Any]] = []

    # Level A is always included
    a_criteria = kb.get_criteria_by_level("A")
    applicable_criteria.extend(a_criteria)

    # Level AA if target is AA or AAA
    if target_level in ("AA", "AAA"):
        aa_criteria = kb.get_criteria_by_level("AA")
        applicable_criteria.extend(aa_criteria)

    # Level AAA if target is AAA
    if target_level == "AAA":
        aaa_criteria = kb.get_criteria_by_level("AAA")
        applicable_criteria.extend(aaa_criteria)

    criteria_checked = len(applicable_criteria)

    # 2. Analyse description for accessibility signals
    desc_lower = component_or_page_description.lower()
    impl_lower = (current_implementation or "").lower()
    combined_text = f"{desc_lower} {impl_lower}"

    violations: list[dict[str, Any]] = []
    passes: list[dict[str, Any]] = []
    recommendations: list[dict[str, Any]] = []

    checked_wcag_ids: set[str] = set()

    for check in _A11Y_SIGNAL_CHECKS:
        # Determine if this check's level is within scope
        check_level = check["level"]
        if check_level == "AAA" and target_level != "AAA":
            continue
        if check_level == "AA" and target_level == "A":
            continue

        # Check if any signal keywords match the description
        matched_keywords = [
            kw for kw in check["signal_keywords"]
            if kw in combined_text
        ]

        if matched_keywords:
            violation: dict[str, Any] = {
                "wcag_criterion": check["wcag"],
                "level": check_level,
                "category": check["category"],
                "issue": check["issue"],
                "matched_signals": matched_keywords,
                "verification": check["check"],
            }
            violations.append(violation)
            checked_wcag_ids.add(check["wcag"])

            recommendations.append({
                "wcag_criterion": check["wcag"],
                "action": check["check"],
                "priority": "high" if check_level == "A" else (
                    "medium" if check_level == "AA" else "low"
                ),
            })

    # 3. Check for positive signals (things done right)
    positive_signals: list[tuple[str, str, str]] = [
        ("aria-label", "1.1.1", "Accessible names provided via ARIA"),
        ("aria-describedby", "1.3.1", "Descriptions associated with controls"),
        ("role=", "4.1.2", "ARIA roles explicitly defined"),
        ("alt=", "1.1.1", "Alternative text attributes present"),
        ("focus-visible", "2.4.7", "Focus-visible styles implemented"),
        ("skip to", "2.4.1", "Skip navigation link present"),
        ("aria-live", "4.1.3", "Live regions for dynamic content"),
        ("prefers-reduced-motion", "2.3.3", "Reduced motion preference respected"),
        ("lang=", "3.1.1", "Language attribute set"),
        ("caption", "1.3.1", "Table captions provided"),
    ]

    for keyword, wcag_id, description in positive_signals:
        if keyword in combined_text:
            passes.append({
                "wcag_criterion": wcag_id,
                "description": description,
                "signal": keyword,
            })
            checked_wcag_ids.add(wcag_id)

    # 4. Determine relevant automated checks
    automated_checks: list[dict[str, str]] = []
    for tool_check in _AUTOMATED_CHECKS:
        automated_checks.append(tool_check)

    # 5. Calculate compliance score
    # Score is based on: criteria without violations / total criteria checked
    # Signal-based checks that found violations reduce the score
    if violations:
        # Each violation at Level A is weighted more heavily
        violation_weight = 0.0
        for v in violations:
            if v["level"] == "A":
                violation_weight += 0.15
            elif v["level"] == "AA":
                violation_weight += 0.10
            else:
                violation_weight += 0.05

        compliance_score = max(0.0, round(1.0 - violation_weight, 2))
    else:
        compliance_score = 1.0

    # 6. Build result
    result: dict[str, Any] = {
        "target_level": target_level,
        "criteria_checked": criteria_checked,
        "violations": violations,
        "passes": passes,
        "recommendations": recommendations,
        "automated_checks": automated_checks,
        "compliance_score": compliance_score,
    }

    emit_event("evaluate_accessibility", {
        "description": component_or_page_description[:120],
        "target_level": target_level,
        "criteria_checked": criteria_checked,
        "violations_count": len(violations),
        "passes_count": len(passes),
        "compliance_score": compliance_score,
    })

    return result
