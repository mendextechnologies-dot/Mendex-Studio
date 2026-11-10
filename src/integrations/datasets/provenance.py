from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field


class DatasetMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    dataset_id: str
    name: str
    version: str
    description: str
    license_name: str
    source_url: str
    citation: str
    expected_sha256: str
    record_count: int = 0
    verified: bool = False
    imported_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def verify_dataset_file(file_path: Path, expected_sha256: str) -> bool:
    """Computes SHA-256 and compares to expected checksum."""
    if not file_path.exists() or not file_path.is_file():
        return False
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().lower() == expected_sha256.lower()
