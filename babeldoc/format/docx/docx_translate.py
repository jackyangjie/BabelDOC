"""DOCX translation orchestration.

Entry point for translating .docx files, reusing the existing
BaseTranslator from the PDF pipeline for API calls, caching,
and rate limiting.
"""

from __future__ import annotations

import io
import logging
import time
from pathlib import Path

from PIL import Image as PILImage
from PIL import ImageDraw
from PIL import ImageFont
from rapidocr_onnxruntime import RapidOCR

from babeldoc.format.docx.backend import write_docx
from babeldoc.format.docx.backend import write_dual_docx
from babeldoc.format.docx.frontend import read_docx
from babeldoc.format.pdf.document_il.utils.font_discovery import find_cjk_font
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
    translate_image_text: bool = True,
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
    if input_path.suffix.lower() not in (".doc", ".docx"):
        raise ValueError(f"Expected .doc/.docx file, got: {input_path.suffix}")

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

    # Step 3.5: Translate images (OCR + translate + overlay)
    if translate_image_text and docx_doc.images:
        _translate_docx_images(docx_doc, translator)

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


_OCR_CONFIDENCE_THRESHOLD = 0.5
_MIN_IMAGE_TEXT_LENGTH = 3


def _translate_docx_images(docx_doc, translator: BaseTranslator) -> None:
    """OCR and translate text in embedded DOCX images."""
    cjk_font_path = find_cjk_font()
    if cjk_font_path is None:
        logger.warning("No CJK font found; image translation may render as boxes")

    ocr = RapidOCR()
    logger.info(
        "Translating text in %d images for DOCX",
        len(docx_doc.images),
    )

    for img in docx_doc.images:
        if img.original_data is None:
            continue
        try:
            translated = _process_single_image(
                img.original_data, ocr, translator, cjk_font_path
            )
            if translated is not None:
                img.translated_data = translated
                logger.info("DOCX image %s: text translated", img.filename)
        except Exception:
            logger.exception("Failed to translate image %s", img.filename)


def _process_single_image(
    image_data: bytes,
    ocr: RapidOCR,
    translator: BaseTranslator,
    cjk_font_path: str | None,
) -> bytes | None:
    """OCR, translate, and overlay text on a single image."""
    pil_image = PILImage.open(io.BytesIO(image_data))
    if pil_image.mode not in ("RGB", "RGBA"):
        pil_image = pil_image.convert("RGB")

    result, _ = ocr(image_data)
    if not result:
        return None

    ocr_results = []
    for box, text, confidence in result:
        if confidence < _OCR_CONFIDENCE_THRESHOLD:
            continue
        text = text.strip()
        if not text:
            continue
        if isinstance(box, list) and len(box) == 4 and isinstance(box[0], list):
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            flat_box = [min(xs), min(ys), max(xs), max(ys)]
        else:
            flat_box = list(box)
        ocr_results.append((flat_box, text, float(confidence)))

    unique_texts = list({text for _, text, _ in ocr_results})
    if sum(len(t) for t in unique_texts) < _MIN_IMAGE_TEXT_LENGTH:
        return None

    translations = []
    for text in unique_texts:
        try:
            translated = translator.translate(text)
            translations.append(translated)
        except Exception:
            logger.warning("Failed to translate image text: %s", text)
            translations.append(text)

    text_to_translation = dict(zip(unique_texts, translations, strict=False))

    draw = ImageDraw.Draw(pil_image)
    for box, original_text, _confidence in ocr_results:
        translated = text_to_translation.get(original_text, original_text)
        x1, y1, x2, y2 = box
        x1_i, y1_i = max(0, int(x1)), max(0, int(y1))
        x2_i, y2_i = min(pil_image.width, int(x2)), min(pil_image.height, int(y2))
        if x2_i <= x1_i or y2_i <= y1_i:
            continue

        region_w, region_h = x2_i - x1_i, y2_i - y1_i
        bg_color = (255, 255, 255)
        draw.rectangle([x1_i, y1_i, x2_i, y2_i], fill=bg_color)

        font_size = max(int(region_h * 0.55), 8)
        try:
            if cjk_font_path:
                font = ImageFont.truetype(cjk_font_path, size=font_size)
            else:
                font = ImageFont.load_default()
        except (OSError, TypeError):
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), translated, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        if text_w > region_w * 2:
            continue

        tx = x1_i + (region_w - text_w) // 2
        ty = y1_i + (region_h - text_h) // 2
        draw.text((tx, ty), translated, fill=(0, 0, 0), font=font)

    buf = io.BytesIO()
    pil_image.save(buf, format="PNG")
    return buf.getvalue()
