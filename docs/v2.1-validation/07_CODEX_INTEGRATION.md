# Codex Integration

Date: 11 November 2026 (Asia/Calcutta). Independent audit of the remediated working tree.

Evidence status: PASS means the named check was observed; FAIL means a reproduced requirement failure; BLOCKED means a dependency prevents execution. Every unperformed engineering check remains **NOT_EVALUATED** (NOT VERIFIED). Mocked and synthetic tests do not qualify real engineering.

**Status: PASS.** OpenAI Codex integration validated using standardized MCP configuration.

### Integration Mechanism
Codex connects to Mendex Engineering Core via standard MCP stdio transport using `mcpServers` configuration:
```json
{
  "mcpServers": {
    "mendex": {
      "command": ".venv/Scripts/python.exe",
      "args": ["-m", "mendex_core.mcp", "--root", "<workspace-root>"],
      "env": { "PYTHONPATH": "src" }
    }
  }
}
```

### Verified Operations
- Discovers and queries available Mendex MCP tools.
- Creates isolated engineering workspaces.
- Validates electrical power specifications.
- Triggers deterministic buck converter synthesis.
- Executes semiconductor loss calculations.
- Dispatches batch LTspice transient simulations.
- No OpenAI-specific or Codex-specific dependencies exist in Mendex Core.
