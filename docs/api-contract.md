# PaperLens REST API 契约文档

## 通用约定

- 基础路径：`/api/v1`
- 认证：Bearer Token（JWT）
- 分页：`?page=1&page_size=20`
- 时间格式：ISO 8601（`2026-07-12T10:30:00Z`）
- 错误响应格式：
```json
{
  "error": {
    "code": "INVALID_FILE_TYPE",
    "message": "Only PDF files are accepted"
  }
}
```

## 1. 论文管理

### POST /papers/upload
上传论文 PDF。

**请求**：`multipart/form-data`
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | PDF 文件，最大 50MB |
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
| status | String | 过滤状态：UPLOADING / PARSED / FAILED |

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
  "created_at": "2026-07-12T10:00:00Z",
  "updated_at": "2026-07-12T10:05:00Z"
}
```

### DELETE /papers/{paper_id}
删除论文及其所有关联数据（页面、章节、分块、证据、审阅结果、指标记录）。

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
  "width": 612.0,
  "height": 792.0
}
```

## 3. 分析任务

### POST /papers/{paper_id}/tasks
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
| task_type | String | 是 | REVIEW / METRIC_EXTRACTION / EXPERIMENT_ANALYSIS |
| options | Object | 否 | 任务选项 |

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
获取任务详情（含进度）。

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
获取论文的审阅结果。

**响应** `200`：
```json
{
  "reviews": [
    {
      "id": "uuid",
      "dimension": "SOUNDNESS",
      "rating": 4,
      "summary": "The methodology is sound and well-justified.",
      "strengths": [
        {
          "content": "Clear experimental setup with proper baselines.",
          "evidence_ids": ["uuid-e1", "uuid-e2"]
        }
      ],
      "weaknesses": [
        {
          "content": "Limited dataset diversity.",
          "evidence_ids": ["uuid-e3"]
        }
      ],
      "suggestions": [
        {
          "content": "Consider evaluating on additional benchmarks.",
          "evidence_ids": ["uuid-e3"]
        }
      ],
      "overall_verdict": "WEAK_ACCEPT",
      "created_at": "2026-07-12T10:35:00Z"
    }
  ]
}
```

### GET /evidences/{evidence_id}
获取证据详情（用于前端高亮定位）。

**响应** `200`：
```json
{
  "id": "uuid",
  "content": "Our model achieves 89.1% accuracy on SQuAD...",
  "page_number": 7,
  "location_desc": "Section 4.2, Paragraph 2",
  "evidence_type": "TEXT",
  "section_id": "uuid",
  "chunk_id": "uuid"
}
```

## 5. 实验指标

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
      "table_id": "table-3",
      "row_index": 2
    }
  ]
}
```

## 6. 实验数据文件

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

## 7. 报告导出

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
  "status": "GENERATING",
  "created_at": "2026-07-12T12:00:00Z"
}
```

### GET /exports/{export_id}
获取导出状态。

**响应** `200`：
```json
{
  "id": "uuid",
  "report_type": "MARKDOWN",
  "status": "READY",
  "file_size": 20480,
  "created_at": "2026-07-12T12:00:00Z"
}
```

### GET /exports/{export_id}/download
下载导出的报告文件。

**响应** `200`：文件流（Content-Type 根据 report_type 确定）

## 8. 健康检查

### GET /health
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
| 422 | 请求体验证失败 |
| 429 | 请求频率过高 |
| 500 | 服务器内部错误 |