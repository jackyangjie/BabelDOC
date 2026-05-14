# babeldoc/pdfminer/ — Fork 的 pdfminer.six 库

## 概述

从 [pdfminer.six](https://github.com/pdfminer/pdfminer.six) fork 的 PDF 解析库, 针对 BabelDOC 翻译需求做了定制修改。提供底层的 PDF 解析、字体处理、CMap 支持等能力。

## 文件说明

### 核心解析
| 文件 | 行数 | 说明 |
|------|------|------|
| `pdfinterp.py` | 43K | PDF指令解释器 (核心) |
| `pdfdocument.py` | 37K | PDF文档结构解析 |
| `pdffont.py` | 36K | PDF字体处理 |
| `converter.py` | 37K | PDF→文本/布局转换 |
| `pdfparser.py` | 5.7K | PDF语法解析器 |
| `pdftypes.py` | 12K | PDF对象类型 |
| `psparser.py` | 20K | PostScript解析器 |

### 布局与输出
| 文件 | 说明 |
|------|------|
| `layout.py` (33K) | PDF布局分析 |
| `pdfpage.py` | 页面处理 |
| `pdfdevice.py` | PDF设备抽象 |
| `high_level.py` | 高级提取API |

### 数据文件 (只读, 不修改)
| 文件 | 行数 | 内容 |
|------|------|------|
| `fontmetrics.py` | **110K** | Adobe字体度量数据 |
| `glyphlist.py` | **128K** | Unicode字形映射 |
| `encodingdb.py` | 3.9K | 编码数据库 |

### 编码/压缩
`arcfour.py`, `ascii85.py`, `ccitt.py`, `lzw.py`, `runlength.py`, `jbig2.py`, `image.py`

### CMap 资源
`cmap/` — 148个 `.gz` 文件, Adobe字符映射表(CJK支持)

## 重要约定

- **除非修复关键 bug, 不要修改此目录的文件** — 这是上游 fork, 保持差异最小化
- **不要新增功能到此目录** — 新功能应使用 `new_parser/`
- fork 的修改主要集中在: 扩展字体支持、增强字符提取以获取更精细的位置/样式信息
- 版本号通过 `importlib.metadata.version("pdfminer.six")` 获取
- `babeldoc/format/pdf/pdfinterp.py` 是对此模块的上层封装
