# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""Shape-C signal-index engine — unit + parameterization + dual-loader proof
(story-e76bcc29, council 3e6eeeab).

Locks the ported engine (a JUSTIFIED MIRROR of the shipped mnemos/coeus
``_SignalEngine``, firewall-safe — proven by tests/test_firewall.py):

* get_signal_index is deterministic + byte-reproducible (repeat calls, a fresh
  loader, and a real PYTHONHASHSEED subprocess flip) and fails CLOSED on a hash
  collision at load;
* hydrate returns the four-state fail-closed envelope over the ``related_patterns``
  edge, deep-frozen, no husk; DANGLING is exercised by a CONSTRUCTED fixture
  (Directive 8: on the real corpus seeds always resolve and — until S2 materializes
  the edge — there is no fan-out, so the natural DANGLING state cannot occur);
* the engine lives ONCE as ``_SignalEngine`` + module free-fns, PARAMETERIZED over
  a ``_NamedIndex`` seam so the SAME primitives serve BOTH the component index
  (signals / related_patterns) and a second design_systems-shaped index (signals /
  related_systems) — with the ceilings/floor/state-vocab/_signal_id/RetrievalResult/
  deep_freeze SHARED across both and NO cross-corpus node surfacing in the wrong
  index's result (component<->system id-spaces disjoint);
* both loaders inherit the one engine — proven against a constructed tmp_path Kuzu
  DB, never the live othrys.db.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import theia.knowledge.loader as L
from theia.knowledge.loader import (
    DANGLING,
    HIT,
    LOW_CONFIDENCE,
    NO_MATCH,
    _CONFIDENCE_FLOOR,
    _SEED_CAP,
    _TOPK_CAP,
    _FrozenDict,
    _NamedIndex,
    _SignalEngine,
    KnowledgeLoader,
    RetrievalResult,
    deep_freeze,
    _signal_id,
)

_SRC = str(Path(L.__file__).resolve().parents[2])  # .../src


@pytest.fixture(scope="module")
def kb() -> KnowledgeLoader:
    return KnowledgeLoader()


def _ds_index(kb: KnowledgeLoader) -> _NamedIndex:
    """Return the loader's BUILT design_systems index (S5 wires it in ``__init__``).

    S1 parameterized the seam and proved the engine primitives are corpus-agnostic
    against an ephemeral construction; S5 builds this index for real, so the
    parameterization proofs now run over the SHIPPING ``self._systems_index`` object,
    not a throwaway."""
    assert kb._systems_index.name == "design_systems"          # S5: built, not ephemeral
    assert kb._systems_index.signal_index                       # populated at load
    return kb._systems_index


# ==========================================================================
# get_signal_index — determinism, byte-reproducibility, fail-closed collision
# ==========================================================================

class TestSignalIndex:
    def test_view_shape_is_component_ids(self, kb: KnowledgeLoader) -> None:
        idx = kb.get_signal_index()
        assert idx
        assert all(set(e) == {"signal_id", "signal_text", "component_ids"} for e in idx)
        assert all(e["signal_id"] == _signal_id(e["signal_text"]) for e in idx)

    def test_index_covers_every_distinct_component_signal(self, kb: KnowledgeLoader) -> None:
        distinct = {s.strip() for c in kb._component_patterns for s in c.get("signals", []) if s.strip()}
        assert len(kb.get_signal_index()) == len(distinct)

    def test_deterministic_and_sorted(self, kb: KnowledgeLoader) -> None:
        a = kb.get_signal_index()
        assert a == kb.get_signal_index()
        assert [e["signal_id"] for e in a] == sorted(e["signal_id"] for e in a)
        assert all(e["component_ids"] == sorted(e["component_ids"]) for e in a)

    def test_byte_reproducible_fresh_loader(self) -> None:
        dumps = [json.dumps(KnowledgeLoader().get_signal_index(), sort_keys=True) for _ in range(3)]
        assert len(set(dumps)) == 1

    def test_byte_reproducible_across_pythonhashseed(self) -> None:
        """A real PYTHONHASHSEED flip must not move the serialised index."""
        snippet = (
            "import json,hashlib;"
            "from theia.knowledge.loader import KnowledgeLoader as K;"
            "print(hashlib.sha256(json.dumps(K().get_signal_index(),sort_keys=True).encode()).hexdigest())"
        )
        import os
        env_base = {**os.environ, "PYTHONPATH": _SRC}
        outs = []
        for seed in ("0", "1", "12345"):
            r = subprocess.run(
                [sys.executable, "-c", snippet],
                capture_output=True, text=True, env={**env_base, "PYTHONHASHSEED": seed},
            )
            assert r.returncode == 0, r.stderr
            outs.append(r.stdout.strip())
        assert len(set(outs)) == 1, f"index sha256 moved across PYTHONHASHSEED: {outs}"

    def test_fail_closed_on_hash_collision(self, monkeypatch) -> None:
        """Two distinct signal texts colliding on one sid must raise at load, never
        silently merge into a corrupted index."""
        monkeypatch.setattr(L, "_signal_id", lambda _t: "sig-collide00000")
        idx = _NamedIndex(
            name="c",
            node_index={
                "a": {"id": "a", "signals": ["foo shape"]},
                "b": {"id": "b", "signals": ["bar shape"]},
            },
            signal_field="signals", edge_field="related_patterns", id_field="component_ids",
        )
        with pytest.raises(ValueError, match="collision"):
            _SignalEngine()._build_signal_index(idx)

    def test_no_collision_on_real_corpus(self) -> None:
        KnowledgeLoader()  # would raise in __init__ if the frozen corpus collided
        assert KnowledgeLoader().get_signal_index()  # non-empty, built cleanly


# ==========================================================================
# signal_ids_for — the seed-from-node accessor (drives S5's seed-from-node path)
# ==========================================================================

class TestSignalIdsFor:
    def test_returns_the_components_own_signal_ids(self, kb: KnowledgeLoader) -> None:
        comp = kb.get_component_pattern("navbar")
        expected = sorted({_signal_id(s.strip()) for s in comp["signals"] if s.strip()})
        assert kb.signal_ids_for("navbar") == expected
        idx = {e["signal_id"]: e for e in kb.get_signal_index()}
        assert all("navbar" in idx[sid]["component_ids"] for sid in kb.signal_ids_for("navbar"))

    def test_unknown_or_none_seed_is_empty(self, kb: KnowledgeLoader) -> None:
        assert kb.signal_ids_for("no-such-component") == []
        assert kb.signal_ids_for("") == []
        assert kb.signal_ids_for(None) == []

    def test_seed_hydrates_the_node(self, kb: KnowledgeLoader) -> None:
        """Seeding hydrate with a component's own signal ids self-votes it (HIT when
        it carries >=2 signals); post-S2 its resolvable neighbours also fan out."""
        res = kb.hydrate(kb.signal_ids_for("navbar"), k=10)
        assert res.state == HIT
        assert "navbar" in {p["id"] for p in res.patterns}

    def test_deterministic_and_sorted(self, kb: KnowledgeLoader) -> None:
        a = kb.signal_ids_for("navbar")
        assert a == kb.signal_ids_for("navbar") == sorted(a)


# ==========================================================================
# hydrate — four-state fail-closed envelope
# ==========================================================================

class TestHydrateStates:
    def test_hit_multi_vote(self, kb: KnowledgeLoader) -> None:
        # navbar carries >=2 signals -> seeding its own ids gives score >= floor -> HIT
        res = kb.hydrate(kb.signal_ids_for("navbar"), k=10)
        assert res.state == HIT
        assert res.patterns[0]["retrieval"]["score"] >= _CONFIDENCE_FLOOR

    def test_low_confidence_single_vote(self, kb: KnowledgeLoader) -> None:
        # fan_out=False isolates the single-direct-vote case: post-S2 the live edge
        # would otherwise accumulate one seed's neighbours to a HIT. One signal id gives
        # each carrying component exactly one direct vote -> best score 1 < floor.
        one = kb.signal_ids_for("navbar")[0]
        res = kb.hydrate([one], k=10, fan_out=False)
        assert res.state == LOW_CONFIDENCE
        assert res.patterns  # surfaced, never an empty list narrated as an answer
        assert res.patterns[0]["retrieval"]["score"] < _CONFIDENCE_FLOOR

    def test_no_match_unrecognised_signal(self, kb: KnowledgeLoader) -> None:
        res = kb.hydrate(["sig-does-not-exist"], k=10)
        assert res.state == NO_MATCH
        assert res.patterns == []          # fail closed, no husk
        assert res.votes == {}
        assert res.unmatched_signals == ["sig-does-not-exist"]

    def test_empty_input_is_no_match(self, kb: KnowledgeLoader) -> None:
        assert kb.hydrate([], k=10).state == NO_MATCH

    def test_dangling_state_constructed_fixture(self) -> None:
        """DANGLING state: EVERY hydrated id fails to resolve. Unreachable on the real
        corpus (seeds always resolve; the edge is empty at S1), so it is built
        directly (Directive 8) — an index entry pointing only at an absent id."""
        loader = KnowledgeLoader()
        ghost = "sig-ghost0000000"
        loader._component_index.signal_index[ghost] = {
            "signal_id": ghost, "signal_text": "ghost", "component_ids": ["__absent_component__"],
        }
        res = loader.hydrate([ghost], k=10)
        assert res.state == DANGLING
        assert res.patterns == []                       # no husk on DANGLING
        assert res.votes == {}
        assert "__absent_component__" in res.dangling

    def test_fanout_live_after_s2(self, kb: KnowledgeLoader) -> None:
        """S2 (story-302d9772) materialized the component ``related_patterns`` edge, so
        the fan-out is now LIVE: a seed with resolvable neighbours propagates its
        weight to them, surfacing propagated-only nodes alongside the direct seeds.
        (Supersedes the S1 empty-edge proof, which the migration deliberately kills.)"""
        assert any(c.get("related_patterns") for c in kb._component_patterns)
        res = kb.hydrate(kb.signal_ids_for("navbar"), k=10, fan_out=True)
        neighbours = {n for n in kb.get_component_pattern("navbar")["related_patterns"]
                      if kb.get_component_pattern(n)}
        propagated = {p["id"] for p in res.patterns if not p["retrieval"]["seed"]}
        assert neighbours and (neighbours & propagated)
        assert any(p["retrieval"]["propagated_votes"] > 0 for p in res.patterns)
        # the flag still genuinely gates propagation: fan_out=False -> seed-only
        res_no = kb.hydrate(kb.signal_ids_for("navbar"), k=10, fan_out=False)
        assert all(p["retrieval"]["propagated_votes"] == 0 for p in res_no.patterns)


class TestHydrateInvariants:
    def test_deep_frozen_patterns_are_read_only(self, kb: KnowledgeLoader) -> None:
        res = kb.hydrate(kb.signal_ids_for("navbar"), k=5)
        p = res.patterns[0]
        assert isinstance(p, _FrozenDict)
        with pytest.raises(TypeError):
            p["id"] = "tampered"
        assert isinstance(p["signals"], tuple)          # nested list -> immutable tuple
        with pytest.raises(AttributeError):
            p["signals"].append("x")

    def test_hydrate_does_not_corrupt_corpus(self, kb: KnowledgeLoader) -> None:
        before = list(kb.get_component_pattern("navbar")["signals"])
        kb.hydrate(kb.signal_ids_for("navbar"), k=10)
        assert kb.get_component_pattern("navbar")["signals"] == before

    def test_ranking_deterministic(self, kb: KnowledgeLoader) -> None:
        sigs = kb.signal_ids_for("navbar")
        runs = [[p["id"] for p in kb.hydrate(sigs, k=10).patterns] for _ in range(5)]
        assert all(r == runs[0] for r in runs)
        assert [p["id"] for p in KnowledgeLoader().hydrate(sigs, k=10).patterns] == runs[0]

    def test_k5_is_prefix_of_k10(self, kb: KnowledgeLoader) -> None:
        # a signal shared by several components gives a k>1 result to slice
        multi = max(kb.get_signal_index(), key=lambda e: len(e["component_ids"]))
        sigs = [multi["signal_id"]]
        b10 = [p["id"] for p in kb.hydrate(sigs, k=10).patterns]
        b5 = [p["id"] for p in kb.hydrate(sigs, k=5).patterns]
        assert b5 == b10[:5]

    def test_ceilings_unchanged(self) -> None:
        assert (_SEED_CAP, _TOPK_CAP, _CONFIDENCE_FLOOR) == (64, 50, 2)


# ==========================================================================
# Parameterization — ONE engine, TWO corpora (component + S5 design_systems)
# ==========================================================================

class TestParameterizedSecondIndex:
    def test_same_primitives_serve_the_design_systems_index(self, kb: KnowledgeLoader) -> None:
        """The engine primitives are corpus-agnostic: run over the design_systems
        _NamedIndex they build a view keyed by ``system_ids`` and hydrate systems —
        no engine code is duplicated for the second corpus (council reservation)."""
        ds = _ds_index(kb)
        view = kb._signal_index_view(ds)
        assert view and all(set(e) == {"signal_id", "signal_text", "system_ids"} for e in view)
        # seed-from-node over a system + live fan-out over its ``related_systems``
        seed_sys = next(s["id"] for s in kb._design_systems
                        if s.get("signals") and s.get("related_systems"))
        res = kb._hydrate(ds, kb._signal_ids_for(ds, seed_sys), k=10)
        assert res.state in (HIT, LOW_CONFIDENCE)
        assert seed_sys in {p["id"] for p in res.patterns}

    def test_live_edge_fan_out_propagates_on_second_index(self, kb: KnowledgeLoader) -> None:
        """Unlike the component index (empty edge at S1), design_systems carries a
        LIVE ``related_systems`` edge, so the SAME fan-out primitive propagates —
        proving the edge field is genuinely parameterized, not hardcoded."""
        ds = _ds_index(kb)
        seed_sys = "atomic_design"
        res = kb._hydrate(ds, kb._signal_ids_for(ds, seed_sys), k=10, fan_out=True)
        propagated = {p["id"] for p in res.patterns if not p["retrieval"]["seed"]}
        resolvable = {n for n in kb.get_design_system(seed_sys)["related_systems"]
                      if n in kb._design_system_index}
        assert resolvable and resolvable <= propagated

    def test_shared_primitives_are_identical_objects_across_corpora(self, kb: KnowledgeLoader) -> None:
        """The ceilings/floor/state-vocab/hash/RetrievalResult/deep_freeze are ONE
        source of truth — the second index reuses the exact same module-level
        symbols, never a re-declared copy."""
        ds = _ds_index(kb)
        # both indices are served by the very same bound-method objects
        assert kb._hydrate.__func__ is _SignalEngine._hydrate
        assert kb._build_signal_index.__func__ is _SignalEngine._build_signal_index
        assert kb._signal_index_view.__func__ is _SignalEngine._signal_index_view
        # and the second index carries no private ceiling/floor/state of its own
        assert not any(hasattr(ds, n) for n in ("_SEED_CAP", "_TOPK_CAP", "_CONFIDENCE_FLOOR"))

    def test_no_cross_corpus_leakage(self, kb: KnowledgeLoader) -> None:
        """Theia's binding reservation: a component id can NEVER surface in a
        design_systems result, nor a system id in a component result. The id-spaces
        are disjoint and each hydrate reads only its own ``_NamedIndex``."""
        comp_ids, sys_ids = set(kb._component_pattern_index), set(kb._design_system_index)
        assert not (comp_ids & sys_ids)                 # disjoint by construction
        ds = _ds_index(kb)
        ds_res = kb._hydrate(ds, kb._signal_ids_for(ds, "atomic_design"), k=50)
        assert not ({p["id"] for p in ds_res.patterns} & comp_ids)
        comp_res = kb.hydrate(kb.signal_ids_for("navbar"), k=50)
        assert not ({p["id"] for p in comp_res.patterns} & sys_ids)


# ==========================================================================
# Free-function primitives (deep_freeze) + facet gate (ported, DORMANT)
# ==========================================================================

class TestPrimitives:
    def test_deep_freeze_severs_references(self) -> None:
        src = {"a": [1, 2, {"b": 3}]}
        frozen = deep_freeze(src)
        assert isinstance(frozen, _FrozenDict)
        assert isinstance(frozen["a"], tuple)
        assert isinstance(frozen["a"][2], _FrozenDict)
        src["a"].append(99)                 # mutating the source must not touch the copy
        assert 99 not in frozen["a"]

    def test_facet_gate_dormant_on_component_corpus(self, kb: KnowledgeLoader) -> None:
        """The ported facet gate is DORMANT: no component carries an avoid_when facet
        dict, so is_gated is always False (the LIVE gate is filter_by_constraints)."""
        for comp in kb._component_patterns:
            assert L.is_gated(comp, {"team_size": "1", "scale": "startup_mvp"}) is False

    def test_split_conditions_partitions_by_type(self) -> None:
        texts, facets = L.split_conditions(["free text", {"team_size": "1-5"}, "more text"])
        assert texts == ["free text", "more text"]
        assert facets == [{"team_size": "1-5"}]

    def test_parse_team_range(self) -> None:
        assert L._parse_team_range("1-5") == (1, 5)
        assert L._parse_team_range("3") == (3, 3)
        assert L._parse_team_range("50+")[0] == 50
        assert L._parse_team_range("garbage") is None


# ==========================================================================
# Constraint filter RETAINED — the matcher is DELETED at S6 (story-041efcf4)
# ==========================================================================

# RETIRED at S6: test_match_structural_signals_present_and_callable exercised the
# exact-substring matcher (loader.match_structural_signals), deleted from both loaders at
# S6 at zero shipping/tool callers. Its frozen output is preserved by the grader's LEG-1
# source-recompute and the S0/BAR-1 pins (covered@10 35). filter_by_constraints is KEPT
# per the S6 scope (a retained filter/getter), so its presence guard stays.
class TestConstraintFilterRetained:
    def test_filter_by_constraints_present_and_callable(self, kb: KnowledgeLoader) -> None:
        rule = kb.get_rule("rule_dashboard_layout")
        assert kb.filter_by_constraints([rule], {}) == [rule]


# ==========================================================================
# Dual-loader — ONE engine, both modes (constructed tmp_path Kuzu, never live DB)
# ==========================================================================

class TestDualLoader:
    def test_both_loaders_inherit_one_engine(self) -> None:
        from theia.knowledge.graph_loader import GraphKnowledgeLoader
        assert issubclass(KnowledgeLoader, _SignalEngine)
        assert issubclass(GraphKnowledgeLoader, _SignalEngine)
        # the engine PRIMITIVES are the same objects on both (no duplicate engine code)
        assert KnowledgeLoader._hydrate is _SignalEngine._hydrate
        assert GraphKnowledgeLoader._hydrate is _SignalEngine._hydrate
        assert KnowledgeLoader._build_signal_index is _SignalEngine._build_signal_index
        # the S1-wired public bindings are inherited by the graph loader unchanged
        assert GraphKnowledgeLoader.get_signal_index is KnowledgeLoader.get_signal_index
        assert GraphKnowledgeLoader.hydrate is KnowledgeLoader.hydrate

    def test_graph_loader_read_path_delegates_to_json_engine(self, tmp_path) -> None:
        """GraphKnowledgeLoader delegates the read path to the JSON parent (Coeus
        subclass shape), so it builds the identical component signal index — proven
        against a CONSTRUCTED tmp_path Kuzu DB, never the live othrys.db."""
        kuzu = pytest.importorskip("real_ladybug", reason="kuzu/real_ladybug not installed")
        from theia.knowledge.graph_loader import GraphKnowledgeLoader
        db = kuzu.Database(str(tmp_path / "theia_engine_test.db"))
        conn = kuzu.Connection(db)
        gl = GraphKnowledgeLoader(conn)
        jl = KnowledgeLoader()
        assert gl.get_signal_index() == jl.get_signal_index()
        assert gl.hydrate(gl.signal_ids_for("navbar"), k=10).state == HIT
