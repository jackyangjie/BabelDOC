"""DOCX frontend: parse a .docx file into a DocxDocument."""

from __future__ import annotations

import logging

from docx import Document as DocxDocument_PythonDocx

from babeldoc.format.docx.il import DocxDocument
from babeldoc.format.docx.il import DocxParagraph
from babeldoc.format.docx.il import DocxRun
from babeldoc.format.docx.il import DocxTable
from babeldoc.format.docx.il import DocxTableCell
from babeldoc.format.docx.il import DocxTableRow

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


def read_docx(filepath: str) -> DocxDocument:
    """Read a .docx file and return a DocxDocument with extracted paragraphs and tables.

    Args:
        filepath: Path to the .docx file.

    Returns:
        A DocxDocument containing all paragraphs and tables.
    """
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

    logger.info(
        "Parsed DOCX: %d paragraphs, %d tables",
        len(result.paragraphs),
        len(result.tables),
    )
    return result
