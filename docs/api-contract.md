# PaperLens REST API 契约文档

## 通用约定

- 基础路径：`/api/v1`
- 认证：当前使用配置项 `DEMO_USER_ID` 做数据隔离；Bearer Token（JWT）为后续计划
- 分页：`?page=1&page_size=20`
- 时间格式：ISO 8601（`2026-07-12T10:30:00Z`）
- 错误响应格式：
```json
{
  "error": {
    "code": "INVALID_FILE_TYPE",
    "message": "Only PDF files are accepted",
    "details": null
  }
}
```

`details` 字段：`null` 或数组。当存在多个验证错误时返回数组：
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {"field": "task_type", "message": "Invalid task type"},
      {"field": "options.language", "message": "Unsupported language"}
    ]
  }
}
```

- UUID 路径参数：当 `{paper_id}`、`{task_id}`、`{evidence_id}` 等为无效 UUID 格式时，返回 `422 Unprocessable Entity`

## 1. 论文管理

### POST /papers/upload
上传论文 PDF（multipart 流式上传，最大 50MB）。

**请求**：`multipart/form-data`
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | PDF 文件，最大 50MB，仅支持包含可提取文本的 PDF |
| title | String | 否 | 论文标题（默认从 PDF 提取） |

**响应** `201`：
```json
{
  "id": "uuid",
  "title": "Attention Is All You Need",
  "filename": "attention.pdf",
  "file_size": 1048576,
  "status": "UPLOADING",
  "created_at": "2026-07-12T10:00:00Z"
}
```

### GET /papers
获取当前用户的论文列表。

**查询参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| page | Integer | 页码，默认 1 |
| page_size | Integer | 每页数量，默认 20 |
| status | String | 过滤状态：UPLOADING / PROCESSING / PARSED / FAILED |

**响应** `200`：
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Attention Is All You Need",
      "filename": "attention.pdf",
      "page_count": 12,
      "status": "PARSED",
      "created_at": "2026-07-12T10:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

### GET /papers/{paper_id}
获取论文详情。

**响应** `200`：
```json
{
  "id": "uuid",
  "title": "Attention Is All You Need",
  "filename": "attention.pdf",
  "file_size": 1048576,
  "page_count": 12,
  "status": "PARSED",
  "error_message": null,
  "created_at": "2026-07-12T10:00:00Z",
  "updated_at": "2026-07-12T10:05:00Z"
}
```

### DELETE /papers/{paper_id}
删除论文及其所有关联数据（页面、章节、分块、表格、证据、审阅结果、指标记录）。

**响应** `204`：无内容

## 2. 论文结构

### GET /papers/{paper_id}/sections
获取论文章节结构。

**响应** `200`：
```json
{
  "sections": [
    {
      "id": "uuid",
      "section_type": "ABSTRACT",
      "title": "Abstract",
      "level": 1,
      "sequence": 1,
      "start_page": 1,
      "end_page": 1,
      "text_content": "..."
    }
  ]
}
```

### GET /papers/{paper_id}/pages/{page_number}
获取指定页面内容。

**响应** `200`：
```json
{
  "id": "uuid",
  "page_number": 1,
  "text_content": "...",
  "normalized_text_content": "...",
  "width": 612.0,
  "height": 792.0
}
```

### GET /papers/{paper_id}/tables
获取论文表格列表。

**响应** `200`：
```json
{
  "tables": [
    {
      "id": "uuid",
      "page_number": 5,
      "table_index": 1,
      "caption": "Table 1: Main results on SQuAD 2.0",
      "bbox_x0": 72.0,
      "bbox_y0": 200.0,
      "bbox_x1": 540.0,
      "bbox_y1": 450.0,
      "structured_data": { ... },
      "raw_text": "Model | EM | F1\nBERT | 86.1 | 88.7"
    }
  ]
}
```

## 3. 分析任务

> P3.1 CURRENT：当前仅支持 `task_type=REVIEW`，使用 FastAPI BackgroundTasks 和 MockLLMClient。`METRIC_EXTRACTION`、`EXPERIMENT_ANALYSIS` 与任务取消仍为规划功能。

### POST /papers/{paper_id}/tasks
✅ **CURRENT**

创建分析任务。

**请求**：
```json
{
  "task_type": "REVIEW",
  "options": {
    "dimensions": ["SOUNDNESS", "NOVELTY", "CLARITY"],
    "language": "zh"
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_type | String | 是 | 当前仅支持 REVIEW；其他类型返回 `TASK_TYPE_NOT_SUPPORTED` |
| options | Object | 否 | 默认 dimensions=[OVERALL]、language=zh |

**响应** `201`：
```json
{
  "id": "uuid",
  "paper_id": "uuid",
  "task_type": "REVIEW",
  "status": "PENDING",
  "progress": 0,
  "created_at": "2026-07-12T10:30:00Z"
}
```

### GET /papers/{paper_id}/tasks
✅ **CURRENT**

获取论文的分析任务列表。

**响应** `200`：
```json
{
  "items": [
    {
      "id": "uuid",
      "task_type": "REVIEW",
      "status": "SUCCEEDED",
      "progress": 100,
      "started_at": "2026-07-12T10:30:00Z",
      "completed_at": "2026-07-12T10:35:00Z"
    }
  ]
}
```

### GET /tasks/{task_id}
✅ **CURRENT**

获取任务详情（含进度，用于 HTTP 轮询）。

**响应** `200`：
```json
{
  "id": "uuid",
  "paper_id": "uuid",
  "task_type": "REVIEW",
  "status": "RUNNING",
  "progress": 65,
  "error_message": null,
  "started_at": "2026-07-12T10:30:00Z",
  "completed_at": null,
  "created_at": "2026-07-12T10:30:00Z"
}
```

### POST /tasks/{task_id}/cancel
📋 **PLANNED**

取消正在运行的任务。

**响应** `200`：
```json
{
  "id": "uuid",
  "status": "CANCELLED"
}
```

## 4. 审阅结果

### GET /papers/{paper_id}/reviews
✅ **CURRENT**

获取论文的审阅结果。一个任务可产生多个 ReviewResult（按维度），每个 ReviewResult 包含多个 ReviewFinding。

当前公开响应只返回 `VERIFIED` Finding；引用为空、未知 alias、原始 UUID 或混合非法引用的 Finding 保存为 `UNVERIFIED` 且不展示。P3.1 使用同论文 Evidence 的确定性 Top-K 候选，FAISS/Embedding 语义检索仍为规划。

**响应** `200`：
```json
{
  "reviews": [
    {
      "id": "uuid",
      "task_id": "uuid",
      "dimension": "SOUNDNESS",
      "rating": 4,
      "summary": "The methodology is sound and well-justified.",
      "overall_verdict": null,
      "findings": [
        {
          "id": "uuid",
          "finding_type": "STRENGTH",
          "content": "Clear experimental setup with proper baselines.",
          "confidence": 0.92,
          "verification_status": "VERIFIED",
          "sequence": 1,
          "evidence_ids": ["uuid-e1", "uuid-e2"]
        },
        {
          "id": "uuid",
          "finding_type": "WEAKNESS",
          "content": "Limited dataset diversity.",
          "confidence": 0.85,
          "verification_status": "VERIFIED",
          "sequence": 2,
          "evidence_ids": ["uuid-e3"]
        },
        {
          "id": "uuid",
          "finding_type": "SUGGESTION",
          "content": "Consider evaluating on additional benchmarks.",
          "confidence": 0.78,
          "verification_status": "VERIFIED",
          "sequence": 3,
          "evidence_ids": ["uuid-e3"]
        }
      ],
      "created_at": "2026-07-12T10:35:00Z"
    }
  ]
}
```

## 5. 证据

### GET /papers/{paper_id}/evidences
获取论文的证据列表。Evidence 为页内定位（page-local），基于 PyMuPDF block 提取。

**查询参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| page_number | Integer | 按页码过滤 |
| evidence_type | String | 按类型过滤：TEXT / TABLE / FIGURE_CAPTION / EQUATION |

> 当前实现暂不接受上述过滤参数，返回论文全部 Evidence；过滤功能为后续计划。

**响应** `200`：
```json
{
  "evidences": [
    {
      "id": "uuid",
      "quoted_text": "Our model achieves 89.1% accuracy on SQuAD...",
      "page_number": 7,
      "bbox_x0": 72.0,
      "bbox_y0": 350.0,
      "bbox_x1": 540.0,
      "bbox_y1": 380.0,
      "char_start": 1420,
      "char_end": 1498,
      "evidence_type": "TEXT",
      "section_id": "uuid",
      "chunk_id": "uuid"
    }
  ]
}
```

### GET /evidences/{evidence_id}
获取证据详情（含页面内定位信息，用于前端高亮跳转）。

**响应** `200`：
```json
{
  "id": "uuid",
  "quoted_text": "Our model achieves 89.1% accuracy on SQuAD...",
  "page_number": 7,
  "bbox_x0": 72.0,
  "bbox_y0": 350.0,
  "bbox_x1": 540.0,
  "bbox_y1": 380.0,
  "char_start": 1420,
  "char_end": 1498,
  "evidence_type": "TEXT",
  "section_id": "uuid",
  "chunk_id": "uuid"
}
```

## 6. 实验指标

### GET /papers/{paper_id}/metrics
获取论文的实验指标记录。

**查询参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| model_name | String | 按模型名过滤 |
| dataset_name | String | 按数据集过滤 |
| checkpoint_type | String | 按口径过滤：FINAL / MAX / MEAN / BEST / UNKNOWN |

**响应** `200`：
```json
{
  "metrics": [
    {
      "id": "uuid",
      "model_name": "BERT-base",
      "dataset_name": "SQuAD 2.0",
      "metric_name": "F1",
      "metric_value": 83.1,
      "checkpoint_type": "BEST",
      "checkpoint_source": "TABLE_HEADER",
      "evidence_id": "uuid",
      "raw_text": "BERT-base 83.1 79.0",
      "table_id": "uuid",
      "row_index": 2
    }
  ]
}
```

## 7. 实验数据文件

### POST /papers/{paper_id}/experiment-files/upload
上传实验数据文件（CSV/Excel）。

**请求**：`multipart/form-data`
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | CSV/XLSX/XLS 文件，最大 20MB |

**响应** `201`：
```json
{
  "id": "uuid",
  "filename": "experiment_results.csv",
  "file_type": "CSV",
  "row_count": 50,
  "column_count": 8,
  "columns_info": {
    "model": "string",
    "accuracy": "float",
    "f1_score": "float"
  }
}
```

### GET /papers/{paper_id}/experiment-files
获取论文关联的实验数据文件列表。

**响应** `200`：
```json
{
  "items": [
    {
      "id": "uuid",
      "filename": "experiment_results.csv",
      "file_type": "CSV",
      "row_count": 50,
      "created_at": "2026-07-12T11:00:00Z"
    }
  ]
}
```

### GET /experiment-files/{file_id}/result
获取实验数据分析结果。

**响应** `200`：
```json
{
  "id": "uuid",
  "summary_stats": {
    "columns": {
      "accuracy": {
        "count": 10,
        "mean": 0.852,
        "std": 0.023,
        "min": 0.810,
        "max": 0.891,
        "median": 0.855
      }
    }
  },
  "metric_comparisons": [
    {
      "metric_name": "accuracy",
      "dataset": "SQuAD",
      "paper_value": 0.891,
      "experiment_value": 0.855,
      "diff": -0.036,
      "checkpoint_type": "MAX",
      "status": "MISMATCH"
    }
  ]
}
```

### DELETE /experiment-files/{file_id}
删除实验数据文件及其分析结果。

**响应** `204`：无内容

## 8. 报告导出

### POST /papers/{paper_id}/exports
生成导出报告。

**请求**：
```json
{
  "report_type": "MARKDOWN",
  "include_metrics": true,
  "include_experiment_analysis": true,
  "language": "zh"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| report_type | String | 是 | MARKDOWN / PDF / DOCX |
| include_metrics | Boolean | 否 | 是否包含指标记录，默认 true |
| include_experiment_analysis | Boolean | 否 | 是否包含实验分析，默认 true |
| language | String | 否 | 报告语言：zh / en，默认 zh |

**响应** `201`：
```json
{
  "id": "uuid",
  "report_type": "MARKDOWN",
  "status": "PENDING",
  "created_at": "2026-07-12T12:00:00Z"
}
```

### GET /exports/{export_id}
获取导出状态（用于 HTTP 轮询）。

**响应** `200`：
```json
{
  "id": "uuid",
  "report_type": "MARKDOWN",
  "status": "READY",
  "file_size": 20480,
  "error_message": null,
  "created_at": "2026-07-12T12:00:00Z",
  "completed_at": "2026-07-12T12:01:00Z"
}
```

### GET /exports/{export_id}/download
下载导出的报告文件。

**响应** `200`：文件流（Content-Type 根据 report_type 确定）

## 9. 健康检查

### GET /api/v1/health
服务健康检查。

**响应** `200`：
```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

## HTTP 状态码汇总

| 状态码 | 含义 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 204 | 删除成功（无内容） |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 413 | 文件过大 |
| 415 | 不支持的文件类型 |
| 422 | 请求体验证失败（含无效 UUID 路径参数） |
| 429 | 请求频率过高 |
| 500 | 服务器内部错误 |
