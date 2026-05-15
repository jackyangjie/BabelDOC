"""Figure OCR: extract text from image-only PDF pages using OCR.

Runs BEFORE ParagraphFinder. Creates PdfParagraph elements directly so
ParagraphFinder preserves them (via extend + reassign at lines 424-445).
"""

import logging
import uuid

import fitz
from rapidocr_onnxruntime import RapidOCR

from babeldoc.format.pdf.document_il import Box
from babeldoc.format.pdf.document_il import Document
from babeldoc.format.pdf.document_il import PdfCharacter
from babeldoc.format.pdf.document_il import PdfLine
from babeldoc.format.pdf.document_il import PdfParagraph
from babeldoc.format.pdf.document_il import PdfParagraphComposition
from babeldoc.format.pdf.document_il import PdfStyle
from babeldoc.format.pdf.document_il import VisualBbox
from babeldoc.format.pdf.translation_config import TranslationConfig
from babeldoc.format.pdf.document_il.utils.style_helper import BLACK

logger = logging.getLogger(__name__)


class FigureOCRExtractor:
    """OCR image-only pages and inject as PdfParagraph before ParagraphFinder."""

    stage_name = "FigureOCRExtractor"

    _OCR_FONT_SIZE = 8.0

    def __init__(self, translation_config: TranslationConfig):
        self.translation_config = translation_config
        self._ocr: RapidOCR | None = None

    def _get_ocr(self) -> RapidOCR:
        if self._ocr is None:
            self._ocr = RapidOCR()
        return self._ocr

    def process(self, document: Document, mupdf_doc: fitz.Document) -> None:
        """Run OCR on pages with no existing paragraphs/characters."""
        for page in document.page:
            if page.pdf_paragraph or page.pdf_character:
                continue
            self._ocr_page(page, mupdf_doc)

    def _ocr_page(self, page, mupdf_doc: fitz.Document) -> None:
        """Full-page OCR: render as image, OCR, create PdfParagraphs."""
        if not page.cropbox or not page.cropbox.box:
            return
        pix = mupdf_doc[page.page_number].get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")
        ocr_result = self._get_ocr()(img_bytes)
        if not ocr_result:
            return
        result_list, _elapse = ocr_result
        if not result_list:
            return

        crop = page.cropbox.box
        style = PdfStyle(
            font_id="base",
            font_size=self._OCR_FONT_SIZE,
            graphic_state=BLACK,
        )

        count = 0
        for line_box, text, confidence in result_list:
            if confidence < 0.5:
                continue
            text = text.strip()
            if not text or len(text) < 1:
                continue

            xs = [pt[0] for pt in line_box]
            ys = [pt[1] for pt in line_box]

            para_box = Box(
                x=crop.x + min(xs),
                y=crop.y + min(ys),
                x2=crop.x + max(xs),
                y2=crop.y + max(ys),
            )

            # Build individual PdfCharacter objects, one per character
            chars_per_line = 60
            char_w = (para_box.x2 - para_box.x) / min(len(text), chars_per_line)
            char_h = (para_box.y2 - para_box.y)
            pdf_chars = []
            for j, ch in enumerate(text):
                cx = para_box.x + j * char_w
                pdf_chars.append(
                    PdfCharacter(
                        box=Box(x=cx, y=para_box.y, x2=cx + char_w, y2=para_box.y2),
                        pdf_style=style,
                        char_unicode=ch,
                        xobj_id=0,
                        visual_bbox=VisualBbox(
                            box=Box(
                                x=cx,
                                y=para_box.y,
                                x2=cx + char_w,
                                y2=para_box.y2,
                            ),
                        ),
                    ),
                )

            paragraph = PdfParagraph(
                box=para_box,
                unicode=text,
                layout_label="text",
                first_line_indent=False,
                pdf_style=style,
                xobj_id=0,
                debug_id=str(uuid.uuid4()),
                pdf_paragraph_composition=[
                    PdfParagraphComposition(
                        pdf_line=PdfLine(
                            pdf_character=pdf_chars,
                        ),
                    ),
                ],
            )
            page.pdf_paragraph.append(paragraph)
            count += 1

        logger.info(
            "FigureOCR: page %s — injected %d paragraphs",
            page.page_number,
            count,
        )
