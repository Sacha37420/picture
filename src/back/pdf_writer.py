"""
pdf_writer.py – PdfWriter class.

Writes a MultiImage to a PDF file (one image per page).
Requires PyMuPDF (``pip install pymupdf``).

Each image is scaled so its width fits within a standard PDF page width
(A4 = 595 pt, Letter = 612 pt).  If the image is narrower than the page
it is left at its natural size.  Height is scaled proportionally.

Standard page widths in points (1 pt = 1/72 inch)
--------------------------------------------------
  A4     : 595 × 842 pt
  Letter : 612 × 792 pt
  A3     : 842 × 1191 pt
  Legal  : 612 × 1008 pt
"""
from __future__ import annotations

import io
from typing import Optional

from .multiimage import MultiImage

# Standard page widths in points
PAGE_WIDTHS_PT = {
    "A4":     595.0,
    "Letter": 612.0,
    "A3":     842.0,
    "Legal":  612.0,
}
_DEFAULT_PAGE = "A4"


class PdfWriter:
    """
    Save a :class:`MultiImage` as a multi-page PDF.

    Each image is scaled so its width fits within *page_format* width
    (preserving aspect ratio).  Images already narrower than the page
    are kept at their natural pixel size.

    Parameters
    ----------
    multiimage : MultiImage
        Collection to write.
    output_path : str
        Destination file path (e.g. ``"output/result.pdf"``).
    dpi : int
        Resolution used to convert pixel dimensions to point dimensions.
        Defaults to 96 (standard screen resolution).
    page_format : str
        Maximum page width preset.  One of ``"A4"`` (default),
        ``"Letter"``, ``"A3"``, ``"Legal"``.

    Raises
    ------
    ImportError
        If PyMuPDF is not installed.
    ValueError
        If *multiimage* contains no images.

    Examples
    --------
    >>> PdfWriter(mi, "output/result.pdf")
    >>> PdfWriter(mi, "output/letter.pdf", page_format="Letter")
    """

    def __init__(
        self,
        multiimage: MultiImage,
        output_path: str,
        dpi: int = 96,
        page_format: str = _DEFAULT_PAGE,
    ) -> None:
        if len(multiimage) == 0:
            raise ValueError("MultiImage is empty – nothing to write.")
        if page_format not in PAGE_WIDTHS_PT:
            raise ValueError(
                f"Unknown page_format '{page_format}'. "
                f"Choose from: {list(PAGE_WIDTHS_PT)}"
            )
        self._write(multiimage, output_path, dpi, page_format)

    def _write(
        self,
        multiimage: MultiImage,
        output_path: str,
        dpi: int,
        page_format: str,
    ) -> None:
        try:
            import fitz  # PyMuPDF
        except ImportError as exc:
            raise ImportError(
                "PyMuPDF is required for PDF writing.  "
                "Install it with:  pip install pymupdf"
            ) from exc

        max_w_pt = PAGE_WIDTHS_PT[page_format]

        doc = fitz.open()
        try:
            for img in multiimage:
                # Natural size in points at the given DPI
                nat_w_pt = img.width  * 72.0 / dpi
                nat_h_pt = img.height * 72.0 / dpi

                # Scale down if wider than page; never scale up
                if nat_w_pt > max_w_pt:
                    scale   = max_w_pt / nat_w_pt
                    w_pt    = max_w_pt
                    h_pt    = nat_h_pt * scale
                else:
                    w_pt = nat_w_pt
                    h_pt = nat_h_pt

                page = doc.new_page(width=w_pt, height=h_pt)

                # Serialise image as PNG in memory (lossless, supports RGBA)
                buf = io.BytesIO()
                img.to_pil().save(buf, format="PNG")
                buf.seek(0)

                page.insert_image(
                    fitz.Rect(0, 0, w_pt, h_pt),
                    stream=buf.read(),
                )

            doc.save(output_path, garbage=4, deflate=True)
        finally:
            doc.close()
