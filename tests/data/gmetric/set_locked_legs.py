# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""Freeze the THREE locked legs of theia-Gmetric-v1 AFTER the baseline is read.

council 3e6eeeab + e920f1f4-decision-7: "THREE LOCKED legs set AFTER the baseline
is read (LEG_1 delta, LEG_2 design-works floor, LEG_3 distribution)". Mirrors the
mnemos set_locked_legs shape.

These are the BAR for the later Theia retrieval engine. S0 SETS them; it does not
run the engine. Calibrated from the measured baseline and the ceilings, so a real
win clears them and a marginal/noise result fails. Once frozen here, the bar is
locked.

Pipeline order: build_gmetric_v1.py -> grade.py (pin baseline) -> set_locked_legs.py.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
_VER = os.environ.get("THEIA_GMETRIC_VERSION", "v1")
_SUF = "" if _VER == "v1" else f"_{_VER}"
BASELINE_IN = HERE / f"baseline_matcher_pinned{_SUF}.json"
GMETRIC_IN = HERE / f"gmetric_{_VER}.json"
OUT = HERE / f"locked_legs_{_VER}.json"


def canonical_dump(obj) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def main() -> None:
    base = json.loads(BASELINE_IN.read_text(encoding="utf-8"))
    gm = json.loads(GMETRIC_IN.read_text(encoding="utf-8"))

    core = base["RESULT_baseline"]
    denom = core["denominator_E_golds"]                 # 58 E-golds
    b_recall10 = core["recall"]["10"]                   # 0.6034
    b_covered10 = core["covered"]["10"]                 # 35
    n_problems = gm["5_reproducibility"]["n_problems"]  # 31
    content = gm["2_denominators"]["content_method_independent"]
    ceiling = gm["2_denominators"]["matcher_reachable_ceiling_method_dependent"]
    by_qc = {qc: v["10"] for qc, v in core["by_qclass"].items()}

    # The pooled baseline 0.60 is inflated by PA=1.0 and TK=1.0 (token/rule-prose,
    # already maxed). The entire PROBLEM-LANGUAGE register (PB + CE = 22 E-golds) is
    # scored 0.0. The engine's win MUST land there. Legs are forced into that register:
    problem_language_gap = by_qc.get("PB", {}).get("of", 0) + by_qc.get("CE", {}).get("of", 0)

    # ---- leg calibration (from the measured baseline) ----
    DELTA_BAR = 0.20   # >= 0.20 over baseline 0.6034 -> >= 0.8034; recovering ~half of the
                       #  22-gold problem-language gap while PA/TK stay maxed = clearly-not-noise.
    FLOOR = 0.80       # the new path surfaces a strong majority; must exceed the already-0.60
                       #  baseline meaningfully (mnemos used 0.60 over a 0.35 baseline).
    DIST_MIN = 27      # of 31 problems (mnemos 35/40 = 0.875; 27/31 = 0.871).

    delta_min_covered = b_covered10 + math.ceil(DELTA_BAR * denom)
    floor_min_covered = math.ceil(FLOOR * denom)

    legs = {
        "spec_id": "theia-Gmetric-v1-locked-legs",
        "story": "story-af407698",
        "status": "LOCKED",
        "set_after": "baseline_matcher_pinned.json (legs calibrated from the measured baseline, never before)",
        "is_the_bar_for": "the later Theia retrieval engine. S0 sets this bar; it does not run the engine.",
        "baseline_snapshot": {
            "recall_at_10": b_recall10, "covered_at_10": b_covered10, "denominator_E_golds": denom,
            "by_qclass_at_10": by_qc,
            "not_a_strawman": ("PA (verbatim rule-prose) baseline = "
                               f"{by_qc['PA']['covered']}/{by_qc['PA']['of']} = {by_qc['PA']['recall']}; "
                               "the matcher answers its own idiom perfectly. TK (component tokens) = "
                               f"{by_qc['TK']['covered']}/{by_qc['TK']['of']} = {by_qc['TK']['recall']}."),
            "the_number_that_lies": (f"The pooled recall@10 {b_recall10} hides the register split: the "
                                     f"entire problem-language register (PB {by_qc['PB']['covered']}/"
                                     f"{by_qc['PB']['of']}, CE {by_qc['CE']['covered']}/{by_qc['CE']['of']}) "
                                     "is 0.0. Read the by_qclass split, never the pool (m-e8ccb163)."),
        },
        "ceilings_for_interpretation": {
            "content_coverage_E_over_total": content["content_coverage_E_over_total"],
            "content_coverage_mainstream": gm["Q_answer_measured"]["mainstream_PA_PB_TK_SEED"]["coverage"],
            "composite_matcher_reachable_ceiling": ceiling["composite"]["composite_reachable_ceiling"],
            "engine_content_ceiling": ("~1.0 of the E-golds: every E-gold exists in the corpus and is wired "
                                       "to be reachable (composite ceiling 1.0). The recall gap is purely "
                                       "REACHABILITY -- problem-language queries do not trigger the exact "
                                       "legs -- not content (m-0364c120)."),
        },
        "LEG_1_primary_delta": {
            "rule": f"recall@10(engine) - recall@10(baseline={b_recall10}) >= {DELTA_BAR}",
            "equivalently": f"engine covers >= {delta_min_covered} of {denom} E-golds (baseline {b_covered10} + "
                            f"{math.ceil(DELTA_BAR*denom)})",
            "delta_bar": DELTA_BAR,
            "engine_min_recall_at_10": round(b_recall10 + DELTA_BAR, 4),
            "engine_min_covered_at_10": delta_min_covered,
            "why": (f"The problem-language gap the baseline scores 0 on is {problem_language_gap}/{denom} of the "
                    "set; recovering ~half of it is a clearly-not-noise win. Because PA/TK are already maxed, "
                    "the delta can ONLY be earned in PB/CE/SEED -- the win is forced into the target classes."),
        },
        "LEG_2_design_works_floor": {
            "rule": f"recall@10(engine) >= {FLOOR}",
            "equivalently": f"engine covers >= {floor_min_covered} of {denom} E-golds",
            "floor": FLOOR,
            "engine_min_covered_at_10": floor_min_covered,
            "why": ("Establishes the new path surfaces a strong majority of what is reachable, not merely that "
                    "it beats a matcher already at 0.60 on its own idiom. The floor must exceed the baseline "
                    "meaningfully to mean anything."),
        },
        "LEG_3_distribution_wins": {
            "rule": f"engine covered@10 >= baseline covered@10 on >= {DIST_MIN} of {n_problems} problems",
            "min_problems_ge_baseline": DIST_MIN,
            "n_problems": n_problems,
            "why": ("Guards against a win concentrated in a few problems AND against regressing the 18 PA/TK/"
                    "SEED problems the matcher already covers. Because those are maxed, the LEG_1 delta can "
                    "only be earned in PB/CE -- the win is forced to land in the target classes."),
        },
        "verdict_rule": "PASS = LEG_1 AND LEG_2 AND LEG_3. Any one failing = NOT a pass; return to council.",
        "re_freeze": ("On corpus/benchmark drift (any pinned hash changes) re-freeze v1->v2; the v1 E-set must "
                      "stay covered@10 by the engine (eviction FAILS)."),
    }
    OUT.write_text(canonical_dump(legs), encoding="utf-8")
    print("=== LOCKED LEGS (set after baseline) ===")
    print(f"baseline recall@10 = {b_covered10}/{denom} = {b_recall10}  (PA {by_qc['PA']['recall']}, "
          f"PB {by_qc['PB']['recall']}, TK {by_qc['TK']['recall']}, SEED {by_qc['SEED']['recall']}, "
          f"CE {by_qc['CE']['recall']})")
    print(f"LEG_1 primary delta : engine recall@10 >= {round(b_recall10+DELTA_BAR,4)} "
          f"(>= {delta_min_covered}/{denom}); delta >= {DELTA_BAR}")
    print(f"LEG_2 design floor  : engine recall@10 >= {FLOOR} (>= {floor_min_covered}/{denom})")
    print(f"LEG_3 distribution  : engine covered@10 >= baseline on >= {DIST_MIN}/{n_problems} problems")
    print(f"wrote {OUT.name}")


if __name__ == "__main__":
    main()
