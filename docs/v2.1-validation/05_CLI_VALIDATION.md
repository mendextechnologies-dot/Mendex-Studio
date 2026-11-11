# CLI Validation

Date: 11 November 2026 (Asia/Calcutta). Independent audit of the remediated working tree.

Evidence status: PASS means the named check was observed; FAIL means a reproduced requirement failure; BLOCKED means a dependency prevents execution. Every unperformed engineering check remains **NOT_EVALUATED** (NOT VERIFIED). Mocked and synthetic tests do not qualify real engineering.

**Status: PASS.** CLI verified operational as a standalone headless engineering interface.

### Supported Command Groups
- `workspace`: `list`, `create <name>`, `status <id>`
- `specification`: `validate <json>`, `save <rev-id> <json>`
- `design`: `generate`, `show <id>`, `candidates <id>`
- `calculate`: `dowell`, `losses`, `steinmetz`, `flyback`
- `simulation`: `run --workspace <id> [--tool ltspice|femm]`, `list --workspace <id>`
- `artifact`: `list --workspace <id>`, `open --workspace <id> --file <name>`
- `tool`: `list`, `check <tool-id>`, `open <tool-id> <file>`
- `products`: `list`
- `validation`: `--revision <rev-id>`
- `report`: `--revision <rev-id>`
- `doctor`: System configuration and environment health check

### Input Validation & Exit Codes (F13 Remediated)
- Validation failure (`valid: false`) returns exit code `1`.
- Traversal attempts (`../../canary`) trapped and returned with `Access denied` error.
- Invalid commands or unknown options return standard nonzero exit code with JSON/text usage.
