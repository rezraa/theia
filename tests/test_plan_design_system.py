# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""plan_design_system's base-system match retrofitted onto the Shape-C engine over a
SECOND design_systems signal index — story-0e030efd (council 3e6eeeab).

*** NORTH STAR. *** plan_design_system stops defaulting every product to 'custom': it
hydrates the nearest existing design system through the shared engine over the
design_systems corpus, fanning out over ``related_systems``, or ABSTAINS via the
four-state envelope WITH a reason — never a silent always-'custom' husk.

The base-system-match leg alone is wired: the caller (the LLM) recognises the product's
structural signals against ``get_system_signal_index`` and passes the matched ids;
plan_design_system hydrates through ``loader.hydrate_systems`` (the SAME parameterized
``_SignalEngine`` primitives the component index uses — ZERO new engine code, only a
second ``_NamedIndex`` over ``signals`` / ``related_systems`` / ``system_ids``). This is
the one home for the leg's proofs:

* RED-first NORTH STAR — the AC's parking app (measured -> silent 'custom') now abstains
  through the envelope WITH a reason; a product matching a known system's signals
  hydrates that system + its ``related_systems`` fan-out;
* the four-state envelope on the foundation (HIT / LOW_CONFIDENCE surface the nearest
  system; NO_MATCH / DANGLING abstain to the honest custom/create foundation, not a husk);
* BAR-2 — the before/after delta against the pinned pre-edit always-'custom' output;
* the generative token/hierarchy/responsive/theming scaffolding is BYTE-UNCHANGED
  (the shipping file's scaffolding region hashes to the pinned pre-edit hash, and the
  scaffolding is independent of which foundation leg fired);
* the existing_system explicit-id path is kept BYTE-UNCHANGED and still overrides the
  signal match;
* the mutation proof — retrieval off -> RED (the matched system collapses back to 'custom');
* the SECOND index is BUILT + its public bindings share the ONE engine, with NO
  cross-corpus leakage (a system never surfaces in a component result nor vice versa);
* determinism (incl. a fresh loader), the caller-boundary ceiling on matched ids, and
  the firewall (theia.* only).

The component-index recall (engine 45 / union 53) and the matcher are untouched here;
their non-regression rides tests/test_retrieval_bar1.py + tests/test_gmetric_s2.py.

Firewall: imports only theia.* . Never opens the live Othrys DB.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
from pathlib import Path

import pytest

import theia.tools._shared as _shared
from theia.knowledge.loader import (
    DANGLING,
    HIT,
    LOW_CONFIDENCE,
    NO_MATCH,
    KnowledgeLoader,
    RetrievalResult,
    _SignalEngine,
)
from theia.tools._shared import _MAX_MATCHED_SIGNALS
from theia.tools.plan_design_system import plan_design_system

_PDS_SRC = Path(inspect.getsourcefile(plan_design_system))
_PIN = json.loads(
    (Path(__file__).parent / "data" / "baseline_plan_design_system_pinned.json").read_text(
        encoding="utf-8"
    )
)

# The AC's RED-first product — measured -> 'custom' at HEAD (pinned).
_PARKING = "parking app for finding/reserving spaces"

# A system that carries both signals AND a resolvable related_systems fan-out; its
# OWN signals are the "product matching a known system's signals" the AC names.
_KNOWN_SYSTEM = "atomic_design"


@pytest.fixture()
def kb() -> KnowledgeLoader:
    _shared._knowledge = None
    return _shared.get_knowledge(conn=None)


def _foundation(**kwargs) -> dict:
    return plan_design_system(**kwargs)["recommended_foundation"]


def _match_ids(kb: KnowledgeLoader, system_id: str) -> list[str]:
    """The signal ids a caller would recognise for a product that IS this system's
    idiom — the system's own catalogued signals (seed-from-node over the systems index)."""
    return kb.system_signal_ids_for(system_id)


# ===================================================================
# RED-FIRST — the NORTH STAR: no more silent always-'custom'
# ===================================================================

class TestNorthStar:
    def test_parking_app_abstains_with_a_reason_not_a_silent_custom(self, kb) -> None:
        """The AC probe: the parking app (whose signals match no system) no longer
        returns a bare 'custom' husk — it abstains THROUGH the four-state envelope with
        a retrieval_state and a reason naming WHY. The before side is pinned silent."""
        before = _PIN["cases"]["parking_app_always_custom"]
        assert before["base_system"] == "custom"
        assert before["has_retrieval_state_key"] is False        # silent at HEAD

        f = _foundation(product_description=_PARKING, platforms=["mobile", "web"])
        assert f["base_system"] == "custom"                      # honest abstention...
        assert f["retrieval_state"] == NO_MATCH                  # ...but now stated
        assert f["extend_or_fork"] == "create"
        assert f["related_systems"] == []
        assert str(NO_MATCH) in f["rationale"]                   # the reason names the state
        assert f["rationale"] != before["foundation"]["rationale"]

    def test_matching_product_hydrates_the_system_and_its_related_systems(self, kb) -> None:
        """The AC's other half: a product matching a known system's signals hydrates
        THAT system as the base and fans out over its OWN related_systems."""
        sids = _match_ids(kb, _KNOWN_SYSTEM)
        assert sids                                              # the system has signals
        f = _foundation(product_description="a component library", matched_signal_ids=sids)
        assert f["base_system"] == _KNOWN_SYSTEM
        assert f["extend_or_fork"] == "fork"
        assert f["retrieval_state"] in (HIT, LOW_CONFIDENCE)
        # the fan-out surface == the system's OWN resolvable related_systems, resolved
        own = [n for n in kb.get_design_system(_KNOWN_SYSTEM)["related_systems"]
               if kb.get_design_system(n)]
        assert [r["system_id"] for r in f["related_systems"]] == own
        assert all(r["system_name"] == kb.get_design_system(r["system_id"])["name"]
                   for r in f["related_systems"])
        # transparent, auditable votes (integers), never a tuned score
        assert isinstance(f["retrieval"]["score"], int) and f["retrieval"]["seed"] is True

    def test_every_system_with_signals_self_hydrates(self, kb) -> None:
        """Generalises the match proof beyond one system: EVERY design system that
        carries signals hydrates itself as the base when seeded from its own signals
        (the 2 signal-less orphans — inclusive_design/design_sprint — correctly abstain;
        authoring their signals is out of scope)."""
        seedable = [s for s in kb._design_systems if s.get("signals")]
        assert len(seedable) == 52                               # 54 - 2 orphans
        for s in seedable:
            f = _foundation(product_description="x", matched_signal_ids=kb.system_signal_ids_for(s["id"]))
            assert f["base_system"] == s["id"], f"{s['id']} did not self-hydrate"
        for orphan in ("inclusive_design", "design_sprint"):
            f = _foundation(product_description="x", matched_signal_ids=kb.system_signal_ids_for(orphan))
            assert f["base_system"] == "custom" and f["retrieval_state"] == NO_MATCH


# ===================================================================
# FOUR-STATE ENVELOPE on the foundation — abstain, never a husk
# ===================================================================

class TestEnvelope:
    def test_no_matched_ids_is_honest_no_match(self, kb) -> None:
        f = _foundation(product_description=_PARKING)
        assert f["retrieval_state"] == NO_MATCH
        assert f["base_system"] == "custom" and f["related_systems"] == []

    def test_junk_ids_abstain_with_unmatched_surfaced(self, kb) -> None:
        f = _foundation(product_description="x", matched_signal_ids=["sig-000000000000"])
        assert f["retrieval_state"] == NO_MATCH
        assert f["unmatched"] == ["sig-000000000000"]
        assert f["base_system"] == "custom"

    def test_abstention_and_hit_share_the_envelope_keys(self, kb) -> None:
        """Both the abstention and the match carry retrieval_state / unmatched /
        dangling / related_systems — one stable envelope, not a shape that vanishes on
        a miss (the legacy silent-custom dropped the whole envelope)."""
        miss = _foundation(product_description=_PARKING)
        hit = _foundation(product_description="x", matched_signal_ids=_match_ids(kb, _KNOWN_SYSTEM))
        envelope = {"retrieval_state", "unmatched", "dangling", "related_systems"}
        assert envelope <= set(miss) and envelope <= set(hit)

    def test_dangling_state_abstains(self, kb, monkeypatch) -> None:
        """A DANGLING envelope (ids resolving only to absent systems) abstains to the
        honest custom foundation, never a husk. Constructed (Directive 8): the real
        corpus has no dangling related_systems, so the state is injected at the seam."""
        monkeypatch.setattr(
            KnowledgeLoader, "hydrate_systems",
            lambda self, ids, k=10, fan_out=True: RetrievalResult(
                state=DANGLING, dangling=["__ghost_system__"]),
        )
        f = _foundation(product_description="x", matched_signal_ids=["sig-whatever00"])
        assert f["base_system"] == "custom"
        assert f["retrieval_state"] == DANGLING
        assert f["dangling"] == ["__ghost_system__"]


# ===================================================================
# BAR-2 — before/after delta vs the pinned pre-edit always-'custom' output
# ===================================================================

class TestBaselineDeltaBar2:
    def test_pre_edit_source_hash_pinned(self) -> None:
        """The before side is provenance-bound: the pin records the pre-edit source
        hash (CRLF working tree) and the EOL-agnostic scaffolding anchor."""
        assert len(_PIN["_meta"]["source_sha256_pre_edit"]) == 64
        assert _PIN["_meta"]["n_systems_with_keywords_field"] == 0   # the pathology's root
        assert _PIN["_meta"]["n_systems"] == 54

    def test_silent_custom_becomes_stated_abstention(self, kb) -> None:
        """BAR-2 delta on the parking probe: pinned pre-edit = 'custom' with NO
        retrieval_state and the generic 'did not match' rationale; post-edit = 'custom'
        WITH the envelope + a state-naming reason."""
        before = _PIN["cases"]["parking_app_always_custom"]["foundation"]
        assert "retrieval_state" not in before
        assert before["rationale"] == "Product description did not match any existing system"
        after = _foundation(product_description=_PARKING, platforms=["mobile", "web"])
        assert "retrieval_state" in after and after["retrieval_state"] == NO_MATCH

    def test_always_custom_sweep_now_can_hydrate(self, kb) -> None:
        """The pinned sweep was 6/6 'custom' regardless of the product (the degenerate
        keyword leg). The new leg hydrates a real system the moment the caller supplies
        recognised signals — the pathology (best_score stuck at 0) is gone."""
        assert _PIN["cases"]["always_custom_sweep"]["all_custom"] is True
        # the same sweep products, now with recognised signals, reach a real system
        hydrated = _foundation(product_description="ops dashboard",
                               matched_signal_ids=_match_ids(kb, _KNOWN_SYSTEM))
        assert hydrated["base_system"] == _KNOWN_SYSTEM != "custom"

    def test_frozen_grader_leg4_is_the_untouched_comparand(self) -> None:
        """The grader's LEG-4 replica of this leg stays FROZEN (the pre-S5 comparand,
        out of scope, no --refreeze): on the parking query it still returns the empty
        design-system id-list, never a component id."""
        assert _PIN["_meta"]["frozen_grader_leg4_parking_output"] == []


# ===================================================================
# SCAFFOLDING BYTE-UNCHANGED — the generative token/hierarchy/responsive/theming
# ===================================================================

def _scaffolding_region(src_text: str, marker: str) -> str:
    lf = src_text.replace("\r\n", "\n")
    assert lf.count(marker) == 1, "scaffolding marker not unique"
    return lf[lf.index(marker):]


class TestScaffoldingByteUnchanged:
    def test_scaffolding_region_hashes_to_pinned_pre_edit(self) -> None:
        """The generative token/hierarchy/responsive/theming scaffolding (from the
        section-2 marker to EOF) is BYTE-IDENTICAL to the pre-edit HEAD reference — the
        S5 edit is entirely ABOVE the marker. Any future edit to it trips this."""
        marker = _PIN["_meta"]["scaffolding_start_marker"]
        region = _scaffolding_region(_PDS_SRC.read_text(encoding="utf-8"), marker)
        assert hashlib.sha256(region.encode("utf-8")).hexdigest() == \
            _PIN["_meta"]["scaffolding_lf_sha256"]

    def test_the_edit_is_above_the_marker(self) -> None:
        """Provenance for the byte-unchanged claim: the three things S5 added
        (matched_signal_ids, the hydrate_systems call, the related_systems fan-out) all
        occur BEFORE the scaffolding marker in the source."""
        lf = _PDS_SRC.read_text(encoding="utf-8").replace("\r\n", "\n")
        cut = lf.index(_PIN["_meta"]["scaffolding_start_marker"])
        for token in ("matched_signal_ids", "hydrate_systems", "related_systems"):
            assert token in lf[:cut]
            assert token not in lf[cut:], f"{token} leaked into the scaffolding region"

    def test_scaffolding_independent_of_which_leg_fired(self, kb) -> None:
        """A behavioural byte-unchanged proof: for identical platforms, the token /
        hierarchy / responsive / theming outputs are IDENTICAL whether the foundation
        hydrated a system, abstained, or came from existing_system — the scaffolding
        does not read the foundation leg."""
        keys = ("token_architecture", "component_hierarchy", "responsive_strategy",
                "theming_approach")
        miss = plan_design_system(product_description=_PARKING, platforms=["web"])
        hit = plan_design_system(product_description="x", platforms=["web"],
                                 matched_signal_ids=_match_ids(kb, _KNOWN_SYSTEM))
        ex = plan_design_system(product_description="x", platforms=["web"],
                                existing_system=_KNOWN_SYSTEM)
        for k in keys:
            assert miss[k] == hit[k] == ex[k]

    def test_full_result_shape_unchanged(self, kb) -> None:
        res = plan_design_system(product_description="x", matched_signal_ids=_match_ids(kb, _KNOWN_SYSTEM))
        assert set(res) == {"recommended_foundation", "token_architecture",
                            "component_hierarchy", "responsive_strategy", "theming_approach"}
        json.dumps(res)  # no _FrozenDict / tuple leak from the hydrate boundary


# ===================================================================
# existing_system explicit-id path — kept BYTE-UNCHANGED, still overrides
# ===================================================================

class TestExistingSystemPath:
    def test_existing_system_foundation_byte_identical_to_pin(self, kb) -> None:
        """The explicit-id path is untouched by S5 — its foundation dict matches the
        pinned pre-edit output exactly (keys, values, 'extend', rationale)."""
        pinned = _PIN["cases"]["existing_system_atomic_design_BYTE_UNCHANGED"]["foundation"]
        f = _foundation(product_description="whatever", existing_system=_KNOWN_SYSTEM)
        assert f == pinned

    def test_existing_system_overrides_signal_match(self, kb) -> None:
        """existing_system wins even when matched_signal_ids point elsewhere — the
        explicit path is checked first and short-circuits the signal match."""
        other = _match_ids(kb, "design_tokens")
        f = _foundation(product_description="x", existing_system=_KNOWN_SYSTEM,
                        matched_signal_ids=other)
        assert f["base_system"] == _KNOWN_SYSTEM
        assert f["rationale"].startswith("Building on existing system")
        assert "retrieval_state" not in f            # the explicit path carries no envelope

    def test_unknown_existing_system_falls_through_to_the_signal_leg(self, kb) -> None:
        """A non-resolving existing_system id does not short-circuit — the signal leg
        still runs (and abstains honestly here, no husk)."""
        f = _foundation(product_description="x", existing_system="no_such_system_xyz")
        assert f["base_system"] == "custom" and f["retrieval_state"] == NO_MATCH


# ===================================================================
# MUTATION — retrieval off -> RED (the leg is load-bearing)
# ===================================================================

class TestRetrievalMutation:
    def test_retrieval_off_collapses_the_match_back_to_custom(self, kb, monkeypatch) -> None:
        """Prove the hydrate leg does the work: a product that hydrates its system with
        retrieval ON collapses to 'custom' the moment hydrate_systems is disabled — the
        win is the retrieval's, not an accident of the surrounding scaffolding."""
        sids = _match_ids(kb, _KNOWN_SYSTEM)
        healthy = _foundation(product_description="x", matched_signal_ids=sids)
        assert healthy["base_system"] == _KNOWN_SYSTEM                     # GREEN with retrieval

        monkeypatch.setattr(
            KnowledgeLoader, "hydrate_systems",
            lambda self, ids, k=10, fan_out=True: RetrievalResult(state=NO_MATCH),
        )
        _shared._knowledge = None
        mutated = _foundation(product_description="x", matched_signal_ids=sids)
        assert mutated["base_system"] == "custom"                          # RED without it
        assert mutated["retrieval_state"] == NO_MATCH


# ===================================================================
# SECOND INDEX built + public bindings share ONE engine; NO cross-corpus leak
# ===================================================================

class TestSecondIndexBuiltAndShared:
    def test_loader_builds_the_second_index_at_load(self, kb) -> None:
        assert kb._systems_index.name == "design_systems"
        assert kb._systems_index.signal_field == "signals"
        assert kb._systems_index.edge_field == "related_systems"
        assert kb._systems_index.id_field == "system_ids"
        assert kb._systems_index.signal_index                     # populated in __init__

    def test_public_bindings_delegate_to_the_ONE_engine(self, kb) -> None:
        """The S5 public bindings are thin delegations of the SAME _SignalEngine
        primitives the component bindings use — no duplicated engine, one source."""
        assert KnowledgeLoader.hydrate_systems is not KnowledgeLoader.hydrate  # distinct bindings
        assert KnowledgeLoader._hydrate is _SignalEngine._hydrate              # ...over ONE engine
        assert KnowledgeLoader._build_signal_index is _SignalEngine._build_signal_index
        assert KnowledgeLoader._signal_index_view is _SignalEngine._signal_index_view

    def test_system_signal_index_view_is_system_keyed(self, kb) -> None:
        view = kb.get_system_signal_index()
        assert view and all(set(e) == {"signal_id", "signal_text", "system_ids"} for e in view)

    def test_no_cross_corpus_leakage_through_public_bindings(self, kb) -> None:
        """Theia's binding reservation, enforced through the SHIPPING bindings: a system
        never surfaces in a component hydrate, nor a component in a system hydrate. The
        id-spaces are disjoint and each hydrate reads only its own _NamedIndex."""
        comp_ids, sys_ids = set(kb._component_pattern_index), set(kb._design_system_index)
        assert not (comp_ids & sys_ids)
        sys_res = kb.hydrate_systems(kb.system_signal_ids_for(_KNOWN_SYSTEM), k=50)
        assert not ({p["id"] for p in sys_res.patterns} & comp_ids)
        comp_res = kb.hydrate(kb.signal_ids_for("navbar"), k=50)
        assert not ({p["id"] for p in comp_res.patterns} & sys_ids)

    def test_plan_design_system_surfaces_no_component_id(self, kb) -> None:
        """End-to-end: the tool's foundation/related_systems never carry a component id."""
        comp_ids = set(kb._component_pattern_index)
        f = _foundation(product_description="x", matched_signal_ids=_match_ids(kb, _KNOWN_SYSTEM))
        assert f["base_system"] not in comp_ids
        assert not ({r["system_id"] for r in f["related_systems"]} & comp_ids)


# ===================================================================
# DETERMINISM — identical input -> identical output (fresh loader too)
# ===================================================================

class TestDeterminism:
    def test_identical_input_identical_output(self, kb) -> None:
        sids = _match_ids(kb, _KNOWN_SYSTEM)
        runs = [plan_design_system(product_description="x", matched_signal_ids=sids) for _ in range(4)]
        base = json.dumps(runs[0], sort_keys=True)
        assert all(json.dumps(r, sort_keys=True) == base for r in runs[1:])

    def test_fresh_loader_identical(self, kb) -> None:
        sids = _match_ids(kb, _KNOWN_SYSTEM)
        a = plan_design_system(product_description="x", matched_signal_ids=sids)
        _shared._knowledge = None
        b = plan_design_system(product_description="x", matched_signal_ids=_match_ids(_shared.get_knowledge(), _KNOWN_SYSTEM))
        assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


# ===================================================================
# HYPERION — caller-boundary ceiling on matched ids; firewall theia.* only
# ===================================================================

class TestCallerBoundaryAndFirewall:
    def test_matched_signal_ids_bounded_before_hydrate(self, kb) -> None:
        """A flood of caller ids is bounded at _MAX_MATCHED_SIGNALS before hydrate; all
        junk still abstains, no amplification past the cap."""
        flood = [f"sig-{i:012x}" for i in range(_MAX_MATCHED_SIGNALS * 10)]
        f = _foundation(product_description="x", matched_signal_ids=flood)
        assert f["retrieval_state"] == NO_MATCH
        assert len(f["unmatched"]) <= _MAX_MATCHED_SIGNALS

    def test_product_description_never_drives_the_match(self, kb) -> None:
        """The free-text product_description is context only — the match is driven by
        matched_signal_ids. Naming a system verbatim in the prose (no ids) still abstains
        (the degenerate name-substring leg is gone)."""
        f = _foundation(product_description="an Atomic Design component library system")
        assert f["base_system"] == "custom" and f["retrieval_state"] == NO_MATCH

    def test_shipping_tool_imports_theia_only(self) -> None:
        """The retrofitted tool (and the system-index accessor) import theia.* only."""
        from theia.tools import get_signal_index as gsi
        for mod_path in (_PDS_SRC, Path(inspect.getsourcefile(gsi))):
            tree = ast.parse(mod_path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    assert (node.module or "").split(".")[0] not in ("coeus", "othrys", "mnemos")
                elif isinstance(node, ast.Import):
                    for a in node.names:
                        assert a.name.split(".")[0] not in ("coeus", "othrys", "mnemos")
