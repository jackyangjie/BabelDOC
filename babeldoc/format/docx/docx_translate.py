"""DOCX translation orchestration.

Entry point for translating .docx files, reusing the existing
BaseTranslator from the PDF pipeline for API calls, caching,
and rate limiting.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from babeldoc.format.docx.backend import write_docx
from babeldoc.format.docx.backend import write_dual_docx
from babeldoc.format.docx.frontend import read_docx
from babeldoc.translator.translator import BaseTranslator

logger = logging.getLogger(__name__)


def translate_docx(
    input_file: str,
    output_dir: str | None,
    translator: BaseTranslator,
    lang_in: str,
    lang_out: str,
    no_dual: bool = False,
    no_mono: bool = False,
) -> dict:
    """Translate a .docx file.

    Orchestrates the DOCX translation pipeline:
    1. Parse the DOCX file into a DocxDocument
    2. Translate each paragraph and table cell via BaseTranslator
    3. Write the translated document(s)

    When ``no_dual`` is false (default), a bilingual .docx is produced
    alongside the monolingual one, mirroring the PDF pipeline behaviour.

    Args:
        input_file: Path to the source .docx file.
        output_dir: Output directory. If None, uses the source file's directory.
        translator: A BaseTranslator instance (e.g. OpenAITranslator).
        lang_in: Source language code.
        lang_out: Target language code.
        no_dual: If True, skip dual-language output.
        no_mono: If True, skip monolingual output.

    Returns:
        A dict with translation result info (paths, timing).
    """
    start_time = time.time()

    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    if input_path.suffix.lower() != ".docx":
        raise ValueError(f"Expected .docx file, got: {input_path.suffix}")

    output_dir_path = Path(output_dir) if output_dir else input_path.parent
    output_dir_path.mkdir(parents=True, exist_ok=True)

    stem = input_path.stem
    mono_output_path: Path | None = None
    dual_output_path: Path | None = None

    # Step 1: Parse DOCX
    logger.info("Parsing DOCX: %s", input_file)
    docx_doc = read_docx(str(input_path))
    total_items = len(docx_doc.paragraphs) + sum(
        len(row.cells) for t in docx_doc.tables for row in t.rows
    )
    logger.info(
        "Found %d paragraphs and %d table cells to translate",
        len(docx_doc.paragraphs),
        total_items - len(docx_doc.paragraphs),
    )

    # Step 2: Translate paragraphs
    _translate_paragraphs(docx_doc, translator)

    # Step 3: Translate table cells
    _translate_table_cells(docx_doc, translator)

    # Step 4: Write output(s) — mirror PDF dual/mono behaviour
    if not no_mono:
        mono_filename = f"{stem}_translated.docx"
        mono_output_path = output_dir_path / mono_filename
        write_docx(docx_doc, str(mono_output_path))
        logger.info("Monolingual DOCX saved to: %s", mono_output_path)

    if not no_dual:
        dual_filename = f"{stem}_dual.docx"
        dual_output_path = output_dir_path / dual_filename
        write_dual_docx(docx_doc, str(dual_output_path))
        logger.info("Dual-language DOCX saved to: %s", dual_output_path)

    elapsed = time.time() - start_time
    logger.info("DOCX translation complete in %.2f seconds", elapsed)

    return {
        "output_path": str(mono_output_path) if mono_output_path else None,
        "dual_output_path": str(dual_output_path) if dual_output_path else None,
        "total_seconds": elapsed,
        "input_file": input_file,
        "lang_in": lang_in,
        "lang_out": lang_out,
    }


def _translate_paragraphs(docx_doc, translator: BaseTranslator) -> None:
    """Translate all paragraphs in the DocxDocument."""
    total = len(docx_doc.paragraphs)
    for i, para in enumerate(docx_doc.paragraphs):
        text = para.text.strip()
        if not text:
            continue
        try:
            translated = translator.translate(text)
            para.translated_text = translated
        except Exception as e:
            logger.exception("Failed to translate paragraph %d: %s", i, e)
            para.translated_text = text

        if (i + 1) % 50 == 0:
            logger.debug("Translated %d/%d paragraphs", i + 1, total)


def _translate_table_cells(docx_doc, translator: BaseTranslator) -> None:
    """Translate all table cells in the DocxDocument."""
    total_cells = sum(len(row.cells) for t in docx_doc.tables for row in t.rows)
    translated = 0
    for table in docx_doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text = cell.text.strip()
                if not text:
                    continue
                try:
                    translated_text = translator.translate(text)
                    cell.translated_text = translated_text
                except Exception as e:
                    logger.exception(
                        "Failed to translate table cell: %s",
                        e,
                    )
                    cell.translated_text = text
                translated += 1
                if translated % 50 == 0:
                    logger.debug(
                        "Translated %d/%d table cells",
                        translated,
                        total_cells,
                    )
