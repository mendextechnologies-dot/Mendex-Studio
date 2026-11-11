"""Mendex Engineering Studio desktop launcher."""
import sys
from pathlib import Path

# Add src to sys.path if not present
src_path = Path(__file__).parent.resolve()
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from mendex_ui.__main__ import main

if __name__ == "__main__":
    main()
