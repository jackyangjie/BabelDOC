"""DOCX-specific intermediate layer data model.

Simplified data model for DOCX documents, designed to carry enough
information for translation while being independent of the PDF-centric
IL model in babeldoc.format.pdf.document_il.il_version_1.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field


@dataclass(slots=True)
class DocxRun:
    """A run of text with uniform formatting within a paragraph."""

    text: str
    bold: bool | None = None
    italic: bool | None = None
    underline: bool | None = None
    font_name: str | None = None
    font_size: int | None = None
    font_color_hex: str | None = None


@dataclass(slots=True)
class DocxParagraph:
    """A single paragraph in a DOCX document."""

    text: str
    runs: list[DocxRun] = field(default_factory=list)
    style_name: str | None = None
    translated_text: str | None = None


@dataclass(slots=True)
class DocxTableCell:
    """A single cell in a DOCX table."""

    text: str
    translated_text: str | None = None


@dataclass(slots=True)
class DocxTableRow:
    """A row in a DOCX table."""

    cells: list[DocxTableCell] = field(default_factory=list)


@dataclass(slots=True)
class DocxTable:
    """A table in a DOCX document."""

    rows: list[DocxTableRow] = field(default_factory=list)


@dataclass(slots=True)
class DocxDocument:
    """Parsed representation of a DOCX file for translation purposes."""

    filepath: str
    paragraphs: list[DocxParagraph] = field(default_factory=list)
    tables: list[DocxTable] = field(default_factory=list)
