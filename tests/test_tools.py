# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""Tests for Theia tools — audit_design, plan_design_system, spec_component,
evaluate_accessibility, log_decision."""

from __future__ import annotations

import pytest

from theia.tools.audit_design import audit_design
from theia.tools.plan_design_system import plan_design_system
from theia.tools.spec_component import spec_component
from theia.tools.evaluate_accessibility import evaluate_accessibility
from theia.tools.log_decision import log_decision


# ===================================================================
# TestAuditDesign
# ===================================================================

class TestAuditDesign:
    """Test the design audit tool."""

    def test_matches_dashboard_signals(self):
        result = audit_design(
            description="Admin dashboard with metrics",
            structural_signals=["dashboard with metric cards and data tables"],
        )
        assert len(result["matched_rules"]) >= 1
        rule_ids = [r["rule_id"] for r in result["matched_rules"]]
        assert "rule_dashboard_layout" in rule_ids

    def test_matches_form_signals(self):
        result = audit_design(
            description="User registration form",
            structural_signals=["form with 10+ fields"],
        )
        assert len(result["matched_rules"]) >= 1
        rule_ids = [r["rule_id"] for r in result["matched_rules"]]
        assert "rule_long_form" in rule_ids

    def test_returns_design_issues(self):
        result = audit_design(
            description="Status indicator using colour",
            structural_signals=["color-only", "no-labels"],
        )
        assert len(result["design_issues"]) >= 2
        issues = [d["issue"] for d in result["design_issues"]]
        assert "Color used as sole indicator" in issues
        assert "Form inputs missing visible labels" in issues

    def test_empty_signals(self):
        result = audit_design(
            description="Some interface",
            structural_signals=[],
        )
        assert result["matched_rules"] == []
        assert result["design_issues"] == []
        assert result["accessibility_flags"] == []

    def test_constraint_filtering(self):
        # Dashboard rule has avoid_when containing "fewer than 3 metrics"
        result = audit_design(
            description="Admin panel",
            structural_signals=["dashboard with metric cards and data tables"],
            constraints={"context": "fewer than 3 metrics"},
        )
        # The constraint should filter out the dashboard rule
        rule_ids = [r["rule_id"] for r in result["matched_rules"]]
        assert "rule_dashboard_layout" not in rule_ids

    def test_accessibility_flags(self):
        result = audit_design(
            description="Form with colour indicators",
            structural_signals=["color-only", "no-focus-indicator"],
        )
        assert len(result["accessibility_flags"]) >= 2
        wcag_ids = [f.get("wcag_criterion") for f in result["accessibility_flags"]]
        assert "1.4.1" in wcag_ids
        assert "2.4.7" in wcag_ids

    def test_result_structure(self):
        result = audit_design(
            description="Test interface",
            structural_signals=["low-contrast"],
        )
        assert "matched_rules" in result
        assert "design_issues" in result
        assert "recommendations" in result
        assert "accessibility_flags" in result


# ===================================================================
# TestPlanDesignSystem
# ===================================================================

class TestPlanDesignSystem:
    """Test the design system planning tool."""

    def test_returns_token_architecture(self):
        result = plan_design_system(
            product_description="SaaS analytics platform",
        )
        tokens = result["token_architecture"]
        assert "spacing" in tokens
        assert "type_scale" in tokens
        assert "color" in tokens

    def test_platform_web(self):
        result = plan_design_system(
            product_description="Consumer web application",
            platforms=["web"],
        )
        strategy = result["responsive_strategy"]
        assert strategy["selected"] == "mobile-first"
        considerations = result["token_architecture"]["platform_considerations"]
        assert any("CSS" in c or "container" in c.lower() for c in considerations)

    def test_platform_mobile(self):
        result = plan_design_system(
            product_description="Mobile banking app",
            platforms=["mobile"],
        )
        considerations = result["token_architecture"]["platform_considerations"]
        assert any("thumb" in c.lower() or "swipe" in c.lower() for c in considerations)

    def test_returns_component_hierarchy(self):
        result = plan_design_system(
            product_description="Design system for enterprise product",
        )
        hierarchy = result["component_hierarchy"]
        assert "atoms" in hierarchy
        assert "molecules" in hierarchy
        assert "organisms" in hierarchy
        assert "templates" in hierarchy
        assert "pages" in hierarchy

    def test_brand_attributes(self):
        result = plan_design_system(
            product_description="Children's educational app",
            brand_attributes=["playful", "fun"],
        )
        theming = result["theming_approach"]
        assert theming["brand_attributes"] == ["playful", "fun"]
        assert theming.get("radius_style") == "rounded"
        assert theming.get("motion_style") == "expressive"

    def test_brand_professional(self):
        result = plan_design_system(
            product_description="Legal document platform",
            brand_attributes=["professional", "corporate"],
        )
        theming = result["theming_approach"]
        assert theming.get("radius_style") == "subtle"
        assert theming.get("motion_style") == "minimal"

    def test_adaptive_strategy_multi_platform(self):
        result = plan_design_system(
            product_description="Cross-platform app",
            platforms=["mobile", "desktop"],
        )
        assert result["responsive_strategy"]["selected"] == "adaptive"

    def test_desktop_first_strategy(self):
        result = plan_design_system(
            product_description="Enterprise tool",
            platforms=["desktop"],
        )
        assert result["responsive_strategy"]["selected"] == "desktop-first"


# ===================================================================
# TestSpecComponent
# ===================================================================

class TestSpecComponent:
    """Test the component specification tool."""

    def test_button_spec(self):
        result = spec_component(component_type="button")
        assert result["component"] == "button"
        assert len(result["anatomy"]) >= 2
        assert len(result["variants"]) >= 3
        assert result["accessibility"]["role"] == "button"
        assert len(result["common_mistakes"]) >= 1

    def test_input_spec(self):
        result = spec_component(component_type="input")
        assert result["component"] == "input"
        assert result["accessibility"]["role"] == "textbox"
        assert "error" in result["states"]
        assert len(result["variants"]) >= 3

    def test_unknown_component(self):
        result = spec_component(component_type="sparkle_widget_xyz")
        # Should return a basic structure, not an error
        assert result["component"] == "sparkle_widget_xyz"
        assert "anatomy" in result
        assert "states" in result
        assert "variants" in result
        assert len(result["states"]) >= 1
        assert len(result["anatomy"]) >= 1

    def test_includes_accessibility(self):
        result = spec_component(component_type="button")
        a11y = result["accessibility"]
        assert "role" in a11y
        assert "keyboard_interaction" in a11y
        assert len(a11y["keyboard_interaction"]) >= 1

    def test_includes_states(self):
        result = spec_component(component_type="button")
        states = result["states"]
        assert "hover" in states or "active" in states
        assert "focus" in states or "focus-visible" in states
        assert "disabled" in states

    def test_includes_responsive(self):
        result = spec_component(component_type="button", platform="web")
        responsive = result["responsive_behavior"]
        assert len(responsive) >= 1
        assert responsive[0]["platform"] == "web"
        assert "breakpoints" in responsive[0]

    def test_modal_spec(self):
        result = spec_component(component_type="modal")
        assert result["accessibility"]["role"] == "dialog"
        assert "Escape to close" in result["accessibility"]["keyboard_interaction"]

    def test_design_tokens_generated(self):
        result = spec_component(component_type="button")
        tokens = result["design_tokens"]
        assert any("button-background" in t for t in tokens)
        assert any("button-foreground" in t for t in tokens)


# ===================================================================
# TestEvaluateAccessibility
# ===================================================================

class TestEvaluateAccessibility:
    """Test the accessibility evaluation tool."""

    def test_level_a_criteria(self):
        result = evaluate_accessibility(
            component_or_page_description="Simple text page",
            target_level="A",
        )
        assert result["target_level"] == "A"
        assert result["criteria_checked"] >= 30

    def test_level_aa_criteria(self):
        result = evaluate_accessibility(
            component_or_page_description="Standard web page",
            target_level="AA",
        )
        assert result["target_level"] == "AA"
        # AA should include A + AA criteria
        assert result["criteria_checked"] >= 50

    def test_detects_color_only(self):
        result = evaluate_accessibility(
            component_or_page_description="Status indicator uses color only to show state",
        )
        assert len(result["violations"]) >= 1
        wcag_ids = [v["wcag_criterion"] for v in result["violations"]]
        assert "1.4.1" in wcag_ids

    def test_detects_missing_labels(self):
        result = evaluate_accessibility(
            component_or_page_description="Form with no label for each input, placeholder only",
        )
        assert len(result["violations"]) >= 1
        wcag_ids = [v["wcag_criterion"] for v in result["violations"]]
        assert "1.3.1" in wcag_ids

    def test_compliance_score(self):
        result = evaluate_accessibility(
            component_or_page_description="Well built page with aria-label and focus-visible",
        )
        score = result["compliance_score"]
        assert 0.0 <= score <= 1.0

    def test_returns_recommendations(self):
        result = evaluate_accessibility(
            component_or_page_description="Form with color only indicators and no label",
        )
        assert len(result["recommendations"]) >= 1
        for rec in result["recommendations"]:
            assert "action" in rec
            assert "wcag_criterion" in rec

    def test_positive_signals_detected(self):
        result = evaluate_accessibility(
            component_or_page_description="Component with aria-label and focus-visible styles",
        )
        assert len(result["passes"]) >= 1
        pass_criteria = [p["wcag_criterion"] for p in result["passes"]]
        assert "1.1.1" in pass_criteria or "2.4.7" in pass_criteria

    def test_automated_checks_included(self):
        result = evaluate_accessibility(
            component_or_page_description="Any page",
        )
        assert len(result["automated_checks"]) >= 5
        tool_names = [c["tool"] for c in result["automated_checks"]]
        assert "axe-core" in tool_names

    def test_violation_reduces_score(self):
        clean = evaluate_accessibility(
            component_or_page_description="Simple text paragraph",
        )
        dirty = evaluate_accessibility(
            component_or_page_description="Form with color only status, no label, low contrast text",
        )
        assert dirty["compliance_score"] < clean["compliance_score"]


# ===================================================================
# TestLogDecision
# ===================================================================

class TestLogDecision:
    """Test the decision logging tool."""

    def test_logs_decision(self, tmp_data_dir):
        result = log_decision(
            decision_type="component",
            context="Choosing button style for primary actions",
            choice_made="Filled button with high contrast",
            alternatives_considered=["Ghost button", "Outlined button"],
            rationale="Higher visibility for primary CTAs",
        )
        assert result["recorded"] is True
        assert result["decision_type"] == "component"

    def test_returns_decision_id(self, tmp_data_dir):
        result = log_decision(
            decision_type="color",
            context="Selecting primary brand colour",
            choice_made="Blue #0066CC",
        )
        assert "decision_id" in result
        assert isinstance(result["decision_id"], str)
        assert result["decision_id"].startswith("d-")

    def test_valid_decision_types(self, tmp_data_dir):
        for dt in ["component", "layout", "typography", "color", "accessibility"]:
            result = log_decision(
                decision_type=dt,
                context="Test context",
                choice_made="Test choice",
            )
            assert result["decision_type"] == dt

    def test_invalid_type_normalises_to_other(self, tmp_data_dir):
        result = log_decision(
            decision_type="nonexistent_category",
            context="Test",
            choice_made="Test",
        )
        assert result["decision_type"] == "other"

    def test_timestamp(self, tmp_data_dir):
        result = log_decision(
            decision_type="pattern",
            context="Test",
            choice_made="Test",
        )
        assert "timestamp" in result
        assert isinstance(result["timestamp"], str)
        # ISO format contains T separator
        assert "T" in result["timestamp"]

    def test_decision_persisted_to_file(self, tmp_data_dir):
        log_decision(
            decision_type="spacing",
            context="Spacing scale",
            choice_made="8px base unit",
        )
        decisions_file = tmp_data_dir / "decisions.jsonl"
        assert decisions_file.exists()
        lines = decisions_file.read_text().strip().splitlines()
        assert len(lines) >= 1
