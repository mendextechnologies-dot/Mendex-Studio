"""Executable entry point for Mendex MCP Server.

Usage:
  python -m mendex_core.mcp [--root DATA_ROOT]
"""
import argparse
from pathlib import Path
import sys

from .server import MendexMCPServer


def main(argv=None):
    parser = argparse.ArgumentParser(description="Mendex Standard Model Context Protocol (MCP) Server")
    parser.add_argument("--root", type=Path, default=None, help="Path to Mendex data root (default: Mendex project root or MENDEX_DATA_ROOT)")
    args = parser.parse_args(argv)

    server = MendexMCPServer(data_root=args.root)
    try:
        server.run_stdio()
        return 0
    except (KeyboardInterrupt, BrokenPipeError):
        return 0


if __name__ == "__main__":
    sys.exit(main())
