"""
multiimage.py – MultiImage class.

MultiImage is the main entry point: it owns a list of Image objects and
exposes every Image operation as a batch method that applies to all images.
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple, Union

from .image import Image


class MultiImage:
    """
    Collection of :class:`Image` objects.

    All mutating operations return a *new* MultiImage (the source list is
    never modified in place).  Operations that depend on a per-image
    mapping (e.g. :meth:`recolor_element`) accept the list of mappings
    returned by :meth:`categorize_by_color`.

    Parameters
    ----------
    images : list[Image], optional
        Initial list of images.  Defaults to an empty list.
    """

    def __init__(self, images: Optional[List[Image]] = None) -> None:
        self.images: List[Image] = list(images) if images else []

    # ------------------------------------------------------------------ #
    # Collection helpers                                                   #
    # ------------------------------------------------------------------ #

    def add_image(self, image: Image) -> None:
        """Append *image* to the collection."""
        self.images.append(image)

    def __len__(self) -> int:
        return len(self.images)

    def __getitem__(self, index: int) -> Image:
        return self.images[index]

    def __iter__(self):
        return iter(self.images)

    def __repr__(self) -> str:
        return f"MultiImage(count={len(self.images)})"

    # ------------------------------------------------------------------ #
    # Batch Image operations                                               #
    # ------------------------------------------------------------------ #

    def compress(self, compression_level: int) -> "MultiImage":
        """
        Compress all images.

        Parameters
        ----------
        compression_level : int
            Perfect square ≥ 4.  Block size = sqrt(compression_level).

        Returns
        -------
        MultiImage
            New collection with every image compressed.

        See Also
        --------
        Image.compress
        """
        return MultiImage([img.compress(compression_level) for img in self.images])

    def to_rgba(self) -> "MultiImage":
        """
        Convert all RGB images to RGBA (alpha = 255 – fully opaque).

        Returns
        -------
        MultiImage
            New collection with every image in RGBA mode.

        See Also
        --------
        Image.to_rgba
        """
        return MultiImage([img.to_rgba() for img in self.images])

    def make_color_transparent(
        self,
        color: Union[Tuple[int, int, int], Tuple[int, int, int, int]],
        threshold: float = 30.0,
    ) -> "MultiImage":
        """
        Make a colour (and similar colours) transparent in every image.

        Parameters
        ----------
        color : tuple
            Target RGB or RGBA colour.
        threshold : float
            Maximum Euclidean distance in RGB space.

        Returns
        -------
        MultiImage
            New collection with matching pixels made transparent.

        See Also
        --------
        Image.make_color_transparent
        """
        return MultiImage(
            [img.make_color_transparent(color, threshold) for img in self.images]
        )

    def categorize_by_color(self, threshold: float = 30.0) -> List[Dict]:
        """
        Categorise pixels in every image into colour-based elements.

        Parameters
        ----------
        threshold : float
            Clustering distance threshold (see :meth:`Image.categorize_by_color`).

        Returns
        -------
        list[dict]
            One mapping per image.  Each mapping has the form::

                {
                  element_id: {
                    'average_color': [R, G, B],
                    'pixels': np.ndarray  # shape (n, 2) – rows & cols
                  }
                }

        See Also
        --------
        Image.categorize_by_color
        """
        return [img.categorize_by_color(threshold) for img in self.images]

    def recolor_element(
        self,
        mappings: List[Dict],
        element_id: int,
        new_color: Union[Tuple[int, int, int], List[int]],
    ) -> "MultiImage":
        """
        Recolour one element across all images.

        If *element_id* does not exist in a particular image's mapping the
        image is kept unchanged.

        Parameters
        ----------
        mappings : list[dict]
            Per-image mappings as returned by :meth:`categorize_by_color`.
        element_id : int
            ID of the element to recolour.
        new_color : tuple or list
            New average colour [R, G, B].

        Returns
        -------
        MultiImage
            New collection with the element recoloured.

        See Also
        --------
        Image.recolor_element
        """
        new_images = []
        for img, mapping in zip(self.images, mappings):
            if element_id in mapping:
                new_images.append(img.recolor_element(mapping, element_id, new_color))
            else:
                new_images.append(img)
        return MultiImage(new_images)

    def make_element_transparent(
        self,
        mappings: List[Dict],
        element_id: int,
    ) -> "MultiImage":
        """
        Make one element transparent across all images.

        If *element_id* does not exist in a particular image's mapping the
        image is kept unchanged.

        Parameters
        ----------
        mappings : list[dict]
            Per-image mappings as returned by :meth:`categorize_by_color`.
        element_id : int
            ID of the element to make transparent.

        Returns
        -------
        MultiImage
            New collection with the element's pixels set to alpha = 0.

        See Also
        --------
        Image.make_element_transparent
        """
        new_images = []
        for img, mapping in zip(self.images, mappings):
            if element_id in mapping:
                new_images.append(
                    img.make_element_transparent(mapping, element_id)
                )
            else:
                new_images.append(img)
        return MultiImage(new_images)

    def crop(self, x: int, y: int, width: int, height: int) -> "MultiImage":
        """
        Crop all images to the same region.

        Parameters
        ----------
        x, y : int
            Top-left corner of the crop region.
        width, height : int
            Dimensions of the crop region.

        Returns
        -------
        MultiImage
            New collection with every image cropped.

        See Also
        --------
        Image.crop
        """
        return MultiImage([img.crop(x, y, width, height) for img in self.images])

    # ------------------------------------------------------------------ #
    # Persistence                                                          #
    # ------------------------------------------------------------------ #

    def save_all(
        self, output_dir: str, prefix: str = "image", fmt: str = "PNG"
    ) -> None:
        """
        Save every image to *output_dir*.

        Parameters
        ----------
        output_dir : str
            Destination directory (created if it does not exist).
        prefix : str
            Filename prefix.
        fmt : str
            Image format understood by Pillow (e.g. ``"PNG"``, ``"JPEG"``).
        """
        os.makedirs(output_dir, exist_ok=True)
        ext = fmt.lower()
        for idx, img in enumerate(self.images):
            img.save(os.path.join(output_dir, f"{prefix}_{idx:04d}.{ext}"))
