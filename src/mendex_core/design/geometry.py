"""Shared PCB geometry API (structural KiCad 8/9/10 reader)."""
from .native_geometry import extract_pcb_geometry

__all__ = ["extract_pcb_geometry"]
