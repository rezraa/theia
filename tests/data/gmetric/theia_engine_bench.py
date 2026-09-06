# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""Shape-C engine harness for theia-Gmetric (story-cb7e532b, S0-FIX; council 3e6eeeab).

BAR-1 is measured by feeding the SAME frozen benchmark queries through the ported
Shape-C engine (``loader.hydrate``) and grading with ``grade.grade`` VERBATIM. The
grader hands a method ``prob["query"]``; ``hydrate`` needs matched *signal ids*.
The bridge is a RECOGNIZER — in production an LLM recognises a problem's signals
against ``get_signal_index()`` in working memory; the benchmark cannot run an LLM
deterministically, so this module is its FROZEN, gold-blind stand-in (mirroring the
SHIPPED mnemos_engine_bench.py by READING it, never importing it — firewall:
theia.* only).

*** WHY A CURATED SHAPE, AND WHY IT IS BLIND (S0-FIX north star). ***
The predecessor recognizer was a degenerate prose stand-in: exact-signal-text +
seed-from-node ONLY. It structurally capped the problem-language register (PB/CE) at
0 — a paraphrased problem shares few or no VERBATIM tokens with a component's
signal texts, and the verbatim-query contract forbids reading the problem statement
into the corpus. So it measured the RECOGNIZER's poverty, not the engine: the signals
ARE in the migrated index and hydrate retrieves them GIVEN recognised ids. Coeus and
Mnemos do not have this hole because their benchmark feeds a curated, frozen
recognition per problem. Theia now matches that standard.

The recogniser, made maximally auditable and GOLD-BLIND (Mnemos parity):
    recognition(query) = the union of three legs, all deterministic and gold-blind —
      1. OVERLAP: signals whose text shares >= 2 stemmed content tokens with
         (query + SHAPE[pid]).  SHAPE is the recogniser's WORKING MEMORY: a
         designer's restatement of the problem's UI shape in standard component
         vocabulary, authored ONCE from the frozen problem/query ALONE — NEVER
         from gmetric's acceptable_ids (never read here) and never tuned toward gold
         after a result was seen (the blind-curation gate). The mechanical matcher
         does the id-picking, so a SHAPE string cannot secretly encode a pattern id;
         a reviewer audits each {problem -> matched signal_texts} pair (emitted into
         theia_matches_*.json) against the problem alone.
      2. EXACT: query string == a catalogued signal text (verbatim). This is how the
         PA class lands — its queries ARE decision-rule structural_signals that S2
         migrated verbatim ONTO the components those rules recommend.
      3. SEED-FROM-NODE: a query token that IS a component id (kebab<->snake) ->
         that component's own signal ids. This is how the TK/SEED token classes land
         — the query IS the component token under test.

SHAPE is authored from the ``problem`` sentence + the verbatim ``query`` and names
no acceptable_id the problem's own domain language does not already imply. It uses
space-separated natural UI vocabulary (``data table``, ``toggle switch``), never the
underscore/kebab corpus id (``data_table``): the OVERLAP leg matches signal TEXT,
not ids, so a token is a bridge to a signal's prose, not an encoded answer. The A
(absent) canon-edge problems (P30/P31) carry a SHAPE too, harmlessly: they have no
E-gold and never score.

Two method_fns are exported (same contract as ``grade.rank_baseline``):
  * ``rank_engine`` — the pure hydrate path (the engine's OWN reach, stratified);
  * ``rank_union``  — the retrieval SYSTEM: the existing matcher UNION the engine,
    the direct non-regression comparand (routes through production ``hydrate`` and
    must not drop below the pinned baseline; the matcher is untouched here).

Firewall: imports only the sibling frozen grader (theia-only), stdlib. Reads only
problems_blind + the loader's live index; NEVER reads gmetric_*.json (the answer
key). No live-DB access.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBLEMS_IN = HERE / "problems_blind_v1.json"  # query text is generation-invariant

# --------------------------------------------------------------------------- #
# Deterministic, gold-independent text normalisation (IR-standard). A faithful
# mirror of mnemos_engine_bench's tokenizer (read-only) so the two benches grade
# on one normalisation — NOT a divergent fork. This lives in the TEST HARNESS
# (the LLM stand-in), never in shipping retrieval code: Theia's shipping engine
# does NO keyword matching; it takes matched signal ids as input (from the LLM in
# production, from this recognizer in the benchmark). So this token overlap is not
# the loader's "no fuzzy matching" doctrine's concern.
# --------------------------------------------------------------------------- #
_STOP = set(
    "a an the of to in for and or is are with be by on at from into over as you i "
    "my me can how what is do so each some any all more most only not that this "
    "these those it its their them then than we our your there many single every "
    "out back same much may must onto per keep given find".split()
)


def _stem(w: str) -> str:
    """Conservative plural-only normalisation (deterministic, gold-independent).

    Strips a single trailing plural ``s`` (``cards``->``card``, ``tables``->``table``,
    ``rows``->``row``) with a length guard and a guard against words that merely end
    in ``s`` (``status``, ``progress``, ``analysis``). No aggressive ``es``/``ing``/
    ``ly`` stripping — that over-stems and adds noise.
    """
    if len(w) > 4 and w.endswith("s") and not w.endswith(("ss", "us", "is", "as", "os")):
        return w[:-1]
    return w


def _toks(s: str) -> set[str]:
    """Lowercase -> content tokens (non-alnum split, stop-word + length filter, stem)."""
    raw = [t for t in re.split(r"[^a-z0-9]+", s.lower()) if t and t not in _STOP and len(t) > 2]
    return {_stem(t) for t in raw}


# --------------------------------------------------------------------------- #
# SHAPE: the recogniser's working memory, keyed by problem id. Each value is a
# designer's restatement of that problem's UI SHAPE in standard component
# vocabulary, authored from the frozen problem/query ALONE (gold-blind: no gmetric
# read, no corpus id named — space-separated words, never an underscore id). Frozen
# here; theia_matches_v3.json is the pinned snapshot, and test_retrieval_bar1
# asserts live recognition == it.
# --------------------------------------------------------------------------- #
SHAPE: dict[str, str] = {
    # PA — prose, rule-prose-aligned (the EXACT leg lands these; SHAPE is backup).
    "P01": "dashboard summary metric cards across the top detailed data tables below grid layout",
    "P02": "guided multi step onboarding flow setup one screen at a time steps progress indicator",
    "P03": "screen rendering more than a hundred rows of structured records table pagination pages",
    "P04": "action requires the user to stop and make a decision before continuing modal dialog confirmation",
    "P05": "page or section shows placeholder shapes while content is still loading skeleton",
    "P06": "view surfaces key performance indicators and metrics dashboard metric cards charts",
    "P07": "navigation structure three or more levels deep nested hierarchy sidebar tree breadcrumb",
    "P08": "state signalled by colour alone red green pill redundant text label icon accessibility cue",
    # PB — prose, problem-language (blind). SHAPE is the bridge the register needs.
    "P09": "operations dashboard live health metric numbers at a glance summary cards above a scrolling data table of recent alerts rows grid",
    "P10": "status pill relies on red and green colour alone colour blind operators need another cue text label badge tag tooltip icon",
    "P11": "confirmation popup modal dialog open keyboard focus trap stays inside overlay until dismissed accessibility",
    "P12": "screen shows a big arrangement of tiles grid of cards responsive columns tapping one tile opens its details",
    "P13": "settings page many on off toggle switches users lost scrolling grouped collapsible accordion sections",
    "P14": "long running export task progress indicator show it is working spinner announce completion toast notification when finished",
    "P15": "new accounts land on a blank empty projects screen no data guide the new user first run call to action",
    "P16": "power users jump anywhere by typing a few letters command palette keyboard quick search autocomplete instead of menus",
    # TK — token, component-id vocabulary (the SEED leg lands these; SHAPE is backup).
    "P17": "sortable paginated table of structured records",
    "P18": "expandable collapsible view of nested hierarchical data tree",
    "P19": "keyboard driven overlay to run commands by name palette",
    "P20": "binary on off control toggle switch",
    "P21": "calendar control for choosing a date picker",
    "P22": "zero data placeholder for a list or table empty",
    # SEED — token, rich-spec-vs-husk. SHAPE restates the archetype the token names.
    "P23": "step indicator multi step progress wizard",
    "P24": "dropdown menu select options list",
    "P25": "single line text input field form entry label",
    "P26": "primary navigation bar top menu header links",
    "P27": "modal overlay dialog centered on screen",
    # CE — canon-edge probes. P28/P29 exist (E); P30/P31 are ABSENT (A, never score).
    "P28": "small numeric indicator showing an unread count badge on top of an icon notification",
    "P29": "colour picker with a hue wheel and a hex input swatch palette",
    "P30": "interactive product tour coach mark bubbles pointing at interface elements onboarding walkthrough spotlight",
    "P31": "draggable splitter between two panes drag to resize each side divider handle split pane",
}


def _load_problems() -> list[dict]:
    return json.loads(PROBLEMS_IN.read_text(encoding="utf-8"))["problems"]


def _query_to_pid() -> dict[tuple[str, ...], str]:
    """Map each frozen query (as a tuple) -> its problem id, from problems_blind."""
    return {tuple(p["query"]): p["id"] for p in _load_problems()}


def _recognize_over(index, resolve_seed, query: list[str], shape: str) -> list[str]:
    """Generic blind 3-leg recognizer over ANY signal-index surface (parameterized).

    The ONE recognition engine, shared by the component recognizer (:func:`recognize`,
    below) and the design-system recognizer (``typed_index_bench``, the TYPED-INDEX S0
    gate, story-1c54b0b7), so both index shapes run IDENTICAL legs from one source of
    truth — no forked leg logic. A parity test (test_typed_index_s0) proves the system
    path and this component path are the same behaviour on the shared engine.

      1. OVERLAP — a signal whose text shares >= 2 stemmed content tokens with
         (query + SHAPE working memory).
      2. EXACT — a query string that verbatim IS a catalogued signal text.
      3. SEED-FROM-NODE — ``resolve_seed(query_token)`` returns that node's own signal
         ids when the token IS a node id, else ``[]``.

    ``index`` is the ``[{signal_id, signal_text, ...}]`` view of the target surface;
    ``resolve_seed`` closes over the loader's node getters. Returns a sorted, de-duped
    list of signal ids. Reads only its arguments — never the gold answer key.
    """
    q: set[str] = set()
    for qs in query:
        q |= _toks(qs)
    q |= _toks(shape)

    text2id = {e["signal_text"].strip().lower(): e["signal_id"] for e in index}
    matched: set[str] = set()

    # 1. OVERLAP leg — problem-language (PB) / rule-prose (PA/CE).
    for e in index:
        if len(q & _toks(e["signal_text"])) >= 2:
            matched.add(e["signal_id"])
    # 2. EXACT leg — a query that verbatim IS a catalogued signal.
    for qs in query:
        hit = text2id.get(qs.strip().lower())
        if hit is not None:
            matched.add(hit)
    # 3. SEED-FROM-NODE leg — a query token that IS a node id.
    for qs in query:
        matched.update(resolve_seed(qs.strip()))
    return sorted(matched)


def recognize(loader, query: list[str], shape: str) -> list[str]:
    """Recognise matched component signal ids for one problem. Deterministic, gold-blind.

    A thin binding of the shared :func:`_recognize_over` engine to the COMPONENT index:
    the OVERLAP/EXACT legs read ``loader.get_signal_index()`` and the SEED-FROM-NODE leg
    resolves a query token that IS a component id (kebab<->snake) to its own signal ids.
    Returns a sorted, de-duplicated list of signal ids. Reads only its arguments +
    the loader's live index — never the gold answer key.
    """
    def _component_seed(token: str) -> list[str]:
        ids: list[str] = []
        for cand in (token, token.replace("-", "_"), token.replace("_", "-")):
            if loader.get_component_pattern(cand):
                ids += loader.signal_ids_for(cand)
        return ids

    return _recognize_over(loader.get_signal_index(), _component_seed, query, shape)


def build_matches(loader) -> dict[str, list[str]]:
    """Recognise matched signal ids for every problem -> {pid: [signal_id, ...]}.

    Pure function of (problems_blind, loader's signal index, SHAPE). Used both to
    emit the frozen snapshot (build_theia_matches.py) and to prove live == frozen.
    """
    out: dict[str, list[str]] = {}
    for p in _load_problems():
        out[p["id"]] = recognize(loader, p["query"], SHAPE.get(p["id"], ""))
    return out


# --------------------------------------------------------------------------- #
# rank_engine: the method_fn for grade.grade(), the Shape-C analogue of
# grade.rank_baseline. Recomputes recognition LIVE (query -> matched signals ->
# hydrate) so BAR-1 measures the whole engine path end to end; the frozen
# theia_matches_v3.json + its pin + the live==frozen test guard reproducibility.
# --------------------------------------------------------------------------- #
_Q2PID: dict[tuple[str, ...], str] | None = None


def rank_engine(loader, query: list[str]) -> list[str]:
    """Map a frozen query -> ranked component ids via the pure Shape-C hydrate path.

    Resolves the query to its problem id (to fetch the recogniser's working-memory
    SHAPE), recognises matched signal ids against the loader's LIVE index, hydrates
    through the production engine, and returns the ranked ids. Same signature
    contract as ``grade.rank_baseline`` so ``grade.grade`` drives it verbatim.
    """
    global _Q2PID
    if _Q2PID is None:
        _Q2PID = _query_to_pid()
    pid = _Q2PID.get(tuple(query))
    shape = SHAPE.get(pid, "") if pid else ""
    matched = recognize(loader, query, shape)
    res = loader.hydrate(matched, k=10, fan_out=True)
    return [p["id"] for p in res.patterns]


def rank_union(loader, query: list[str]) -> list[str]:
    """The retrieval SYSTEM: the current matcher UNION the engine hydrate path.

    The direct non-regression comparand — it INCLUDES the production ``hydrate``
    leg (so BAR-1 is "reproduced through grade.grade()+production hydrate") and,
    because the matcher is untouched here, it can only match or exceed the pinned
    baseline. Matcher legs first (they surface real component/rule ids the two
    auxiliary baseline legs cannot displace), then the engine's ranked ids, deduped
    first-seen. Imported lazily so this module stays free of a hard grade import at
    definition time.
    """
    import grade  # sibling frozen grader (theia-only); path-injected by the test

    ranked: list[str] = []
    seen: set[str] = set()

    def add(x: str | None) -> None:
        if x and x not in seen:
            seen.add(x)
            ranked.append(x)

    for x in grade.rank_baseline(loader, query):
        add(x)
    for x in rank_engine(loader, query):
        add(x)
    return ranked
