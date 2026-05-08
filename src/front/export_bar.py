"""
export_bar.py – bottom bar.

Allows the user to choose an output format and save the MultiImage.
Shows an estimated file size that updates when the format changes.
"""
from __future__ import annotations

import io
import logging
import os
from typing import Optional

_log = logging.getLogger("picture.export_bar")

from .qt_compat import (
    pyqtSignal,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from ..back.multiimage import MultiImage
from ..back.pdf_writer import PdfWriter, PAGE_WIDTHS_PT
from ..back.image_writer import ImageWriter

_FORMATS = ["PNG", "JPEG", "BMP", "TIFF", "WebP", "PDF"]
_PAGE_FORMATS = list(PAGE_WIDTHS_PT.keys())  # ["A4", "Letter", "A3", "Legal"]

# Pillow format strings (PDF handled separately via PdfWriter)
_PILLOW_FMT = {
    "PNG":  "PNG",
    "JPEG": "JPEG",
    "BMP":  "BMP",
    "TIFF": "TIFF",
    "WebP": "WEBP",
}


def _estimate_size(mi: MultiImage, fmt: str, page_format: str = "A4") -> int:
    """Return estimated total size in bytes by encoding each image in memory."""
    total = 0
    if fmt == "PDF":
        buf = io.BytesIO()
        try:
            import fitz
            max_w_pt = PAGE_WIDTHS_PT.get(page_format, 595.0)
            dpi = 96
            doc = fitz.open()
            for img in mi:
                nat_w_pt = img.width  * 72.0 / dpi
                nat_h_pt = img.height * 72.0 / dpi
                if nat_w_pt > max_w_pt:
                    scale  = max_w_pt / nat_w_pt
                    w_pt   = max_w_pt
                    h_pt   = nat_h_pt * scale
                else:
                    w_pt, h_pt = nat_w_pt, nat_h_pt
                pil = img.to_pil()
                img_buf = io.BytesIO()
                pil.save(img_buf, format="PNG")
                img_buf.seek(0)
                page = doc.new_page(width=w_pt, height=h_pt)
                page.insert_image(
                    fitz.Rect(0, 0, w_pt, h_pt),
                    stream=img_buf.read(),
                )
            doc.save(buf)
            doc.close()
            total = buf.tell()
        except Exception:
            _log.error("_estimate_size (PDF): fitz error", exc_info=True)
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
        self._fmt_combo.setCurrentText("PDF")
        self._fmt_combo.currentTextChanged.connect(self._on_format_changed)
        self._fmt_combo.setFixedWidth(90)
        layout.addWidget(self._fmt_combo)

        # Page format selector – visible only when PDF is selected
        self._page_lbl = QLabel("Page :")
        layout.addWidget(self._page_lbl)

        self._page_combo = QComboBox()
        self._page_combo.addItems(_PAGE_FORMATS)
        self._page_combo.setFixedWidth(80)
        self._page_combo.currentTextChanged.connect(self._on_format_changed)
        layout.addWidget(self._page_combo)

        self._size_label = QLabel("Poids estimé : —")
        self._size_label.setObjectName("status")
        layout.addWidget(self._size_label)

        layout.addStretch()

        self._btn_save = QPushButton("💾  Enregistrer…")
        self._btn_save.setObjectName("accent")
        self._btn_save.setFixedHeight(34)
        self._btn_save.clicked.connect(self._on_save)
        layout.addWidget(self._btn_save)

        # Initial visibility
        self._update_page_visibility(self._fmt_combo.currentText())

    # ------------------------------------------------------------------ #

    def set_multiimage(self, mi: Optional[MultiImage]):
        self._mi = mi
        self._refresh_size()

    def _on_format_changed(self, _):
        self._update_page_visibility(self._fmt_combo.currentText())
        self._refresh_size()

    def _update_page_visibility(self, fmt: str):
        visible = (fmt == "PDF")
        self._page_lbl.setVisible(visible)
        self._page_combo.setVisible(visible)

    def _refresh_size(self):
        if self._mi is None or len(self._mi) == 0:
            self._size_label.setText("Poids estimé : —")
            return
        fmt = self._fmt_combo.currentText()
        page_fmt = self._page_combo.currentText()
        size = _estimate_size(self._mi, fmt, page_fmt)
        self._size_label.setText(f"Poids estimé : {_human_size(size)}")

    def _on_save(self):
        if self._mi is None or len(self._mi) == 0:
            return
        fmt = self._fmt_combo.currentText()
        _log.debug("ExportBar._on_save: format=%s", fmt)
        if fmt == "PDF":
            path, _ = QFileDialog.getSaveFileName(
                self, "Enregistrer le PDF", "", "PDF (*.pdf)"
            )
            if path:
                try:
                    PdfWriter(
                        self._mi,
                        path,
                        page_format=self._page_combo.currentText(),
                    )
                    _log.info("ExportBar: PDF saved to '%s'", path)
                except Exception:
                    _log.error("ExportBar: PDF save FAILED for '%s'", path, exc_info=True)
                    raise
        else:
            directory = QFileDialog.getExistingDirectory(
                self, "Choisir le dossier de destination"
            )
            if directory:
                ImageWriter(self._mi, directory, fmt=_PILLOW_FMT.get(fmt, "PNG"))
