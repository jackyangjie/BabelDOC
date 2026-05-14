"""PPTX backend: write translated text back into a .pptx file.

Strategy: open the original presentation, walk slides, shapes, and tables
in parallel with the PptxDocument, and replace text content while preserving
the original document structure and formatting.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from copy import deepcopy
from pathlib import Path

from pptx import Presentation as PptxPresentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Inches, Pt

from babeldoc.format.pptx.il import PptxDocument

logger = logging.getLogger(__name__)

# Colour constant for dual-language translation text (matching DOCX dual style)
_DUAL_TRANSLATION_COLOR_HEX = "2E75B6"

# Magic bytes for old binary OLE2 format
_OLE2_MAGIC = b"\xd0\xcf\x11\xe0"


def _is_old_ppt_format(filepath: str) -> bool:
    """Check if a file is an old binary OLE2 .ppt format."""
    with open(filepath, "rb") as f:
        header = f.read(8)
    return header[:4] == _OLE2_MAGIC


def _create_presentation_from_text(
    pptx_doc: PptxDocument,
) -> PptxPresentation:
    """Create a new .pptx presentation from scratch for legacy .ppt files.

    Since old binary .ppt cannot be opened by python-pptx, we create
    a fresh presentation and populate it with the translated text.
    Outputs a single slide with all paragraphs in reading order.
    """
    prs = PptxPresentation()
    blank_layout = prs.slide_layouts[6]

    # Collect all translated text
    all_texts: list[str] = []
    for slide in pptx_doc.slides:
        for shape in slide.shapes:
            text = shape.translated_text or shape.text
            if text.strip():
                all_texts.append(text.strip())

    if not all_texts:
        return prs

    # Single slide with all text in reading order
    slide = prs.slides.add_slide(blank_layout)
    y_pos = Inches(0.3)
    for item in all_texts:
        # Estimate needed height based on text length
        est_lines = max(1, len(item) // 80 + 1)
        height = Inches(0.3 * est_lines + 0.1)
        # If not enough room, create new slide
        if y_pos + height > Inches(7.2):
            slide = prs.slides.add_slide(blank_layout)
            y_pos = Inches(0.3)
        tx_box = slide.shapes.add_textbox(
            Inches(0.5), y_pos, Inches(8.5), height,
        )
        tf = tx_box.text_frame
        tf.text = item
        tf.paragraphs[0].font.size = Pt(14)
        # Enable word wrap
        tf.word_wrap = True
        y_pos += height + Inches(0.1)

    return prs

    return prs


def _create_dual_presentation_from_text(
    pptx_doc: PptxDocument,
) -> PptxPresentation:
    """Create a dual-language .pptx from scratch for legacy .ppt files.

    Outputs alternating original/translated slides for all paragraphs.
    """
    prs = PptxPresentation()
    blank_layout = prs.slide_layouts[6]

    # Collect all original + translated pairs
    pairs: list[tuple[str, str]] = []
    for slide in pptx_doc.slides:
        for shape in slide.shapes:
            original = shape.text.strip()
            translated = shape.translated_text.strip() if shape.translated_text else ""
            if original:
                pairs.append((original, translated or original))

    # Create alternating original/translated slides
    for original, translated in pairs:
        slide = prs.slides.add_slide(blank_layout)
        est_lines = max(1, len(original) // 80 + 1)
        height = Inches(0.3 * est_lines + 0.1)
        tx_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(0.5), Inches(8.5), height,
        )
        tf = tx_box.text_frame
        tf.text = original
        tf.paragraphs[0].font.size = Pt(14)

        # Translated slide
        slide_t = prs.slides.add_slide(blank_layout)
        tx_box_t = slide_t.shapes.add_textbox(
            Inches(0.5), Inches(0.5), Inches(8.5), height,
        )
        tf_t = tx_box_t.text_frame
        tf_t.text = translated
        tf_t.paragraphs[0].font.size = Pt(14)
        if tf_t.paragraphs[0].runs:
            _set_run_color_blue(tf_t.paragraphs[0].runs[0])

    return prs


def _open_presentation(pptx_doc: PptxDocument) -> PptxPresentation:
    """Open a presentation from a PPTX document, handling legacy .ppt format."""
    if _is_old_ppt_format(pptx_doc.filepath):
        return _create_presentation_from_text(pptx_doc)

    tmpfd = tempfile.NamedTemporaryFile(suffix=".pptx", delete=False)
    try:
        shutil.copy2(pptx_doc.filepath, tmpfd.name)
        tmpfd.close()
        prs = PptxPresentation(tmpfd.name)
    except Exception:
        Path(tmpfd.name).unlink(missing_ok=True)
        raise
    return prs


def write_pptx(
    pptx_doc: PptxDocument,
    output_path: str,
) -> None:
    """Write translated text into a new .pptx file.

    Opens the original presentation, replaces shape and table cell text
    with translated content, and saves to *output_path*.
    Handles both modern .pptx and legacy binary .ppt files.

    Args:
        pptx_doc: The PptxDocument containing translated text.
        output_path: Path to write the translated .pptx file.
    """
    # Use converted .pptx if available (LibreOffice path)
    source_path = pptx_doc._pptx_source_path or pptx_doc.filepath

    if _is_old_ppt_format(source_path):
        # Legacy binary .ppt without conversion — create from scratch
        prs = _create_presentation_from_text(pptx_doc)
        prs.save(output_path)
        logger.info(
            "Translated PPTX (from legacy .ppt) saved to: %s",
            output_path,
        )
        return

    tmpfd = tempfile.NamedTemporaryFile(suffix=".pptx", delete=False)
    try:
        shutil.copy2(source_path, tmpfd.name)
        tmpfd.close()

        prs = PptxPresentation(tmpfd.name)

        _replace_slide_text(prs, pptx_doc)

        prs.save(output_path)
        logger.info("Translated PPTX saved to: %s", output_path)
    finally:
        Path(tmpfd.name).unlink(missing_ok=True)


def _replace_slide_text(
    prs: PptxPresentation,
    pptx_doc: PptxDocument,
) -> None:
    """Walk slides, shapes, and tables to inject translated text."""
    for slide_idx, slide_info in enumerate(pptx_doc.slides):
        if slide_idx >= len(prs.slides):
            logger.warning(
                "Slide index %d exceeds presentation slides (%d), skipping",
                slide_idx,
                len(prs.slides),
            )
            break

        slide = prs.slides[slide_idx]
        shape_index = 0
        table_index = 0

        def _walk_shapes(shapes):
            nonlocal shape_index, table_index
            for shape in shapes:
                if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                    _walk_shapes(shape.shapes)
                elif shape.has_table:
                    if table_index < len(slide_info.tables):
                        _replace_table_cells(
                            shape.table,
                            slide_info.tables[table_index],
                        )
                        table_index += 1
                elif _is_relevant_shape(shape):
                    if shape_index < len(slide_info.shapes):
                        if shape.has_text_frame:
                            shape_info = slide_info.shapes[shape_index]
                            translated = shape_info.translated_text
                            if translated and translated.strip():
                                _replace_textframe_text(
                                    shape.text_frame,
                                    translated,
                                )
                        shape_index += 1

        _walk_shapes(slide.shapes)


def _is_relevant_shape(shape) -> bool:
    """Check if a shape is a text-containing shape we track."""
    if not shape.has_text_frame:
        return False
    # Skip empty shapes and group shapes (handled differently)
    text = shape.text_frame.text
    return bool(text and text.strip())


def _replace_textframe_text(tf, new_text: str) -> None:
    """Replace all text in a text frame while preserving formatting.

    Clears existing text runs and adds a single new run with the
    translated text, copying the formatting from the first original run.
    """
    original_paragraphs = list(tf.paragraphs)

    # Capture formatting from the first non-empty run
    fmt = _capture_paragraph_format(original_paragraphs)

    # Clear text from all paragraphs
    for para in original_paragraphs:
        for run in para.runs:
            run.text = ""

    # Set translated text in the first paragraph
    if tf.paragraphs:
        first_para = tf.paragraphs[0]
        first_para.text = ""
        run = first_para.add_run()
        run.text = new_text
        _apply_run_format(run, fmt)


def _capture_paragraph_format(paragraphs) -> dict:
    """Capture font formatting from the first non-empty paragraph."""
    fmt: dict = {}
    for para in paragraphs:
        for run in para.runs:
            if run.text.strip():
                font = run.font
                for attr in ("bold", "italic", "underline", "size", "name"):
                    try:
                        val = getattr(font, attr, None)
                        if val is not None:
                            fmt[attr] = val
                    except Exception:
                        pass
                try:
                    if font.color and font.color.rgb:
                        fmt["color_rgb"] = str(font.color.rgb)
                except Exception:
                    pass
                if fmt:
                    return fmt
    return fmt


def _apply_run_format(run, fmt: dict) -> None:
    """Apply captured formatting dict to a run."""
    for key, val in fmt.items():
        if val is None:
            continue
        try:
            if key == "bold":
                run.font.bold = val
            elif key == "italic":
                run.font.italic = val
            elif key == "underline":
                run.font.underline = val
            elif key == "size":
                run.font.size = val
            elif key == "name":
                run.font.name = val
        except Exception:
            pass


def _replace_table_cells(table, table_info) -> None:
    """Walk table rows and inject translated cell text."""
    for r_idx, row_info in enumerate(table_info.rows):
        if r_idx >= len(table.rows):
            break
        row = table.rows[r_idx]
        for c_idx, cell_info in enumerate(row_info.cells):
            if c_idx >= len(row.cells):
                break
            translated = cell_info.translated_text
            if translated and translated.strip():
                cell = row.cells[c_idx]
                # Clear existing text
                for para in cell.text_frame.paragraphs:
                    for run in para.runs:
                        run.text = ""
                # Set translated text
                if cell.text_frame.paragraphs:
                    cell.text_frame.paragraphs[0].text = translated


# ---------------------------------------------------------------------------
# Dual-language (bilingual) support
# ---------------------------------------------------------------------------


def write_dual_pptx(
    pptx_doc: PptxDocument,
    output_path: str,
) -> None:
    """Write a dual-language .pptx with original and translated text.

    Strategy: duplicate every slide so that each original is immediately
    followed by its translated version.  The original slide is left unchanged;
    the duplicated slide has all text replaced by the blue translation.

    Handles both modern .pptx and legacy binary .ppt files.

    Args:
        pptx_doc: The PptxDocument containing both original and translated text.
        output_path: Path to write the bilingual .pptx file.
    """
    source_path = pptx_doc._pptx_source_path or pptx_doc.filepath

    if _is_old_ppt_format(source_path):
        prs = _create_dual_presentation_from_text(pptx_doc)
        prs.save(output_path)
        logger.info(
            "Dual-language PPTX (from legacy .ppt) saved to: %s",
            output_path,
        )
        return

    tmpfd = tempfile.NamedTemporaryFile(suffix=".pptx", delete=False)
    try:
        shutil.copy2(source_path, tmpfd.name)
        tmpfd.close()

        prs = PptxPresentation(tmpfd.name)

        _duplicate_slides_and_apply_translation(prs, pptx_doc)

        prs.save(output_path)
        logger.info("Dual-language PPTX saved to: %s", output_path)
    finally:
        Path(tmpfd.name).unlink(missing_ok=True)


def _duplicate_slides_and_apply_translation(
    prs: PptxPresentation,
    pptx_doc: PptxDocument,
) -> None:
    """Duplicate each slide and replace text on the duplicate with blue translation."""
    from copy import deepcopy

    # Iterate from last to first so insertions do not shift indices
    total_slides = len(prs.slides)
    for slide_idx in range(total_slides - 1, -1, -1):
        source_slide = prs.slides[slide_idx]
        slide_info = pptx_doc.slides[slide_idx]

        # Duplicate slide using source layout
        new_slide = prs.slides.add_slide(source_slide.slide_layout)

        # Remove default shapes from new slide
        for shape in list(new_slide.shapes):
            sp = shape._element
            sp.getparent().remove(sp)

        # Copy all shapes from source (including pictures)
        for shape in source_slide.shapes:
            new_el = deepcopy(shape._element)
            new_slide.shapes._spTree.insert_element_before(new_el, "p:extLst")

        # Fix image relationships for copied picture shapes
        _fix_copied_image_relations(source_slide, new_slide)

        # Move duplicated slide right after the original
        _move_slide_to_position(prs, slide_idx, len(prs.slides) - 1)

        # Apply blue translation to the duplicated slide
        _apply_blue_translation(new_slide, slide_info)


def _move_slide_to_position(
    prs: PptxPresentation,
    target_idx: int,
    source_idx: int,
) -> None:
    """Move slide at *source_idx* to position *target_idx* + 1."""
    slide_id_list = prs.slides._sldIdLst
    sldId = slide_id_list[source_idx]
    slide_id_list.remove(sldId)
    slide_id_list.insert(target_idx + 1, sldId)


def _fix_copied_image_relations(source_slide, new_slide) -> None:
    """Fix image relationship references in a shape-copied slide.

    When picture shapes are deep-copied, their ``<a:blip r:embed="rIdX">``
    references point to rIds that don't exist in the new slide's rels.
    This function finds all such broken references and copies the actual
    image data into the new slide, updating the rId references.
    """
    import tempfile
    from pptx.opc.constants import RELATIONSHIP_TYPE as RT

    ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    a_ns = "http://schemas.openxmlformats.org/drawingml/2006/main"

    # Collect all blip elements in the new slide
    for blip in new_slide.shapes._spTree.findall(
        ".//{%s}blip" % a_ns,
    ):
        embed_attr = "{%s}embed" % ns
        rId = blip.get(embed_attr)
        if rId is None:
            continue

        # Check if rId exists in new slide's relationships
        if rId in new_slide.part.rels:
            continue

        # rId is broken — copy image from source slide
        source_rels = source_slide.part.rels
        if rId not in source_rels:
            continue

        source_rel = source_rels[rId]
        if source_rel.reltype != RT.IMAGE:
            continue

        try:
            image_blob = source_rel.target_part.blob
            # Write to temp file for python-pptx
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            tmp.write(image_blob)
            tmp.close()

            # Add image to new slide (this correctly creates relationship)
            new_part, new_rId = new_slide.part.get_or_add_image_part(
                tmp.name
            )
            blip.set(embed_attr, new_rId)
            Path(tmp.name).unlink(missing_ok=True)
        except Exception as e:
            logger.warning("Failed to copy image (rId=%s): %s", rId, e)


def _apply_blue_translation(
    slide,
    slide_info,
) -> None:
    """Replace all text on *slide* with blue translated text."""
    shape_index = 0
    table_index = 0

    def _walk_shapes(shapes):
        nonlocal shape_index, table_index
        for shape in shapes:
            if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                _walk_shapes(shape.shapes)
            elif shape.has_table:
                if table_index < len(slide_info.tables):
                    _replace_table_cells_blue(
                        shape.table,
                        slide_info.tables[table_index],
                    )
                    table_index += 1
            elif _is_relevant_shape(shape):
                if shape_index < len(slide_info.shapes):
                    if shape.has_text_frame:
                        shape_info = slide_info.shapes[shape_index]
                        translated = shape_info.translated_text
                        if translated and translated.strip():
                            _replace_textframe_text_blue(
                                shape.text_frame,
                                translated,
                            )
                    shape_index += 1

    _walk_shapes(slide.shapes)


def _replace_textframe_text_blue(
    tf,
    new_text: str,
) -> None:
    """Replace all text in a text frame with blue translated text."""
    original_paragraphs = list(tf.paragraphs)

    # Capture formatting from the first non-empty run
    fmt = _capture_paragraph_format(original_paragraphs)

    # Clear text from all paragraphs
    for para in original_paragraphs:
        for run in para.runs:
            run.text = ""

    # Set translated text in the first paragraph
    if tf.paragraphs:
        first_para = tf.paragraphs[0]
        first_para.text = ""
        run = first_para.add_run()
        run.text = new_text
        _apply_run_format(run, fmt)

        # Apply blue colour
        _set_run_color_blue(run)


def _replace_table_cells_blue(
    table,
    table_info,
) -> None:
    """Walk table rows and replace cell text with blue translation."""
    for r_idx, row_info in enumerate(table_info.rows):
        if r_idx >= len(table.rows):
            break
        row = table.rows[r_idx]
        for c_idx, cell_info in enumerate(row_info.cells):
            if c_idx >= len(row.cells):
                break
            translated = cell_info.translated_text
            if translated and translated.strip():
                cell = row.cells[c_idx]
                # Clear existing text
                for para in cell.text_frame.paragraphs:
                    for run in para.runs:
                        run.text = ""
                # Set blue translated text
                if cell.text_frame.paragraphs:
                    para = cell.text_frame.paragraphs[0]
                    para.text = ""
                    run = para.add_run()
                    run.text = translated
                    _set_run_color_blue(run)


def _set_run_color_blue(run) -> None:
    """Set run text colour to the dual translation blue."""
    try:
        from pptx.oxml.ns import qn as pptx_qn

        rpr = run._r.get_or_add_rPr()
        color_elem = rpr.find(pptx_qn("a:solidFill"))
        if color_elem is None:
            color_elem = rpr.makeelement(pptx_qn("a:solidFill"), {})
            rpr.insert(0, color_elem)
        srgb = color_elem.find(pptx_qn("a:srgbClr"))
        if srgb is None:
            srgb = color_elem.makeelement(pptx_qn("a:srgbClr"), {})
            color_elem.insert(0, srgb)
        srgb.set("val", _DUAL_TRANSLATION_COLOR_HEX)
    except Exception:
        # Fallback to font colour if XML manipulation fails
        try:
            run.font.color.rgb = _DUAL_TRANSLATION_COLOR_HEX
        except Exception:
            pass
