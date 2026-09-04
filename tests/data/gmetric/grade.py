# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""Deterministic grader for theia-Gmetric-v1 (story-af407698).

ONE grader (DRY, no fork). It grades ANY method that maps a frozen query to a
rank-ordered list of corpus ids, against the frozen concept map in gmetric_v1.json:

    A gold is COVERED@k iff its acceptable_ids intersect the method's top-k.
    recall@k = (# E-golds covered) / (# E-golds).  Only E golds are scored.

The later Theia retrieval engine reuses grade(method_fn, ...) VERBATIM over the
frozen queries + corpus, so the outcome comparison rides one substrate/determinism/
trust spine (e920f1f4-decision-1). This mirrors the SHIPPED mnemos grade.py SHAPE
by having read it read-only -- it is NOT imported (firewall: theia.* only).

rank_baseline is the frozen matcher baseline, the deterministic UNION of Theia's
retrieval surfaces (e920f1f4-decision-1): the match_structural_signals replica +
spec_component exact-id + plan_design_system keywords leg. It replicates each surface's
MATCHING logic side-effect-free (the real tools emit_event to disk and run heavy a11y
enrichment we must not trigger in a deterministic grader) over the retained corpus +
id-lookup getters. The exact-substring matcher is DELETED from the loaders + tools at S6
(story-041efcf4); LEG-1 is now its frozen source-recompute (_match_structural_signals_leg,
the established LEG-3/LEG-4 pattern), and the former audit_design _ANTI_PATTERNS leg is
dropped (measured-empty on v3). The spec_component archetype-husk (_COMPONENT_ARCHETYPES,
S4) and the audit_design island (_ANTI_PATTERNS, S6) are gone; the baseline result-core
is byte-identical across every removal (no --refreeze).

Every number is stratified by qclass, register, and structure -- never a single
pooled mean (m-e8ccb163). Determinism: grade runs with a FRESH KnowledgeLoader and
is byte-identical across fresh loaders; run under any PYTHONHASHSEED and the result
CORE is stable (the invariant is the result core, not any file's sha256).

Tamper-evidence: _verify_substrate reads its pins from the EXTERNAL
freeze_manifest.json (the trust root), never from gmetric_v1.json (which it grades
against), and fails closed on ANY drift -- gmetric included, plus a content-hash over
the E-gold answer key so an acceptable_ids widening trips even when no score moves
(CWE-345).

Firewall: imports only theia.* (theia.knowledge, theia.tools constants), never
othrys.*/coeus.*/mnemos.*. No live-DB access.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from theia.knowledge.loader import KnowledgeLoader

HERE = Path(__file__).resolve().parent
KDIR = Path(__file__).resolve().parents[3] / "src" / "theia" / "knowledge"
COMPONENTS_FILE = "component_patterns.json"
RULES_FILE = "decision_rules.json"
SYSTEMS_FILE = "design_systems.json"
A11Y_FILE = "accessibility_standards.json"
CORPUS_FILES = (COMPONENTS_FILE, RULES_FILE, SYSTEMS_FILE, A11Y_FILE)

# Corpus-freeze generation (see build_gmetric_v1._VER). Default v1 = S0 provenance.
_VER = os.environ.get("THEIA_GMETRIC_VERSION", "v1")
_SUF = "" if _VER == "v1" else f"_{_VER}"

PROBLEMS_IN = HERE / f"problems_blind_{_VER}.json"
GMETRIC_IN = HERE / f"gmetric_{_VER}.json"
FREEZE_MANIFEST = HERE / f"freeze_manifest{_SUF}.json"
BASELINE_OUT = HERE / f"baseline_matcher_pinned{_SUF}.json"

KS = (10, 5)  # primary, secondary


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_path(p: Path) -> str:
    return sha_bytes(p.read_bytes())


def canonical_dump(obj) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def answer_key_sha256_from_gmetric() -> str:
    """Recompute the E-gold answer-key content-hash from gmetric's reachable_set_map.

    Mirrors build_gmetric_v1.answer_key_sha256 but reads the FROZEN map (the file
    under test), so a widened acceptable_ids set changes this even when the graded
    result_core is unchanged. Compared against the manifest pin in _verify_substrate."""
    reach_map = json.loads(GMETRIC_IN.read_text(encoding="utf-8"))["reachable_set_map"]
    tuples = sorted(
        (r["problem"], r["canonical"], tuple(sorted(r["acceptable_ids"])))
        for r in reach_map if r["verdict"] == "E"
    )
    return sha_bytes(json.dumps(tuples, sort_keys=True, ensure_ascii=True).encode("utf-8"))


# --------------------------------------------------------------------------- #
# THE CURRENT MATCHER BASELINE: the deterministic UNION of the four surfaces.
# --------------------------------------------------------------------------- #

def _spec_component_resolve(loader: KnowledgeLoader, signal: str) -> str | None:
    """spec_component's exact-id resolution, side-effect-free.

    The frozen baseline's LEG-3 surface: exact id, then hyphen<->underscore variants.
    The legacy tool also had a hardcoded ``_COMPONENT_ARCHETYPES`` husk branch, but it
    emitted only ``archetype:<slug>`` tokens (never a real corpus id), which never
    appear in the pinned baseline's ranked output — the branch was dead on this
    benchmark. It is deleted with the island at S4 (story-57031f25), which leaves the
    baseline result-core byte-identical (no --refreeze). Returns the resolved id or
    None. We do not call spec_component() itself: it now runs a hydrate and an
    emit_event (a filesystem write) a deterministic grader must not trigger."""
    cl = signal.lower().strip()
    for cand in (cl, cl.replace("-", "_"), cl.replace("_", "-")):
        if loader.get_component_pattern(cand):
            return cand
    return None


def _plan_design_system_keywords_leg(loader: KnowledgeLoader, query: list[str]) -> list[str]:
    """plan_design_system's base-match keyword/name/category scorer, side-effect-free.

    Mirrors plan_design_system lines 217-257 (the `keywords` leg). NOTE the leg is
    DEGENERATE on the live corpus: 0 of 54 systems carry a `keywords` field, so the
    +2 keyword-overlap term never fires; only a system name or category substring in
    the query can score. Pinned as-is (fixing it is S5, out of scope). Returns the
    best-match design_system id (design-system id-space) or []."""
    desc = " ".join(query).lower()
    best, best_score = None, 0
    for cat in loader.list_design_system_categories():
        for system in loader.get_design_systems_by_category(cat):
            score = 0
            for kw in [k.lower() for k in system.get("keywords", [])]:
                if kw in desc:
                    score += 2
            if system.get("name", "").lower() in desc:
                score += 1
            if cat.lower() in desc:
                score += 1
            if score > best_score:
                best_score, best = score, system
    return [best["id"]] if best else []


# The priority order the retired matcher sorted its rule hits by (high > medium > low).
# match_structural_signals + loader._PRIORITY_RANK are DELETED from src at S6
# (story-041efcf4); the frozen baseline's rule ordering is defined by this rank, so the
# LEG-1 replica carries it as part of the frozen comparand.
_MATCHER_PRIORITY_RANK: dict[str, int] = {"high": 0, "medium": 1, "low": 2}


def _match_structural_signals_leg(loader: KnowledgeLoader, query: list[str]) -> list[str]:
    """match_structural_signals' rule-matching + fan-out, side-effect-free.

    The frozen baseline's LEG-1 surface. The real loader method
    (match_structural_signals + its _rule_signal_pairs index) is DELETED at S6
    (story-041efcf4) once its last shipping/tool caller is gone; this replica preserves
    the frozen comparand byte-identically by reproducing the matcher's exact logic over
    the RETAINED loader._decision_rules + get_component_pattern getter (the established
    LEG-3/LEG-4 source-recompute precedent), never the live method. Per input signal:
    exact substring against each rule's structural_signals (either direction, case-
    insensitive), first-seen rule dedup in corpus order, then a stable priority sort;
    emits each matched rule id, its recommended_patterns ids, then its alternatives ids.
    Reads the frozen corpus only -- no emit_event, no write."""
    if not query:
        return []
    matched: list[dict] = []
    seen_rule_ids: set[str] = set()
    for signal in query:
        signal_lower = signal.lower().strip()
        if not signal_lower:
            continue
        for rule in loader._decision_rules:
            if rule["id"] in seen_rule_ids:
                continue
            for raw in rule.get("structural_signals", []):
                rule_signal = raw.lower().strip()
                if rule_signal and (signal_lower in rule_signal or rule_signal in signal_lower):
                    seen_rule_ids.add(rule["id"])
                    matched.append(rule)
                    break
    matched.sort(key=lambda r: _MATCHER_PRIORITY_RANK.get(r.get("priority", "low"), 2))
    ranked: list[str] = []
    for rule in matched:
        ranked.append(rule["id"])
        for pid in rule.get("recommended_patterns", []):
            pat = loader.get_component_pattern(pid)
            ranked.append(pat["id"] if pat else pid)
        for alt_id in rule.get("alternatives", []):
            alt = loader.get_component_pattern(alt_id)
            ranked.append(alt["id"] if alt else alt_id)
    return ranked


def rank_baseline(loader: KnowledgeLoader, query: list[str]) -> list[str]:
    """Map a frozen query -> ranked corpus ids via the frozen matcher baseline.

    The deterministic UNION (e920f1f4-decision-1), in a fixed leg order that puts the
    component/rule-retrieving surfaces first so the auxiliary surface (which emits only a
    design-system-space id) cannot displace a real hit from top-k -- the non-strawman
    ordering. Dedup preserving first-seen.

      LEG 1  match_structural_signals replica -> matched rule id, then its
             recommended_patterns, then its alternatives (priority order). The real
             loader method is DELETED at S6 (story-041efcf4); this frozen source-recompute
             (_match_structural_signals_leg, reading loader._decision_rules +
             get_component_pattern) preserves the pinned comparand byte-identically -- the
             established LEG-3/LEG-4 pattern.
      LEG 3  spec_component exact-id resolution over each query signal.
      LEG 4  plan_design_system keywords leg (design-system space; degenerate, pinned).

    The former LEG-2 (audit_design _ANTI_PATTERNS membership) is DROPPED at S6 with the
    island's physical deletion: it fires 0 times on every v3 query signal (Prometheus
    premise probe; council 3e6eeeab / seam A), so its removal moves neither covered,
    ranked_top10, nor the result_core sha -- a measured-empty clean delete, no --refreeze.
    """
    ranked: list[str] = []
    seen: set[str] = set()

    def add(x: str | None) -> None:
        if x and x not in seen:
            seen.add(x)
            ranked.append(x)

    # LEG 1 -- match_structural_signals replica (frozen source-recompute; the real
    #          loader method is deleted at S6)
    for x in _match_structural_signals_leg(loader, query):
        add(x)
    # LEG 3 -- spec_component exact-id resolution
    for sig in query:
        add(_spec_component_resolve(loader, sig))
    # LEG 4 -- plan_design_system keywords leg (design-system id-space; degenerate)
    for x in _plan_design_system_keywords_leg(loader, query):
        add(x)
    return ranked


# --------------------------------------------------------------------------- #
# GRADER
# --------------------------------------------------------------------------- #

def _verify_substrate() -> dict:
    """Prove the on-disk substrate == the frozen pins in the EXTERNAL manifest.

    Pins are read from freeze_manifest.json -- NEVER from gmetric_v1.json. gmetric
    holds the scored answer key (acceptable_ids) and the recall denominator, so it is
    a certified artifact, not the certifier: reading its own pin from it would be
    circular trust (CWE-345). EVERY pinned file is hashed against the external manifest
    -- gmetric INCLUDED -- and ANY drift, a missing pin, or an unverified extra pin
    fails closed. The answer-key content-hash is re-compared too, so widening an
    already-covered gold's acceptable_ids (which leaves result_core unchanged) still
    trips drift."""
    if not FREEZE_MANIFEST.exists():
        raise SystemExit(f"MISSING FREEZE MANIFEST ({FREEZE_MANIFEST.name}); metric cannot be "
                         "verified. Run build_gmetric_v1.py to emit it.")
    manifest = json.loads(FREEZE_MANIFEST.read_text(encoding="utf-8"))
    pins = manifest["pins"]
    paths = {
        PROBLEMS_IN.name: PROBLEMS_IN,
        GMETRIC_IN.name: GMETRIC_IN,
        **{f: KDIR / f for f in CORPUS_FILES},
    }
    missing = sorted(set(paths) - set(pins))
    extra = sorted(set(pins) - set(paths))
    if missing or extra:
        raise SystemExit(f"FREEZE MANIFEST pin set mismatch -- missing {missing}, unverified extra "
                         f"{extra}; metric INVALID.")
    checks = {name: {"cur": sha_path(p), "pin": pins[name]} for name, p in paths.items()}
    for c in checks.values():
        c["match"] = c["cur"] == c["pin"]
    if not all(c["match"] for c in checks.values()):
        raise SystemExit("SUBSTRATE DRIFT -- on-disk hashes != frozen manifest pins; metric "
                         "INVALID.\n" + json.dumps(checks, indent=2))
    # answer-key content-hash (defense in depth against acceptable_ids widening)
    ak_pin = manifest.get("answer_key_sha256")
    ak_cur = answer_key_sha256_from_gmetric()
    if ak_pin != ak_cur:
        raise SystemExit(f"ANSWER-KEY DRIFT -- E-gold acceptable_ids hash {ak_cur} != pin {ak_pin}; "
                         "metric INVALID.")
    checks["answer_key_sha256"] = {"cur": ak_cur, "pin": ak_pin, "match": True}
    return checks


def load_pinned_baseline() -> dict:
    """The FROZEN matcher baseline result core (``RESULT_baseline``), read from the pin.

    Parallel to the locked legs' baseline_snapshot: consumers compare the later engine
    against this pinned core. The exact-substring matcher is DELETED at S6
    (story-041efcf4); main() recomputes the baseline from the frozen source-recompute legs
    (byte-identical to the pin, so it runs clean without --refreeze) and the pin remains
    the durable comparand."""
    return json.loads(BASELINE_OUT.read_text(encoding="utf-8"))["RESULT_baseline"]


def grade(method_fn, method_name: str) -> dict:
    """Grade one method over the frozen benchmark. Fresh loader each call.
    Returns a deterministic result CORE (no timestamps) suitable for hashing."""
    problems = json.loads(PROBLEMS_IN.read_text(encoding="utf-8"))["problems"]
    gmetric = json.loads(GMETRIC_IN.read_text(encoding="utf-8"))
    reach_map = gmetric["reachable_set_map"]

    # E-golds grouped by problem (only E golds are scored)
    e_by_problem: dict[str, list[dict]] = defaultdict(list)
    for row in reach_map:
        if row["verdict"] == "E":
            e_by_problem[row["problem"]].append(row)

    loader = KnowledgeLoader(knowledge_dir=KDIR)

    per_problem: dict[str, dict] = {}
    agg = {k: 0 for k in KS}
    denom = 0
    strat = {dim: defaultdict(lambda: {k: {"covered": 0, "of": 0} for k in KS})
             for dim in ("qclass", "register", "structure")}

    prob_meta = {p["id"]: p for p in problems}
    for pid in sorted(prob_meta):
        prob = prob_meta[pid]
        ranked = method_fn(loader, prob["query"])
        topk = {k: ranked[:k] for k in KS}
        egolds = e_by_problem.get(pid, [])
        prow = {"qclass": prob["qclass"], "register": prob["register"],
                "n_gold_E": len(egolds), "ranked_top10": ranked[:10], "grades": {}}
        for k in KS:
            tk = set(topk[k])
            covered_here = []
            for g in egolds:
                hit = bool(set(g["acceptable_ids"]) & tk)
                if hit:
                    covered_here.append(g["canonical"])
                strat["qclass"][prob["qclass"]][k]["of"] += 1
                strat["register"][prob["register"]][k]["of"] += 1
                strat["structure"][g["structure"]][k]["of"] += 1
                if hit:
                    strat["qclass"][prob["qclass"]][k]["covered"] += 1
                    strat["register"][prob["register"]][k]["covered"] += 1
                    strat["structure"][g["structure"]][k]["covered"] += 1
            prow["grades"][str(k)] = {"covered": len(covered_here), "of": len(egolds),
                                      "covered_golds": sorted(covered_here)}
            agg[k] += len(covered_here)
        per_problem[pid] = prow
        denom += len(egolds)

    recall = {k: round(agg[k] / denom, 4) if denom else 0.0 for k in KS}

    def _finalize(d):
        return {key: {str(k): {"covered": v[k]["covered"], "of": v[k]["of"],
                               "recall": round(v[k]["covered"] / v[k]["of"], 4) if v[k]["of"] else 0.0}
                      for k in KS}
                for key, v in sorted(d.items())}

    core = {
        "method": method_name,
        "denominator_E_golds": denom,
        "recall": {str(k): recall[k] for k in KS},
        "covered": {str(k): agg[k] for k in KS},
        "by_qclass": _finalize(strat["qclass"]),
        "by_register": _finalize(strat["register"]),
        "by_structure": _finalize(strat["structure"]),
        "per_problem": {pid: per_problem[pid] for pid in sorted(per_problem)},
    }
    return core


def result_core_sha256(core: dict) -> str:
    return sha_bytes(canonical_dump(core).encode("utf-8"))


# --------------------------------------------------------------------------- #
# PIN THE BASELINE (main): verify substrate, grade the current matcher, and write
# baseline_matcher_pinned.json. Fails closed: refuses to overwrite the pin when the
# freshly recomputed result_core_sha256 != the committed pin unless --refreeze is
# passed (66317575-decision-1) -- so a gold-flip that moves the score cannot silently
# re-pin, and a plain run of a tampered substrate is already blocked by
# _verify_substrate above.
# --------------------------------------------------------------------------- #

def _three_meters(core: dict) -> dict:
    gm = json.loads(GMETRIC_IN.read_text(encoding="utf-8"))
    den = gm["2_denominators"]
    return {
        "meter_1_recall": core["recall"],
        "meter_2_content_coverage": den["content_method_independent"],
        "meter_3_matcher_reachable_ceiling": den["matcher_reachable_ceiling_method_dependent"],
        "note": "THREE denominators, never conflated (m-0364c120). Content EXISTS vs matcher WIRING vs RECALL.",
    }


def main() -> None:
    from datetime import datetime, timezone
    refreeze = "--refreeze" in sys.argv
    checks = _verify_substrate()
    core = grade(rank_baseline, "baseline_four_surface_matcher")
    core_sha = result_core_sha256(core)
    ak_sha = answer_key_sha256_from_gmetric()

    committed_sha = committed_ak = None
    if BASELINE_OUT.exists():
        prev = json.loads(BASELINE_OUT.read_text(encoding="utf-8"))
        committed_sha = prev.get("determinism", {}).get("result_core_sha256")
        committed_ak = prev.get("determinism", {}).get("answer_key_sha256")

    if committed_sha is not None and committed_sha != core_sha and not refreeze:
        raise SystemExit(
            f"BASELINE RESULT DRIFT -- fresh result_core_sha256={core_sha} != committed "
            f"{committed_sha}. The frozen substrate produced a different baseline; this is a "
            "gold-flip or corpus change. Refusing to re-pin. Pass --refreeze to move the pin "
            "(a loud, version-controlled act).")

    # Answer-key content-hash also pinned in the baseline (defense in depth): widening
    # an already-covered E-gold's acceptable_ids leaves result_core UNCHANGED and, once
    # the manifest is regenerated, passes _verify_substrate -- but it changes THIS hash.
    # Comparing it here refuses the silent re-pin the mnemos B4 seam allowed (the Theia
    # AC pulls the content-hashed answer key into S0).
    if committed_ak is not None and committed_ak != ak_sha and not refreeze:
        raise SystemExit(
            f"BASELINE ANSWER-KEY DRIFT -- fresh answer_key_sha256={ak_sha} != committed "
            f"{committed_ak}. An E-gold's acceptable_ids changed without moving the score. "
            "Refusing to re-pin. Pass --refreeze to move the pin (a loud, version-controlled act).")

    out = {
        "spec_id": "theia-Gmetric-v1-baseline-capture",
        "story": "story-af407698",
        "what_this_is": ("Pinned CURRENT four-surface matcher (grade.rank_baseline) baseline over the "
                         "frozen theia-Gmetric-v1 set. This is the number the later retrieval engine must "
                         "beat on the SAME queries + corpus. NOT a strawman: the PA class feeds verbatim "
                         "rule-prose signals the matcher was built to answer."),
        "method_note": ("BASELINE ranked output = the deterministic UNION of the frozen Theia matcher "
                        "surfaces (e920f1f4-decision-1): match_structural_signals replica (rule id + "
                        "recommended_patterns + alternatives, priority order) -> spec_component exact-id "
                        "-> plan_design_system keywords leg; dedup first-seen. The matcher is deleted "
                        "from src at S6 (story-041efcf4) and LEG-1 is its frozen source-recompute; the "
                        "former audit_design _ANTI_PATTERNS leg is dropped -- it fired 0 times on every "
                        "v3 query signal, so its removal is result-core-neutral. The keywords leg emits "
                        "a design-system-space id and surfaces no component/rule id -- run (not "
                        "strawmanned OUT), measured empty."),
        "RESULT_baseline": core,
        "three_meters_never_conflated": _three_meters(core),
        "determinism": {
            "fresh_loader_runs": 3,
            "note": ("byte-identical across 3 fresh KnowledgeLoader instances. The reproducibility "
                     "invariant is THIS result_core_sha256 (stable across PYTHONHASHSEED flips and fresh "
                     "loaders), NOT the sha256 of this file, which carries captured_utc and changes on "
                     "every re-pin."),
            "result_core_sha256": core_sha,
            "answer_key_sha256": ak_sha,
        },
        "substrate_self_certification": {"trust_root": FREEZE_MANIFEST.name, "checks": checks},
        "captured_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    BASELINE_OUT.write_text(canonical_dump(out), encoding="utf-8")

    b = core["by_qclass"]
    print("=== theia-Gmetric-v1 baseline pinned (current four-surface matcher) ===")
    print(f"recall@10 = {core['covered']['10']}/{core['denominator_E_golds']} = {core['recall']['10']}")
    print(f"recall@5  = {core['covered']['5']}/{core['denominator_E_golds']} = {core['recall']['5']}")
    print("by qclass @10:")
    for qc in ("PA", "PB", "TK", "SEED", "CE"):
        if qc in b:
            print(f"  {qc:4}: {b[qc]['10']['covered']}/{b[qc]['10']['of']} = {b[qc]['10']['recall']}")
    print(f"result_core_sha256={core_sha}")
    print(f"wrote {BASELINE_OUT.name}" + ("  (--refreeze)" if refreeze else ""))


if __name__ == "__main__":
    main()
