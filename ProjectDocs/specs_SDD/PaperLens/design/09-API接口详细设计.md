# API 接口详细设计

## 文档信息

| 项目 | 内容 |
|------|------|
| 项目名称 | PaperLens |
| 文档版本 | v1.0 |
| 创建日期 | 2026-07-13 |
| 最后更新 | 2026-07-13 |

## 1. API 设计规范

### 1.1 RESTful API 设计原则

- 基础路径: `/api/v1`
- 使用名词复数表示资源: `/papers`, `/tasks`, `/evidences`
- 使用 HTTP 方法表示操作: GET(查询)、POST(创建)、DELETE(删除)
- 使用路径参数表示具体资源: `/papers/{paper_id}`
- 使用查询参数进行过滤和分页: `/papers?status=PARSED&page=1&page_size=20`

### 1.2 统一响应格式

**成功响应:** 直接返回资源数据

**分页响应:**

```json
{
  "items": [...],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

**错误响应:**

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Error description",
    "details": null
  }
}
```

### 1.3 HTTP 状态码

| 状态码 | 说明 | 使用场景 |
|--------|------|----------|
| 200 | 成功 | 请求成功 |
| 201 | 已创建 | 资源创建成功 |
| 204 | 无内容 | 删除成功 |
| 400 | 错误请求 | 参数错误 |
| 401 | 未认证 | 未登录或 Token 失效 |
| 404 | 未找到 | 资源不存在 |
| 413 | 文件过大 | 超过大小限制 |
| 415 | 不支持的文件类型 | 文件类型错误 |
| 422 | 无法处理 | 数据验证失败 |
| 429 | 请求过多 | 频率限制 |
| 500 | 服务器错误 | 系统错误 |

### 1.4 认证方式

> 📋 **PLANNED**: Bearer/JWT 认证尚未实现。当前 `_get_user_id()` 返回 `settings.demo_user_id`，无实际鉴权。

规划 Bearer Token 认证: `Authorization: Bearer <token>`

### 1.5 通用约定

- 时间格式: ISO 8601（`2026-07-12T10:30:00Z`）
- 分页参数: `?page=1&page_size=20`
- UUID 路径参数: 无效 UUID 返回 422

## 2. 论文管理 API

### 2.1 上传论文

✅ **CURRENT**: `POST /api/v1/papers/upload`

**请求类型**: `multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | PDF 文件，最大 50MB |

> **注意**: 当前实现仅接受 `file` 字段，无可选 `title` 参数。标题由清洗后的文件名 stem 自动生成。响应状态为 `PROCESSING`（非 `UPLOADING`）。

**响应** `201`:

```json
{
  "id": "uuid",
  "title": "Attention Is All You Need",
  "filename": "attention.pdf",
  "file_size": 1048576,
  "status": "PROCESSING",
  "created_at": "2026-07-12T10:00:00Z"
}
```

### 2.2 获取论文列表

✅ **CURRENT**: `GET /api/v1/papers`

**查询参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| page | Integer | 页码，默认 1 |
| page_size | Integer | 每页数量，默认 20 |
| status | String | UPLOADING / PROCESSING / PARSED / FAILED |

**响应** `200`:

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

### 2.3 获取论文详情

✅ **CURRENT**: `GET /api/v1/papers/{paper_id}`

**响应** `200`:

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

### 2.4 删除论文

📋 **PLANNED**: `DELETE /api/v1/papers/{paper_id}`

**响应** `204`: 无内容

## 3. 论文结构 API

### 3.1 获取章节结构

✅ **CURRENT**: `GET /api/v1/papers/{paper_id}/sections`

**响应** `200`:

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

### 3.2 获取页面内容

✅ **CURRENT**: `GET /api/v1/papers/{paper_id}/pages/{page_number}`

**响应** `200`:

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

### 3.3 获取表格列表

📋 **PLANNED**: `GET /api/v1/papers/{paper_id}/tables`

**响应** `200`:

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
      "structured_data": {},
      "raw_text": "Model | EM | F1\nBERT | 86.1 | 88.7"
    }
  ]
}
```

## 4. 分析任务 API

### 4.1 创建分析任务

✅ **CURRENT**: `POST /api/v1/papers/{paper_id}/tasks`（P3.1 仅支持 REVIEW）

**请求参数**:

```json
{
  "task_type": "REVIEW",
  "options": {
    "dimensions": ["SOUNDNESS", "NOVELTY", "CLARITY"],
    "language": "zh"
  }
}
```

**响应** `201`:

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

### 4.2 获取任务列表

✅ **CURRENT**: `GET /api/v1/papers/{paper_id}/tasks`

**响应** `200`:

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

### 4.3 获取任务详情

✅ **CURRENT**: `GET /api/v1/tasks/{task_id}`

**响应** `200`:

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

### 4.4 取消任务

📋 **PLANNED**: `POST /api/v1/tasks/{task_id}/cancel`

**响应** `200`:

```json
{
  "id": "uuid",
  "status": "CANCELLED"
}
```

## 5. 审阅结果 API

### 5.1 获取审阅结果

✅ **CURRENT**: `GET /api/v1/papers/{paper_id}/reviews`

P3.1 只返回当前用户论文下、通过 AnalysisTask.user_id 再次隔离的结果。公开 findings 仅包含 VERIFIED 项；UNVERIFIED 项不展示。Evidence 候选为确定性 Top-K，语义检索和真实云模型仍为 PLANNED。

**响应** `200`:

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
        }
      ],
      "created_at": "2026-07-12T10:35:00Z"
    }
  ]
}
```

## 6. 证据 API

### 6.1 获取证据列表

✅ **CURRENT**: `GET /api/v1/papers/{paper_id}/evidences`

> **注意**: 当前实现不接受 `page_number` 或 `evidence_type` 过滤参数，返回该论文全部证据。

**查询参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| page_number | Integer | 📋 PLANNED: 按页码过滤 |
| evidence_type | String | 📋 PLANNED: TEXT / TABLE / FIGURE_CAPTION / EQUATION |

**响应** `200`:

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

### 6.2 获取证据详情

✅ **CURRENT**: `GET /api/v1/evidences/{evidence_id}`

**响应** `200`: 同证据列表中的单条数据

## 7. 实验指标 API

### 7.1 获取指标记录

📋 **PLANNED**: `GET /api/v1/papers/{paper_id}/metrics`

**查询参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| model_name | String | 按模型名过滤 |
| dataset_name | String | 按数据集过滤 |
| checkpoint_type | String | FINAL / MAX / MEAN / BEST / UNKNOWN |

**响应** `200`:

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

## 8. 实验数据文件 API

### 8.1 上传实验数据文件

📋 **PLANNED**: `POST /api/v1/papers/{paper_id}/experiment-files/upload`

**请求类型**: `multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | CSV/XLSX/XLS 文件，最大 20MB |

**响应** `201`:

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

### 8.2 获取实验数据文件列表

📋 **PLANNED**: `GET /api/v1/papers/{paper_id}/experiment-files`

**响应** `200`:

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

### 8.3 获取实验数据分析结果

📋 **PLANNED**: `GET /api/v1/experiment-files/{file_id}/result`

**响应** `200`:

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

### 8.4 删除实验数据文件

📋 **PLANNED**: `DELETE /api/v1/experiment-files/{file_id}`

**响应** `204`: 无内容

## 9. 报告导出 API

### 9.1 生成导出报告

📋 **PLANNED**: `POST /api/v1/papers/{paper_id}/exports`

**请求参数**:

```json
{
  "report_type": "MARKDOWN",
  "include_metrics": true,
  "include_experiment_analysis": true,
  "language": "zh"
}
```

**响应** `201`:

```json
{
  "id": "uuid",
  "report_type": "MARKDOWN",
  "status": "PENDING",
  "created_at": "2026-07-12T12:00:00Z"
}
```

### 9.2 获取导出状态

📋 **PLANNED**: `GET /api/v1/exports/{export_id}`

**响应** `200`:

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

### 9.3 下载导出报告

📋 **PLANNED**: `GET /api/v1/exports/{export_id}/download`

**响应** `200`: 文件流

## 10. 健康检查 API

### 10.1 服务健康检查

✅ **CURRENT**: `GET /api/v1/health`

**响应** `200`:

```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

## 11. 接口安全

### 11.1 参数验证

- 必填字段检查
- 数据类型检查（Pydantic 自动验证）
- UUID 路径参数格式校验
- 文件类型和大小校验

### 11.2 文件安全

- 文件类型验证: 仅接受 PDF / CSV / XLSX / XLS
- 文件大小限制: PDF 最大 50MB，实验数据文件最大 20MB
- 路径穿越防护
- 文件名安全处理

### 11.3 限流策略

| 接口 | 限制 |
|------|------|
| 默认 | 100 次/分钟 |
| 上传接口 | 10 次/分钟 |
| 导出接口 | 5 次/分钟 |

---

**文档版本**: v1.0
**创建日期**: 2026-07-13
**最后更新**: 2026-07-13
