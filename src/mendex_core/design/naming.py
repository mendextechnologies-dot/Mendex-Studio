"""Filesystem naming and sanitization utilities for Mendex Studio.

Ensures generated CAD, netlist, and report filenames are safe, deterministic,
and compliant across Windows (NTFS) and POSIX filesystems without Errno 22.
"""
from __future__ import annotations

import re


def sanitize_filename(name: str, fallback: str = "circuit_design") -> str:
    """Sanitizes an arbitrary title, label or user input into a safe filesystem filename.

    Guarantees compatibility across Windows and POSIX:
    - Strips control characters, newlines, CR, tabs.
    - Translates common engineering symbols (e.g., '→' to 'to', '@' to 'at').
    - Replaces any non-alphanumeric character (except '-' and '_') with '_'.
    - Collapses consecutive underscores.
    - Strips leading and trailing underscores and hyphens.
    - Limits length to 48 characters.
    - Defaults to `fallback` if empty.
    """
    if not name:
        return fallback

    text = str(name).strip()
    # Replace control characters and newlines with spaces
    text = re.sub(r"[\r\n\t\x00-\x1f]+", " ", text).strip()
    # Normalize common symbols
    text = text.replace("→", "to").replace("->", "to").replace("@", "at").replace("&", "and")
    # Replace any character that is not alphanumeric, hyphen, or underscore
    text = re.sub(r"[^a-zA-Z0-9_\-]+", "_", text)
    # Collapse multiple underscores
    text = re.sub(r"_+", "_", text).strip("_-")

    clean = text[:48].rstrip("_-").lower()
    return clean if clean else fallback


def clean_title(title: str, fallback: str = "Untitled Design") -> str:
    """Cleans human-readable title of newlines, tabs, and non-ASCII arrow characters."""
    if not title:
        return fallback
    text = str(title).replace("→", "->").replace("←", "<-")
    cleaned = " ".join(re.sub(r"[\r\n\t\x00-\x1f]+", " ", text).split()).strip()
    return cleaned if cleaned else fallback
