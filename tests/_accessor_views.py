# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""The accessor's compact groups, inverted back into loader-view entry lists.

``get_signal_index`` serves each group as ``{owner_id: {signal_id: signal_text}}``
(council 1e970338). Tests that recognise text -> signal id, or pick an id by
position, read the entry-list form; deriving it HERE from the accessor's own output
keeps their ids sourced from the production surface (Directive 8), and because the
inversion rebuilds the loader view exactly (proven in test_typed_index_s1), every
positional pick lands on the same id it did against the loader view.
"""

from __future__ import annotations

from theia.tools.get_signal_index import get_signal_index

# Each group's owner-id key — the column of the loader view it was projected from.
GROUP_ID_KEYS = {"component_signals": "component_ids", "system_signals": "system_ids"}


def flatten_group(group: dict[str, dict[str, str]], id_key: str) -> list[dict]:
    """Invert one compact group into ``[{signal_id, signal_text, <id_key>}]`` sorted by
    ``signal_id``. Owner lists keep the group's emitted owner order, so a rebuilt view
    equal to the loader view also proves the owners were emitted sorted."""
    entries: dict[str, dict] = {}
    for owner, signals in group.items():
        for sid, text in signals.items():
            entries.setdefault(sid, {"signal_id": sid, "signal_text": text, id_key: []})[id_key].append(owner)
    return [entries[sid] for sid in sorted(entries)]


def accessor_views() -> dict[str, list[dict]]:
    """Both accessor groups, each as its loader-view entry list."""
    nested = get_signal_index()
    return {g: flatten_group(nested[g], id_key) for g, id_key in GROUP_ID_KEYS.items()}
