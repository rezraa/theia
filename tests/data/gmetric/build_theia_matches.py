# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""Emit the FROZEN recognizer snapshot for theia-Gmetric (story-cb7e532b, S0-FIX).

Provenance record + emitter for the two recognizer artifacts (the S0-FIX analogue of
the shipped mnemos_matches; council 3e6eeeab): a FROZEN recognition, gold-blind and
hash-pinned, so no hand-edit can hide in the measured path.

  * theia_matches_<VER>.json    -- the frozen recognition: {problem_id -> [signal_id]}
    PLUS the human-auditable {problem_id -> [signal_text]} so a reviewer can confirm
    each recognised signal describes the problem's shape, from the problem alone.
    Produced by theia_engine_bench.build_matches over the frozen problems_blind + the
    live signal index; NEVER reads gmetric_*.json (the answer key), so recognition is
    provably gold-blind.
  * theia_matches_freeze<_SUF>.json -- the recognizer trust root: pins the frozen
    recognition snapshot + the corpus file its signal index derives from. Kept
    SEPARATE from the S0 freeze_manifest.json on purpose: grade._verify_substrate
    enforces an EXACT 6-pin set (problems + gmetric + 4 corpus; missing/extra fails
    closed) and build_gmetric_v1.py regenerates that manifest with exactly those pins,
    so adding a pin there would break the S0 grader and drift from its builder. A
    separate recognizer manifest gives recognition its own frozen + hash-pinned +
    tamper-evident trust root without touching the byte-frozen S0 substrate.
    test_retrieval_bar1 verifies against BOTH.

The pin set is PRECISE, not defensive-by-accident: recognition is a pure function of
(problems_blind, the COMPONENT signal index). The loader builds that index from
component_patterns.json ALONE (decision_rules' problem-language was migrated ONTO the
components at S2 and now lives in component_patterns.json). So exactly three inputs
govern the snapshot -- the matches file, problems_blind, and component_patterns.json.

Determinism: build_matches is a pure function; re-running emits byte-identical
theia_matches_<VER>.json (its own sha256 is stable -- no timestamps in the pinned
body). Run under any PYTHONHASHSEED and the signal ids (content hashes) are identical.

Firewall: imports only theia.* + stdlib (never coeus.*/othrys.*/mnemos.*). No live-DB
access.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

from theia.knowledge.loader import KnowledgeLoader

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import theia_engine_bench as eng  # noqa: E402  (path-injected sibling harness)

KDIR = Path(__file__).resolve().parents[3] / "src" / "theia" / "knowledge"
COMPONENTS_FILE = "component_patterns.json"  # the ONE source of the component signal index

# Corpus-freeze generation (see build_gmetric_v1._VER). recognize() reads the LIVE
# migrated index via the loader; the problem QUERIES are generation-invariant. Default
# v1 preserves provenance; S0-FIX re-pins on v3.
_VER = os.environ.get("THEIA_GMETRIC_VERSION", "v1")
_SUF = "" if _VER == "v1" else f"_{_VER}"
MATCHES_OUT = HERE / f"theia_matches_{_VER}.json"
FREEZE_OUT = HERE / f"theia_matches_freeze{_SUF}.json"
PROBLEMS_IN = HERE / f"problems_blind_{_VER}.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_dump(obj) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def main() -> None:
    loader = KnowledgeLoader(knowledge_dir=KDIR)
    index = loader.get_signal_index()
    id2text = {e["signal_id"]: e["signal_text"] for e in index}

    matches = eng.build_matches(loader)
    # human-auditable companion: the signal TEXT behind each recognised id
    matches_text = {pid: [id2text[s] for s in sigs] for pid, sigs in matches.items()}

    out = {
        "spec_id": "theia-Gmetric-recognizer",
        "story": "story-cb7e532b",
        "authored_by": "Theia",
        "what": (
            "FROZEN gold-blind recognition {problem_id -> matched signal_ids} that "
            "bridges each frozen benchmark query to the Shape-C hydrate path. The "
            "LLM-stand-in for the benchmark (production uses a live LLM). Produced by "
            "theia_engine_bench.recognize over problems_blind + the signal index; "
            "independent of gmetric's acceptable_ids (never read here)."
        ),
        "recognition_rule": (
            "signal matched iff (query + authored SHAPE working-memory) overlaps its "
            "text by >= 2 stemmed content tokens, OR query == signal_text (EXACT leg), "
            "OR a query token IS a component id (SEED-FROM-NODE leg). SHAPE is a "
            "designer's gold-blind restatement of each problem's UI shape in standard "
            "component vocabulary (space-separated words, never an underscore id); the "
            "mechanical matcher picks ids, so SHAPE cannot encode a pattern id. Audit "
            "matches_by_signal_text against problems_blind."
        ),
        "corpus_snapshot_sha256": {COMPONENTS_FILE: sha(KDIR / COMPONENTS_FILE)},
        "n_problems": len(matches),
        "matches": {pid: matches[pid] for pid in sorted(matches)},
        "matches_by_signal_text": {pid: matches_text[pid] for pid in sorted(matches_text)},
    }
    MATCHES_OUT.write_text(canonical_dump(out), encoding="utf-8")

    freeze = {
        "spec_id": "theia-Gmetric-recognizer-freeze",
        "story": "story-cb7e532b",
        "what": (
            "Recognizer trust root: pins the frozen recognition snapshot + the corpus "
            "file its signal index derives from (component_patterns.json). Separate "
            "from the S0 freeze_manifest.json (which grade._verify_substrate holds to "
            "an exact pin set). Regenerating this manifest is the only way to move a "
            "pin -- a visible, reviewable act."
        ),
        "hash_algo": "sha256",
        "pins": {
            MATCHES_OUT.name: sha(MATCHES_OUT),
            PROBLEMS_IN.name: sha(PROBLEMS_IN),
            COMPONENTS_FILE: sha(KDIR / COMPONENTS_FILE),
        },
    }
    FREEZE_OUT.write_text(canonical_dump(freeze), encoding="utf-8")

    print(f"wrote {MATCHES_OUT.name} sha256={sha(MATCHES_OUT)[:16]}... ({len(matches)} problems)")
    print(f"wrote {FREEZE_OUT.name} pinning {len(freeze['pins'])} files sha256={sha(FREEZE_OUT)[:16]}...")
    total = sum(len(v) for v in matches.values())
    print(f"total recognised signal ids: {total} (mean {total/len(matches):.1f}/problem)")


if __name__ == "__main__":
    main()
