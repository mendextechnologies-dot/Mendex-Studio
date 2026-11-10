"""Documented standalone diagnostics entry point."""
import sys

from .cli import main


if __name__ == "__main__":
    sys.exit(main(["doctor", *sys.argv[1:]]))
