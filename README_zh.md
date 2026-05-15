<div align="center">

<br/>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://s.immersivetranslate.com/assets/uploads/babeldoc-big-logo-darkmode-with-transparent-background-IKuNO1.svg" width="320px" alt="BabelDOC"/>
  <img src="https://s.immersivetranslate.com/assets/uploads/babeldoc-big-logo-with-transparent-background-2xweBr.svg" width="320px" alt="BabelDOC"/>
</picture>

<p>
  <!-- PyPI -->
  <a href="https://pypi.org/project/BabelDOC/">
    <img src="https://img.shields.io/pypi/v/BabelDOC"></a>
  <a href="https://pepy.tech/projects/BabelDOC">
    <img src="https://static.pepy.tech/badge/BabelDOC"></a>
  <!-- License -->
  <a href="./LICENSE">
    <img src="https://img.shields.io/github/license/funstory-ai/BabelDOC"></a>
  <a href="https://t.me/+Z9_SgnxmsmA5NzBl">
    <img src="https://img.shields.io/badge/Telegram-2CA5E0?style=flat-squeare&logo=telegram&logoColor=white"></a>
  <a href="https://deepwiki.com/funstory-ai/BabelDOC"><img src="https://deepwiki.com/badge.svg" alt="Ask DeepWiki"></a>
</p>

<a href="https://trendshift.io/repositories/13358" target="_blank"><img src="https://trendshift.io/api/badge/repositories/13358" alt="funstory-ai%2FBabelDOC | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

</div>

**[English](./README.md) | 中文**

PDF / DOCX 科技论文翻译与双语对照库。

- 支持 **PDF** 文件翻译：保留复杂排版、公式、表格和嵌入图片中的文字翻译
- 支持 **DOCX**（Word）文件翻译：段落/表格翻译、嵌入图片中的文字 OCR 翻译
- 双栏对照（bilingual）输出：mono（仅译文）+ dual（原文/译文左右对照）
- **在线服务**：[沉浸式翻译 - BabelDOC](https://app.immersivetranslate.com/babel-doc/) Beta 版已上线，每月提供免费使用额度，详情请查看页面 FAQ
- **自部署**：[PDFMathTranslate-next](https://github.com/PDFMathTranslate-next/PDFMathTranslate-next) 支持 BabelDOC，可自部署 + WebUI，提供更多翻译服务
- 提供简单易用的[命令行界面](#快速开始)
- 提供 [Python API](#python-api)
- 主要为嵌入其他程序而设计，也可直接用于简单翻译任务

> [!TIP]
>
> 如何在 Zotero 中使用 BabelDOC
>
> 1. 沉浸式翻译 Pro 用户可使用 [immersive-translate/zotero-immersivetranslate](https://github.com/immersive-translate/zotero-immersivetranslate) 插件
>
> 2. PDFMathTranslate 自部署用户可使用 [guaguastandup/zotero-pdf2zh](https://github.com/guaguastandup/zotero-pdf2zh) 插件

[支持的语言](https://funstory-ai.github.io/BabelDOC/supported_languages/)

## 预览

<div align="center">
<img src="https://s.immersivetranslate.com/assets/r2-uploads/images/babeldoc-preview.png" width="80%"/>
</div>

## 快速开始

### 从 PyPI 安装

推荐使用 [uv](https://github.com/astral-sh/uv) 的 Tool 功能安装 BabelDOC。

1. 首先参照 [uv 安装指南](https://github.com/astral-sh/uv#installation) 安装 uv，并按要求配置 `PATH` 环境变量。

2. 使用以下命令安装 BabelDOC：

```bash
uv tool install --python 3.12 BabelDOC

babeldoc --help
```

3. 使用 `babeldoc` 命令，例如：

```bash
# PDF 翻译（mono + dual 双输出）
babeldoc --openai --openai-model "gpt-4o-mini" --openai-base-url "https://api.openai.com/v1" --openai-api-key "your-api-key-here" --files example.pdf

# DOCX / Word 翻译（mono + dual 双输出，含图片文字翻译）
babeldoc --openai --openai-model "gpt-4o-mini" --openai-base-url "https://api.openai.com/v1" --openai-api-key "your-api-key-here" --files example.docx

# 多个文件混合（PDF 和 DOCX 混用）
babeldoc --openai --openai-model "gpt-4o-mini" --openai-base-url "https://api.openai.com/v1" --openai-api-key "your-api-key-here" --files example1.pdf --files example2.docx
```

### 从源码安装

仍然推荐使用 [uv](https://github.com/astral-sh/uv) 管理虚拟环境。

1. 首先参照 [uv 安装指南](https://github.com/astral-sh/uv#installation) 安装 uv，并按要求配置 `PATH` 环境变量。

2. 使用以下命令安装 BabelDOC：

```bash
# 克隆项目
git clone https://github.com/funstory-ai/BabelDOC

# 进入项目目录
cd BabelDOC

# 安装依赖并运行
uv run babeldoc --help
```

3. 使用 `uv run babeldoc` 命令，例如：

```bash
# PDF
uv run babeldoc --files example.pdf --openai --openai-model "gpt-4o-mini" --openai-base-url "https://api.openai.com/v1" --openai-api-key "your-api-key-here"

# DOCX / Word
uv run babeldoc --files example.docx --openai --openai-model "gpt-4o-mini" --openai-base-url "https://api.openai.com/v1" --openai-api-key "your-api-key-here"

# 多个文件混合
uv run babeldoc --files example.pdf --files example2.docx --openai --openai-model "gpt-4o-mini" --openai-base-url "https://api.openai.com/v1" --openai-api-key "your-api-key-here"
```

> [!TIP]
> 推荐使用绝对路径。

## 高级选项

> [!NOTE]
> CLI 主要用于调试。终端用户可以直接使用**在线服务**：[沉浸式翻译 - BabelDOC](https://app.immersivetranslate.com/babel-doc/) 每月 1000 页免费额度。
>
> 需要自部署的终端用户请使用 [PDFMathTranslate 2.0](https://github.com/PDFMathTranslate/PDFMathTranslate-next)
>
> 如果某个选项未在下方列出，说明它是维护者使用的调试选项，请不要使用。

### 语言选项

- `--lang-in`, `-li`：源语言代码（默认：en）
- `--lang-out`, `-lo`：目标语言代码（默认：zh）

> [!TIP]
> 本项目目前主要专注于英译中场景，其他语言场景未经全面测试。
>
> （2025.3.1 更新）：已初步支持英语作为目标语言，主要优化了单词内部换行问题（[0-9A-Za-z]+）。
>
> [HELP WANTED: 收集更多语言的单词正则表达式](https://github.com/funstory-ai/BabelDOC/issues/129)

### PDF 处理选项

- `--files`：一个或多个输入 PDF 文件路径
- `--pages`, `-p`：指定翻译页面（如 "1,2,1-,-3,3-5"）。不设置则翻译所有页面
- `--split-short-lines`：强制将短行拆分为不同段落（可能导致排版问题和 Bug）
- `--short-line-split-factor`：拆分阈值因子（默认 0.8）。实际阈值为当前页所有行长度的中位数 × 该因子
- `--skip-clean`：跳过 PDF 清理步骤
- `--dual-translate-first`：在 dual PDF 模式中将翻译页放在前面（默认原文在前）
- `--disable-rich-text-translate`：禁用富文本翻译（有助于提高部分 PDF 兼容性）
- `--enhance-compatibility`：启用所有兼容性增强选项（等价于 --skip-clean --dual-translate-first --disable-rich-text-translate）
- `--use-alternating-pages-dual`：使用交替页面模式生成 dual PDF。启用时原文和翻译页交替排列。禁用时（默认）在同一页左右分栏显示
- `--watermark-output-mode`：水印输出模式控制：'watermarked'（默认）为翻译后 PDF 添加水印，'no_watermark' 不添加，'both' 同时输出
- `--no-dual`：跳过双语对照输出
- `--no-mono`：跳过纯译文输出
- `--skip-form-render`：跳过表单/图形渲染（PDF 表单元素渲染，不是数学公式）
- `--skip-curve-render`：跳过曲线渲染
- `--disable-graphic-element-process`：跳过图形元素处理（将平移 pdf_form 和 type3 字体中的图形元素）

### 翻译服务选项

- `--openai`：使用 OpenAI 兼容接口进行翻译
- `--openai-model`：模型名称（默认：gpt-4o-mini）
- `--openai-base-url`：API 地址
- `--openai-api-key`：API Key
- `--qps`：每秒查询数限制（默认 10）
- `--min-text-length`：最小文本长度。长度小于此值的文本将被跳过（默认 1）
- `--disable-same-text-fallback`：当翻译后文本与原文相同时，禁止使用原文作为回退（默认会将原文作为翻译结果）

### 其他选项

- `--output`, `-o`：输出目录
- `--debug`：启用调试日志和中间文件
- `--skip-scanned-dection`：跳过扫描件检测
- `--ocr-workaround`：使用 OCR 模式处理扫描件（耗时长、错误率高、不保留排版）

## Python API

详见 [docs/python-api.md](./docs/python-api.md)

## 工作原理

BabelDOC 定义了一个标准的文档中间表示（IL，Intermediate Layer），将解析器和渲染器解耦：

1. **Frontend（解析器）**：读取 PDF / DOCX 文件，解析为结构化的中间表示
2. **Midend（处理链）**：对中间表示进行布局分析、段落识别、公式处理、样式应用、文字翻译、图片文字翻译（OCR + 覆盖）
3. **Backend（渲染器）**：将处理后的中间表示渲染为新的 PDF / DOCX 文件

### 图片文字翻译
- **PDF**：提取页面中的图片 XObject → RapidOCR 文字检测 → OpenAI 翻译 → 覆盖翻译文字
- **DOCX**：提取嵌入的图片（inline shapes）→ RapidOCR 文字检测 → OpenAI 翻译 → 覆盖翻译文字
- **Dual 模式**：原文图片保持在左栏，翻译后的图片添加到右栏

这种架构使得新增解析器或渲染器变得简单——只需实现 IL 的输入或输出即可。

## 已知问题

1. 作者和参考文献部分的解析错误，翻译后可能合并为一段
2. 复杂的表格结构尚未完全支持
3. 不支持线条（line art）元素
4. 不支持首字下沉（drop caps）
5. 过大的页面会被跳过
6. DOCX 嵌入图片翻译后，JPEG 图片会转为 PNG 格式（文件大小可能增大）

## 贡献指南

BabelDOC 目前以维护者主导模式进行开发。欢迎提交 Bug 报告、可复现的 PDF、文档修复和小的兼容性修复。如果涉及解析、渲染、翻译或服务集成等行为的变更，请先提交 issue 讨论后再提交 Pull Request。

所有在 BabelDOC 及其子项目的代码库、issue 追踪、聊天室和邮件列表中互动的人员，均应遵守 BabelDOC 的[行为准则](https://github.com/funstory-ai/BabelDOC/blob/main/docs/CODE_OF_CONDUCT.md)。

[沉浸式翻译](https://immersivetranslate.com)每月为活跃贡献者赞助 Pro 会员兑换码，详见：[CONTRIBUTOR_REWARD.md](https://github.com/funstory-ai/BabelDOC/blob/main/docs/CONTRIBUTOR_REWARD.md)

## 发展路线图

- [x] PDF 文字翻译与排版保留
- [x] PDF 公式翻译
- [x] PDF 嵌入图片文字翻译（OCR + 覆盖）
- [x] DOCX 文字翻译（段落、表格）
- [x] DOCX 嵌入图片文字翻译（OCR + 覆盖）
- [x] 双语对照输出（PDF / DOCX）
- [ ] 表格支持
- [ ] 线条元素支持
- [ ] 跨页/跨列段落支持
- [ ] 更高级的排版功能
- [ ] 大纲（目录）支持
- [ ] ...

## 致谢

BabelDOC 仍处于早期开发阶段，许多地方还远未达到我们期望的完善程度。我们真诚感谢每一个 Bug 报告、批评、建议、可复现的 PDF、下游集成经验以及来自 BabelDOC 和相关上下游项目贡献者的付出。我们将持续迭代 BabelDOC，修复 Bug，逐步改进。

- [PDFMathTranslate](https://github.com/PDFMathTranslate/PDFMathTranslate)
- [DocLayout-YOLO](https://github.com/opendatalab/DocLayout-YOLO)
- [pdfminer](https://github.com/pdfminer/pdfminer.six)
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF)
- [RapidOCR](https://github.com/RapidAI/RapidOCR)（图片文字检测）
- [python-docx](https://github.com/python-openxml/python-docx)（DOCX 支持）
- [Asynchronize](https://github.com/multimeric/Asynchronize/tree/master?tab=readme-ov-file)
- [PriorityThreadPoolExecutor](https://github.com/oleglpts/PriorityThreadPoolExecutor)

<h2 id="star_hist">Star History</h2>

<a href="https://star-history.com/#funstory-ai/babeldoc&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=funstory-ai/babeldoc&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=funstory-ai/babeldoc&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=funstory-ai/babeldoc&type=Date" />
 </picture>
</a>
