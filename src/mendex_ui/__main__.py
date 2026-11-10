import argparse
from pathlib import Path
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from mendex_core.service import StudioService
from .window import StudioWindow


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--smoke-test", action="store_true", help="Launch and close automatically for local verification")
    args = parser.parse_args()
    app = QApplication(sys.argv)
    app.setApplicationName("Mendex Engineering Studio")
    window = StudioWindow(StudioService(args.root))
    window.show()
    if args.smoke_test:
        QTimer.singleShot(300, app.quit)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
