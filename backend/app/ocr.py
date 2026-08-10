"""Local OCR helpers for scanned answer sheets.

The application deliberately calls the Tesseract executable on the same machine
as the API.  No answer-sheet image or extracted text is sent to a third party.
"""

import os
from io import BytesIO
from pathlib import Path

import fitz
from PIL import Image, ImageEnhance, ImageOps
import pytesseract


class OCRUnavailableError(RuntimeError):
    """Raised when the local Tesseract executable cannot be used."""


def _prepare_image(image: Image.Image) -> Image.Image:
    """Make a scanned page more legible without aggressively altering handwriting."""
    grayscale = ImageOps.grayscale(image)
    normalized = ImageOps.autocontrast(grayscale)
    enhanced = ImageEnhance.Contrast(normalized).enhance(1.35)
    return enhanced.resize((enhanced.width * 2, enhanced.height * 2), Image.Resampling.LANCZOS)


def _read_image(image: Image.Image) -> str:
    command = os.getenv("TESSERACT_CMD")
    if command:
        pytesseract.pytesseract.tesseract_cmd = command
    try:
        return pytesseract.image_to_string(_prepare_image(image), config="--oem 1 --psm 6")
    except pytesseract.TesseractNotFoundError as error:
        raise OCRUnavailableError(
            "Tesseract is not installed or is not on PATH. Install it locally, then restart the API."
        ) from error


def extract_text(file_path: Path) -> str:
    """Extract text from an image or each page of a PDF using local Tesseract."""
    if file_path.suffix.lower() == ".pdf":
        try:
            document = fitz.open(file_path)
        except fitz.FileDataError as error:
            raise ValueError("The uploaded PDF could not be read.") from error
        try:
            pages = []
            for page in document:
                # 200 DPI is a good quality/speed balance for typical answer sheets.
                pixmap = page.get_pixmap(matrix=fitz.Matrix(200 / 72, 200 / 72), alpha=False)
                with Image.open(BytesIO(pixmap.tobytes("png"))) as image:
                    pages.append(_read_image(image))
            return "\n\n".join(page.strip() for page in pages if page.strip()).strip()
        finally:
            document.close()

    try:
        with Image.open(file_path) as image:
            return _read_image(image).strip()
    except (Image.UnidentifiedImageError, OSError) as error:
        raise ValueError("The uploaded image could not be read.") from error
