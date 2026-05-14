"""PPTX translation orchestration.

Entry point for translating .pptx files, reusing the existing
BaseTranslator from the PDF pipeline for API calls, caching,
and rate limiting.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from babeldoc.format.pptx.backend import write_dual_pptx
from babeldoc.format.pptx.backend import write_pptx
from babeldoc.format.pptx.frontend import read_pptx
from babeldoc.translator.translator import BaseTranslator

logger = logging.getLogger(__name__)


def translate_pptx(
    input_file: str,
    output_dir: str | None,
    translator: BaseTranslator,
    lang_in: str,
    lang_out: str,
    no_dual: bool = False,
    no_mono: bool = False,
) -> dict:
    """Translate a .pptx file.

    Orchestrates the PPTX translation pipeline:
    1. Parse the PPTX file into a PptxDocument
    2. Translate each shape and table cell via BaseTranslator
    3. Write the translated document(s)

    When ``no_dual`` is false (default), a bilingual .pptx is produced
    alongside the monolingual one, mirroring the DOCX pipeline behaviour.

    Args:
        input_file: Path to the source .pptx file.
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
    if input_path.suffix.lower() not in (".ppt", ".pptx"):
        raise ValueError(f"Expected .ppt/.pptx file, got: {input_path.suffix}")

    output_dir_path = Path(output_dir) if output_dir else input_path.parent
    output_dir_path.mkdir(parents=True, exist_ok=True)

    stem = input_path.stem
    mono_output_path: Path | None = None
    dual_output_path: Path | None = None

    # Step 1: Parse PPTX
    logger.info("Parsing PPTX: %s", input_file)
    pptx_doc = read_pptx(str(input_path))
    total_shapes = sum(len(s.shapes) for s in pptx_doc.slides)
    total_cells = sum(
        len(row.cells)
        for s in pptx_doc.slides
        for t in s.tables
        for row in t.rows
    )
    logger.info(
        "Found %d shapes and %d table cells to translate across %d slides",
        total_shapes,
        total_cells,
        len(pptx_doc.slides),
    )

    # Step 2: Translate shapes
    _translate_shapes(pptx_doc, translator)

    # Step 3: Translate table cells
    _translate_table_cells(pptx_doc, translator)

    # Step 4: Write output(s) — mirror DOCX dual/mono behaviour
    if not no_mono:
        mono_filename = f"{stem}_translated.pptx"
        mono_output_path = output_dir_path / mono_filename
        write_pptx(pptx_doc, str(mono_output_path))
        logger.info("Monolingual PPTX saved to: %s", mono_output_path)

    if not no_dual:
        dual_filename = f"{stem}_dual.pptx"
        dual_output_path = output_dir_path / dual_filename
        write_dual_pptx(pptx_doc, str(dual_output_path))
        logger.info("Dual-language PPTX saved to: %s", dual_output_path)

    elapsed = time.time() - start_time
    logger.info("PPTX translation complete in %.2f seconds", elapsed)

    # Clean up any LibreOffice-converted temp file
    _cleanup_converted_source(pptx_doc)

    return {
        "output_path": str(mono_output_path) if mono_output_path else None,
        "dual_output_path": str(dual_output_path) if dual_output_path else None,
        "total_seconds": elapsed,
        "input_file": input_file,
        "lang_in": lang_in,
        "lang_out": lang_out,
    }


def _cleanup_converted_source(pptx_doc) -> None:
    """Remove temporary converted .pptx file from LibreOffice."""
    src_path = getattr(pptx_doc, "_pptx_source_path", None)
    if src_path:
        try:
            Path(src_path).unlink(missing_ok=True)
        except Exception:
            pass


def _translate_shapes(pptx_doc, translator: BaseTranslator) -> None:
    """Translate all shape text in the PptxDocument."""
    total = sum(len(s.shapes) for s in pptx_doc.slides)
    translated = 0
    for slide in pptx_doc.slides:
        for shape in slide.shapes:
            text = shape.text.strip()
            if not text:
                continue
            try:
                translated_text = translator.translate(text)
                shape.translated_text = translated_text
            except Exception as e:
                logger.exception(
                    "Failed to translate shape text: %s",
                    e,
                )
                shape.translated_text = text

            translated += 1
            if translated % 50 == 0:
                logger.debug("Translated %d/%d shapes", translated, total)


def _translate_table_cells(pptx_doc, translator: BaseTranslator) -> None:
    """Translate all table cells in the PptxDocument."""
    total_cells = sum(
        len(row.cells)
        for s in pptx_doc.slides
        for t in s.tables
        for row in t.rows
    )
    translated = 0
    for slide in pptx_doc.slides:
        for table in slide.tables:
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
    if total_cells > 0:
        logger.debug("Translated %d table cells", translated)
