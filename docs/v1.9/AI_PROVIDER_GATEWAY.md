# MENDEX ENGINEERING STUDIO v1.9 — AI PROVIDER GATEWAY

## 1. Provider-Neutral Architecture

The `AICopilotGateway` provides an abstraction layer across AI models:

- **Offline Deterministic Backend**: Built-in rule-based engineering engine. Zero network calls, zero API keys, 100% deterministic physics calculation.
- **Gemini API**: Optional provider for complex natural-language requirement extraction and reasoning.
- **OpenAI API**: Optional provider for multi-modal engineering reasoning.
- **Local Models**: Ollama / LLaMA local model connectors.

### Privacy & Governance Safeguards
- Cloud transmission is strictly **opt-in** (`cloud_opt_in=False` by default).
- Proprietary customer designs and netlists are never transmitted without explicit user permission.
