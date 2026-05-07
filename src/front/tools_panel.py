"""
tools_panel.py – right panel.

Groups all MultiImage operations into collapsible QGroupBox sections:
  1. Compress
  2. Convert to RGBA
  3. Make colour transparent
  4. Elements (categorise → recolour / make transparent)
  5. Crop

Each section emits a signal that the MainWindow connects to its
MultiImage mutation slot.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


# ------------------------------------------------------------------ #
# Small helper: colour picker button                                   #
# ------------------------------------------------------------------ #

class _ColorButton(QPushButton):
    """Square button that shows a colour and opens a QColorDialog on click."""

    color_changed = pyqtSignal(QColor)

    def __init__(self, initial: QColor = QColor(255, 255, 255), parent=None):
        super().__init__(parent)
        self.setFixedSize(28, 28)
        self._color = initial
        self._refresh()
        self.clicked.connect(self._pick)

    def _refresh(self):
        c = self._color
        self.setStyleSheet(
            f"background-color: rgb({c.red()},{c.green()},{c.blue()});"
            "border: 2px solid #45475a; border-radius: 4px;"
        )

    def _pick(self):
        col = QColorDialog.getColor(self._color, self, "Choisir une couleur")
        if col.isValid():
            self._color = col
            self._refresh()
            self.color_changed.emit(col)

    def color(self) -> QColor:
        return self._color

    def set_color(self, c: QColor):
        self._color = c
        self._refresh()


# ------------------------------------------------------------------ #
# ToolsPanel                                                           #
# ------------------------------------------------------------------ #

class ToolsPanel(QWidget):
    """Right panel – all MultiImage operations."""

    # Signals consumed by MainWindow
    sig_compress            = pyqtSignal(int)             # compression_level
    sig_to_rgba             = pyqtSignal()
    sig_make_transparent    = pyqtSignal(tuple, float)    # (r,g,b), threshold
    sig_categorize          = pyqtSignal(float)           # threshold
    sig_recolor_element     = pyqtSignal(int, tuple)      # element_id, (r,g,b)
    sig_transparent_element = pyqtSignal(int)             # element_id
    sig_crop                = pyqtSignal(int, int, int, int)  # x,y,w,h

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mappings: Optional[List[Dict]] = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        title = QLabel("OUTILS")
        title.setObjectName("section_title")
        title.setContentsMargins(8, 8, 8, 4)
        root.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(8, 8, 8, 8)
        inner_layout.setSpacing(10)

        inner_layout.addWidget(self._build_compress())
        inner_layout.addWidget(self._build_to_rgba())
        inner_layout.addWidget(self._build_make_transparent())
        inner_layout.addWidget(self._build_elements())
        inner_layout.addWidget(self._build_crop())
        inner_layout.addStretch()

        scroll.setWidget(inner)
        root.addWidget(scroll, stretch=1)

    # ------------------------------------------------------------------ #
    # Section builders                                                     #
    # ------------------------------------------------------------------ #

    def _build_compress(self) -> QGroupBox:
        box = QGroupBox("Compression")
        layout = QFormLayout(box)
        layout.setSpacing(8)

        self._compress_combo = QComboBox()
        _levels = [4, 9, 16, 25, 36, 49, 64]
        for lvl in _levels:
            import math
            s = int(math.isqrt(lvl))
            self._compress_combo.addItem(f"{s}×{s}  (niveau {lvl})", lvl)
        layout.addRow("Bloc :", self._compress_combo)

        btn = QPushButton("Compresser")
        btn.setObjectName("accent")
        btn.clicked.connect(self._emit_compress)
        layout.addRow(btn)
        return box

    def _build_to_rgba(self) -> QGroupBox:
        box = QGroupBox("Espace colorimétrique")
        layout = QVBoxLayout(box)
        self._btn_to_rgba = QPushButton("Convertir en RGBA")
        self._btn_to_rgba.setObjectName("accent")
        self._btn_to_rgba.clicked.connect(self.sig_to_rgba.emit)
        layout.addWidget(self._btn_to_rgba)
        return box

    def _build_make_transparent(self) -> QGroupBox:
        box = QGroupBox("Rendre une couleur transparente")
        form = QFormLayout(box)
        form.setSpacing(8)

        self._transp_color_btn = _ColorButton(QColor(255, 255, 255))
        form.addRow("Couleur :", self._transp_color_btn)

        self._transp_threshold = QDoubleSpinBox()
        self._transp_threshold.setRange(0.0, 441.0)   # max √(255²×3)
        self._transp_threshold.setValue(30.0)
        self._transp_threshold.setSingleStep(5.0)
        self._transp_threshold.setDecimals(1)
        self._transp_threshold.setSuffix("  distance")
        form.addRow("Seuil :", self._transp_threshold)

        btn = QPushButton("Appliquer")
        btn.setObjectName("accent")
        btn.clicked.connect(self._emit_make_transparent)
        form.addRow(btn)
        return box

    def _build_elements(self) -> QGroupBox:
        box = QGroupBox("Éléments (catégorisation)")
        layout = QVBoxLayout(box)
        layout.setSpacing(8)

        form = QFormLayout()
        self._cat_threshold = QDoubleSpinBox()
        self._cat_threshold.setRange(0.0, 441.0)
        self._cat_threshold.setValue(30.0)
        self._cat_threshold.setSingleStep(5.0)
        self._cat_threshold.setDecimals(1)
        self._cat_threshold.setSuffix("  distance")
        form.addRow("Seuil :", self._cat_threshold)
        layout.addLayout(form)

        btn_detect = QPushButton("Détecter les éléments")
        btn_detect.clicked.connect(self._emit_categorize)
        layout.addWidget(btn_detect)

        self._elem_list = QListWidget()
        self._elem_list.setMinimumHeight(100)
        self._elem_list.setMaximumHeight(160)
        layout.addWidget(self._elem_list)

        # recolour row
        recolor_row = QHBoxLayout()
        self._recolor_btn_color = _ColorButton(QColor(200, 50, 50))
        recolor_row.addWidget(self._recolor_btn_color)
        btn_recolor = QPushButton("Recolorer")
        btn_recolor.clicked.connect(self._emit_recolor)
        recolor_row.addWidget(btn_recolor, stretch=1)
        layout.addLayout(recolor_row)

        btn_transp_elem = QPushButton("Rendre transparent")
        btn_transp_elem.clicked.connect(self._emit_transparent_element)
        layout.addWidget(btn_transp_elem)

        return box

    def _build_crop(self) -> QGroupBox:
        box = QGroupBox("Rogner")
        form = QFormLayout(box)
        form.setSpacing(8)

        self._crop_x = QSpinBox(); self._crop_x.setRange(0, 99999)
        self._crop_y = QSpinBox(); self._crop_y.setRange(0, 99999)
        self._crop_w = QSpinBox(); self._crop_w.setRange(1, 99999); self._crop_w.setValue(100)
        self._crop_h = QSpinBox(); self._crop_h.setRange(1, 99999); self._crop_h.setValue(100)

        form.addRow("X :", self._crop_x)
        form.addRow("Y :", self._crop_y)
        form.addRow("Largeur :", self._crop_w)
        form.addRow("Hauteur :", self._crop_h)

        btn = QPushButton("Rogner")
        btn.setObjectName("accent")
        btn.clicked.connect(self._emit_crop)
        form.addRow(btn)
        return box

    # ------------------------------------------------------------------ #
    # Emit helpers                                                         #
    # ------------------------------------------------------------------ #

    def _emit_compress(self):
        lvl = self._compress_combo.currentData()
        self.sig_compress.emit(lvl)

    def _emit_make_transparent(self):
        c = self._transp_color_btn.color()
        self.sig_make_transparent.emit(
            (c.red(), c.green(), c.blue()),
            self._transp_threshold.value(),
        )

    def _emit_categorize(self):
        self.sig_categorize.emit(self._cat_threshold.value())

    def _emit_recolor(self):
        row = self._elem_list.currentRow()
        if row < 0:
            return
        elem_id = self._elem_list.item(row).data(Qt.ItemDataRole.UserRole)
        c = self._recolor_btn_color.color()
        self.sig_recolor_element.emit(elem_id, (c.red(), c.green(), c.blue()))

    def _emit_transparent_element(self):
        row = self._elem_list.currentRow()
        if row < 0:
            return
        elem_id = self._elem_list.item(row).data(Qt.ItemDataRole.UserRole)
        self.sig_transparent_element.emit(elem_id)

    def _emit_crop(self):
        self.sig_crop.emit(
            self._crop_x.value(),
            self._crop_y.value(),
            self._crop_w.value(),
            self._crop_h.value(),
        )

    # ------------------------------------------------------------------ #
    # Public helpers called by MainWindow                                  #
    # ------------------------------------------------------------------ #

    def update_image_dimensions(self, width: int, height: int):
        """Clamp crop spinboxes to image dimensions."""
        self._crop_x.setMaximum(max(0, width - 1))
        self._crop_y.setMaximum(max(0, height - 1))
        self._crop_w.setMaximum(width)
        self._crop_h.setMaximum(height)
        self._crop_w.setValue(width)
        self._crop_h.setValue(height)

    def populate_elements(self, mappings: List[Dict]):
        """Fill the element list from *mappings*."""
        self._mappings = mappings
        self._elem_list.clear()
        if not mappings:
            return
        # Aggregate across all images: element ids present in ALL mappings
        all_ids: set = set(mappings[0].keys())
        for m in mappings[1:]:
            all_ids &= set(m.keys())
        for eid in sorted(all_ids):
            # average colour from first image's mapping
            avg = mappings[0][eid]["average_color"]
            r, g, b = int(avg[0]), int(avg[1]), int(avg[2])
            n_pixels = sum(len(m[eid]["pixels"]) for m in mappings if eid in m)
            item = QListWidgetItem(
                f"  Élément #{eid}   RGB({r},{g},{b})   {n_pixels} px"
            )
            item.setData(Qt.ItemDataRole.UserRole, eid)
            # colour swatch via foreground
            item.setForeground(QColor(r, g, b))
            self._elem_list.addItem(item)
