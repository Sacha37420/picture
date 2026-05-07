"""
preview_panel.py – centre panel.

Scrollable vertical strip showing every image in the current MultiImage.
Each image is rendered as a thumbnail that fills the panel width while
preserving the aspect ratio.  A label under each thumbnail shows its
index, dimensions and channel count.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
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

        self._pixels = pixels
        self._pixmap_orig = _array_to_pixmap(pixels)
        self._current_width: int = 100
        self._crop_rect: tuple | None = None      # (x, y, w, h) en coords image
        self._highlight_mask: np.ndarray | None = None  # bool (H, W)

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
        self._current_width = width
        self._refresh_display()

    def _refresh_display(self):
        if self._pixmap_orig.isNull():
            return
        base = self._make_highlight_pixmap() if self._highlight_mask is not None else self._pixmap_orig
        scaled = base.scaledToWidth(self._current_width, Qt.TransformationMode.SmoothTransformation)
        if self._crop_rect is not None:
            scaled = self._apply_crop_overlay(scaled)
        self._img_label.setPixmap(scaled)

    def _make_highlight_pixmap(self) -> QPixmap:
        """Pixmap avec les pixels hors-élément assombris à 20 %."""
        arr = self._pixels.astype(np.float32)
        arr[~self._highlight_mask] *= 0.20
        np.clip(arr, 0, 255, out=arr)
        return _array_to_pixmap(arr.astype(np.uint8))

    def _apply_crop_overlay(self, scaled: QPixmap) -> QPixmap:
        """Voile sombre en dehors du rect de rognage + bordure bleue."""
        x, y, w, h = self._crop_rect
        ih, iw = self._pixels.shape[:2]
        sw, sh = scaled.width(), scaled.height()
        sx  = int(x * sw / iw)
        sy  = int(y * sh / ih)
        sw2 = max(1, int(w * sw / iw))
        sh2 = max(1, int(h * sh / ih))
        result = QPixmap(scaled)
        painter = QPainter(result)
        dark = QColor(0, 0, 0, 150)
        painter.fillRect(0,      0,      sw,        sy,        dark)
        painter.fillRect(0,      sy+sh2, sw,        sh-sy-sh2, dark)
        painter.fillRect(0,      sy,     sx,        sh2,       dark)
        painter.fillRect(sx+sw2, sy,     sw-sx-sw2, sh2,       dark)
        painter.setPen(QPen(QColor(89, 180, 250), 2))
        painter.drawRect(sx, sy, sw2 - 1, sh2 - 1)
        painter.end()
        return result

    # -- overlay API ---------------------------------------------------- #

    def show_crop(self, x: int, y: int, w: int, h: int):
        self._crop_rect = (x, y, w, h)
        self._refresh_display()

    def clear_crop(self):
        self._crop_rect = None
        self._refresh_display()

    def show_element_highlight(self, mask: np.ndarray):
        self._highlight_mask = mask
        self._refresh_display()

    def clear_element_highlight(self):
        self._highlight_mask = None
        self._refresh_display()


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

    # -- overlay API ----------------------------------------------------- #

    def show_crop_overlay(self, x: int, y: int, w: int, h: int, target: int | None = None):
        for i, card in enumerate(self._cards):
            if target is None or i == target:
                card.show_crop(x, y, w, h)
            else:
                card.clear_crop()

    def clear_crop_overlay(self):
        for card in self._cards:
            card.clear_crop()

    def show_element_highlight(self, masks: list):
        """masks[i] est un tableau bool (H,W) ou None pour la carte i."""
        for i, card in enumerate(self._cards):
            m = masks[i] if i < len(masks) else None
            if m is not None:
                card.show_element_highlight(m)
            else:
                card.clear_element_highlight()

    def clear_element_highlight(self):
        for card in self._cards:
            card.clear_element_highlight()
