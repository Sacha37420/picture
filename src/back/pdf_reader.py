"""
pdf_reader.py – PdfReader class.

Reads a PDF file and populates a MultiImage with one Image per page.
Requires PyMuPDF (``pip install pymupdf``).
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np

from .image import Image
from .multiimage import MultiImage

_log = logging.getLogger("picture.pdf_reader")


class PdfReader:
    """
    Convert a PDF file into a :class:`MultiImage`.

    Each page of the PDF becomes one :class:`Image`.  If a
    :class:`MultiImage` is supplied the pages are appended to it;
    otherwise a new :class:`MultiImage` is created.

    Parameters
    ----------
    pdf_path : str
        Path to the PDF file.
    multiimage : MultiImage, optional
        Existing collection to append to.  If ``None`` a new
        :class:`MultiImage` is created.

    Raises
    ------
    ImportError
        If PyMuPDF is not installed.

    Examples
    --------
    >>> mi = PdfReader("document.pdf").multiimage
    >>> # append a second PDF to the same collection
    >>> PdfReader("appendix.pdf", mi)
    """

    def __init__(
        self, pdf_path: str, multiimage: Optional[MultiImage] = None
    ) -> None:
        self.multiimage: MultiImage = (
            multiimage if multiimage is not None else MultiImage()
        )
        self._load(pdf_path)

    def _load(self, pdf_path: str) -> None:
        _log.debug("PdfReader._load: opening '%s'", pdf_path)
        try:
            import fitz  # PyMuPDF
            _log.debug("PdfReader: fitz imported OK (%s)", fitz.__file__)
        except ImportError as exc:
            _log.error("PdfReader: fitz import FAILED", exc_info=True)
            raise ImportError(
                "PyMuPDF is required for PDF reading.  "
                "Install it with:  pip install pymupdf"
            ) from exc

        doc = fitz.open(pdf_path)
        _log.debug("PdfReader: opened doc with %d pages", doc.page_count)
        try:
            for page in doc:
                pix = page.get_pixmap()
                # pix.n is the number of colour components (3 = RGB, 4 = RGBA)
                img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                    pix.height, pix.width, pix.n
                )
                self.multiimage.add_image(Image(img_array))
        finally:
            doc.close()
        _log.debug("PdfReader: loaded %d pages from '%s'", len(self.multiimage), pdf_path)
