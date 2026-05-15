"""DOCX backend: write translated text back into a .docx file.

Strategy: open the original document, walk paragraphs and tables in
parallel with the DocxDocument, and replace text content while preserving
the original document structure and formatting.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path

from docx import Document as DocxDocument_PythonDocx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from babeldoc.format.docx.il import DocxDocument

logger = logging.getLogger(__name__)


def write_docx(
    docx_doc: DocxDocument,
    output_path: str,
) -> None:
    """Write translated text into a new .docx file.

    Opens the original document, replaces paragraph and table cell text
    with translated content, and saves to *output_path*.

    Args:
        docx_doc: The DocxDocument containing translated text.
        output_path: Path to write the translated .docx file.
    """
    # Work on a copy of the original to preserve structure/formatting
    tmpfd = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
    try:
        shutil.copy2(docx_doc.filepath, tmpfd.name)
        tmpfd.close()

        doc = DocxDocument_PythonDocx(tmpfd.name)

        _replace_paragraphs(doc, docx_doc)
        _replace_table_cells(doc, docx_doc)
        _replace_images(doc, docx_doc)

        doc.save(output_path)
        logger.info("Translated DOCX saved to: %s", output_path)
    finally:
        Path(tmpfd.name).unlink(missing_ok=True)


def _replace_paragraphs(doc: DocxDocument_PythonDocx, docx_doc: DocxDocument) -> None:
    """Walk document paragraphs and inject translated text."""
    doc_paragraphs = list(doc.paragraphs)
    for i, para_info in enumerate(docx_doc.paragraphs):
        if i >= len(doc_paragraphs):
            logger.warning(
                "Paragraph index %d exceeds document paragraphs (%d), skipping",
                i,
                len(doc_paragraphs),
            )
            break
        translated = para_info.translated_text
        if translated is None or translated == para_info.text:
            continue
        if not translated.strip():
            continue

        wp = doc_paragraphs[i]
        _replace_paragraph_text(wp, translated)


def _has_image_run(run) -> bool:
    """Check if a run contains embedded images (drawings)."""
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    return bool(run._element.findall(f".//{ns}drawing"))


def _replace_paragraph_text(paragraph, new_text: str) -> None:
    """Replace paragraph text while preserving formatting and images.

    Only clears text-carrying runs. Runs that contain embedded images
    (drawings) are preserved intact.
    """
    original_runs = list(paragraph.runs)
    # Find the first text-carrying run (not an image run)
    first_text_run = None
    for r in original_runs:
        if not _has_image_run(r):
            first_text_run = r
            break

    fmt = {}
    if first_text_run is not None:
        for attr in ("bold", "italic", "underline", "size", "name"):
            try:
                val = getattr(first_text_run.font, attr, None)
                if val is not None:
                    fmt[attr] = val
            except Exception:
                pass
        try:
            if first_text_run.font.color and first_text_run.font.color.rgb:
                fmt["color_rgb"] = first_text_run.font.color.rgb
        except Exception:
            pass

    for run in original_runs:
        if not _has_image_run(run):
            run._element.getparent().remove(run._element)

    new_run = paragraph.add_run(new_text)

    for key, val in fmt.items():
        if val is None:
            continue
        try:
            if key == "bold":
                new_run.font.bold = val
            elif key == "italic":
                new_run.font.italic = val
            elif key == "size":
                new_run.font.size = val
            elif key == "name":
                new_run.font.name = val
            elif key == "color_rgb":
                new_run.font.color.rgb = val
        except Exception:
            pass


def _replace_table_cells(doc: DocxDocument_PythonDocx, docx_doc: DocxDocument) -> None:
    """Walk document tables and inject translated cell text."""
    doc_tables = list(doc.tables)
    for t_idx, table_info in enumerate(docx_doc.tables):
        if t_idx >= len(doc_tables):
            logger.warning(
                "Table index %d exceeds document tables (%d), skipping",
                t_idx,
                len(doc_tables),
            )
            break
        dt = doc_tables[t_idx]
        for r_idx, row_info in enumerate(table_info.rows):
            if r_idx >= len(dt.rows):
                break
            for c_idx, cell_info in enumerate(row_info.cells):
                if c_idx >= len(dt.rows[r_idx].cells):
                    break
                translated = cell_info.translated_text
                if translated and translated.strip():
                    # python-docx cell text replacement
                    cell = dt.rows[r_idx].cells[c_idx]
                    for para in cell.paragraphs:
                        for run in para.runs:
                            run.text = ""
                    if cell.paragraphs:
                        cell.paragraphs[0].add_run(translated)


# ---------------------------------------------------------------------------
# Dual-language (bilingual) support — side-by-side via two-column + column breaks
# ---------------------------------------------------------------------------

_DUAL_TRANSLATION_COLOR_HEX = "2E75B6"


def _set_two_columns(doc: DocxDocument_PythonDocx) -> None:
    """Set all sections of the document to two-column equal-width layout."""
    for section in doc.sections:
        sect_pr = section._sectPr
        for existing_cols in sect_pr.findall(qn("w:cols")):
            sect_pr.remove(existing_cols)
        cols = OxmlElement("w:cols")
        cols.set(qn("w:num"), "2")
        cols.set(qn("w:equalWidth"), "true")
        cols.set(qn("w:space"), "480")
        sect_pr.append(cols)


def _insert_column_break_after(element) -> None:
    """Insert an empty paragraph that contains only a column break.

    In a two-column layout this moves subsequent content to the next column.
    The new paragraph is placed immediately after *element* in the XML tree.
    """
    col_break_p = OxmlElement("w:p")
    run = OxmlElement("w:r")
    br = OxmlElement("w:br")
    br.set(qn("w:type"), "column")
    run.append(br)
    col_break_p.append(run)
    element.addnext(col_break_p)


def _make_translation_paragraph(text: str) -> OxmlElement:
    """Build a ``<w:p>`` element containing *text* styled in the dual
    translation colour."""
    p = OxmlElement("w:p")
    r = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), _DUAL_TRANSLATION_COLOR_HEX)
    rpr.append(color)
    r.append(rpr)
    t_el = OxmlElement("w:t")
    t_el.set(qn("xml:space"), "preserve")
    t_el.text = text
    r.append(t_el)
    p.append(r)
    return p


def _inject_dual_paragraphs(
    doc: DocxDocument_PythonDocx, docx_doc: DocxDocument
) -> None:
    """Walk paragraphs in reverse and insert column-break-delimited
    translation pairs for dual-column bilingual display.

    For each paragraph with a non-trivial translation:

        [original text]  ← original paragraph (unchanged)
        [column break]
        [translated text (blue)]  ← inserted
        [column break]            ← inserted (back to left column)
        [next original]

    Reverse iteration avoids index corruption caused by XML insertion.
    """
    doc_paragraphs = list(doc.paragraphs)
    for i in range(len(docx_doc.paragraphs) - 1, -1, -1):
        if i >= len(doc_paragraphs):
            continue
        para_info = docx_doc.paragraphs[i]
        translated = para_info.translated_text
        if not translated or not translated.strip():
            continue
        if translated == para_info.text:
            continue

        wp_element = doc_paragraphs[i]._element

        # (a) column break → right column
        _insert_column_break_after(wp_element)
        col_break_1 = wp_element.getnext()

        # (b) translation paragraph (blue) after the column break
        trans_p = _make_translation_paragraph(translated)
        col_break_1.addnext(trans_p)

        # (c) column break → back to left column for next original
        _insert_column_break_after(trans_p)


def _replace_table_cells_keep_original(
    doc: DocxDocument_PythonDocx,
    docx_doc: DocxDocument,
) -> None:
    """For dual output: keep original cell text and append the translation
    as a new blue-coloured paragraph inside the same cell."""
    doc_tables = list(doc.tables)
    for t_idx, table_info in enumerate(docx_doc.tables):
        if t_idx >= len(doc_tables):
            break
        dt = doc_tables[t_idx]
        for r_idx, row_info in enumerate(table_info.rows):
            if r_idx >= len(dt.rows):
                break
            for c_idx, cell_info in enumerate(row_info.cells):
                if c_idx >= len(dt.rows[r_idx].cells):
                    break
                translated = cell_info.translated_text
                if not translated or not translated.strip():
                    continue
                if translated == cell_info.text:
                    continue
                cell = dt.rows[r_idx].cells[c_idx]
                cell._element.append(_make_translation_paragraph(translated))


def write_dual_docx(
    docx_doc: DocxDocument,
    output_path: str,
) -> None:
    """Write a dual-language .docx with original and translation in a
    side-by-side two-column layout.

    Original text flows in the left column; translated text appears in
    the right column, styled in blue, separated by column breaks.

    Args:
        docx_doc: The DocxDocument containing both original and translated text.
        output_path: Path to write the bilingual .docx file.
    """
    tmpfd = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
    try:
        shutil.copy2(docx_doc.filepath, tmpfd.name)
        tmpfd.close()

        doc = DocxDocument_PythonDocx(tmpfd.name)

        _set_two_columns(doc)
        _inject_dual_paragraphs(doc, docx_doc)
        _replace_table_cells_keep_original(doc, docx_doc)
        _inject_dual_images(doc, docx_doc)

        doc.save(output_path)
        logger.info("Dual-language DOCX saved to: %s", output_path)
    finally:
        Path(tmpfd.name).unlink(missing_ok=True)


def _replace_images(doc: DocxDocument_PythonDocx, docx_doc: DocxDocument) -> None:
    """Replace image blobs with translated versions in the python-docx document.

    Matches images by filename against the document's image parts and
    updates the blob for any image with translated data.
    """
    if not docx_doc.images:
        return

    translated_map = {
        img.filename: img.translated_data
        for img in docx_doc.images
        if img.translated_data is not None
    }
    if not translated_map:
        return

    replaced = 0
    for rel in doc.part.rels.values():
        if rel.is_external:
            continue
        part = rel.target_part
        partname = part.partname
        filename = partname.rsplit("/", 1)[-1]
        if filename in translated_map:
            try:
                part._blob = translated_map[filename]
                replaced += 1
            except Exception:
                logger.warning(
                    "Failed to replace image blob for %s", filename, exc_info=True
                )

    if replaced:
        logger.info("Replaced %d translated images in DOCX", replaced)


def _inject_dual_images(doc: DocxDocument_PythonDocx, docx_doc: DocxDocument) -> None:
    """For dual mode: keep original images in left column, inject translated
    copies into the right column via column breaks.

    Original image paragraphs are left untouched.  A column‑break paragraph
    followed by a new paragraph containing the translated image is inserted
    immediately after each original image paragraph.
    """
    from io import BytesIO

    from docx.shared import Inches
    from PIL import Image as PILImage

    translated_map = {
        img.filename: img.translated_data
        for img in docx_doc.images
        if img.translated_data is not None
    }
    if not translated_map:
        return

    WPML = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    A = "http://schemas.openxmlformats.org/drawingml/2006/main"
    WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"

    doc_paras = list(doc.paragraphs)
    image_records = []

    for i, para in enumerate(doc_paras):
        for drawing in para._element.findall(f".//{{{WPML}}}drawing"):
            for blip in drawing.findall(f".//{{{A}}}blip"):
                r_id = blip.get(qn("r:embed"))
                if not r_id:
                    continue
                try:
                    part = doc.part.related_parts[r_id]
                    filename = part.partname.rsplit("/", 1)[-1]
                except (KeyError, AttributeError):
                    continue
                if filename not in translated_map:
                    continue

                pil_img = PILImage.open(BytesIO(translated_map[filename]))
                width_px, height_px = pil_img.size

                inline = drawing.find(f"{{{WP}}}inline")
                extent = None if inline is None else inline.find(f"{{{WP}}}extent")
                if extent is not None:
                    cx = int(extent.get("cx", "0"))
                    cy = int(extent.get("cy", "0"))
                else:
                    cx, cy = width_px * 9525, height_px * 9525

                image_records.append(
                    (i, translated_map[filename], cx, cy)
                )

    for para_idx, img_data, cx, cy in reversed(image_records):
        para_elem = doc_paras[para_idx]._element

        _insert_column_break_after(para_elem)
        col_break_elem = para_elem.getnext()

        width_inches = cx / 914400.0
        height_inches = cy / 914400.0

        new_para = doc.add_paragraph()
        new_run = new_para.add_run()
        new_run.add_picture(
            BytesIO(img_data),
            width=Inches(width_inches),
            height=Inches(height_inches),
        )

        new_elem = new_para._element
        new_elem.getparent().remove(new_elem)
        col_break_elem.addnext(new_elem)

        _insert_column_break_after(new_elem)

    if image_records:
        logger.info(
            "Injected %d translated images into dual DOCX right column",
            len(image_records),
        )
