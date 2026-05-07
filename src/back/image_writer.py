"""
image_writer.py – ImageWriter class.

Writes each image of a MultiImage to an individual file.
Supports every format understood by Pillow (PNG, JPEG, BMP, TIFF,
WebP, PPM, TGA, ICO, …).

JPEG special case: JPEG does not support transparency.  If an RGBA
image is written to JPEG the alpha channel is composited onto a white
background automatically.

GIF / single-file animation note: each image is written as a separate
file.  For animated GIF / APNG use PdfWriter or Pillow directly.
"""
from __future__ import annotations

import os
from typing import Optional

from PIL import Image as PILImage

from .multiimage import MultiImage

# Formats that do not support an alpha channel
_NO_ALPHA_FORMATS = frozenset({"JPEG", "JPG", "BMP", "PPM"})


def _prepare_for_format(pil_image: PILImage.Image, fmt: str) -> PILImage.Image:
    """Convert *pil_image* to a mode compatible with *fmt*."""
    upper = fmt.upper()
    if upper in _NO_ALPHA_FORMATS and pil_image.mode == "RGBA":
        bg = PILImage.new("RGB", pil_image.size, (255, 255, 255))
        bg.paste(pil_image, mask=pil_image.split()[3])
        return bg
    if upper in _NO_ALPHA_FORMATS and pil_image.mode not in ("RGB", "L"):
        return pil_image.convert("RGB")
    return pil_image


class ImageWriter:
    """
    Save every :class:`Image` in a :class:`MultiImage` to individual files.

    Files are named ``<prefix>_<index>.<ext>`` and written to *output_dir*
    (created if it does not exist).

    Parameters
    ----------
    multiimage : MultiImage
        Collection to write.
    output_dir : str
        Destination directory.
    prefix : str
        Filename prefix.  Defaults to ``"image"``.
    fmt : str
        Pillow format string (e.g. ``"PNG"``, ``"JPEG"``, ``"WEBP"``).
        Defaults to ``"PNG"``.

    Examples
    --------
    >>> ImageWriter(mi, "output/pages", prefix="page", fmt="PNG")
    >>> ImageWriter(mi, "output/thumbs", prefix="thumb", fmt="JPEG")
    """

    def __init__(
        self,
        multiimage: MultiImage,
        output_dir: str,
        prefix: str = "image",
        fmt: str = "PNG",
    ) -> None:
        self._write(multiimage, output_dir, prefix, fmt)

    def _write(
        self,
        multiimage: MultiImage,
        output_dir: str,
        prefix: str,
        fmt: str,
    ) -> None:
        os.makedirs(output_dir, exist_ok=True)
        ext = fmt.lower()
        # Normalise extension for JPEG
        if ext == "jpeg":
            ext = "jpg"
        for idx, img in enumerate(multiimage):
            path = os.path.join(output_dir, f"{prefix}_{idx:04d}.{ext}")
            pil_img = _prepare_for_format(img.to_pil(), fmt)
            pil_img.save(path, format=fmt)
