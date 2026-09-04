# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""Tests for Theia tools — audit_design, plan_design_system, spec_component,
evaluate_accessibility, log_decision."""

from __future__ import annotations

import pytest

from theia.tools.plan_design_system import plan_design_system
from theia.tools.evaluate_accessibility import evaluate_accessibility
from theia.tools.log_decision import log_decision


# ===================================================================
# TestAuditDesign — RETIRED (S3, story-5b040677; Directive 10/12)
# ===================================================================
# The legacy prose-substring TestAuditDesign class was KILLED-WITH-REASON and
# superseded (strictly stronger) by tests/test_audit_design.py, which exercises the
# Shape-C retrofit: signal-id interface, the four-state fail-closed envelope, issues
# reasoned over each retrieved component's OWN fields, the populated accessibility
# field (the accessibility_requirements read fix), and the before/after BAR-2 delta.
# The five superseded tests, each named with what replaced it:
#   * test_matches_dashboard_signals / test_matches_form_signals -> the dead
#     ``matched_rules`` rule path is dropped (test_matched_rules_dropped).
#   * test_returns_design_issues / test_accessibility_flags -> the hardcoded
#     _ANTI_PATTERNS island exact-slug detector is off the runtime path; issues +
#     a11y flags come from retrieved components' own fields
#     (test_island_slug_tokens_no_longer_answered, TestRedFirstProbe).
#   * test_constraint_filtering -> filter_by_constraints is not on the tool path;
#     the dormant facet gate tiers, never filters (TestGateDormant).
#   * test_empty_signals / test_result_structure -> the new envelope contract
#     (TestEnvelopeFailClosed, TestContract).
# Not a silent drop: the substring interface is retired (no alias shim), so these
# would not even call. The signal-id interface lives in tests/test_audit_design.py.


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

# ===================================================================
# TestSpecComponent — RETIRED (S4, story-57031f25; Directive 10/12)
# ===================================================================
# The legacy archetype/husk TestSpecComponent class was KILLED-WITH-REASON and
# superseded (strictly stronger) by tests/test_spec_component.py, which exercises the
# SEED-FROM-NODE retrofit: resolve id -> the component's OWN signals -> one hydrate ->
# the component's OWN rich fields through the four-state fail-closed envelope, the
# accessibility_requirements read fix, the nearest path, and the BAR-2 husk delta.
# The eight superseded tests, each named with what replaced it:
#   * test_button_spec / test_input_spec / test_includes_accessibility / test_modal_spec
#     -> the hardcoded _COMPONENT_ARCHETYPES a11y-role dict is deleted; the a11y surface
#     is the component's OWN accessibility_requirements list
#     (test_archetype_role_interface_retired, TestRedFirstNorthStar).
#   * test_unknown_component -> an unknown type fails closed, no ['container','content']
#     husk (test_unknown_no_longer_returns_a_structure, TestEnvelopeFailClosed).
#   * test_includes_states -> states are the component's OWN corpus field
#     (TestSeedFromNode.test_every_component_self_resolves_at_hit).
#   * test_includes_responsive -> responsive_behavior is the corpus field; the platform
#     knob is retired (test_platform_knob_retired, test_own_responsive_and_tokens_not_computed).
#   * test_design_tokens_generated -> design_tokens_needed is the corpus field, not a
#     name-generated list (test_own_responsive_and_tokens_not_computed).
# Not a silent drop: the platform param is retired (no shim), so test_includes_responsive
# would not even call. The signal-id/SEED interface lives in tests/test_spec_component.py.


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
