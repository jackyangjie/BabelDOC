# babeldoc/docvision/ — 文档视觉分析

## 概述

基于 ONNX 的文档布局分析与 OCR 模块。从 PDF 页面图像中检测文本块、公式、表格、图片等元素的布局结构，为后续翻译提供版面信息。

## 结构

```
docvision/
├── __init__.py        # 包初始化
├── base_doclayout.py  # ⭐ 布局分析基类/抽象接口
├── doclayout.py       # ⭐ 本地布局分析 (ONNX模型推理)
├── README.md          # 模块说明
├── rpc_doclayout*.py  # RPC远程布局服务客户端 (8文件)
│   rpc_doclayout.py ~ rpc_doclayout8.py
│   # 支持多个远程布局服务端点, 用于分布式/GPU部署
└── table_detection/   # 表格检测子模块
```

## 关键约定

- 支持 **本地推理** (`doclayout.py`) 和 **RPC远程调用** (`rpc_doclayout*.py`) 两种模式
- RPC 客户端连接外部部署的布局分析服务 — 通过 CLI `--rpc-doclayout*` 参数配置
- `rpc_doclayout*.py` 8个文件结构高度相似, 仅端点不同
- 核心依赖: onnxruntime、numpy、opencv-python-headless、scikit-image
- **midend/layout_parser.py** 调用此模块获取布局结果, 结果用于段落查找和排版
- `base_doclayout.py` 定义抽象接口, `doclayout.py` 是默认本地实现
- 输入: PDF页面渲染图像; 输出: 布局元素边界框+类型标签
