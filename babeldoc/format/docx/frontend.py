"""DOCX frontend: parse a .docx file into a DocxDocument.

Supports both modern .docx (OOXML) and legacy binary .doc formats.
Legacy .doc text is extracted via olefile and stored in a DocxDocument.
"""

from __future__ import annotations

import logging

from docx import Document as DocxDocument_PythonDocx

from babeldoc.format.docx.il import DocxDocument
from babeldoc.format.docx.il import DocxImage
from babeldoc.format.docx.il import DocxParagraph
from babeldoc.format.docx.il import DocxRun
from babeldoc.format.docx.il import DocxTable
from babeldoc.format.docx.il import DocxTableCell
from babeldoc.format.docx.il import DocxTableRow

_OLE2_MAGIC = b"\xd0\xcf\x11\xe0"

logger = logging.getLogger(__name__)


def _parse_runs(paragraph) -> list[DocxRun]:
    """Extract run-level formatting from a python-docx paragraph."""
    runs: list[DocxRun] = []
    for run in paragraph.runs:
        font = run.font
        # Extract color hex if available
        color_hex = None
        if font.color and font.color.rgb:
            color_hex = str(font.color.rgb)
        runs.append(
            DocxRun(
                text=run.text,
                bold=font.bold,
                italic=font.italic,
                underline=font.underline,
                font_name=font.name,
                font_size=font.size,
                font_color_hex=color_hex,
            ),
        )
    return runs


def _is_old_doc_format(filepath: str) -> bool:
    """Check if a file is an old binary OLE2 .doc format."""
    with open(filepath, "rb") as f:
        header = f.read(8)
    return header[:4] == _OLE2_MAGIC


def _extract_text_from_binary_doc(filepath: str) -> list[str]:
    """Extract paragraph text from an old binary .doc file.

    Uses olefile to read the WordDocument stream and scans for
    UTF-16LE encoded text sequences.

    Returns a list of text fragments representing paragraphs.
    """
    import olefile

    ole = olefile.OleFileIO(filepath)
    data = ole.openstream("WordDocument").read()
    ole.close()

    texts: list[str] = []
    i = 0
    while i < len(data) - 1:
        if 0x20 <= data[i] <= 0x7E and data[i + 1] == 0:
            chunk_bytes = bytearray()
            start = i
            while i < len(data) - 1 and 0x20 <= data[i] <= 0x7E and data[i + 1] == 0:
                chunk_bytes.append(data[i])
                i += 2
            text = chunk_bytes.decode("ascii", errors="replace").strip()
            if len(text) >= 3:
                texts.append(text)
        elif data[i] == 0 and 0x20 <= data[i + 1] <= 0x7E:
            chunk_bytes = bytearray()
            while i < len(data) - 1 and data[i] == 0 and 0x20 <= data[i + 1] <= 0x7E:
                chunk_bytes.append(data[i + 1])
                i += 2
            text = chunk_bytes.decode("ascii", errors="replace").strip()
            if len(text) >= 3:
                texts.append(text)
        else:
            i += 1

    # Deduplicate
    seen: set[str] = set()
    unique: list[str] = []
    for t in texts:
        if t not in seen:
            seen.add(t)
            unique.append(t)

    return unique


def _read_binary_doc(filepath: str) -> DocxDocument:
    """Parse an old binary .doc into a DocxDocument.

    Extracts text via olefile and stores each fragment as a paragraph.
    This loses formatting but preserves all textual content for translation.
    """
    texts = _extract_text_from_binary_doc(filepath)
    logger.info(
        "Extracted %d text fragments from legacy .doc: %s",
        len(texts),
        filepath,
    )

    result = DocxDocument(filepath=filepath)
    for text in texts:
        result.paragraphs.append(DocxParagraph(text=text))

    return result


def read_docx(filepath: str) -> DocxDocument:
    """Read a .docx or .doc file and return a DocxDocument.

    Automatically detects legacy binary .doc format and handles it
    via text extraction (without requiring LibreOffice).

    Args:
        filepath: Path to the .docx or .doc file.

    Returns:
        A DocxDocument containing all paragraphs and tables.
    """
    if _is_old_doc_format(filepath):
        return _read_binary_doc(filepath)

    doc = DocxDocument_PythonDocx(filepath)
    result = DocxDocument(filepath=filepath)

    # Extract paragraphs
    for para in doc.paragraphs:
        text = para.text
        if not text or not text.strip():
            # Still keep empty paragraphs to preserve structure
            result.paragraphs.append(
                DocxParagraph(
                    text=text or "",
                    runs=[],
                    style_name=para.style.name if para.style else None,
                ),
            )
            continue

        runs = _parse_runs(para)
        result.paragraphs.append(
            DocxParagraph(
                text=text,
                runs=runs,
                style_name=para.style.name if para.style else None,
            ),
        )

    # Extract tables
    for table in doc.tables:
        docx_table = DocxTable()
        for row in table.rows:
            docx_row = DocxTableRow()
            for cell in row.cells:
                docx_row.cells.append(DocxTableCell(text=cell.text))
            docx_table.rows.append(docx_row)
        result.tables.append(docx_table)

    # Extract images
    _extract_images(doc, result)

    logger.info(
        "Parsed DOCX: %d paragraphs, %d tables, %d images",
        len(result.paragraphs),
        len(result.tables),
        len(result.images),
    )
    return result


def _extract_images(doc: DocxDocument_PythonDocx, result: DocxDocument) -> None:
    """Extract image blobs from a python-docx document via inline shapes."""
    seen: set[str] = set()
    for shape in doc.inline_shapes:
        try:
            r_id = shape._inline.graphic.graphicData.pic.blipFill.blip.embed
        except AttributeError:
            continue
        if r_id in seen:
            continue
        seen.add(r_id)
        try:
            image_part = doc.part.related_parts[r_id]
            blob = image_part.blob
            filename = image_part.partname.split("/")[-1]
        except (KeyError, AttributeError):
            continue
        result.images.append(
            DocxImage(
                filename=filename,
                original_data=blob,
            ),
        )
