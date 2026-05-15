"""ImageTranslator: OCR text in PDF images, translate, and overlay translation.

Runs AFTER translation and BEFORE typesetting. For each image form:
  1. Extract pixel data from source PDF (xref) or inline form
  2. OCR to detect text regions
  3. Translate detected text via the existing translation engine
  4. Overlay translated text onto the image (hide original text, render translation)
  5. Convert PdfXobjForm to PdfInlineForm with the modified image

The backend writes modified inline images directly and needs zero changes.
"""

from __future__ import annotations

import base64
import io
import json
import logging

import fitz
from PIL import Image as PILImage
from rapidocr_onnxruntime import RapidOCR

from babeldoc.format.pdf.document_il import il_version_1
from babeldoc.format.pdf.document_il.utils.font_discovery import find_cjk_font
from babeldoc.translator.translator import BaseTranslator

if True:
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from babeldoc.format.pdf.document_il import Document
        from babeldoc.format.pdf.translation_config import TranslationConfig

logger = logging.getLogger(__name__)

# Minimum confidence threshold for OCR results.
_OCR_CONFIDENCE_THRESHOLD = 0.5
# Images with fewer than this many total characters are skipped.
_MIN_TEXT_LENGTH = 3


class ImageTranslator:
    """Translate text found inside images embedded in PDF pages."""

    stage_name = "ImageTranslator"

    def __init__(self, translation_config: TranslationConfig):
        self.translation_config = translation_config
        self._ocr: RapidOCR | None = None
        self._cjk_font_path: str | None = None

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def process(
        self,
        document: Document,
        mupdf_doc: fitz.Document,
        translator: BaseTranslator | None,
    ) -> None:
        """Process all image forms in the document.

        Args:
            document: The IL document to process.
            mupdf_doc: PyMuPDF document handle for image extraction.
            translator: The translation engine to use.
        """
        if not self.translation_config.translate_image_text:
            logger.debug("ImageTranslator disabled by config")
            return

        if translator is None:
            logger.debug("ImageTranslator: no translator available, skipping")
            return

        self._cjk_font_path = find_cjk_font()
        if self._cjk_font_path is None:
            logger.warning(
                "No CJK font found. Translated text may render as boxes.",
            )

        ocr = self._get_ocr()

        for page in document.page:
            for form in page.pdf_form:
                if form.form_type != "image":
                    continue
                try:
                    self._process_form(form, mupdf_doc, ocr, translator)
                except Exception:
                    logger.exception(
                        "ImageTranslator: failed on page %s form %s",
                        page.page_number,
                        form.xobj_id,
                    )

    # ------------------------------------------------------------------
    # Per-form processing
    # ------------------------------------------------------------------

    def _process_form(
        self,
        form: il_version_1.PdfForm,
        mupdf_doc: fitz.Document,
        ocr: RapidOCR,
        translator: BaseTranslator,
    ) -> None:
        """Extract, OCR, translate, overlay, and replace a single image form."""
        # 1. Extract image bytes
        image_bytes, ext = self._extract_image(form, mupdf_doc)
        if image_bytes is None:
            return

        # 2. OCR
        ocr_results = self._ocr_image(image_bytes, ocr)
        if not ocr_results:
            return

        # 3. Collect unique text for translation
        unique_texts = list({text for _, text, _ in ocr_results})
        if sum(len(t) for t in unique_texts) < _MIN_TEXT_LENGTH:
            return

        translations = self._translate_texts(unique_texts, translator)
        if not translations:
            return

        # Build translation mapping
        text_to_translation = dict(zip(unique_texts, translations, strict=False))

        # 4. Overlay translations
        pil_image = PILImage.open(io.BytesIO(image_bytes))
        if pil_image.mode not in ("RGB", "RGBA"):
            pil_image = pil_image.convert("RGB")

        new_image_bytes = self._overlay_translations(
            pil_image,
            ocr_results,
            text_to_translation,
            ext,
        )

        # 5. Replace form subtype
        self._replace_form_subtype(form, new_image_bytes, ext)

    # ------------------------------------------------------------------
    # Image extraction
    # ------------------------------------------------------------------

    def _extract_image(
        self,
        form: il_version_1.PdfForm,
        mupdf_doc: fitz.Document,
    ) -> tuple[bytes | None, str]:
        """Extract raw image bytes from a PdfForm.

        Returns:
            Tuple of (image_bytes, extension) or (None, "") on failure.
        """
        subtype = form.pdf_form_subtype
        if subtype is None:
            return None, ""

        # Case 1: XObject form -- extract via xref from source PDF
        if subtype.pdf_xobj_form:
            xref_id = subtype.pdf_xobj_form.xref_id
            if xref_id is None:
                return None, ""
            try:
                pix = mupdf_doc.extract_image(xref_id)
                if pix is None:
                    return None, ""
                return pix["image"], pix["ext"]
            except Exception:
                logger.debug(
                    "Failed to extract image xref %s",
                    xref_id,
                    exc_info=True,
                )
                return None, ""

        # Case 2: Inline form -- decode from base64
        if subtype.pdf_inline_form and subtype.pdf_inline_form.form_data:
            try:
                data = base64.b64decode(subtype.pdf_inline_form.form_data)
                return data, "png"
            except Exception:
                logger.debug(
                    "Failed to decode inline image data",
                    exc_info=True,
                )
                return None, ""

        return None, ""

    # ------------------------------------------------------------------
    # OCR
    # ------------------------------------------------------------------

    def _get_ocr(self) -> RapidOCR:
        if self._ocr is None:
            self._ocr = RapidOCR()
        return self._ocr

    def _ocr_image(
        self,
        image_bytes: bytes,
        ocr: RapidOCR,
    ) -> list[tuple[list[float], str, float]]:
        """Run OCR on image bytes, return filtered results.

        Returns:
            List of ([x1, y1, x2, y2], text, confidence) with high-confidence text.
        """
        try:
            result = ocr(image_bytes)
        except Exception:
            logger.debug("OCR failed on image", exc_info=True)
            return []

        if not result:
            return []
        result_list, _elapse = result
        if not result_list:
            return []

        filtered = []
        for box, text, confidence in result_list:
            if confidence < _OCR_CONFIDENCE_THRESHOLD:
                continue
            text = text.strip()
            if not text:
                continue
            filtered.append((list(box), text, float(confidence)))
        return filtered

    # ------------------------------------------------------------------
    # Translation
    # ------------------------------------------------------------------

    def _translate_texts(
        self,
        texts: list[str],
        translator: BaseTranslator,
    ) -> list[str]:
        """Translate a list of strings using the existing translation engine.

        Joins texts with newline separator for batch calls.
        """
        if not texts:
            return []

        # Single text -- translate directly
        if len(texts) == 1:
            try:
                translated = translator.translate(texts[0])
                return [translated]
            except Exception:
                logger.debug("Translation failed", exc_info=True)
                return texts

        # Multiple texts -- join with separator
        separator = "\n----\n"
        joined = separator.join(texts)
        try:
            translated_joined = translator.translate(joined)
            translated_list = translated_joined.split(separator)
            if len(translated_list) != len(texts):
                return self._translate_texts_one_by_one(texts, translator)
            return [t.strip() for t in translated_list]
        except Exception:
            logger.debug(
                "Batch translation failed, falling back to per-item",
                exc_info=True,
            )
            return self._translate_texts_one_by_one(texts, translator)

    def _translate_texts_one_by_one(
        self,
        texts: list[str],
        translator: BaseTranslator,
    ) -> list[str]:
        """Fallback: translate each text individually."""
        results = []
        for text in texts:
            try:
                results.append(translator.translate(text))
            except Exception:
                results.append(text)  # keep original on failure
        return results

    # ------------------------------------------------------------------
    # Image overlay
    # ------------------------------------------------------------------

    def _overlay_translations(
        self,
        image: PILImage.Image,
        ocr_results: list[tuple[list[float], str, float]],
        text_to_translation: dict[str, str],
        _ext: str,
    ) -> bytes:
        """Render translated text onto the image, hiding original text.

        Strategy:
          1. For each OCR region, draw a filled rectangle with background
             color sampled from region edges.
          2. Draw the translated text centered in the region, with font
             size scaled to fit.

        Returns:
            PNG-encoded image bytes.
        """
        from PIL import ImageDraw
        from PIL import ImageFont

        draw = ImageDraw.Draw(image)

        for box, original_text, _confidence in ocr_results:
            x1, y1, x2, y2 = box
            translated = text_to_translation.get(original_text, original_text)

            # Clamp to image boundaries
            x1_i = max(0, int(x1))
            y1_i = max(0, int(y1))
            x2_i = min(image.width, int(x2))
            y2_i = min(image.height, int(y2))
            if x2_i <= x1_i or y2_i <= y1_i:
                continue

            region_w = x2_i - x1_i
            region_h = y2_i - y1_i

            # Sample background color from region edges
            bg_color = self._sample_background_color(
                image,
                x1_i,
                y1_i,
                x2_i,
                y2_i,
            )

            # Draw filled rectangle to hide original text
            draw.rectangle([x1_i, y1_i, x2_i, y2_i], fill=bg_color)

            # Calculate font size to fit translated text
            font_size = self._fit_font_size(translated, region_w, region_h)
            if font_size < 4:
                continue

            try:
                if self._cjk_font_path:
                    used_font = ImageFont.truetype(
                        self._cjk_font_path,
                        size=max(int(font_size), 4),
                    )
                else:
                    used_font = ImageFont.load_default()
            except (OSError, TypeError):
                used_font = ImageFont.load_default()

            # Get text bounding box for centering
            bbox = draw.textbbox((0, 0), translated, font=used_font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            # Center text in the region
            tx = x1_i + (region_w - text_w) // 2
            ty = y1_i + (region_h - text_h) // 2

            # Draw translated text in dark color
            draw.text((tx, ty), translated, fill=(0, 0, 0), font=used_font)

        # Encode back to bytes
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return buf.getvalue()

    def _sample_background_color(
        self,
        image: PILImage.Image,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
    ) -> tuple[int, int, int]:
        """Sample background color from 2px border around text region."""
        import numpy as np

        arr = np.array(image)
        if arr.ndim < 3:
            return (255, 255, 255)

        h, w = arr.shape[:2]
        border_mask = np.zeros((h, w), dtype=bool)

        # Top border
        top_start = max(0, y1 - 2)
        top_end = y1
        if top_end > top_start:
            border_mask[top_start:top_end, x1:x2] = True
        # Bottom border
        bot_start = y2
        bot_end = min(h, y2 + 2)
        if bot_end > bot_start:
            border_mask[bot_start:bot_end, x1:x2] = True
        # Left border
        left_start = max(0, x1 - 2)
        left_end = x1
        if left_end > left_start:
            border_mask[y1:y2, left_start:left_end] = True
        # Right border
        right_start = x2
        right_end = min(w, x2 + 2)
        if right_end > right_start:
            border_mask[y1:y2, right_start:right_end] = True

        if not border_mask.any():
            return (255, 255, 255)

        border_pixels = arr[border_mask]
        if border_pixels.shape[0] == 0:
            return (255, 255, 255)

        # Use median of each channel for robustness
        median = np.median(border_pixels, axis=0).astype(int)
        return (int(median[0]), int(median[1]), int(median[2]))

    def _fit_font_size(
        self,
        text: str,
        max_width: int,
        max_height: int,
    ) -> float:
        """Binary search for the largest font size that fits the region."""
        from PIL import ImageDraw
        from PIL import ImageFont

        lo, hi = 4.0, float(max_height)
        best = lo

        for _ in range(8):
            mid = (lo + hi) / 2
            try:
                if self._cjk_font_path:
                    f = ImageFont.truetype(self._cjk_font_path, size=mid)
                else:
                    f = ImageFont.load_default()
                # Dummy image for text measurement
                dummy_img = PILImage.new("RGB", (1, 1))
                dummy = ImageDraw.Draw(dummy_img)
                bbox = dummy.textbbox((0, 0), text, font=f)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                if tw <= max_width and th <= max_height:
                    best = mid
                    lo = mid + 0.5
                else:
                    hi = mid - 0.5
            except Exception:
                hi = mid - 0.5
        return best

    # ------------------------------------------------------------------
    # IL replacement
    # ------------------------------------------------------------------

    def _replace_form_subtype(
        self,
        form: il_version_1.PdfForm,
        new_image_bytes: bytes,
        ext: str,
    ) -> None:
        """Replace the form's subtype from XObjForm to InlineForm.

        The modified image is base64-encoded and stored as an inline image,
        so the backend writes it directly into the PDF stream.
        """
        new_data = base64.b64encode(new_image_bytes).decode("ascii")

        # Determine image parameters from the new image
        pil_img = PILImage.open(io.BytesIO(new_image_bytes))
        w, h = pil_img.size

        mode_to_cs = {
            "L": "/G",
            "RGB": "/RGB",
            "RGBA": "/RGB",
            "CMYK": "/CMYK",
        }
        cs = mode_to_cs.get(pil_img.mode, "/RGB")

        ext_to_filter = {
            "png": "/FlateDecode",
            "jpg": "/DCTDecode",
            "jpeg": "/DCTDecode",
        }
        pdf_filter = ext_to_filter.get(ext.lower(), "/FlateDecode")

        params = {
            "W": w,
            "H": h,
            "CS": cs,
            "BPC": 8,
            "Filter": pdf_filter,
        }

        inline_form = il_version_1.PdfInlineForm(
            form_data=new_data,
            image_parameters=json.dumps(params),
        )
        form.pdf_form_subtype = il_version_1.PdfFormSubtype(
            pdf_inline_form=inline_form,
            pdf_xobj_form=None,
        )
