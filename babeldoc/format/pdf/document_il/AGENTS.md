# babeldoc/format/pdf/document_il/ — 文档中间层(IL)

## 概述

文档中间层(Document Intermediate Language) — PDF 翻译的核心抽象层。将PDF解析为与格式无关的IL表示, 在IL上执行翻译/排版等操作, 再输出为PDF。

## 三层架构

```
PDF文件
  │
  ▼ [frontend/] IL创建器 (5文件)
  │   il_creater.py       # 标准IL创建 (1355行)
  │   il_creater_active.py # Active模式IL创建 (1574行)
  │   il_creater_active_support.py
  │   inline_image_params.py
  │
  ▼ [midend/] 处理管线 (12文件, 按序执行)
  │   1. layout_parser.py          # ⭐ 布局OCR分析
  │   2. paragraph_finder.py       # 段落识别/合并
  │   3. styles_and_formulas.py    # 样式&公式识别
  │   4. il_translator.py          # ⭐ IL翻译核心
  │   5. il_translator_llm_only.py # LLM-only翻译模式
  │   6. table_parser.py           # 表格解析
  │   7. typesetting.py            # ⭐ 排版引擎(1672行)
  │   8. add_debug_information.py  # 调试信息注入
  │   9. detect_scanned_file.py    # 扫描件检测
  │  10. automatic_term_extractor.py # 术语自动提取
  │  11. remove_descent.py         # 下行部分清理
  │
  ▼ [backend/] PDF生成器 (2文件)
  │   pdf_creater.py     # ⭐ IL→PDF (1653行)
  │
  ▼ 翻译后PDF
```

## IL数据模型

核心文件: `il_version_1.py` (1343行) — 用 `@dataclass(slots=True)` 定义所有IL类型。

关键IL类型:
- `Document` / `Page` / `PageLayout` — 文档结构
- `PdfCharacter` / `PdfSameStyleCharacters` — 字符级文本
- `PdfParagraph` / `PdfParagraphComposition` — 段落
- `PdfFont` / `PdfStyle` — 字体和样式
- `PdfFormula` / `PdfFigure` / `PdfPath` — 公式/图形/路径
- `PdfLine` / `PdfCurve` / `PdfRectangle` — 矢量图形

## 关键约定

- **midend处理是有序的** — 新增步骤必须按照正确的管线顺序插入
- `il_version_1.py` 是IL的规范定义 — 所有前端/中端/后端都依赖它
- `xml_converter.py` 提供IL的XML序列化/反序列化
- IL工具函数在 `utils/` 中 — 见 fontmap, extract_char, layout_helper, formular_helper 等
- `Document` 和 `Page` 的 `__init__` 中定义字段 — 用 `@dataclass` 注解
