# Learnings — PDF Image Text Translation

## Implementation Summary

### Files Created
- `babeldoc/format/pdf/document_il/midend/image_translator.py` (502 lines) — Core ImageTranslator class
- `babeldoc/format/pdf/document_il/utils/font_discovery.py` (55 lines) — CJK font discovery helper

### Files Modified
- `pyproject.toml` — Added Pillow>=10.0.0 dependency
- `babeldoc/format/pdf/translation_config.py` — Added `translate_image_text: bool = True` config flag
- `babeldoc/format/pdf/high_level.py` — Inserted ImageTranslator call after translation, before typesetting

### Design Decisions
1. **Midend approach**: ImageTranslator runs after text translation, before typesetting. Modifies IL in-place.
2. **No backend changes**: Converts PdfXobjForm (xref-based) → PdfInlineForm (inline data), existing backend handles inline images.
3. **XObject images extracted via PyMuPDF**: `mupdf_doc.extract_image(xref_id)` returns pixel data + metadata.
4. **RapidOCR for text detection**: Same library already used by FigureOCR for scanned pages.
5. **Pillow for image manipulation**: Draws background-colored rectangles over OCR regions, renders translated text.
6. **CJK font discovery**: Searches common system font paths for CJK fonts (Noto, WenQuanYi, AR PL UMing, etc.)
7. **Batch translation**: Joins multiple OCR texts with separator for efficient API usage, falls back to per-item.

### Key Technical Details
- RapidOCR returns `([x1, y1, x2, y2], text, confidence)` tuples in image pixel space
- Background color sampling uses median of 2px border around each OCR region
- Font size is fitted to OCR region using binary search (8 iterations)
- PdfForm.form_type == "image" identifies image forms (vs "form" for Form XObjects)
- Image parameters for inline PDF: W, H, CS (colorspace), BPC (8), Filter
- Not committing code — user hasn't requested commits yet

### Verification
- All files compile without errors
- ruff check passes clean
- ruff format applied
- uv sync succeeds with Pillow
- font_discovery.find_cjk_font() works: finds /usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc
