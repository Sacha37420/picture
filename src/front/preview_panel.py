"""
preview_panel.py – centre panel.

Scrollable vertical strip showing every image in the current MultiImage.
Each image is rendered as a thumbnail that fills the panel width while
preserving the aspect ratio.  A label under each thumbnail shows its
index, dimensions and channel count.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import numpy as np

from ..back.multiimage import MultiImage


def _array_to_pixmap(pixels: np.ndarray) -> QPixmap:
    """Convert an (H, W, C) uint8 array to a QPixmap."""
    h, w, c = pixels.shape
    if c == 1:
        # greyscale → replicate to RGB
        pixels = np.repeat(pixels, 3, axis=2)
        c = 3
    if c == 3:
        fmt = QImage.Format.Format_RGB888
        bytes_per_line = w * 3
    elif c == 4:
        fmt = QImage.Format.Format_RGBA8888
        bytes_per_line = w * 4
    else:
        return QPixmap()
    img = QImage(pixels.tobytes(), w, h, bytes_per_line, fmt)
    return QPixmap.fromImage(img)


class _ImageCard(QWidget):
    """Thumbnail + info label for one image."""

    def __init__(self, index: int, pixels: np.ndarray, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self._pixmap_orig = _array_to_pixmap(pixels)

        self._img_label = QLabel()
        self._img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        layout.addWidget(self._img_label)

        h, w, c = pixels.shape
        info = QLabel(f"#{index}  {w}×{h}  {'RGBA' if c==4 else 'RGB' if c==3 else 'L'}")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet("color: #6c7086; font-size: 11px;")
        layout.addWidget(info)

    def set_width(self, width: int):
        """Scale the thumbnail to *width* pixels."""
        if self._pixmap_orig.isNull():
            return
        scaled = self._pixmap_orig.scaledToWidth(
            width, Qt.TransformationMode.SmoothTransformation
        )
        self._img_label.setPixmap(scaled)


class PreviewPanel(QWidget):
    """Scrollable strip showing all images in the MultiImage."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: list[_ImageCard] = []
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        title = QLabel("APERÇU")
        title.setObjectName("section_title")
        title.setContentsMargins(8, 8, 8, 4)
        root.addWidget(title)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self._container = QWidget()
        self._v_layout = QVBoxLayout(self._container)
        self._v_layout.setContentsMargins(4, 4, 4, 4)
        self._v_layout.setSpacing(12)
        self._v_layout.addStretch()

        self._scroll.setWidget(self._container)
        root.addWidget(self._scroll, stretch=1)

        self._empty_label = QLabel("Aucune image chargée")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet("color: #45475a; font-size: 14px;")
        self._v_layout.insertWidget(0, self._empty_label)

    # ------------------------------------------------------------------ #

    def load_multiimage(self, mi: MultiImage | None):
        """Refresh the preview from *mi*."""
        # clear
        for card in self._cards:
            self._v_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()

        if mi is None or len(mi) == 0:
            self._empty_label.setVisible(True)
            return

        self._empty_label.setVisible(False)
        available_w = max(self._scroll.viewport().width() - 16, 100)

        for idx, img in enumerate(mi):
            card = _ImageCard(idx, img.pixels)
            card.set_width(available_w)
            # insert before the trailing stretch
            self._v_layout.insertWidget(
                self._v_layout.count() - 1, card
            )
            self._cards.append(card)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        available_w = max(self._scroll.viewport().width() - 16, 100)
        for card in self._cards:
            card.set_width(available_w)
