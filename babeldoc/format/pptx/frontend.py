"""PPTX frontend: parse a .pptx file into a PptxDocument.

Supports both modern .pptx (OOXML) and legacy binary .ppt formats.
Legacy .ppt is converted via LibreOffice (if available) for full
formatting and image preservation, falling back to olefile text extraction.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from pptx import Presentation as PptxPresentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from babeldoc.format.pptx.il import PptxDocument
from babeldoc.format.pptx.il import PptxShape
from babeldoc.format.pptx.il import PptxSlide
from babeldoc.format.pptx.il import PptxTable
from babeldoc.format.pptx.il import PptxTableCell
from babeldoc.format.pptx.il import PptxTableRow

logger = logging.getLogger(__name__)

# Magic bytes for old binary OLE2 format
_OLE2_MAGIC = b"\xd0\xcf\x11\xe0"

# Patterns that indicate non-content text in binary PPT extraction
_NOISE_PATTERNS = re.compile(
    r"^(___PPT\d+|Rectangle \d+|Oval \d+|TextBox \d+|Text Box \d+|"
    r"Picture \d+|Table \d+|(Times )?New Roman|Arial[^a-z]|"
    r"Wingdings|Symbol|Courier|Tahoma|Verdana|"
    r"http[s]?://|www\.|Slide\d+|Title\s*\d*|"
    r"Subtitle\s*\d*|Blank Presentation|"
    r"[!(),./:;?${}\[\]\\|`~@#%^&*+=<>\"\']+)$",
    re.IGNORECASE,
)


def _is_valid_text_fragment(text: str) -> bool:
    """Check if extracted text is a valid content fragment (vs noise).

    Real slide text is typically multi-word phrases or sentences.
    Single words, URLs, shape names, and font names are filtered out.
    """
    if len(text) < 8:
        return False
    if _NOISE_PATTERNS.match(text):
        return False
    if text.startswith("___PPT") or text.startswith("http"):
        return False
    if text.isdigit():
        return False
    # Must contain at least 5 alphabetic characters (real sentence has words)
    alpha_count = sum(1 for c in text if c.isalpha())
    if alpha_count < 5:
        return False
    # Must contain at least one space (multi-word = real content)
    if " " not in text and alpha_count < 10:
        return False
    return True

# Shapes that can contain text
_SHAPES_WITH_TEXTFRAME = (
    "SHAPE",
    "AUTO_SHAPE",
    "ROUNDED_RECTANGLE",
    "OVAL",
    "DIAMOND",
    "RECTANGLE",
    "PLACEHOLDER",
)


def _has_text_content(shape) -> bool:
    """Check if a shape has a text frame with non-empty text."""
    if not shape.has_text_frame:
        return False
    text = shape.text_frame.text
    return bool(text and text.strip())


def _is_text_container(shape) -> bool:
    """Check if shape type can contain text."""
    try:
        st = shape.shape_type
        name = str(st).split(".")[-1] if st is not None else ""
        return name in _SHAPES_WITH_TEXTFRAME or shape.has_text_frame
    except Exception:
        return shape.has_text_frame


def _extract_text_from_shape(shape) -> str:
    """Extract the full text from a shape's text frame."""
    if not shape.has_text_frame:
        return ""
    return shape.text_frame.text


def _parse_slide(slide) -> PptxSlide:
    """Parse a single slide into a PptxSlide, extracting text shapes and tables."""
    pptx_slide = PptxSlide()

    def _walk_shapes(shapes):
        for shape in shapes:
            if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                _walk_shapes(shape.shapes)
            elif shape.has_table:
                table = shape.table
                pptx_table = PptxTable()
                for row in table.rows:
                    pptx_row = PptxTableRow()
                    for cell in row.cells:
                        pptx_row.cells.append(PptxTableCell(text=cell.text))
                    pptx_table.rows.append(pptx_row)
                pptx_slide.tables.append(pptx_table)
            elif _has_text_content(shape):
                text = _extract_text_from_shape(shape)
                if text.strip():
                    pptx_slide.shapes.append(PptxShape(text=text))

    _walk_shapes(slide.shapes)
    return pptx_slide


def _is_old_ppt_format(filepath: str) -> bool:
    """Check if a file is an old binary OLE2 .ppt format."""
    with open(filepath, "rb") as f:
        header = f.read(8)
    return header[:4] == _OLE2_MAGIC


def _extract_text_from_binary_ppt(filepath: str) -> list[str]:
    """Extract slide text from an old binary .ppt file.

    Uses olefile to read the PowerPoint Document stream, then scans for
    UTF-16LE encoded text sequences (the format stores text as
    contiguous Unicode runs).

    Returns a list of text fragments, one per slide or text element.
    """
    import olefile

    ole = olefile.OleFileIO(filepath)
    data = ole.openstream("PowerPoint Document").read()
    ole.close()

    texts: list[str] = []

    # Scan UTF-16LE text runs
    i = 0
    while i < len(data) - 1:
        # Check for ASCII-range char in UTF-16LE
        if 0x20 <= data[i] <= 0x7E and data[i + 1] == 0:
            start = i
            chunk_bytes = bytearray()
            while (
                i < len(data) - 1
                and 0x20 <= data[i] <= 0x7E
                and data[i + 1] == 0
            ):
                chunk_bytes.append(data[i])
                i += 2
            extracted_text = chunk_bytes.decode("ascii", errors="replace").strip()
            if _is_valid_text_fragment(extracted_text):
                texts.append(extracted_text)
        elif data[i] == 0 and 0x20 <= data[i + 1] <= 0x7E:
            # Also try reversed byte order (big-endian UTF-16)
            start = i
            chunk_bytes = bytearray()
            while (
                i < len(data) - 1
                and data[i] == 0
                and 0x20 <= data[i + 1] <= 0x7E
            ):
                chunk_bytes.append(data[i + 1])
                i += 2
            extracted_text = chunk_bytes.decode("ascii", errors="replace").strip()
            if _is_valid_text_fragment(extracted_text):
                texts.append(extracted_text)
        else:
            i += 1

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_texts: list[str] = []
    for t in texts:
        if t not in seen:
            seen.add(t)
            unique_texts.append(t)

    return unique_texts


def _convert_ppt_to_pptx(filepath: str) -> str | None:
    """Convert old binary .ppt to .pptx using LibreOffice.

    LibreOffice ignores --outdir and outputs to the current working
    directory with the same base name as the input file.
    We detect the output path and move it to a temp location.

    Returns path to the converted .pptx file, or None if conversion fails.
    """
    try:
        stem = Path(filepath).stem
        cwd = Path.cwd()
        expected_out = cwd / f"{stem}.pptx"

        result = subprocess.run(
            [
                "soffice",
                "--headless",
                "--convert-to", "pptx",
                filepath,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            logger.warning(
                "LibreOffice conversion failed: %s", result.stderr,
            )
            return None

        if expected_out.exists():
            # Move to a named temp file so we control cleanup
            tmp_path = cwd / f"__babeldoc_conv_{stem}.pptx"
            shutil.move(str(expected_out), str(tmp_path))
            logger.info("Converted legacy .ppt to .pptx via LibreOffice")
            return str(tmp_path)

        logger.warning(
            "LibreOffice conversion: expected output not found at %s",
            expected_out,
        )
        return None
    except Exception as e:
        logger.warning("LibreOffice conversion error: %s", e)
        return None


def _read_binary_ppt(filepath: str) -> PptxDocument:
    """Parse an old binary .ppt into a PptxDocument.

    First tries LibreOffice conversion for full layout and image preservation.
    Falls back to olefile text extraction if conversion is unavailable.
    """
    # Try LibreOffice conversion first
    pptx_path = _convert_ppt_to_pptx(filepath)
    if pptx_path:
        try:
            doc = _read_pptx_file(pptx_path)
            doc.filepath = filepath
            doc._pptx_source_path = pptx_path
            return doc
        except Exception as e:
            logger.warning(
                "Failed to parse converted .pptx, falling back to text extraction: %s",
                e,
            )
            Path(pptx_path).unlink(missing_ok=True)

    # Fallback: olefile text extraction
    texts = _extract_text_from_binary_ppt(filepath)
    logger.info(
        "Extracted %d text fragments from legacy .ppt (olefile fallback): %s",
        len(texts),
        filepath,
    )

    # Merge consecutive fragments into longer paragraphs
    merged: list[str] = []
    current = ""
    for t in texts:
        if not current:
            current = t
        elif len(t) < 20 and current:
            current += " " + t
        elif current and (current.rstrip()[-1] in ".!?" or len(current) > 200):
            merged.append(current.strip())
            current = t
        else:
            current += " " + t
    if current:
        merged.append(current.strip())

    logger.info("Merged into %d paragraphs", len(merged))

    result = PptxDocument(filepath=filepath)
    slide = PptxSlide()
    for text in merged:
        slide.shapes.append(PptxShape(text=text))
    result.slides.append(slide)

    return result


def _read_pptx_file(filepath: str) -> PptxDocument:
    """Parse a modern .pptx file using python-pptx."""
    prs = PptxPresentation(filepath)
    result = PptxDocument(filepath=filepath)

    for slide in prs.slides:
        pptx_slide = _parse_slide(slide)
        result.slides.append(pptx_slide)

    total_shapes = sum(len(s.shapes) for s in result.slides)
    total_tables = sum(len(s.tables) for s in result.slides)
    total_cells = sum(
        len(row.cells)
        for s in result.slides
        for t in s.tables
        for row in t.rows
    )
    logger.info(
        "Parsed PPTX: %d slides, %d text shapes, %d tables, %d table cells",
        len(result.slides),
        total_shapes,
        total_tables,
        total_cells,
    )
    return result


def read_pptx(filepath: str) -> PptxDocument:
    """Read a .pptx or .ppt file and return a PptxDocument.

    Automatically detects legacy binary .ppt format and converts it via
    LibreOffice for full layout and image preservation (falls back to
    olefile-based text extraction if LibreOffice is unavailable).

    Args:
        filepath: Path to the .pptx or .ppt file.

    Returns:
        A PptxDocument containing all slides, shapes, and tables.
    """
    if _is_old_ppt_format(filepath):
        return _read_binary_ppt(filepath)

    return _read_pptx_file(filepath)
