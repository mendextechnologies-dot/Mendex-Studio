"""Mendex Engineering Studio Integrations Framework (v1.5).

Owned by Agent 2 (Antigravity). Provides safe execution, tool detection,
external tool connectors, parsers, and research dataset provenance.
"""

from .contracts import (
    ToolDescriptor,
    ToolKind,
    ToolState,
    JobState,
    JobRequest,
    JobResult,
    ArtifactManifest,
    ToolAdapter,
)

__all__ = [
    "ToolDescriptor",
    "ToolKind",
    "ToolState",
    "JobState",
    "JobRequest",
    "JobResult",
    "ArtifactManifest",
    "ToolAdapter",
]
