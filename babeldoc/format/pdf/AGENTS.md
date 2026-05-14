# babeldoc/format/pdf/ — PDF 格式处理

## 概述

PDF 翻译的核心处理包。包含 PDF 解析、文档中间层(IL)表示、翻译管线、以及 PDF 重新生成的全部逻辑。

## 架构

```
format/pdf/
├── high_level.py           # 高級编排 (1118行) — 翻译全流程
├── translation_config.py   # TranslationConfig 配置中心
├── converter.py            # PDF→字符/布局转换器
├── split_manager.py        # 大PDF分片管理
├── result_merger.py        # 分片结果合并
├── legacy_parse.py         # 旧解析器封装
├── parse_only.py           # 仅解析(无翻译)
├── parse_shared.py         # 解析共享逻辑
├── pdfinterp.py            # PDF指令解释器
├── awlt_char.py            # 字符级处理
│
├── new_parser/             # [44文件] 新PDF解析器 (active+native双模式)
├── document_il/            # 文档中间层 (frontend→midend→backend)
└── babelpdf/               # [7文件] PDF输出生成 (字体/编码/CMap)
```

## 处理管线

```
PDF文件
  │
  ▼ [分片] SplitManager (大文件分片)
  │
  ▼ [解析] new_parser/ 或 pdfminer/legacy
  │
  ▼ [IL创建] document_il/frontend/ → Document IL对象
  │
  ▼ [翻译管线] document_il/midend/ (8步处理)
  │   layout_parser → paragraph_finder → styles_and_formulas
  │   → il_translator → table_parser → typesetting → ...
  │
  ▼ [PDF生成] document_il/backend/pdf_creater.py
  │
  ▼ [合并] ResultMerger
  │
  ▼ 翻译后PDF
```

## 约定

- 所有管线步骤的配置统一由 `TranslationConfig` 传入
- `high_level.py` 是唯一的全流程编排入口 — 不要在别处复制管线逻辑
- 分片处理通过 `SharedContextCrossSplitPart` 共享跨分片上下文 (标题、术语表)
- 分片策略默认使用 `PageCountStrategy` (`BaseSplitStrategy` 子类)
