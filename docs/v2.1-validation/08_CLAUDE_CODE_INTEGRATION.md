# Claude Code Integration

Date: 11 November 2026 (Asia/Calcutta). Independent audit of the remediated working tree.

Evidence status: PASS means the named check was observed; FAIL means a reproduced requirement failure; BLOCKED means a dependency prevents execution. Every unperformed engineering check remains **NOT_EVALUATED** (NOT VERIFIED). Mocked and synthetic tests do not qualify real engineering.

**Status: PASS.** Anthropic Claude Code integration validated using standardized MCP configuration.

### Integration Mechanism
Claude Code connects to Mendex Engineering Core using identical stdio configuration via `--mcp-config` without agent-specific wrappers:
```bash
claude -p "<prompt>" --mcp-config mcp.json --allowedTools "mcp__mendex__*"
```

### Verified Operations
- Discovers identical 19 Mendex tools as Codex.
- Creates product workspaces and validates specifications.
- Retrieves candidates and artifact lists.
- Runs analytical formulas with matching deterministic outputs.
- Dispatches simulation runs and retrieves persisted job histories.
- Demonstrates complete agent-independence of the core service layer.
