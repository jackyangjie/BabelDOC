# babeldoc/ — 主源码包

## 概述

BabelDOC 的核心 Python 包。包含 CLI、PDF 解析/生成、ML 视觉分析、翻译引擎以及所有业务逻辑。

## 架构概览

```
babeldoc/                    # 包根 (5文件 + 12子包)
├── main.py                  # CLI入口 (945行)
├── const.py                 # 全局常量、缓存路径、进程池管理
├── glossary.py              # 术语表加载/匹配
├── progress_monitor.py      # Rich进度条监控
│
├── format/pdf/              # ⭐ 核心: PDF解析→IL→翻译→PDF生成
├── pdfminer/                # Forked pdfminer.six (PDF解析)
├── docvision/               # ML文档布局分析 (ONNX推理)
├── translator/              # OpenAI翻译引擎
│
├── tools/                   # 开发工具
├── utils/                   # 通用工具
├── assets/                  # 嵌入资源 (模型下载)
├── babeldoc_exception/      # 异常定义
└── asynchronize/            # 异步回调适配器
```

## 关键入口

| 符号 | 文件 | 说明 |
|------|------|------|
| `cli()` | `main.py` | CLI入口点 (console_scripts) |
| `translate_pdf()` | `format/pdf/high_level.py` | 高級翻译API |
| `TranslationConfig` | `format/pdf/translation_config.py` | 核心配置数据类 |
| `translate_document()` | `format/pdf/document_il/midend/il_translator.py` | IL翻译器 |

## 约定

- 子包用 `__init__.py` 导出公共API (`format/` 和 `format/pdf/` 是命名空间包)
- `format/pdf/new_parser/__init__.py` 仅包含 `"""Native PDF parser package for BabelDOC."""` docstring
- 跨模块类型在 `translation_config.py` 中定义 (如 `SharedContextCrossSplitPart`)
