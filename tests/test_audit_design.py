# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""audit_design wired onto the Shape-C engine — story-5b040677 (council 3e6eeeab).

The FIRST Theia concern tool retrofitted onto the shared engine (analyze_architecture
template). It retrieves through one ``kb.hydrate`` call (the proven four-state,
fail-closed envelope) and reasons one entry per retrieved component over that
component's OWN fields — ``common_mistakes`` / ``anatomy`` / ``states`` (the design
issue) and ``accessibility_requirements`` (the accessibility flag) — with NO
hardcoded ``_ANTI_PATTERNS`` island read on the runtime path and NO dead
``matched_rules`` rule leg. It FIXES the legacy ``pattern.get('accessibility')``
field-name bug (the corpus field is ``accessibility_requirements``).

This is the one home for the rebuilt tool's proofs. It carries:

* the RED-first NORTH-STAR probe — the AC's problem-language probe ('cards showing
  KPIs above a table' / 'status shown only by hue' / 'popup that traps keyboard
  focus'), recognised into signal ids, now returns non-empty matched components AND
  a populated accessibility field, where the pinned pre-edit output was fully empty;
* the field-name-bug fix proven (component.get('accessibility') is None on the
  corpus; the flags come from accessibility_requirements) — the "field read
  reverted to 'accessibility' -> RED" mutation, encoded;
* the "retrieval off -> RED" mutation, encoded (hydrate abstains -> empty result);
* the legacy tests KILLED-WITH-REASON (Directive 10/12): the island exact-slug
  detector, the dead matched_rules rule path, the old prose-substring interface;
* BAR-2 — the before/after delta against the pinned pre-edit output, and
  through-tool == direct-hydrate equivalence, with the win landing in the
  problem-language (PB) register the matcher scored 0 on;
* the envelope fail-closed states, determinism (incl. a fresh loader), the caller-
  boundary ceilings, the S6 deletion of the _ANTI_PATTERNS island, and the deep-freeze
  that keeps the singleton corpus uncorrupted through the tool.

Firewall: imports only theia.* . Never opens the live Othrys DB.
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path

import pytest

import theia.tools._shared as _shared
from theia.knowledge.loader import DANGLING, HIT, NO_MATCH, KnowledgeLoader, _signal_id
from theia.tools._shared import (
    _MAX_CONSTRAINT_VALUE_LEN,
    _MAX_CONSTRAINTS,
    _MAX_DESCRIPTION_LEN,
    _MAX_MATCHED_SIGNALS,
)
from theia.tools.audit_design import audit_design

# The tool module's source path (via the function, since the submodule name is
# shadowed by the re-exported function in theia.tools.__init__).
_AUDIT_SRC = Path(inspect.getsourcefile(audit_design))
_PIN = json.loads(
    (Path(__file__).parent / "data" / "baseline_audit_design_pinned.json").read_text(encoding="utf-8")
)

DESC = "context/telemetry only"

# The AC's measured-empty probe: three problem-language (PB-register) phrasings the
# legacy matcher scored 0 on. Recognition (query prose -> component) is the LLM's job
# in production (get_signal_index.py); these are Theia's gold-blind recognitions of
# the probe onto the components each phrase describes.
_PROBE = ["cards showing KPIs above a table", "status shown only by hue",
          "popup that traps keyboard focus"]
_PROBE_COMPONENTS = ["stat_card", "data_table", "badge", "alert", "modal", "dialog"]


@pytest.fixture()
def kb() -> KnowledgeLoader:
    _shared._knowledge = None
    return _shared.get_knowledge(conn=None)


def _probe_signal_ids(kb: KnowledgeLoader) -> list[str]:
    """Recognised signal ids for the AC probe: each probe phrase -> the component(s) it
    describes -> those components' own signal ids (seed-from-node). Derived from the
    live index so the proof tracks the corpus, never a hand-frozen id list."""
    sids: set[str] = set()
    for cid in _PROBE_COMPONENTS:
        sids.update(kb.signal_ids_for(cid))
    return sorted(sids)


def _issue_ids(res: dict) -> list[str]:
    return [d["component_id"] for d in res["design_issues"]]


def _fresh_call(**kwargs) -> dict:
    _shared._knowledge = None
    return audit_design(**kwargs)


# ===================================================================
# RED-FIRST — the NORTH STAR probe: dead-empty -> live, populated a11y
# ===================================================================

class TestRedFirstProbe:
    def test_probe_lifts_from_pinned_empty_to_non_empty_with_populated_a11y(self, kb) -> None:
        """The pinned pre-edit output on the AC probe was fully empty (matcher +
        island + the field-name bug); after the retrofit the same probe, recognised
        into signal ids, returns non-empty matched components AND a populated
        accessibility field. The measured-empty output is dead."""
        # before (pinned pre-edit, real problem-language): every container empty
        before = _PIN["cases"]["real_problem_language"]
        assert before["design_issues_count"] == 0
        assert before["accessibility_flags_count"] == 0
        assert before["matched_rules_count"] == 0
        # after: recognised ids hydrate real components with populated a11y
        res = audit_design(description="AC probe", matched_signal_ids=_probe_signal_ids(kb))
        assert res["retrieval_state"] == HIT
        assert res["design_issues"], "probe must hydrate non-empty matched components"
        assert {"stat_card", "data_table", "modal"} <= set(_issue_ids(res))
        assert res["accessibility_flags"], "accessibility field must be POPULATED"
        assert all(f["requirements"] for f in res["accessibility_flags"])

    def test_accessibility_field_read_fix_not_the_dead_field(self, kb) -> None:
        """The populated accessibility field proves the accessibility_requirements read
        fix. The legacy read pattern.get('accessibility') is None on 66/66 components,
        so reverting the read to 'accessibility' would empty the flags (the RED mutant),
        while 'accessibility_requirements' populates them."""
        res = audit_design(description=DESC, matched_signal_ids=_probe_signal_ids(kb))
        for f in res["accessibility_flags"]:
            comp = kb.get_component_pattern(f["component_id"])
            assert comp.get("accessibility") is None            # the dead field (the bug)
            assert comp["accessibility_requirements"]           # the real field
            assert f["requirements"] == comp["accessibility_requirements"]

    def test_true_miss_abstains_via_envelope_not_silent_empty(self, kb) -> None:
        """A genuine miss abstains through the envelope (empty + retrieval_state), the
        honest fail-closed state, not the old silent empty with no signal of why."""
        res = audit_design(description=DESC, matched_signal_ids=["sig-000000000000"])
        assert res["retrieval_state"] == NO_MATCH
        assert res["design_issues"] == []
        assert res["accessibility_flags"] == []
        assert res["unmatched"] == ["sig-000000000000"]

    def test_retrieval_off_is_red(self, kb, monkeypatch) -> None:
        """Mutation proof (retrieval off -> RED): force hydrate to abstain and the tool
        returns empty — the probe assertion above then fails. Binds the tool's output
        to the retrieval, not to any residual island path. audit_design resolves its
        loader via the module singleton (conn=None), so the singleton is what we patch."""
        from theia.knowledge.loader import RetrievalResult

        sids = _probe_signal_ids(kb)                         # recognise BEFORE crippling hydrate
        monkeypatch.setattr(
            kb, "hydrate",
            lambda *a, **k: RetrievalResult(state=NO_MATCH, reason="retrieval off"),
        )
        monkeypatch.setattr(_shared, "_knowledge", kb)      # audit_design's singleton
        res = audit_design(description="AC probe", matched_signal_ids=sids)
        assert res["retrieval_state"] == NO_MATCH
        assert res["design_issues"] == [] and res["accessibility_flags"] == []


# ===================================================================
# ENVELOPE — fail closed through the tool, never a husk
# ===================================================================

class TestEnvelopeFailClosed:
    def test_empty_signals_abstain(self, kb) -> None:
        res = audit_design(description=DESC, matched_signal_ids=[], constraints={"platform": "mobile"})
        assert res["retrieval_state"] == NO_MATCH
        assert res["design_issues"] == []
        assert res["recommendations"] == []
        assert res["accessibility_flags"] == []
        assert res["constraints_analyzed"] == {"platform": "mobile"}   # envelope still populated

    def test_unrecognised_signals_abstain_not_husk(self, kb) -> None:
        res = audit_design(description=DESC, matched_signal_ids=["sig-000000000000", "sig-ffffffffffff"])
        assert res["retrieval_state"] == NO_MATCH
        assert res["design_issues"] == []
        assert sorted(res["unmatched"]) == ["sig-000000000000", "sig-ffffffffffff"]

    def test_absent_concept_abstains(self, kb) -> None:
        """A concept the corpus genuinely lacks abstains, never the nearest component."""
        sid = _signal_id("Tokenization of card PAN before storage in a PCI vault")
        res = audit_design(description=DESC, matched_signal_ids=[sid])
        assert res["retrieval_state"] == NO_MATCH
        assert res["design_issues"] == []


# ===================================================================
# CONTRACT — the new output surface
# ===================================================================

class TestContract:
    def test_top_level_keys_present(self, kb) -> None:
        res = audit_design(description=DESC, matched_signal_ids=_probe_signal_ids(kb))
        for key in ("constraints_analyzed", "design_issues", "recommendations",
                    "accessibility_flags", "retrieval_state", "unmatched", "dangling"):
            assert key in res

    def test_issue_entry_shape(self, kb) -> None:
        res = audit_design(description=DESC, matched_signal_ids=_probe_signal_ids(kb))
        for d in res["design_issues"]:
            assert set(d) == {"component_id", "component_name", "gated",
                              "common_mistakes", "anatomy", "states", "retrieval"}
            assert isinstance(d["gated"], bool)
            assert d["common_mistakes"] and d["anatomy"] and d["states"]
            assert isinstance(d["retrieval"]["score"], int) and not isinstance(d["retrieval"]["score"], bool)

    def test_accessibility_flag_shape(self, kb) -> None:
        res = audit_design(description=DESC, matched_signal_ids=_probe_signal_ids(kb))
        issue_ids = set(_issue_ids(res))
        for f in res["accessibility_flags"]:
            assert set(f) == {"component_id", "component_name", "requirements"}
            assert f["component_id"] in issue_ids       # a11y flag rides its retrieved component
            assert f["requirements"]

    def test_recommendations_are_deduped_resolvable_remediation(self, kb) -> None:
        res = audit_design(description=DESC, matched_signal_ids=_probe_signal_ids(kb))
        ids = [r["pattern_id"] for r in res["recommendations"]]
        assert len(ids) == len(set(ids))               # deduped
        issue_ids = set(_issue_ids(res))
        for r in res["recommendations"]:
            assert r["pattern_id"] not in issue_ids     # excludes what is already an issue
            assert kb.get_component_pattern(r["pattern_id"]) is not None  # never a husk
            assert r["pattern_name"]

    def test_output_is_json_serializable(self, kb) -> None:
        """No _FrozenDict / tuple leaks from the hydrate boundary into the output."""
        res = audit_design(description=DESC, matched_signal_ids=_probe_signal_ids(kb))
        assert isinstance(json.loads(json.dumps(res)), dict)


# ===================================================================
# GATE — dormant on the component corpus (no avoid_when facet dicts)
# ===================================================================

class TestGateDormant:
    def test_all_gated_flags_false_no_false_control_claim(self, kb) -> None:
        """The facet gate is the S4/S5-ready seam; Theia components carry no avoid_when
        facet dict, so nothing gates. Every gated flag is False — the tier claims no
        control it does not have."""
        res = audit_design(description=DESC, matched_signal_ids=_probe_signal_ids(kb),
                           constraints={"platform": "mobile", "audience": "enterprise"})
        assert all(d["gated"] is False for d in res["design_issues"])

    def test_constraints_do_not_filter_the_retrieved_set(self, kb) -> None:
        """A matching constraint would tier (dormant here), never drop the retrieved set —
        the same components appear with and without constraints."""
        sids = _probe_signal_ids(kb)
        plain = audit_design(description=DESC, matched_signal_ids=sids)
        constrained = audit_design(description=DESC, matched_signal_ids=sids,
                                   constraints={"platform": "mobile"})
        assert set(_issue_ids(plain)) == set(_issue_ids(constrained))


# ===================================================================
# KILLED-WITH-REASON (Directive 10/12) — the superseded legacy behaviours
# ===================================================================

class TestKilledLegacy:
    def test_matched_rules_dropped(self, kb) -> None:
        """KILLED test_matches_dashboard_signals / test_matches_form_signals: they
        asserted the dead rule path populated ``matched_rules``. REPLACED: matched_rules
        is dropped from the contract (the rule leg was measured empty on real problem
        language)."""
        res = audit_design(description=DESC, matched_signal_ids=_probe_signal_ids(kb))
        assert "matched_rules" not in res

    def test_island_slug_tokens_no_longer_answered(self, kb) -> None:
        """KILLED test_returns_design_issues / test_accessibility_flags: they asserted
        the hardcoded _ANTI_PATTERNS island answered exact slug tokens ('color-only').
        REPLACED: slug tokens are not signal ids, so they abstain — the island detector
        is off the runtime path; issues come from retrieved components' own fields."""
        res = audit_design(description=DESC, matched_signal_ids=["color-only", "no-labels"])
        assert res["retrieval_state"] == NO_MATCH
        assert res["design_issues"] == []
        assert sorted(res["unmatched"]) == ["color-only", "no-labels"]

    def test_prose_substring_interface_retired(self, kb) -> None:
        """KILLED the structural_signals prose-substring interface: the parameter is
        retired (no alias shim). Passing the old kwarg is a TypeError, not a silent
        second interface."""
        with pytest.raises(TypeError):
            audit_design(description=DESC, structural_signals=["x"])   # type: ignore[call-arg]


# ===================================================================
# BAR-2 — before/after delta + through-tool == direct-hydrate; win in PB
# ===================================================================

class TestBaselineDeltaBar2:
    def test_dead_output_gone_and_issues_live(self, kb) -> None:
        """S0/pre-edit pinned the tool DEAD on real problem language: matched_rules=0
        AND design_issues=0 AND accessibility_flags=0 (three dead ends). The rebuild
        eliminates all three: on recognised signal ids the issue set is non-empty, the
        accessibility field is populated, and matched_rules is gone from the contract."""
        assert _PIN["cases"]["real_problem_language"]["matched_rules_count"] == 0
        assert _PIN["cases"]["real_problem_language"]["design_issues_count"] == 0
        assert _PIN["cases"]["real_problem_language"]["accessibility_flags_count"] == 0
        assert "matched_rules" in _PIN["_meta"]["legacy_output_keys"]
        res = audit_design(description=DESC, matched_signal_ids=_probe_signal_ids(kb))
        assert res["design_issues"] and res["accessibility_flags"]
        assert "matched_rules" not in res

    def test_through_tool_equals_direct_hydrate(self, kb) -> None:
        """The tool faithfully sits on the engine: with no gate firing, the components
        the tool reasons over are exactly hydrate's ranked components in order (the
        sibling '86/130 through-tool == direct hydrate' equivalence)."""
        sids = _probe_signal_ids(kb)
        res = audit_design(description=DESC, matched_signal_ids=sids, k=10)
        direct = [p["id"] for p in kb.hydrate(sids, k=10).patterns]
        assert _issue_ids(res) == direct

    def test_win_lands_in_problem_language_register(self, kb) -> None:
        """The delta lands in the PB (problem-language) register the matcher scored 0
        on: the AC probe is problem-language paraphrase (not verbatim corpus prose),
        the pinned matcher output on it was empty, and the tool now surfaces the real
        design components with their own accessibility requirements."""
        # the probe strings are not verbatim signal texts (they are paraphrases) ->
        # the matcher's exact-substring / island legs scored 0 (pinned empty)
        index_texts = {e["signal_text"].strip().lower() for e in kb.get_signal_index()}
        assert not any(p.strip().lower() in index_texts for p in _PROBE)   # genuine paraphrase
        res = audit_design(description="AC probe", matched_signal_ids=_probe_signal_ids(kb))
        assert res["retrieval_state"] == HIT
        assert len(res["design_issues"]) >= 3


# ===================================================================
# DETERMINISM — identical input -> identical output (fresh loader too)
# ===================================================================

class TestDeterminism:
    def test_identical_input_identical_output(self, kb) -> None:
        sids = _probe_signal_ids(kb)
        runs = [audit_design(description=DESC, matched_signal_ids=sids) for _ in range(4)]

        def sig(res):
            return ([(d["component_id"], d["retrieval"]["score"]) for d in res["design_issues"]],
                    [f["component_id"] for f in res["accessibility_flags"]],
                    [r["pattern_id"] for r in res["recommendations"]])

        base = sig(runs[0])
        for other in runs[1:]:
            assert sig(other) == base
        assert sig(_fresh_call(description=DESC, matched_signal_ids=sids)) == base


# ===================================================================
# HYPERION — named ceilings at the caller boundary; no eval/regex on input
# ===================================================================

class TestCallerBoundaryCeilings:
    def test_matched_signal_ids_bounded(self, kb) -> None:
        flood = [f"sig-{i:012x}" for i in range(_MAX_MATCHED_SIGNALS * 10)]
        res = audit_design(description=DESC, matched_signal_ids=flood)
        assert res["retrieval_state"] == NO_MATCH   # all junk; no amplification past the cap

    def test_constraints_cardinality_and_value_bounded(self, kb) -> None:
        huge = {f"k{i}": "v" for i in range(_MAX_CONSTRAINTS * 5)}
        res = audit_design(description=DESC, matched_signal_ids=_probe_signal_ids(kb), constraints=huge)
        assert len(res["constraints_analyzed"]) <= _MAX_CONSTRAINTS
        res2 = audit_design(description=DESC, matched_signal_ids=_probe_signal_ids(kb),
                            constraints={"platform": "x" * (_MAX_CONSTRAINT_VALUE_LEN * 4)})
        assert len(res2["constraints_analyzed"]["platform"]) <= _MAX_CONSTRAINT_VALUE_LEN

    def test_description_bounded_and_never_surfaced(self, kb) -> None:
        """The untrusted free-text description is bounded where it enters and never
        reaches the output surface — retrieval is driven by matched_signal_ids."""
        assert isinstance(_MAX_DESCRIPTION_LEN, int) and _MAX_DESCRIPTION_LEN > 0
        marker = "SENSITIVE_MARKER_" + "z" * (_MAX_DESCRIPTION_LEN * 3)
        res = audit_design(description=marker, matched_signal_ids=_probe_signal_ids(kb))
        assert "SENSITIVE_MARKER_" not in json.dumps(res)

    def test_no_eval_or_regex_on_constraint_input(self, kb) -> None:
        payloads = {"platform": "__import__('os').system('echo x')", "audience": "${7*7}"}
        res = audit_design(description=DESC, matched_signal_ids=_probe_signal_ids(kb), constraints=payloads)
        assert res["constraints_analyzed"]["audience"] == "${7*7}"   # inert, not evaluated


# ===================================================================
# DELETIONS — _ANTI_PATTERNS island GONE at S6 (physical deletion + grader
# LEG-2 removal); matcher not called; the field-name bug read gone
# ===================================================================

class TestDeletions:
    def test_anti_patterns_symbol_deleted(self) -> None:
        """S6 (story-041efcf4): the 12-slug _ANTI_PATTERNS island is DELETED — importing it
        fails and the tool source names it nowhere (grep 0 code refs). Flipped from the S3
        'retained-but-unread' guard now that its last reader (the grader's LEG-2) is gone."""
        with pytest.raises(ImportError):
            from theia.tools.audit_design import _ANTI_PATTERNS  # noqa: F401
        assert "_ANTI_PATTERNS" not in _AUDIT_SRC.read_text(encoding="utf-8")

    def test_grader_no_longer_imports_the_dict(self) -> None:
        """The grader's LEG-2 (_ANTI_PATTERNS membership) is DROPPED at S6 (measured-empty on
        v3), so grade.py no longer imports the dict. Flipped from the S3 retention guard."""
        gpath = Path(__file__).parent / "data" / "gmetric" / "grade.py"
        src = gpath.read_text(encoding="utf-8")
        assert "from theia.tools.audit_design import _ANTI_PATTERNS" not in src

    def test_matcher_not_called_and_field_bug_read_gone(self) -> None:
        """audit_design does not CALL match_structural_signals (the matcher, DELETED from the
        loaders at S6) and does not READ the dead 'accessibility' field name. AST-scanned over
        the function body (not the module) so a prose mention cannot false-positive."""
        tree = ast.parse(_AUDIT_SRC.read_text(encoding="utf-8"))
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "audit_design")
        attrs = [n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute)]
        assert "match_structural_signals" not in attrs        # matcher not called
        assert "filter_by_constraints" not in attrs           # constraint-filter leg not called
        # the dead field-name read: no `<x>.get("accessibility")` in the body
        dead_reads = [
            n for n in ast.walk(fn)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == "get" and n.args
            and isinstance(n.args[0], ast.Constant) and n.args[0].value == "accessibility"
        ]
        assert not dead_reads, "audit_design must not read the dead 'accessibility' field"


# ===================================================================
# DEEP-FREEZE — the singleton corpus stays uncorrupted through the tool
# ===================================================================

class TestCorpusUncorrupted:
    def test_corpus_singleton_uncorrupted_through_tool(self, kb) -> None:
        before = list(kb.get_component_pattern("modal")["accessibility_requirements"])
        audit_design(description=DESC, matched_signal_ids=_probe_signal_ids(kb))
        after = list(kb.get_component_pattern("modal")["accessibility_requirements"])
        assert after == before
