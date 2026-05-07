"""
src/back – image processing backend.

Public API
----------
MultiImage    Main class.  Holds a collection of Image objects and exposes
              every Image operation as a batch method.
Image         Single image (pixel array + operations).
ImageReader   Populate a MultiImage from a single image file.
ImageWriter   Save each image of a MultiImage to individual files.
PdfReader     Populate a MultiImage from a PDF file (one page → one Image).
PdfWriter     Save a MultiImage as a multi-page PDF (requires PyMuPDF).
GraphReader   Render a CSV/TSV/JSON/Excel file as a chart image (requires
              pandas + matplotlib).
GraphConfig   Dataclass controlling chart rendering parameters.
"""
from .image import Image
from .multiimage import MultiImage
from .image_reader import ImageReader
from .image_writer import ImageWriter
from .pdf_reader import PdfReader
from .pdf_writer import PdfWriter
from .graph_reader import GraphReader, GraphConfig

__all__ = [
    "MultiImage",
    "Image",
    "ImageReader",
    "ImageWriter",
    "PdfReader",
    "PdfWriter",
    "GraphReader",
    "GraphConfig",
]
