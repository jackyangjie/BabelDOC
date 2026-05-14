# BabelDOC 项目知识库

**生成时间:** 2026-05-14
**许可证:** AGPL-3.0
**Python:** >=3.10, <3.14

## 概述

BabelDOC 是一个 PDF/文档翻译和双语对照工具。核心流程：解析文档 → 创建中间层（IL）→ 翻译 → 排版/输出。支持 PDF（复杂排版+公式）和 DOCX（双栏对照）格式。

**技术栈:** Python 3.10+, onnxruntime (ML推理), OpenAI API (翻译), PyMuPDF (PDF处理), pydantic, scikit-image, ruff (lint/format)

## 项目结构

```
BabelDOC/
├── babeldoc/           # 主源码包
│   ├── main.py         # CLI入口 (945行)
│   ├── const.py        # 全局常量、缓存、进程池
│   ├── glossary.py     # 术语表管理
│   ├── progress_monitor.py  # 进度监控
│   ├── format/         # PDF/DOCX格式处理
│   │   ├── pdf/        # PDF管线 (解析→IL→翻译→排版→输出)
│   │   └── docx/       # DOCX管线 (解析→IL→翻译→输出)
│   ├── pdfminer/       # Fork的pdfminer.six库
│   ├── docvision/      # ML文档视觉分析
│   ├── translator/     # 翻译引擎(OpenAI)
│   ├── tools/          # 开发工具
│   ├── utils/          # 通用工具类
│   ├── assets/         # 嵌入的模型资产
│   ├── babeldoc_exception/  # 异常层次
│   └── asynchronize/   # 异步回调工具
├── docs/               # MkDocs文档站点
├── examples/           # PDF示例文件
└── .github/workflows/  # CI配置
```

## 查找指南

| 任务 | 位置 | 说明 |
|------|------|------|
| CLI入口 | `babeldoc/main.py` | configargparse CLI, `babeldoc.main:cli` |
| 高級API | `babeldoc/format/pdf/high_level.py` | 翻译全流程编排 |
| 翻译配置 | `babeldoc/format/pdf/translation_config.py` | TranslationConfig, TranslateResult |
| IL数据模型(PDF) | `babeldoc/format/pdf/document_il/il_version_1.py` | 1343行, 所有IL数据类 |
| PDF解析(新) | `babeldoc/format/pdf/new_parser/` | 44文件, 高性能解析器 |
| PDF解析(旧) | `babeldoc/pdfminer/` | 32文件, forked pdfminer.six |
| IL→PDF输出 | `babeldoc/format/pdf/document_il/backend/pdf_creater.py` | 1653行, PDF生成核心 |
| 排版引擎 | `babeldoc/format/pdf/document_il/midend/typesetting.py` | 1672行 |
| ML布局分析 | `babeldoc/docvision/` | 文档布局OCR |
| 翻译引擎 | `babeldoc/translator/translator.py` | OpenAI API调用 |
| **DOCX翻译** | `babeldoc/format/docx/` | 4文件: frontend→translate→backend |
| DOCX IL模型 | `babeldoc/format/docx/il.py` | 65行, DocxDocument + 段落/表格 |
| DOCX前端(解析) | `babeldoc/format/docx/frontend.py` | 读取 .docx → DocxDocument |
| DOCX翻译编排 | `babeldoc/format/docx/docx_translate.py` | 翻译逻辑 + mono/dual输出选择 |
| DOCX后端(输出) | `babeldoc/format/docx/backend.py` | write_docx(mono) + write_dual_docx(双栏对照) |
| 工具函数 | `babeldoc/utils/` | 原子整数、内存工具、线程池 |
| **Executor API** | `babeldoc/tools/executor/` | HTTP API 服务层 |
| Executor 适配器 | `babeldoc/tools/executor/babeldoc_adapter.py` | PDF/DOCX 分流、结果序列化 |

## 约定

### 代码风格
- **格式化:** ruff format (兼容black风格, 行宽88)
- **lint:** ruff check (忽略 E203/E261/E501/E741/F841/C901/S101/SIM 等)
- **pre-commit:** ruff check --fix + ruff-format
- **类型注解:** 使用 `| None` 联合类型语法 (Python 3.10+)
- **数据类:** 大量使用 `@dataclass(slots=True)` (Python 3.10+)

### 架构模式
- **IL管线:** PDF→[frontend]→DocumentIL→[midend处理链]→[backend]→PDF
  - frontend: PDF→IL 创建 (`il_creater.py`, `il_creater_active.py`)
  - midend: 顺序处理链 - 布局解析→段落查找→样式/公式→翻译→表格→排版
  - backend: IL→PDF 输出 (`pdf_creater.py`)
- **DOCX管线:** .docx→[frontend]→DocxDocument→[translate]→[backend]→.docx
  - frontend: `read_docx()` 读 .docx → DocxDocument (段落+runs+表格)
  - translate: `translate_docx()` 调用 BaseTranslator 逐段翻译
  - backend: `write_docx()` 替换原文（mono）或 `write_dual_docx()` 双栏对照（dual）
- **DOCX双栏对照:** 使用 Word 原生双栏布局(`<w:cols w:num="2"/>`) + 分栏符(`<w:br w:type="column"/>`)实现左右对照。原文在左栏，蓝色译文在右栏。输出行为镜像PDF：默认同时输出 `_translated.docx`(mono) 和 `_dual.docx`(dual)，通过 `--no-dual`/`--no-mono` 控制。
- **新解析器双模式:** `new_parser/` 支持 active 模式(快速)和 native 模式(精确)
- **PDF分片:** 大PDF文件自动分片处理 (`split_manager.py`), 结果合并 (`result_merger.py`)
- **异步回调:** `asynchronize/` 用asyncio.Queue实现线程安全进度回调

### 包管理器
- 使用 **uv** (替代pip/poetry)
- 构建系统: hatchling
- workflow命令: `uv sync`, `uv run`, `uv build`

## 反模式(本项目)
- **`# type: ignore`** — 项目中存在多处使用，添加新的 `type: ignore` 前需确认无法通过类型注解解决
- **`# noqa`** — 存在少量使用，应该添加具体规则编号（如 `# noqa: F841`）
- **不要添加新依赖** — 已包含大量PDF/ML/翻译依赖
- **不要修改 pdfminer/** — 这是fork的pdfminer.six, 仅做最小必要修改
- **不要跳过 `format/__init__.py`** — 保持命名空间包结构
- **避免新增大型数据文件** — fontmetrics/glyphlist 已4K+行, 数据应放 `runtime/data/`
- **避免全局可变状态** — `const.py` 中有全局进程池 `_process_pool` 和线程锁，使用时需注意线程安全

## COMMANDS

```bash
# 开发环境
uv sync                          # 安装依赖
uv run ruff check .              # lint检查
uv run ruff format .             # 格式化
uv run python -m compileall babeldoc  # 编译检查

# 构建
uv build                         # 构建wheel/sdist

# 运行
uv run babeldoc --help           # CLI帮助
uv run babeldoc --files input.pdf --openai --openai-api-key YOUR_KEY
uv run babeldoc --files input.docx --openai --openai-api-key YOUR_KEY  # DOCX翻译 (默认输出 mono + dual)
uv run babeldoc --files input.docx --no-dual --openai --openai-api-key YOUR_KEY  # 只输出 mono
uv run babeldoc --files input.docx --no-mono --openai --openai-api-key YOUR_KEY  # 只输出 dual

# CI (GitHub Actions)
# checks.yml: lint → build → compileall → smoke test → E2E
# lint.yml: ruff check
# publish-to-pypi.yml: 发布到PyPI
```

## NOTES
- **无测试用例!** 项目没有 `test_*.py` 文件, 没有 pytest 配置。CI中仅有smoke test和E2E测试
- **web/** 目录已gitignored — 可能有前端Web界面但不在主仓库
- `babeldoc/format/__init__.py` 和 `babeldoc/format/pdf/__init__.py` 是空的命名空间包
- `babeldoc/format/txt` 在gitignore中 — 说明TXT格式在计划中但未实现
- `examples/` 在gitignore中 — 示例文件不提交到仓库
- 文档在 `docs/` 目录, 使用 mkdocs-material 构建
- 原始repo是 `funstory-ai/BabelDOC`, 当前clone是 `jackyangjie/BabelDOC`
- **DOCX双栏对照**: `write_dual_docx()` 在 `backend.py` 中。使用 Word 原生 `<w:cols>` 双栏布局 + `<w:br w:type="column"/>` 分栏符实现。蓝色常量 `_DUAL_TRANSLATION_COLOR_HEX = "2E75B6"`。表格单元格在原文后追加蓝色译文段落。
- **DOCX与PDF输出差异**: DOCX无 `TranslateResult` 类，`translate_docx()` 返回字典含 `output_path`(mono) 和 `dual_output_path`(dual)。PDF 的 `--no-dual`/`--no-mono` 对 DOCX 同样生效。
- **HTTP API(DOCX)**: `babeldoc_adapter.py::run_babeldoc_request()` 通过文件后缀自动分流。DOCX 调用 `_run_docx_translate()` → `translate_docx()`，结果 payload 返回 `mono_docx`/`dual_docx` 字段。
