# DOCX 对照翻译（双语）支持实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: subagent-driven-development or executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** 为 BabelDOC 的 DOCX 翻译管线添加双语对照输出功能，使用 Word 双栏布局 + 分栏符实现原文（左栏）和译文（右栏）左右对照。
   示例:
     Page 1:
        ┌───────────────────────┬───────────────────────┐
        │ 左栏: 原文              │ 右栏: 译文（蓝色）         │
        │                       │                       │
        │ How to compile a .tex │ 如何将 .tex 文件编译  │
        │ file to a .pdf file   │ 为 .pdf 文件          │
        │  ← 分栏符              │                       │
        │ Tools                 │ 工具                  │
        │  ← 分栏符              │                       │
        │ Follow these steps:   │ 请按以下步骤操作：    │
        │  ← 分栏符              │                       │
        └───────────────────────┴───────────────────────┘

**Architecture:** 复用现有 DOCX 管线（frontend → translate → backend），IL 模型已有 `text`（原文）和 `translated_text`（译文）。在 backend 层新增 `write_dual_docx()`，通过 python-docx XML 操作设置文档为双栏布局，为每段译文插入分栏符 `<w:br w:type="column"/>`，实现原文左栏、译文右栏的并排效果。输出行为镜像 PDF 管线：默认同时输出 mono（翻译版）和 dual（双语对照版）。

**Tech Stack:** python-docx, OOXML, lxml

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `babeldoc/format/docx/il.py` | 不改 | 已有 `DocxParagraph.text` + `DocxParagraph.translated_text`，满足需求 |
| `babeldoc/format/docx/backend.py` | **新增函数** | `write_dual_docx()`: 双栏分栏符布局；辅助函数：`_set_two_columns()`, `_insert_column_break_paragraph()`, `_make_dual_paragraph()` |
| `babeldoc/format/docx/docx_translate.py` | **修改** | `translate_docx()` 接收 `no_dual`/`no_mono`，按需调用 `write_docx()` 和/或 `write_dual_docx()` |
| `babeldoc/main.py` | **修改** | docx 分支传递 `no_dual`/`no_mono` 参数；新增强制覆盖选项 |

---

### Task 1: 新增 `write_dual_docx()` 函数到 `backend.py`

**Files:**
- Modify: `babeldoc/format/docx/backend.py`

**核心逻辑：**
1. 复制原始 docx 文件（同现有 `write_docx()`）
2. 将 document 的 section 设置为两栏等宽
3. 对每个有 `translated_text` 的段落，在原文段落后插入：分栏符段落 → 译文本段（蓝色）→ 分栏符段落
4. 表格保持完整宽度（暂不处理双栏）
5. 保存为 `{stem}_dual.docx`

- [ ] **Step 1: 在 backend.py 顶部添加所需的 import**

```python
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph
```

添加到 `backend.py` 现有 import 之后。

- [ ] **Step 2: 新增 `_set_two_columns()` 辅助函数**

```python
def _set_two_columns(doc: DocxDocument_PythonDocx) -> None:
    """Set all sections of the document to two-column equal-width layout."""
    for section in doc.sections:
        sect_pr = section._sectPr
        # Remove existing column definitions
        for existing_cols in sect_pr.findall(qn("w:cols")):
            sect_pr.remove(existing_cols)
        # Create two equal columns with 0.5 inch spacing
        cols = OxmlElement("w:cols")
        cols.set(qn("w:num"), "2")
        cols.set(qn("w:equalWidth"), "true")
        cols.set(qn("w:space"), "480")  # 0.5 inch in twips
        sect_pr.append(cols)
```

- [ ] **Step 3: 新增 `_insert_column_break_after()` 辅助函数**

```python
def _insert_column_break_after(element) -> None:
    """Insert a paragraph containing only a column break after *element*.
    
    In a two-column layout this moves content to the next column.
    """
    col_break_p = OxmlElement("w:p")
    run = OxmlElement("w:r")
    br = OxmlElement("w:br")
    br.set(qn("w:type"), "column")
    run.append(br)
    col_break_p.append(run)
    element.addnext(col_break_p)
```

- [ ] **Step 4: 新增 `_insert_dual_paragraph_after()` 辅助函数**

```python
DUAL_TRANSLATION_COLOR_HEX = "2E75B6"  # Office blue accent


def _insert_dual_paragraph_after(paragraph: Paragraph, translated_text: str) -> None:
    """After *paragraph* (original, left column), column-break into
    the right column, emit the translation (styled blue), then
    column-break back to the left column for the next original paragraph.
    """
    # 1) Column break → right column
    _insert_column_break_after(paragraph._element)

    # 2) Translation paragraph (blue)
    trans_p = OxmlElement("w:p")
    trans_run = OxmlElement("w:r")
    trans_props = OxmlElement("w:rPr")
    trans_color = OxmlElement("w:color")
    trans_color.set(qn("w:val"), DUAL_TRANSLATION_COLOR_HEX)
    trans_props.append(trans_color)
    trans_run.append(trans_props)
    trans_text = OxmlElement("w:t")
    trans_text.set(qn("xml:space"), "preserve")
    trans_text.text = translated_text
    trans_run.append(trans_text)
    trans_p.append(trans_run)

    # Insert after the column-break paragraph
    # (paragraph._element.addnext(col_break) was called above,
    #  so col_break is next after paragraph._element;
    #  we insert trans_p after that col_break)
    col_break_element = paragraph._element.getnext()
    if col_break_element is not None:
        col_break_element.addnext(trans_p)
    else:
        paragraph._element.addnext(trans_p)

    # 3) Column break → back to left column for next original
    _insert_column_break_after(trans_p)
```

- [ ] **Step 5: 新增 `_inject_paragraphs_dual()` 函数，遍历并注入译文**

```python
def _inject_paragraphs_dual(doc: DocxDocument_PythonDocx, docx_doc: DocxDocument) -> None:
    """Walk document paragraphs in reverse, inserting column breaks and
    translations between original-text paragraphs for dual-column display.
    
    Reverse iteration is used so that insertions do not shift indices of
    paragraphs yet to be processed.
    """
    doc_paragraphs = list(doc.paragraphs)
    for i in range(len(docx_doc.paragraphs) - 1, -1, -1):
        if i >= len(doc_paragraphs):
            break
        para_info = docx_doc.paragraphs[i]
        translated = para_info.translated_text
        if not translated or not translated.strip():
            continue
        if translated == para_info.text:
            continue  # nothing to show

        wp = doc_paragraphs[i]
        _insert_dual_paragraph_after(wp, translated)
```

- [ ] **Step 6: 新增 `write_dual_docx()` 主函数**

```python
def write_dual_docx(
    docx_doc: DocxDocument,
    output_path: str,
) -> None:
    """Write a dual-language .docx with original and translation in
    a side-by-side two-column layout.
    
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

        # Set two-column layout
        _set_two_columns(doc)

        # Insert translations as dual-column pairs
        _inject_paragraphs_dual(doc, docx_doc)

        # Table cells: keep original text, append translation
        _replace_table_cells_keep_original(doc, docx_doc)

        doc.save(output_path)
        logger.info("Dual DOCX saved to: %s", output_path)
    finally:
        Path(tmpfd.name).unlink(missing_ok=True)
```

- [ ] **Step 7: 新增 `_replace_table_cells_keep_original()` 处理表格的双语输出**

```python
def _replace_table_cells_keep_original(doc: DocxDocument_PythonDocx, docx_doc: DocxDocument) -> None:
    """For table cells, keep original text and append translation in a
    new paragraph inside the same cell (blue color)."""
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
                # Add translation as a new paragraph in the cell
                new_para = OxmlElement("w:p")
                run = OxmlElement("w:r")
                rpr = OxmlElement("w:rPr")
                color = OxmlElement("w:color")
                color.set(qn("w:val"), DUAL_TRANSLATION_COLOR_HEX)
                rpr.append(color)
                run.append(rpr)
                t_el = OxmlElement("w:t")
                t_el.set(qn("xml:space"), "preserve")
                t_el.text = translated
                run.append(t_el)
                new_para.append(run)
                cell._element.append(new_para)
```

**验证：**
```bash
uv run python -c "
from babeldoc.format.docx.backend import write_dual_docx, _set_two_columns, _insert_column_break_after
print('Dual backend functions import OK')
"
```

---

### Task 2: 修改 `docx_translate.py`，支持 `no_dual`/`no_mono` 参数

**Files:**
- Modify: `babeldoc/format/docx/docx_translate.py`

- [ ] **Step 1: 导入 `write_dual_docx`**

```python
from babeldoc.format.docx.backend import write_docx
from babeldoc.format.docx.backend import write_dual_docx
```

- [ ] **Step 2: 修改 `translate_docx()` 函数签名，添加参数**

```python
def translate_docx(
    input_file: str,
    output_dir: str | None,
    translator: BaseTranslator,
    lang_in: str,
    lang_out: str,
    no_dual: bool = False,
    no_mono: bool = False,
) -> dict:
```

- [ ] **Step 3: 修改输出文件名逻辑**

```python
    stem = input_path.stem

    # Mono output (translated-only)
    mono_output_path: Path | None = None
    if not no_mono:
        mono_filename = f"{stem}_translated.docx"
        mono_output_path = output_dir_path / mono_filename
        # ... existing write_docx call ...

    # Dual output (bilingual side-by-side)
    dual_output_path: Path | None = None
    if not no_dual:
        dual_filename = f"{stem}_dual.docx"
        dual_output_path = output_dir_path / dual_filename
        write_dual_docx(docx_doc, str(dual_output_path))
```

- [ ] **Step 4: 修改返回值，包含 dual path**

```python
    return {
        "output_path": str(mono_output_path) if mono_output_path else None,
        "dual_output_path": str(dual_output_path) if dual_output_path else None,
        "total_seconds": elapsed,
        "input_file": input_file,
        "lang_in": lang_in,
        "lang_out": lang_out,
    }
```

**完整修改后的 `translate_docx()` 函数代码：**

```python
def translate_docx(
    input_file: str,
    output_dir: str | None,
    translator: BaseTranslator,
    lang_in: str,
    lang_out: str,
    no_dual: bool = False,
    no_mono: bool = False,
) -> dict:
    start_time = time.time()

    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    if input_path.suffix.lower() != ".docx":
        raise ValueError(f"Expected .docx file, got: {input_path.suffix}")

    output_dir_path = Path(output_dir) if output_dir else input_path.parent
    output_dir_path.mkdir(parents=True, exist_ok=True)

    stem = input_path.stem
    dual_output_path: Path | None = None
    mono_output_path: Path | None = None

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

    # Step 4: Write output(s)
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
```

**验证：** 确保现有调用不受影响（`no_dual`/`no_mono` 都有默认值 `False`）。

---

### Task 3: 修改 `main.py`，将 `no_dual`/`no_mono` 传递到 docx 分支

**Files:**
- Modify: `babeldoc/main.py`

- [ ] **Step 1: 修改 docx 分支调用，传递 no_dual 和 no_mono**

`main.py:680-695` 的现有代码：

```python
if file_ext == ".docx":
    from babeldoc.format.docx.docx_translate import translate_docx

    result = translate_docx(
        input_file=file,
        output_dir=args.output,
        translator=translator,
        lang_in=args.lang_in,
        lang_out=args.lang_out,
    )
    logger.info(
        "DOCX translation completed: %s (%.2f seconds)",
        result["output_path"],
        result["total_seconds"],
    )
    continue
```

修改为：

```python
if file_ext == ".docx":
    from babeldoc.format.docx.docx_translate import translate_docx

    # Mirror PDF dual behavior:
    #   no_dual=False  → produce both mono + dual (default)
    #   no_dual=True   → mono only
    #   no_mono=True   → dual only
    result = translate_docx(
        input_file=file,
        output_dir=args.output,
        translator=translator,
        lang_in=args.lang_in,
        lang_out=args.lang_out,
        no_dual=args.no_dual,
        no_mono=args.no_mono,
    )
    if result.get("output_path"):
        logger.info(
            "Monolingual DOCX: %s (%.2f seconds)",
            result["output_path"],
            result["total_seconds"],
        )
    if result.get("dual_output_path"):
        logger.info(
            "Dual-language DOCX: %s",
            result["dual_output_path"],
        )
    continue
```

**验证：**
```bash
uv run python -m compileall babeldoc/format/docx/ babeldoc/main.py
```

---

## 自检清单

### 1. Spec 覆盖

- ✅ 双栏左右对照（word 分栏 + 分栏符）
- ✅ 镜像 PDF 输出行为（默认同时输出 mono + dual）
- ✅ 不使用表格
- ✅ 向后兼容（现有 `translate_docx()` 调用不传新参数，默认为 `no_dual=False, no_mono=False`）
- ✅ 表格内也显示对照（原文保留 + 蓝色译文段落）
- ✅ 通过 `--no-dual` 和 `--no-mono` CLI 参数控制

### 2. 类型/签名一致性检查

- `translate_docx()` 返回值新增 `dual_output_path` 键，现有 `output_path` 保持不变
- `write_dual_docx()` 签名与 `write_docx()` 一致：`(docx_doc, output_path)`
- `no_dual`/`no_mono` 默认值 `False` 保证向后兼容

### 3. 边界情况

- 空段落：跳过（`not translated.strip()` 检查）
- 原文=译文：跳过（`translated == para_info.text` 检查）
- 表格单元格内容过多：保留原文 + 在单元格新增蓝色段落
- 多次运行同一输入：文件名不冲突（`_translated` vs `_dual`）

---

*Plan saved. Ready for execution.*
