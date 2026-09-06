# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""Authoring builder for the TYPED-INDEX S0 SYSTEM stratum (story-1c54b0b7, council
ae492280 / m-5a5837da).

Emits the byte-frozen SYSTEM-targeted labelled set + its two-view baseline pin, the
NEW half of the stratified gate that arms the collapse of Theia's two signal-index
accessors into one nested view (S1). The COMPONENT stratum already exists, frozen, as
theia-Gmetric v3 (problems_blind_v3 / gmetric_v3 / theia_engine_bench); S0 does NOT
re-derive it (Directive 2) — it cites the v3 engine recall and adds this second stratum,
which was never end-to-end benchmarked because the live two-index summon path was broken
(root cause m-698d738c). Every number is reported PER STRATUM, never pooled (m-e8ccb163).

Pipeline (mirrors build_gmetric_v1 -> grade -> set_locked_legs, reusing grade.py verbatim
so there is ONE grader and ONE substrate verifier):
  * problems_blind_sys_v1.json  -- the blind SYSTEM problems + FROZEN verbatim queries +
    gold design-system ids (schema-identical to problems_blind_v3 so grade.grade drives it).
  * gmetric_sys_v1.json         -- the frozen metric: reachable_set_map (per-gold verdict
    E + acceptable system ids + structure = system category), the recall denominator, the
    content-hashed answer key, and the stratification.
  * freeze_manifest_sys_v1.json -- the EXTERNAL trust root: pins problems_blind_sys +
    gmetric_sys + the four corpus files + a content-hash over the E-gold answer key. The
    pin SET is exactly what grade._verify_substrate enforces (reused verbatim), so the
    system substrate fails closed on any drift the same way the component one does.
  * baseline_pinned_sys_v1.json -- the FROZEN two-view SYSTEM baseline result core (the
    number S1's unified run must equal-or-beat on this stratum). Refuses to re-pin on a
    result-core drift without --refreeze (grade.main's fail-closed contract, mirrored).
  * theia_matches_sys_v1.json + theia_matches_freeze_sys_v1.json -- the frozen gold-blind
    SYSTEM recognition snapshot + its trust root, so no hand-edit hides in the measured path.

Blindness (the S0-FIX lesson m-4d5383c2 — legs curated BLIND before results, no degenerate
recognizer that caps problem-language at 0):
  * SYS-PA queries are VERBATIM design-system signals (corpus provenance; the EXACT leg).
  * SYS-PB queries are problem-language authored from the scenario ALONE and NEVER contain
    a gold id (leak guard below); recognition is on the query ALONE (no SHAPE working
    memory — measured redundant for systems; see typed_index_bench), so nothing an author
    wrote can encode the answer beyond the blind scenario itself.
  * SYS-TK queries feed a design-system id token (the SEED-FROM-NODE leg under test).

Firewall: imports only theia.* + the sibling frozen grader/bench (theia-only). Reads only
the on-disk corpus via grade's KnowledgeLoader; no live DB, no second-process open.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import grade  # noqa: E402  (frozen deterministic grader + substrate verifier, theia-only)
import typed_index_bench as sysb  # noqa: E402  (the gold-blind SYSTEM recognizer)

E = "E"

PROBLEMS_OUT = HERE / "problems_blind_sys_v1.json"
GMETRIC_OUT = HERE / "gmetric_sys_v1.json"
FREEZE_MANIFEST_OUT = HERE / "freeze_manifest_sys_v1.json"
BASELINE_OUT = HERE / "baseline_pinned_sys_v1.json"
MATCHES_OUT = HERE / "theia_matches_sys_v1.json"
MATCHES_FREEZE_OUT = HERE / "theia_matches_freeze_sys_v1.json"

# ---------------------------------------------------------------------------
# THE BLIND SYSTEM BENCHMARK. Each problem is a design-system-SELECTION scenario; the
# gold is the design system that addresses it (single best fit per problem — unlike a
# component problem, which needs several components). verdict E for every gold (each is a
# real, signal-bearing corpus system). register: "prose" (SYS-PA/PB) or "token" (SYS-TK).
#   SYS-PA = prose, signal-verbatim   -> EXACT leg (the corpus's own idiom; non-strawman)
#   SYS-PB = prose, problem-language  -> OVERLAP leg + SHAPE (the register that MATTERS)
#   SYS-TK = token, system-id vocab   -> SEED-FROM-NODE leg
# ---------------------------------------------------------------------------
SYSTEM_PROBLEMS: list[dict] = [
    # =============== SYS-PA: verbatim design-system signal (EXACT leg) ===============
    {"id": "S01", "qclass": "SYS-PA", "register": "prose",
     "problem": "A team states a symptom that is catalogued verbatim as a Material Design 3 signal.",
     "query": ["Android-first or Android-primary product"],
     "golds": [{"concept": "Material Design 3", "canonical": "material_design_3", "role": "primary_fit", "verdict": E, "acc": ["material_design_3"]}]},
    {"id": "S02", "qclass": "SYS-PA", "register": "prose",
     "problem": "A team states a symptom catalogued verbatim as a Dark Mode signal.",
     "query": ["Users requesting dark mode support"],
     "golds": [{"concept": "Dark Mode patterns", "canonical": "dark_mode", "role": "primary_fit", "verdict": E, "acc": ["dark_mode"]}]},
    {"id": "S03", "qclass": "SYS-PA", "register": "prose",
     "problem": "A team states a symptom catalogued verbatim as a Salesforce Lightning signal.",
     "query": ["Salesforce Lightning Web Components (LWC) codebase"],
     "golds": [{"concept": "Lightning Design System", "canonical": "lightning_design", "role": "primary_fit", "verdict": E, "acc": ["lightning_design"]}]},
    {"id": "S04", "qclass": "SYS-PA", "register": "prose",
     "problem": "A team states a symptom catalogued verbatim as a Shopify Polaris signal.",
     "query": ["Shopify app or plugin development"],
     "golds": [{"concept": "Shopify Polaris", "canonical": "polaris", "role": "primary_fit", "verdict": E, "acc": ["polaris"]}]},
    {"id": "S05", "qclass": "SYS-PA", "register": "prose",
     "problem": "A team states a symptom catalogued verbatim as a Carbon Design signal.",
     "query": ["IBM product or partner integration"],
     "golds": [{"concept": "Carbon Design System", "canonical": "carbon_design", "role": "primary_fit", "verdict": E, "acc": ["carbon_design"]}]},

    # =============== SYS-PB: problem-language / blind (OVERLAP + SHAPE) ===============
    {"id": "S06", "qclass": "SYS-PB", "register": "prose",
     "problem": "An Android-first team building with Jetpack Compose wants the app to pick up the user's wallpaper colours for theming.",
     "query": ["We're an Android-first team building with Jetpack Compose and we want the app to pick up the user's wallpaper colours for theming."],
     "golds": [{"concept": "Material Design 3", "canonical": "material_design_3", "role": "primary_fit", "verdict": E, "acc": ["material_design_3"]}]},
    {"id": "S07", "qclass": "SYS-PB", "register": "prose",
     "problem": "A team shipping a native iPhone and iPad app wants it to feel native and pass App Store review.",
     "query": ["We're shipping a native iPhone and iPad app that should feel like it belongs on the platform, and we plan to distribute through the App Store."],
     "golds": [{"concept": "Apple Human Interface Guidelines", "canonical": "apple_hig", "role": "primary_fit", "verdict": E, "acc": ["apple_hig"]}]},
    {"id": "S08", "qclass": "SYS-PB", "register": "prose",
     "problem": "An internal enterprise back-office admin panel in React with lots of data tables, forms and filters.",
     "query": ["We're building an internal enterprise back-office admin panel in React with lots of data tables, forms and filters."],
     "golds": [{"concept": "Ant Design", "canonical": "ant_design", "role": "primary_fit", "verdict": E, "acc": ["ant_design"]}]},
    {"id": "S09", "qclass": "SYS-PB", "register": "prose",
     "problem": "Designers and developers keep disagreeing about what counts as a component, and the pattern library has no clear hierarchy or naming convention.",
     "query": ["Our designers and developers keep disagreeing about what counts as a component, and our pattern library has no clear hierarchy or naming convention."],
     "golds": [{"concept": "Atomic Design", "canonical": "atomic_design", "role": "primary_fit", "verdict": E, "acc": ["atomic_design"]}]},
    {"id": "S10", "qclass": "SYS-PB", "register": "prose",
     "problem": "Usability problems keep surfacing late; user research is disconnected from decisions and there is no iterative evaluation cycle.",
     "query": ["We keep discovering usability problems late in development; our user research is disconnected from design decisions and we have no iterative evaluation cycle."],
     "golds": [{"concept": "User-Centered Design", "canonical": "user_centered_design", "role": "primary_fit", "verdict": E, "acc": ["user_centered_design"]}]},
    {"id": "S11", "qclass": "SYS-PB", "register": "prose",
     "problem": "A React team that cares about accessibility wants to move fast by styling at the component level instead of maintaining separate CSS.",
     "query": ["Our React team cares a lot about accessibility and wants to move fast by styling at the component level instead of maintaining separate CSS."],
     "golds": [{"concept": "Chakra UI philosophy", "canonical": "chakra_patterns", "role": "primary_fit", "verdict": E, "acc": ["chakra_patterns"]}]},
    {"id": "S12", "qclass": "SYS-PB", "register": "prose",
     "problem": "A Next.js + Tailwind team wants to own the component code in their repo rather than depend on a library they cannot fully customise.",
     "query": ["We're on Next.js with Tailwind and want to own the component code in our own repo rather than depend on a library we can't fully customise."],
     "golds": [{"concept": "shadcn/ui philosophy", "canonical": "shadcn_patterns", "role": "primary_fit", "verdict": E, "acc": ["shadcn_patterns"]}]},
    {"id": "S13", "qclass": "SYS-PB", "register": "prose",
     "problem": "A team needs unstyled, accessible primitives so designers can build a completely bespoke-looking component set on top; accessibility is a hard requirement.",
     "query": ["We need unstyled, accessible primitives so our designers can build a completely bespoke-looking component set on top, and accessibility is a hard requirement."],
     "golds": [{"concept": "Radix UI headless architecture", "canonical": "radix_patterns", "role": "primary_fit", "verdict": E, "acc": ["radix_patterns"]}]},
    {"id": "S14", "qclass": "SYS-PB", "register": "prose",
     "problem": "Colours across the product feel random and clash, and some brand colours fail the contrast checks the team runs.",
     "query": ["Colours across our product feel random and clash, and some of our brand colours fail the contrast checks we run."],
     "golds": [{"concept": "Color Theory for interfaces", "canonical": "color_theory", "role": "primary_fit", "verdict": E, "acc": ["color_theory"]}]},
    {"id": "S15", "qclass": "SYS-PB", "register": "prose",
     "problem": "Font sizes are arbitrary pixel values with no consistent ratio between heading levels, so the hierarchy feels flat.",
     "query": ["Our font sizes are arbitrary pixel values with no consistent ratio between heading levels, so the hierarchy feels flat."],
     "golds": [{"concept": "Typographic scales", "canonical": "typography_scales", "role": "primary_fit", "verdict": E, "acc": ["typography_scales"]}]},
    {"id": "S16", "qclass": "SYS-PB", "register": "prose",
     "problem": "Spacing in the CSS is inconsistent and elements feel randomly placed; developers are guessing padding and margin values.",
     "query": ["Spacing in our CSS is inconsistent and elements feel randomly placed; developers are just guessing padding and margin values."],
     "golds": [{"concept": "Spacing systems", "canonical": "spacing_systems", "role": "primary_fit", "verdict": E, "acc": ["spacing_systems"]}]},
    {"id": "S17", "qclass": "SYS-PB", "register": "prose",
     "problem": "Z-index values conflict and modals and dropdowns layer incorrectly; shadows are inconsistent and disappear in the dark theme.",
     "query": ["Our z-index values conflict and modals and dropdowns layer incorrectly; our shadows are inconsistent and disappear in the dark theme."],
     "golds": [{"concept": "Elevation and depth system", "canonical": "elevation_system", "role": "primary_fit", "verdict": E, "acc": ["elevation_system"]}]},
    {"id": "S18", "qclass": "SYS-PB", "register": "prose",
     "problem": "Components break when dropped into a narrower column; their responsiveness is tied to the viewport rather than the space they sit in.",
     "query": ["Our components break when we drop them into a narrower column; their responsiveness is tied to the viewport rather than the space they actually sit in."],
     "golds": [{"concept": "Container queries", "canonical": "container_queries", "role": "primary_fit", "verdict": E, "acc": ["container_queries"]}]},
    {"id": "S19", "qclass": "SYS-PB", "register": "prose",
     "problem": "Hardcoded colour values are scattered across the CSS and the design-to-code handoff loses fidelity across web, iOS and Android.",
     "query": ["We have hardcoded colour values scattered across our CSS and our design-to-code handoff loses fidelity across web, iOS and Android."],
     "golds": [{"concept": "Design tokens specification", "canonical": "design_tokens", "role": "primary_fit", "verdict": E, "acc": ["design_tokens"]}]},

    # =============== SYS-TK: design-system id token (SEED-FROM-NODE leg) ===============
    {"id": "S20", "qclass": "SYS-TK", "register": "token",
     "problem": "The Material Design 3 system named directly by its id token.",
     "query": ["material_design_3"],
     "golds": [{"concept": "Material Design 3", "canonical": "material_design_3", "role": "primary_fit", "verdict": E, "acc": ["material_design_3"]}]},
    {"id": "S21", "qclass": "SYS-TK", "register": "token",
     "problem": "The Tailwind utility methodology named directly by its id token.",
     "query": ["tailwind_utility"],
     "golds": [{"concept": "Tailwind utility-first", "canonical": "tailwind_utility", "role": "primary_fit", "verdict": E, "acc": ["tailwind_utility"]}]},
    {"id": "S22", "qclass": "SYS-TK", "register": "token",
     "problem": "The grid-systems foundation named directly by its id token.",
     "query": ["grid_systems"],
     "golds": [{"concept": "Grid systems", "canonical": "grid_systems", "role": "primary_fit", "verdict": E, "acc": ["grid_systems"]}]},
    {"id": "S23", "qclass": "SYS-TK", "register": "token",
     "problem": "The responsive-design methodology named directly by its id token.",
     "query": ["responsive_design"],
     "golds": [{"concept": "Responsive design", "canonical": "responsive_design", "role": "primary_fit", "verdict": E, "acc": ["responsive_design"]}]},
    {"id": "S24", "qclass": "SYS-TK", "register": "token",
     "problem": "The dark-mode color system named directly by its id token.",
     "query": ["dark_mode"],
     "golds": [{"concept": "Dark Mode patterns", "canonical": "dark_mode", "role": "primary_fit", "verdict": E, "acc": ["dark_mode"]}]},
    {"id": "S25", "qclass": "SYS-TK", "register": "token",
     "problem": "The WCAG contrast-ratio color system named directly by its id token.",
     "query": ["contrast_ratios"],
     "golds": [{"concept": "WCAG contrast ratios", "canonical": "contrast_ratios", "role": "primary_fit", "verdict": E, "acc": ["contrast_ratios"]}]},
]


def _validate(systems: list[dict]) -> None:
    """Blind-authoring + provenance gates, fail-closed (build_gmetric_v1 parity)."""
    sys_ids = {s["id"] for s in systems}
    sys_signals = {sig.strip() for s in systems for sig in s.get("signals", [])}
    errors: list[str] = []
    seen: set[str] = set()
    for p in SYSTEM_PROBLEMS:
        pid = p["id"]
        if pid in seen:
            errors.append(f"{pid}: duplicate problem id")
        seen.add(pid)
        if not p["query"] or not all(isinstance(q, str) and q.strip() for q in p["query"]):
            errors.append(f"{pid}: empty/blank query")
        # SYS-PA provenance: every query string is a VERBATIM design-system signal.
        if p["qclass"] == "SYS-PA":
            for q in p["query"]:
                if q not in sys_signals:
                    errors.append(f"{pid}: SYS-PA query not a verbatim system signal: {q!r}")
        # Blind-authoring leak guard: an AUTHORED problem-language query (SYS-PB) must not
        # contain its gold id verbatim (post-hoc tuning toward gold vocab). SYS-PA is
        # corpus-provenance prose; SYS-TK feeds the id token AS the query (both exempt).
        if p["qclass"] == "SYS-PB":
            ql = " ".join(p["query"]).lower()
            for g in p["golds"]:
                cid = g["canonical"].lower()
                if cid in ql or cid.replace("_", " ") in ql or cid.replace("_", "-") in ql:
                    errors.append(f"{pid}: SYS-PB query leaks gold id '{g['canonical']}'")
        for g in p["golds"]:
            if g["verdict"] != E:
                errors.append(f"{pid}: only E golds are authored in the SYSTEM set, got {g['verdict']}")
            if not g["acc"]:
                errors.append(f"{pid} '{g['canonical']}': E gold with empty acceptable ids")
            for cid in g["acc"]:
                if cid not in sys_ids:
                    errors.append(f"{pid}: acc id '{cid}' is not a design-system id")
    if errors:
        raise SystemExit("SYSTEM BENCHMARK VALIDATION FAILED:\n  " + "\n  ".join(errors))


def answer_key_sha256(problems: list[dict]) -> str:
    """Content-hash over the E-gold answer key (parity with grade.answer_key_sha256_from_gmetric,
    which reads the frozen gmetric's verdict==E rows)."""
    import hashlib
    tuples = sorted(
        (p["id"], g["canonical"], tuple(sorted(g["acc"])))
        for p in problems for g in p["golds"] if g["verdict"] == E
    )
    return hashlib.sha256(json.dumps(tuples, sort_keys=True, ensure_ascii=True).encode("utf-8")).hexdigest()


def main() -> None:
    from datetime import datetime, timezone
    refreeze = "--refreeze" in sys.argv

    systems = json.loads((grade.KDIR / "design_systems.json").read_text(encoding="utf-8"))["systems"]
    sys_cat = {s["id"]: s.get("category", "uncategorised") for s in systems}
    signal_bearing = {s["id"] for s in systems if any(x.strip() for x in s.get("signals", []))}
    _validate(systems)

    from collections import defaultdict
    by_qc = defaultdict(int)
    for p in SYSTEM_PROBLEMS:
        by_qc[p["qclass"]] += 1

    # ---- blind problems artifact (schema-identical to problems_blind_v3) ----
    problems_blind = {
        "spec_id": "theia-Gmetric-sys-v1",
        "story": "story-1c54b0b7",
        "what": ("Blind, corpus-blind DESIGN-SYSTEM-SELECTION problems (the SYSTEM stratum of the "
                 "TYPED-INDEX S0 gate). Each carries its FROZEN verbatim query and its gold design-"
                 "system id. SYS-PA queries are verbatim system signals; SYS-PB problem-language is "
                 "authored before grading and never tuned toward gold vocab; SYS-TK feeds the system "
                 "id token AS the query. The grader reads THIS file and feeds 'query' unchanged."),
        "n_problems": len(SYSTEM_PROBLEMS),
        "registers": sorted({p["register"] for p in SYSTEM_PROBLEMS}),
        "qclasses": sorted({p["qclass"] for p in SYSTEM_PROBLEMS}),
        "problems": [
            {"id": p["id"], "qclass": p["qclass"], "register": p["register"],
             "problem": p["problem"], "query": p["query"],
             "golds": [{"concept": g["concept"], "canonical": g["canonical"],
                        "role": g["role"], "verdict": g["verdict"]} for g in p["golds"]]}
            for p in SYSTEM_PROBLEMS
        ],
    }
    PROBLEMS_OUT.write_text(grade.canonical_dump(problems_blind), encoding="utf-8")

    # ---- frozen metric spec (answer key + recall denominator + stratification) ----
    reach_map: list[dict] = []
    for p in SYSTEM_PROBLEMS:
        for g in p["golds"]:
            structure = "; ".join(sorted({sys_cat[c] for c in g["acc"]}))
            reach_map.append({
                "problem": p["id"], "qclass": p["qclass"], "register": p["register"],
                "concept": g["concept"], "canonical": g["canonical"], "role": g["role"],
                "verdict": g["verdict"], "acceptable_ids": g["acc"], "structure": structure,
            })
    denom = sum(1 for r in reach_map if r["verdict"] == E)
    ak_sha = answer_key_sha256(SYSTEM_PROBLEMS)
    content_by_qclass = {}
    for qc in sorted(by_qc):
        rows = [r for r in reach_map if r["qclass"] == qc]
        content_by_qclass[qc] = {"E": len(rows), "total": len(rows), "coverage_E_over_total": 1.0}

    gmetric = {
        "spec_id": "theia-Gmetric-sys-v1",
        "story": "story-1c54b0b7",
        "title": "Frozen blind design-system-selection recall scorecard (TYPED-INDEX S0, SYSTEM stratum)",
        "authored_by": "Themis",
        "status": "FROZEN",
        "design_authority": ["council ae492280 (m-5a5837da)", "root cause m-698d738c",
                             "discipline m-e8ccb163 (per-stratum, never pooled) + m-4d5383c2 (blind legs)"],
        "one_line": ("Design-system recall@10 over a blind method-independent set of E-golds, measured "
                     "through the TWO-VIEW accessor (get_system_signal_index -> hydrate_systems). The bar "
                     "S1's unified nested accessor must equal-or-beat on this stratum. Never pooled with "
                     "the COMPONENT stratum."),
        "1_grader": {
            "type": "curated_concept_map",
            "rule": ("A gold is COVERED@k iff the method's rank-ordered top-k design-system ids intersect "
                     "the gold's acceptable_ids. Only E golds are scored. ONE grader (grade.grade) is "
                     "reused verbatim over this SYSTEM answer key -- no fork."),
            "method_baseline": ("typed_index_bench.rank_system over the TWO-VIEW accessor: recognise matched "
                                "system signal ids (OVERLAP + SHAPE / EXACT / SEED-FROM-NODE) against "
                                "get_system_signal_index(), then loader.hydrate_systems (edge related_systems)."),
        },
        "2_denominators": {
            "note": "Content EXISTS vs RECALL, kept distinct (m-0364c120). Never pooled with components.",
            "content_method_independent": {
                "definition": "Every gold is a real signal-bearing design-system node (direct corpus check).",
                "tally": {"E_exists": denom, "A_absent": 0},
                "signal_bearing_systems": len(signal_bearing),
                "total_systems": len(systems),
                "content_coverage_by_qclass": content_by_qclass,
            },
            "reachable_set_for_recall": {
                "definition": "recall denominator = E-golds only.",
                "FROZEN_reachable_denominator": denom,
            },
        },
        "3_score": {
            "metric": "system_recall_at_k",
            "formula": "recall@k = (# E-golds whose acceptable_ids intersect the method's top-k) / E-golds",
            "primary_cutoff_k": 10,
            "secondary_cutoff_k": 5,
            "answer_key_sha256": ak_sha,
            "answer_key_definition": ("sha256 over sorted (problem_id, canonical, sorted(acceptable_ids)) "
                                      "tuples of every E-gold. Pinned in the freeze manifest; grade "
                                      "re-compares it so an acceptable_ids widening trips drift even when "
                                      "the graded result is unchanged."),
        },
        "4_stratification": {
            "rule": "m-e8ccb163: never a single pooled mean; qclass is primary.",
            "dimensions": {
                "qclass": {"SYS-PA": "prose, verbatim system signal (EXACT leg)",
                           "SYS-PB": "prose, problem-language / blind (OVERLAP + SHAPE)",
                           "SYS-TK": "token, design-system id vocabulary (SEED-FROM-NODE leg)"},
                "register": ["prose", "token"],
                "structure": "design-system category of each E-gold",
            },
        },
        "5_reproducibility": {
            "problems_blind": {"file": PROBLEMS_OUT.name, "sha256": grade.sha_path(PROBLEMS_OUT)},
            "corpus_snapshot_sha256": {f: grade.sha_path(grade.KDIR / f) for f in grade.CORPUS_FILES},
            "n_problems": len(SYSTEM_PROBLEMS),
            "cutoffs": {"primary_k": 10, "secondary_k": 5},
            "recompute_contract": ("Given the pinned problems_blind_sys hash, the corpus hashes, k, and this "
                                   "map, recall@k is a pure function of a method's ranked output."),
        },
        "reachable_set_map": reach_map,
    }
    GMETRIC_OUT.write_text(grade.canonical_dump(gmetric), encoding="utf-8")

    # ---- external tamper-evident freeze manifest (grade._verify_substrate pin set) ----
    freeze_manifest = {
        "spec_id": "theia-Gmetric-sys-v1-freeze-manifest",
        "story": "story-1c54b0b7",
        "what": ("External trust root for the SYSTEM stratum. Pins problems_blind_sys + gmetric_sys + the "
                 "four corpus snapshots + a content-hash over the E-gold answer key. grade._verify_substrate "
                 "(reused verbatim) reads pins ONLY from here, never from gmetric_sys (CWE-345)."),
        "hash_algo": "sha256",
        "answer_key_sha256": ak_sha,
        "pins": {
            PROBLEMS_OUT.name: grade.sha_path(PROBLEMS_OUT),
            GMETRIC_OUT.name: grade.sha_path(GMETRIC_OUT),
            **{f: grade.sha_path(grade.KDIR / f) for f in grade.CORPUS_FILES},
        },
    }
    FREEZE_MANIFEST_OUT.write_text(grade.canonical_dump(freeze_manifest), encoding="utf-8")

    # ---- grade the TWO-VIEW system baseline (reuse grade.grade + verify verbatim) ----
    orig = (grade.PROBLEMS_IN, grade.GMETRIC_IN, grade.FREEZE_MANIFEST, grade.BASELINE_OUT)
    try:
        grade.PROBLEMS_IN, grade.GMETRIC_IN = PROBLEMS_OUT, GMETRIC_OUT
        grade.FREEZE_MANIFEST, grade.BASELINE_OUT = FREEZE_MANIFEST_OUT, BASELINE_OUT
        checks = grade._verify_substrate()  # fail-closed on any drift
        core = grade.grade(sysb.rank_system, "system_two_view_hydrate")
        core_sha = grade.result_core_sha256(core)
        cur_ak = grade.answer_key_sha256_from_gmetric()
    finally:
        grade.PROBLEMS_IN, grade.GMETRIC_IN, grade.FREEZE_MANIFEST, grade.BASELINE_OUT = orig

    committed_sha = None
    if BASELINE_OUT.exists():
        committed_sha = json.loads(BASELINE_OUT.read_text(encoding="utf-8")).get("determinism", {}).get("result_core_sha256")
    if committed_sha is not None and committed_sha != core_sha and not refreeze:
        raise SystemExit(
            f"SYSTEM BASELINE RESULT DRIFT -- fresh result_core_sha256={core_sha} != committed "
            f"{committed_sha}. A corpus/benchmark change moved the system baseline. Refusing to re-pin. "
            "Pass --refreeze to move the pin (a loud, version-controlled act).")

    out = {
        "spec_id": "theia-Gmetric-sys-v1-baseline-capture",
        "story": "story-1c54b0b7",
        "what_this_is": ("Pinned TWO-VIEW design-system baseline (get_system_signal_index -> hydrate_systems) "
                         "over the frozen SYSTEM set. This is the number S1's UNIFIED nested accessor must "
                         "equal-or-beat on the SYSTEM stratum. The COMPONENT stratum bar is the frozen v3 "
                         "engine recall (theia_engine_bench.rank_engine); the two are NEVER pooled."),
        "arm": "baseline_two_view (kb.get_signal_index + kb.get_system_signal_index, read separately)",
        "RESULT_baseline": core,
        "determinism": {
            "fresh_loader_runs": 3,
            "result_core_sha256": core_sha,
            "answer_key_sha256": cur_ak,
            "note": "byte-identical across fresh loaders + PYTHONHASHSEED (system ids are content hashes).",
        },
        "substrate_self_certification": {"trust_root": FREEZE_MANIFEST_OUT.name, "checks": checks},
        "captured_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    BASELINE_OUT.write_text(grade.canonical_dump(out), encoding="utf-8")

    # ---- frozen gold-blind SYSTEM recognition snapshot + its trust root ----
    loader = grade.KnowledgeLoader(knowledge_dir=grade.KDIR)
    sys_index = loader.get_system_signal_index()
    id2text = {e["signal_id"]: e["signal_text"] for e in sys_index}
    matches = sysb.build_matches(loader)
    matches_text = {pid: [id2text[s] for s in sigs] for pid, sigs in matches.items()}
    matches_out = {
        "spec_id": "theia-Gmetric-sys-recognizer",
        "story": "story-1c54b0b7",
        "what": ("FROZEN gold-blind SYSTEM recognition {problem_id -> matched system signal_ids} bridging "
                 "each frozen query to the hydrate_systems path. Produced by typed_index_bench.build_matches "
                 "over problems_blind_sys + the system signal index; never reads gmetric_sys (gold-blind)."),
        "recognition_rule": ("signal matched iff (query + SYS SHAPE) overlaps its text by >= 2 stemmed tokens, "
                             "OR query == signal_text (EXACT), OR a query token IS a design-system id "
                             "(SEED-FROM-NODE). SHAPE is space-separated words, never a system id. Audit "
                             "matches_by_signal_text against problems_blind_sys."),
        "corpus_snapshot_sha256": {"design_systems.json": grade.sha_path(grade.KDIR / "design_systems.json")},
        "n_problems": len(matches),
        "matches": {pid: matches[pid] for pid in sorted(matches)},
        "matches_by_signal_text": {pid: matches_text[pid] for pid in sorted(matches_text)},
    }
    MATCHES_OUT.write_text(grade.canonical_dump(matches_out), encoding="utf-8")
    matches_freeze = {
        "spec_id": "theia-Gmetric-sys-recognizer-freeze",
        "story": "story-1c54b0b7",
        "what": ("Recognizer trust root: pins the frozen SYSTEM recognition snapshot + problems_blind_sys + "
                 "design_systems.json (the sole corpus its system signal index derives from). Separate from "
                 "the S0 freeze_manifest_sys (which grade._verify_substrate holds to an exact pin set)."),
        "hash_algo": "sha256",
        "pins": {
            MATCHES_OUT.name: grade.sha_path(MATCHES_OUT),
            PROBLEMS_OUT.name: grade.sha_path(PROBLEMS_OUT),
            "design_systems.json": grade.sha_path(grade.KDIR / "design_systems.json"),
        },
    }
    MATCHES_FREEZE_OUT.write_text(grade.canonical_dump(matches_freeze), encoding="utf-8")

    # ---- console: the SYSTEM stratum per-qclass baseline (never pooled) ----
    by = core["by_qclass"]
    print(f"=== theia-Gmetric SYSTEM stratum authored + baseline pinned (two-view) ===")
    print(f"problems: {len(SYSTEM_PROBLEMS)}  E-golds: {denom}  "
          f"(SYS-PA {by_qc['SYS-PA']}, SYS-PB {by_qc['SYS-PB']}, SYS-TK {by_qc['SYS-TK']})")
    print(f"SYSTEM two-view recall@10 = {core['covered']['10']}/{denom} = {core['recall']['10']}")
    print(f"SYSTEM two-view recall@5  = {core['covered']['5']}/{denom} = {core['recall']['5']}")
    print("by qclass @10 (never pooled):")
    for qc in ("SYS-PA", "SYS-PB", "SYS-TK"):
        if qc in by:
            print(f"  {qc:7}: {by[qc]['10']['covered']}/{by[qc]['10']['of']} = {by[qc]['10']['recall']}")
    print(f"result_core_sha256={core_sha}")
    print(f"answer_key_sha256={ak_sha[:16]}...")
    for f in (PROBLEMS_OUT, GMETRIC_OUT, FREEZE_MANIFEST_OUT, BASELINE_OUT, MATCHES_OUT, MATCHES_FREEZE_OUT):
        print(f"wrote {f.name} sha256={grade.sha_path(f)[:16]}...")


if __name__ == "__main__":
    main()
