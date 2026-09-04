# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""Knowledge loader for Theia.

Loads design_systems.json, component_patterns.json, accessibility_standards.json,
and decision_rules.json and provides pure retrieval, the Shape-C signal-index
hydrate engine (problem-language signals hydrated directly into components,
returned in a four-state fail-closed envelope), the legacy structural signal
matcher (exact substring against decision_rules), and constraint filtering.

No fuzzy keyword matching.  No tokenization.  No Jaccard scoring.
"""

from __future__ import annotations

import hashlib
import heapq
import json
from dataclasses import dataclass, field
from pathlib import Path

_KNOWLEDGE_DIR = Path(__file__).parent


# ==========================================================================
# Shape-C retrieval engine — the signal-index hydrate path
# (problem-language signals -> component), a JUSTIFIED MIRROR of the SHIPPED
# mnemos.knowledge.loader (m-10b6fbf1) / coeus.knowledge.loader ``_SignalEngine``.
# Theia runtime code NEVER imports coeus.*/othrys.*/mnemos.* (the titan-decoupling
# firewall, feedback_titan_decoupling_no_othrys_import); the mirror is kept
# faithful by a semantic-parity drift test (tests/test_firewall.py). Adapted for
# the Theia corpus: the index source is each COMPONENT's ``signals`` field
# (Coeus-parity — Coeus indexes ``signals`` too, so this is not a new divergence),
# the fan-out edge is ``related_patterns`` (materialized in S2; empty until then,
# so hydrate returns seed-only, never a husk), and the node index is a FLAT
# ``id -> component`` map (shedding the Mnemos ``(structure_id, pattern)`` tuple).
#
# The engine is PARAMETERIZED over a ``_NamedIndex`` seam — (index source, signal
# field, edge field) — so S5 adds a SECOND named index over ``design_systems``
# (edge ``related_systems``) that REUSES every primitive below (ceilings, floor,
# state vocab, ``_signal_id``, ``RetrievalResult``, ``deep_freeze``, the facet
# gate) with ZERO duplicated engine code. The drift test proves those primitives
# are shared across both index shapes and that no cross-corpus node surfaces in
# the wrong index's result (component<->system id-spaces are disjoint — Theia's
# binding reservation, council 3e6eeeab). S1 parameterized the seam and proved
# sharing; S5 builds that second index (``self._systems_index``, wired below) over
# these SAME primitives — the two indices differ only in their _NamedIndex axes.
# ==========================================================================
#
# The four-state retrieval envelope is the single output contract. Every
# retrieval resolves to exactly one state, and abstention is a structural field
# rather than an empty list narrated as an answer (fail closed, never a husk).
HIT = "hit"                        # >=1 component hydrated at/above the confidence floor
LOW_CONFIDENCE = "low_confidence"  # components hydrated, best below the confidence floor
NO_MATCH = "no_match"              # signals recognised but none map to a corpus component
DANGLING = "dangling"              # signals map only to ids absent from the corpus

# Two named ceilings bound the fan-out's agency, applied where cost is incurred:
_SEED_CAP: int = 64    # max seed components admitted to fan-out (bound BEFORE expansion)
_TOPK_CAP: int = 50    # hard ceiling on hydrated results (bound AFTER expansion)

# A hit needs at least this many corroborating votes (direct + propagated); a
# lone single vote is surfaced but flagged low_confidence. Auditable integer,
# not a tuned score.
_CONFIDENCE_FLOOR: int = 2


def _signal_id(text: str) -> str:
    """Deterministic, byte-reproducible id for a signal's text.

    A stable content hash so the corpus-derived index recomputes identically
    across processes (independent of PYTHONHASHSEED) and the LLM/harness can
    refer to a signal by a short id.
    """
    return "sig-" + hashlib.sha1(text.strip().encode("utf-8")).hexdigest()[:12]


@dataclass(frozen=True)
class RetrievalResult:
    """The single retrieval output contract (see the four states above).

    ``patterns`` is the ranked, hydrated result (empty for the abstention
    states — the field name is kept ``patterns`` for cross-titan envelope parity;
    the nodes are Theia components). ``votes`` is the transparent, auditable tally
    used for ranking (component_id -> integer vote count). ``dangling`` surfaces
    any referenced component id that did not resolve — an integrity failure is
    reported, never masked by a husk. ``unmatched_signals`` records matched signal
    ids the index did not recognise.
    """

    state: str
    patterns: list[dict] = field(default_factory=list)
    votes: dict[str, int] = field(default_factory=dict)
    dangling: list[str] = field(default_factory=list)
    unmatched_signals: list[str] = field(default_factory=list)
    reason: str = ""


class _FrozenDict(dict):
    """A read-only ``dict``: refuses in-place mutation, serialises as a plain dict.

    Hydrated components are deep-frozen through this type so a caller cannot corrupt
    the shared singleton corpus by mutating a returned node (the shallow-copy
    shared-reference hazard: ``{**node}`` copies the top dict but aliases its nested
    lists). It subclasses ``dict`` so ``json.dumps`` and ``["key"]`` reads work
    unchanged; only the mutators are sealed.
    """

    __slots__ = ()

    def _readonly(self, *_a: object, **_k: object) -> None:
        raise TypeError("hydrated component is read-only")

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = _readonly


def deep_freeze(obj: object) -> object:
    """Recursively copy *obj* into an immutable, JSON-serialisable structure.

    Dicts become :class:`_FrozenDict`, lists/tuples become tuples, scalars pass
    through. The copy severs every shared reference to the source, so this both
    fixes the shared-ref corruption hazard and makes the result tamper-proof.
    """
    if isinstance(obj, dict):
        return _FrozenDict({k: deep_freeze(v) for k, v in obj.items()})
    if isinstance(obj, (list, tuple)):
        return tuple(deep_freeze(v) for v in obj)
    return obj


def _parse_team_range(token: object) -> tuple[float, float] | None:
    """Parse a ``team_size`` token (``"1-5"``, ``"50+"``, ``"3"``) into ``(lo, hi)``.

    Pure string arithmetic — no regex, no eval on caller input. Returns ``None``
    for anything unparseable so the gate can fail OPEN (never demote on a token it
    cannot read). Ported from the shipped mirror as part of the facet gate; DORMANT
    on the Theia component corpus (no component carries facet dicts), but kept
    faithful so the semantic-parity drift test holds and the S3-S5 tool retrofits
    have the primitive ready.
    """
    s = str(token).strip()
    if not s:
        return None
    try:
        if s.endswith("+"):
            return (int(s[:-1]), float("inf"))
        if "-" in s:
            lo, hi = s.split("-", 1)
            return (int(lo), int(hi))
        n = int(s)
        return (n, n)
    except (ValueError, TypeError):
        return None


def facet_matches(facet: dict, constraints: dict) -> bool:
    """Does one structured facet hold under the caller's *constraints*?

    The single facet-matching predicate (one source of truth, not one copy per
    reader). A facet is an AND of conditions; it matches only when the constraints
    confirm *every* key: ``team_size`` by numeric range overlap, every other key by
    categorical exact match (case/whitespace-normalised, never substring). Pure
    comparison — no ``eval``/regex on caller input; an unspecified or unreadable
    key yields ``False`` (fail open, never demote on unconfirmed input). Ported
    from the shipped mirror; DORMANT on the Theia component corpus (facet gate
    ready for S3-S5).
    """
    if not isinstance(facet, dict) or not facet:
        return False
    for key, fval in facet.items():
        cval = constraints.get(key)
        if cval is None:
            return False
        if key == "team_size":
            fr, cr = _parse_team_range(fval), _parse_team_range(cval)
            if fr is None or cr is None:
                return False
            if not (fr[0] <= cr[1] and cr[0] <= fr[1]):
                return False
        elif str(cval).strip().lower() != str(fval).strip().lower():
            return False
    return True


def split_conditions(items: list | None) -> tuple[list[str], list[dict]]:
    """Partition a ``use_when``/``avoid_when`` list into its two kinds.

    These lists mix free-text condition strings (for LLM recognition) and
    structured facet dicts (for deterministic gating). Any reader dispatches on
    element type through this one helper. Single pass; tolerates ``None``. Returns
    ``(text_conditions, facet_constraints)``. Ported from the shipped mirror; on
    the Theia component corpus the facet half is always empty (DORMANT).
    """
    texts: list[str] = []
    facets: list[dict] = []
    for item in items or []:
        (facets if isinstance(item, dict) else texts).append(item)
    return texts, facets


def is_gated(node: dict, constraints: dict) -> bool:
    """Is *node* gated by its OWN ``avoid_when`` facets under *constraints*?

    Reasoning over the node's own field, not a hardcoded detector. Ported from the
    shipped mirror as the deterministic facet gate; DORMANT on the Theia component
    corpus (no component carries an ``avoid_when`` facet dict), so it always returns
    ``False`` here. The live constraint gate on Theia is
    :meth:`KnowledgeLoader.filter_by_constraints`.
    """
    if not constraints:
        return False
    _, facets = split_conditions(node.get("avoid_when"))
    return any(facet_matches(f, constraints) for f in facets)


@dataclass
class _NamedIndex:
    """Descriptor for ONE signal-index corpus the parameterized engine serves.

    The three behavioural axes the council named — (index source, signal field,
    edge field) — are ``node_index`` / ``signal_field`` / ``edge_field``.
    ``id_field`` labels the public view's id-list column for THIS corpus
    (``component_ids`` vs ``system_ids``); it rides with the index source as a
    presentation facet, NOT a fourth behavioural axis — the ceilings, floor, state
    vocabulary, ranking and ``_signal_id`` are identical across corpora, which is
    exactly what the drift test asserts. ``name`` identifies the corpus for the
    cross-corpus-leakage guard. ``signal_index`` (signal_id -> entry) is populated
    by :meth:`_SignalEngine._build_signal_index`.
    """

    name: str
    node_index: dict[str, dict]
    signal_field: str
    edge_field: str
    id_field: str
    signal_index: dict[str, dict] = field(default_factory=dict)


class _SignalEngine:
    """The Shape-C signal-index retrieval engine — inherited by BOTH loaders and
    PARAMETERIZED over a :class:`_NamedIndex` so one copy serves every corpus.

    :class:`KnowledgeLoader` (JSON) and ``GraphKnowledgeLoader`` (Kuzu, via
    subclassing) build ``self._component_index`` in ``__init__`` and expose the
    S1-wired zero-arg public bindings that delegate here. Every primitive below
    reads only its ``_NamedIndex`` argument, so there is exactly ONE copy of the
    engine — no duplicate engine code across the two loaders, and none across the
    component index and S5's future design_systems index.
    """

    # ------------------------------------------------------------------
    # Index build (called from the loader's __init__, once per _NamedIndex)
    # ------------------------------------------------------------------

    def _build_signal_index(self, index: _NamedIndex) -> None:
        """Build ``index.signal_index`` from each node's ``index.signal_field``.

        Derived deterministically so the view is byte-reproducible (ids are
        content hashes; id-lists sorted). Fails CLOSED at load on a hash collision
        between two distinct signal texts — a 48-bit clash would silently merge
        two signals, so we refuse to serve a corrupted index rather than mask it.
        """
        index.signal_index = {}
        for node in index.node_index.values():
            nid = node["id"]
            for raw in node.get(index.signal_field, []):
                text = raw.strip()
                if not text:
                    continue
                sid = _signal_id(text)
                entry = index.signal_index.get(sid)
                if entry is None:
                    index.signal_index[sid] = {
                        "signal_id": sid,
                        "signal_text": text,
                        index.id_field: [nid],
                    }
                elif entry["signal_text"] != text:
                    raise ValueError(
                        f"signal_id collision {sid}: "
                        f"{text!r} vs {entry['signal_text']!r}"
                    )
                elif nid not in entry[index.id_field]:
                    entry[index.id_field].append(nid)
        for entry in index.signal_index.values():
            entry[index.id_field].sort()

    # ------------------------------------------------------------------
    # Node-id resolution (retrieval engine)
    # ------------------------------------------------------------------

    def _lookup_node(self, index: _NamedIndex, node_id: str) -> dict | None:
        """Resolve a node id to its stored dict, fail closed.

        Returns the real node dict or ``None`` — never a synthesised ``{id, name}``
        husk. The retrieval engine records a ``None`` as a typed ``dangling``
        reference in the envelope.
        """
        return index.node_index.get(node_id)

    # ------------------------------------------------------------------
    # Signal-index retrieval engine (problem-language -> node)
    # ------------------------------------------------------------------

    def _signal_index_view(self, index: _NamedIndex) -> list[dict]:
        """Return the deterministic, byte-reproducible signal index view.

        Each entry is ``{signal_id, signal_text, <index.id_field>}``; the LLM
        recognises a problem's signals against this view at runtime and passes the
        matched signal ids to :meth:`_hydrate`. Sorted by ``signal_id`` with sorted
        id-lists so two builds serialise identically.
        """
        return [
            {
                "signal_id": e["signal_id"],
                "signal_text": e["signal_text"],
                index.id_field: list(e[index.id_field]),
            }
            for e in sorted(index.signal_index.values(), key=lambda e: e["signal_id"])
        ]

    def _signal_ids_for(self, index: _NamedIndex, node_id: str) -> list[str]:
        """Return the signal ids of *node_id*'s OWN signals.

        The seed-from-node entry point: a tool that already HOLDS a known node id
        recovers that node's own signal ids from the built index — exactly the ids
        :meth:`_hydrate` recognises — and seeds retrieval with them, so the fan-out
        expands over the node's edge without a caller-supplied recognition step.
        Reads only ``index.signal_index`` (the one source of truth for text ->
        signal id), so the JSON and graph loaders derive the IDENTICAL seed; sorted
        for a deterministic, byte-reproducible order. An unknown or signal-less id
        yields ``[]`` (the caller then hydrates to a fail-closed ``no_match``),
        never a fabricated seed.
        """
        return sorted(
            sid for sid, entry in index.signal_index.items()
            if node_id in entry[index.id_field]
        )

    def _hydrate(
        self,
        index: _NamedIndex,
        matched_signal_ids: list[str],
        k: int = 10,
        fan_out: bool = True,
    ) -> RetrievalResult:
        """Hydrate matched signals into ranked nodes, in the four-state envelope.

        End-to-end entry point a harness drives given matched signal ids:

        * maps each signal id -> its owning node(s), tallying a direct vote per
          signal (a seed's weight = number of matched signals mapping to it);
        * one-hop fan-out over ``index.edge_field`` from the capped seed set,
          propagating each seed's weight to its neighbours (when ``fan_out``);
        * selects the top-``k`` via a size-k heap (``heapq.nlargest``, O(n log k))
          over a two-tier composite key: direct-vote tier (a directly-matched seed
          outranks every propagated-only neighbour), then the pre-fan-out
          direct-vote count within the seed tier (accumulated vote score for
          propagated-only neighbours), then node id ascending — deterministic
          throughout.

        Bounded by two ceilings: ``_SEED_CAP`` before fan-out and ``_TOPK_CAP``
        after. Votes are transparent integer counts, never a tuned score.
        """
        k = min(max(int(k), 1), _TOPK_CAP)

        # 1. Direct hydration: matched signal -> seed node(s), one vote each.
        unmatched: list[str] = []
        direct_votes: dict[str, int] = {}
        for sid in matched_signal_ids or []:
            entry = index.signal_index.get(sid)
            if entry is None:
                unmatched.append(sid)
                continue
            for nid in entry[index.id_field]:
                direct_votes[nid] = direct_votes.get(nid, 0) + 1

        # Empty leg: recognised signals that hydrate to nothing -> abstain.
        if not direct_votes:
            return RetrievalResult(
                state=NO_MATCH,
                unmatched_signals=sorted(set(unmatched)),
                reason="no matched signal maps to a corpus node",
            )

        # 2. Seed cap BEFORE fan-out: rank seeds (weight desc, id asc), bound.
        seeds = sorted(direct_votes.items(), key=lambda kv: (-kv[1], kv[0]))[:_SEED_CAP]

        # 3. Vote tally seeded from the capped seeds' direct votes.
        scores: dict[str, int] = dict(seeds)
        dangling: set[str] = set()

        # 4. One-hop fan-out: propagate each seed's weight to its edge neighbours.
        if fan_out:
            for nid, weight in seeds:
                seed_node = self._lookup_node(index, nid)
                if seed_node is None:
                    continue
                for neighbour in seed_node.get(index.edge_field, []):
                    if self._lookup_node(index, neighbour) is None:
                        dangling.add(neighbour)   # typed dangling, surfaced loud
                        continue
                    scores[neighbour] = scores.get(neighbour, 0) + weight

        # 5. Top-k via heap-top-k over a TWO-TIER composite key. Pre-order
        #    candidates by id asc so nlargest's stable decoration breaks full ties
        #    by node id ascending — the tertiary key. The key is (direct-vote tier,
        #    then the pre-fan-out direct-vote COUNT within the seed tier, else the
        #    accumulated vote score): a directly-matched seed (tier True) outranks
        #    every propagated-only neighbour (tier False) regardless of score, so no
        #    zero-direct-vote hub can evict a gold seed under the k cap; and seeds
        #    rank by direct-vote count, not accumulated score, so fan-out cannot
        #    re-order the seed tier.
        ordered = sorted(scores.items())
        top = heapq.nlargest(
            k,
            ordered,
            key=lambda kv: (
                kv[0] in direct_votes,
                direct_votes[kv[0]] if kv[0] in direct_votes else kv[1],
            ),
        )

        # 6. Hydrate the winners into the envelope; never emit a husk. Each node is
        #    deep-frozen at this boundary: a shallow ``{**node}`` would alias the
        #    singleton corpus's nested lists, so a caller mutating a returned node
        #    would corrupt the shared corpus. deep_freeze severs every reference and
        #    seals the copy, JSON-serialisable throughout.
        patterns: list[dict] = []
        votes: dict[str, int] = {}
        for nid, score in top:
            node = self._lookup_node(index, nid)
            if node is None:
                dangling.add(nid)
                continue
            direct = direct_votes.get(nid, 0)
            patterns.append(deep_freeze({
                **node,
                "retrieval": {
                    "score": score,
                    "direct_votes": direct,
                    "propagated_votes": score - direct,
                    "seed": nid in direct_votes,
                },
            }))
            votes[nid] = score

        # 7. Resolve the envelope state (fail closed).
        if not patterns:
            return RetrievalResult(
                state=DANGLING,
                dangling=sorted(dangling),
                unmatched_signals=sorted(set(unmatched)),
                reason="hydrated ids did not resolve to corpus nodes",
            )
        top_score = patterns[0]["retrieval"]["score"]
        if top_score >= _CONFIDENCE_FLOOR:
            state, reason = HIT, ""
        else:
            state = LOW_CONFIDENCE
            reason = f"best score {top_score} below confidence floor {_CONFIDENCE_FLOOR}"
        return RetrievalResult(
            state=state,
            patterns=patterns,
            votes=votes,
            dangling=sorted(dangling),
            unmatched_signals=sorted(set(unmatched)),
            reason=reason,
        )


# The two named indices the engine serves — the component signal index (S1) and the
# design_systems signal index (S5), each a _NamedIndex over the SAME primitives.
_COMPONENT_INDEX_NAME = "components"
_DESIGN_SYSTEMS_INDEX_NAME = "design_systems"


class KnowledgeLoader(_SignalEngine):
    """Loads and queries the Theia knowledge base (design systems,
    component patterns, accessibility standards, decision rules).

    All matching is structural / exact / data-driven.  No fuzzy keyword overlap.
    Inherits the Shape-C signal-index retrieval engine (:class:`_SignalEngine`).
    """

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def __init__(self, knowledge_dir: Path | None = None) -> None:
        self._dir = knowledge_dir or _KNOWLEDGE_DIR

        with open(self._dir / "design_systems.json", encoding="utf-8") as f:
            self._design_systems_data = json.load(f)

        with open(self._dir / "component_patterns.json", encoding="utf-8") as f:
            self._component_patterns_data = json.load(f)

        with open(self._dir / "accessibility_standards.json", encoding="utf-8") as f:
            self._accessibility_standards_data = json.load(f)

        with open(self._dir / "decision_rules.json", encoding="utf-8") as f:
            self._decision_rules_data = json.load(f)

        # Build convenience lists.
        self._design_systems: list[dict] = self._design_systems_data["systems"]
        self._component_patterns: list[dict] = self._component_patterns_data["patterns"]
        self._accessibility_standards: list[dict] = self._accessibility_standards_data["standards"]
        self._decision_rules: list[dict] = self._decision_rules_data["rules"]

        # Index: id -> dict
        self._design_system_index: dict[str, dict] = {
            s["id"]: s for s in self._design_systems
        }
        self._component_pattern_index: dict[str, dict] = {
            p["id"]: p for p in self._component_patterns
        }
        self._accessibility_index: dict[str, dict] = {
            a["id"]: a for a in self._accessibility_standards
        }
        self._rule_index: dict[str, dict] = {
            r["id"]: r for r in self._decision_rules
        }

        # Shape-C component signal index (from each component's ``signals`` field).
        # Built at load so a hash collision fails CLOSED here, not at first query.
        # The fan-out edge ``related_patterns`` is materialized in S2. The engine is
        # parameterized over this ``_NamedIndex`` seam so the design_systems index
        # below reuses every primitive (one engine, two corpora).
        self._component_index = _NamedIndex(
            name=_COMPONENT_INDEX_NAME,
            node_index=self._component_pattern_index,
            signal_field="signals",
            edge_field="related_patterns",
            id_field="component_ids",
        )
        self._build_signal_index(self._component_index)

        # Shape-C design_systems signal index (S5): the SECOND named index, over each
        # system's ``signals`` field with the LIVE ``related_systems`` fan-out edge.
        # It REUSES every _SignalEngine primitive the component index uses — ZERO
        # duplicated engine code — differing only in the three _NamedIndex axes
        # (source / signal_field / edge_field) plus the id-list label (``system_ids``).
        # The two id-spaces are disjoint (Theia's binding reservation), so no system
        # node can surface in a component result nor a component in a system result.
        self._systems_index = _NamedIndex(
            name=_DESIGN_SYSTEMS_INDEX_NAME,
            node_index=self._design_system_index,
            signal_field="signals",
            edge_field="related_systems",
            id_field="system_ids",
        )
        self._build_signal_index(self._systems_index)

    # ------------------------------------------------------------------
    # Signal-index retrieval engine — S1-wired public API (component index)
    # ------------------------------------------------------------------
    # Thin bindings of the parameterized :class:`_SignalEngine` primitives to the
    # component index. These are the ONLY index wired at S1; S5 adds parallel
    # bindings for the design_systems index. The binding is the parameterization
    # seam, not a duplicate source of truth — the engine logic lives once above.

    def get_signal_index(self) -> list[dict]:
        """Return the deterministic component signal-index view.

        Each entry is ``{signal_id, signal_text, component_ids}``, sorted by
        ``signal_id`` with sorted ``component_ids`` so it serialises identically
        on every call. The LLM recognises a problem's signals against this view
        and passes the matched ids to :meth:`hydrate`.
        """
        return self._signal_index_view(self._component_index)

    def signal_ids_for(self, component_id: str) -> list[str]:
        """Return the signal ids of *component_id*'s own signals (seed-from-node)."""
        return self._signal_ids_for(self._component_index, component_id)

    def hydrate(
        self,
        matched_signal_ids: list[str],
        k: int = 10,
        fan_out: bool = True,
    ) -> RetrievalResult:
        """Hydrate matched signal ids into ranked components (four-state envelope)."""
        return self._hydrate(self._component_index, matched_signal_ids, k, fan_out)

    # ------------------------------------------------------------------
    # Signal-index retrieval engine — S5-wired public API (design_systems index)
    # ------------------------------------------------------------------
    # The SECOND set of thin bindings, delegating the SAME parameterized
    # :class:`_SignalEngine` primitives to the design_systems index. Parallel to the
    # component bindings above — the binding is the parameterization seam, not a
    # duplicate source of truth (the engine logic lives once). plan_design_system
    # drives get_system_signal_index (the LLM's recognition view) -> hydrate_systems
    # (retrieval + the live ``related_systems`` fan-out).

    def get_system_signal_index(self) -> list[dict]:
        """Return the deterministic design_systems signal-index view.

        Each entry is ``{signal_id, signal_text, system_ids}``, sorted by
        ``signal_id`` with sorted ``system_ids`` so it serialises identically on
        every call. The LLM recognises a product's signals against this view and
        passes the matched ids to :meth:`hydrate_systems`.
        """
        return self._signal_index_view(self._systems_index)

    def system_signal_ids_for(self, system_id: str) -> list[str]:
        """Return the signal ids of *system_id*'s own signals (seed-from-node)."""
        return self._signal_ids_for(self._systems_index, system_id)

    def hydrate_systems(
        self,
        matched_signal_ids: list[str],
        k: int = 10,
        fan_out: bool = True,
    ) -> RetrievalResult:
        """Hydrate matched signal ids into ranked design systems (four-state envelope)."""
        return self._hydrate(self._systems_index, matched_signal_ids, k, fan_out)

    # ------------------------------------------------------------------
    # Pure retrieval — design systems
    # ------------------------------------------------------------------

    def get_design_system(self, system_id: str) -> dict | None:
        """Get a design system by ID."""
        return self._design_system_index.get(system_id)

    def get_design_systems_by_category(self, category: str) -> list[dict]:
        """Get all design systems in a given category."""
        return [s for s in self._design_systems if s.get("category") == category]

    def list_design_system_categories(self) -> list[str]:
        """List all unique design system categories."""
        cats: set[str] = set()
        for s in self._design_systems:
            cat = s.get("category")
            if cat:
                cats.add(cat)
        return sorted(cats)

    # ------------------------------------------------------------------
    # Pure retrieval — component patterns
    # ------------------------------------------------------------------

    def get_component_pattern(self, pattern_id: str) -> dict | None:
        """Get a component pattern by ID."""
        return self._component_pattern_index.get(pattern_id)

    def get_components_by_category(self, category: str) -> list[dict]:
        """Get all component patterns in a given category."""
        return [p for p in self._component_patterns if p.get("category") == category]

    def list_component_categories(self) -> list[str]:
        """List all unique component pattern categories."""
        cats: set[str] = set()
        for p in self._component_patterns:
            cat = p.get("category")
            if cat:
                cats.add(cat)
        return sorted(cats)

    # ------------------------------------------------------------------
    # Pure retrieval — accessibility standards
    # ------------------------------------------------------------------

    def get_accessibility_criterion(self, criterion_id: str) -> dict | None:
        """Get an accessibility criterion by ID."""
        return self._accessibility_index.get(criterion_id)

    def get_criteria_by_level(self, level: str) -> list[dict]:
        """Get all accessibility criteria at a given level (A, AA, AAA)."""
        return [a for a in self._accessibility_standards if a.get("level") == level]

    def get_criteria_by_principle(self, principle: str) -> list[dict]:
        """Get all accessibility criteria for a given principle
        (perceivable, operable, understandable, robust)."""
        return [
            a for a in self._accessibility_standards
            if a.get("principle", "").lower() == principle.lower()
        ]

    # ------------------------------------------------------------------
    # Pure retrieval — decision rules
    # ------------------------------------------------------------------

    def get_rule(self, rule_id: str) -> dict | None:
        """Get a decision rule by ID."""
        return self._rule_index.get(rule_id)

    def get_rules_by_category(self, category: str) -> list[dict]:
        """Get all decision rules in a given category."""
        return [r for r in self._decision_rules if r.get("category") == category]

    # ------------------------------------------------------------------
    # Constraint filtering
    # ------------------------------------------------------------------

    def filter_by_constraints(
        self,
        rules: list[dict],
        constraints: dict,
    ) -> list[dict]:
        """Filter rules by constraints.

        Removes rules whose ``constraints.avoid_when`` conditions match the
        provided constraints.  Each key in *constraints* is checked against
        the rule's ``avoid_when`` text (case-insensitive substring match).

        Args:
            rules: List of rule dicts (each must have ``constraints``
                with an ``avoid_when`` key).
            constraints: Dict of constraint signals.  Values that are
                truthy strings are checked against each rule's avoid_when.

        Returns:
            List of rules that survived filtering (avoid_when did not match).
        """
        if not constraints:
            return list(rules)

        # Gather constraint values as lowercase strings for matching.
        constraint_signals: list[str] = []
        for value in constraints.values():
            if isinstance(value, str) and value.strip():
                constraint_signals.append(value.lower().strip())
            elif isinstance(value, bool) and value:
                pass  # boolean flags don't have text to match

        if not constraint_signals:
            return list(rules)

        surviving: list[dict] = []

        for rule in rules:
            avoid_when = rule.get("constraints", {}).get("avoid_when", "")
            if not avoid_when:
                surviving.append(rule)
                continue

            avoid_lower = avoid_when.lower()
            excluded = False
            for cs in constraint_signals:
                if cs in avoid_lower or avoid_lower in cs:
                    excluded = True
                    break

            if not excluded:
                surviving.append(rule)

        return surviving

    # ------------------------------------------------------------------
    # Compact index (for council awareness)
    # ------------------------------------------------------------------

    def get_compact_index(self) -> dict:
        """Return a lightweight summary of all knowledge for agent awareness.

        Includes category counts and IDs only, not full data.
        """
        # Design system categories
        ds_categories: dict[str, list[str]] = {}
        for s in self._design_systems:
            cat = s.get("category", "uncategorised")
            ds_categories.setdefault(cat, []).append(s["id"])

        # Component pattern categories
        cp_categories: dict[str, list[str]] = {}
        for p in self._component_patterns:
            cat = p.get("category", "uncategorised")
            cp_categories.setdefault(cat, []).append(p["id"])

        # Accessibility by level
        a11y_levels: dict[str, list[str]] = {}
        for a in self._accessibility_standards:
            level = a.get("level", "unknown")
            a11y_levels.setdefault(level, []).append(a["id"])

        # Decision rules by category
        rule_categories: dict[str, list[str]] = {}
        for r in self._decision_rules:
            cat = r.get("category", "uncategorised")
            rule_categories.setdefault(cat, []).append(r["id"])

        return {
            "design_systems": {
                "total": len(self._design_systems),
                "categories": {k: len(v) for k, v in ds_categories.items()},
                "ids": [s["id"] for s in self._design_systems],
            },
            "component_patterns": {
                "total": len(self._component_patterns),
                "categories": {k: len(v) for k, v in cp_categories.items()},
                "ids": [p["id"] for p in self._component_patterns],
            },
            "accessibility_standards": {
                "total": len(self._accessibility_standards),
                "levels": {k: len(v) for k, v in a11y_levels.items()},
                "ids": [a["id"] for a in self._accessibility_standards],
            },
            "decision_rules": {
                "total": len(self._decision_rules),
                "categories": {k: len(v) for k, v in rule_categories.items()},
                "ids": [r["id"] for r in self._decision_rules],
            },
        }
