"""
main.py – application entry point.

Usage
-----
    python main.py

Missing dependencies (PyQt6, Pillow, NumPy, PyMuPDF) are detected and
installed automatically on first run via src/install.py.
"""
import logging
import os
import sys
from pathlib import Path


def _setup_logging() -> None:
    """Configure logging to a file next to the executable (or project root)."""
    if getattr(sys, "frozen", False):
        # cx_Freeze / PyInstaller – write log next to the .exe
        log_dir = Path(sys.executable).parent
    else:
        log_dir = Path(__file__).parent

    log_path = log_dir / "Picture_debug.log"

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    log = logging.getLogger("picture")
    log.info("=" * 60)
    log.info("Picture startup")
    log.info("  log file   : %s", log_path)
    log.info("  executable : %s", sys.executable)
    log.info("  frozen     : %s", getattr(sys, "frozen", False))
    log.info("  Python     : %s", sys.version)
    log.info("  sys.path   : %s", sys.path)

    # Probe pymupdf/fitz availability and log details
    try:
        import pymupdf
        log.info("  pymupdf    : %s at %s", pymupdf.__version__, pymupdf.__file__)
    except Exception as exc:
        log.error("  pymupdf import FAILED: %s", exc, exc_info=True)

    try:
        import fitz
        log.info("  fitz       : %s at %s", getattr(fitz, "__version__", "?"), fitz.__file__)
    except Exception as exc:
        log.error("  fitz import FAILED: %s", exc, exc_info=True)

    try:
        import numpy
        log.info("  numpy      : %s at %s", numpy.__version__, numpy.__file__)
    except Exception as exc:
        log.error("  numpy import FAILED: %s", exc, exc_info=True)

    try:
        import pandas
        log.info("  pandas     : %s at %s", pandas.__version__, pandas.__file__)
    except Exception as exc:
        log.error("  pandas import FAILED: %s", exc, exc_info=True)

    log.info("=" * 60)


_setup_logging()

# ── dependency check (must run before any third-party import) ─────
from src.install import ensure_dependencies
ensure_dependencies()
# ──────────────────────────────────────────────────────────────────

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from src.front.main_window import MainWindow


def _app_icon() -> QIcon:
    """Return the application icon, resolving path for both frozen and dev runs."""
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
    for name in ("icon.ico", "icon.png"):
        p = base / "assets" / name
        if p.exists():
            return QIcon(str(p))
    return QIcon()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Picture")
    app.setApplicationDisplayName("Picture")
    app.setWindowIcon(_app_icon())

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
