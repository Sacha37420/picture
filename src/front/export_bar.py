"""
export_bar.py – bottom bar.

Allows the user to choose an output format and save the MultiImage.
Shows an estimated file size that updates when the format changes.
"""
from __future__ import annotations

import io
import os
from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from ..back.multiimage import MultiImage
from ..back.pdf_writer import PdfWriter
from ..back.image_writer import ImageWriter

_FORMATS = ["PNG", "JPEG", "BMP", "TIFF", "WebP", "PDF"]

# Pillow format strings (PDF handled separately via PdfWriter)
_PILLOW_FMT = {
    "PNG":  "PNG",
    "JPEG": "JPEG",
    "BMP":  "BMP",
    "TIFF": "TIFF",
    "WebP": "WEBP",
}


def _estimate_size(mi: MultiImage, fmt: str) -> int:
    """Return estimated total size in bytes by encoding each image in memory."""
    total = 0
    if fmt == "PDF":
        buf = io.BytesIO()
        try:
            import fitz
            doc = fitz.open()
            for img in mi:
                pil = img.to_pil()
                img_buf = io.BytesIO()
                pil.save(img_buf, format="PNG")
                img_buf.seek(0)
                page = doc.new_page(width=img.width, height=img.height)
                page.insert_image(
                    fitz.Rect(0, 0, img.width, img.height),
                    stream=img_buf.read(),
                )
            doc.save(buf)
            doc.close()
            total = buf.tell()
        except Exception:
            total = 0
    else:
        pillow_fmt = _PILLOW_FMT.get(fmt, "PNG")
        for img in mi:
            buf = io.BytesIO()
            try:
                pil = img.to_pil()
                if pillow_fmt == "JPEG" and pil.mode == "RGBA":
                    from PIL import Image as PILImage
                    bg = PILImage.new("RGB", pil.size, (255, 255, 255))
                    bg.paste(pil, mask=pil.split()[3])
                    pil = bg
                pil.save(buf, format=pillow_fmt)
                total += buf.tell()
            except Exception:
                pass
    return total


def _human_size(n: int) -> str:
    if n <= 0:
        return "—"
    if n < 1024:
        return f"{n} o"
    if n < 1024 ** 2:
        return f"{n/1024:.1f} Ko"
    return f"{n/1024**2:.2f} Mo"


class ExportBar(QWidget):
    """Bottom bar – format selector + estimated size + save button."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mi: Optional[MultiImage] = None
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        lbl = QLabel("Format :")
        layout.addWidget(lbl)

        self._fmt_combo = QComboBox()
        self._fmt_combo.addItems(_FORMATS)
        self._fmt_combo.currentTextChanged.connect(self._on_format_changed)
        self._fmt_combo.setFixedWidth(90)
        layout.addWidget(self._fmt_combo)

        self._size_label = QLabel("Poids estimé : —")
        self._size_label.setObjectName("status")
        layout.addWidget(self._size_label)

        layout.addStretch()

        self._btn_save = QPushButton("💾  Enregistrer…")
        self._btn_save.setObjectName("accent")
        self._btn_save.setFixedHeight(34)
        self._btn_save.clicked.connect(self._on_save)
        layout.addWidget(self._btn_save)

    # ------------------------------------------------------------------ #

    def set_multiimage(self, mi: Optional[MultiImage]):
        self._mi = mi
        self._refresh_size()

    def _on_format_changed(self, _):
        self._refresh_size()

    def _refresh_size(self):
        if self._mi is None or len(self._mi) == 0:
            self._size_label.setText("Poids estimé : —")
            return
        fmt = self._fmt_combo.currentText()
        size = _estimate_size(self._mi, fmt)
        self._size_label.setText(f"Poids estimé : {_human_size(size)}")

    def _on_save(self):
        if self._mi is None or len(self._mi) == 0:
            return
        fmt = self._fmt_combo.currentText()
        if fmt == "PDF":
            path, _ = QFileDialog.getSaveFileName(
                self, "Enregistrer le PDF", "", "PDF (*.pdf)"
            )
            if path:
                PdfWriter(self._mi, path)
        else:
            directory = QFileDialog.getExistingDirectory(
                self, "Choisir le dossier de destination"
            )
            if directory:
                ImageWriter(self._mi, directory, fmt=_PILLOW_FMT.get(fmt, "PNG"))
