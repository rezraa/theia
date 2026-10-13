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
  * COMPACT, LOSSLESS, BYTE-STABLE (council 1e970338) — each group is the compact
    ``{owner_id: {signal_id: signal_text}}`` projection of its loader view with that
    view's own owner key: every (signal, text, owner) triple kept, the loader view
    exactly recoverable, owners and signals in sorted id order, byte-identical across
    calls and PYTHONHASHSEED, and smaller than the loader views.
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
import os
import subprocess
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

from theia.knowledge.loader import KnowledgeLoader, NO_MATCH, compact_signal_view  # noqa: E402
from theia.tools import get_signal_index as gsi_mod  # noqa: E402  (the tool MODULE)
from theia.tools.get_signal_index import get_signal_index  # noqa: E402  (the ONE public fn)
from theia.tools.plan_design_system import plan_design_system  # noqa: E402
from theia.tools.spec_component import spec_component  # noqa: E402
from theia.tools.audit_design import audit_design  # noqa: E402
from tests._accessor_views import GROUP_ID_KEYS, accessor_views  # noqa: E402

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

    def test_accessor_returns_both_compact_nested_views(self) -> None:
        view = get_signal_index()
        assert set(view) == set(GROUP_ID_KEYS)
        for group in view.values():
            assert group
            for owner, signals in group.items():
                assert isinstance(owner, str) and isinstance(signals, dict) and signals
                assert all(isinstance(k, str) and isinstance(v, str) for k, v in signals.items())
        distinct = {g: len({sid for sigs in view[g].values() for sid in sigs}) for g in view}
        assert distinct == {"component_signals": 394, "system_signals": 206}


# ==========================================================================
# COMPACT VIEW — lossless projection of the loader views, sorted, byte-stable
# ==========================================================================

_LOADER_VIEWS = {"component_signals": KnowledgeLoader.get_signal_index,
                 "system_signals": KnowledgeLoader.get_system_signal_index}
_HYDRATE = {"component_signals": KnowledgeLoader.hydrate,
            "system_signals": KnowledgeLoader.hydrate_systems}


def _triples(group: dict) -> set:
    return {(sid, text, owner) for owner, signals in group.items() for sid, text in signals.items()}


class TestCompactView:
    @pytest.fixture(scope="class")
    def kb(self) -> KnowledgeLoader:
        return KnowledgeLoader(knowledge_dir=_KDIR)

    def test_tool_is_the_mirrored_projection(self, kb) -> None:
        """The tool adds nothing beyond the one projection the parity case binds, each
        group with its OWN owner key."""
        assert get_signal_index() == {
            g: compact_signal_view(_LOADER_VIEWS[g](kb), GROUP_ID_KEYS[g]) for g in GROUP_ID_KEYS}

    @pytest.mark.parametrize("group", sorted(GROUP_ID_KEYS))
    def test_round_trip_preserves_every_triple(self, kb, group) -> None:
        """Flattening a group gives exactly its loader view's (signal_id, signal_text,
        owner) triples — nothing dropped, nothing invented. A multi-owner signal counts
        once per owner, so distinct signal ids alone would miss a dropped owner."""
        id_key = GROUP_ID_KEYS[group]
        assert _triples(get_signal_index()[group]) == {
            (e["signal_id"], e["signal_text"], o) for e in _LOADER_VIEWS[group](kb) for o in e[id_key]}

    def test_triple_counts(self) -> None:
        view = get_signal_index()
        assert {g: len(_triples(view[g])) for g in view} == {"component_signals": 523, "system_signals": 206}

    @pytest.mark.parametrize("group", sorted(GROUP_ID_KEYS))
    def test_loader_view_is_exactly_recoverable(self, kb, group) -> None:
        """Inverting a group rebuilds its loader view entry-for-entry — same order, same
        owner lists in the same order — not merely the same set of triples."""
        assert accessor_views()[group] == _LOADER_VIEWS[group](kb)

    @pytest.mark.parametrize("group", sorted(GROUP_ID_KEYS))
    def test_every_served_signal_alone_hydrates_to_its_owner(self, kb, group) -> None:
        """Single-signal round trip: each served signal_id, hydrated ON ITS OWN through
        its group's hydrate path, returns the owner it is served under."""
        hydrate = _HYDRATE[group]
        for owner, signals in get_signal_index()[group].items():
            for sid in signals:
                assert owner in {p["id"] for p in hydrate(kb, [sid], k=50).patterns}, (owner, sid)

    def test_compact_signal_view_on_synthetic_unsorted_multi_owner_input(self) -> None:
        """Titan-local proof (independent of the Coeus parity case, which skips when the
        sibling is absent): input order is irrelevant, owners and signals come out
        sorted, a multi-owner signal appears under EACH owner, and a signal repeated
        under one owner is kept once."""
        view = [
            {"signal_id": "s3", "signal_text": "three", "component_ids": ["z", "a"]},
            {"signal_id": "s1", "signal_text": "one", "component_ids": ["z"]},
            {"signal_id": "s2", "signal_text": "two", "component_ids": ["a", "m"]},
            {"signal_id": "s1", "signal_text": "one", "component_ids": ["z"]},
        ]
        expected = '{"a": {"s2": "two", "s3": "three"}, "m": {"s2": "two"}, "z": {"s1": "one", "s3": "three"}}'
        assert json.dumps(compact_signal_view(view, "component_ids")) == expected
        assert json.dumps(compact_signal_view(list(reversed(view)), "component_ids")) == expected
        assert compact_signal_view([], "component_ids") == {}

    def test_owners_and_signals_in_sorted_id_order(self) -> None:
        for group in get_signal_index().values():
            assert list(group) == sorted(group)
            for signals in group.values():
                assert list(signals) == sorted(signals)

    def test_smaller_than_the_loader_views(self, kb) -> None:
        full = json.dumps({g: view(kb) for g, view in _LOADER_VIEWS.items()}, ensure_ascii=False)
        assert len(json.dumps(get_signal_index(), ensure_ascii=False)) < 0.6 * len(full)

    def test_byte_identical_across_calls_and_pythonhashseed(self) -> None:
        """No ``sort_keys``: the emitted order itself is deterministic, in-process and
        across processes — a cacheable prefix."""
        assert len({json.dumps(get_signal_index()) for _ in range(3)}) == 1
        snippet = ("import json,hashlib;"
                   "from theia.tools.get_signal_index import get_signal_index as g;"
                   "print(hashlib.sha256(json.dumps(g()).encode()).hexdigest())")
        src = str(Path(inspect.getsourcefile(gsi_mod)).resolve().parents[2])
        outs = set()
        for seed in ("0", "1"):
            r = subprocess.run([sys.executable, "-c", snippet], stdin=subprocess.DEVNULL,
                               capture_output=True, text=True, timeout=120,
                               env={**os.environ, "PYTHONPATH": src, "PYTHONHASHSEED": seed})
            assert r.returncode == 0, r.stderr
            outs.add(r.stdout.strip())
        assert len(outs) == 1, f"compact view bytes moved across PYTHONHASHSEED: {outs}"


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
        self._nested = accessor_views()  # conn=None -> singleton over the same corpus

    def get_signal_index(self):
        return self._nested["component_signals"]

    def get_system_signal_index(self):
        return self._nested["system_signals"]

    def __getattr__(self, name):
        return getattr(self._loader, name)


def _rank_system_unified_prod(loader, query):
    return sysb.rank_system(loader, query, index=accessor_views()["system_signals"])


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
    return accessor_views()


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
