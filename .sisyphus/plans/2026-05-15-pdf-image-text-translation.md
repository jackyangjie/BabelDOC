# PDF Image Text Translation Implementation Plan

**Goal:** Translate text that appears inside images embedded in PDF pages.

**Architecture:** New midend stage `ImageTranslator` that runs after text translation and before typesetting.

---

## Tasks

### Task 1: Add Pillow dependency
**Files:** `pyproject.toml`
- [x] Step 1: Add Pillow to project dependencies
- [x] Step 2: Sync dependencies
- [x] Step 3: Commit

### Task 2: CJK font discovery helper
**Files:** `babeldoc/format/pdf/document_il/utils/font_discovery.py`
- [x] Step 1: Write `font_discovery.py`
- [x] Step 2: Commit

### Task 3: ImageTranslator midend stage
**Files:** `babeldoc/format/pdf/document_il/midend/image_translator.py`
- [x] Step 1: Write the `ImageTranslator` class
- [x] Step 2: Commit

### Task 4: Config toggle + pipeline integration
**Files:** `babeldoc/format/pdf/translation_config.py`, `babeldoc/format/pdf/high_level.py`
- [x] Step 1: Add `translate_image_text` flag to TranslationConfig
- [x] Step 2: Integrate into high_level.py pipeline
- [x] Step 3: Commit

### Task 5: Lint and type-check
- [x] Step 1: Run ruff check
- [x] Step 2: Run ruff format
- [x] Step 3: Run compileall
- [x] Step 4: Commit

---

## Verification

### Commit: `feat: add ImageTranslator pipeline for text in PDF images`

```
 M babeldoc/format/pdf/high_level.py
 M babeldoc/format/pdf/translation_config.py
 M pyproject.toml
?? babeldoc/format/pdf/document_il/midend/image_translator.py
?? babeldoc/format/pdf/document_il/utils/font_discovery.py
```

5 files changed, 603 insertions(+)

### Checks
- ✅ `compileall` — all pass
- ✅ `ruff check` — zero errors
- ✅ `ruff format` — clean
- ✅ font_discovery: finds `/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc`
- ✅ Pillow importable after `uv sync`
