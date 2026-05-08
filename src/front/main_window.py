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

import logging
import os
import traceback
from typing import List, Optional

_log = logging.getLogger("picture.main_window")

import numpy as np

from .qt_compat import (
    Qt,
    QThread,
    pyqtSignal,
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
from ..back.graph_reader import GraphReader, GraphConfig, GRAPH_EXTENSIONS as _GRAPH_EXTS

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

    finished = pyqtSignal(object, object, str)  # (MultiImage|None, source_map|None, error)

    def __init__(self, paths: List[str], graph_config: Optional[GraphConfig] = None):
        super().__init__()
        self._paths = paths
        self._graph_config = graph_config or GraphConfig()

    def run(self):
        try:
            mi = MultiImage()
            source_map: dict = {}
            for p in self._paths:
                ext = os.path.splitext(p)[1].lower()
                start = len(mi)
                _log.debug("_LoadThread: loading '%s' (ext=%s)", p, ext)
                if ext == ".pdf":
                    PdfReader(p, mi)
                elif ext in _GRAPH_EXTS:
                    GraphReader(p, mi, config=self._graph_config)
                else:
                    ImageReader(p, mi)
                source_map[p] = list(range(start, len(mi)))
                _log.debug("_LoadThread: '%s' → %d images", p, len(mi) - start)
            self.finished.emit(mi, source_map, "")
        except Exception:
            tb = traceback.format_exc()
            _log.error("_LoadThread: exception loading files:\n%s", tb)
            self.finished.emit(None, None, tb)


# ------------------------------------------------------------------ #
# MainWindow                                                           #
# ------------------------------------------------------------------ #

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._mi: Optional[MultiImage] = None
        self._mappings = None
        self._source_map: dict = {}
        self._loader: Optional[_LoadThread] = None
        self._graph_config: GraphConfig = GraphConfig()

        self.setWindowTitle("Picture — éditeur d'images")
        self.resize(1400, 720)
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
        t.sig_crop_preview.connect(self._on_crop_preview)
        t.sig_element_selected.connect(self._on_element_selected)
        t.sig_graph_config_changed.connect(self._on_graph_config_changed)
        t.sig_target_changed.connect(self._on_target_changed)

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

        self._loader = _LoadThread(paths, self._graph_config)
        self._loader.finished.connect(self._on_load_finished)
        self._loader.start()

    def _on_load_finished(self, mi: Optional[MultiImage], source_map: Optional[dict], error: str):
        if error:
            self._status.showMessage(f"Erreur : {error.splitlines()[-1]}")
            return
        self._mi = mi
        self._source_map = source_map or {}
        self._mappings = None
        self._update_target_list()
        self._update_graph_columns()
        self._refresh_ui()
        n = len(mi) if mi else 0
        self._status.showMessage(
            f"{n} image(s) chargée(s)." if n > 0 else "Aucune image."
        )

    # ------------------------------------------------------------------ #
    # UI refresh                                                           #
    # ------------------------------------------------------------------ #

    def _refresh_ui(self):
        self._preview.load_multiimage(self._mi)   # efface aussi les overlays
        self._export_bar.set_multiimage(self._mi)
        if self._mi and len(self._mi) > 0:
            target = self._tools.get_target_index()
            ref = target if (target is not None and 0 <= target < len(self._mi)) else 0
            self._tools.update_image_dimensions(self._mi[ref].width, self._mi[ref].height)

    # ------------------------------------------------------------------ #
    # Tool handlers                                                        #
    # ------------------------------------------------------------------ #

    def _guard(self) -> bool:
        """Return True if a MultiImage is available."""
        if not self._mi or len(self._mi) == 0:
            self._status.showMessage("Aucune image chargée.")
            return False
        return True

    def _on_graph_config_changed(self, config: GraphConfig):
        """Re-render graph files when the template changes."""
        self._graph_config = config
        paths = self._file_panel.file_paths()
        graph_paths = [p for p in paths
                       if os.path.splitext(p)[1].lower() in _GRAPH_EXTS]
        if not graph_paths:
            return
        if self._mi and self._source_map:
            try:
                self._partial_graph_reload(graph_paths, config)
                return
            except Exception as e:
                self._status.showMessage(
                    f"Rechargement partiel échoué ({e}), rechargement complet…"
                )
        self._on_files_changed(paths)

    def _partial_graph_reload(self, graph_paths: List[str], config: GraphConfig):
        """Re-render only graph images, preserving manually edited non-graph images."""
        replacements: dict = {}
        for gp in graph_paths:
            indices = self._source_map.get(gp, [])
            if not indices:
                continue
            tmp = MultiImage()
            GraphReader(gp, tmp, config=config)
            if len(tmp) != len(indices):
                raise ValueError(
                    f"Nombre d'images changé pour '{os.path.basename(gp)}' "
                    f"(attendu {len(indices)}, obtenu {len(tmp)})"
                )
            for local_i, global_i in enumerate(indices):
                replacements[global_i] = tmp[local_i]
        new_mi = MultiImage()
        for i, img in enumerate(self._mi):
            new_mi.add_image(replacements.get(i, img))
        self._mi = new_mi
        self._mappings = None
        self._refresh_ui()
        self._status.showMessage("Graphiques rechargés (modifications préservées).")

    def _update_graph_columns(self):
        """Collect column names from all loaded graph files and populate the X combo."""
        all_cols: List[str] = []
        for path in self._source_map:
            if os.path.splitext(path)[1].lower() in _GRAPH_EXTS:
                try:
                    for col in GraphReader.read_columns(path):
                        if col not in all_cols:
                            all_cols.append(col)
                except Exception:
                    pass
        self._tools.update_graph_columns(all_cols)

    def _update_target_list(self):
        """Rebuild the image target selector in ToolsPanel."""
        if not self._mi or len(self._mi) == 0:
            self._tools.update_target_list([])
            return
        idx_to_source: dict = {}
        for path, indices in self._source_map.items():
            fname = os.path.basename(path)
            for i in indices:
                idx_to_source[i] = fname
        labels = []
        for i in range(len(self._mi)):
            fname = idx_to_source.get(i, "")
            labels.append(f"Image #{i}  —  {fname}" if fname else f"Image #{i}")
        self._tools.update_target_list(labels)

    def _scoped_op(self, method: str, *args) -> MultiImage:
        """Apply a MultiImage batch method to all images or only the selected target."""
        target = self._tools.get_target_index()
        if target is None:
            return getattr(self._mi, method)(*args)
        tmp = MultiImage()
        tmp.add_image(self._mi[target])
        result = getattr(tmp, method)(*args)
        new_mi = MultiImage()
        for i, img in enumerate(self._mi):
            new_mi.add_image(result[0] if i == target else img)
        return new_mi

    def _scoped_categorize(self, threshold: float) -> list:
        """Run categorize_by_color scoped to the target, returning a full-length list."""
        target = self._tools.get_target_index()
        if target is None:
            return self._mi.categorize_by_color(threshold)
        tmp = MultiImage()
        tmp.add_image(self._mi[target])
        [single_mapping] = tmp.categorize_by_color(threshold)
        full_mappings = [{} for _ in range(len(self._mi))]
        full_mappings[target] = single_mapping
        return full_mappings

    def _on_target_changed(self, idx):
        """Called when the user changes the target image selector."""
        self._mappings = None  # stale; force re-categorize
        self._preview.clear_element_highlight()
        if self._mi and len(self._mi) > 0:
            ref = idx if (idx is not None and 0 <= idx < len(self._mi)) else 0
            self._tools.update_image_dimensions(self._mi[ref].width, self._mi[ref].height)

    def _on_crop_preview(self, x: int, y: int, w: int, h: int):
        """Affiche l'overlay de rognage en temps réel."""
        if self._mi and len(self._mi) > 0:
            target = self._tools.get_target_index()
            self._preview.show_crop_overlay(x, y, w, h, target)

    def _on_element_selected(self, elem_id):
        """Met en évidence les pixels de l'élément sélectionné."""
        if elem_id is None or not self._mappings or not self._mi:
            self._preview.clear_element_highlight()
            return
        masks = []
        for i, img in enumerate(self._mi):
            m = self._mappings[i] if i < len(self._mappings) else {}
            if elem_id in m:
                ih, iw = img.pixels.shape[:2]
                mask = np.zeros((ih, iw), dtype=bool)
                pix_list = m[elem_id]["pixels"]
                if len(pix_list) > 0:
                    rows, cols = zip(*pix_list)
                    mask[rows, cols] = True
                masks.append(mask)
            else:
                masks.append(None)
        self._preview.show_element_highlight(masks)

    def _apply_compress(self, level: int):
        if not self._guard(): return
        try:
            self._mi = self._scoped_op("compress", level)
            self._mappings = None
            self._refresh_ui()
            target = self._tools.get_target_index()
            scope = f"image #{target}" if target is not None else "toutes les images"
            self._status.showMessage(f"Compression {level} appliquée ({scope}).")
        except Exception as e:
            self._status.showMessage(f"Erreur compression : {e}")

    def _apply_to_rgba(self):
        if not self._guard(): return
        try:
            self._mi = self._scoped_op("to_rgba")
            self._mappings = None
            self._refresh_ui()
            target = self._tools.get_target_index()
            scope = f"image #{target}" if target is not None else "toutes les images"
            self._status.showMessage(f"Converti en RGBA ({scope}).")
        except Exception as e:
            self._status.showMessage(f"Erreur RGBA : {e}")

    def _apply_make_transparent(self, color: tuple, threshold: float):
        if not self._guard(): return
        try:
            self._mi = self._scoped_op("make_color_transparent", color, threshold)
            self._mappings = None
            self._refresh_ui()
            target = self._tools.get_target_index()
            scope = f"image #{target}" if target is not None else "toutes les images"
            self._status.showMessage(
                f"Couleur {color} rendue transparente (seuil {threshold}, {scope})."
            )
        except Exception as e:
            self._status.showMessage(f"Erreur transparence : {e}")

    def _apply_categorize(self, threshold: float):
        if not self._guard(): return
        try:
            self._mappings = self._scoped_categorize(threshold)
            self._tools.populate_elements(self._mappings)
            target = self._tools.get_target_index()
            ref = target if (target is not None and target < len(self._mappings)) else 0
            n = len(self._mappings[ref]) if self._mappings else 0
            scope = f"image #{target}" if target is not None else "toutes les images"
            self._status.showMessage(f"{n} éléments détectés ({scope}).")
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
            target = self._tools.get_target_index()
            scope = f"image #{target}" if target is not None else "toutes les images"
            self._status.showMessage(f"Élément #{elem_id} recolóré en {color} ({scope}).")
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
            target = self._tools.get_target_index()
            scope = f"image #{target}" if target is not None else "toutes les images"
            self._status.showMessage(f"Élément #{elem_id} rendu transparent ({scope}).")
        except Exception as e:
            self._status.showMessage(f"Erreur transparence élément : {e}")

    def _apply_crop(self, x: int, y: int, w: int, h: int):
        if not self._guard(): return
        try:
            self._mi = self._scoped_op("crop", x, y, w, h)
            self._mappings = None
            self._refresh_ui()
            target = self._tools.get_target_index()
            scope = f"image #{target}" if target is not None else "toutes les images"
            self._status.showMessage(f"Rogné : x={x} y={y} {w}×{h} ({scope}).")
        except Exception as e:
            self._status.showMessage(f"Erreur rognage : {e}")
