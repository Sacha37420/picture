"""
main.py – application entry point.

Usage
-----
    python main.py

Missing dependencies (PyQt6, Pillow, NumPy, PyMuPDF) are detected and
installed automatically on first run via src/install.py.
"""
import sys

# ── dependency check (must run before any third-party import) ─────
from src.install import ensure_dependencies
ensure_dependencies()
# ──────────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import QApplication

from src.front.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Picture")
    app.setApplicationDisplayName("Picture")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
