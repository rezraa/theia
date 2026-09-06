# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""Curated blind recognizer + accessor-shape harness for the TYPED-INDEX S0 gate
(story-1c54b0b7, council ae492280 / m-5a5837da; root cause m-698d738c).

*** THE NORTH STAR. *** Freeze a blind, per-stratum recall@10 baseline for Theia's
TWO-VIEW signal-index accessor (``kb.get_signal_index`` for 66 components +
``kb.get_system_signal_index`` for 54 design systems), so the later collapse of those
two accessors into ONE nested ``{component_signals, system_signals}`` view (S1) cannot
merge unless its unified run equals-or-beats this baseline on BOTH strata. The ONLY
variable between the two arms is PRESENTATION SHAPE; corpus, engine, and ids are held
constant.

This module is the SYSTEM stratum's gold-blind recognizer (the LLM stand-in) plus the
arm harness. The COMPONENT stratum reuses its already-frozen v3 recognizer
(``theia_engine_bench``) verbatim — S0 does not re-derive a settled measurement
(Directive 2); it cites it and adds the second (system) stratum, which was NEVER
end-to-end benchmarked because the live two-index summon path was broken (root cause
m-698d738c: the filename-keyed seed minted only ``get_signal_index``).

Recognition is ONE engine, not a fork: the 3-leg recognizer lives once in
``theia_engine_bench._recognize_over`` and is bound here to the design-system surface —
OVERLAP (>= 2 stemmed content tokens against a signal text), EXACT (query verbatim == a
catalogued signal text), and SEED-FROM-NODE (a query token that IS a design-system id ->
that system's own signal ids via ``system_signal_ids_for``). The tokenizer (``_toks``) is
imported, not copied. test_typed_index_s0 proves, by parity, that this system path and
the component path are the SAME behaviour on the shared engine (m-e8ccb163: measured per
stratum, never pooled).

NO SHAPE WORKING MEMORY (a MEASURED divergence from the component bench, not a shortcut).
The component bench needs a SHAPE bridge because component problem-language shares few
VERBATIM tokens with component signal texts. Design-system problem-language does not have
that gap: a team choosing Material You literally describes "Android, Jetpack Compose,
wallpaper theming" — the very words its signals carry. Query-alone recall was measured
byte-identical to query+SHAPE recall (25/25, gold ranked #1-2), so a SHAPE bridge would
be dead weight that could only be accused of encoding the answer. Recognizing on the
frozen query ALONE is the stricter, more sensitive, more defensible blind measurement:
a future corpus edit that weakens a system's signals drops recall and trips the gate
instead of being masked by an authored SHAPE.

Firewall: imports only the sibling frozen bench (theia-only) + stdlib. Reads only
problems_blind_sys + the loader's live system index; NEVER reads gmetric_sys_*.json (the
answer key). No live-DB access.
"""

from __future__ import annotations

import json
from pathlib import Path

# The shared recognition primitives (one source of truth; theia-only sibling).
from theia_engine_bench import _recognize_over, _toks  # noqa: F401  (_toks re-exported for the parity test)

HERE = Path(__file__).resolve().parent
PROBLEMS_IN = HERE / "problems_blind_sys_v1.json"  # query text is generation-invariant


def _load_problems() -> list[dict]:
    return json.loads(PROBLEMS_IN.read_text(encoding="utf-8"))["problems"]


def _query_to_pid() -> dict[tuple[str, ...], str]:
    """Map each frozen SYSTEM query (as a tuple) -> its problem id, from problems_blind_sys."""
    return {tuple(p["query"]): p["id"] for p in _load_problems()}


def _system_seed(loader, token: str) -> list[str]:
    """SEED-FROM-NODE resolver for the design-system surface.

    A query token that IS a design-system id (kebab<->snake) -> that system's own signal
    ids (``system_signal_ids_for``); ``[]`` for a non-system token. The design-system twin
    of theia_engine_bench.recognize's component seed leg, over the SAME shared engine.
    """
    ids: list[str] = []
    for cand in (token, token.replace("-", "_"), token.replace("_", "-")):
        if loader.get_design_system(cand):
            ids += loader.system_signal_ids_for(cand)
    return ids


def recognize_system(loader, query: list[str], index: list[dict] | None = None) -> list[str]:
    """Recognise matched design-system signal ids for one problem. Deterministic, gold-blind.

    Binds the shared :func:`theia_engine_bench._recognize_over` engine to the SYSTEM
    surface (no SHAPE — query alone; see the module docstring). ``index`` selects the ARM:
    ``None`` reads the two-view accessor ``loader.get_system_signal_index()`` (BASELINE
    arm); an explicit list is the surface the UNIFIED arm supplies
    (``nested_view(loader)["system_signals"]``). The engine reads only the list it is
    handed, so if the two arms' surfaces are byte-identical the recognition — and therefore
    recall — is identical (the S0 invariant).
    """
    idx = loader.get_system_signal_index() if index is None else index
    return _recognize_over(idx, lambda t: _system_seed(loader, t), query, "")


def build_matches(loader, index: list[dict] | None = None) -> dict[str, list[str]]:
    """Recognise matched system signal ids for every SYSTEM problem -> {pid: [signal_id, ...]}.

    Pure function of (problems_blind_sys, the system signal index). Used both to emit the
    frozen snapshot (build_typed_index_s0.py) and to prove live == frozen.
    """
    return {p["id"]: recognize_system(loader, p["query"], index=index) for p in _load_problems()}


# --------------------------------------------------------------------------- #
# rank_system: the method_fn for grade.grade() over the SYSTEM answer key. Recomputes
# recognition LIVE (query -> matched system signals -> hydrate_systems) so the baseline
# measures the whole design-system retrieval path end to end through the production
# ``loader.hydrate_systems`` (edge = related_systems). Same signature contract as
# grade.rank_baseline so grade.grade drives it verbatim.
# --------------------------------------------------------------------------- #

def rank_system(loader, query: list[str], index: list[dict] | None = None) -> list[str]:
    """Map a frozen SYSTEM query -> ranked design-system ids via the hydrate_systems path.

    Recognises matched system signal ids against the arm's index surface, hydrates through
    the production system engine, and returns the ranked system ids. ``index`` selects the
    arm (see :func:`recognize_system`).
    """
    matched = recognize_system(loader, query, index=index)
    res = loader.hydrate_systems(matched, k=10, fan_out=True)
    return [p["id"] for p in res.patterns]


# --------------------------------------------------------------------------- #
# The presentation-shape ARM adapter — the ONLY variable S0 isolates.
# --------------------------------------------------------------------------- #

def nested_view(loader) -> dict[str, list[dict]]:
    """Build the UNIFIED nested view ``{component_signals, system_signals}`` from the SAME
    two accessors the baseline arm reads separately.

    This is the presentation-shape reshape the collapse (S1) will move into the loader;
    S0 constructs it at the harness level (NOT a production accessor — that is S1, out of
    scope) so the unified ARM can be measured today with corpus/engine/ids held constant.
    S1's gate: replace this with the loader's real nested accessor and re-run — recall must
    still be >= the frozen baseline on BOTH strata.
    """
    return {
        "component_signals": loader.get_signal_index(),
        "system_signals": loader.get_system_signal_index(),
    }
