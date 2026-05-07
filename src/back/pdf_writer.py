"""
pdf_writer.py – PdfWriter class.

Writes a MultiImage to a PDF file (one image per page).
Requires PyMuPDF (``pip install pymupdf``).

Page dimensions in the output PDF are set so that one image pixel equals
one point (1 pt = 1/72 inch) at the default 72 DPI.  Pass a different
*dpi* value to scale the pages:

    width_pt  = image_width  * 72 / dpi
    height_pt = image_height * 72 / dpi
"""
from __future__ import annotations

import io

from .multiimage import MultiImage


class PdfWriter:
    """
    Save a :class:`MultiImage` as a multi-page PDF.

    Each :class:`Image` in the collection becomes one page.

    Parameters
    ----------
    multiimage : MultiImage
        Collection to write.
    output_path : str
        Destination file path (e.g. ``"output/result.pdf"``).
    dpi : int
        Resolution used to convert pixel dimensions to point dimensions.
        Defaults to 72 (1 pixel = 1 pt).

    Raises
    ------
    ImportError
        If PyMuPDF is not installed.
    ValueError
        If *multiimage* contains no images.

    Examples
    --------
    >>> PdfWriter(mi, "output/result.pdf")
    >>> PdfWriter(mi, "output/hires.pdf", dpi=150)
    """

    def __init__(
        self,
        multiimage: MultiImage,
        output_path: str,
        dpi: int = 72,
    ) -> None:
        if len(multiimage) == 0:
            raise ValueError("MultiImage is empty – nothing to write.")
        self._write(multiimage, output_path, dpi)

    def _write(self, multiimage: MultiImage, output_path: str, dpi: int) -> None:
        try:
            import fitz  # PyMuPDF
        except ImportError as exc:
            raise ImportError(
                "PyMuPDF is required for PDF writing.  "
                "Install it with:  pip install pymupdf"
            ) from exc

        doc = fitz.open()
        try:
            for img in multiimage:
                w_pt = img.width * 72 / dpi
                h_pt = img.height * 72 / dpi

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
