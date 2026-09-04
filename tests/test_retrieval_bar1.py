# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""BAR-1 end-to-end recall@10 through the curated blind recognizer
(story-cb7e532b, S0-FIX; council 3e6eeeab; supersedes the S1/S2 degenerate-recognizer
bar of story-e76bcc29 / story-302d9772).

*** THE S0-FIX NORTH STAR. *** The predecessor recognizer was degenerate — exact
signal-text + seed-from-node only — which structurally capped the problem-language
register (PB/CE) at 0 and so measured the RECOGNIZER's poverty, not the tool. This
replaces it with a CURATED, BLIND-FROZEN per-problem recognition (theia_engine_bench
SHAPE working memory + theia_matches_v3.json), the Mnemos locked-legs parity, so
recall@10 is a real, reproducible END-TO-END number through the production
``loader.hydrate`` path and a DURABLE regression guard. This test proves, REPRODUCED
not re-derived, stratified per S0 (never a pooled mean, m-e8ccb163):

  * the problem-language register the degenerate recognizer hid is now MEASURED:
    PB 0 -> 16/20, CE 0 -> 2/2 (the PB lift validated end-to-end through audit_design
    in tests/test_audit_design.py rides the same hydrate path);
  * the pinned matcher baseline is UNCHANGED (35/58) and the retrieval SYSTEM (matcher
    UNION the production hydrate path) does NOT regress (>=35/58) — the recognizer is
    additive, the matcher untouched;
  * the pure engine (45/58) does NOT clear the three S0-locked legs (LEG_2 floor
    47/58): leg-clearance is GATED to the production-LLM recognizer story
    (86822862-decision-2 / 905db0ec-decision-0). A component-space hydrate never emits
    the 8 PA rule-id golds, so the blind-bench ceiling is ~50/58 and 45 is the honest
    blind reach — a MEASURED gate to the next story, never hand-waved;
  * recognition is REPRODUCIBLE (live recognize == the frozen theia_matches_v3
    snapshot, so no hand-edit hides in the measured path), gold-BLIND (never reads the
    answer key), and DETERMINISTIC (byte-identical across 3 fresh loaders);
  * the benchmark is a DURABLE GUARD: a planted retrieval regression drops recall AND
    trips the covered-gold ratchet.

Substrate is pinned two ways, both fail-closed: the S0 corpus/benchmark via
freeze_manifest_v3.json (grade._verify_substrate, verbatim) and the recognizer via
theia_matches_freeze_v3.json. The recognition never authors per-problem gold vocab —
SHAPE is a designer's restatement of the problem, the mechanical matcher picks ids.

Firewall: imports only theia.* + the frozen grader + the engine bench (theia-only).
Never opens the live Othrys DB.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

_GMETRIC = Path(__file__).resolve().parent / "data" / "gmetric"
if str(_GMETRIC) not in sys.path:
    sys.path.insert(0, str(_GMETRIC))

import grade  # noqa: E402  (frozen deterministic grader, reused verbatim, theia-only)
import theia_engine_bench as eng  # noqa: E402  (curated blind Shape-C harness)

# Version-resolved through grade (conftest defaults the session to the live trust
# root v3, which pins the recognizer snapshot). The matcher baseline is byte-identical
# across v1/v2/v3 (the matcher was untouched), so the non-regression comparand is stable.
BASELINE = json.loads(grade.BASELINE_OUT.read_text(encoding="utf-8"))
LEGS = json.loads((_GMETRIC / f"locked_legs_{grade._VER}.json").read_text(encoding="utf-8"))
MATCHES_FROZEN = json.loads((_GMETRIC / f"theia_matches_{grade._VER}.json").read_text(encoding="utf-8"))
MATCHES_FREEZE = json.loads(
    (_GMETRIC / f"theia_matches_freeze_{grade._VER}.json").read_text(encoding="utf-8")
)

_BASELINE_COVERED_10 = BASELINE["RESULT_baseline"]["covered"]["10"]  # 35
_DENOM = BASELINE["RESULT_baseline"]["denominator_E_golds"]          # 58

# The measured blind-recognizer reach (pinned floors — the durable regression guard).
_ENGINE_COVERED_10 = 45      # PA 16 + PB 16 + TK 6 + SEED 5 + CE 2
_ENGINE_PB_10 = 16           # of 20  (was 0 under the degenerate recognizer)
_ENGINE_CE_10 = 2            # of 2   (was 0)
_UNION_COVERED_10 = 53


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def engine_core() -> dict:
    return grade.grade(eng.rank_engine, "shape_c_engine")


@pytest.fixture(scope="module")
def union_core() -> dict:
    return grade.grade(eng.rank_union, "matcher_union_engine")


@pytest.fixture(scope="module")
def baseline_core() -> dict:
    return grade.grade(grade.rank_baseline, "baseline_four_surface_matcher")


# ==========================================================================
# Substrate — fail closed on any drift (S0 corpus + the recognizer snapshot)
# ==========================================================================

class TestSubstrate:
    def test_s0_substrate_matches_frozen_pins(self) -> None:
        grade._verify_substrate()  # raises SystemExit on any drift

    def test_recognizer_substrate_matches_frozen_pins(self) -> None:
        """theia_matches_v3.json + the corpus its signal index derives from match the
        recognizer pins (a separate trust root from the S0 manifest)."""
        pins = MATCHES_FREEZE["pins"]
        paths = {
            f"theia_matches_{grade._VER}.json": _GMETRIC / f"theia_matches_{grade._VER}.json",
            grade.PROBLEMS_IN.name: grade.PROBLEMS_IN,
            "component_patterns.json": grade.KDIR / "component_patterns.json",
        }
        assert set(pins) == set(paths), "recognizer manifest pin set mismatch"
        for name, p in paths.items():
            assert _sha256(p) == pins[name], f"{name} drifted from the recognizer pin"

    def test_recognition_is_reproducible(self) -> None:
        """Live recognition == the frozen snapshot: the pinned matches are exactly what
        theia_engine_bench produces from problems_blind + the index (no hidden hand-edit)."""
        live = eng.build_matches(grade.KnowledgeLoader(knowledge_dir=grade.KDIR))
        assert live == MATCHES_FROZEN["matches"]

    def test_all_matched_signals_resolve(self) -> None:
        idx_ids = {e["signal_id"] for e in grade.KnowledgeLoader(knowledge_dir=grade.KDIR).get_signal_index()}
        unresolved = {p: [s for s in sigs if s not in idx_ids]
                      for p, sigs in MATCHES_FROZEN["matches"].items()}
        unresolved = {p: v for p, v in unresolved.items() if v}
        assert not unresolved, f"unresolved matched signals: {unresolved}"

    def test_engine_bench_is_gold_blind(self) -> None:
        """The harness never reads the answer key (gmetric_*.json) in executable code —
        it reads only problems_blind + the loader's live index. Docstrings (which cite
        the answer key by name to explain the discipline) are excluded; only string
        literals used in real statements are scanned."""
        import ast
        tree = ast.parse((_GMETRIC / "theia_engine_bench.py").read_text(encoding="utf-8"))
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                body = getattr(node, "body", [])
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                        and isinstance(body[0].value.value, str):
                    docstrings.add(id(body[0].value))
        offenders = [n.value for n in ast.walk(tree)
                     if isinstance(n, ast.Constant) and isinstance(n.value, str)
                     and id(n) not in docstrings and "gmetric_" in n.value]
        assert not offenders, f"harness reads the answer key in code: {offenders}"

    def test_shape_encodes_no_underscore_component_id(self) -> None:
        """Blind-curation guard: SHAPE is a designer's problem restatement in
        space-separated words, NEVER a verbatim corpus id. No SHAPE string contains an
        underscore/kebab component id (which would encode an answer instead of bridging
        to a signal text). A space-separated english word that happens to equal a
        one-word id (grid, modal, badge, card, tag) is problem language, not an id."""
        loader = grade.KnowledgeLoader(knowledge_dir=grade.KDIR)
        multiword_ids = [c["id"] for c in loader._component_patterns
                         if ("_" in c["id"] or "-" in c["id"])]
        leaks = {pid: [cid for cid in multiword_ids if cid in shape]
                 for pid, shape in eng.SHAPE.items()}
        leaks = {pid: v for pid, v in leaks.items() if v}
        assert not leaks, f"SHAPE encodes a corpus id verbatim: {leaks}"


# ==========================================================================
# Non-regression — the matcher is untouched, the recognizer additive
# ==========================================================================

class TestNonRegression:
    def test_baseline_unchanged_matcher_untouched(self, baseline_core: dict) -> None:
        """The pinned matcher baseline still measures 35/58 — the recognizer replacement
        touched no existing surface, so the existing capability is preserved."""
        assert baseline_core["covered"]["10"] == _BASELINE_COVERED_10 == 35
        assert baseline_core["covered"] == BASELINE["RESULT_baseline"]["covered"]

    def test_union_does_not_regress_reproduced_through_hydrate(self, union_core: dict) -> None:
        """The retrieval SYSTEM (matcher UNION the production hydrate path) does not drop
        below the baseline and now covers the problem-language register. rank_union
        routes through loader.hydrate, so this IS BAR-1 reproduced through the ported
        hydrate, additive over the matcher."""
        assert union_core["covered"]["10"] >= _BASELINE_COVERED_10
        assert union_core["covered"]["10"] == _UNION_COVERED_10 == 53
        assert union_core["denominator_E_golds"] == _DENOM
        assert union_core["by_qclass"]["PB"]["10"]["covered"] > 0

    def test_union_recomputes_live_not_trusted(self, union_core: dict) -> None:
        """Recompute the union live and confirm the covered count is stable (measured
        here, not read from a pin)."""
        again = grade.grade(eng.rank_union, "u")
        assert again["covered"] == union_core["covered"]

    def test_reported_stratified_never_pooled(self, union_core: dict, engine_core: dict) -> None:
        """Every number is reported by qclass (m-e8ccb163). The PB/CE problem-language
        register is now VISIBLE and non-zero (the whole point), not hidden in a pooled
        mean and no longer stuck at 0."""
        for core in (union_core, engine_core):
            assert {"PA", "PB", "TK", "SEED", "CE"} <= set(core["by_qclass"])
        assert engine_core["by_qclass"]["PB"]["10"]["covered"] == _ENGINE_PB_10 > 0
        assert engine_core["by_qclass"]["CE"]["10"]["covered"] == _ENGINE_CE_10 > 0


# ==========================================================================
# Engine reach — the measured blind recall, stratified (PB/CE now real)
# ==========================================================================

class TestEngineReach:
    def test_engine_recovers_all_token_classes(self, engine_core: dict) -> None:
        """The pure hydrate path fully recovers the token classes: TK (query IS a
        component id) and SEED (seed-from-node + SHAPE resolving the archetype huskies
        'input'->text_input, 'navigation'->navbar)."""
        by = engine_core["by_qclass"]
        assert by["TK"]["10"]["covered"] == 6
        assert by["SEED"]["10"]["covered"] == 5

    def test_engine_lifts_the_problem_language_register(self, engine_core: dict) -> None:
        """The S0-FIX outcome: the problem-language register the degenerate recognizer
        capped at 0 is now MEASURED and non-trivial (PB 16/20, CE 2/2), lifted by the
        curated BLIND SHAPE recognition, not gamed — three PB problems remain honest
        partial misses (P10 1/3, P11 1/2, P14 2/3), left untuned."""
        by = engine_core["by_qclass"]
        assert by["PB"]["10"]["covered"] == _ENGINE_PB_10 == 16   # was 0 (degenerate)
        assert by["CE"]["10"]["covered"] == _ENGINE_CE_10 == 2    # was 0
        assert by["PA"]["10"]["covered"] == 16                    # component golds only
        assert engine_core["covered"]["10"] == _ENGINE_COVERED_10 == 45


# ==========================================================================
# Legs GATED to the LLM-recognizer story — asserted so the gate is measured
# ==========================================================================

class TestLegsGatedToLLMRecognizer:
    def test_pure_engine_does_not_clear_the_legs(self, engine_core: dict, baseline_core: dict) -> None:
        """The three legs are NOT cleared by the blind-bench engine — proven, so the
        deferral to the production-LLM recognizer story is a measured fact. LEG_2 floor
        is 47/58; the engine is 45 (a component-space hydrate never emits the 8 PA
        rule-id golds, ceiling ~50). LEG_1 delta 0.20 over baseline is also not met."""
        assert engine_core["covered"]["10"] < LEGS["LEG_2_design_works_floor"]["engine_min_covered_at_10"]
        delta = round(engine_core["recall"]["10"] - baseline_core["recall"]["10"], 4)
        assert delta < LEGS["LEG_1_primary_delta"]["delta_bar"]

    def test_legs_remain_locked(self) -> None:
        """The S0-locked legs are untouched by the S0-FIX re-freeze — same bar, re-pinned
        on v3 byte-identical, still the LLM-recognizer story's bar."""
        assert LEGS["status"] == "LOCKED"
        assert LEGS["LEG_2_design_works_floor"]["engine_min_covered_at_10"] == 47


# ==========================================================================
# Determinism — byte-identical across fresh loaders
# ==========================================================================

class TestDeterminism:
    def test_engine_three_fresh_runs_byte_identical(self) -> None:
        cores = [grade.grade(eng.rank_engine, "e") for _ in range(3)]
        shas = {grade.result_core_sha256(c) for c in cores}
        assert len(shas) == 1

    def test_union_three_fresh_runs_byte_identical(self) -> None:
        cores = [grade.grade(eng.rank_union, "u") for _ in range(3)]
        shas = {grade.result_core_sha256(c) for c in cores}
        assert len(shas) == 1

    def test_engine_k5_prefix_of_k10_all_problems(self) -> None:
        loader = grade.KnowledgeLoader(knowledge_dir=grade.KDIR)
        for pid, sigs in MATCHES_FROZEN["matches"].items():
            b10 = [n["id"] for n in loader.hydrate(sigs, k=10).patterns]
            b5 = [n["id"] for n in loader.hydrate(sigs, k=5).patterns]
            assert b5 == b10[:5], f"{pid}: k5 not a prefix of k10"


# ==========================================================================
# DURABLE GUARD — a planted retrieval regression drops recall + trips the ratchet
# ==========================================================================

def _covered_golds(method_fn) -> set:
    core = grade.grade(method_fn, "m")
    return {(pid, g) for pid, row in core["per_problem"].items()
            for g in row["grades"]["10"]["covered_golds"]}


class TestGuardBites:
    def test_planted_retrieval_regression_drops_recall_and_trips_ratchet(self, engine_core: dict) -> None:
        """RED: the benchmark is a real regression guard. The healthy engine covers 45
        E-golds@10; plant a retrieval regression (disable the one-hop fan-out edge the
        production hydrate propagates over) and recall drops AND specific golds are
        evicted — so a covered-gold ratchet pinned at today's reach fails closed. This
        is the guard every FUTURE retrieval change trips if it regresses."""
        healthy = _covered_golds(eng.rank_engine)
        assert engine_core["covered"]["10"] == len(healthy) == _ENGINE_COVERED_10

        def rank_regressed(loader, query: list[str]) -> list[str]:
            pid = eng._query_to_pid().get(tuple(query))
            shape = eng.SHAPE.get(pid, "") if pid else ""
            matched = eng.recognize(loader, query, shape)
            res = loader.hydrate(matched, k=10, fan_out=False)  # regression: fan-out removed
            return [p["id"] for p in res.patterns]

        regressed_core = grade.grade(rank_regressed, "regressed")
        regressed = _covered_golds(rank_regressed)

        # recall drops
        assert regressed_core["covered"]["10"] < engine_core["covered"]["10"]
        # specific golds evicted (the ratchet has teeth, not just a pooled dip)
        evicted = healthy - regressed
        assert evicted, "planted regression evicted no gold — guard is toothless"
        # the ratchet FAILS CLOSED on the regression
        with pytest.raises(AssertionError):
            assert healthy <= regressed, f"evicted: {sorted(healthy - regressed)}"
