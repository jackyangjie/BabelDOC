"""PPTX-specific intermediate layer data model.

Simplified data model for PPTX presentations, designed to carry enough
information for translation while being independent of the PDF-centric
IL model in babeldoc.format.pdf.document_il.il_version_1.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field


@dataclass(slots=True)
class PptxTableCell:
    """A single cell in a PPTX table."""

    text: str
    translated_text: str | None = None


@dataclass(slots=True)
class PptxTableRow:
    """A row in a PPTX table."""

    cells: list[PptxTableCell] = field(default_factory=list)


@dataclass(slots=True)
class PptxTable:
    """A table in a PPTX presentation."""

    rows: list[PptxTableRow] = field(default_factory=list)


@dataclass(slots=True)
class PptxShape:
    """A shape (text box, auto shape) on a slide that can contain text.

    Attributes:
        text: The full text content (concatenated from paragraphs).
        translated_text: The translated text for mono replacement.
    """

    text: str
    translated_text: str | None = None


@dataclass(slots=True)
class PptxSlide:
    """A single slide in a PPTX presentation.

    Attributes:
        shapes: Text-containing shapes on this slide.
        tables: Tables on this slide.
    """

    shapes: list[PptxShape] = field(default_factory=list)
    tables: list[PptxTable] = field(default_factory=list)


@dataclass(slots=True)
class PptxDocument:
    """Parsed representation of a PPTX file for translation purposes.

    Attributes:
        filepath: Path to the original source file (.ppt or .pptx).
        slides: List of parsed slides.
        _pptx_source_path: Internal: path to a converted .pptx to use as
            template when the original file is old binary .ppt format.
    """

    filepath: str
    slides: list[PptxSlide] = field(default_factory=list)
    _pptx_source_path: str | None = field(default=None, repr=False)
