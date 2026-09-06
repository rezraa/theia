# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""S1 proof for the TYPED-INDEX collapse (story-f875164f, council ae492280 /
m-5a5837da; root cause m-698d738c). The S0 gate (story-1c54b0b7) armed the RED bar;
this suite discharges it against the REAL production accessor.

*** THE NORTH STAR. *** Theia exposes exactly ONE reachable signal-index tool
returning a NESTED typed view ``{component_signals, system_signals}``, with
``get_system_signal_index`` removed (no shim), such that unified recall@10
equals-or-beats the frozen S0 baseline on BOTH strata (never pooled) and the
filename-keyed seed-drop is made impossible by construction.

What is MEASURED here (not asserted):

  * REACHABILITY-BY-CONSTRUCTION — ``theia.tools.get_signal_index`` holds exactly ONE
    public top-level function, and ``server.py`` declares exactly one signal-index
    ``@mcp.tool``. This is the seed-drop fix: the filename-keyed seed mints one graph
    tool per file, so one public function cannot be silently dropped. (This test FAILS
    on the pre-collapse two-function state — the RED-first case.)
  * RECALL GUARD — the UNIFIED nested view sourced from the PRODUCTION accessor
    (``theia.tools.get_signal_index.get_signal_index``, NOT the S0 harness reshape)
    equals-or-beats the frozen S0 per-stratum baseline: SYSTEM covered@10 >= 25,
    COMPONENT covered@10 >= 45. Reuses the frozen S0 grader/benches verbatim; never
    refreezes or mutates the key/corpus; the two strata are NEVER pooled (m-e8ccb163).
  * DETERMINISM — each nested view is sorted by ``signal_id`` with sorted id-lists, and
    the composite is byte-identical to a fresh loader's two separate views (only
    presentation shape changed).
  * END-TO-END (Directive 8, ids taken from the accessor's OWN output, never hand-built)
    — a known SYSTEM signal -> plan_design_system -> base_system != 'custom' AND
    related_systems non-empty; a known COMPONENT signal -> audit_design / spec_component
    hydrate correctly.
  * MIS-TYPE — a system-typed id fed to spec_component and a component-typed id fed to
    plan_design_system abstain via NO_MATCH + unmatched_signals with a reason (no silent
    custom); empty ids -> NO_MATCH.

Firewall: imports only theia.* + the frozen S0 grader/benches/helpers (theia-only, via
sys.path). Never opens the live Othrys DB; the live-summon reachability leg is the user's
post-re-seed step (the filename-keyed seed mints tool identity only at ingestion).
"""

from __future__ import annotations

import ast
import inspect
import json
import sys
from pathlib import Path

import pytest

_TESTS = Path(__file__).resolve().parent
_G = _TESTS / "data" / "gmetric"
for _p in (str(_TESTS), str(_G)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import grade  # noqa: E402  (frozen deterministic grader, theia-only)
import theia_engine_bench as eng  # noqa: E402  (frozen COMPONENT recognizer)
import typed_index_bench as sysb  # noqa: E402  (SYSTEM recognizer + arm harness)
import test_typed_index_s0 as s0  # noqa: E402  (frozen S0 gate: _grade_sys + per-stratum bars)

from theia.knowledge.loader import KnowledgeLoader, NO_MATCH  # noqa: E402
from theia.tools import get_signal_index as gsi_mod  # noqa: E402  (the tool MODULE)
from theia.tools.get_signal_index import get_signal_index  # noqa: E402  (the ONE public fn)
from theia.tools.plan_design_system import plan_design_system  # noqa: E402
from theia.tools.spec_component import spec_component  # noqa: E402
from theia.tools.audit_design import audit_design  # noqa: E402

_KDIR = grade.KDIR
_SYS_COVERED_10 = s0._SYS_COVERED_10   # 25 — the frozen SYSTEM two-view bar (m-68d8ff4e)
_COMP_COVERED_10 = s0._COMP_COVERED_10  # 45 — the frozen v3 engine COMPONENT bar

_NONRESOLVING_TYPE = "not_a_real_component_zzz"  # never a corpus id -> forces the id-driven path


# ==========================================================================
# REACHABILITY-BY-CONSTRUCTION — one public fn, one @mcp.tool (the seed-drop fix)
# ==========================================================================

def _public_top_level_functions(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [n.name for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not n.name.startswith("_")]


def _mcp_tool_functions(path: Path) -> list[str]:
    """Names of module-level functions decorated with ``@mcp.tool(...)``."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for n in tree.body:
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in n.decorator_list:
            call = dec.func if isinstance(dec, ast.Call) else dec
            if isinstance(call, ast.Attribute) and call.attr == "tool" \
                    and isinstance(call.value, ast.Name) and call.value.id == "mcp":
                names.append(n.name)
    return names


class TestReachabilityByConstruction:
    def test_tool_module_has_exactly_one_public_function(self) -> None:
        """The filename-keyed seed mints ONE tool per file keyed by the stem; a single
        public function makes the second-function drop (m-698d738c) impossible. FAILS on
        the pre-collapse two-function file."""
        fns = _public_top_level_functions(Path(inspect.getsourcefile(gsi_mod)))
        assert fns == ["get_signal_index"], f"expected one public fn, found {fns}"

    def test_system_accessor_removed_no_shim(self) -> None:
        assert not hasattr(gsi_mod, "get_system_signal_index"), "no shim: the split fn must be gone"

    def test_server_declares_exactly_one_signal_index_tool(self) -> None:
        import theia.server as server
        tools = [t for t in _mcp_tool_functions(Path(inspect.getsourcefile(server))) if "signal_index" in t]
        assert tools == ["get_signal_index"], f"expected one signal-index @mcp.tool, found {tools}"

    def test_accessor_returns_both_nested_views(self) -> None:
        view = get_signal_index()
        assert set(view) == {"component_signals", "system_signals"}
        assert view["component_signals"] and view["system_signals"]
        for entry in view["component_signals"]:
            assert set(entry) == {"signal_id", "signal_text", "component_ids"}
        for entry in view["system_signals"]:
            assert set(entry) == {"signal_id", "signal_text", "system_ids"}


# ==========================================================================
# DETERMINISM — sorted views, byte-identical to the fresh two-view (shape only)
# ==========================================================================

class TestDeterminism:
    def test_each_view_sorted_by_signal_id_with_sorted_id_lists(self) -> None:
        view = get_signal_index()
        for surface, id_field in (("component_signals", "component_ids"), ("system_signals", "system_ids")):
            entries = view[surface]
            assert [e["signal_id"] for e in entries] == sorted(e["signal_id"] for e in entries), surface
            for e in entries:
                assert e[id_field] == sorted(e[id_field]), f"{surface} {e['signal_id']} id-list unsorted"

    def test_composite_is_the_two_views_only_reshaped(self) -> None:
        """Only presentation shape changed: the composite re-presents the SAME frozen
        signal_ids under two labels, so recall is identical-by-construction."""
        fresh = KnowledgeLoader(knowledge_dir=_KDIR)
        view = get_signal_index()
        assert view["component_signals"] == fresh.get_signal_index()
        assert view["system_signals"] == fresh.get_system_signal_index()

    def test_composite_byte_identical_across_fresh_calls(self) -> None:
        dumps = {json.dumps(get_signal_index(), sort_keys=True) for _ in range(3)}
        assert len(dumps) == 1


# ==========================================================================
# RECALL GUARD — the UNIFIED PRODUCTION accessor meets the S0 bar on BOTH strata
# ==========================================================================

class _ProdUnifiedProxy:
    """A loader whose signal-index accessors read from the PRODUCTION nested tool
    accessor (theia.tools.get_signal_index.get_signal_index), delegating hydrate and
    every other method to the real loader. This is the S1 gate the S0 harness
    anticipated: recognition now reads the real composite's surfaces, not the two
    separate loader methods nor the S0 harness reshape."""

    def __init__(self, loader) -> None:
        self._loader = loader
        self._nested = get_signal_index()  # conn=None -> singleton over the same corpus

    def get_signal_index(self):
        return self._nested["component_signals"]

    def get_system_signal_index(self):
        return self._nested["system_signals"]

    def __getattr__(self, name):
        return getattr(self._loader, name)


def _rank_system_unified_prod(loader, query):
    return sysb.rank_system(loader, query, index=get_signal_index()["system_signals"])


def _rank_component_unified_prod(loader, query):
    return eng.rank_engine(_ProdUnifiedProxy(loader), query)


class TestRecallGuard:
    def test_system_unified_recall_meets_baseline(self) -> None:
        core = s0._grade_sys(_rank_system_unified_prod, "s1_sys_unified_prod")
        assert core["covered"]["10"] >= _SYS_COVERED_10, \
            f"SYSTEM unified {core['covered']['10']} < baseline {_SYS_COVERED_10}"

    def test_component_unified_recall_meets_baseline(self) -> None:
        core = grade.grade(_rank_component_unified_prod, "s1_comp_unified_prod")  # conftest defaults v3
        assert core["covered"]["10"] >= _COMP_COVERED_10, \
            f"COMPONENT unified {core['covered']['10']} < baseline {_COMP_COVERED_10}"

    def test_strata_reported_separately(self) -> None:
        """Never pooled (m-e8ccb163): the two bars have different denominators and are
        graded through different frozen sets."""
        sys_core = s0._grade_sys(_rank_system_unified_prod, "s1_sys")
        comp_core = grade.grade(_rank_component_unified_prod, "s1_comp")
        assert sys_core["denominator_E_golds"] != comp_core["denominator_E_golds"]


# ==========================================================================
# END-TO-END — ids taken from the accessor's OWN output, never hand-built (Directive 8)
# ==========================================================================

def _view() -> dict:
    return get_signal_index()


def _a_system_signal_with_related() -> str:
    """A signal_id from the accessor whose owning system carries a non-empty
    related_systems edge — so plan_design_system's fan-out is non-empty."""
    view = _view()
    kb = KnowledgeLoader(knowledge_dir=_KDIR)
    for e in view["system_signals"]:
        for sid in e["system_ids"]:
            node = kb.get_design_system(sid)
            if node and node.get("related_systems"):
                return e["signal_id"]
    raise AssertionError("no system signal maps to a system with related_systems")


def _a_component_signal_for(component_id: str) -> str:
    view = _view()
    for e in view["component_signals"]:
        if component_id in e["component_ids"]:
            return e["signal_id"]
    raise AssertionError(f"no component signal maps to {component_id}")


class TestEndToEnd:
    def test_known_system_signal_plans_a_real_foundation(self) -> None:
        sig = _a_system_signal_with_related()
        res = plan_design_system(product_description="ctx only", matched_signal_ids=[sig])
        found = res["recommended_foundation"]
        assert found["base_system"] != "custom", found
        assert found["related_systems"], "related_systems fan-out must be non-empty"
        assert found["retrieval_state"] in ("hit", "low_confidence")

    def test_known_component_signal_audits_correctly(self) -> None:
        sig = _a_component_signal_for("button")
        res = audit_design(description="ctx only", matched_signal_ids=[sig])
        assert res["retrieval_state"] in ("hit", "low_confidence")
        assert res["design_issues"], "a recognised component signal must hydrate issues"
        assert "button" in {d["component_id"] for d in res["design_issues"]}

    def test_known_component_signal_specs_via_nearest(self) -> None:
        sig = _a_component_signal_for("button")
        res = spec_component(component_type=_NONRESOLVING_TYPE, matched_signal_ids=[sig])
        assert res["from_knowledge_base"] is True and res["nearest"] is True
        assert res["component_id"] == "button"
        assert res["anatomy"], "a hydrated spec must carry the component's own anatomy"


# ==========================================================================
# MIS-TYPE — cross-corpus id abstains via NO_MATCH + unmatched (no silent custom)
# ==========================================================================

class TestMisType:
    def test_system_id_into_spec_component_abstains(self) -> None:
        sys_sig = _view()["system_signals"][0]["signal_id"]
        res = spec_component(component_type=_NONRESOLVING_TYPE, matched_signal_ids=[sys_sig])
        assert res["from_knowledge_base"] is False
        assert res["retrieval_state"] == NO_MATCH
        assert sys_sig in res["unmatched"]

    def test_component_id_into_plan_design_system_abstains(self) -> None:
        comp_sig = _view()["component_signals"][0]["signal_id"]
        res = plan_design_system(product_description="ctx only", matched_signal_ids=[comp_sig])
        found = res["recommended_foundation"]
        assert found["base_system"] == "custom"
        assert found["retrieval_state"] == NO_MATCH
        assert comp_sig in found["unmatched"]
        assert found["rationale"], "the abstention must carry a reason (no silent custom)"

    def test_empty_ids_yield_no_match_every_tool(self) -> None:
        assert plan_design_system(product_description="x", matched_signal_ids=[])[
            "recommended_foundation"]["retrieval_state"] == NO_MATCH
        assert spec_component(component_type=_NONRESOLVING_TYPE, matched_signal_ids=[])[
            "retrieval_state"] == NO_MATCH
        assert audit_design(description="x", matched_signal_ids=[])["retrieval_state"] == NO_MATCH
