# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""Themis ratification gate for theia-Gmetric-v1 (story-af407698, S0 BLOCKS ALL).

RED-first outcome gate. Proves the frozen, blind, stratified design-retrieval
benchmark is an HONEST outcome gate before any later Theia retrieval story unblocks:

  * the pinned four-surface matcher baseline is deterministic + STRATIFIED, and
    NON-strawman (PA answers its own idiom, TK resolves its own tokens);
  * the THREE denominators are reported SEPARATELY and never conflated;
  * the corpus is a REACHABILITY gap, not a content gap, BY MEASUREMENT;
  * the grader is byte-identical across 3 fresh loaders + PYTHONHASHSEED {0,1,42};
  * the substrate FAILS CLOSED -- gold-flip, answer-key widening, and manifest
    regeneration are all BLOCKED; only an explicit --refreeze mutates the pin;
  * the three locked legs were set AFTER the baseline read.

Firewall: imports only theia.* + the frozen grader (read via sys.path, theia-only).
Never opens the live Othrys DB.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_GMETRIC = Path(__file__).resolve().parent / "data" / "gmetric"
if str(_GMETRIC) not in sys.path:
    sys.path.insert(0, str(_GMETRIC))

import grade  # noqa: E402  (frozen deterministic grader, theia-only imports)

# Version-resolved through grade (THEIA_GMETRIC_VERSION; conftest defaults the session
# to the live trust root v2). v1 is retained on disk but its pins predate the S2 corpus
# migration, so this ratification runs against the ACTIVE frozen set, not stale v1 pins.
GMETRIC = json.loads(grade.GMETRIC_IN.read_text(encoding="utf-8"))
PROBLEMS = json.loads(grade.PROBLEMS_IN.read_text(encoding="utf-8"))
BASELINE = json.loads(grade.BASELINE_OUT.read_text(encoding="utf-8"))
LEGS = json.loads((_GMETRIC / f"locked_legs_{grade._VER}.json").read_text(encoding="utf-8"))
MANIFEST = json.loads(grade.FREEZE_MANIFEST.read_text(encoding="utf-8"))

_PY = sys.executable
_SRC = str(Path(__file__).resolve().parents[1] / "src")


# ==========================================================================
# Substrate — clean, and the answer key is content-hashed
# ==========================================================================

class TestSubstrate:
    def test_substrate_verifies_clean(self) -> None:
        checks = grade._verify_substrate()  # raises SystemExit on any drift
        assert all(c["match"] for c in checks.values())

    def test_answer_key_is_content_hashed_and_pinned(self) -> None:
        """The E-gold answer key is content-hashed and pinned in BOTH the external
        manifest and the baseline (defense in depth against acceptable_ids widening)."""
        ak = grade.answer_key_sha256_from_gmetric()
        assert MANIFEST["answer_key_sha256"] == ak
        assert BASELINE["determinism"]["answer_key_sha256"] == ak
        assert GMETRIC["3_score"]["answer_key_sha256"] == ak

    def test_manifest_pins_all_load_bearing_files(self) -> None:
        expected = {grade.PROBLEMS_IN.name, grade.GMETRIC_IN.name,
                    "component_patterns.json", "decision_rules.json",
                    "design_systems.json", "accessibility_standards.json"}
        assert set(MANIFEST["pins"]) == expected


# ==========================================================================
# Benchmark shape — blind, verbatim, stratified, N>=25
# ==========================================================================

class TestBenchmarkShape:
    def test_at_least_25_blind_problems(self) -> None:
        assert PROBLEMS["n_problems"] >= 25
        assert len(PROBLEMS["problems"]) == PROBLEMS["n_problems"]

    def test_all_five_strata_present(self) -> None:
        qclasses = {p["qclass"] for p in PROBLEMS["problems"]}
        assert {"PA", "PB", "TK", "SEED", "CE"} <= qclasses

    def test_every_E_gold_is_a_real_corpus_id(self) -> None:
        """No fabricated golds -- every E acceptable_id resolves in the 240-node corpus."""
        loader = grade.KnowledgeLoader(knowledge_dir=grade.KDIR)
        comp = {p["id"] for p in loader._component_patterns}
        rules = {r["id"] for r in loader._decision_rules}
        systems = {s["id"] for s in loader._design_systems}
        a11y = {a["id"] for a in loader._accessibility_standards}
        corpus = comp | rules | systems | a11y
        for row in GMETRIC["reachable_set_map"]:
            if row["verdict"] == "E":
                for cid in row["acceptable_ids"]:
                    assert cid in corpus, f"fabricated E acc id {cid} in {row['problem']}"

    def test_no_authored_prose_query_leaks_a_gold_id(self) -> None:
        """d-6146f069: authored problem-language (PB/CE) never contains its gold id.
        (PA is verbatim rule-prose from the corpus; TK/SEED feed the token by design.)"""
        for p in PROBLEMS["problems"]:
            if p["qclass"] in ("PB", "CE"):
                ql = " ".join(p["query"]).lower()
                for g in p["golds"]:
                    cid = g["canonical"].lower()
                    assert not (cid in ql or cid.replace("_", " ") in ql or cid.replace("_", "-") in ql), \
                        f"{p['id']} leaks gold {g['canonical']}"

    def test_PA_queries_are_verbatim_rule_signals(self) -> None:
        """PA provenance: each PA query is a real rule structural_signal (not tuned)."""
        loader = grade.KnowledgeLoader(knowledge_dir=grade.KDIR)
        sigs = {s for r in loader._decision_rules for s in r.get("structural_signals", [])}
        for p in PROBLEMS["problems"]:
            if p["qclass"] == "PA":
                for q in p["query"]:
                    assert q in sigs, f"{p['id']} PA query not a verbatim rule signal: {q!r}"


# ==========================================================================
# Determinism — byte-identical across fresh loaders + PYTHONHASHSEED flips
# ==========================================================================

class TestDeterminism:
    def test_three_fresh_loaders_byte_identical(self) -> None:
        cores = [grade.grade(grade.rank_baseline, "baseline_four_surface_matcher") for _ in range(3)]
        shas = {grade.result_core_sha256(c) for c in cores}
        assert len(shas) == 1
        assert shas.pop() == BASELINE["determinism"]["result_core_sha256"]

    @pytest.mark.parametrize("seed", ["0", "1", "42"])
    def test_pythonhashseed_stable(self, seed: str) -> None:
        """A real subprocess with PYTHONHASHSEED set recomputes the pinned core sha."""
        code = (
            "import sys; sys.path.insert(0, r'%s'); import grade; "
            "c = grade.grade(grade.rank_baseline, 'baseline_four_surface_matcher'); "
            "print(grade.result_core_sha256(c))" % str(_GMETRIC)
        )
        env = {"PYTHONHASHSEED": seed, "PYTHONPATH": _SRC}
        import os
        full_env = {**os.environ, **env}
        out = subprocess.run([_PY, "-c", code], capture_output=True, text=True, env=full_env)
        assert out.returncode == 0, out.stderr
        assert out.stdout.strip() == BASELINE["determinism"]["result_core_sha256"]


# ==========================================================================
# Baseline — non-strawman, stratified, and the pooled mean flagged
# ==========================================================================

class TestBaselineStratified:
    def test_non_strawman_PA_answers_its_own_idiom(self) -> None:
        by = BASELINE["RESULT_baseline"]["by_qclass"]
        assert by["PA"]["10"]["recall"] > 0.0
        assert by["PA"]["10"]["recall"] == 1.0  # verbatim rule-prose -> perfect
        assert by["TK"]["10"]["recall"] > 0.0

    def test_reachability_gap_problem_language_missed(self) -> None:
        """The whole problem-language register is missed even though the content exists
        and is wired -- the REACHABILITY gap, measured."""
        by = BASELINE["RESULT_baseline"]["by_qclass"]
        assert by["PB"]["10"]["recall"] == 0.0
        assert by["CE"]["10"]["recall"] == 0.0

    def test_pooled_mean_flagged_as_the_number_that_lies(self) -> None:
        snap = LEGS["baseline_snapshot"]
        assert "the_number_that_lies" in snap
        # the pooled recall hides a PA=1.0 / PB=0.0 split
        assert snap["by_qclass_at_10"]["PA"]["recall"] == 1.0
        assert snap["by_qclass_at_10"]["PB"]["recall"] == 0.0

    def test_baseline_recomputes_from_source_bypassing_the_pin(self) -> None:
        """Recompute the baseline live and confirm it equals the pin (not trusted)."""
        core = grade.grade(grade.rank_baseline, "baseline_four_surface_matcher")
        assert core["covered"] == BASELINE["RESULT_baseline"]["covered"]
        assert core["by_qclass"] == BASELINE["RESULT_baseline"]["by_qclass"]


# ==========================================================================
# Three denominators — never conflated
# ==========================================================================

class TestThreeDenominators:
    def test_three_meters_present_and_distinct(self) -> None:
        m = BASELINE["three_meters_never_conflated"]
        assert set(m) >= {"meter_1_recall", "meter_2_content_coverage",
                          "meter_3_matcher_reachable_ceiling"}
        recall10 = m["meter_1_recall"]["10"]
        content = m["meter_2_content_coverage"]["content_coverage_E_over_total"]
        ceiling = m["meter_3_matcher_reachable_ceiling"]["composite"]["composite_reachable_ceiling"]
        # the three answer different questions and take different values
        assert recall10 < content <= ceiling

    def test_content_gap_vs_reachability_answered_by_measurement(self) -> None:
        """Mainstream content present (~1.0), composite wiring present (1.0), recall low
        on problem-language -> REACHABILITY gap, not content. Answered by number."""
        q = GMETRIC["Q_answer_measured"]
        assert q["mainstream_PA_PB_TK_SEED"]["coverage"] == 1.0
        assert GMETRIC["2_denominators"]["matcher_reachable_ceiling_method_dependent"]["composite"]["composite_reachable_ceiling"] == 1.0
        assert BASELINE["RESULT_baseline"]["by_qclass"]["PB"]["10"]["recall"] == 0.0
        assert "REACHABILITY" in q["verdict"]

    def test_absent_gaps_recorded_not_filled(self) -> None:
        """Genuine canon-edge absences are recorded (content gap deferred, not filled)."""
        absent = GMETRIC["Q_answer_measured"]["genuine_content_gaps_ABSENT"]
        assert len(absent) >= 1
        loader = grade.KnowledgeLoader(knowledge_dir=grade.KDIR)
        comp = {p["id"] for p in loader._component_patterns}
        for a in absent:
            assert a not in comp  # truly absent, not a hidden husk


# ==========================================================================
# Locked legs — set AFTER the baseline read
# ==========================================================================

class TestLockedLegs:
    def test_three_legs_locked(self) -> None:
        assert LEGS["status"] == "LOCKED"
        assert {"LEG_1_primary_delta", "LEG_2_design_works_floor",
                "LEG_3_distribution_wins"} <= set(LEGS)

    def test_legs_baseline_snapshot_matches_measured(self) -> None:
        snap = LEGS["baseline_snapshot"]
        assert snap["covered_at_10"] == BASELINE["RESULT_baseline"]["covered"]["10"]
        assert snap["denominator_E_golds"] == BASELINE["RESULT_baseline"]["denominator_E_golds"]


# ==========================================================================
# FAIL-CLOSED substrate — the security hard line (Hyperion, council 3e6eeeab)
# ==========================================================================

def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Copy the frozen substrate + corpus into a tmp tree and repoint the grader at
    it, so a tamper never touches the real (uncommitted) artifacts."""
    gdir = tmp_path / "gmetric"
    kdir = tmp_path / "knowledge"
    gdir.mkdir()
    kdir.mkdir()
    # version-resolved names (v2 by default) so the tmp manifest pins the CURRENT
    # migrated corpus -- a tamper is detected on its own merits, never masked by a
    # spurious v1-vs-migrated-corpus drift.
    frozen = {"PROBLEMS_IN": grade.PROBLEMS_IN.name, "GMETRIC_IN": grade.GMETRIC_IN.name,
              "FREEZE_MANIFEST": grade.FREEZE_MANIFEST.name, "BASELINE_OUT": grade.BASELINE_OUT.name}
    for name in frozen.values():
        shutil.copy(_GMETRIC / name, gdir / name)
    for name in grade.CORPUS_FILES:
        shutil.copy(grade.KDIR / name, kdir / name)
    for attr, fname in frozen.items():
        monkeypatch.setattr(grade, attr, gdir / fname)
    monkeypatch.setattr(grade, "KDIR", kdir)
    return gdir, kdir


def _regen_manifest(gdir: Path, kdir: Path, *, refresh_answer_key: bool) -> None:
    """Rebuild the freeze manifest to match the (possibly tampered) on-disk files.
    refresh_answer_key toggles whether the attacker also updates the answer-key hash.
    Operates through the sandbox-monkeypatched grade paths (version-agnostic)."""
    man = json.loads(grade.FREEZE_MANIFEST.read_text(encoding="utf-8"))
    man["pins"][grade.GMETRIC_IN.name] = _sha(grade.GMETRIC_IN)
    man["pins"][grade.PROBLEMS_IN.name] = _sha(grade.PROBLEMS_IN)
    for f in grade.CORPUS_FILES:
        man["pins"][f] = _sha(kdir / f)
    if refresh_answer_key:
        man["answer_key_sha256"] = grade.answer_key_sha256_from_gmetric()
    grade.FREEZE_MANIFEST.write_text(
        json.dumps(man, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _flip_gold_acc(gdir: Path, problem: str, new_acc_for_first_E) -> None:
    """Replace the first E-gold acc of `problem` in the tmp gmetric (grade-resolved)."""
    gm = json.loads(grade.GMETRIC_IN.read_text(encoding="utf-8"))
    for row in gm["reachable_set_map"]:
        if row["problem"] == problem and row["verdict"] == "E":
            row["acceptable_ids"] = new_acc_for_first_E
            break
    grade.GMETRIC_IN.write_text(
        json.dumps(gm, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class TestFailClosed:
    def test_L1_gold_flip_blocked_substrate_drift(self, sandbox) -> None:
        """Flipping an acceptable_id changes gmetric's bytes -> manifest pin mismatch."""
        gdir, _ = sandbox
        _flip_gold_acc(gdir, "P01", ["wrong_id"])
        with pytest.raises(SystemExit, match="SUBSTRATE DRIFT"):
            grade._verify_substrate()

    def test_L1b_answer_key_drift_blocked_when_manifest_filepins_regenerated(self, sandbox) -> None:
        """Attacker regenerates the manifest FILE pins to hide the gmetric edit but
        leaves the answer-key hash stale -> the content-hash catches it."""
        gdir, kdir = sandbox
        _flip_gold_acc(gdir, "P01", ["wrong_id"])
        _regen_manifest(gdir, kdir, refresh_answer_key=False)
        with pytest.raises(SystemExit, match="ANSWER-KEY DRIFT"):
            grade._verify_substrate()

    def test_L2_score_moving_flip_blocked_at_baseline_pin(self, sandbox) -> None:
        """Attacker regenerates the WHOLE manifest so _verify_substrate passes, but a
        score-moving flip trips the baseline result-core pin in main()."""
        gdir, kdir = sandbox
        _flip_gold_acc(gdir, "P01", ["wrong_id"])  # PA gold no longer hit -> score drops
        _regen_manifest(gdir, kdir, refresh_answer_key=True)
        grade._verify_substrate()  # now passes (file + key consistent)
        with pytest.raises(SystemExit, match="BASELINE RESULT DRIFT"):
            grade.main()

    def test_L3_widen_already_covered_blocked_at_baseline_answer_key(self, sandbox) -> None:
        """Widening an ALREADY-covered gold leaves the score unchanged (result-core
        stable) but changes the answer key -> the baseline answer-key pin catches it,
        the mnemos B4 seam closed at S0 (Theia AC)."""
        gdir, kdir = sandbox
        # P01's data_table gold is already covered; add a second real id -> score unchanged.
        _flip_gold_acc(gdir, "P01", ["data_table", "grid"])
        _regen_manifest(gdir, kdir, refresh_answer_key=True)
        grade._verify_substrate()  # passes
        with pytest.raises(SystemExit, match="BASELINE ANSWER-KEY DRIFT"):
            grade.main()

    def test_only_refreeze_mutates(self, sandbox) -> None:
        """--refreeze is the one loud, explicit path that moves the pin."""
        gdir, kdir = sandbox
        _flip_gold_acc(gdir, "P01", ["data_table", "grid"])
        _regen_manifest(gdir, kdir, refresh_answer_key=True)
        monkeypatch_argv = ["grade.py", "--refreeze"]
        old = sys.argv
        try:
            sys.argv = monkeypatch_argv
            grade.main()  # must not raise
        finally:
            sys.argv = old
        repinned = json.loads(grade.BASELINE_OUT.read_text(encoding="utf-8"))
        assert repinned["determinism"]["answer_key_sha256"] == grade.answer_key_sha256_from_gmetric()


# ==========================================================================
# Firewall — S0 artifacts import only theia.* (never coeus/othrys/mnemos)
# ==========================================================================

class TestFirewall:
    @pytest.mark.parametrize("fn", ["grade.py", "build_gmetric_v1.py",
                                     "set_locked_legs.py", "theia_engine_bench.py",
                                     "build_theia_matches.py"])
    def test_no_forbidden_imports(self, fn: str) -> None:
        """AST-scan the actual import graph (not prose): S0 artifacts import only
        theia.* / stdlib, never coeus.*/othrys.*/mnemos.*."""
        import ast
        tree = ast.parse((_GMETRIC / fn).read_text(encoding="utf-8"))
        forbidden = {"coeus", "othrys", "mnemos"}
        mods: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods.append(node.module)
        offenders = [m for m in mods if m.split(".")[0] in forbidden]
        assert not offenders, f"{fn} imports {offenders}"
