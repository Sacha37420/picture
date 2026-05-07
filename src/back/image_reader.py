"""
image_reader.py – ImageReader class.

Reads a single image file and populates a MultiImage.
Supports every file format and colour mode understood by Pillow:
  PNG, JPEG, BMP, TIFF, GIF, WebP, ICO, PPM, TGA, …
  1-bit, greyscale (L/LA), palette (P/PA), RGB, RGBA, CMYK,
  YCbCr, LAB, HSV, 32-bit int (I), 32-bit float (F), …

Normalisation rules applied before storing the pixel array:
  - Modes with alpha  (RGBA, LA, PA, RGBa, La, P+transparency) → RGBA
  - Greyscale without alpha (1, L, I, F)                        → L
  - Everything else   (RGB, CMYK, YCbCr, LAB, HSV, RGBX …)     → RGB
"""
from __future__ import annotations

from typing import Optional

import numpy as np
from PIL import Image as PILImage

from .image import Image
from .multiimage import MultiImage

# Modes that must be stored as RGBA (contain or may contain transparency)
_ALPHA_MODES = frozenset({"RGBA", "LA", "RGBa", "La", "PA"})
# Modes that are greyscale (no alpha)
_GREY_MODES = frozenset({"L", "1", "I", "F"})


def _normalize_pil(pil_image: PILImage.Image) -> PILImage.Image:
    """Return *pil_image* converted to a normalised mode (L / RGB / RGBA)."""
    mode = pil_image.mode
    if mode in _ALPHA_MODES:
        return pil_image.convert("RGBA")
    if mode == "P":
        # Palette image: has transparency if "transparency" key is present
        if "transparency" in pil_image.info:
            return pil_image.convert("RGBA")
        return pil_image.convert("RGB")
    if mode in _GREY_MODES:
        return pil_image.convert("L")
    if mode in ("RGB", "RGBX"):
        return pil_image.convert("RGB")
    # Fallback: CMYK, YCbCr, LAB, HSV, …
    return pil_image.convert("RGB")


class ImageReader:
    """
    Load an image file into a :class:`MultiImage`.

    If a :class:`MultiImage` is supplied the image is appended to it;
    otherwise a new :class:`MultiImage` is created.

    Parameters
    ----------
    image_path : str
        Path to the image file.
    multiimage : MultiImage, optional
        Existing collection to append to.  If ``None`` a new
        :class:`MultiImage` is created.

    Examples
    --------
    >>> mi = ImageReader("photo.png").multiimage
    >>> # append a second image to the same collection
    >>> ImageReader("overlay.png", mi)
    """

    def __init__(
        self, image_path: str, multiimage: Optional[MultiImage] = None
    ) -> None:
        self.multiimage: MultiImage = (
            multiimage if multiimage is not None else MultiImage()
        )
        self._load(image_path)

    def _load(self, image_path: str) -> None:
        pil_image = _normalize_pil(PILImage.open(image_path))
        pixels = np.array(pil_image, dtype=np.uint8)
        # Greyscale arrays are 2-D – add channel axis
        if pixels.ndim == 2:
            pixels = pixels[:, :, np.newaxis]
        self.multiimage.add_image(Image(pixels))
