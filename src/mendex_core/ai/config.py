"""AI Provider Configuration & API Key Storage Manager."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class AIProviderConfig(BaseModel):
    provider: str = "offline"  # "gemini", "openai", "offline"
    model: str = "local_engineering_rules"
    api_key: str = ""
    cloud_opt_in: bool = False
    custom_endpoint: Optional[str] = None


def get_config_path(data_root: Optional[Path] = None) -> Path:
    root = data_root or Path.cwd()
    return root / ".mendex" / "ai_config.json"


def load_ai_config(data_root: Optional[Path] = None) -> AIProviderConfig:
    """Loads AI configuration from .mendex/ai_config.json, falling back to environment variables."""
    cfg = AIProviderConfig()

    # 1. Check environment variables first
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    provider_env = os.getenv("MENDEX_AI_PROVIDER")

    if provider_env:
        cfg.provider = provider_env.lower()
    elif gemini_key:
        cfg.provider = "gemini"
    elif openai_key:
        cfg.provider = "openai"

    if cfg.provider == "gemini":
        cfg.api_key = gemini_key or ""
        cfg.model = os.getenv("MENDEX_AI_MODEL", "gemini-2.0-flash")
    elif cfg.provider == "openai":
        cfg.api_key = openai_key or ""
        cfg.model = os.getenv("MENDEX_AI_MODEL", "gpt-4o")

    # 2. Check local file override (.mendex/ai_config.json)
    cfg_file = get_config_path(data_root)
    if cfg_file.exists():
        try:
            data = json.loads(cfg_file.read_text(encoding="utf-8"))
            if data.get("provider"):
                cfg.provider = data["provider"]
            if data.get("model"):
                cfg.model = data["model"]
            if data.get("api_key"):
                cfg.api_key = data["api_key"]
            if "cloud_opt_in" in data:
                cfg.cloud_opt_in = bool(data["cloud_opt_in"])
            if data.get("custom_endpoint"):
                cfg.custom_endpoint = data["custom_endpoint"]
        except Exception:
            pass

    return cfg


def save_ai_config(config: AIProviderConfig, data_root: Optional[Path] = None) -> Path:
    """Persists AI configuration to .mendex/ai_config.json and updates process environment."""
    cfg_file = get_config_path(data_root)
    cfg_file.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "provider": config.provider,
        "model": config.model,
        "api_key": config.api_key,
        "cloud_opt_in": config.cloud_opt_in,
        "custom_endpoint": config.custom_endpoint,
    }
    cfg_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # Sync to current runtime environment
    if config.provider == "gemini" and config.api_key:
        os.environ["GEMINI_API_KEY"] = config.api_key
    elif config.provider == "openai" and config.api_key:
        os.environ["OPENAI_API_KEY"] = config.api_key

    return cfg_file
