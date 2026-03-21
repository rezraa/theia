# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""Theia tool modules.

Each tool is implemented in its own submodule and registered with the
FastMCP server via ``@mcp.tool()`` decorators in ``theia.server``.

Shared state (KnowledgeLoader) lives in
``theia.tools._shared`` and is imported by every tool module.
"""

from theia.tools.audit_design import audit_design
from theia.tools.plan_design_system import plan_design_system
from theia.tools.spec_component import spec_component
from theia.tools.evaluate_accessibility import evaluate_accessibility
from theia.tools.log_decision import log_decision

__all__ = [
    "audit_design",
    "plan_design_system",
    "spec_component",
    "evaluate_accessibility",
    "log_decision",
]
