# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""Authoring builder for theia-Gmetric-v1 (story-af407698, council 3e6eeeab).

FROZEN, blind, corpus-blind DESIGN-SELECTION retrieval benchmark for Theia.

Mirrors the SHIPPED mnemos-Gmetric-v1 shape (f1b39fbd-decision-4) by reading
F:/Repos/mnemos/tests/data/gmetric/ READ-ONLY -- it is NOT imported (firewall:
Theia artifacts import only theia.*, never mnemos.*/coeus.*/othrys.*).

This script is the PROVENANCE record of how the benchmark was authored. It emits
the byte-frozen artifacts and computes the method-independent denominators:

  * problems_blind_v1.json  -- the blind problems, their FROZEN verbatim query
    signals, and their gold component/rule ids + roles. THIS is the benchmark
    data; the grader reads it (not this script) and re-verifies its sha256.
  * gmetric_v1.json         -- the frozen metric spec: the concept/alias map
    (per-gold verdict E/B/A + acceptable corpus ids + structure), the THREE
    never-conflated denominators (content-coverage method-INDEPENDENT, matcher-
    reachable ceiling method-DEPENDENT split per leg, and the recall
    denominator), the score definition, the register/class strata, the answer-
    key content-hash, and the reproducibility hashes. The three LOCKED legs are
    written by set_locked_legs.py AFTER the baseline is read (never before).
  * freeze_manifest.json    -- the EXTERNAL trust root. Pins the sha256 of both
    frozen artifacts (problems_blind AND gmetric -- the scored answer key +
    recall denominator live in gmetric, so it MUST be pinned externally) plus
    the four loaded corpus files, PLUS a content-hash over the E-gold answer key
    (problem, canonical, sorted(acceptable_ids)). grade._verify_substrate reads
    its pins from HERE, never from gmetric_v1.json (pinning the scored key inside
    the file it certifies is circular trust, CWE-345).

Design authorities (do not re-litigate):
  * council 3e6eeeab (Theia design authority) + pre-story council e920f1f4.
  * e920f1f4-decision-1 -- the baseline method_fn is the deterministic UNION of
    the FOUR current Theia surfaces (match_structural_signals + audit_design
    _ANTI_PATTERNS + spec_component exact-id/_COMPONENT_ARCHETYPES +
    plan_design_system keywords leg), returning corpus ids in their own id-space;
    golds keyed per stratum to that id-space so no surface is strawmanned out.
    The composite lives in grade.rank_baseline (ONE grader, no fork).
  * d-6146f069 -- the paraphrase-only failure this must avoid: problems AND golds
    are recorded VERBATIM and byte-frozen; prose queries are authored BEFORE any
    grading and never tuned toward gold vocabulary after seeing results. (Token
    strata TK/SEED deliberately feed a component token AS the query -- that is the
    seed path under test, not a leak, so the leak-check skips them.)
  * m-0364c120 -- a retrieval miss is NOT a content gap. Content existence
    (E/B/A) is decided by DIRECT corpus check here; coverage is decided by the
    grader later. The two are never conflated. Theia's live probe: 216 of 263
    rule recommended/alternative refs DANGLE (193 present nowhere in the 240-node
    corpus) -- a reachability defect wearing a content-gap costume.
  * m-e8ccb163 -- never a single pooled mean. Every number is stratified by
    query-class, register, and structure (component category), and the finest
    split (class) is primary so a bimodal population cannot cancel into a null.

Firewall: imports nothing from othrys.*/coeus.*/mnemos.*. Reads only the on-disk
Theia corpus via a direct json.load (no live DB, no second-process open).
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
KDIR = Path(__file__).resolve().parents[3] / "src" / "theia" / "knowledge"
COMPONENTS_FILE = "component_patterns.json"
RULES_FILE = "decision_rules.json"
SYSTEMS_FILE = "design_systems.json"
A11Y_FILE = "accessibility_standards.json"
CORPUS_FILES = (COMPONENTS_FILE, RULES_FILE, SYSTEMS_FILE, A11Y_FILE)

# Corpus-freeze GENERATION selector (mirror mnemos build_gmetric_v1._VER). The
# benchmark DATA (problems, golds, verdicts) is generation-invariant; only the
# corpus it freezes against moves. Default "v1" is S0 provenance.
_VER = os.environ.get("THEIA_GMETRIC_VERSION", "v1")
_SUF = "" if _VER == "v1" else f"_{_VER}"

PROBLEMS_OUT = HERE / f"problems_blind_{_VER}.json"
GMETRIC_OUT = HERE / f"gmetric_{_VER}.json"
FREEZE_MANIFEST_OUT = HERE / f"freeze_manifest{_SUF}.json"

# Verdict codes (method-independent concept existence in the 240-node corpus).
E, B, A = "E", "B", "A"  # Exists standalone / Borderline embedded / Absent
# v4 leg re-calibration verdict (story-846210c3; council 905db0ec REVISE = EXCLUDE, not
# re-label). X = the concept EXISTS in the corpus (like E) but is EXCLUDED from the RECALL
# denominator: it is a decision-RULE id in an id-space the component-space engine
# (loader.hydrate returns component patterns, never a rule id) structurally cannot emit,
# so scoring it measured the id-space mismatch, not retrieval quality. X is NEVER
# re-labelled onto the rule's recommended_patterns: every RESOLVABLE recommended target
# is already an independent E-gold in the same problem (see the exclusion ledger), so a
# re-label would inflate the engine's covered@10 with zero new retrieval and break the
# 'move the denominator, not the retrieval' invariant. X moves ONLY the denominator.
X = "X"
_EXISTS = (E, X)  # content-existence verdicts (method-independent: the concept IS present)

# Versions predating the v4 rule-space re-calibration. Their frozen artifacts are retained
# byte-identical, so the exclusion never fires for them and their regeneration is identical.
_PRE_RECAL_VERSIONS = frozenset({"v1", "v2", "v3"})
_RECALIBRATE = _VER not in _PRE_RECAL_VERSIONS


def _is_rule_space_gold(g: dict, rule_ids: set, comp_ids: set) -> bool:
    """A source_rule gold whose acceptable ids are ALL decision-rule ids (no component).

    The 8 (P01-P08) rule-space golds a component-space engine structurally cannot cover:
    loader.hydrate emits component patterns, never a rule id. Deterministic and
    derivation-based -- decided from the gold's authored role + acc id-space, NEVER from
    any retrieval output (blindness)."""
    acc = set(g["acc"])
    return (g["verdict"] == E and g.get("role") == "source_rule"
            and bool(acc) and acc <= rule_ids and not (acc & comp_ids))


def _eff_verdict(g: dict, rule_ids: set, comp_ids: set) -> str:
    """The effective verdict: X for an excluded rule-space gold under re-calibration, else
    the authored verdict. ONE source of truth for 'which golds are scored' -- grade.py
    reads verdict==E, and the answer key + tally + reach_map all resolve through here."""
    return X if (_RECALIBRATE and _is_rule_space_gold(g, rule_ids, comp_ids)) else g["verdict"]

# ---------------------------------------------------------------------------
# THE BLIND BENCHMARK.
#
# register: "prose" (problem-language / rule-prose idiom) or "token" (corpus
#   component-id vocabulary). qclass is the FINER, primary stratum:
#     PA = prose, rule-prose-aligned      -> the CURRENT matcher CAN answer
#          (match_structural_signals substring-hits the rule's own signal)
#     PB = prose, problem-language (blind) -> the matcher misses; the real target
#     TK = token, component-id vocabulary  -> the spec_component exact-id seed path
#     SEED = token, rich-spec-vs-husk      -> known component_type: does
#            spec_component return the rich KB entry or an archetype/skeleton husk?
#     CE = canon-edge probe (any register) -> deliberately probes content coverage
#          (is there a first-class component at all?)
#
# query: the EXACT signal string(s) fed verbatim to the composite baseline. For
#   prose strata authored BEFORE grading and NEVER tuned toward gold vocabulary.
#   For token strata (TK/SEED) the query IS the component token under test.
#
# golds: each is one CONCEPT the problem needs. canonical names it; role is its
#   fit; verdict is decided by DIRECT corpus check (validated below); acc is the
#   acceptable corpus ids (component OR rule ids) that satisfy it. Only E golds
#   are scored; B and A are neutral (excluded from numerator AND denominator) but
#   recorded so content-coverage is measurable.
# ---------------------------------------------------------------------------

PROBLEMS: list[dict] = [
    # =============== PA: prose, rule-prose-aligned (matcher answerable) ===============
    {
        "id": "P01", "qclass": "PA", "register": "prose",
        "problem": "A product analytics dashboard that shows summary metric cards across the top and detailed data tables below.",
        "query": ["dashboard with metric cards and data tables"],
        "golds": [
            {"concept": "dashboard layout rule", "canonical": "rule_dashboard_layout", "role": "source_rule", "verdict": E, "acc": ["rule_dashboard_layout"]},
            {"concept": "responsive grid container", "canonical": "grid", "role": "primary_fit", "verdict": E, "acc": ["grid"]},
            {"concept": "summary metric card", "canonical": "stat_card", "role": "primary_fit", "verdict": E, "acc": ["stat_card"]},
            {"concept": "tabular data display", "canonical": "data_table", "role": "primary_fit", "verdict": E, "acc": ["data_table"]},
        ],
    },
    {
        "id": "P02", "qclass": "PA", "register": "prose",
        "problem": "A guided multi-step onboarding flow that walks a new user through setup one screen at a time.",
        "query": ["multi-step process or onboarding"],
        "golds": [
            {"concept": "wizard flow rule", "canonical": "rule_wizard_flow", "role": "source_rule", "verdict": E, "acc": ["rule_wizard_flow"]},
            {"concept": "step indicator", "canonical": "stepper", "role": "primary_fit", "verdict": E, "acc": ["stepper"]},
            {"concept": "inline form validation", "canonical": "form_validation", "role": "constraint_alternative", "verdict": E, "acc": ["form_validation"]},
            {"concept": "progress indicator", "canonical": "progress_bar", "role": "alternative", "verdict": E, "acc": ["progress_bar"]},
        ],
    },
    {
        "id": "P03", "qclass": "PA", "register": "prose",
        "problem": "A screen that must render more than a hundred rows of structured records at once.",
        "query": ["100+ rows of structured data"],
        "golds": [
            {"concept": "large dataset rule", "canonical": "rule_large_dataset", "role": "source_rule", "verdict": E, "acc": ["rule_large_dataset"]},
            {"concept": "tabular data display", "canonical": "data_table", "role": "primary_fit", "verdict": E, "acc": ["data_table"]},
            {"concept": "pagination control", "canonical": "pagination", "role": "constraint_alternative", "verdict": E, "acc": ["pagination"]},
        ],
    },
    {
        "id": "P04", "qclass": "PA", "register": "prose",
        "problem": "An action that requires the user to stop and make a decision before continuing.",
        "query": ["action requiring user decision"],
        "golds": [
            {"concept": "blocking action rule", "canonical": "rule_blocking_action", "role": "source_rule", "verdict": E, "acc": ["rule_blocking_action"]},
            {"concept": "modal overlay", "canonical": "modal", "role": "primary_fit", "verdict": E, "acc": ["modal"]},
            {"concept": "confirmation dialog", "canonical": "dialog", "role": "primary_fit", "verdict": E, "acc": ["dialog"]},
        ],
    },
    {
        "id": "P05", "qclass": "PA", "register": "prose",
        "problem": "A page or section that shows placeholder shapes while its content is still loading.",
        "query": ["initial page or section load"],
        "golds": [
            {"concept": "loading skeleton rule", "canonical": "rule_loading_skeleton", "role": "source_rule", "verdict": E, "acc": ["rule_loading_skeleton"]},
            {"concept": "skeleton placeholder", "canonical": "skeleton", "role": "primary_fit", "verdict": E, "acc": ["skeleton"]},
        ],
    },
    {
        "id": "P06", "qclass": "PA", "register": "prose",
        "problem": "A view whose whole purpose is to surface key performance indicators and metrics.",
        "query": ["KPI or metric display"],
        "golds": [
            {"concept": "metrics rule", "canonical": "rule_metrics", "role": "source_rule", "verdict": E, "acc": ["rule_metrics"]},
            {"concept": "metric card", "canonical": "stat_card", "role": "primary_fit", "verdict": E, "acc": ["stat_card"]},
            {"concept": "chart", "canonical": "data_chart", "role": "primary_fit", "verdict": E, "acc": ["data_chart"]},
        ],
    },
    {
        "id": "P07", "qclass": "PA", "register": "prose",
        "problem": "A navigation structure that is three or more levels deep.",
        "query": ["navigation with 3+ levels of depth"],
        "golds": [
            {"concept": "deep hierarchy rule", "canonical": "rule_deep_hierarchy", "role": "source_rule", "verdict": E, "acc": ["rule_deep_hierarchy"]},
            {"concept": "sidebar navigation", "canonical": "sidebar", "role": "primary_fit", "verdict": E, "acc": ["sidebar"]},
            {"concept": "tree navigation", "canonical": "tree_view", "role": "primary_fit", "verdict": E, "acc": ["tree_view"]},
            {"concept": "breadcrumb trail", "canonical": "breadcrumb", "role": "alternative", "verdict": E, "acc": ["breadcrumb"]},
        ],
    },
    {
        "id": "P08", "qclass": "PA", "register": "prose",
        "problem": "A state that today is signalled by colour alone (a red/green pill).",
        "query": ["status indicated by color alone"],
        "golds": [
            {"concept": "color-only anti-pattern rule", "canonical": "rule_color_only", "role": "source_rule", "verdict": E, "acc": ["rule_color_only"]},
            {"concept": "tooltip label to disambiguate", "canonical": "tooltip", "role": "constraint_alternative", "verdict": E, "acc": ["tooltip"]},
        ],
    },

    # =============== PB: prose, problem-language / blind (matcher misses) ===============
    {
        "id": "P09", "qclass": "PB", "register": "prose",
        "problem": "A network operations centre wall screen: a handful of live health numbers at a glance above a long scrolling table of the most recent alerts.",
        "query": ["We run a network operations centre; the main screen must show a handful of live health numbers at a glance above a long, scrolling table of the most recent alerts."],
        "golds": [
            {"concept": "metric card", "canonical": "stat_card", "role": "primary_fit", "verdict": E, "acc": ["stat_card"]},
            {"concept": "tabular data display", "canonical": "data_table", "role": "primary_fit", "verdict": E, "acc": ["data_table"]},
            {"concept": "responsive grid container", "canonical": "grid", "role": "alternative", "verdict": E, "acc": ["grid"]},
        ],
    },
    {
        "id": "P10", "qclass": "PB", "register": "prose",
        "problem": "Status pills that rely on red and green alone; colour-blind operators cannot tell them apart and need another cue.",
        "query": ["Our status pills currently rely on red and green alone; colour-blind operators can't tell them apart and we need another way to signal state."],
        "golds": [
            {"concept": "labelled badge", "canonical": "badge", "role": "primary_fit", "verdict": E, "acc": ["badge"]},
            {"concept": "text tag", "canonical": "tag", "role": "alternative", "verdict": E, "acc": ["tag"]},
            {"concept": "tooltip label", "canonical": "tooltip", "role": "constraint_alternative", "verdict": E, "acc": ["tooltip"]},
        ],
    },
    {
        "id": "P11", "qclass": "PB", "register": "prose",
        "problem": "When the confirmation pop-up is open, keyboard users can still tab into the page behind it; focus must stay inside until dismissed.",
        "query": ["When our confirmation pop-up is open, keyboard users can still tab into the page behind it; focus needs to stay inside the pop-up until they dismiss it."],
        "golds": [
            {"concept": "focus-trapping modal", "canonical": "modal", "role": "primary_fit", "verdict": E, "acc": ["modal"]},
            {"concept": "confirmation dialog", "canonical": "dialog", "role": "primary_fit", "verdict": E, "acc": ["dialog"]},
        ],
    },
    {
        "id": "P12", "qclass": "PB", "register": "prose",
        "problem": "A parking app where each screen shows a big arrangement of parking bays and tapping a bay opens its details.",
        "query": ["We're building a parking app; each screen shows a big arrangement of parking bays and tapping one bay opens its details."],
        "golds": [
            {"concept": "grid of tiles", "canonical": "grid", "role": "primary_fit", "verdict": E, "acc": ["grid"]},
            {"concept": "tile card", "canonical": "card", "role": "primary_fit", "verdict": E, "acc": ["card"]},
            {"concept": "responsive columns", "canonical": "responsive_columns", "role": "alternative", "verdict": E, "acc": ["responsive_columns"]},
        ],
    },
    {
        "id": "P13", "qclass": "PB", "register": "prose",
        "problem": "A settings page grown to about 47 on/off switches; users are lost scrolling through them.",
        "query": ["Our settings page has grown to about 47 on/off switches and users get lost scrolling through the whole list."],
        "golds": [
            {"concept": "toggle switch control", "canonical": "toggle_switch", "role": "primary_fit", "verdict": E, "acc": ["toggle_switch"]},
            {"concept": "collapsible grouping", "canonical": "accordion", "role": "constraint_alternative", "verdict": E, "acc": ["accordion"]},
        ],
    },
    {
        "id": "P14", "qclass": "PB", "register": "prose",
        "problem": "After the user clicks Export a report can take a minute to generate; show that it is working and announce when it is done.",
        "query": ["After the user clicks Export, a big report can take up to a minute to generate; we need to show it's working and tell them when it's finished."],
        "golds": [
            {"concept": "progress indicator", "canonical": "progress_bar", "role": "primary_fit", "verdict": E, "acc": ["progress_bar"]},
            {"concept": "completion toast", "canonical": "toast", "role": "primary_fit", "verdict": E, "acc": ["toast"]},
            {"concept": "spinner", "canonical": "spinner", "role": "alternative", "verdict": E, "acc": ["spinner"]},
        ],
    },
    {
        "id": "P15", "qclass": "PB", "register": "prose",
        "problem": "New accounts land on a blank projects screen and think the app is broken; guide them instead.",
        "query": ["New accounts see a blank projects screen and assume the app is broken; we want to guide them toward creating their first project instead."],
        "golds": [
            {"concept": "empty state", "canonical": "empty_state", "role": "primary_fit", "verdict": E, "acc": ["empty_state"]},
        ],
    },
    {
        "id": "P16", "qclass": "PB", "register": "prose",
        "problem": "Power users want to jump anywhere in the app by typing a few letters instead of clicking through menus.",
        "query": ["Power users want to jump anywhere in the app by typing a few letters instead of clicking through menus."],
        "golds": [
            {"concept": "command palette", "canonical": "command_palette", "role": "primary_fit", "verdict": E, "acc": ["command_palette"]},
            {"concept": "search input", "canonical": "search_input", "role": "alternative", "verdict": E, "acc": ["search_input"]},
            {"concept": "autocomplete", "canonical": "autocomplete", "role": "alternative", "verdict": E, "acc": ["autocomplete"]},
        ],
    },

    # =============== TK: token / component-id corpus vocabulary (spec_component seed path) ===============
    {
        "id": "P17", "qclass": "TK", "register": "token",
        "problem": "A sortable, paginated table of structured records.",
        "query": ["data-table"],
        "golds": [
            {"concept": "tabular data display", "canonical": "data_table", "role": "primary_fit", "verdict": E, "acc": ["data_table"]},
        ],
    },
    {
        "id": "P18", "qclass": "TK", "register": "token",
        "problem": "An expandable/collapsible view of nested, hierarchical data.",
        "query": ["tree_view"],
        "golds": [
            {"concept": "tree navigation", "canonical": "tree_view", "role": "primary_fit", "verdict": E, "acc": ["tree_view"]},
        ],
    },
    {
        "id": "P19", "qclass": "TK", "register": "token",
        "problem": "A keyboard-driven overlay to run commands by name.",
        "query": ["command-palette"],
        "golds": [
            {"concept": "command palette", "canonical": "command_palette", "role": "primary_fit", "verdict": E, "acc": ["command_palette"]},
        ],
    },
    {
        "id": "P20", "qclass": "TK", "register": "token",
        "problem": "A binary on/off control.",
        "query": ["toggle-switch"],
        "golds": [
            {"concept": "toggle switch control", "canonical": "toggle_switch", "role": "primary_fit", "verdict": E, "acc": ["toggle_switch"]},
        ],
    },
    {
        "id": "P21", "qclass": "TK", "register": "token",
        "problem": "A calendar control for choosing a date.",
        "query": ["date_picker"],
        "golds": [
            {"concept": "date picker", "canonical": "date_picker", "role": "primary_fit", "verdict": E, "acc": ["date_picker"]},
        ],
    },
    {
        "id": "P22", "qclass": "TK", "register": "token",
        "problem": "The zero-data placeholder for a list or table.",
        "query": ["empty-state"],
        "golds": [
            {"concept": "empty state", "canonical": "empty_state", "role": "primary_fit", "verdict": E, "acc": ["empty_state"]},
        ],
    },

    # =============== SEED: known component_type -> rich spec vs husk ===============
    {
        "id": "P23", "qclass": "SEED", "register": "token",
        "problem": "Spec the stepper component (present in the KB as a rich pattern).",
        "query": ["stepper"],
        "golds": [
            {"concept": "step indicator (rich KB spec)", "canonical": "stepper", "role": "primary_fit", "verdict": E, "acc": ["stepper"]},
        ],
    },
    {
        "id": "P24", "qclass": "SEED", "register": "token",
        "problem": "Spec the dropdown_menu component (present in the KB as a rich pattern).",
        "query": ["dropdown_menu"],
        "golds": [
            {"concept": "dropdown menu (rich KB spec)", "canonical": "dropdown_menu", "role": "primary_fit", "verdict": E, "acc": ["dropdown_menu"]},
        ],
    },
    {
        "id": "P25", "qclass": "SEED", "register": "token",
        "problem": "Spec a text input. The user names the archetype 'input'; the rich first-class pattern is text_input.",
        "query": ["input"],
        "golds": [
            {"concept": "text input field", "canonical": "text_input", "role": "primary_fit", "verdict": E, "acc": ["text_input"]},
        ],
    },
    {
        "id": "P26", "qclass": "SEED", "register": "token",
        "problem": "Spec the primary navigation. The user names the archetype 'navigation'; the rich first-class pattern is navbar.",
        "query": ["navigation"],
        "golds": [
            {"concept": "navigation bar", "canonical": "navbar", "role": "primary_fit", "verdict": E, "acc": ["navbar"]},
        ],
    },
    {
        "id": "P27", "qclass": "SEED", "register": "token",
        "problem": "Spec the modal component (present in the KB and also an archetype -- rich spec must win).",
        "query": ["modal"],
        "golds": [
            {"concept": "modal overlay (rich KB spec)", "canonical": "modal", "role": "primary_fit", "verdict": E, "acc": ["modal"]},
        ],
    },

    # =============== CE: canon-edge content-coverage probes (E/B/A) ===============
    {
        "id": "P28", "qclass": "CE", "register": "prose",
        "problem": "A small numeric indicator showing an unread count on top of an icon.",
        "query": ["A small numeric indicator showing an unread count on top of an icon."],
        "golds": [
            {"concept": "count badge", "canonical": "badge", "role": "primary_fit", "verdict": E, "acc": ["badge"]},
        ],
    },
    {
        "id": "P29", "qclass": "CE", "register": "prose",
        "problem": "A colour picker with a hue wheel and a hex input.",
        "query": ["A colour picker with a hue wheel and a hex input field."],
        "golds": [
            {"concept": "colour picker", "canonical": "color_picker", "role": "primary_fit", "verdict": E, "acc": ["color_picker"]},
        ],
    },
    {
        "id": "P30", "qclass": "CE", "register": "prose",
        "problem": "An interactive product tour with coach-mark bubbles that point at UI elements one at a time.",
        "query": ["An interactive product tour with coach-mark bubbles that point at interface elements one at a time."],
        "golds": [
            {"concept": "product tour / coach-mark overlay", "canonical": "product-tour-coachmark", "role": "primary_fit", "verdict": A, "acc": []},
        ],
    },
    {
        "id": "P31", "qclass": "CE", "register": "prose",
        "problem": "A draggable splitter between two panes that the user drags to resize them.",
        "query": ["A draggable splitter between two panes that the user drags to resize each side."],
        "golds": [
            {"concept": "resizable split-pane handle", "canonical": "resizable-splitter", "role": "primary_fit", "verdict": A, "acc": []},
        ],
    },
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_dump(obj) -> str:
    """Deterministic byte-stable JSON: sorted keys, fixed separators, trailing newline."""
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def answer_key_sha256(problems: list[dict], rule_ids: set, comp_ids: set) -> str:
    """Content-hash over the SCORED (effectively-E) answer key (Theia AC: 'a content-hashed
    answer key'; closes the mnemos B4 seam, f276f253-decision-1, which mnemos deferred to
    S1 but the Theia AC pulls into S0).

    Hashes the canonicalized (problem_id, canonical, sorted(acceptable_ids)) tuples of
    every effectively-E gold (excluded rule-space golds re-tagged X drop out, so the key
    is over the 50-gold recall set under v4). Byte-for-byte parity with
    grade.answer_key_sha256_from_gmetric, which reads the frozen gmetric's verdict==E rows.
    Widening an already-covered gold's acceptable_ids leaves the graded result_core
    unchanged, so the result-hash alone cannot see it; this hash trips on ANY
    acceptable_ids edit even when no score moves. Pinned in the freeze manifest and
    re-compared by grade._verify_substrate."""
    tuples = sorted(
        (p["id"], g["canonical"], tuple(sorted(g["acc"])))
        for p in problems for g in p["golds"] if _eff_verdict(g, rule_ids, comp_ids) == E
    )
    payload = json.dumps(tuples, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main() -> None:
    components = json.loads((KDIR / COMPONENTS_FILE).read_text(encoding="utf-8"))["patterns"]
    rules = json.loads((KDIR / RULES_FILE).read_text(encoding="utf-8"))["rules"]
    systems = json.loads((KDIR / SYSTEMS_FILE).read_text(encoding="utf-8"))["systems"]
    a11y = json.loads((KDIR / A11Y_FILE).read_text(encoding="utf-8"))["standards"]

    comp_ids = {p["id"] for p in components}
    comp_cat = {p["id"]: p.get("category", "uncategorised") for p in components}
    rule_ids = {r["id"] for r in rules}
    ds_ids = {s["id"] for s in systems}
    a11y_ids = {a["id"] for a in a11y}
    corpus_ids = comp_ids | rule_ids | ds_ids | a11y_ids  # the 240-node id-space

    # ---- method-DEPENDENT matcher-reachable ceiling, split per leg (its own meter) ----
    # LEG 1 (match_structural_signals): a component is rule-reachable iff some rule
    #   names it as a REAL recommended_pattern or alternative. Dangling refs (216 of
    #   263, 193 present nowhere) do NOT count -- they resolve to husk stubs, not the
    #   real component (loader.py:197). This is the ceiling that caps the PA/PB register.
    rule_wired_components: set[str] = set()
    for r in rules:
        for ref in list(r.get("recommended_patterns", [])) + list(r.get("alternatives", [])):
            if ref in comp_ids:
                rule_wired_components.add(ref)
    # LEG 3 (spec_component exact-id): EVERY real component id is resolvable by its own
    #   token, so the leg-3 corpus ceiling over component golds is total -- but only a
    #   token query triggers it (the TK/SEED register). Archetype-only aliases whose id
    #   is not a real component (input, navigation) resolve to a HUSK, not the real id.
    leg3_reachable_components = set(comp_ids)

    # ---- validate the authored benchmark ----
    # rule structural_signal universe -- PA queries must be verbatim members (their
    # provenance is the CORPUS, not authoring-to-match; the leak guard below therefore
    # exempts PA -- rule prose legitimately names the domain concept it recommends).
    rule_signals_all = {s for r in rules for s in r.get("structural_signals", [])}
    seen_pids: set[str] = set()
    errors: list[str] = []
    for prob in PROBLEMS:
        pid = prob["id"]
        if pid in seen_pids:
            errors.append(f"{pid}: duplicate problem id")
        seen_pids.add(pid)
        if not prob["query"] or not all(isinstance(q, str) and q.strip() for q in prob["query"]):
            errors.append(f"{pid}: empty/blank query signal")
        # PA provenance: every PA query string is a VERBATIM rule structural_signal
        # (copied from the corpus, not tuned) -- the 'matcher answers its own idiom'
        # test. Proven here so PA cannot be silently authored toward gold vocab.
        if prob["qclass"] == "PA":
            for q in prob["query"]:
                if q not in rule_signals_all:
                    errors.append(f"{pid}: PA query not a verbatim rule structural_signal: {q!r}")
        # d-6146f069 leak guard: no AUTHORED prose query (PB/CE -- problem-language I
        # write freely) may contain a gold id verbatim (post-hoc tuning toward gold
        # vocab). PA is corpus-provenance prose (exempt, asserted verbatim above);
        # TOKEN strata (TK/SEED) deliberately feed the component token AS the query.
        if prob["qclass"] in ("PB", "CE"):
            ql = " ".join(prob["query"]).lower()
            for g in prob["golds"]:
                cid = g["canonical"].lower()
                if cid in ql or cid.replace("_", " ") in ql or cid.replace("_", "-") in ql:
                    errors.append(f"{pid}: authored prose query leaks gold id '{g['canonical']}'")
        for g in prob["golds"]:
            v, acc = g["verdict"], g["acc"]
            if v == E:
                if not acc:
                    errors.append(f"{pid} '{g['canonical']}': E gold with empty acceptable ids")
                if g["canonical"] not in corpus_ids:
                    errors.append(f"{pid}: E canonical '{g['canonical']}' not a corpus id")
                for cid in acc:
                    if cid not in corpus_ids:
                        errors.append(f"{pid}: E acc id '{cid}' not in corpus")
            elif v == B:
                for cid in acc:
                    if cid not in corpus_ids:
                        errors.append(f"{pid}: B acc id '{cid}' not in corpus")
            elif v == A:
                # ABSENT: the concept has NO first-class corpus node. Pattern-id test,
                # not a text-grep test. A and B are both neutral (excluded from
                # numerator AND denominator), governing only the content-coverage tally.
                if acc:
                    errors.append(f"{pid} '{g['canonical']}': A gold must have empty acceptable ids")
                if g["canonical"] in corpus_ids:
                    errors.append(f"{pid}: A canonical '{g['canonical']}' unexpectedly IS a corpus id")
            else:
                errors.append(f"{pid}: bad verdict '{v}'")

    if errors:
        raise SystemExit("BENCHMARK VALIDATION FAILED:\n  " + "\n  ".join(errors))

    # ---- build the frozen concept/alias map + tallies (method-independent) ----
    reach_map: list[dict] = []
    tally = {E: 0, B: 0, A: 0, X: 0}
    e_gold_leg1_reachable = 0   # rule-wiring reachable (caps PA/PB)
    e_gold_leg3_reachable = 0   # spec_component token reachable (caps TK/SEED)
    e_gold_composite_reachable = 0
    for prob in PROBLEMS:
        for g in prob["golds"]:
            v = _eff_verdict(g, rule_ids, comp_ids)   # X re-tags an excluded rule-space gold
            tally[v] += 1
            if v in _EXISTS:
                structure = "; ".join(sorted({comp_cat[c] for c in g["acc"] if c in comp_ids})) or (
                    "decision_rule" if any(c in rule_ids for c in g["acc"]) else "__other__")
            elif v == B and g["acc"]:
                structure = "; ".join(sorted({comp_cat.get(c, "embedded") for c in g["acc"]})) + " (embedded)"
            else:
                structure = "__absent__"
            row = {
                "problem": prob["id"], "qclass": prob["qclass"], "register": prob["register"],
                "concept": g["concept"], "canonical": g["canonical"], "role": g["role"],
                "verdict": v, "acceptable_ids": g["acc"], "structure": structure,
            }
            if v in _EXISTS:
                leg1 = bool(set(g["acc"]) & (rule_wired_components | rule_ids))
                leg3 = bool(set(g["acc"]) & leg3_reachable_components)
                leg4 = bool(set(g["acc"]) & ds_ids)
                row["leg1_rule_reachable"] = leg1
                row["leg3_spec_component_reachable"] = leg3
                row["composite_reachable"] = leg1 or leg3 or leg4
                if v == E:   # ceiling counters are over the RECALL set (E only); X is excluded
                    e_gold_leg1_reachable += int(leg1)
                    e_gold_leg3_reachable += int(leg3)
                    e_gold_composite_reachable += int(leg1 or leg3 or leg4)
            reach_map.append(row)

    total_golds = sum(tally.values())
    reachable_denominator = tally[E]

    # ---- content coverage stratified by qclass (m-e8ccb163: never a pooled mean) ----
    # Content EXISTENCE is method-independent (m-0364c120): an excluded X gold is a real
    # corpus node, so it counts as content that EXISTS (E+X) even though it is out of the
    # RECALL denominator. Coverage is therefore v3-identical -- the corpus did not move.
    content_by_qclass: dict[str, dict] = {}
    for qc in ("PA", "PB", "TK", "SEED", "CE"):
        rows = [r for r in reach_map if r["qclass"] == qc]
        t = {k: sum(1 for r in rows if r["verdict"] == k) for k in (E, B, A, X)}
        tot = sum(t.values())
        entry = {"E": t[E], "B": t[B], "A": t[A], "total": tot,
                 "coverage_E_over_total": round((t[E] + t[X]) / tot, 4) if tot else 0.0}
        if _RECALIBRATE:   # X key present under re-calibration only; v1-v3 shape unchanged
            entry["X"] = t[X]
        content_by_qclass[qc] = entry
    mainstream = [r for r in reach_map if r["qclass"] in ("PA", "PB", "TK", "SEED")]
    ms_E = sum(1 for r in mainstream if r["verdict"] in _EXISTS)
    ms_tot = len(mainstream)
    absent_gaps = sorted({r["canonical"] for r in reach_map if r["verdict"] == A})
    borderline = sorted({r["canonical"] for r in reach_map if r["verdict"] == B})

    ak_sha = answer_key_sha256(PROBLEMS, rule_ids, comp_ids)

    # Content tally + definition: X is folded into content EXISTENCE (E+X) and appears as
    # its own key ONLY under re-calibration, so the v1/v2/v3 content section stays byte-
    # identical (X count is 0 there and its formula collapses to E/total).
    content_tally = {"E_exists": tally[E], "B_borderline": tally[B], "A_absent": tally[A]}
    if _RECALIBRATE:
        content_tally["X_excluded_from_recall"] = tally[X]
    content_def = (
        "Does the gold concept EXIST in the 240-node corpus, by DIRECT corpus "
        "check? E=standalone component/rule (or naming variant); "
        + ("X=exists (a standalone rule) but EXCLUDED from the RECALL denominator (v4 "
           "re-calibration) -- still content that EXISTS; " if _RECALIBRATE else "")
        + "B=embedded/borderline only; A=absent. Independent of any retrieval method "
        + ("(m-0364c120: a miss is not a content gap; content coverage counts E+X)."
           if _RECALIBRATE else "(m-0364c120: a miss is not a content gap).")
    )

    # ---- v4 re-calibration exclusion ledger: per-gold derivation chain + non-gaming
    #      evidence (rule_id -> recommended_patterns -> resolvable component -> already a
    #      scored E-gold in the same problem?). Emitted only under re-calibration, so the
    #      v1/v2/v3 gmetric shape is unchanged. Derivation-based, never from retrieval. ----
    exclusion_ledger = None
    if _RECALIBRATE:
        rules_by_id = {r["id"]: r for r in rules}
        e_canon_by_problem: dict[str, set] = {}
        for r in reach_map:
            if r["verdict"] == E:
                e_canon_by_problem.setdefault(r["problem"], set()).add(r["canonical"])
        ledger_golds: list[dict] = []
        content_gap_followups: list[str] = []
        for r in reach_map:
            if r["verdict"] != X:
                continue
            rid = r["acceptable_ids"][0]
            recs = list(rules_by_id.get(rid, {}).get("recommended_patterns", []))
            chain, resolvable = [], []
            for ref in recs:
                resolved = next((c for c in (ref, ref.replace("-", "_"), ref.replace("_", "-"))
                                 if c in comp_ids), None)
                already = bool(resolved and resolved in e_canon_by_problem.get(r["problem"], set()))
                chain.append({"recommended_pattern": ref, "resolves_to_component": resolved,
                              "already_scored_E_gold_in_same_problem": already})
                if resolved:
                    resolvable.append(resolved)
            if not resolvable:
                content_gap_followups.append(rid)
            ledger_golds.append({
                "problem": r["problem"], "rule_id": rid, "recommended_patterns": recs,
                "derivation": chain, "resolvable_targets": sorted(resolvable),
                "all_resolvable_targets_already_scored_golds": (
                    bool(resolvable) and all(c["already_scored_E_gold_in_same_problem"]
                                             for c in chain if c["resolves_to_component"])),
            })
        exclusion_ledger = {
            "story": "story-846210c3",
            "mechanism": "EXCLUDE from the recall denominator (verdict X); NOT re-label",
            "council": "905db0ec REVISE (EXCLUDE) over the story's original RE-LABEL",
            "reason": ("The excluded golds are decision-rule ids; the component-space engine "
                       "(loader.hydrate returns component patterns, never a rule id) structurally "
                       "covers 0 of them, while the retired matcher's rule-id leg covered all of "
                       "them, so scoring them measured the id-space mismatch, not retrieval."),
            "recall_denominator_before": tally[E] + tally[X],
            "recall_denominator_after": tally[E],
            "excluded_count": tally[X],
            "non_gaming_evidence": ("Every RESOLVABLE recommended_pattern of an excluded rule is "
                                    "ALREADY an independent E-gold in the same problem, so a "
                                    "re-label adds ZERO new retrieval to the engine's covered set "
                                    "while inflating covered@10 -- the reason EXCLUDE was chosen. "
                                    "The numerator is unchanged; only the denominator moves."),
            "blind_data_note": ("problems_blind records the AUTHORED content-existence verdict (E); "
                                "this metric re-tags them X for RECALL scoring only -- the concept "
                                "still EXISTS (m-0364c120)."),
            "content_gap_followups": content_gap_followups,
            "content_gap_note": ("rule_color_only (P08): all three recommended_patterns "
                                 "(badge_with_label, icon_status, text_label) dangle -- a genuine "
                                 "content gap, RECORDED as an authoring follow-up, no component invented."),
            "golds": ledger_golds,
        }

    # ---- blind problems artifact (byte-frozen benchmark DATA) ----
    problems_blind = {
        "spec_id": "theia-Gmetric-v1",
        "story": "story-af407698",
        "what": ("Blind, corpus-blind DESIGN-SELECTION problems. Each carries its FROZEN "
                 "verbatim query signal(s) fed to the composite baseline and its gold "
                 "component/rule ids. Recorded verbatim and byte-frozen (d-6146f069): the "
                 "grader reads THIS file and feeds 'query' to the method unchanged. Prose "
                 "strata (PA/PB/CE) are authored before grading and never tuned toward gold "
                 "vocabulary; token strata (TK/SEED) feed the component token AS the query."),
        "n_problems": len(PROBLEMS),
        "registers": sorted({p["register"] for p in PROBLEMS}),
        "qclasses": sorted({p["qclass"] for p in PROBLEMS}),
        "problems": [
            {"id": p["id"], "qclass": p["qclass"], "register": p["register"],
             "problem": p["problem"], "query": p["query"],
             "golds": [{"concept": g["concept"], "canonical": g["canonical"],
                        "role": g["role"], "verdict": g["verdict"]} for g in p["golds"]]}
            for p in PROBLEMS
        ],
    }
    PROBLEMS_OUT.write_text(canonical_dump(problems_blind), encoding="utf-8")

    # ---- frozen metric spec ----
    gmetric = {
        "spec_id": "theia-Gmetric-v1",
        "story": "story-af407698",
        "title": "Frozen blind design-selection retrieval scorecard for the Theia retrofit",
        "authored_by": "Themis",
        "status": "FROZEN",
        "design_authority": ["council 3e6eeeab (Theia)", "pre-story council e920f1f4 (decisions 1-7)",
                             "mirrors mnemos-Gmetric-v1 shape (f1b39fbd-decision-4)"],
        "one_line": ("Concept-level recall@10 over a method-independent set of E-golds; the later "
                     "retrieval engine must beat the CURRENT four-surface exact-substring matcher on "
                     "the same set. Every number stratified by query-class, register, and structure."),
        "1_grader": {
            "type": "curated_concept_map",
            "decision": "Frozen deterministic concept/alias lookup, NOT a live LLM judge.",
            "why": ("A frozen map is a pure function -> 'compute twice, same score' holds byte-exactly. "
                    "The map pre-encodes naming/mechanism variants so a correct alternate id still counts."),
            "rule": ("A gold is COVERED@k iff the method's rank-ordered top-k corpus ids for that "
                     "problem intersect ANY of that gold's acceptable_ids. Only E golds are scored; "
                     "B and A are neutral (excluded from numerator AND denominator)."),
            "baseline_method": ("grade.rank_baseline = the deterministic UNION of the four current Theia "
                                "surfaces (e920f1f4-decision-1): match_structural_signals (rule id + "
                                "recommended_patterns + alternatives, priority order) THEN spec_component "
                                "exact-id/_COMPONENT_ARCHETYPES THEN audit_design _ANTI_PATTERNS THEN "
                                "plan_design_system keywords leg; dedup first-seen. Returns corpus ids in "
                                "their own id-space; the two auxiliary legs (anti-pattern WCAG space, "
                                "keyword design-system space) run so they are not strawmanned OUT but "
                                "surface no component/rule id -- a measured reachability fact."),
            "verbatim_query_contract": ("The grader feeds problems_blind_v1.json 'query' to the composite "
                                        "unchanged. No paraphrase layer (d-6146f069)."),
        },
        "2_denominators": {
            "note": "THREE denominators, kept strictly distinct (m-0364c120). Never conflated.",
            "content_method_independent": {
                "definition": content_def,
                "tally": content_tally,
                "total_golds": total_golds,
                "content_coverage_E_over_total": round((tally[E] + tally[X]) / total_golds, 4) if total_golds else 0.0,
                "content_coverage_by_qclass": content_by_qclass,
                "pooled_number_warning": ("The pooled coverage mixes mainstream selection (PA/PB/TK/SEED) "
                                          "with deliberately-probed canon-edge cases (CE). Read the "
                                          "by_qclass split, not the pool (m-e8ccb163)."),
            },
            "matcher_reachable_ceiling_method_dependent": {
                "definition": ("Ceiling on what the CURRENT four-surface matcher could ever retrieve, by "
                               "corpus WIRING (query-independent). Split per leg because each leg caps a "
                               "different register."),
                "leg1_match_structural_signals": {
                    "definition": ("A component is rule-reachable iff some rule names it as a REAL "
                                   "recommended_pattern or alternative. Dangling refs resolve to husk "
                                   "stubs (loader.py:197), NOT the real component, and do not count. This "
                                   "caps the PA/PB (rule-prose) register."),
                    "corpus_components_rule_wired": len(rule_wired_components),
                    "corpus_component_count": len(comp_ids),
                    "corpus_rule_refs_total": sum(len(r.get("recommended_patterns", [])) + len(r.get("alternatives", [])) for r in rules),
                    "corpus_rule_refs_dangling_note": ("216 of 263 distinct rec/alt refs dangle (193 present "
                                                       "nowhere in the 240-node corpus) -- the m-0364c120 "
                                                       "reachability defect in a content-gap costume."),
                    "benchmark_E_golds_leg1_reachable": e_gold_leg1_reachable,
                },
                "leg3_spec_component": {
                    "definition": ("Every real component id is resolvable by spec_component via its own "
                                   "exact-id token (hyphen/underscore normalised), so the corpus ceiling "
                                   "over component golds is total -- but ONLY a token query triggers it "
                                   "(the TK/SEED register). Archetype-only aliases whose id is not a real "
                                   "component (input, navigation) resolve to a HUSK, not the real id."),
                    "benchmark_E_golds_leg3_reachable": e_gold_leg3_reachable,
                },
                "composite": {
                    "benchmark_E_golds_composite_reachable": e_gold_composite_reachable,
                    "benchmark_E_golds_total": reachable_denominator,
                    "composite_reachable_ceiling": round(e_gold_composite_reachable / reachable_denominator, 4) if reachable_denominator else 0.0,
                    "reading": ("The composite wiring ceiling is high (content + wiring both present), yet "
                                "recall@10 on the BLIND problem-language queries is low -- the gap is a "
                                "REACHABILITY gap (register mismatch: prose queries do not trigger the "
                                "exact-substring rule leg nor the exact-token spec_component leg), NOT a "
                                "content gap. Answered by measurement, not assumed (m-0364c120)."),
                },
            },
            "reachable_set_for_recall": {
                "definition": "recall denominator = E-golds only (B and A excluded, scored neutral).",
                "FROZEN_reachable_denominator": reachable_denominator,
            },
        },
        "3_score": {
            "metric": "concept_recall_at_k",
            "formula": "recall@k = (# E-golds whose acceptable_ids intersect the method's top-k) / E-golds",
            "primary_cutoff_k": 10,
            "secondary_cutoff_k": 5,
            "method_output_contract": ("Per problem the method emits a rank-ordered list of DISTINCT corpus "
                                       "ids. BASELINE = grade.rank_baseline (the four-surface UNION). AFTER "
                                       "= the ported retrieval engine over the SAME frozen queries + corpus."),
            "answer_key_sha256": ak_sha,
            "answer_key_definition": ("sha256 over sorted (problem_id, canonical, sorted(acceptable_ids)) "
                                      "tuples of every E-gold. Pinned in the freeze manifest; grade "
                                      "re-compares it so an acceptable_ids widening trips drift even when "
                                      "the graded result is unchanged (closes the mnemos B4 seam at S0)."),
        },
        "4_stratification": {
            "rule": "m-e8ccb163: never a single pooled mean. The finest split (qclass) is primary.",
            "dimensions": {
                "qclass": {"PA": "prose, rule-prose-aligned (matcher answerable)",
                           "PB": "prose, problem-language / blind (matcher misses)",
                           "TK": "token, component-id vocabulary (spec_component seed path)",
                           "SEED": "token, known component_type -> rich KB spec vs archetype/skeleton husk",
                           "CE": "canon-edge content-coverage probe"},
                "register": ["prose", "token"],
                "structure": "component category of each E-gold's acceptable ids (or decision_rule)",
            },
        },
        "5_reproducibility": {
            "problems_blind": {"file": PROBLEMS_OUT.name, "sha256": sha(PROBLEMS_OUT)},
            "corpus_snapshot_sha256": {f: sha(KDIR / f) for f in CORPUS_FILES},
            "corpus_component_count": len(comp_ids),
            "corpus_rule_count": len(rule_ids),
            "corpus_system_count": len(ds_ids),
            "corpus_a11y_count": len(a11y_ids),
            "corpus_node_count": len(corpus_ids),
            "n_problems": len(PROBLEMS),
            "cutoffs": {"primary_k": 10, "secondary_k": 5},
            "recompute_contract": ("Given the pinned problems_blind hash, the corpus hashes, k, and this "
                                   "map, recall@k is a pure function of a method's ranked output -> "
                                   "identical on every recompute. Any hash change INVALIDATES the metric "
                                   "and forces a re-freeze (v1->v2)."),
        },
        "6_locked_legs": {
            "status": "SET_AFTER_BASELINE -> locked_legs_v1.json",
            "note": ("The three legs are calibrated from and frozen in locked_legs_v1.json AFTER the "
                     "baseline is read (never before)."),
        },
        "Q_answer_measured": {
            "question": "Is the ~240-node Theia corpus a CONTENT gap or a REACHABILITY gap for design selection?",
            "verdict": ("REACHABILITY gap. Mainstream design-selection content is present; the matcher "
                        "misses it because problem-language queries do not trigger the exact-substring "
                        "rule leg nor the exact-token spec_component leg. Measured, assumed neither way "
                        "(m-0364c120)."),
            "mainstream_PA_PB_TK_SEED": {"E": ms_E, "total": ms_tot,
                                         "coverage": round(ms_E / ms_tot, 4) if ms_tot else 0.0,
                                         "reading": "mainstream gold concepts exist in the corpus."},
            "canon_edge_CE": content_by_qclass["CE"],
            "genuine_content_gaps_ABSENT": absent_gaps,
            "borderline_embedded_only": borderline,
            "scope_note": ("Per AC these gaps are RECORDED, not filled. Authoring new components/rules is "
                           "out of scope for S0 (content gap deferred -- measured, not filled)."),
        },
        "reachable_set_map": reach_map,
    }
    if exclusion_ledger is not None:
        gmetric["recalibration_v4_exclusion_ledger"] = exclusion_ledger
    GMETRIC_OUT.write_text(canonical_dump(gmetric), encoding="utf-8")

    # ---- external tamper-evident freeze manifest (LAST: both artifacts now exist) ----
    freeze_manifest = {
        "spec_id": "theia-Gmetric-v1-freeze-manifest",
        "story": "story-af407698",
        "what": ("External trust root for the frozen metric. Pins the sha256 of both frozen artifacts "
                 "(the blind problems AND the scored concept/alias map + recall denominator in "
                 "gmetric_v1.json) plus the four loaded corpus snapshots, plus a content-hash over the "
                 "E-gold answer key. grade._verify_substrate reads pins ONLY from HERE, never from "
                 "gmetric_v1.json (which it grades against -- that would be circular trust, CWE-345). "
                 "Regenerating this manifest is the only way to move a pin, a visible reviewable change."),
        "hash_algo": "sha256",
        "answer_key_sha256": ak_sha,
        "pins": {
            PROBLEMS_OUT.name: sha(PROBLEMS_OUT),
            GMETRIC_OUT.name: sha(GMETRIC_OUT),
            **{f: sha(KDIR / f) for f in CORPUS_FILES},
        },
    }
    FREEZE_MANIFEST_OUT.write_text(canonical_dump(freeze_manifest), encoding="utf-8")

    # ---- console ----
    print(f"=== theia-Gmetric authored ({_VER}{'  RE-CALIBRATED (X-excluded)' if _RECALIBRATE else ''}) ===")
    print(f"problems: {len(PROBLEMS)}  golds: {total_golds}  (E={tally[E]} X={tally[X]} B={tally[B]} A={tally[A]})")
    print(f"content coverage ((E+X)/total): {tally[E]+tally[X]}/{total_golds} = {(tally[E]+tally[X])/total_golds:.4f}")
    print(f"reachable denominator (E-golds, recall-scored): {reachable_denominator}")
    print(f"leg1 rule-wiring reachable E-golds: {e_gold_leg1_reachable}/{reachable_denominator}")
    print(f"leg3 spec_component reachable E-golds: {e_gold_leg3_reachable}/{reachable_denominator}")
    print(f"composite reachable ceiling: {e_gold_composite_reachable}/{reachable_denominator} "
          f"= {e_gold_composite_reachable/reachable_denominator:.4f}")
    print(f"corpus: {len(comp_ids)} components ({len(rule_wired_components)} rule-wired), "
          f"{len(rule_ids)} rules, {len(ds_ids)} systems, {len(a11y_ids)} a11y = {len(corpus_ids)} nodes")
    print("by qclass:")
    for qc in ("PA", "PB", "TK", "SEED", "CE"):
        n = sum(1 for p in PROBLEMS if p["qclass"] == qc)
        eg = sum(1 for r in reach_map if r["qclass"] == qc and r["verdict"] == E)
        print(f"  {qc:4}: {n} problems, {eg} E-golds")
    print(f"answer_key_sha256={ak_sha[:16]}...")
    print(f"wrote {PROBLEMS_OUT.name} sha256={sha(PROBLEMS_OUT)[:16]}...")
    print(f"wrote {GMETRIC_OUT.name} sha256={sha(GMETRIC_OUT)[:16]}...")
    print(f"wrote {FREEZE_MANIFEST_OUT.name} pinning {len(freeze_manifest['pins'])} files "
          f"sha256={sha(FREEZE_MANIFEST_OUT)[:16]}...")


if __name__ == "__main__":
    main()
