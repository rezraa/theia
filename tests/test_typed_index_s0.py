# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""Themis ratification gate for TYPED-INDEX S0 (story-1c54b0b7, council ae492280 /
m-5a5837da; root cause m-698d738c). BLOCKS the accessor collapse (S1).

*** THE NORTH STAR. *** A blind, byte-frozen, PER-STRATUM recall@10 baseline for
Theia's TWO-VIEW signal-index accessor (COMPONENT via get_signal_index -> hydrate;
SYSTEM via get_system_signal_index -> hydrate_systems), plus a standing corpus-
disjointness guard, armed as the RED gate S1's collapse to ONE nested
{component_signals, system_signals} accessor must equal-or-beat on BOTH strata before it
can merge. This test proves, MEASURED not asserted:

  * the two strata are reported SEPARATELY, never pooled (m-e8ccb163): COMPONENT 45/58
    (the frozen v3 engine, honest partial misses left in) and SYSTEM 25/25 (a NEW blind
    labelled set; design-system selection is a one-distinctive-answer task, gold ranked
    #1-2, recognised on the query ALONE — no SHAPE to encode an answer);
  * ONLY presentation shape varies across arms: the unified nested view is byte-identical
    to the two separate surfaces, and per-stratum recall is arm-invariant end to end;
  * empty matched_signal_ids yield NO_MATCH on every arm and both strata (fail closed);
  * the standing disjointness guard holds (0 node-id overlap, 0 signal-text overlap, no
    cross-kind related edge, no dangling related edge) AND FAILS LOUDLY on any planted
    violation;
  * the SYSTEM substrate fails closed on drift (CWE-345 trust spine, grade reused);
  * the recognizer is ONE shared engine (no fork) and gold-blind (never reads the key);
  * the RED gate has teeth: a planted collapse regression (the exact m-698d738c bug — the
    unified view drops the system surface) fails the >=-baseline gate.

Firewall: imports only theia.* + the frozen grader/benches (theia-only, via sys.path).
Never opens the live Othrys DB.
"""

from __future__ import annotations

import ast
import contextlib
import hashlib
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

import pytest

_G = Path(__file__).resolve().parent / "data" / "gmetric"
if str(_G) not in sys.path:
    sys.path.insert(0, str(_G))

import grade  # noqa: E402  (frozen deterministic grader + substrate verifier, theia-only)
import theia_engine_bench as eng  # noqa: E402  (frozen COMPONENT recognizer)
import typed_index_bench as sysb  # noqa: E402  (SYSTEM recognizer + arm harness)
from theia.knowledge.loader import KnowledgeLoader, NO_MATCH, _signal_id  # noqa: E402

_KDIR = grade.KDIR
_SYS_FILES = {
    "PROBLEMS_IN": "problems_blind_sys_v1.json",
    "GMETRIC_IN": "gmetric_sys_v1.json",
    "FREEZE_MANIFEST": "freeze_manifest_sys_v1.json",
    "BASELINE_OUT": "baseline_pinned_sys_v1.json",
}

# The frozen SYSTEM stratum artifacts (durable regression floors).
SYS_PROBLEMS = json.loads((_G / "problems_blind_sys_v1.json").read_text(encoding="utf-8"))
SYS_GMETRIC = json.loads((_G / "gmetric_sys_v1.json").read_text(encoding="utf-8"))
SYS_MANIFEST = json.loads((_G / "freeze_manifest_sys_v1.json").read_text(encoding="utf-8"))
SYS_BASELINE = json.loads((_G / "baseline_pinned_sys_v1.json").read_text(encoding="utf-8"))
SYS_MATCHES = json.loads((_G / "theia_matches_sys_v1.json").read_text(encoding="utf-8"))
SYS_MATCHES_FREEZE = json.loads((_G / "theia_matches_freeze_sys_v1.json").read_text(encoding="utf-8"))

# Per-stratum baseline floors (the RED gate bar; never pooled — m-e8ccb163).
_SYS_COVERED_10 = 25          # SYS-PA 5 + SYS-PB 14 + SYS-TK 6
_SYS_DENOM = 25
_COMP_COVERED_10 = 45         # the frozen v3 engine (PA 16 + PB 16 + TK 6 + SEED 5 + CE 2)
_COMP_DENOM = 58


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@contextlib.contextmanager
def _sys_globals():
    """Repoint the reused grader at the SYSTEM frozen set (in-process, auto-reverted)."""
    orig = {a: getattr(grade, a) for a in _SYS_FILES}
    for a, name in _SYS_FILES.items():
        setattr(grade, a, _G / name)
    try:
        yield
    finally:
        for a, v in orig.items():
            setattr(grade, a, v)


def _grade_sys(method_fn, name):
    with _sys_globals():
        return grade.grade(method_fn, name)


def _result(core: dict) -> dict:
    """The graded RESULT (recall / per-problem / stratified), excluding the ``method``
    label. Arm invariance is about the retrieval result, not the method's name string."""
    return {k: v for k, v in core.items() if k != "method"}


# ==========================================================================
# Substrate — SYSTEM trust spine fails closed (CWE-345), grade reused verbatim
# ==========================================================================

class TestSubstrate:
    def test_system_substrate_verifies_clean(self) -> None:
        with _sys_globals():
            checks = grade._verify_substrate()  # raises SystemExit on any drift
        assert all(c["match"] for c in checks.values())

    def test_answer_key_content_hashed_and_pinned(self) -> None:
        with _sys_globals():
            ak = grade.answer_key_sha256_from_gmetric()
        assert SYS_MANIFEST["answer_key_sha256"] == ak
        assert SYS_BASELINE["determinism"]["answer_key_sha256"] == ak
        assert SYS_GMETRIC["3_score"]["answer_key_sha256"] == ak

    def test_manifest_pins_the_exact_set(self) -> None:
        expected = {"problems_blind_sys_v1.json", "gmetric_sys_v1.json",
                    "component_patterns.json", "decision_rules.json",
                    "design_systems.json", "accessibility_standards.json"}
        assert set(SYS_MANIFEST["pins"]) == expected

    def test_fail_closed_on_gold_flip(self, tmp_path, monkeypatch) -> None:
        """A flipped acceptable_id changes gmetric_sys bytes -> manifest pin mismatch."""
        gdir, kdir = tmp_path / "gmetric", tmp_path / "knowledge"
        gdir.mkdir(); kdir.mkdir()
        for name in _SYS_FILES.values():
            shutil.copy(_G / name, gdir / name)
        for f in grade.CORPUS_FILES:
            shutil.copy(_KDIR / f, kdir / f)
        for a, name in _SYS_FILES.items():
            monkeypatch.setattr(grade, a, gdir / name)
        monkeypatch.setattr(grade, "KDIR", kdir)
        gm = json.loads(grade.GMETRIC_IN.read_text(encoding="utf-8"))
        gm["reachable_set_map"][0]["acceptable_ids"] = ["wrong_id"]
        grade.GMETRIC_IN.write_text(json.dumps(gm, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with pytest.raises(SystemExit, match="SUBSTRATE DRIFT"):
            grade._verify_substrate()


# ==========================================================================
# Benchmark shape — blind, verbatim, stratified
# ==========================================================================

class TestBenchmarkShape:
    def test_n_and_strata(self) -> None:
        assert SYS_PROBLEMS["n_problems"] == len(SYS_PROBLEMS["problems"]) >= 25
        assert {"SYS-PA", "SYS-PB", "SYS-TK"} == {p["qclass"] for p in SYS_PROBLEMS["problems"]}

    def test_every_E_gold_is_a_real_signal_bearing_system(self) -> None:
        kb = KnowledgeLoader(knowledge_dir=_KDIR)
        signal_bearing = {s["id"] for s in kb._design_systems
                          if any(x.strip() for x in s.get("signals", []))}
        for row in SYS_GMETRIC["reachable_set_map"]:
            if row["verdict"] == "E":
                for cid in row["acceptable_ids"]:
                    assert cid in signal_bearing, f"gold {cid} is not a signal-bearing system"

    def test_sys_pb_no_gold_id_leak(self) -> None:
        """d-6146f069: authored problem-language (SYS-PB) never contains its gold id."""
        for p in SYS_PROBLEMS["problems"]:
            if p["qclass"] == "SYS-PB":
                ql = " ".join(p["query"]).lower()
                for g in p["golds"]:
                    cid = g["canonical"].lower()
                    assert not (cid in ql or cid.replace("_", " ") in ql or cid.replace("_", "-") in ql), \
                        f"{p['id']} leaks gold {g['canonical']}"

    def test_sys_pa_queries_are_verbatim_system_signals(self) -> None:
        kb = KnowledgeLoader(knowledge_dir=_KDIR)
        sigs = {s for sys in kb._design_systems for s in sys.get("signals", [])}
        for p in SYS_PROBLEMS["problems"]:
            if p["qclass"] == "SYS-PA":
                for q in p["query"]:
                    assert q in sigs, f"{p['id']} SYS-PA query not a verbatim system signal: {q!r}"

    def test_recognizer_is_gold_blind(self) -> None:
        """typed_index_bench never reads the answer key (gmetric_sys) in executable code."""
        tree = ast.parse((_G / "typed_index_bench.py").read_text(encoding="utf-8"))
        docstrings = set()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                docstrings.add(id(body[0].value))
        offenders = [n.value for n in ast.walk(tree)
                     if isinstance(n, ast.Constant) and isinstance(n.value, str)
                     and id(n) not in docstrings and "gmetric_" in n.value]
        assert not offenders, f"recognizer reads the answer key in code: {offenders}"


# ==========================================================================
# Recognition — reproducible, gold-blind, resolvable (no hand-edit hides)
# ==========================================================================

class TestRecognition:
    def test_recognition_reproducible(self) -> None:
        live = sysb.build_matches(KnowledgeLoader(knowledge_dir=_KDIR))
        assert live == SYS_MATCHES["matches"]

    def test_recognizer_substrate_pins(self) -> None:
        pins = SYS_MATCHES_FREEZE["pins"]
        paths = {
            "theia_matches_sys_v1.json": _G / "theia_matches_sys_v1.json",
            "problems_blind_sys_v1.json": _G / "problems_blind_sys_v1.json",
            "design_systems.json": _KDIR / "design_systems.json",
        }
        assert set(pins) == set(paths)
        for name, p in paths.items():
            assert _sha(p) == pins[name], f"{name} drifted from the recognizer pin"

    def test_all_matched_signals_resolve(self) -> None:
        idx_ids = {e["signal_id"] for e in KnowledgeLoader(knowledge_dir=_KDIR).get_system_signal_index()}
        unresolved = {p: [s for s in sigs if s not in idx_ids] for p, sigs in SYS_MATCHES["matches"].items()}
        assert not {p: v for p, v in unresolved.items() if v}


# ==========================================================================
# Shared engine — ONE recognizer, no fork (DRY; the m-e8ccb163 "same primitives")
# ==========================================================================

class TestSharedEngine:
    def test_system_and_component_share_one_engine(self) -> None:
        assert sysb._recognize_over is eng._recognize_over

    def test_component_recognition_via_shared_engine_matches(self) -> None:
        """The shared engine, bound to the component accessors, reproduces the frozen
        component recognizer exactly -> the system path is a generalisation, not a fork."""
        kb = KnowledgeLoader(knowledge_dir=_KDIR)
        problems = json.loads(eng.PROBLEMS_IN.read_text(encoding="utf-8"))["problems"]

        def _shared(query, shape):
            def seed(t):
                ids = []
                for c in (t, t.replace("-", "_"), t.replace("_", "-")):
                    if kb.get_component_pattern(c):
                        ids += kb.signal_ids_for(c)
                return ids
            return sysb._recognize_over(kb.get_signal_index(), seed, query, shape)

        for p in problems:
            shape = eng.SHAPE.get(p["id"], "")
            assert _shared(p["query"], shape) == eng.recognize(kb, p["query"], shape), p["id"]


# ==========================================================================
# Per-stratum baseline — reported SEPARATELY, never pooled (m-e8ccb163)
# ==========================================================================

class TestPerStratumBaseline:
    def test_system_two_view_baseline_matches_pin(self) -> None:
        # the pin was captured under this method name (grade's core embeds "method").
        core = _grade_sys(sysb.rank_system, "system_two_view_hydrate")
        assert core["covered"]["10"] == _SYS_COVERED_10
        assert core["denominator_E_golds"] == _SYS_DENOM
        assert grade.result_core_sha256(core) == SYS_BASELINE["determinism"]["result_core_sha256"]
        assert core["covered"] == SYS_BASELINE["RESULT_baseline"]["covered"]

    def test_system_stratified_reported_per_qclass(self) -> None:
        core = _grade_sys(sysb.rank_system, "system_two_view")
        by = core["by_qclass"]
        assert by["SYS-PA"]["10"]["covered"] == 5
        assert by["SYS-PB"]["10"]["covered"] == 14   # the problem-language register is NON-zero (not degenerate)
        assert by["SYS-TK"]["10"]["covered"] == 6

    def test_component_two_view_baseline(self) -> None:
        core = grade.grade(eng.rank_engine, "component_two_view")  # conftest defaults v3
        assert core["covered"]["10"] == _COMP_COVERED_10
        assert core["denominator_E_golds"] == _COMP_DENOM
        # honest partial misses left in (non-degenerate): PA 16/25, PB 16/20
        assert core["by_qclass"]["PB"]["10"]["covered"] == 16
        assert core["by_qclass"]["PB"]["10"]["of"] == 20

    def test_strata_are_never_pooled(self) -> None:
        """The two baselines have different denominators and are stored in different frozen
        cores -- there is no single pooled number that averages them (m-e8ccb163)."""
        assert _SYS_DENOM != _COMP_DENOM
        assert "RESULT_baseline" in SYS_BASELINE
        # the system baseline core carries ONLY system golds; no component id leaks in.
        kb = KnowledgeLoader(knowledge_dir=_KDIR)
        comp_ids = {c["id"] for c in kb._component_patterns}
        for row in SYS_GMETRIC["reachable_set_map"]:
            assert not (set(row["acceptable_ids"]) & comp_ids)


# ==========================================================================
# Arm invariance — ONLY presentation shape varies (two-view vs unified nested)
# ==========================================================================

class _UnifiedLoaderProxy:
    """A loader whose signal-index accessors read from the UNIFIED nested view, delegating
    everything else. The S1 collapse stand-in: recognition reads view["component_signals"]
    / view["system_signals"] instead of the two separate methods."""

    def __init__(self, loader) -> None:
        self._loader = loader
        self._nested = sysb.nested_view(loader)

    def get_signal_index(self):
        return self._nested["component_signals"]

    def get_system_signal_index(self):
        return self._nested["system_signals"]

    def __getattr__(self, name):
        return getattr(self._loader, name)


def _rank_component_unified(loader, query):
    return eng.rank_engine(_UnifiedLoaderProxy(loader), query)


def _rank_system_unified(loader, query):
    return sysb.rank_system(loader, query, index=sysb.nested_view(loader)["system_signals"])


class TestArmInvariance:
    def test_nested_view_surfaces_are_byte_identical_to_two_view(self) -> None:
        kb = KnowledgeLoader(knowledge_dir=_KDIR)
        view = sysb.nested_view(kb)
        assert view["component_signals"] == kb.get_signal_index()
        assert view["system_signals"] == kb.get_system_signal_index()

    def test_system_recall_is_arm_invariant(self) -> None:
        two_view = _grade_sys(sysb.rank_system, "arm")
        unified = _grade_sys(_rank_system_unified, "arm")
        assert _result(two_view) == _result(unified)  # only presentation shape varies

    def test_component_recall_is_arm_invariant(self) -> None:
        two_view = grade.grade(eng.rank_engine, "arm")
        unified = grade.grade(_rank_component_unified, "arm")
        assert _result(two_view) == _result(unified)


# ==========================================================================
# Fail-closed abstention — empty matched_signal_ids -> NO_MATCH on EVERY arm
# ==========================================================================

_GIBBERISH = ["zzqqxx nonexistent gibberish termxyz wibble"]


class TestNoMatchOnEmpty:
    def test_direct_empty_yields_no_match_both_strata(self) -> None:
        kb = KnowledgeLoader(knowledge_dir=_KDIR)
        assert kb.hydrate([]).state == NO_MATCH
        assert kb.hydrate_systems([]).state == NO_MATCH
        # an unresolvable signal id is also fail-closed
        assert kb.hydrate(["sig-doesnotexist0"]).state == NO_MATCH
        assert kb.hydrate_systems(["sig-doesnotexist0"]).state == NO_MATCH

    def test_recognizer_empty_leg_no_match_every_arm(self) -> None:
        """A query that recognises nothing -> [] -> NO_MATCH, on BOTH arms and BOTH strata."""
        kb = KnowledgeLoader(knowledge_dir=_KDIR)
        view = sysb.nested_view(kb)
        proxy = _UnifiedLoaderProxy(kb)
        # SYSTEM: two-view arm and unified arm
        assert sysb.recognize_system(kb, _GIBBERISH) == []
        assert sysb.recognize_system(kb, _GIBBERISH, index=view["system_signals"]) == []
        assert kb.hydrate_systems(sysb.recognize_system(kb, _GIBBERISH)).state == NO_MATCH
        # COMPONENT: two-view arm and unified arm (via the shared engine / proxy)
        assert eng.recognize(kb, _GIBBERISH, "") == []
        assert eng.recognize(proxy, _GIBBERISH, "") == []
        assert kb.hydrate(eng.recognize(kb, _GIBBERISH, "")).state == NO_MATCH


# ==========================================================================
# STANDING disjointness guard — holds AND fails loudly on any violation
# ==========================================================================

def assert_corpus_disjoint(components: list[dict], systems: list[dict]) -> None:
    """The standing component-vs-system disjointness invariant (story AC). Raises
    AssertionError (fail-closed, loud) if ANY of the four facts becomes non-zero. This is
    the single check the live guard and every planted-violation test exercise."""
    comp_ids = {c["id"] for c in components}
    sys_ids = {s["id"] for s in systems}
    # 1. node-id overlap == 0
    assert not (comp_ids & sys_ids), f"node-id overlap: {sorted(comp_ids & sys_ids)}"
    # 2. signal-text overlap == 0 (=> no content-hash sig-id collision across corpora)
    comp_sig = {x.strip() for c in components for x in c.get("signals", []) if x.strip()}
    sys_sig = {x.strip() for s in systems for x in s.get("signals", []) if x.strip()}
    assert not (comp_sig & sys_sig), f"signal-text overlap: {sorted(comp_sig & sys_sig)}"
    assert not ({_signal_id(t) for t in comp_sig} & {_signal_id(t) for t in sys_sig})
    # 3. no cross-kind related/alternative edge (either direction, any relational field)
    for c in components:
        for f in ("related_patterns", "alternatives"):
            assert not (set(c.get(f, [])) & sys_ids), f"{c['id']}.{f} -> system"
    for s in systems:
        for f in ("related_systems", "alternatives"):
            assert not (set(s.get(f, [])) & comp_ids), f"{s['id']}.{f} -> component"
    # 4. no dangling related edge (every related target resolves within its own corpus)
    for c in components:
        for n in c.get("related_patterns", []):
            assert n in comp_ids, f"{c['id']} related_patterns dangling: {n}"
    for s in systems:
        for n in s.get("related_systems", []):
            assert n in sys_ids, f"{s['id']} related_systems dangling: {n}"


class TestDisjointnessGuard:
    def test_real_corpus_is_disjoint(self) -> None:
        kb = KnowledgeLoader(knowledge_dir=_KDIR)
        assert len(kb._component_patterns) == 66 and len(kb._design_systems) == 54
        assert_corpus_disjoint(kb._component_patterns, kb._design_systems)  # must not raise

    def test_planted_node_id_collision_trips_guard(self) -> None:
        kb = KnowledgeLoader(knowledge_dir=_KDIR)
        comps = kb._component_patterns
        systems = [dict(s) for s in kb._design_systems]
        systems[0] = {**systems[0], "id": comps[0]["id"]}   # a system stealing a component id
        with pytest.raises(AssertionError, match="node-id overlap"):
            assert_corpus_disjoint(comps, systems)

    def test_planted_signal_text_collision_trips_guard(self) -> None:
        kb = KnowledgeLoader(knowledge_dir=_KDIR)
        comps = kb._component_patterns
        stolen = comps[0]["signals"][0]
        systems = [dict(s) for s in kb._design_systems]
        systems[0] = {**systems[0], "signals": list(systems[0].get("signals", [])) + [stolen]}
        with pytest.raises(AssertionError, match="signal-text overlap"):
            assert_corpus_disjoint(comps, systems)

    def test_planted_cross_kind_edge_trips_guard(self) -> None:
        kb = KnowledgeLoader(knowledge_dir=_KDIR)
        comps = kb._component_patterns
        systems = [dict(s) for s in kb._design_systems]
        systems[0] = {**systems[0], "related_systems": list(systems[0].get("related_systems", [])) + [comps[0]["id"]]}
        with pytest.raises(AssertionError, match="-> component"):
            assert_corpus_disjoint(comps, systems)

    def test_planted_dangling_related_edge_trips_guard(self) -> None:
        kb = KnowledgeLoader(knowledge_dir=_KDIR)
        comps = kb._component_patterns
        systems = [dict(s) for s in kb._design_systems]
        systems[0] = {**systems[0], "related_systems": list(systems[0].get("related_systems", [])) + ["ghost_system_xyz"]}
        with pytest.raises(AssertionError, match="dangling"):
            assert_corpus_disjoint(comps, systems)


# ==========================================================================
# RED gate armed for S1 — the bar, and it has teeth
# ==========================================================================

class TestRedGateArmed:
    def test_frozen_baselines_are_the_bar(self) -> None:
        """The two frozen per-stratum two-view numbers are the durable bar S1 must beat."""
        assert SYS_BASELINE["RESULT_baseline"]["covered"]["10"] == _SYS_COVERED_10
        assert SYS_BASELINE["arm"].startswith("baseline_two_view")

    def test_compliant_unified_meets_the_gate_both_strata(self) -> None:
        """A faithful collapse (unified view byte-identical to two-view) equals-or-beats the
        baseline on BOTH strata -> a compliant S1 passes the gate."""
        sys_unified = _grade_sys(_rank_system_unified, "sys_unified")["covered"]["10"]
        comp_unified = grade.grade(_rank_component_unified, "comp_unified")["covered"]["10"]
        assert sys_unified >= _SYS_COVERED_10
        assert comp_unified >= _COMP_COVERED_10

    def test_planted_collapse_regression_fails_the_gate(self) -> None:
        """RED: the gate has teeth. Plant the EXACT m-698d738c bug — the collapse drops the
        system surface (system_signals empty in the unified view) — and system recall
        collapses below baseline, so the >=-baseline gate FAILS LOUDLY. This is the
        regression the whole story guards against."""
        def _rank_system_broken(loader, query):
            return sysb.rank_system(loader, query, index=[])  # unified view lost the system surface

        broken = _grade_sys(_rank_system_broken, "sys_broken")["covered"]["10"]
        assert broken < _SYS_COVERED_10                      # the surface loss dropped recall
        with pytest.raises(AssertionError):
            assert broken >= _SYS_COVERED_10, f"unified {broken} < baseline {_SYS_COVERED_10}"


# ==========================================================================
# Firewall — S0 artifacts import only theia.* (never coeus/othrys/mnemos)
# ==========================================================================

class TestFirewall:
    @pytest.mark.parametrize("fn", ["typed_index_bench.py", "build_typed_index_s0.py"])
    def test_no_forbidden_imports(self, fn: str) -> None:
        tree = ast.parse((_G / fn).read_text(encoding="utf-8"))
        forbidden = {"coeus", "othrys", "mnemos"}
        mods: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods.append(node.module)
        assert not [m for m in mods if m.split(".")[0] in forbidden]
