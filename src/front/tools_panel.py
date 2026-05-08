"""
tools_panel.py – right panel.

Groups all MultiImage operations into collapsible QGroupBox sections:
  1. Compress
  2. Convert to RGBA
  3. Make colour transparent
  4. Elements (categorise → recolour / make transparent)
  5. Crop
  6. Graphiques – template (style, type, taille, DPI, palette)

Each section emits a signal that the MainWindow connects to its
MultiImage mutation slot.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .qt_compat import (
    Qt,
    pyqtSignal,
    QColor,
    QCheckBox,
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
    sig_compress             = pyqtSignal(int)            # compression_level
    sig_to_rgba              = pyqtSignal()
    sig_make_transparent     = pyqtSignal(tuple, float)   # (r,g,b), threshold
    sig_categorize           = pyqtSignal(float)          # threshold
    sig_recolor_element      = pyqtSignal(int, tuple)     # element_id, (r,g,b)
    sig_transparent_element  = pyqtSignal(int)            # element_id
    sig_crop                 = pyqtSignal(int, int, int, int)  # x,y,w,h
    sig_crop_preview         = pyqtSignal(int, int, int, int)  # x,y,w,h (live)
    sig_element_selected     = pyqtSignal(object)         # int | None
    sig_graph_config_changed = pyqtSignal(object)         # GraphConfig
    sig_target_changed       = pyqtSignal(object)         # int | None

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

        # ── target selector ──────────────────────────────────────── #
        _target_bar = QWidget()
        _tbar_layout = QHBoxLayout(_target_bar)
        _tbar_layout.setContentsMargins(8, 2, 8, 4)
        _tbar_layout.setSpacing(6)
        _tbar_lbl = QLabel("Cible :")
        _tbar_lbl.setStyleSheet("color: #cdd6f4; font-size: 12px;")
        _tbar_layout.addWidget(_tbar_lbl)
        self._target_combo = QComboBox()
        self._target_combo.addItem("Toutes les images", None)
        self._target_combo.setToolTip(
            "Sélectionner une image spécifique.\n"
            "Les opérations ne s\'appliqueront qu\'à la cible choisie."
        )
        self._target_combo.currentIndexChanged.connect(self._on_target_changed)
        _tbar_layout.addWidget(self._target_combo, stretch=1)
        root.addWidget(_target_bar)

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
        inner_layout.addWidget(self._build_graph_settings())
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
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)

        self._compress_combo = QComboBox()
        self._compress_combo.setMaximumWidth(130)
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
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)

        self._transp_color_btn = _ColorButton(QColor(255, 255, 255))
        form.addRow("Couleur :", self._transp_color_btn)

        self._transp_threshold = QDoubleSpinBox()
        self._transp_threshold.setRange(0.0, 441.0)   # max √(255²×3)
        self._transp_threshold.setValue(30.0)
        self._transp_threshold.setSingleStep(5.0)
        self._transp_threshold.setDecimals(1)
        self._transp_threshold.setSuffix("  distance")
        self._transp_threshold.setMaximumWidth(120)
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
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)
        self._cat_threshold = QDoubleSpinBox()
        self._cat_threshold.setRange(0.0, 441.0)
        self._cat_threshold.setValue(30.0)
        self._cat_threshold.setSingleStep(5.0)
        self._cat_threshold.setDecimals(1)
        self._cat_threshold.setSuffix("  distance")
        self._cat_threshold.setMaximumWidth(120)
        form.addRow("Seuil :", self._cat_threshold)
        layout.addLayout(form)

        btn_detect = QPushButton("Détecter les éléments")
        btn_detect.clicked.connect(self._emit_categorize)
        layout.addWidget(btn_detect)

        self._elem_list = QListWidget()
        self._elem_list.setMinimumHeight(100)
        self._elem_list.setMaximumHeight(160)
        self._elem_list.setMinimumWidth(0)
        self._elem_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._elem_list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self._elem_list.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
        )
        layout.addWidget(self._elem_list)

        self._elem_list.currentRowChanged.connect(self._emit_element_selected)

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
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)

        self._crop_x = QSpinBox(); self._crop_x.setRange(0, 99999); self._crop_x.setMaximumWidth(90)
        self._crop_y = QSpinBox(); self._crop_y.setRange(0, 99999); self._crop_y.setMaximumWidth(90)
        self._crop_w = QSpinBox(); self._crop_w.setRange(1, 99999); self._crop_w.setValue(100); self._crop_w.setMaximumWidth(90)
        self._crop_h = QSpinBox(); self._crop_h.setRange(1, 99999); self._crop_h.setValue(100); self._crop_h.setMaximumWidth(90)

        form.addRow("X :", self._crop_x)
        form.addRow("Y :", self._crop_y)
        form.addRow("Largeur :", self._crop_w)
        form.addRow("Hauteur :", self._crop_h)

        for sb in (self._crop_x, self._crop_y, self._crop_w, self._crop_h):
            sb.valueChanged.connect(self._emit_crop_preview)

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

    def _emit_crop_preview(self, _=None):
        self.sig_crop_preview.emit(
            self._crop_x.value(),
            self._crop_y.value(),
            self._crop_w.value(),
            self._crop_h.value(),
        )

    def _emit_element_selected(self, row: int):
        if row < 0:
            self.sig_element_selected.emit(None)
            return
        item = self._elem_list.item(row)
        self.sig_element_selected.emit(
            item.data(Qt.ItemDataRole.UserRole) if item else None
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
                f"#{eid}  RGB({r},{g},{b})  {n_pixels}px"
            )
            item.setData(Qt.ItemDataRole.UserRole, eid)
            # colour swatch via foreground
            item.setForeground(QColor(r, g, b))
            self._elem_list.addItem(item)

    def update_target_list(self, labels: list):
        """Repopulate the image target combo.  labels[i] is the display text for image i."""
        self._target_combo.blockSignals(True)
        prev_idx = self._target_combo.currentIndex()
        self._target_combo.clear()
        self._target_combo.addItem("Toutes les images", None)
        for i, lbl in enumerate(labels):
            self._target_combo.addItem(lbl, i)
        if 0 <= prev_idx < self._target_combo.count():
            self._target_combo.setCurrentIndex(prev_idx)
        else:
            self._target_combo.setCurrentIndex(0)
        self._target_combo.blockSignals(False)

    def get_target_index(self) -> Optional[int]:
        """Return the selected image index, or None for 'Toutes les images'."""
        return self._target_combo.currentData()

    def _on_target_changed(self, _: int = 0):
        self.sig_target_changed.emit(self.get_target_index())

    # ------------------------------------------------------------------ #
    # Graph settings section                                               #
    # ------------------------------------------------------------------ #

    def _build_graph_settings(self) -> QGroupBox:
        from ..back.graph_reader import GRAPH_STYLES, CHART_TYPES, COLORMAPS

        box = QGroupBox("Graphiques – Template")
        form = QFormLayout(box)
        form.setSpacing(8)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)

        # Style
        self._graph_style = QComboBox()
        self._graph_style.addItems(GRAPH_STYLES)
        self._graph_style.setMaximumWidth(150)
        self._graph_style.setToolTip("Style matplotlib appliqué au graphique")
        form.addRow("Style :", self._graph_style)

        # Chart type
        self._graph_type = QComboBox()
        self._graph_type.addItems(CHART_TYPES)
        self._graph_type.setMaximumWidth(150)
        self._graph_type.setToolTip(
            "Type de graphique ('auto' = détection automatique)"
        )
        form.addRow("Type :", self._graph_type)

        # X-axis column
        self._graph_x_col = QComboBox()
        self._graph_x_col.addItem("Auto", None)
        self._graph_x_col.setMaximumWidth(150)
        self._graph_x_col.setToolTip(
            "Colonne utilisée comme abscisse (X).\n"
            "'Auto' laisse le lecteur choisir selon le type de données."
        )
        form.addRow("Abscisse (X) :", self._graph_x_col)

        # Figure size
        self._graph_w = QDoubleSpinBox()
        self._graph_w.setRange(2.0, 40.0)
        self._graph_w.setValue(10.0)
        self._graph_w.setSingleStep(0.5)
        self._graph_w.setSuffix(" po")
        self._graph_w.setMaximumWidth(90)
        self._graph_h = QDoubleSpinBox()
        self._graph_h.setRange(2.0, 40.0)
        self._graph_h.setValue(6.0)
        self._graph_h.setSingleStep(0.5)
        self._graph_h.setSuffix(" po")
        self._graph_h.setMaximumWidth(90)
        size_col = QVBoxLayout()
        size_col.setSpacing(3)
        size_col.setContentsMargins(0, 0, 0, 0)
        for lbl_txt, sp in (("larg.", self._graph_w), ("haut.", self._graph_h)):
            r = QHBoxLayout()
            r.setSpacing(4)
            l = QLabel(lbl_txt)
            l.setFixedWidth(30)
            r.addWidget(l)
            r.addWidget(sp)
            r.addStretch()
            size_col.addLayout(r)
        size_widget = QWidget()
        size_widget.setLayout(size_col)
        form.addRow("Taille :", size_widget)

        # DPI
        self._graph_dpi = QSpinBox()
        self._graph_dpi.setRange(72, 300)
        self._graph_dpi.setValue(150)
        self._graph_dpi.setSingleStep(10)
        self._graph_dpi.setSuffix(" dpi")
        self._graph_dpi.setMaximumWidth(90)
        form.addRow("Résolution :", self._graph_dpi)

        # Colormap / palette
        self._graph_cmap = QComboBox()
        self._graph_cmap.addItems(COLORMAPS)
        self._graph_cmap.setMaximumWidth(150)
        self._graph_cmap.setToolTip("Palette de couleurs pour les séries de données")
        form.addRow("Palette :", self._graph_cmap)

        # Overlap hints
        self._graph_overlap = QCheckBox("Afficher les superpositions")
        self._graph_overlap.setToolTip(
            "Active des aides visuelles quand plusieurs courbes se superposent :\n"
            "• Styles de ligne alternés (plein / tirets / pointillés)\n"
            "• Marqueurs différents espacés sur chaque courbe\n"
            "• Halo semi-transparent derrière chaque tracé\n"
            "• Hachures sur les barres (bar chart)"
        )
        form.addRow(self._graph_overlap)

        # ── Axis limits ────────────────────────────────────────────── #
        def _axis_limit_row(label: str):
            """Return (enable_checkbox, min_spin, max_spin)."""
            cb = QCheckBox("Activer")
            lo = QDoubleSpinBox()
            hi = QDoubleSpinBox()
            for sp in (lo, hi):
                sp.setRange(-1e9, 1e9)
                sp.setDecimals(2)
                sp.setSingleStep(1.0)
                sp.setEnabled(False)
                sp.setMaximumWidth(90)
            cb.toggled.connect(lo.setEnabled)
            cb.toggled.connect(hi.setEnabled)
            # vertical layout: checkbox / min row / max row
            col = QVBoxLayout()
            col.setSpacing(2)
            col.setContentsMargins(0, 0, 0, 0)
            col.addWidget(cb)
            for lbl_txt, sp in (("min", lo), ("max", hi)):
                r = QHBoxLayout()
                r.setSpacing(4)
                lbl = QLabel(lbl_txt)
                lbl.setFixedWidth(24)
                r.addWidget(lbl)
                r.addWidget(sp, stretch=1)
                col.addLayout(r)
            w = QWidget()
            w.setLayout(col)
            form.addRow(label, w)
            return cb, lo, hi

        self._xlim_cb, self._xlim_min, self._xlim_max = _axis_limit_row("Axe X :")
        self._ylim_cb, self._ylim_min, self._ylim_max = _axis_limit_row("Axe Y :")

        # Connect all widgets → emit config on every change
        for w in (self._graph_style, self._graph_type, self._graph_cmap,
                  self._graph_x_col):
            w.currentTextChanged.connect(self._emit_graph_config)
        for w in (self._graph_w, self._graph_h,
                  self._xlim_min, self._xlim_max,
                  self._ylim_min, self._ylim_max):
            w.valueChanged.connect(self._emit_graph_config)
        self._graph_dpi.valueChanged.connect(self._emit_graph_config)
        self._graph_overlap.checkStateChanged.connect(self._emit_graph_config)
        self._xlim_cb.toggled.connect(self._emit_graph_config)
        self._ylim_cb.toggled.connect(self._emit_graph_config)

        return box

    def _emit_graph_config(self, *_):
        self.sig_graph_config_changed.emit(self.get_graph_config())

    def get_graph_config(self):
        """Return the current :class:`GraphConfig` from the UI state."""
        from ..back.graph_reader import GraphConfig
        return GraphConfig(
            chart_type    = self._graph_type.currentText(),
            style         = self._graph_style.currentText(),
            figsize       = (self._graph_w.value(), self._graph_h.value()),
            dpi           = self._graph_dpi.value(),
            colormap      = self._graph_cmap.currentText(),
            overlap_hints = self._graph_overlap.isChecked(),
            x_col         = self._graph_x_col.currentData(),
            x_min         = self._xlim_min.value() if self._xlim_cb.isChecked() else None,
            x_max         = self._xlim_max.value() if self._xlim_cb.isChecked() else None,
            y_min         = self._ylim_min.value() if self._ylim_cb.isChecked() else None,
            y_max         = self._ylim_max.value() if self._ylim_cb.isChecked() else None,
        )

    def update_graph_columns(self, columns: list):
        """Populate the X-axis column combo with *columns*."""
        self._graph_x_col.blockSignals(True)
        prev = self._graph_x_col.currentData()  # preserve current selection
        self._graph_x_col.clear()
        self._graph_x_col.addItem("Auto", None)
        for col in columns:
            self._graph_x_col.addItem(str(col), str(col))
        # Restore previous selection if still present
        if prev is not None:
            idx = self._graph_x_col.findData(prev)
            if idx >= 0:
                self._graph_x_col.setCurrentIndex(idx)
        self._graph_x_col.blockSignals(False)

