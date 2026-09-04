# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""spec_component wired onto the Shape-C engine (SEED-FROM-NODE) — story-57031f25
(council 3e6eeeab).

The SECOND Theia concern tool retrofitted onto the shared engine (audit_design is the
S3 sibling). spec_component resolves ``component_type`` to a corpus id and SEEDS
retrieval from that component's OWN signals (``kb.signal_ids_for`` -> one
``kb.hydrate`` whose one-hop fan-out expands over ``related_patterns``), returning the
resolved component's OWN corpus fields — anatomy/states/variants/
accessibility_requirements/common_mistakes/responsive_behavior/design_tokens_needed —
through the four-state fail-closed envelope. A non-resolving type retrieves the
nearest component from the caller's recognised ``matched_signal_ids`` (flagged
``nearest``); a true miss fails closed, NEVER the ['container','content'] husk.

This is the one home for the rebuilt tool's proofs. It carries:

* the RED-first NORTH-STAR probe — a known type ('navbar') returns its OWN 6
  accessibility_requirements (the pinned pre-edit output dropped them: role='' /
  wcag_requirements=[]) plus its variants + common_mistakes;
* the accessibility-requirements read FIX (component.get('accessibility') is None on
  66/66; the flags come from accessibility_requirements) — the "a11y read reverted ->
  RED" mutation, encoded;
* the SEED-FROM-NODE proof — every one of the 66 components self-resolves at HIT to
  its own rich spec — and the "seed from a foreign node -> RED" mutation;
* the nearest path (agent-supplied matched_signal_ids on a non-resolving type);
* the fail-closed envelope states — the "husk branch restored -> RED" mutation;
* BAR-2 — the SEED-class before/after delta against the pinned pre-edit husk;
* determinism (incl. a fresh loader), the caller-boundary ceilings, the deleted
  _COMPONENT_ARCHETYPES island (grep 0 code refs) with the grader's baseline left
  byte-identical, and the deep-freeze that keeps the singleton corpus uncorrupted.

Firewall: imports only theia.* . Never opens the live Othrys DB.
"""

from __future__ import annotations

import ast
import inspect
import json
import sys
from pathlib import Path

import pytest

import theia.tools._shared as _shared
from theia.knowledge.loader import DANGLING, HIT, NO_MATCH, KnowledgeLoader, _signal_id
from theia.tools._shared import _MAX_DESCRIPTION_LEN, _MAX_MATCHED_SIGNALS
from theia.tools.spec_component import spec_component

_SPEC_SRC = Path(inspect.getsourcefile(spec_component))
_PIN = json.loads(
    (Path(__file__).parent / "data" / "baseline_spec_component_pinned.json").read_text(encoding="utf-8")
)

# The v3 SEED stratum's five component types + their gold components (the token the
# problem feeds -> the component it names). 'input'/'navigation' are the archetype
# huskies: they do NOT resolve to a corpus id (text_input/navbar do), so they land
# through the nearest path.
_SEED_EXACT = {"stepper": "stepper", "dropdown_menu": "dropdown_menu", "modal": "modal"}
_SEED_NEAREST = {"input": "text_input", "navigation": "navbar"}


@pytest.fixture()
def kb() -> KnowledgeLoader:
    _shared._knowledge = None
    return _shared.get_knowledge(conn=None)


def _fresh_call(**kwargs) -> dict:
    _shared._knowledge = None
    return spec_component(**kwargs)


# ===================================================================
# RED-FIRST — the NORTH STAR: the navbar HIT surfaces its OWN a11y
# ===================================================================

class TestRedFirstNorthStar:
    def test_navbar_hit_surfaces_its_own_six_a11y_requirements(self, kb) -> None:
        """The pinned pre-edit navbar HIT dropped the component's own
        accessibility_requirements (role='' / wcag_requirements=[] — the a11y_role +
        keyword_map bug). After the retrofit the same navbar HIT returns navbar's OWN
        6 accessibility_requirements, plus its variants + common_mistakes."""
        before = _PIN["cases"]["navbar_HIT"]
        assert before["accessibility_role"] == ""
        assert before["wcag_requirements_count"] == 0
        assert before["has_accessibility_requirements_key"] is False
        assert before["own_accessibility_requirements_count_in_corpus"] == 6

        res = spec_component(component_type="navbar")
        assert res["retrieval_state"] == HIT
        assert res["from_knowledge_base"] is True
        assert res["nearest"] is False
        assert res["component_id"] == "navbar"
        assert len(res["accessibility_requirements"]) == 6
        assert res["accessibility_requirements"] == kb.get_component_pattern("navbar")["accessibility_requirements"]
        assert len(res["variants"]) == 4
        assert len(res["common_mistakes"]) == 5

    def test_a11y_read_is_the_real_field_not_the_dead_one(self, kb) -> None:
        """The populated a11y proves the accessibility_requirements read fix. The legacy
        read kb_pattern.get('a11y_role') (0/66 components carry it) + a hardcoded
        keyword_map; reverting the read to the dead 'accessibility' field would empty it
        (the RED mutant), while 'accessibility_requirements' populates it."""
        for cid in ("navbar", "modal", "stepper", "dropdown_menu"):
            comp = kb.get_component_pattern(cid)
            assert comp.get("a11y_role") is None        # the dead field the legacy read
            assert comp.get("accessibility") is None    # also absent
            assert comp["accessibility_requirements"]   # the real field
            res = spec_component(component_type=cid)
            assert res["accessibility_requirements"] == comp["accessibility_requirements"]

    def test_own_responsive_and_tokens_not_computed(self, kb) -> None:
        """responsive_behavior + design_tokens_needed come from the component's OWN
        corpus fields, not the legacy computed _RESPONSIVE_BREAKPOINTS dict / name-
        generated token list."""
        comp = kb.get_component_pattern("navbar")
        res = spec_component(component_type="navbar")
        assert res["responsive_behavior"] == comp["responsive_behavior"]
        assert res["design_tokens_needed"] == comp["design_tokens_needed"]
        # the legacy computed shapes are gone from the contract
        assert "design_tokens" not in res
        assert not any(isinstance(x, dict) for x in res["responsive_behavior"])


# ===================================================================
# SEED-FROM-NODE — resolve id -> own signals -> hydrate -> own spec
# ===================================================================

class TestSeedFromNode:
    def test_every_component_self_resolves_at_hit(self, kb) -> None:
        """END-TO-END over the whole corpus: every one of the 66 components, asked by
        its exact id, seeds from its OWN signals and hydrates to ITSELF at HIT with a
        populated own-fields spec — the retrofit works corpus-wide, not just navbar."""
        comps = kb._component_patterns
        assert len(comps) == 66
        for c in comps:
            res = spec_component(component_type=c["id"])
            assert res["retrieval_state"] == HIT, f"{c['id']} not HIT"
            assert res["component_id"] == c["id"], f"{c['id']} mis-resolved to {res['component_id']}"
            assert res["from_knowledge_base"] is True
            assert res["nearest"] is False
            assert res["accessibility_requirements"] == c["accessibility_requirements"]

    def test_hyphen_underscore_normalisation_preserved(self, kb) -> None:
        """The legacy exact + hyphen<->underscore resolution is kept: 'data-table'
        resolves to the 'data_table' corpus id."""
        res = spec_component(component_type="data-table")
        assert res["component_id"] == "data_table"
        assert res["retrieval_state"] == HIT

    def test_seed_from_foreign_node_is_red(self, kb, monkeypatch) -> None:
        """Mutation proof (seed from a foreign node -> RED): force signal_ids_for to
        return a DIFFERENT component's signals while asking for navbar, and the primary
        is no longer navbar. Binds the spec to the resolved component's OWN seed."""
        healthy = spec_component(component_type="navbar")
        assert healthy["component_id"] == "navbar"

        orig = kb.signal_ids_for
        monkeypatch.setattr(kb, "signal_ids_for", lambda cid: orig("modal"))
        monkeypatch.setattr(_shared, "_knowledge", kb)
        res = spec_component(component_type="navbar")
        assert res["component_id"] != "navbar"       # foreign seed -> wrong primary
        assert res["component_id"] == "modal"

    def test_related_components_are_the_fanout_edge(self, kb) -> None:
        """related_components is the deduped resolution of the primary's OWN
        related_patterns edge (the shared fan-out primitive) — every entry a real
        component, never a husk, never the primary itself."""
        res = spec_component(component_type="navbar")
        ids = [r["pattern_id"] for r in res["related_components"]]
        assert ids == sorted(set(ids), key=ids.index)       # deduped, order preserved
        for r in res["related_components"]:
            assert r["pattern_id"] != "navbar"
            assert kb.get_component_pattern(r["pattern_id"]) is not None
            assert r["pattern_name"]


# ===================================================================
# NEAREST — agent-supplied matched_signal_ids on a non-resolving type
# ===================================================================

class TestNearestPath:
    def test_nonresolving_type_with_signals_returns_nearest_rich(self, kb) -> None:
        """A non-resolving type ('parking-space-tile') with agent-supplied
        matched_signal_ids retrieves the nearest component's OWN rich fields, flagged
        nearest — recognize-then-retrieve, not an exact resolution."""
        sids = kb.signal_ids_for("text_input")
        res = spec_component(component_type="parking-space-tile", matched_signal_ids=sids)
        assert res["nearest"] is True
        assert res["from_knowledge_base"] is True
        assert res["component_id"] == "text_input"
        assert res["retrieval_state"] == HIT
        assert res["accessibility_requirements"] == kb.get_component_pattern("text_input")["accessibility_requirements"]

    def test_archetype_husk_slugs_now_reach_the_real_component(self, kb) -> None:
        """The two archetype huskies ('input'/'navigation') — which the legacy tool
        answered with a hardcoded archetype, never the real component — now reach the
        real text_input/navbar through the nearest path (agent recognises the slug ->
        the component's signals)."""
        for slug, real in _SEED_NEAREST.items():
            sids = kb.signal_ids_for(real)
            res = spec_component(component_type=slug, matched_signal_ids=sids)
            assert res["component_id"] == real
            assert res["nearest"] is True
            assert res["accessibility_requirements"] == kb.get_component_pattern(real)["accessibility_requirements"]

    def test_matched_signal_ids_ignored_on_a_resolving_type(self, kb) -> None:
        """A resolving type seeds from its OWN signals; caller-supplied
        matched_signal_ids are ignored (reduced attack surface — the seed is derived
        internally)."""
        foreign = kb.signal_ids_for("modal")
        res = spec_component(component_type="navbar", matched_signal_ids=foreign)
        assert res["component_id"] == "navbar"
        assert res["nearest"] is False


# ===================================================================
# ENVELOPE — fail closed through the tool, never a husk
# ===================================================================

class TestEnvelopeFailClosed:
    def test_true_miss_fails_loud_not_husk(self, kb) -> None:
        """A non-resolving type with NO signals abstains through the envelope (empty
        spec + retrieval_state), NEVER the ['container','content'] husk the legacy tool
        emitted."""
        res = spec_component(component_type="parking-space-tile")
        assert res["retrieval_state"] == NO_MATCH
        assert res["from_knowledge_base"] is False
        assert res["nearest"] is False
        assert res["component_id"] is None
        assert res["anatomy"] == []
        assert res["anatomy"] != ["container", "content"]      # the husk is dead
        for field in ("states", "variants", "accessibility_requirements",
                      "common_mistakes", "responsive_behavior", "design_tokens_needed",
                      "related_components"):
            assert res[field] == []

    def test_husk_branch_restored_would_be_red(self, kb) -> None:
        """Mutation proof (husk branch restored -> RED): the unknown-type result carries
        NO ['container','content'] anatomy and NO ['default'] variant husk — restoring
        the generic-husk branch would repopulate them and flip these assertions."""
        res = spec_component(component_type="sparkle_widget_xyz")
        assert res["anatomy"] != ["container", "content"]
        assert res["variants"] != ["default"]
        assert res["variants"] == []
        assert res["retrieval_state"] == NO_MATCH

    def test_unrecognised_signals_abstain(self, kb) -> None:
        res = spec_component(component_type="parking-space-tile",
                             matched_signal_ids=["sig-000000000000", "sig-ffffffffffff"])
        assert res["retrieval_state"] == NO_MATCH
        assert res["anatomy"] == []
        assert sorted(res["unmatched"]) == ["sig-000000000000", "sig-ffffffffffff"]

    def test_absent_concept_abstains(self, kb) -> None:
        """A concept the corpus genuinely lacks abstains, never the nearest component."""
        sid = _signal_id("Tokenization of card PAN before storage in a PCI vault")
        res = spec_component(component_type="pci-vault-widget", matched_signal_ids=[sid])
        assert res["retrieval_state"] == NO_MATCH
        assert res["component_id"] is None


# ===================================================================
# VARIANTS — variants_needed filters the component's OWN variants
# ===================================================================

class TestVariantsFilter:
    def test_variants_needed_filters_own_variants(self, kb) -> None:
        """variants_needed keeps only the requested names from the component's OWN
        {name, when_to_use} variants — a filter, not a husk append of unknown names."""
        res = spec_component(component_type="navbar",
                             variants_needed=["fixed", "transparent", "NONEXISTENT"])
        names = [v["name"] for v in res["variants"]]
        assert names == ["fixed", "transparent"]        # NONEXISTENT is NOT appended
        assert all(set(v) == {"name", "when_to_use"} for v in res["variants"])

    def test_no_variants_needed_returns_all_own(self, kb) -> None:
        res = spec_component(component_type="navbar")
        assert res["variants"] == [dict(v) for v in kb.get_component_pattern("navbar")["variants"]]

    def test_variants_needed_none_of_them_owned_yields_empty(self, kb) -> None:
        res = spec_component(component_type="navbar", variants_needed=["zzz", "qqq"])
        assert res["variants"] == []                    # no husk append


# ===================================================================
# CONTRACT — the new output surface
# ===================================================================

class TestContract:
    _KEYS = {"component", "component_id", "component_name", "description", "anatomy",
             "states", "variants", "accessibility_requirements", "common_mistakes",
             "responsive_behavior", "design_tokens_needed", "related_components",
             "from_knowledge_base", "nearest", "retrieval_state", "unmatched", "dangling"}

    def test_hit_keys_present_and_stable(self, kb) -> None:
        res = spec_component(component_type="navbar")
        assert set(res) == self._KEYS

    def test_miss_keys_identical_to_hit(self, kb) -> None:
        """The fail-closed spec has the SAME key set as a HIT (one stable shape)."""
        res = spec_component(component_type="parking-space-tile")
        assert set(res) == self._KEYS

    def test_legacy_keys_gone(self, kb) -> None:
        """The legacy computed surfaces are removed from the contract."""
        res = spec_component(component_type="navbar")
        for dead in ("accessibility", "design_tokens"):
            assert dead not in res

    def test_output_is_json_serializable(self, kb) -> None:
        """No _FrozenDict / tuple leaks from the hydrate boundary into the output."""
        res = spec_component(component_type="navbar")
        assert isinstance(json.loads(json.dumps(res)), dict)


# ===================================================================
# BAR-2 — the SEED-class before/after delta vs the pinned pre-edit husk
# ===================================================================

class TestBaselineDeltaBar2:
    def test_seed_hits_lift_from_dropped_a11y_to_own_a11y(self, kb) -> None:
        """SEED-class delta: the three exactly-resolving SEED hits pinned the a11y
        DROPPED (role='' / no accessibility_requirements key); the rebuild surfaces each
        component's OWN accessibility_requirements."""
        for slug, real in _SEED_EXACT.items():
            before = _PIN["cases"][f"{real}_HIT" if f"{real}_HIT" in _PIN["cases"] else f"{slug}_HIT"]
            assert before["has_accessibility_requirements_key"] is False
            res = spec_component(component_type=slug)
            assert res["component_id"] == real
            assert res["accessibility_requirements"] == kb.get_component_pattern(real)["accessibility_requirements"]
            assert len(res["accessibility_requirements"]) >= 1

    def test_archetype_huskies_lift_to_the_real_component(self, kb) -> None:
        """SEED-class delta: 'input'/'navigation' pinned the hardcoded archetype husk
        (real component dropped); the rebuild reaches the real text_input/navbar with
        their own accessibility_requirements through the nearest path."""
        for slug, real in _SEED_NEAREST.items():
            before = _PIN["cases"][f"{slug}_husk_archetype"]
            assert before["resolved"] is False
            assert before["real_component_id"] == real
            sids = kb.signal_ids_for(real)
            res = spec_component(component_type=slug, matched_signal_ids=sids)
            assert res["component_id"] == real
            assert len(res["accessibility_requirements"]) == before["real_component_accessibility_requirements_count"]

    def test_husk_probe_generic_husk_gone(self, kb) -> None:
        """BAR-2 husk-probe: the pinned unknown type returned the ['container','content']
        generic husk; the rebuild fails closed instead."""
        before = _PIN["cases"]["unknown_generic_husk"]
        assert before["anatomy"] == ["container", "content"]
        res = spec_component(component_type=before["component_type"])
        assert res["anatomy"] == []
        assert res["retrieval_state"] == NO_MATCH

    def test_pre_edit_source_hash_pinned(self) -> None:
        """The BAR-2 pin records the pre-edit source hash it was captured from — the
        before side of the delta is provenance-bound, not asserted by fiat."""
        assert len(_PIN["_meta"]["source_sha256_pre_edit"]) == 64
        assert _PIN["_meta"]["n_component_archetypes_island"] == 8


# ===================================================================
# DETERMINISM — identical input -> identical output (fresh loader too)
# ===================================================================

class TestDeterminism:
    def test_identical_input_identical_output(self, kb) -> None:
        runs = [spec_component(component_type="navbar") for _ in range(4)]
        base = json.dumps(runs[0], sort_keys=True)
        for other in runs[1:]:
            assert json.dumps(other, sort_keys=True) == base
        assert json.dumps(_fresh_call(component_type="navbar"), sort_keys=True) == base

    def test_nearest_path_deterministic(self, kb) -> None:
        sids = kb.signal_ids_for("text_input")
        a = spec_component(component_type="xyz", matched_signal_ids=sids)
        b = spec_component(component_type="xyz", matched_signal_ids=sids)
        assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


# ===================================================================
# HYPERION — named ceilings at the caller boundary; no eval on input
# ===================================================================

class TestCallerBoundaryCeilings:
    def test_matched_signal_ids_bounded(self, kb) -> None:
        """A flood of caller-supplied signal ids is bounded at _MAX_MATCHED_SIGNALS
        before hydrate; all-junk still abstains, no amplification past the cap."""
        flood = [f"sig-{i:012x}" for i in range(_MAX_MATCHED_SIGNALS * 10)]
        res = spec_component(component_type="parking-space-tile", matched_signal_ids=flood)
        assert res["retrieval_state"] == NO_MATCH
        assert len(res["unmatched"]) <= _MAX_MATCHED_SIGNALS

    def test_context_bounded_and_never_surfaced(self, kb) -> None:
        """The untrusted free-text context is bounded where it enters and never reaches
        the output surface — retrieval is driven by the resolved id / matched ids."""
        assert isinstance(_MAX_DESCRIPTION_LEN, int) and _MAX_DESCRIPTION_LEN > 0
        marker = "SENSITIVE_MARKER_" + "z" * (_MAX_DESCRIPTION_LEN * 3)
        res = spec_component(component_type="navbar", context=marker)
        assert "SENSITIVE_MARKER_" not in json.dumps(res)


# ===================================================================
# DELETIONS — _COMPONENT_ARCHETYPES gone (0 code refs); grader byte-identical
# ===================================================================

class TestDeletions:
    def test_component_archetypes_symbol_deleted(self) -> None:
        """The 8-slug _COMPONENT_ARCHETYPES island is DELETED — importing it fails, and
        the tool source names it nowhere (grep 0 code refs)."""
        with pytest.raises(ImportError):
            from theia.tools.spec_component import _COMPONENT_ARCHETYPES  # noqa: F401
        src = _SPEC_SRC.read_text(encoding="utf-8")
        assert "_COMPONENT_ARCHETYPES" not in src

    def test_legacy_computed_constants_deleted(self) -> None:
        """The computed state/breakpoint constants are gone (states/responsive read from
        the corpus now)."""
        src = _SPEC_SRC.read_text(encoding="utf-8")
        for dead in ("_DEFAULT_STATES", "_INTERACTIVE_STATES", "_RESPONSIVE_BREAKPOINTS"):
            assert dead not in src

    def test_grader_no_longer_imports_the_island(self) -> None:
        """grade.py no longer imports or uses the deleted symbol (its LEG-3 archetype
        husk branch was dead on this benchmark; removing it left the baseline
        byte-identical — the reason it goes at S4, not bundled to S6 like _ANTI_PATTERNS
        + the matcher teardown)."""
        gpath = Path(__file__).parent / "data" / "gmetric" / "grade.py"
        tree = ast.parse(gpath.read_text(encoding="utf-8"))
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imported += [a.name for a in node.names]
        assert "_COMPONENT_ARCHETYPES" not in imported
        # the sibling _ANTI_PATTERNS island is now ALSO gone at S6 (story-041efcf4)
        assert "_ANTI_PATTERNS" not in imported

    def test_grader_baseline_byte_identical(self) -> None:
        """The pinned matcher baseline result-core is unchanged by the deletion — the
        archetype husk never surfaced a real id, so LEG-3's removal is score-neutral,
        no --refreeze."""
        gdir = Path(__file__).parent / "data" / "gmetric"
        if str(gdir) not in sys.path:
            sys.path.insert(0, str(gdir))
        import grade  # noqa: E402  (frozen grader, theia-only)
        core = grade.grade(grade.rank_baseline, "baseline_four_surface_matcher")
        pinned = json.loads(grade.BASELINE_OUT.read_text(encoding="utf-8"))["determinism"]["result_core_sha256"]
        assert grade.result_core_sha256(core) == pinned
        assert core["covered"]["10"] == 35


# ===================================================================
# KILLED-WITH-REASON (Directive 10/12) — superseded legacy behaviours
# ===================================================================

class TestKilledLegacy:
    def test_unknown_no_longer_returns_a_structure(self, kb) -> None:
        """KILLED test_unknown_component: it asserted an unknown type returns a basic
        structure (anatomy>=1, states>=1). REPLACED: an unknown type fails closed
        (empty + retrieval_state), the husk is gone."""
        res = spec_component(component_type="sparkle_widget_xyz")
        assert res["anatomy"] == [] and res["states"] == []
        assert res["retrieval_state"] == NO_MATCH

    def test_archetype_role_interface_retired(self, kb) -> None:
        """KILLED test_button_spec / test_input_spec / test_includes_accessibility /
        test_modal_spec: they asserted the hardcoded archetype accessibility dict
        (result['accessibility']['role'] == 'button'/'textbox'/'dialog'). REPLACED: the
        accessibility surface is the component's OWN accessibility_requirements list;
        there is no 'accessibility' role dict."""
        res = spec_component(component_type="button")
        assert "accessibility" not in res
        assert res["component_id"] == "button"
        assert res["accessibility_requirements"] == kb.get_component_pattern("button")["accessibility_requirements"]

    def test_platform_knob_retired(self, kb) -> None:
        """KILLED test_includes_responsive: it passed platform='web' and asserted the
        computed breakpoint dict. REPLACED: responsive_behavior is the corpus field;
        the platform param is retired (no shim), so passing it is a TypeError."""
        with pytest.raises(TypeError):
            spec_component(component_type="navbar", platform="web")  # type: ignore[call-arg]


# ===================================================================
# DEEP-FREEZE — the singleton corpus stays uncorrupted through the tool
# ===================================================================

class TestCorpusUncorrupted:
    def test_corpus_singleton_uncorrupted_through_tool(self, kb) -> None:
        before = list(kb.get_component_pattern("navbar")["accessibility_requirements"])
        res = spec_component(component_type="navbar")
        # mutating the returned spec must not touch the singleton corpus
        res["accessibility_requirements"].append("TAMPER")
        res["variants"].clear()
        after = list(kb.get_component_pattern("navbar")["accessibility_requirements"])
        assert after == before


# ===================================================================
# FIREWALL — the tool imports only theia.*
# ===================================================================

class TestFirewall:
    def test_no_forbidden_imports(self) -> None:
        tree = ast.parse(_SPEC_SRC.read_text(encoding="utf-8"))
        forbidden = {"coeus", "othrys", "mnemos"}
        mods: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods.append(node.module)
        offenders = [m for m in mods if m.split(".")[0] in forbidden]
        assert not offenders, f"spec_component imports {offenders}"
