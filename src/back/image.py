"""
image.py – core Image class.

An Image stores its pixel data as a NumPy array of shape
(height, width, channels) with dtype uint8.  All mutating operations
return a *new* Image so the original is never modified.
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple, Union

import numpy as np
from PIL import Image as PILImage


class Image:
    """
    Single image represented as a pixel array.

    Parameters
    ----------
    pixels : np.ndarray
        Array of shape (height, width, channels), dtype uint8.
    """

    def __init__(self, pixels: np.ndarray) -> None:
        if not isinstance(pixels, np.ndarray):
            raise TypeError("pixels must be a numpy ndarray")
        if pixels.ndim != 3:
            raise ValueError("pixels must be a 3-D array (height, width, channels)")
        self.pixels: np.ndarray = pixels.astype(np.uint8)
        self.height: int = pixels.shape[0]
        self.width: int = pixels.shape[1]
        self.channels: int = pixels.shape[2]

    # ------------------------------------------------------------------ #
    # Compression                                                          #
    # ------------------------------------------------------------------ #

    def compress(self, compression_level: int) -> "Image":
        """
        Compress the image by averaging non-overlapping blocks.

        Each square block of size ``sqrt(compression_level)`` ×
        ``sqrt(compression_level)`` is replaced by a single pixel whose
        colour is the average of the block.

        Parameters
        ----------
        compression_level : int
            Must be a perfect square ≥ 4 (e.g. 4 → 2×2, 9 → 3×3, 16 → 4×4).

        Returns
        -------
        Image
            New compressed image.
        """
        block = int(math.isqrt(compression_level))
        if block * block != compression_level or block < 2:
            raise ValueError(
                "compression_level must be a perfect square ≥ 4 (4, 9, 16, …)"
            )

        new_h = self.height // block
        new_w = self.width // block
        trimmed = self.pixels[: new_h * block, : new_w * block]
        # reshape → (new_h, block, new_w, block, channels) then average over axes 1 & 3
        averaged = (
            trimmed.reshape(new_h, block, new_w, block, self.channels)
            .mean(axis=(1, 3))
            .astype(np.uint8)
        )
        return Image(averaged)

    # ------------------------------------------------------------------ #
    # Colour-space conversion                                              #
    # ------------------------------------------------------------------ #

    def to_rgba(self) -> "Image":
        """
        Convert an RGB image to RGBA with full opacity (alpha = 255).

        Returns
        -------
        Image
            New RGBA image.  If already RGBA, returns a copy.
        """
        if self.channels == 4:
            return Image(self.pixels.copy())
        if self.channels != 3:
            raise ValueError("Image must be RGB (3 channels) to convert to RGBA")
        alpha = np.full((self.height, self.width, 1), 255, dtype=np.uint8)
        return Image(np.concatenate([self.pixels, alpha], axis=2))

    # ------------------------------------------------------------------ #
    # Transparency                                                         #
    # ------------------------------------------------------------------ #

    def make_color_transparent(
        self,
        color: Union[Tuple[int, int, int], Tuple[int, int, int, int]],
        threshold: float = 30.0,
    ) -> "Image":
        """
        Set pixels whose RGB colour is within *threshold* of *color* to
        fully transparent (alpha = 0).

        Parameters
        ----------
        color : tuple
            Target RGB or RGBA colour.
        threshold : float
            Maximum Euclidean distance in RGB space.

        Returns
        -------
        Image
            New RGBA image with matching pixels made transparent.
        """
        if self.channels != 4:
            raise ValueError("Image must be RGBA.  Call to_rgba() first.")
        target = np.array(color[:3], dtype=float)
        distances = np.linalg.norm(
            self.pixels[:, :, :3].astype(float) - target, axis=2
        )
        new_pixels = self.pixels.copy()
        new_pixels[distances <= threshold, 3] = 0
        return Image(new_pixels)

    # ------------------------------------------------------------------ #
    # Colour-based categorisation                                          #
    # ------------------------------------------------------------------ #

    def categorize_by_color(self, threshold: float = 30.0) -> Dict:
        """
        Group image pixels into colour-based elements.

        Uses a greedy algorithm: unique colours are processed one by one;
        a colour is assigned to the nearest existing cluster if its
        Euclidean distance is ≤ *threshold*, otherwise a new cluster is
        created.  Working on unique colours instead of every pixel makes
        this tractable for most images.

        Parameters
        ----------
        threshold : float
            Maximum Euclidean distance in RGB space to merge into an
            existing cluster.

        Returns
        -------
        dict
            Mapping::

                {
                  element_id: {
                    'average_color': [R, G, B],        # float
                    'pixels': np.ndarray               # shape (n, 2) – rows & cols
                  }
                }
        """
        flat_rgb = self.pixels[:, :, :3].reshape(-1, 3).astype(np.int32)

        # Work on unique colours to reduce iteration count
        unique_colors, inverse = np.unique(flat_rgb, axis=0, return_inverse=True)

        color_to_cluster = np.full(len(unique_colors), -1, dtype=np.int32)
        centroids: List[np.ndarray] = []

        for i, color in enumerate(unique_colors.astype(float)):
            if centroids:
                c_arr = np.asarray(centroids)  # (k, 3)
                dists = np.linalg.norm(c_arr - color, axis=1)
                best = int(np.argmin(dists))
                if dists[best] <= threshold:
                    color_to_cluster[i] = best
                    continue
            color_to_cluster[i] = len(centroids)
            centroids.append(color.copy())

        # Assign every pixel to its cluster
        pixel_clusters = color_to_cluster[inverse]  # (H*W,)

        all_idx = np.arange(self.height * self.width)
        all_rows, all_cols = np.divmod(all_idx, self.width)

        mapping: Dict = {}
        for cid, _ in enumerate(centroids):
            mask = pixel_clusters == cid
            coords = np.stack([all_rows[mask], all_cols[mask]], axis=1)
            avg = flat_rgb[mask].mean(axis=0).tolist()
            mapping[cid] = {"average_color": avg, "pixels": coords}

        return mapping

    # ------------------------------------------------------------------ #
    # Element recolouring                                                  #
    # ------------------------------------------------------------------ #

    def recolor_element(
        self,
        mapping: Dict,
        element_id: int,
        new_color: Union[Tuple[int, int, int], List[int]],
    ) -> "Image":
        """
        Shift the colours of one mapping element toward a new average colour.

        For each pixel in the element:
        ``new_pixel = new_avg + (old_pixel – old_avg)``  (clamped to [0, 255]).

        The mapping's ``average_color`` entry for the element is updated
        in-place to reflect the change.

        Parameters
        ----------
        mapping : dict
            Mapping produced by :meth:`categorize_by_color`.
        element_id : int
            ID of the element to recolour.
        new_color : tuple or list
            New average colour [R, G, B].

        Returns
        -------
        Image
            New image with the element recoloured.
        """
        if element_id not in mapping:
            raise KeyError(f"Element {element_id} not found in mapping.")
        element = mapping[element_id]
        old_avg = np.array(element["average_color"], dtype=float)
        new_avg = np.array(new_color[:3], dtype=float)
        coords = element["pixels"]
        rows, cols = coords[:, 0], coords[:, 1]

        new_pixels = self.pixels.copy()
        old_colors = self.pixels[rows, cols, :3].astype(float)
        shifted = np.clip(new_avg + (old_colors - old_avg), 0, 255).astype(np.uint8)
        new_pixels[rows, cols, :3] = shifted

        mapping[element_id]["average_color"] = [float(v) for v in new_color[:3]]
        return Image(new_pixels)

    # ------------------------------------------------------------------ #
    # Element transparency                                                 #
    # ------------------------------------------------------------------ #

    def make_element_transparent(self, mapping: Dict, element_id: int) -> "Image":
        """
        Make all pixels of a mapping element fully transparent (alpha = 0).

        Parameters
        ----------
        mapping : dict
            Mapping produced by :meth:`categorize_by_color`.
        element_id : int
            ID of the element to make transparent.

        Returns
        -------
        Image
            New RGBA image with the element's pixels set to alpha = 0.
        """
        if self.channels != 4:
            raise ValueError("Image must be RGBA.  Call to_rgba() first.")
        if element_id not in mapping:
            raise KeyError(f"Element {element_id} not found in mapping.")
        coords = mapping[element_id]["pixels"]
        rows, cols = coords[:, 0], coords[:, 1]
        new_pixels = self.pixels.copy()
        new_pixels[rows, cols, 3] = 0
        return Image(new_pixels)

    # ------------------------------------------------------------------ #
    # Cropping                                                             #
    # ------------------------------------------------------------------ #

    def crop(self, x: int, y: int, width: int, height: int) -> "Image":
        """
        Crop the image.

        Parameters
        ----------
        x : int
            Left boundary (column index).
        y : int
            Top boundary (row index).
        width : int
            Width of the crop region.
        height : int
            Height of the crop region.

        Returns
        -------
        Image
            New cropped image.
        """
        if x < 0 or y < 0 or x + width > self.width or y + height > self.height:
            raise ValueError("Crop region exceeds image boundaries.")
        return Image(self.pixels[y : y + height, x : x + width].copy())

    # ------------------------------------------------------------------ #
    # PIL interop & persistence                                            #
    # ------------------------------------------------------------------ #

    def to_pil(self) -> PILImage.Image:
        """Convert to a :class:`PIL.Image.Image`."""
        mode_map = {1: "L", 2: "LA", 3: "RGB", 4: "RGBA"}
        mode = mode_map.get(self.channels)
        if mode is None:
            raise ValueError(f"Unsupported channel count: {self.channels}")
        return PILImage.fromarray(self.pixels, mode)

    def save(self, path: str) -> None:
        """Save the image to *path* (format inferred from extension)."""
        self.to_pil().save(path)

    @classmethod
    def from_pil(cls, pil_image: PILImage.Image) -> "Image":
        """Create an :class:`Image` from a :class:`PIL.Image.Image`."""
        return cls(np.array(pil_image))

    def __repr__(self) -> str:
        return (
            f"Image(width={self.width}, height={self.height}, "
            f"channels={self.channels})"
        )
