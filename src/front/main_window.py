"""
main_window.py – application main window.

Layout
------
┌─────────────────────────────────────────────────────────────────────┐
│  [FileListPanel │ PreviewPanel │ ToolsPanel ]  (QSplitter)          │
├─────────────────────────────────────────────────────────────────────┤
│  ExportBar                                                          │
│  StatusBar                                                          │
└─────────────────────────────────────────────────────────────────────┘

The MainWindow owns the master MultiImage.  Any change to the file list
triggers a full reload; any tool operation mutates the master MultiImage
in place (cumulative), then refreshes the preview.
"""
from __future__ import annotations

import os
import traceback
from typing import List, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QMainWindow,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ..back.image_reader import ImageReader
from ..back.multiimage import MultiImage
from ..back.pdf_reader import PdfReader

from .export_bar import ExportBar
from .file_list_panel import FileListPanel
from .preview_panel import PreviewPanel
from .styles import MAIN_STYLE
from .tools_panel import ToolsPanel


# ------------------------------------------------------------------ #
# Background loader thread                                             #
# ------------------------------------------------------------------ #

class _LoadThread(QThread):
    """Load a list of files into a MultiImage in a worker thread."""

    finished = pyqtSignal(object, str)   # (MultiImage | None, error_msg)

    def __init__(self, paths: List[str]):
        super().__init__()
        self._paths = paths

    def run(self):
        try:
            mi = MultiImage()
            for p in self._paths:
                ext = os.path.splitext(p)[1].lower()
                if ext == ".pdf":
                    PdfReader(p, mi)
                else:
                    ImageReader(p, mi)
            self.finished.emit(mi, "")
        except Exception as exc:
            self.finished.emit(None, traceback.format_exc())


# ------------------------------------------------------------------ #
# MainWindow                                                           #
# ------------------------------------------------------------------ #

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._mi: Optional[MultiImage] = None
        self._mappings = None
        self._loader: Optional[_LoadThread] = None

        self.setWindowTitle("Picture — éditeur d'images")
        self.resize(1400, 820)
        self.setMinimumSize(900, 600)
        self.setStyleSheet(MAIN_STYLE)

        self._build_ui()

    # ------------------------------------------------------------------ #
    # UI construction                                                      #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 4)
        root.setSpacing(6)

        # ── main splitter ──────────────────────────────────────────── #
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Left
        self._file_panel = FileListPanel()
        self._file_panel.setMinimumWidth(180)
        self._file_panel.setMaximumWidth(320)
        self._file_panel.files_changed.connect(self._on_files_changed)
        splitter.addWidget(self._wrap_panel(self._file_panel))

        # Centre
        self._preview = PreviewPanel()
        self._preview.setMinimumWidth(300)
        splitter.addWidget(self._wrap_panel(self._preview))

        # Right
        self._tools = ToolsPanel()
        self._tools.setMinimumWidth(220)
        self._tools.setMaximumWidth(360)
        self._connect_tools()
        splitter.addWidget(self._wrap_panel(self._tools))

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        root.addWidget(splitter, stretch=1)

        # ── export bar ────────────────────────────────────────────── #
        self._export_bar = ExportBar()
        root.addWidget(self._export_bar)

        # ── status bar ────────────────────────────────────────────── #
        self._status = QStatusBar()
        self._status.setStyleSheet(
            "QStatusBar { color: #a6e3a1; font-size: 11px; }"
        )
        self.setStatusBar(self._status)
        self._status.showMessage("Prêt.")

    @staticmethod
    def _wrap_panel(widget: QWidget) -> QFrame:
        frame = QFrame()
        frame.setObjectName("panel")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(widget)
        return frame

    # ------------------------------------------------------------------ #
    # Tool signal wiring                                                   #
    # ------------------------------------------------------------------ #

    def _connect_tools(self):
        t = self._tools
        t.sig_compress.connect(self._apply_compress)
        t.sig_to_rgba.connect(self._apply_to_rgba)
        t.sig_make_transparent.connect(self._apply_make_transparent)
        t.sig_categorize.connect(self._apply_categorize)
        t.sig_recolor_element.connect(self._apply_recolor)
        t.sig_transparent_element.connect(self._apply_transparent_element)
        t.sig_crop.connect(self._apply_crop)

    # ------------------------------------------------------------------ #
    # File list → reload                                                   #
    # ------------------------------------------------------------------ #

    def _on_files_changed(self, paths: List[str]):
        if not paths:
            self._mi = None
            self._mappings = None
            self._refresh_ui()
            return

        self._status.showMessage("Chargement en cours…")
        # cancel any running loader
        if self._loader and self._loader.isRunning():
            self._loader.quit()
            self._loader.wait()

        self._loader = _LoadThread(paths)
        self._loader.finished.connect(self._on_load_finished)
        self._loader.start()

    def _on_load_finished(self, mi: Optional[MultiImage], error: str):
        if error:
            self._status.showMessage(f"Erreur : {error.splitlines()[-1]}")
            return
        self._mi = mi
        self._mappings = None
        self._refresh_ui()
        n = len(mi) if mi else 0
        self._status.showMessage(
            f"{n} image(s) chargée(s)." if n > 0 else "Aucune image."
        )

    # ------------------------------------------------------------------ #
    # UI refresh                                                           #
    # ------------------------------------------------------------------ #

    def _refresh_ui(self):
        self._preview.load_multiimage(self._mi)
        self._export_bar.set_multiimage(self._mi)
        if self._mi and len(self._mi) > 0:
            img0 = self._mi[0]
            self._tools.update_image_dimensions(img0.width, img0.height)

    # ------------------------------------------------------------------ #
    # Tool handlers                                                        #
    # ------------------------------------------------------------------ #

    def _guard(self) -> bool:
        """Return True if a MultiImage is available."""
        if not self._mi or len(self._mi) == 0:
            self._status.showMessage("Aucune image chargée.")
            return False
        return True

    def _apply_compress(self, level: int):
        if not self._guard(): return
        try:
            self._mi = self._mi.compress(level)
            self._mappings = None
            self._refresh_ui()
            self._status.showMessage(f"Compression {level} appliquée.")
        except Exception as e:
            self._status.showMessage(f"Erreur compression : {e}")

    def _apply_to_rgba(self):
        if not self._guard(): return
        try:
            self._mi = self._mi.to_rgba()
            self._mappings = None
            self._refresh_ui()
            self._status.showMessage("Converti en RGBA.")
        except Exception as e:
            self._status.showMessage(f"Erreur RGBA : {e}")

    def _apply_make_transparent(self, color: tuple, threshold: float):
        if not self._guard(): return
        try:
            self._mi = self._mi.make_color_transparent(color, threshold)
            self._mappings = None
            self._refresh_ui()
            self._status.showMessage(
                f"Couleur {color} rendue transparente (seuil {threshold})."
            )
        except Exception as e:
            self._status.showMessage(f"Erreur transparence : {e}")

    def _apply_categorize(self, threshold: float):
        if not self._guard(): return
        try:
            self._mappings = self._mi.categorize_by_color(threshold)
            self._tools.populate_elements(self._mappings)
            n = len(self._mappings[0]) if self._mappings else 0
            self._status.showMessage(f"{n} éléments détectés.")
        except Exception as e:
            self._status.showMessage(f"Erreur catégorisation : {e}")

    def _apply_recolor(self, elem_id: int, color: tuple):
        if not self._guard(): return
        if not self._mappings:
            self._status.showMessage("Lancez d'abord la détection des éléments.")
            return
        try:
            self._mi = self._mi.recolor_element(self._mappings, elem_id, list(color))
            self._refresh_ui()
            self._status.showMessage(f"Élément #{elem_id} recoloré en {color}.")
        except Exception as e:
            self._status.showMessage(f"Erreur recoloration : {e}")

    def _apply_transparent_element(self, elem_id: int):
        if not self._guard(): return
        if not self._mappings:
            self._status.showMessage("Lancez d'abord la détection des éléments.")
            return
        try:
            self._mi = self._mi.make_element_transparent(self._mappings, elem_id)
            self._refresh_ui()
            self._status.showMessage(f"Élément #{elem_id} rendu transparent.")
        except Exception as e:
            self._status.showMessage(f"Erreur transparence élément : {e}")

    def _apply_crop(self, x: int, y: int, w: int, h: int):
        if not self._guard(): return
        try:
            self._mi = self._mi.crop(x, y, w, h)
            self._mappings = None
            self._refresh_ui()
            self._status.showMessage(f"Rogné : x={x} y={y} {w}×{h}.")
        except Exception as e:
            self._status.showMessage(f"Erreur rognage : {e}")
