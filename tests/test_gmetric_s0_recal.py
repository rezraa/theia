# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""Themis ratification gate for the v4 leg RE-CALIBRATION (story-846210c3; council
905db0ec REVISE = EXCLUDE, not re-label).

*** THE NORTH STAR. *** The formal S0 legs (>=47/58 floor, +0.20 delta) were set at S0
before it was understood that 8 of the PA golds are decision-RULE ids a COMPONENT-space
engine structurally cannot emit (loader.hydrate returns component patterns, never a rule
id). This gate proves the v4 re-calibration EXCLUDES those 8 from the recall denominator
(58->50) on HONEST, UNCHANGED retrieval -- the numerator stays 45 -- so the engine clears
the legs at 45/50 = 0.90, never on inflated labels:

  * numerator INVARIANT: engine covered@10 is still 45 (PA 16 + PB 16 + TK 6 + SEED 5 +
    CE 2); PB 16/20 and CE 2/2 unchanged; the retrieval SYSTEM (union) still 45 over the
    50-set -- the exclusion moved the DENOMINATOR, not the retrieval;
  * the 8 excluded golds are EXACTLY the rule-space golds (verdict X: exists-in-corpus,
    excluded-from-recall), a component-space engine covers 0 of them (measured), and the
    retired matcher's rule-id leg covered all 8 -- the structural id-space mismatch;
  * derivation-EVIDENCED, non-gaming: every RESOLVABLE recommended_pattern of an excluded
    rule is ALREADY an independent E-gold in the same problem, so a re-label would add
    zero new retrieval while inflating covered@10 -- the reason EXCLUDE was chosen;
  * rule_color_only (P08) is a genuine CONTENT gap (all three recommendeds dangle),
    recorded as an authoring follow-up, NO component invented;
  * the three legs, re-calibrated from the v4 baseline (27/50 = 0.54), CLEAR: LEG_2
    0.90 >= 0.80; LEG_1 delta 0.90 - 0.54 = 0.36 >= 0.20; LEG_3 engine>=baseline on
    30/31 >= 27;
  * v1/v2/v3 are RETAINED byte-identical (the exclusion is additive, v4 only);
  * the CWE-345 trust spine holds on v4 (substrate fails closed) and the v4 result core
    is deterministic across fresh loaders + PYTHONHASHSEED.

Firewall: imports only theia.* + the frozen grader + the engine bench (theia-only).
Never opens the live Othrys DB.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_GMETRIC = Path(__file__).resolve().parent / "data" / "gmetric"
if str(_GMETRIC) not in sys.path:
    sys.path.insert(0, str(_GMETRIC))

import grade  # noqa: E402  (frozen deterministic grader, theia-only)
import theia_engine_bench as eng  # noqa: E402  (curated blind Shape-C harness)

_PY = sys.executable
_SRC = str(Path(__file__).resolve().parents[1] / "src")

V4_FILES = {
    "GMETRIC_IN": "gmetric_v4.json",
    "PROBLEMS_IN": "problems_blind_v4.json",
    "FREEZE_MANIFEST": "freeze_manifest_v4.json",
    "BASELINE_OUT": "baseline_matcher_pinned_v4.json",
}


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture()
def v4(monkeypatch):
    """Repoint the grader at the v4 frozen set (in-process, auto-reverted) and return the
    graded cores + the locked-legs. The engine/baseline/union method_fns are version-
    independent; the DENOMINATOR (which golds are E) comes from grade.GMETRIC_IN."""
    for attr, name in V4_FILES.items():
        f = _GMETRIC / name
        if not f.exists():
            pytest.fail(f"v4 artifact missing: {name} -- build v4 (build_gmetric_v1.py -> "
                        f"grade.py --refreeze -> set_locked_legs.py, THEIA_GMETRIC_VERSION=v4)")
        monkeypatch.setattr(grade, attr, f)
    grade._verify_substrate()  # raises SystemExit on any drift
    return {
        "engine": grade.grade(eng.rank_engine, "shape_c_engine"),
        "baseline": grade.grade(grade.rank_baseline, "baseline_four_surface_matcher"),
        "union": grade.grade(eng.rank_union, "matcher_union_engine"),
        "legs": json.loads((_GMETRIC / "locked_legs_v4.json").read_text(encoding="utf-8")),
        "gmetric": json.loads((_GMETRIC / "gmetric_v4.json").read_text(encoding="utf-8")),
        "baseline_pin": json.loads((_GMETRIC / "baseline_matcher_pinned_v4.json").read_text(encoding="utf-8")),
        "manifest": json.loads((_GMETRIC / "freeze_manifest_v4.json").read_text(encoding="utf-8")),
    }


# ==========================================================================
# The numerator is UNCHANGED -- the exclusion moves the denominator, not retrieval
# ==========================================================================

class TestNumeratorInvariant:
    def test_engine_covered_unchanged_at_45(self, v4) -> None:
        """The retrieval is byte-for-byte the same; only the denominator moved."""
        assert v4["engine"]["covered"]["10"] == 45
        by = v4["engine"]["by_qclass"]
        assert by["PA"]["10"]["covered"] == 16   # component golds only (8 rule golds excluded)
        assert by["PB"]["10"]["covered"] == 16   # unchanged from v3
        assert by["CE"]["10"]["covered"] == 2    # unchanged from v3
        assert by["TK"]["10"]["covered"] == 6
        assert by["SEED"]["10"]["covered"] == 5

    def test_denominator_moved_58_to_50(self, v4) -> None:
        assert v4["engine"]["denominator_E_golds"] == 50
        assert v4["baseline"]["denominator_E_golds"] == 50
        assert v4["union"]["denominator_E_golds"] == 50

    def test_baseline_and_union_over_the_50_set(self, v4) -> None:
        # baseline loses the 8 rule-id golds it covered for free (35 -> 27); union 45.
        assert v4["baseline"]["covered"]["10"] == 27
        assert v4["union"]["covered"]["10"] == 45


# ==========================================================================
# The 8 excluded golds are exactly the rule-space golds; engine covers 0
# ==========================================================================

class TestExclusionIsRuleSpaceOnly:
    def test_excluded_are_the_eight_source_rule_golds(self, v4) -> None:
        loader = grade.KnowledgeLoader(knowledge_dir=grade.KDIR)
        rule_ids = {r["id"] for r in loader._decision_rules}
        excluded = [r for r in v4["gmetric"]["reachable_set_map"] if r["verdict"] == "X"]
        assert len(excluded) == 8
        assert {r["problem"] for r in excluded} == {f"P0{i}" for i in range(1, 9)}
        for r in excluded:
            assert r["role"] == "source_rule"
            assert set(r["acceptable_ids"]) <= rule_ids
            assert r["structure"] == "decision_rule"

    def test_engine_covers_zero_of_the_excluded(self, v4) -> None:
        """A component-space hydrate emits no rule id -> 0/8. This is the structural
        reason the golds are excluded, measured end-to-end through grade.grade()."""
        excluded = {(r["problem"], r["canonical"])
                    for r in v4["gmetric"]["reachable_set_map"] if r["verdict"] == "X"}
        eng_cov = {(pid, g) for pid, row in v4["engine"]["per_problem"].items()
                   for g in row["grades"]["10"]["covered_golds"]}
        assert not (eng_cov & excluded)


# ==========================================================================
# The three legs CLEAR on honest retrieval (the north star)
# ==========================================================================

class TestLegsClear:
    def test_leg_2_design_works_floor(self, v4) -> None:
        floor = v4["legs"]["LEG_2_design_works_floor"]
        assert v4["engine"]["recall"]["10"] >= floor["floor"] == 0.80
        assert v4["engine"]["covered"]["10"] >= floor["engine_min_covered_at_10"]

    def test_leg_1_primary_delta(self, v4) -> None:
        leg1 = v4["legs"]["LEG_1_primary_delta"]
        delta = round(v4["engine"]["recall"]["10"] - v4["baseline"]["recall"]["10"], 4)
        assert delta >= leg1["delta_bar"] == 0.20
        assert v4["engine"]["covered"]["10"] >= leg1["engine_min_covered_at_10"]

    def test_leg_3_distribution_wins(self, v4) -> None:
        leg3 = v4["legs"]["LEG_3_distribution_wins"]
        ge = 0
        for pid, erow in v4["engine"]["per_problem"].items():
            brow = v4["baseline"]["per_problem"][pid]
            if erow["grades"]["10"]["covered"] >= brow["grades"]["10"]["covered"]:
                ge += 1
        assert ge >= leg3["min_problems_ge_baseline"] == 27
        assert ge == 30  # the one loss is P08's tooltip (the content-gap problem)

    def test_all_three_legs_pass_verdict_rule(self, v4) -> None:
        """PASS = LEG_1 AND LEG_2 AND LEG_3 (the legs' own verdict_rule)."""
        e_cov, e_rec = v4["engine"]["covered"]["10"], v4["engine"]["recall"]["10"]
        legs = v4["legs"]
        leg2 = e_rec >= legs["LEG_2_design_works_floor"]["floor"]
        leg1 = round(e_rec - v4["baseline"]["recall"]["10"], 4) >= legs["LEG_1_primary_delta"]["delta_bar"]
        ge = sum(1 for pid, er in v4["engine"]["per_problem"].items()
                 if er["grades"]["10"]["covered"] >= v4["baseline"]["per_problem"][pid]["grades"]["10"]["covered"])
        leg3 = ge >= legs["LEG_3_distribution_wins"]["min_problems_ge_baseline"]
        assert leg1 and leg2 and leg3

    def test_legs_calibrated_from_the_v4_baseline(self, v4) -> None:
        snap = v4["legs"]["baseline_snapshot"]
        assert snap["covered_at_10"] == 27
        assert snap["denominator_E_golds"] == 50
        assert snap["recall_at_10"] == 0.54


# ==========================================================================
# The exclusion ledger -- derivation chain + non-gaming evidence
# ==========================================================================

class TestExclusionLedger:
    def test_ledger_present_and_complete(self, v4) -> None:
        led = v4["gmetric"]["recalibration_v4_exclusion_ledger"]
        assert led["mechanism"].startswith("EXCLUDE")
        assert led["recall_denominator_before"] == 58
        assert led["recall_denominator_after"] == 50
        assert led["excluded_count"] == 8
        assert len(led["golds"]) == 8

    def test_resolvable_targets_are_already_scored_golds(self, v4) -> None:
        """The non-gaming evidence: every RESOLVABLE recommended target of P01-P07 is
        already an independent E-gold in the same problem -> a re-label adds zero new
        retrieval (the reason EXCLUDE beats re-label)."""
        led = v4["gmetric"]["recalibration_v4_exclusion_ledger"]
        for g in led["golds"]:
            if g["resolvable_targets"]:  # P08 has none (all dangle)
                assert g["all_resolvable_targets_already_scored_golds"], g["rule_id"]
                for c in g["derivation"]:
                    if c["resolves_to_component"]:
                        assert c["already_scored_E_gold_in_same_problem"], (g["rule_id"], c)

    def test_p08_recorded_as_content_gap(self, v4) -> None:
        led = v4["gmetric"]["recalibration_v4_exclusion_ledger"]
        assert "rule_color_only" in led["content_gap_followups"]
        p08 = next(g for g in led["golds"] if g["rule_id"] == "rule_color_only")
        assert p08["resolvable_targets"] == []
        assert {c["recommended_pattern"] for c in p08["derivation"]} == {
            "badge_with_label", "icon_status", "text_label"}
        assert all(c["resolves_to_component"] is None for c in p08["derivation"])


# ==========================================================================
# Content coverage is UNCHANGED -- the corpus did not move (X still EXISTS)
# ==========================================================================

class TestContentCoverageUnchanged:
    def test_content_existence_unchanged_from_v3(self, v4) -> None:
        """m-0364c120: content existence is method-independent. The 8 rules still EXIST;
        the exclusion is a RECALL decision. So content coverage is byte-for-byte v3."""
        content = v4["gmetric"]["2_denominators"]["content_method_independent"]
        assert content["content_coverage_E_over_total"] == 0.9667
        assert content["tally"]["E_exists"] == 50
        assert content["tally"]["X_excluded_from_recall"] == 8
        assert content["tally"]["A_absent"] == 2


# ==========================================================================
# Trust spine (CWE-345) holds on v4 + determinism
# ==========================================================================

class TestTrustSpineV4:
    def test_answer_key_content_hashed_and_pinned(self, v4) -> None:
        for attr in ("GMETRIC_IN", "PROBLEMS_IN", "FREEZE_MANIFEST", "BASELINE_OUT"):
            setattr(grade, attr, _GMETRIC / V4_FILES[attr])
        ak = grade.answer_key_sha256_from_gmetric()
        assert v4["manifest"]["answer_key_sha256"] == ak
        assert v4["baseline_pin"]["determinism"]["answer_key_sha256"] == ak
        assert v4["gmetric"]["3_score"]["answer_key_sha256"] == ak

    def test_manifest_pins_the_v4_set(self, v4) -> None:
        expected = {"problems_blind_v4.json", "gmetric_v4.json",
                    "component_patterns.json", "decision_rules.json",
                    "design_systems.json", "accessibility_standards.json"}
        assert set(v4["manifest"]["pins"]) == expected

    def test_v4_result_core_deterministic_fresh_loaders(self, v4) -> None:
        cores = [grade.grade(eng.rank_engine, "e") for _ in range(3)]
        assert len({grade.result_core_sha256(c) for c in cores}) == 1

    @pytest.mark.parametrize("seed", ["0", "1", "42"])
    def test_v4_pythonhashseed_stable(self, seed: str) -> None:
        """A real subprocess with PYTHONHASHSEED + THEIA_GMETRIC_VERSION=v4 recomputes a
        stable baseline core sha (the reproducibility invariant is the result core)."""
        code = (
            "import sys; sys.path.insert(0, r'%s'); import grade; "
            "c = grade.grade(grade.rank_baseline, 'b'); "
            "print(grade.result_core_sha256(c))" % str(_GMETRIC)
        )
        env = {**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": _SRC,
               "THEIA_GMETRIC_VERSION": "v4"}
        out = subprocess.run([_PY, "-c", code], capture_output=True, text=True, env=env)
        assert out.returncode == 0, out.stderr
        first = out.stdout.strip()
        out2 = subprocess.run([_PY, "-c", code], capture_output=True, text=True, env=env)
        assert out2.stdout.strip() == first

    def test_v4_substrate_fails_closed_on_gold_flip(self, tmp_path, monkeypatch) -> None:
        """The CWE-345 spine holds on v4: a flipped acceptable_id trips SUBSTRATE DRIFT."""
        gdir = tmp_path / "gmetric"
        kdir = tmp_path / "knowledge"
        gdir.mkdir()
        kdir.mkdir()
        for name in V4_FILES.values():
            shutil.copy(_GMETRIC / name, gdir / name)
        for name in grade.CORPUS_FILES:
            shutil.copy(grade.KDIR / name, kdir / name)
        for attr, name in V4_FILES.items():
            monkeypatch.setattr(grade, attr, gdir / name)
        monkeypatch.setattr(grade, "KDIR", kdir)
        gm = json.loads(grade.GMETRIC_IN.read_text(encoding="utf-8"))
        for row in gm["reachable_set_map"]:
            if row["verdict"] == "E":
                row["acceptable_ids"] = ["wrong_id"]
                break
        grade.GMETRIC_IN.write_text(json.dumps(gm, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with pytest.raises(SystemExit, match="SUBSTRATE DRIFT"):
            grade._verify_substrate()


# ==========================================================================
# v1/v2/v3 RETAINED byte-identical (the exclusion is additive, v4 only)
# ==========================================================================

class TestPriorVersionsRetained:
    @pytest.mark.parametrize("ver", ["v1", "v2", "v3"])
    def test_prior_gmetric_and_problems_match_their_manifest_pins(self, ver: str) -> None:
        suf = "" if ver == "v1" else f"_{ver}"
        manifest = json.loads((_GMETRIC / f"freeze_manifest{suf}.json").read_text(encoding="utf-8"))
        for name in (f"gmetric_{ver}.json", f"problems_blind_{ver}.json"):
            assert _sha(_GMETRIC / name) == manifest["pins"][name], f"{name} drifted"

    @pytest.mark.parametrize("ver", ["v1", "v2", "v3"])
    def test_prior_versions_have_no_excluded_golds(self, ver: str) -> None:
        gm = json.loads((_GMETRIC / f"gmetric_{ver}.json").read_text(encoding="utf-8"))
        assert not [r for r in gm["reachable_set_map"] if r["verdict"] == "X"]
        assert sum(1 for r in gm["reachable_set_map"] if r["verdict"] == "E") == 58
