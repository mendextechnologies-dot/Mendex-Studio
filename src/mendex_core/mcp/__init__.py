"""Standardized Model Context Protocol (MCP) Server for Mendex Engineering Core v2.1.

Allows AI agents (OpenAI Codex, Anthropic Claude Code, etc.) to discover and
execute deterministic engineering tools over standard JSON-RPC 2.0 stdio.
"""
from .server import MendexMCPServer

__all__ = ["MendexMCPServer"]
