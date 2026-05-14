# BabelDOC HTTP API 接口文档

PDF 科学论文翻译和双语对照工具的 HTTP API 服务。

---

## 启动服务

```bash
export BABELDOC_EXECUTOR_WORKROOT=/path/to/workroot
python -m babeldoc.tools.executor --host 0.0.0.0 --port 7860
```

---

## 接口概览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/healthz` | 健康检查 |
| POST | `/v1/executions` | 创建翻译任务 |
| GET | `/v1/executions/{execution_id}/events?after_sequence=N` | 获取任务进度（SSE 流） |
| POST | `/v1/abort` | 中止当前任务 |
| POST | `/v1/pdf/watermark1` | 添加平铺水印 |
| POST | `/v1/pdf/watermark2` | 添加平铺水印（模式2） |

> **注意**：同时只能处理一个翻译任务，新任务会返回 `409 Conflict`。

---

## 1. 健康检查

检测服务是否正常运行。

### 请求

```bash
curl http://127.0.0.1:7860/healthz
```

### 响应

```json
{
  "status": "ok"
}
```

---

## 2. 创建翻译任务

提交 PDF 翻译任务，返回 `execution_id` 用于后续查询进度。

### 请求

```bash
curl -X POST http://127.0.0.1:7860/v1/executions \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "my-task-001",
    "paths": {
      "input_file": "docs/sample.pdf",
      "output_dir": "output/"
    },
    "translation_config": {
      "lang_in": "en",
      "lang_out": "zh",
      "debug": false,
      "no_dual": false,
      "no_mono": false
    },
    "runtime_limits": {
      "qps": 4,
      "report_interval_seconds": 0.5,
      "max_pages_per_part": 10,
      "pool_max_workers": 4,
      "term_pool_max_workers": 4
    },
    "gateways": {
      "main_llm": {
        "model": "trs-m5",
        "base_url": "http://192.168.5.82:23000/api/v1",
        "api_key": "sk-xxx"
      },
      "ate_llm": {
        "model": "trs-m5",
        "base_url": "http://192.168.5.82:23000/api/v1",
        "api_key": "sk-xxx"
      },
      "layout": {
        "adapter": "rpc_doclayout8",
        "base_url": "http://layout-service:5000",
        "requires_line_extraction": true
      }
    }
  }'
```

### 成功响应

```
HTTP 201 Created
```

```json
{
  "execution_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "started",
  "initial_sequence": 12345
}
```

### 忙时响应

```
HTTP 409 Conflict
```

```json
{
  "code": "busy",
  "message": "executor is busy",
  "snapshot": {
    "execution_id": "prev-task-id",
    "task_id": "prev-task",
    "request": {}
  }
}
```

### 参数说明

#### translation_config

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `lang_in` | string | 是 | 源语言代码，如 `en`、`ja`、`fr` |
| `lang_out` | string | 是 | 目标语言代码，如 `zh` |
| `pages` | string | 否 | 页码范围，如 `"1-10"` |
| `debug` | boolean | 是 | 是否开启调试模式 |
| `no_dual` | boolean | 是 | 不生成双语对照版 |
| `no_mono` | boolean | 是 | 不生成单语版 |
| `skip_clean` | boolean | 否 | 跳过清理临时文件 |
| `dual_translate_first` | boolean | 否 | 优先翻译双语版 |
| `disable_rich_text_translate` | boolean | 否 | 禁用富文本翻译 |
| `use_side_by_side_dual` | boolean | 否 | 使用并排双语模式 |
| `use_alternating_pages_dual` | boolean | 否 | 使用交替页面双语模式 |
| `skip_scanned_detection` | boolean | 否 | 跳过扫描件检测 |
| `ocr_workaround` | boolean | 否 | 启用 OCR 替代方案 |
| `auto_extract_glossary` | boolean | 否 | 自动提取术语表 |
| `auto_enable_ocr_workaround` | boolean | 否 | 自动启用 OCR 替代方案 |
| `primary_font_family` | string | 否 | 首选字体族 |
| `only_include_translated_page` | boolean | 否 | 只包含翻译后的页面 |
| `merge_alternating_line_numbers` | boolean | 否 | 合并交替行号 |
| `remove_non_formula_lines` | boolean | 否 | 移除非公式行 |
| `custom_system_prompt` | string | 否 | 自定义系统提示词 |

#### runtime_limits

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `qps` | int | 是 | 每秒最大 LLM API 请求数 |
| `report_interval_seconds` | number | 是 | 进度上报间隔（秒） |
| `max_pages_per_part` | int | 是 | PDF 分片页数，大 PDF 按此拆分处理 |
| `pool_max_workers` | int | 是 | 翻译并发线程数 |
| `term_pool_max_workers` | int | 是 | 术语提取并发线程数 |

#### gateways

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `main_llm` | object | 是 | 翻译用 LLM 配置 |
| `main_llm.model` | string | 是 | 模型名称 |
| `main_llm.base_url` | string | 是 | API 端点地址 |
| `main_llm.api_key` | string | 是 | API 密钥 |
| `ate_llm` | object | 是 | 术语提取用 LLM 配置 |
| `ate_llm.model` | string | 是 | 模型名称 |
| `ate_llm.base_url` | string | 是 | API 端点地址 |
| `ate_llm.api_key` | string | 是 | API 密钥 |
| `layout` | object | 是 | 布局分析服务配置 |
| `layout.adapter` | string | 是 | 适配器，目前仅支持 `rpc_doclayout8` |
| `layout.base_url` | string | 是 | 布局分析服务地址 |
| `layout.requires_line_extraction` | boolean | 是 | 是否需要提取线条信息 |

---

## 3. 获取任务事件流 (SSE)

通过 Server-Sent Events 流式获取翻译进度和结果。

### 请求

```bash
# 首次从 after_sequence=0 开始
curl -N http://127.0.0.1:7860/v1/executions/a1b2c3d4-e5f6-7890-abcd-ef1234567890/events?after_sequence=0
```

### 响应（SSE 流，每行一个 JSON）

**progress 事件** — 翻译进度更新

```json
{
  "type": "progress",
  "execution_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "sequence": 1,
  "payload": {
    "type": "progress_update",
    "stage": "Translate Paragraphs",
    "overall_progress": 45.5
  }
}
```

**result 事件** — 翻译完成

```json
{
  "type": "result",
  "execution_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "sequence": 42,
  "payload": {
    "files": {
      "mono_pdf": "output/sample.zh.mono.pdf",
      "dual_pdf": "output/sample.zh.dual.pdf",
      "mono_no_watermark_pdf": "output/sample.no_watermark.zh.mono.pdf",
      "dual_no_watermark_pdf": "output/sample.no_watermark.zh.dual.pdf",
      "auto_extracted_glossary_csv": "output/sample.glossary.csv"
    },
    "metrics": {
      "time_consume_seconds": 52.7,
      "peak_memory_usage": 4936.17,
      "pdf_total_char_count": 4378,
      "pdf_total_char_token_count": 1435
    },
    "pages": "1-2"
  }
}
```

**error 事件** — 翻译失败

```json
{
  "type": "error",
  "execution_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "sequence": 10,
  "payload": {
    "code": "babeldoc_failed",
    "message": "Translation failed: ...",
    "message_for_user": "翻译过程中出现错误，请稍后重试",
    "details": {
      "exception_type": "SomeException"
    }
  }
}
```

### 事件类型汇总

| type | 说明 |
|------|------|
| `progress` | 翻译进度更新（包含 `progress_update`、`babeldoc_version` 等子类型） |
| `result` | 翻译完成，携带输出文件路径和指标 |
| `error` | 翻译失败，携带错误信息 |

---

## 4. 中止当前任务

### 请求

```bash
curl -X POST http://127.0.0.1:7860/v1/abort
```

### 响应

```
HTTP 202 Accepted
```

```json
{
  "status": "aborting"
}
```

---

## 5. 添加平铺水印

对已翻译的 PDF 叠加图片水印。

### 请求

```bash
curl -X POST http://127.0.0.1:7860/v1/pdf/watermark1 \
  -H "Content-Type: application/json" \
  -d '{
    "input_file": "output/sample.zh.mono.pdf",
    "output_file": "output/sample.zh.mono.watermarked.pdf",
    "asset_files": ["assets/watermark.png"]
  }'
```

### 响应

```json
{
  "operation_id": "watermark-op-id",
  "output_file": "output/sample.zh.mono.watermarked.pdf"
}
```

---

## 完整调用流程示例

```bash
# 1. 健康检查
curl http://127.0.0.1:7860/healthz

# 2. 提交翻译任务
RESPONSE=$(curl -s -X POST http://127.0.0.1:7860/v1/executions \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "demo-1",
    "paths": {
      "input_file": "paper.pdf",
      "output_dir": "out/"
    },
    "translation_config": {
      "lang_in": "en",
      "lang_out": "zh",
      "debug": false,
      "no_dual": false,
      "no_mono": false
    },
    "runtime_limits": {
      "qps": 4,
      "report_interval_seconds": 0.5,
      "max_pages_per_part": 10,
      "pool_max_workers": 4,
      "term_pool_max_workers": 4
    },
    "gateways": {
      "main_llm": {
        "model": "trs-m5",
        "base_url": "http://192.168.5.82:23000/api/v1",
        "api_key": "sk-your-key"
      },
      "ate_llm": {
        "model": "trs-m5",
        "base_url": "http://192.168.5.82:23000/api/v1",
        "api_key": "sk-your-key"
      },
      "layout": {
        "adapter": "rpc_doclayout8",
        "base_url": "http://layout-service:5000",
        "requires_line_extraction": true
      }
    }
  }')

EXECUTION_ID=$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin)['execution_id'])")
echo "Execution ID: $EXECUTION_ID"

# 3. 监听进度直到完成
curl -N "http://127.0.0.1:7860/v1/executions/$EXECUTION_ID/events?after_sequence=0"
```
