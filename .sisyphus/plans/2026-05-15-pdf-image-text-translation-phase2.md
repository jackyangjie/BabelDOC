# PDF Image Text Translation Phase 2 — Page Resource Images

**Goal:** Translate text in images that are stored as page-level XObject resources (e.g., `/Im0`, `/Im1` in source PDF page Resources), which the current `ImageTranslator` misses.

**Architecture:** In midend, scan source PDF page resources for image XObjects via PyMuPDF, OCR → translate → overlay, then store translated images in a side-channel dict. In backend, intercept image stream copies and replace with translated versions.

---

## Why Phase 1 Wasn't Enough

Phase 1 only handled `PdfForm` entries (`form_type == "image"`). NIST.CSWP.29.pdf has 3 images on page 1, but they're stored as:

- `/Im0` (xref=1484) — 1659x1555 JPEG — **NOT in the IL model at all**
- `/Im1` (xref=1485) — 1415x197 PNG — **NOT in the IL model at all**
- `/Fm0` (xref=1482) — Form XObject — only one in `page.pdf_xobject`

The images are page-level XObjects, unreferenced from the IL. They persist in output because backend opens source PDF as base.

---

## File Structure

### Modified files:
- `babeldoc/format/pdf/document_il/midend/image_translator.py` — Add page resource image scanning
- `babeldoc/format/pdf/translation_config.py` — Add side-channel for translated images
- `babeldoc/format/pdf/document_il/backend/pdf_creater.py` — Intercept image stream copies

### PIL/ImageConv — no new files, reuse existing Pillow + RapidOCR

---

## Technical Design

### Data flow
```
ImageTranslator.process()
  ├── Process page.pdf_form (existing Phase 1)
  └── NEW: Scan source PDF page resources via PyMuPDF
       ├── For each /Subtype /Image XObject:
       │   ├── Extract via mupdf_doc.extract_image(xref)
       │   ├── OCR → find text
       │   ├── Translate
       │   ├── Overlay translated text
       │   └── Store in translation_config._page_translated_images
       └── END

PDFCreater.write()
  ├── pdf = pymupdf.open(self.original_pdf_path)
  ├── For each page:
  │   ├── update_page_content_stream (existing)
  │   └── NEW: Replace image streams
  │       └── if page has translated images in config:
  │           └── pdf.update_stream(xref, new_image_bytes)
  └── pdf.save(...)
```

### Storage: `TranslationConfig._page_translated_images`
```python
# Dict: page_number (0-indexed) → {xref_id: image_bytes}
# Private field, set by ImageTranslator, read by PDFCreater
self._page_translated_images: dict[int, dict[int, bytes]] = {}
```

### Backend image replacement logic
```python
# In PDFCreater.write(), after update_page_content_stream for each page:
pn = page.page_number
if pn in translation_config._page_translated_images:
    for xref, new_data in translation_config._page_translated_images[pn].items():
        try:
            pdf.update_stream(xref, new_data)
        except Exception:
            logger.warning(f"Failed to update image xref {xref}")
```

---

### Task 1: Add side-channel for translated images to TranslationConfig

**Files:**
- Modify: `babeldoc/format/pdf/translation_config.py`

- [x] **Step 1: Add `_page_translated_images` dict**

```python
# In TranslationConfig.__init__(), after self.translate_image_text = ...
self._page_translated_images: dict[int, dict[int, bytes]] = {}
```

- [ ] **Step 2: Commit**

---

### Task 2: Extend ImageTranslator to scan page resources

**Files:**
- Modify: `babeldoc/format/pdf/document_il/midend/image_translator.py`

- [ ] **Step 1: Add `_process_page_resources()` method**

```python
def _process_page_resources(
    self,
    page: il_version_1.Page,
    mupdf_doc: fitz.Document,
    ocr: RapidOCR,
    translator: BaseTranslator,
) -> None:
    """Scan page-level XObject resources for images and translate them."""
    pn = page.page_number
    page_xref = mupdf_doc[pn].xref
    
    # Get page resources
    res_type, res_value = mupdf_doc.xref_get_key(page_xref, "Resources")
    if res_type != "dict":
        return
    
    # Parse Resources/XObject to find image references
    try:
        resources_dict = res_value
        xobj_match = re.search(r"/XObject\s*<<(.+?)>>", resources_dict)
        if not xobj_match:
            return
        xobj_section = xobj_match.group(1)
        # Find all XObject entries: /Name xref 0 R
        xobjs = re.findall(r"/(\w+)\s+(\d+)\s+0\s+R", xobj_section)
    except Exception:
        return
    
    page_translated: dict[int, bytes] = {}
    
    for name, xref_str in xobjs:
        xref = int(xref_str)
        try:
            # Check if this is an image
            obj_str = mupdf_doc.xref_object(xref)
            if "/Subtype /Image" not in obj_str:
                continue
            
            # Extract image
            pix = mupdf_doc.extract_image(xref)
            if pix is None:
                continue
            img_bytes = pix["image"]
            ext = pix["ext"]
            
            # OCR
            ocr_results = self._ocr_image(img_bytes, ocr)
            if not ocr_results:
                continue
            
            # Translate
            unique_texts = list({text for _, text, _ in ocr_results})
            if sum(len(t) for t in unique_texts) < _MIN_TEXT_LENGTH:
                continue
            
            translations = self._translate_texts(unique_texts, translator)
            if not translations:
                continue
            text_to_translation = dict(zip(unique_texts, translations, strict=False))
            
            # Overlay
            pil_image = PILImage.open(io.BytesIO(img_bytes))
            if pil_image.mode not in ("RGB", "RGBA"):
                pil_image = pil_image.convert("RGB")
            new_bytes = self._overlay_translations(
                pil_image, ocr_results, text_to_translation, ext,
            )
            page_translated[xref] = new_bytes
            
        except Exception:
            logger.debug("Failed to process image /%s (xref %s)", name, xref, exc_info=True)
            continue
    
    if page_translated:
        self.translation_config._page_translated_images[pn] = page_translated
```

- [ ] **Step 2: Call `_process_page_resources` from `process()`**

```python
def process(self, document, mupdf_doc, translator):
    # ... existing code ...
    for page in document.page:
        # Existing: process PdfForm entries
        for form in page.pdf_form:
            # ... existing code ...
        
        # NEW: process page-level XObject images
        self._process_page_resources(page, mupdf_doc, ocr, translator)
```

- [ ] **Step 3: Commit**

---

### Task 3: Add image stream replacement in PDFCreater

**Files:**
- Modify: `babeldoc/format/pdf/document_il/backend/pdf_creater.py`

- [ ] **Step 1: Image replacement in `write()` method**

After `update_page_content_stream` for each page (around line 1376-1378), add:

```python
for page in self.docs.page:
    self.update_page_content_stream(
        check_font_exists, page, pdf, translation_config
    )
    # NEW: Replace translated image streams
    pn = page.page_number
    if hasattr(translation_config, '_page_translated_images') and pn in translation_config._page_translated_images:
        for xref, new_data in translation_config._page_translated_images[pn].items():
            try:
                pdf.update_stream(xref, new_data)
            except Exception:
                logger.warning("Failed to update translated image xref %s", xref)
    pbar.advance()
```

- [ ] **Step 2: Commit**

---

### Task 4: Test and verify

- [ ] **Step 1: Compile check**

```bash
uv run python -m compileall babeldoc/format/pdf/document_il/midend/image_translator.py babeldoc/format/pdf/translation_config.py babeldoc/format/pdf/document_il/backend/pdf_creater.py
```

Expected: No errors.

- [ ] **Step 2: Lint check**

```bash
uv run ruff check babeldoc/format/pdf/document_il/midend/image_translator.py babeldoc/format/pdf/translation_config.py babeldoc/format/pdf/document_il/backend/pdf_creater.py
```

Expected: All checks passed.

- [ ] **Step 3: Format**

```bash
uv run ruff format babeldoc/format/pdf/document_il/midend/image_translator.py babeldoc/format/pdf/translation_config.py babeldoc/format/pdf/document_il/backend/pdf_creater.py
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: translate text in page-level XObject images"
```

---

## Self-Review

| Requirement | Task | Status |
|---|---|---|
| Scan page resources for images | Task 2 Step 1 `_process_page_resources` | ✅ |
| Extract, OCR, translate page images | Task 2 Step 1 | ✅ |
| Store translated images in side-channel | Task 1 | ✅ |
| Backend replaces image streams | Task 3 Step 1 | ✅ |
| Error handling for missing/deleted xrefs | Task 3 Step 1 (try/except) | ✅ |
| No regression for PdfForm path | Unchanged code | ✅ |
