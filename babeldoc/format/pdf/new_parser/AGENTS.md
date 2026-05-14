# babeldoc/format/pdf/new_parser/ — 新 PDF 解析器

## 概述

44 个文件的新一代 PDF 解析器。支持两种运行模式：**active 模式**(实时访问原始 PDF 字节, 性能优先)和 **native 模式**(完全自主解析, 不依赖外部库)。也提供基于 PyMuPDF 的集成模式。

## 模块结构

```
new_parser/
├── __init__.py              # 包docstring
│
├── active_*.py              # Active模式 (9文件)
│   ├── active_parse_runtime.py       # 运行时解析
│   ├── active_direct_font_backend.py  # 直接字体访问
│   ├── active_font_backend.py         # 字体后端
│   ├── active_font_resource_runtime.py
│   ├── active_font_runtime.py
│   ├── active_object_backend.py       # 对象后端
│   ├── active_object_projection.py
│   ├── active_value_access.py
│   └── active_direct_font_backend.py
│
├── native_*.py              # Native模式 (2文件)
│   ├── native_parse.py               # 自主PDF解析
│   └── native_page_execution_session.py
│   └── native_page_interpreter.py
│
├── pymupdf_*.py             # PyMuPDF集成 (5文件)
│   ├── pymupdf_candidate_parse.py
│   ├── pymupdf_object_access.py
│   ├── pymupdf_page_execution_session.py
│   ├── pymupdf_page_view_access.py
│   └── pymupdf_prepared_page_access.py
│
├── page_*.py                # 页面处理 (7文件)
│   ├── page_api.py, page_content_access.py
│   ├── page_content_execution.py
│   ├── page_execution_session.py
│   ├── page_interpreter.py
│   └── prepared_page*.py (prepared, prepared_debug, prepared_execution)
│
├── interpreter.py           # 指令解释器核心
├── tokenizer.py             # PDF tokenizer
├── object_parser.py         # PDF对象解析
├── object_model.py          # 对象模型
├── resources.py             # 资源管理
├── state.py                 # 解析状态
├── text_positioning.py      # 文本定位
├── glyphs.py                # 字形处理
├── bridge_types.py          # 桥接类型
│
├── runtime/                 # [13文件] 运行时类型系统
│   ├── object_primitives_runtime.py
│   ├── object_stream_runtime.py
│   ├── font_data_runtime.py
│   ├── font_encoding_runtime.py
│   ├── cid_cmap_runtime.py
│   └── ...
│
├── sinks/                   # [2文件] 输出接收器
│   ├── legacy_ir.py         # 旧版IR兼容
│   └── native_text.py       # 原生文本输出
│
└── compat/                  # [1文件] 兼容层
```

## 关键约定

- **active_* 文件**: 操作原始PDF字节流, 性能更优但不做完整校验
- **native_* 文件**: 自主解析PDF结构, 不依赖PyMuPDF/pdfminer
- **pymupdf_* 文件**: 基于PyMuPDF的集成方案, 作为candidate解析
- **prepared_* 文件**: 预解析页面缓存机制, 加速重复访问
- `font_types.py` 和 `font_spec_primitives.py` 定义了字体系统抽象
- `base_operations.py` 提供基础操作原语
