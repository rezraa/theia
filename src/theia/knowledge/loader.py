# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""Knowledge loader for Theia.

Loads design_systems.json, component_patterns.json, accessibility_standards.json,
and decision_rules.json and provides pure retrieval, structural signal matching
(exact substring against decision_rules), and constraint filtering.

No fuzzy keyword matching.  No tokenization.  No Jaccard scoring.
"""

from __future__ import annotations

import json
from pathlib import Path

_KNOWLEDGE_DIR = Path(__file__).parent

_PRIORITY_RANK: dict[str, int] = {"high": 0, "medium": 1, "low": 2}


class KnowledgeLoader:
    """Loads and queries the Theia knowledge base (design systems,
    component patterns, accessibility standards, decision rules).

    All matching is structural / exact / data-driven.  No fuzzy keyword overlap.
    """

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def __init__(self, knowledge_dir: Path | None = None) -> None:
        self._dir = knowledge_dir or _KNOWLEDGE_DIR

        with open(self._dir / "design_systems.json", encoding="utf-8") as f:
            self._design_systems_data = json.load(f)

        with open(self._dir / "component_patterns.json", encoding="utf-8") as f:
            self._component_patterns_data = json.load(f)

        with open(self._dir / "accessibility_standards.json", encoding="utf-8") as f:
            self._accessibility_standards_data = json.load(f)

        with open(self._dir / "decision_rules.json", encoding="utf-8") as f:
            self._decision_rules_data = json.load(f)

        # Build convenience lists.
        self._design_systems: list[dict] = self._design_systems_data["systems"]
        self._component_patterns: list[dict] = self._component_patterns_data["patterns"]
        self._accessibility_standards: list[dict] = self._accessibility_standards_data["standards"]
        self._decision_rules: list[dict] = self._decision_rules_data["rules"]

        # Index: id -> dict
        self._design_system_index: dict[str, dict] = {
            s["id"]: s for s in self._design_systems
        }
        self._component_pattern_index: dict[str, dict] = {
            p["id"]: p for p in self._component_patterns
        }
        self._accessibility_index: dict[str, dict] = {
            a["id"]: a for a in self._accessibility_standards
        }
        self._rule_index: dict[str, dict] = {
            r["id"]: r for r in self._decision_rules
        }

        # Build rule signal index: normalised structural_signal -> rule
        # Each rule has a list of structural_signals; index each one.
        self._rule_signal_pairs: list[tuple[str, dict]] = []
        for rule in self._decision_rules:
            for signal in rule.get("structural_signals", []):
                normalised = signal.lower().strip()
                if normalised:
                    self._rule_signal_pairs.append((normalised, rule))

    # ------------------------------------------------------------------
    # Pure retrieval — design systems
    # ------------------------------------------------------------------

    def get_design_system(self, system_id: str) -> dict | None:
        """Get a design system by ID."""
        return self._design_system_index.get(system_id)

    def get_design_systems_by_category(self, category: str) -> list[dict]:
        """Get all design systems in a given category."""
        return [s for s in self._design_systems if s.get("category") == category]

    def list_design_system_categories(self) -> list[str]:
        """List all unique design system categories."""
        cats: set[str] = set()
        for s in self._design_systems:
            cat = s.get("category")
            if cat:
                cats.add(cat)
        return sorted(cats)

    # ------------------------------------------------------------------
    # Pure retrieval — component patterns
    # ------------------------------------------------------------------

    def get_component_pattern(self, pattern_id: str) -> dict | None:
        """Get a component pattern by ID."""
        return self._component_pattern_index.get(pattern_id)

    def get_components_by_category(self, category: str) -> list[dict]:
        """Get all component patterns in a given category."""
        return [p for p in self._component_patterns if p.get("category") == category]

    def list_component_categories(self) -> list[str]:
        """List all unique component pattern categories."""
        cats: set[str] = set()
        for p in self._component_patterns:
            cat = p.get("category")
            if cat:
                cats.add(cat)
        return sorted(cats)

    # ------------------------------------------------------------------
    # Pure retrieval — accessibility standards
    # ------------------------------------------------------------------

    def get_accessibility_criterion(self, criterion_id: str) -> dict | None:
        """Get an accessibility criterion by ID."""
        return self._accessibility_index.get(criterion_id)

    def get_criteria_by_level(self, level: str) -> list[dict]:
        """Get all accessibility criteria at a given level (A, AA, AAA)."""
        return [a for a in self._accessibility_standards if a.get("level") == level]

    def get_criteria_by_principle(self, principle: str) -> list[dict]:
        """Get all accessibility criteria for a given principle
        (perceivable, operable, understandable, robust)."""
        return [
            a for a in self._accessibility_standards
            if a.get("principle", "").lower() == principle.lower()
        ]

    # ------------------------------------------------------------------
    # Pure retrieval — decision rules
    # ------------------------------------------------------------------

    def get_rule(self, rule_id: str) -> dict | None:
        """Get a decision rule by ID."""
        return self._rule_index.get(rule_id)

    def get_rules_by_category(self, category: str) -> list[dict]:
        """Get all decision rules in a given category."""
        return [r for r in self._decision_rules if r.get("category") == category]

    # ------------------------------------------------------------------
    # Structural matching — exact against decision_rules.json
    # ------------------------------------------------------------------

    def match_structural_signals(self, signals: list[str]) -> list[dict]:
        """Given structural signals identified by the agent, find matching
        decision rules.

        Matching is exact substring on the ``structural_signals`` field of
        each rule -- NOT fuzzy keyword overlap.  For each input signal, checks
        if any of the rule's structural_signals contain it as a substring, or
        vice versa (case-insensitive).

        Returns matching rules augmented with resolved pattern details,
        sorted by priority (high > medium > low)::

            [{"rule": {...}, "signal": "...",
              "recommended_patterns": [...],
              "alternatives": [...]}]
        """
        if not signals:
            return []

        results: list[dict] = []
        seen_rule_ids: set[str] = set()

        for signal in signals:
            signal_lower = signal.lower().strip()
            if not signal_lower:
                continue

            for rule_signal, rule in self._rule_signal_pairs:
                if rule["id"] in seen_rule_ids:
                    continue

                # Exact substring match: the agent's signal appears in the
                # rule's structural_signal, or vice versa.
                if signal_lower in rule_signal or rule_signal in signal_lower:
                    seen_rule_ids.add(rule["id"])

                    # Resolve recommended patterns
                    rec_pattern_ids = rule.get("recommended_patterns", [])
                    rec_patterns = []
                    for pid in rec_pattern_ids:
                        pat = self.get_component_pattern(pid)
                        if pat:
                            rec_patterns.append(pat)
                        else:
                            rec_patterns.append({"id": pid, "name": pid})

                    # Resolve alternatives
                    alt_ids = rule.get("alternatives", [])
                    alternatives = []
                    for alt_id in alt_ids:
                        alt_pat = self.get_component_pattern(alt_id)
                        if alt_pat:
                            alternatives.append(alt_pat)
                        else:
                            alternatives.append({"id": alt_id, "name": alt_id})

                    results.append({
                        "rule": rule,
                        "signal": signal,
                        "recommended_patterns": rec_patterns,
                        "alternatives": alternatives,
                    })

        # Sort by priority: high=0, medium=1, low=2
        results.sort(
            key=lambda r: _PRIORITY_RANK.get(
                r["rule"].get("priority", "low"), 2
            )
        )

        return results

    # ------------------------------------------------------------------
    # Constraint filtering
    # ------------------------------------------------------------------

    def filter_by_constraints(
        self,
        rules: list[dict],
        constraints: dict,
    ) -> list[dict]:
        """Filter rules by constraints.

        Removes rules whose ``constraints.avoid_when`` conditions match the
        provided constraints.  Each key in *constraints* is checked against
        the rule's ``avoid_when`` text (case-insensitive substring match).

        Args:
            rules: List of rule dicts (each must have ``constraints``
                with an ``avoid_when`` key).
            constraints: Dict of constraint signals.  Values that are
                truthy strings are checked against each rule's avoid_when.

        Returns:
            List of rules that survived filtering (avoid_when did not match).
        """
        if not constraints:
            return list(rules)

        # Gather constraint values as lowercase strings for matching.
        constraint_signals: list[str] = []
        for value in constraints.values():
            if isinstance(value, str) and value.strip():
                constraint_signals.append(value.lower().strip())
            elif isinstance(value, bool) and value:
                pass  # boolean flags don't have text to match

        if not constraint_signals:
            return list(rules)

        surviving: list[dict] = []

        for rule in rules:
            avoid_when = rule.get("constraints", {}).get("avoid_when", "")
            if not avoid_when:
                surviving.append(rule)
                continue

            avoid_lower = avoid_when.lower()
            excluded = False
            for cs in constraint_signals:
                if cs in avoid_lower or avoid_lower in cs:
                    excluded = True
                    break

            if not excluded:
                surviving.append(rule)

        return surviving

    # ------------------------------------------------------------------
    # Compact index (for council awareness)
    # ------------------------------------------------------------------

    def get_compact_index(self) -> dict:
        """Return a lightweight summary of all knowledge for agent awareness.

        Includes category counts and IDs only, not full data.
        """
        # Design system categories
        ds_categories: dict[str, list[str]] = {}
        for s in self._design_systems:
            cat = s.get("category", "uncategorised")
            ds_categories.setdefault(cat, []).append(s["id"])

        # Component pattern categories
        cp_categories: dict[str, list[str]] = {}
        for p in self._component_patterns:
            cat = p.get("category", "uncategorised")
            cp_categories.setdefault(cat, []).append(p["id"])

        # Accessibility by level
        a11y_levels: dict[str, list[str]] = {}
        for a in self._accessibility_standards:
            level = a.get("level", "unknown")
            a11y_levels.setdefault(level, []).append(a["id"])

        # Decision rules by category
        rule_categories: dict[str, list[str]] = {}
        for r in self._decision_rules:
            cat = r.get("category", "uncategorised")
            rule_categories.setdefault(cat, []).append(r["id"])

        return {
            "design_systems": {
                "total": len(self._design_systems),
                "categories": {k: len(v) for k, v in ds_categories.items()},
                "ids": [s["id"] for s in self._design_systems],
            },
            "component_patterns": {
                "total": len(self._component_patterns),
                "categories": {k: len(v) for k, v in cp_categories.items()},
                "ids": [p["id"] for p in self._component_patterns],
            },
            "accessibility_standards": {
                "total": len(self._accessibility_standards),
                "levels": {k: len(v) for k, v in a11y_levels.items()},
                "ids": [a["id"] for a in self._accessibility_standards],
            },
            "decision_rules": {
                "total": len(self._decision_rules),
                "categories": {k: len(v) for k, v in rule_categories.items()},
                "ids": [r["id"] for r in self._decision_rules],
            },
        }
