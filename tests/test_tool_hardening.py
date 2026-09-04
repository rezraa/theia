# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""Hardening tests for Theia's coerce/coerce_or_raise contract.

Covers the new container-default behaviour of ``coerce`` (returns *default*
on mismatch, not ``[]``/``{}``), the persist-safe ``coerce_or_raise`` backing
``log_decision``'s ``alternatives_considered``, and that the existing tool
call sites still hand containers downstream (no None-leak regression).
"""

from __future__ import annotations

import pytest

from theia.tools._shared import coerce, coerce_or_raise
from theia.tools.audit_design import audit_design
from theia.tools.plan_design_system import plan_design_system
from theia.tools.spec_component import spec_component
from theia.tools.log_decision import log_decision


class TestCoerce:
    """The new contract: *default* (None unless supplied) on any mismatch."""

    def test_json_string_to_list(self):
        assert coerce("[1, 2]", list) == [1, 2]

    def test_json_string_to_dict(self):
        assert coerce('{"k": 1}', dict) == {"k": 1}

    def test_native_passthrough(self):
        assert coerce(["a"], list) == ["a"]
        assert coerce({"k": 1}, dict) == {"k": 1}

    def test_none_returns_default(self):
        assert coerce(None, list) is None
        assert coerce(None, list, default=[]) == []

    def test_wrong_type_returns_default_not_empty_container(self):
        # The old version returned [] here; the new contract returns *default*.
        assert coerce(5, list) is None
        assert coerce(5, list, default=[]) == []

    def test_bare_nonjson_string_returns_default(self):
        assert coerce("nope", list) is None

    def test_idiom_or_empty_still_yields_container(self):
        # The call-site idiom every tool uses must still produce a container.
        assert (coerce(5, list) or []) == []
        assert (coerce("nope", dict) or {}) == {}


class TestCoerceOrRaise:
    """Persist-safe variant used by log_decision's alternatives_considered."""

    def test_none_returns_empty_default(self):
        assert coerce_or_raise(None, list, []) == []

    def test_native_list_passthrough(self):
        assert coerce_or_raise(["a", "b"], list, []) == ["a", "b"]

    def test_json_array_string(self):
        assert coerce_or_raise('["a", "b"]', list, []) == ["a", "b"]

    def test_nonempty_wrong_type_raises(self):
        with pytest.raises(TypeError):
            coerce_or_raise({"a": 1}, list, [])

    def test_bare_nonjson_string_raises(self):
        with pytest.raises(TypeError):
            coerce_or_raise("solo", list, [])


class TestToolCallSitesNoNoneLeak:
    """Wrong-typed/absent container args must not leak None into the tools."""

    def test_audit_design_wrong_type_signals(self):
        # matched_signal_ids as a bare string -> coerce(...) or [] -> [] -> abstain.
        result = audit_design(description="x", matched_signal_ids="oops")
        assert result["retrieval_state"] == "no_match"
        assert result["design_issues"] == []
        assert result["accessibility_flags"] == []

    def test_audit_design_wrong_type_constraints(self):
        # constraints as a bare string -> coerce(...) or {} -> {}; junk ids abstain.
        result = audit_design(
            description="x",
            matched_signal_ids=["color-only"],
            constraints="prod",
        )
        assert isinstance(result, dict)
        assert result["constraints_analyzed"] == {}

    def test_plan_design_system_none_platforms_defaults_web(self):
        result = plan_design_system(product_description="a CRM", platforms=None)
        assert result["responsive_strategy"]["target_platforms"] == ["web"]

    def test_plan_design_system_wrong_type_platforms_defaults_web(self):
        result = plan_design_system(product_description="a CRM", platforms=5)
        assert result["responsive_strategy"]["target_platforms"] == ["web"]

    def test_spec_component_wrong_type_variants_no_crash(self):
        # bare call site: coerce(variants_needed, list) or [] -> [].
        result = spec_component(component_type="button", variants_needed="bad")
        assert isinstance(result["variants"], list)
        assert len(result["variants"]) >= 1


class TestLogDecisionPersistedField:
    """alternatives_considered is persisted -> coerce_or_raise contract."""

    def test_none_alternatives_ok(self, tmp_data_dir):
        result = log_decision(
            decision_type="component",
            context="ctx",
            choice_made="A",
            alternatives_considered=None,
        )
        assert result["recorded"] is True

    def test_list_alternatives_ok(self, tmp_data_dir):
        result = log_decision(
            decision_type="component",
            context="ctx",
            choice_made="A",
            alternatives_considered=["B", "C"],
        )
        assert result["recorded"] is True

    def test_json_string_alternatives_ok(self, tmp_data_dir):
        result = log_decision(
            decision_type="component",
            context="ctx",
            choice_made="A",
            alternatives_considered='["B", "C"]',
        )
        assert result["recorded"] is True

    def test_nonempty_wrong_type_alternatives_raises(self, tmp_data_dir):
        # A dict where a list is expected must fail loud, not persist [].
        with pytest.raises(TypeError):
            log_decision(
                decision_type="component",
                context="ctx",
                choice_made="A",
                alternatives_considered={"not": "a list"},
            )
