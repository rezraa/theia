# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""Tests for Theia knowledge base — design systems, component patterns,
accessibility standards, decision rules."""

from __future__ import annotations

import pytest

from theia.knowledge.loader import KnowledgeLoader


@pytest.fixture(scope="module")
def kb():
    return KnowledgeLoader()


class TestKnowledgeLoading:
    """Verify all JSON files load and index correctly."""

    def test_loads_design_systems(self, kb):
        systems = kb._design_systems
        assert len(systems) >= 50, f"Expected 50+ design systems, got {len(systems)}"

    def test_loads_component_patterns(self, kb):
        patterns = kb._component_patterns
        assert len(patterns) >= 60, f"Expected 60+ component patterns, got {len(patterns)}"

    def test_loads_accessibility_standards(self, kb):
        standards = kb._accessibility_standards
        assert len(standards) >= 50, f"Expected 50+ accessibility standards, got {len(standards)}"

    def test_loads_decision_rules(self, kb):
        rules = kb._decision_rules
        assert len(rules) >= 40, f"Expected 40+ decision rules, got {len(rules)}"

    def test_design_systems_have_required_fields(self, kb):
        for s in kb._design_systems:
            assert "id" in s, f"Design system missing id: {s}"
            assert "name" in s, f"Design system missing name: {s.get('id')}"

    def test_component_patterns_have_required_fields(self, kb):
        for p in kb._component_patterns:
            assert "id" in p, f"Pattern missing id: {p}"
            assert "name" in p, f"Pattern missing name: {p.get('id')}"
            assert "category" in p, f"Pattern missing category: {p.get('id')}"


class TestDesignSystemRetrieval:
    """Test design system lookup and filtering."""

    def test_get_design_system(self, kb):
        s = kb.get_design_system("atomic_design")
        assert s is not None
        assert s["id"] == "atomic_design"

    def test_get_design_system_not_found(self, kb):
        s = kb.get_design_system("nonexistent_system_xyz")
        assert s is None

    def test_get_design_systems_by_category(self, kb):
        cats = kb.list_design_system_categories()
        assert len(cats) >= 3
        # Pick a category and check filtering
        systems = kb.get_design_systems_by_category(cats[0])
        assert len(systems) >= 1
        for s in systems:
            assert s.get("category") == cats[0]


class TestComponentPatternRetrieval:
    """Test component pattern lookup and filtering."""

    def test_get_component_pattern(self, kb):
        p = kb.get_component_pattern("navbar")
        assert p is not None
        assert p["id"] == "navbar"

    def test_get_component_pattern_not_found(self, kb):
        p = kb.get_component_pattern("nonexistent_pattern_xyz")
        assert p is None

    def test_get_components_by_category(self, kb):
        cats = kb.list_component_categories()
        assert len(cats) >= 3
        for cat in cats:
            components = kb.get_components_by_category(cat)
            assert len(components) >= 1
            for c in components:
                assert c.get("category") == cat


class TestAccessibilityRetrieval:
    """Test accessibility criterion lookup and filtering."""

    def test_get_accessibility_criterion(self, kb):
        c = kb.get_accessibility_criterion("wcag_1_1_1")
        assert c is not None
        assert c["id"] == "wcag_1_1_1"

    def test_get_accessibility_criterion_not_found(self, kb):
        c = kb.get_accessibility_criterion("wcag_99_99_99")
        assert c is None

    def test_get_criteria_by_level(self, kb):
        a_criteria = kb.get_criteria_by_level("A")
        assert len(a_criteria) >= 20
        for c in a_criteria:
            assert c.get("level") == "A"

        aa_criteria = kb.get_criteria_by_level("AA")
        assert len(aa_criteria) >= 15
        for c in aa_criteria:
            assert c.get("level") == "AA"

    def test_get_criteria_by_principle(self, kb):
        perceivable = kb.get_criteria_by_principle("perceivable")
        assert len(perceivable) >= 10
        for c in perceivable:
            assert c.get("principle", "").lower() == "perceivable"

        operable = kb.get_criteria_by_principle("operable")
        assert len(operable) >= 10
        for c in operable:
            assert c.get("principle", "").lower() == "operable"


class TestStructuralSignalMatching:
    """Test decision rule matching against structural signals."""

    def test_match_structural_signals(self, kb):
        results = kb.match_structural_signals(
            ["dashboard with metric cards and data tables"]
        )
        assert len(results) >= 1
        rule_ids = [r["rule"]["id"] for r in results]
        assert "rule_dashboard_layout" in rule_ids

    def test_match_no_signals(self, kb):
        results = kb.match_structural_signals([])
        assert results == []

    def test_match_returns_recommended_patterns(self, kb):
        results = kb.match_structural_signals(
            ["dashboard with metric cards and data tables"]
        )
        assert len(results) >= 1
        # Each result should have recommended_patterns list
        for r in results:
            assert "recommended_patterns" in r
            assert isinstance(r["recommended_patterns"], list)

    def test_match_multiple_signals(self, kb):
        results = kb.match_structural_signals([
            "dashboard with metric cards and data tables",
            "form with 10+ fields",
        ])
        rule_ids = [r["rule"]["id"] for r in results]
        assert "rule_dashboard_layout" in rule_ids
        assert "rule_long_form" in rule_ids


class TestConstraintFiltering:
    """Test constraint-based rule filtering."""

    def test_filter_by_constraints(self, kb):
        # Get the dashboard rule which has avoid_when
        rule = kb.get_rule("rule_dashboard_layout")
        assert rule is not None
        rules = [rule]

        # Filter with a constraint that matches avoid_when
        surviving = kb.filter_by_constraints(
            rules, {"context": "fewer than 3 metrics"}
        )
        assert len(surviving) == 0

    def test_filter_no_constraints(self, kb):
        rule = kb.get_rule("rule_dashboard_layout")
        assert rule is not None
        rules = [rule]

        surviving = kb.filter_by_constraints(rules, {})
        assert len(surviving) == 1

    def test_filter_non_matching_constraint(self, kb):
        rule = kb.get_rule("rule_dashboard_layout")
        assert rule is not None
        rules = [rule]

        surviving = kb.filter_by_constraints(
            rules, {"context": "completely unrelated constraint"}
        )
        assert len(surviving) == 1


class TestCompactIndex:
    """Test the compact index summary."""

    def test_compact_index(self, kb):
        idx = kb.get_compact_index()
        assert "design_systems" in idx
        assert "component_patterns" in idx
        assert "accessibility_standards" in idx
        assert "decision_rules" in idx

        assert idx["design_systems"]["total"] >= 50
        assert idx["component_patterns"]["total"] >= 60
        assert idx["accessibility_standards"]["total"] >= 50
        assert idx["decision_rules"]["total"] >= 40

    def test_compact_index_has_ids(self, kb):
        idx = kb.get_compact_index()
        assert len(idx["design_systems"]["ids"]) >= 50
        assert len(idx["component_patterns"]["ids"]) >= 60

    def test_compact_index_has_categories(self, kb):
        idx = kb.get_compact_index()
        assert len(idx["design_systems"]["categories"]) >= 3
        assert len(idx["component_patterns"]["categories"]) >= 3
        assert len(idx["accessibility_standards"]["levels"]) >= 2
