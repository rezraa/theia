# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""Shared fixtures for Theia test suite."""

from __future__ import annotations

import os
import shutil
import tempfile

import pytest

from theia.tools._shared import get_knowledge


@pytest.fixture()
def knowledge():
    """Create a fresh KnowledgeLoader instance for testing.

    Returns the JSON-backed singleton (standalone mode, no graph connection).
    Each test gets the same singleton -- tests that need isolation should
    mock the loader internals.
    """
    return get_knowledge(conn=None)


@pytest.fixture()
def tmp_data_dir(monkeypatch, tmp_path):
    """Patch THEIA_DATA_DIR to a temporary directory.

    This ensures log_decision and other file-writing tools write to a
    throwaway location and don't pollute the real data directory.
    The directory is cleaned up automatically by pytest's tmp_path.
    """
    data_dir = tmp_path / "theia_data"
    data_dir.mkdir()
    monkeypatch.setenv("THEIA_DATA_DIR", str(data_dir))
    return data_dir
