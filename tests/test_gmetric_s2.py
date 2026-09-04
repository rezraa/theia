# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""S2 outcome gate (story-302d9772, council 3e6eeeab): dissolve the decision_rules'
problem-language prose onto the component signal index + materialize the component
``related_patterns`` fan-out edge + re-freeze the benchmark v1->v2.

RED-first proofs of the AC, all measured / provenance-bound, never asserted by fiat:

  * REACHABILITY of rule problem-language in get_signal_index rises from 0 to the full
    MIGRATED set (128 of the 248 distinct rule structural_signals -- the 120 remainder
    belong to the 30 rules whose recommended_patterns are ALL dangling and are recorded,
    not migrated). The corpus IS the deterministic image of decision_rules.json, so the
    rise is provenance-bound: every migrated signal sits on a component a resolvable
    rule recommends, copied VERBATIM, no original signal displaced (copy-not-move).
  * the 216/263 dangling refs are surfaced (regression-locked), and migration touched
    ONLY resolvable component ids -- 0 edge points at a non-component id.
  * ``related_patterns`` is materialized + non-empty for every component appearing in
    >=1 rule, symmetric, co-occurrence-derived; the single non-derivable exception
    (``container``, whose sole rule has no resolvable co-member) is asserted + documented.
  * the v2 benchmark is re-frozen FAIL-CLOSED (v1 pins never mutated) and no v1 E-gold
    is evicted@10 (ratchet floor 35); a planted eviction (reverting the migration in a
    tmp sandbox) trips the ratchet -> AssertionError, and the real corpus is verified
    byte-unchanged (reverted + hash-verified, naming component_patterns.json).
  * BAR-1 holds on v2 STRATIFIED: the matcher baseline is byte-identical (35/58), the
    retrieval SYSTEM (union) does not regress, the pure engine RECOVERS PA (0->16), and
    PB/CE stay 0 (gated to S3's LLM recognizer). PB/CE before->after reported.
  * determinism: 0 signal_id collisions on the migrated corpus + a unique id per text
    (the byte-reproducible-across-PYTHONHASHSEED proof over this same migrated index is
    locked in tests/test_signal_engine.py -- shared substrate, not duplicated here).
  * the matcher's frozen baseline stays byte-stable: decision_rules.json hash is pinned
    and unchanged, and the grader's LEG-1 source-recompute (replacing the S6-deleted
    match_structural_signals) reproduces the pinned baseline result-core byte-identically.

Firewall: imports only theia.* + the frozen grader + engine bench (theia-only). Reads
the on-disk corpus; never opens the live Othrys DB.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

import pytest

_GMETRIC = Path(__file__).resolve().parent / "data" / "gmetric"
if str(_GMETRIC) not in sys.path:
    sys.path.insert(0, str(_GMETRIC))

import grade  # noqa: E402  (frozen deterministic grader, theia-only)
import theia_engine_bench as eng  # noqa: E402  (Shape-C harness, gold-blind)
from theia.knowledge.loader import KnowledgeLoader, _signal_id  # noqa: E402

_KDIR = grade.KDIR
_COMPONENTS = _KDIR / "component_patterns.json"
_RULES = _KDIR / "decision_rules.json"
# The matcher-facing corpus must stay byte-stable until S6 (decision_rules is never
# opened by the loader matcher; the pin is the byte contract the story binds).
_RULES_SHA_PIN = "d5e6971dbcaf4baa5c6dd7dbfd43da1bc2b26c9fe35e2e4adb3cf016c281e5b6"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _load():
    rules = json.loads(_RULES.read_text(encoding="utf-8"))["rules"]
    comps = json.loads(_COMPONENTS.read_text(encoding="utf-8"))["patterns"]
    return rules, comps, {c["id"] for c in comps}, {c["id"]: c for c in comps}


def _derive(rules, comp_ids):
    """Independent re-derivation of the migration image from the rules (provenance).

    signals: each rule's structural_signals onto its RESOLVABLE recommended_patterns.
    edges:   within each rule, resolvable(recommended u alternatives) mutually related.
    Resolvable = the id is a real component (dangling refs are never a home nor an edge).
    """
    add: dict[str, set[str]] = defaultdict(set)
    for r in rules:
        for cid in (p for p in r.get("recommended_patterns", []) if p in comp_ids):
            for s in r.get("structural_signals", []):
                add[cid].add(s.strip())
    edges: dict[str, set[str]] = defaultdict(set)
    for r in rules:
        u = sorted({p for f in ("recommended_patterns", "alternatives")
                    for p in r.get(f, []) if p in comp_ids})
        for a in u:
            edges[a].update(x for x in u if x != a)
    return add, edges


_RULES_L, _COMPS_L, _COMP_IDS, _COMP_BY_ID = _load()
_ADD, _EDGES = _derive(_RULES_L, _COMP_IDS)
_ALL_RULE_SIGS = {s.strip() for r in _RULES_L for s in r.get("structural_signals", [])}
_MIGRATABLE = {s for texts in _ADD.values() for s in texts}   # distinct migrated signals


# ==========================================================================
# Reachability + provenance — rule prose reaches the index, copy-not-move
# ==========================================================================

class TestReachabilityProvenance:
    def test_reachability_rises_from_zero_to_the_full_migrated_set(self) -> None:
        kb = KnowledgeLoader(knowledge_dir=_KDIR)
        index_texts = {e["signal_text"].strip() for e in kb.get_signal_index()}
        reachable = {s for s in _ALL_RULE_SIGS if s in index_texts}
        # the full migratable set is reachable, and it is exactly the derived set
        assert reachable == _MIGRATABLE
        assert len(reachable) == 128
        # the remainder (rules whose recommended_patterns ALL dangle) is NOT invented
        # into the index -- recorded, not migrated (docs/migration_proofs.md)
        assert len(_ALL_RULE_SIGS - reachable) == 120

    def test_copy_not_move_verbatim_no_original_displaced(self) -> None:
        """Each migrated block is the sorted derived set appended VERBATIM after the
        component's original signals; the original prefix carried NO rule prose, so
        pre-migration reachability of rule prose was 0 (the rise is genuine, not a
        relabel). Proven without the pre-image via the append invariant + disjointness."""
        for cid, texts in _ADD.items():
            block = sorted(texts)
            sig = _COMP_BY_ID[cid]["signals"]
            assert sig[-len(block):] == block                    # appended verbatim, sorted
            original_prefix = sig[:-len(block)]
            assert not (set(original_prefix) & _ALL_RULE_SIGS)   # original held no rule prose

    def test_every_indexed_rule_signal_has_correct_provenance(self) -> None:
        """No signal migrated to a wrong home: every rule structural_signal present on a
        component is a signal of a rule that RECOMMENDS that component (resolvable)."""
        recommends = defaultdict(set)  # signal_text -> {cid a resolvable rule recommends}
        for r in _RULES_L:
            for cid in (p for p in r.get("recommended_patterns", []) if p in _COMP_IDS):
                for s in r.get("structural_signals", []):
                    recommends[s.strip()].add(cid)
        for c in _COMPS_L:
            for s in c["signals"]:
                if s in _ALL_RULE_SIGS:                          # a migrated rule signal
                    assert c["id"] in recommends[s], f"{s!r} wrongly homed on {c['id']}"

    def test_migrated_prose_lives_one_place_index_dedupes_multi_home(self) -> None:
        """A page-level signal distributed onto ALL a rule's recommended components is
        ONE index entry (content-hash keyed) fanning to many component_ids -- one source
        of truth, not a duplicated concept."""
        kb = KnowledgeLoader(knowledge_dir=_KDIR)
        idx = {e["signal_text"]: e for e in kb.get_signal_index()}
        page = "dashboard with metric cards and data tables"       # rule_dashboard_layout
        assert page in idx
        assert set(idx[page]["component_ids"]) == {"data_table", "grid", "stat_card"}


# ==========================================================================
# Dangling refs — surfaced, never masked; migration only over resolvable ids
# ==========================================================================

class TestDanglingSurfaced:
    def test_investigation_numbers_regression_locked(self) -> None:
        """216 of 263 distinct rule->component refs dangle; 47 resolve. Locked so a later
        corpus edit that silently resolves/loses a ref is caught."""
        refs = {p for r in _RULES_L for f in ("recommended_patterns", "alternatives")
                for p in r.get(f, [])}
        resolvable = refs & _COMP_IDS
        dangling = refs - _COMP_IDS
        assert len(refs) == 263
        assert len(resolvable) == 47
        assert len(dangling) == 216

    def test_dangling_decomposition_cross_space_vs_dead(self) -> None:
        """The 216 dangling refs decompose: 23 point into OTHER corpus id-spaces (16
        design_systems + 7 accessibility -- disjoint from components by the engine's
        binding reservation, S5 territory) and 193 are dead ids present in NO corpus."""
        ds = {s["id"] for s in json.loads((_KDIR / "design_systems.json").read_text("utf-8"))["systems"]}
        a11y = {a["id"] for a in json.loads((_KDIR / "accessibility_standards.json").read_text("utf-8"))["standards"]}
        dangling = {p for r in _RULES_L for f in ("recommended_patterns", "alternatives")
                    for p in r.get(f, [])} - _COMP_IDS
        assert len(dangling & ds) == 16
        assert len(dangling & a11y) == 7
        assert len(dangling - ds - a11y) == 193

    def test_no_edge_points_at_a_dangling_ref(self) -> None:
        """Never edge to a dead ref: every related_patterns target is a real component."""
        for c in _COMPS_L:
            for n in c.get("related_patterns", []):
                assert n in _COMP_IDS, f"{c['id']} edges to non-component {n}"


# ==========================================================================
# related_patterns edge — materialized, non-empty, symmetric, co-occurrence
# ==========================================================================

class TestRelatedPatternsEdge:
    def test_materialized_and_matches_the_derivation(self) -> None:
        for cid, nb in _EDGES.items():
            assert _COMP_BY_ID[cid].get("related_patterns", []) == sorted(nb)

    def test_non_empty_for_every_rule_component_except_documented_container(self) -> None:
        appears = {p for r in _RULES_L for f in ("recommended_patterns", "alternatives")
                   for p in r.get(f, []) if p in _COMP_IDS}
        empty = {cid for cid in appears if not _COMP_BY_ID[cid].get("related_patterns")}
        # 46/47 non-empty; container is the single non-derivable edge (its sole rule
        # rule_content_heavy has no resolvable co-member) -- recorded, not forced.
        assert empty == {"container"}
        assert "related_patterns" not in _COMP_BY_ID["container"]

    def test_edges_are_symmetric(self) -> None:
        edge = {c["id"]: set(c.get("related_patterns", [])) for c in _COMPS_L}
        for a, nb in edge.items():
            for b in nb:
                assert a in edge.get(b, set()), f"asymmetric {a}->{b}"

    def test_every_edge_pair_co_occurs_in_a_rule(self) -> None:
        cooc = set()
        for r in _RULES_L:
            u = [p for f in ("recommended_patterns", "alternatives")
                 for p in r.get(f, []) if p in _COMP_IDS]
            cooc.update((a, b) for a in u for b in u if a != b)
        for c in _COMPS_L:
            for n in c.get("related_patterns", []):
                assert (c["id"], n) in cooc, f"invented edge {c['id']}->{n}"


# ==========================================================================
# Determinism — 0 signal_id collisions on the migrated corpus
# ==========================================================================

class TestDeterminismCollisions:
    def test_zero_collisions_and_unique_ids(self) -> None:
        # a hash collision on two distinct texts fails CLOSED in __init__; reaching a
        # built loader is itself the proof, re-asserted structurally here.
        kb = KnowledgeLoader(knowledge_dir=_KDIR)
        idx = kb.get_signal_index()
        distinct = {s.strip() for c in _COMPS_L for s in c["signals"] if s.strip()}
        assert len(idx) == len(distinct)                       # no two texts merged
        ids = [e["signal_id"] for e in idx]
        assert len(ids) == len(set(ids))                       # unique id per entry
        assert all(e["signal_id"] == _signal_id(e["signal_text"]) for e in idx)

    def test_fresh_loaders_byte_identical_index(self) -> None:
        a = json.dumps(KnowledgeLoader(knowledge_dir=_KDIR).get_signal_index(), sort_keys=True)
        b = json.dumps(KnowledgeLoader(knowledge_dir=_KDIR).get_signal_index(), sort_keys=True)
        assert a == b


# ==========================================================================
# Frozen matcher baseline — decision_rules byte-stable + result-core stable
# (the matcher itself is DELETED at S6, story-041efcf4)
# ==========================================================================

class TestFrozenMatcherBaselineStable:
    def test_decision_rules_byte_stable(self) -> None:
        assert _sha(_RULES) == _RULES_SHA_PIN

    # RETIRED at S6: test_match_structural_signals_callable_unchanged exercised
    # loader.match_structural_signals, deleted at S6. Its frozen output is preserved by the
    # LEG-1 source-recompute and asserted below via the pinned baseline result-core.

    def test_baseline_result_core_unchanged_matcher_output_stable(self) -> None:
        """The four-surface matcher produces byte-identical output over the migrated
        corpus -- the pinned v2 baseline result-core equals what grade recomputes."""
        core = grade.grade(grade.rank_baseline, "baseline_four_surface_matcher")
        pinned = json.loads(grade.BASELINE_OUT.read_text("utf-8"))["determinism"]["result_core_sha256"]
        assert grade.result_core_sha256(core) == pinned
        assert core["covered"]["10"] == 35


# ==========================================================================
# BAR-1 on v2 STRATIFIED — non-regression + the measured PA reachability win
# ==========================================================================

class TestBar1OnV2:
    def test_substrate_v2_clean_fail_closed(self) -> None:
        checks = grade._verify_substrate()          # raises SystemExit on any drift
        assert all(c["match"] for c in checks.values())
        assert checks["component_patterns.json"]["match"]     # v2 pins the migrated corpus

    def test_stratified_before_after_pa_recovered_pb_ce_measured(self) -> None:
        """The engine recovers PA component-golds (0 at S1 -> >0 after the S2 migration)
        and the union does not regress. The PB/CE problem-language register — which the
        DEGENERATE S1/S2 recognizer capped at 0 — is now MEASURED and non-zero after the
        S0-FIX replaced that recognizer with the curated blind recognition
        (story-cb7e532b); its full stratified proof lives in tests/test_retrieval_bar1.py.
        Every number stratified, never a pooled mean (m-e8ccb163)."""
        engine = grade.grade(eng.rank_engine, "engine")["by_qclass"]
        union = grade.grade(eng.rank_union, "union")
        baseline = grade.grade(grade.rank_baseline, "baseline")
        assert engine["PA"]["10"]["covered"] > 0             # S2 win (was 0 at S1)
        assert engine["PB"]["10"]["covered"] > 0             # S0-FIX: measured (was 0 under degenerate)
        assert engine["CE"]["10"]["covered"] > 0
        assert union["covered"]["10"] >= baseline["covered"]["10"] == 35   # non-regression


# ==========================================================================
# No-eviction ratchet — v1 E-set stays covered@10; fail-closed on a plant
# ==========================================================================

def _covered_golds(method_fn) -> set:
    core = grade.grade(method_fn, "m")
    return {(pid, g) for pid, row in core["per_problem"].items()
            for g in row["grades"]["10"]["covered_golds"]}


def _assert_no_eviction(covered_now: set, floor: set) -> None:
    """Ratchet: no gold in *floor* may drop out of *covered_now*. Raises AssertionError
    (fail-closed) on any eviction -- the single check both the live gate and the planted
    -eviction test exercise."""
    assert floor <= covered_now, f"evicted: {sorted(floor - covered_now)}"


_FLOOR_V1 = {(pid, g) for pid, row in grade.load_pinned_baseline()["per_problem"].items()
             for g in row["grades"]["10"]["covered_golds"]}


class TestNoEviction:
    def test_v2_system_covers_the_v1_floor(self) -> None:
        """The v2 retrieval SYSTEM (matcher UNION hydrate) still covers@10 every E-gold
        the pinned v1 baseline covered -- count ratchet floor 35, and no specific gold
        evicted."""
        assert len(_FLOOR_V1) == 35
        _assert_no_eviction(_covered_golds(eng.rank_union), _FLOOR_V1)

    def test_planted_eviction_trips_the_ratchet_corpus_untouched(self, tmp_path, monkeypatch) -> None:
        """RED: the ratchet is fail-closed. Revert the migration in a TMP corpus (strip
        the migrated signals + related_patterns) -> the pure engine loses its PA reach ->
        the engine's own covered@10 floor is violated -> AssertionError. The real
        component_patterns.json is verified byte-unchanged (reverted + hash-verified)."""
        before = _sha(_COMPONENTS)
        engine_floor = _covered_golds(eng.rank_engine)          # the migrated engine reach
        assert engine_floor                                     # non-empty floor to protect

        # build the pre-migration corpus in a sandbox (strip the appended blocks + edges)
        kdir = tmp_path / "knowledge"
        kdir.mkdir()
        for f in grade.CORPUS_FILES:
            shutil.copy(_KDIR / f, kdir / f)
        cp = json.loads((_KDIR / "component_patterns.json").read_text("utf-8"))
        for c in cp["patterns"]:
            block = sorted(_ADD.get(c["id"], set()))
            if block:
                c["signals"] = c["signals"][:-len(block)]       # undo the appended block
            c.pop("related_patterns", None)                     # undo the edge
        (kdir / "component_patterns.json").write_text(json.dumps(cp), encoding="utf-8")

        monkeypatch.setattr(grade, "KDIR", kdir)
        degraded = _covered_golds(eng.rank_engine)
        assert engine_floor - degraded                          # golds were actually evicted
        with pytest.raises(AssertionError):
            _assert_no_eviction(degraded, engine_floor)

        assert _sha(_COMPONENTS) == before                      # real corpus byte-unchanged
