# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""MCP tool: audit_design

Audit an interface or system design for issues, pattern mismatches,
and accessibility concerns.

The agent (LLM) reads the design/interface and identifies structural
signals.  This tool matches those signals against decision_rules.json,
checks for common anti-patterns, and flags accessibility violations.
"""

from __future__ import annotations

from typing import Any

from theia.tools._shared import coerce, emit_event, get_knowledge

# ---------------------------------------------------------------------------
# Anti-pattern detectors — structural signal keywords → design issues
# ---------------------------------------------------------------------------

_ANTI_PATTERNS: dict[str, dict[str, Any]] = {
    "color-only": {
        "issue": "Color used as sole indicator",
        "severity": "high",
        "wcag": "1.4.1",
        "recommendation": "Add non-color indicators (icons, patterns, text labels) alongside color",
    },
    "no-labels": {
        "issue": "Form inputs missing visible labels",
        "severity": "high",
        "wcag": "1.3.1",
        "recommendation": "Add visible, associated labels to all form controls",
    },
    "small-touch-targets": {
        "issue": "Touch targets below minimum size",
        "severity": "medium",
        "wcag": "2.5.8",
        "recommendation": "Ensure touch targets are at least 44x44 CSS pixels (48x48 recommended)",
    },
    "no-focus-indicator": {
        "issue": "Missing visible focus indicator",
        "severity": "high",
        "wcag": "2.4.7",
        "recommendation": "Add visible focus styles for all interactive elements",
    },
    "auto-play": {
        "issue": "Auto-playing media content",
        "severity": "medium",
        "wcag": "1.4.2",
        "recommendation": "Provide pause/stop/mute controls; avoid auto-play for audio",
    },
    "no-alt-text": {
        "issue": "Images missing alternative text",
        "severity": "high",
        "wcag": "1.1.1",
        "recommendation": "Add descriptive alt text or mark decorative images with empty alt",
    },
    "low-contrast": {
        "issue": "Insufficient color contrast",
        "severity": "high",
        "wcag": "1.4.3",
        "recommendation": "Ensure 4.5:1 contrast ratio for normal text, 3:1 for large text",
    },
    "no-keyboard-access": {
        "issue": "Interactive elements not keyboard accessible",
        "severity": "high",
        "wcag": "2.1.1",
        "recommendation": "Ensure all interactive elements are reachable and operable via keyboard",
    },
    "missing-error-messaging": {
        "issue": "Form errors not clearly communicated",
        "severity": "medium",
        "wcag": "3.3.1",
        "recommendation": "Identify errors in text, describe them, and suggest corrections",
    },
    "inconsistent-navigation": {
        "issue": "Navigation patterns vary across pages",
        "severity": "medium",
        "wcag": "3.2.3",
        "recommendation": "Keep navigation mechanisms consistent across all pages",
    },
    "no-skip-link": {
        "issue": "No skip navigation mechanism",
        "severity": "medium",
        "wcag": "2.4.1",
        "recommendation": "Add a skip-to-main-content link as the first focusable element",
    },
    "motion-heavy": {
        "issue": "Excessive motion without reduced-motion support",
        "severity": "medium",
        "wcag": "2.3.3",
        "recommendation": "Honour prefers-reduced-motion and provide pause controls",
    },
}


# ---------------------------------------------------------------------------
# Main tool
# ---------------------------------------------------------------------------

def audit_design(
    description: str,
    structural_signals: list[str],
    constraints: dict | None = None,
    conn: object = None,
) -> dict:
    """Audit a design for issues, pattern mismatches, and accessibility concerns.

    Args:
        description: Description of the interface or system design to audit.
        structural_signals: Agent-identified signals, e.g.
            ["color-only", "no-labels", "modal-dialog", "data-table"].
        constraints: Optional dict with constraint signals for filtering
            (e.g. ``{"platform": "mobile", "audience": "enterprise"}``).
        conn: Kuzu/LadybugDB connection for graph mode, or None for JSON.

    Returns:
        Dict with keys: matched_rules, design_issues, recommendations,
        accessibility_flags.
    """
    structural_signals = coerce(structural_signals, list) or []
    constraints = coerce(constraints, dict) or {}

    kb = get_knowledge(conn)

    # 1. Match structural signals against decision rules
    matched_rules: list[dict[str, Any]] = []
    recommendations: list[dict[str, Any]] = []
    accessibility_flags: list[dict[str, Any]] = []

    if structural_signals:
        rule_matches = kb.match_structural_signals(structural_signals)

        # Apply constraint filtering if constraints provided
        if constraints:
            filtered_rules = kb.filter_by_constraints(
                [rm["rule"] for rm in rule_matches], constraints
            )
            filtered_ids = {r["id"] for r in filtered_rules}
            rule_matches = [
                rm for rm in rule_matches if rm["rule"]["id"] in filtered_ids
            ]

        for rm in rule_matches:
            rule = rm["rule"]

            rule_entry: dict[str, Any] = {
                "signal": rm["signal"],
                "rule_id": rule["id"],
                "description": rule.get("description", ""),
                "priority": rule.get("priority", "medium"),
                "recommended_patterns": [
                    p.get("id", "") for p in rm.get("recommended_patterns", [])
                ],
            }
            matched_rules.append(rule_entry)

            # Build recommendations from matched patterns
            for pattern in rm.get("recommended_patterns", []):
                rec: dict[str, Any] = {
                    "pattern_id": pattern.get("id", ""),
                    "pattern_name": pattern.get("name", pattern.get("id", "")),
                    "description": pattern.get("description", ""),
                    "source_rule": rule["id"],
                }
                recommendations.append(rec)

                # Check for accessibility requirements in the pattern
                a11y_reqs = pattern.get("accessibility", {})
                if a11y_reqs:
                    accessibility_flags.append({
                        "pattern_id": pattern.get("id", ""),
                        "requirements": a11y_reqs,
                        "source": "pattern",
                    })

    # 2. Detect anti-patterns from structural signals
    design_issues: list[dict[str, Any]] = []

    for signal in structural_signals:
        sig_lower = signal.lower().strip()
        anti = _ANTI_PATTERNS.get(sig_lower)
        if anti:
            design_issues.append({
                "signal": signal,
                "issue": anti["issue"],
                "severity": anti["severity"],
                "wcag_criterion": anti.get("wcag", ""),
                "recommendation": anti["recommendation"],
            })
            accessibility_flags.append({
                "signal": signal,
                "wcag_criterion": anti.get("wcag", ""),
                "issue": anti["issue"],
                "source": "anti_pattern",
            })

    # 3. Build result
    result: dict[str, Any] = {
        "matched_rules": matched_rules,
        "design_issues": design_issues,
        "recommendations": recommendations,
        "accessibility_flags": accessibility_flags,
    }

    emit_event("audit_design", {
        "description": description[:120],
        "signals": structural_signals,
        "matched_rules_count": len(matched_rules),
        "design_issues_count": len(design_issues),
        "accessibility_flags_count": len(accessibility_flags),
    })

    return result
