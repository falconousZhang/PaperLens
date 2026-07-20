# API接口设计

## 文档信息

- **项目名称**: PaperLens
- **文档版本**: v1.0
- **创建日期**: 2026-07-13
- **最后更新**: 2026-07-13

> **说明**: FastAPI 会自动生成 OpenAPI 文档，本文档定义核心接口规范和设计原则。当前 Swagger UI 为 `/api/docs`，OpenAPI Schema 为 `/api/openapi.json`，ReDoc 保持 FastAPI 默认地址 `/redoc`。

## 1. API设计规范

### 1.1 RESTful API设计原则

- 基础路径：`/api/v1`
- 使用名词复数表示资源：`/papers`, `/tasks`, `/evidences`
- 使用HTTP方法表示操作：GET(查询)、POST(创建)、DELETE(删除)
- 使用路径参数表示具体资源：`/papers/{paper_id}`
- 使用查询参数进行过滤和分页：`/papers?status=PARSED&page=1&page_size=20`

### 1.2 统一响应格式

#### 成功响应

直接返回资源数据，不包裹额外层级：

```json
{
  "id": "uuid",
  "title": "Attention Is All You Need",
  "status": "PARSED"
}
```

#### 分页响应

```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Attention Is All You Need",
      "status": "PARSED",
      "created_at": "2026-07-12T10:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

#### 错误响应

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

### 1.3 HTTP状态码

| 状态码 | 说明 | 使用场景 |
|--------|------|----------|
| 200 | 成功 | 请求成功 |
| 201 | 已创建 | 资源创建成功 |
| 204 | 无内容 | 删除成功 |
| 400 | 错误请求 | 参数错误 |
| 401 | 未认证 | 未登录或Token失效 |
| 403 | 禁止访问 | 无权限 |
| 404 | 未找到 | 资源不存在 |
| 413 | 文件过大 | 超过大小限制 |
| 415 | 不支持的文件类型 | 文件类型错误 |
| 422 | 无法处理 | 数据验证失败（含无效 UUID 路径参数） |
| 429 | 请求过多 | 频率限制 |
| 500 | 服务器错误 | 系统错误 |

### 1.4 认证方式

> ✅ **P3.5 CURRENT**：所有现有论文、Evidence、任务和审阅路由使用统一 Bearer JWT + AuthSession 鉴权；user_id 只来自认证依赖。

当前使用 Bearer Token 认证：
```
Authorization: Bearer <token>
```

### 1.5 通用约定

- 时间格式：ISO 8601（`2026-07-12T10:30:00Z`）
- 分页参数：`?page=1&page_size=20`
- UUID 路径参数：无效 UUID 格式返回 `422 Unprocessable Entity`

## 2. 论文管理API

### 2.1 上传论文

✅ **CURRENT**: `POST /api/v1/papers/upload`

**请求类型**：`multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | PDF 文件，最大 50MB，仅支持包含可提取文本的 PDF |

> **注意**: 当前实现仅接受 `file` 字段，无可选 `title` 参数。标题由清洗后的文件名 stem 自动生成。响应状态为 `PROCESSING`（非 `UPLOADING`）。

**响应** `201`：
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

### 2.3 获取论文详情

✅ **CURRENT**: `GET /api/v1/papers/{paper_id}`

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

### 2.4 删除论文

📋 **PLANNED**: `DELETE /api/v1/papers/{paper_id}`

删除论文及其所有关联数据（页面、章节、分块、表格、证据、审阅结果、指标记录）。

**响应** `204`：无内容

## 3. 论文结构API

### 3.1 获取章节结构

✅ **CURRENT**: `GET /api/v1/papers/{paper_id}/sections`

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

### 3.2 获取页面内容

✅ **CURRENT**: `GET /api/v1/papers/{paper_id}/pages/{page_number}`

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

### 3.3 获取表格列表

📋 **PLANNED**: `GET /api/v1/papers/{paper_id}/tables`

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

## 4. 分析任务API

### 4.1 创建分析任务

✅ **CURRENT**: `POST /api/v1/papers/{paper_id}/tasks`（P3.1 仅支持 REVIEW）

**请求参数**：
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
| task_type | String | 是 | 当前仅支持 REVIEW；其他类型返回 422 / TASK_TYPE_NOT_SUPPORTED |
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

### 4.2 获取任务列表

✅ **CURRENT**: `GET /api/v1/papers/{paper_id}/tasks`

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

### 4.3 获取任务详情

✅ **CURRENT**: `GET /api/v1/tasks/{task_id}`

用于 HTTP 轮询任务进度。

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

### 4.4 取消任务

📋 **PLANNED**: `POST /api/v1/tasks/{task_id}/cancel`

**响应** `200`：
```json
{
  "id": "uuid",
  "status": "CANCELLED"
}
```

## 5. 审阅结果API

### 5.1 获取审阅结果

✅ **CURRENT**: `GET /api/v1/papers/{paper_id}/reviews`

一个任务可产生多个 ReviewResult（按请求维度稳定持久化），每个 ReviewResult 包含多个 ReviewFinding。公开响应仅返回 `VERIFIED` Finding；`UNVERIFIED` Finding 保留在数据库用于审计但不展示。P3.1 使用确定性 Top-K Evidence 候选，FAISS/Embedding 仍为 PLANNED。

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

## 6. 证据API

### 6.1 获取证据列表

✅ **CURRENT**: `GET /api/v1/papers/{paper_id}/evidences`

Evidence 为页内定位（page-local），基于 PyMuPDF block 提取。

> **注意**: 当前实现不接受 `page_number` 或 `evidence_type` 过滤参数，返回该论文全部证据。

**查询参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| page_number | Integer | 📋 PLANNED: 按页码过滤 |
| evidence_type | String | 📋 PLANNED: 按类型过滤：TEXT / TABLE / FIGURE_CAPTION / EQUATION |

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

### 6.2 获取证据详情

✅ **CURRENT**: `GET /api/v1/evidences/{evidence_id}`

含页面内定位信息，用于前端高亮跳转。

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

## 7. 实验指标API

### 7.1 获取指标记录

✅ **CURRENT**: `GET /api/v1/papers/{paper_id}/metrics`

**查询参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| task_id | UUID | 按任务过滤 |
| metric_name | String | 按规范指标名精确过滤 |
| dataset_name | String | 按数据集过滤 |
| checkpoint_type | String | FINAL / MAX / MEAN / BEST / LAST / UNKNOWN |
| page / page_size | Integer | 分页；page_size 最大 100 |

**响应** `200`：
```json
{
  "items": [
    {
      "id": "uuid",
      "paper_id": "uuid",
      "task_id": "uuid",
      "model_name": "BERT-base",
      "dataset_name": "SQuAD 2.0",
      "metric_name": "F1",
      "metric_value": 0.831,
      "checkpoint_type": "BEST",
      "checkpoint_source": "caption",
      "evidence_id": null,
      "raw_text": "F1: 83.1%",
      "table_id": "uuid",
      "row_index": 2,
      "created_at": "2026-07-14T00:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

✅ `GET /api/v1/metrics/{metric_id}` 返回单条详情。两个接口都要求 Bearer 并执行真实用户隔离；跨用户详情按 404 处理。指标任务通过现有 `POST /papers/{paper_id}/tasks` 创建，`task_type=METRIC_EXTRACTION` 且 options 只能省略或为空对象。

P4.2 前端只发送 `task_id`、`metric_name`、`dataset_name`、`checkpoint_type`、`page` 和 `page_size`。页面必须先选择一个成功指标任务并始终携带 `task_id`；空筛选值不发送，`page_size` 在前端限制为 1～100，后端继续执行最终校验。

## 8. 实验数据文件API

P5.1 当前只提供安全上传、分页列表和结构详情。公开 schema 为严格 version=1 `columns_info`，不返回完整文件哈希、storage_key、样本值或数据行；result、DELETE、下载和预览均仍规划。

### 8.1 上传实验数据文件

✅ **CURRENT (P5.1)**: `POST /api/v1/papers/{paper_id}/experiment-files/upload`

**请求类型**：`multipart/form-data`

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

### 8.2 获取实验数据文件列表

✅ **CURRENT (P5.1)**: `GET /api/v1/papers/{paper_id}/experiment-files`

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

### 8.3 获取实验文件结构详情

✅ **CURRENT (P5.1)**: `GET /api/v1/experiment-files/{file_id}`

返回 id、paper_id、filename、file_type、file_size、row_count、column_count、严格 columns_info 和 created_at；不存在和跨用户统一 404。

### 8.4 创建实验数据统计任务

✅ **CURRENT (P5.2)**: `POST /api/v1/experiment-files/{file_id}/analysis`

新建任务返回 201；已有活动任务或结果返回 200，并通过 `duplicate` 标识幂等命中。规模超限返回 413 `ANALYSIS_TOO_LARGE`，不存在、跨用户及 ADMIN 访问他人资源统一 404。

### 8.5 获取实验数据统计结果

✅ **CURRENT (P5.2)**: `GET /api/v1/experiment-files/{file_id}/result`

**响应** `200`：
```json
{
  "id": "uuid",
  "file_id": "uuid",
  "task_id": "uuid",
  "summary_stats": {
    "version": 1,
    "row_count": 10,
    "column_count": 1,
    "columns": [
      {
        "name": "accuracy",
        "dtype": "float",
        "count": 10,
        "null_count": 0,
        "stats": {
        "mean": 0.852,
        "stddev": 0.023,
        "min": 0.810,
        "max": 0.891,
        "median": 0.855
        }
      }
    ]
  },
  "created_at": "2026-07-14T00:00:00Z"
}
```

结果未就绪返回 404；公开响应不包含 storage key、文件哈希、原始行、`column_analysis` 或 `metric_comparisons`。

### 8.5 删除实验数据文件

📋 **PLANNED**: `DELETE /api/v1/experiment-files/{file_id}`

删除实验数据文件及其分析结果。

**响应** `204`：无内容

## 9. 报告导出API

### 9.1 生成导出报告

✅ **CURRENT (P6.1)**: `POST /api/v1/papers/{paper_id}/exports`

**请求参数**：
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

### 9.2 获取导出状态

✅ **CURRENT (P6.1)**: `GET /api/v1/exports/{export_id}`

用于 HTTP 轮询导出进度。

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

### 9.3 下载导出报告

✅ **CURRENT (P6.1)**: `GET /api/v1/exports/{export_id}/download`

**响应** `200`：文件流（Content-Type 根据 report_type 确定）

## 10. 健康检查API

### 10.1 服务健康检查

✅ **CURRENT**: `GET /api/v1/health`

**响应** `200`：
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
- UUID 路径参数格式校验（无效 UUID 返回 422）
- 文件类型和大小校验

### 11.2 文件安全

- 文件类型验证：仅接受 PDF / CSV / XLSX / XLS
- 文件大小限制：PDF 最大 50MB，实验数据文件最大 20MB
- 路径穿越防护
- 文件名安全处理

### 11.3 限流策略

- 默认：100次/分钟
- 上传接口：10次/分钟
- 导出接口：5次/分钟

**限流响应**：
```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Too many requests",
    "details": null
  }
}
```

## 12. 接口文档

### 12.1 OpenAPI文档

FastAPI 自动生成以下文档：
- Swagger UI: `/api/docs`
- ReDoc: `/api/redoc`
- OpenAPI JSON: `/api/openapi.json`

### 12.2 接口版本管理

**版本策略**：
- URL路径版本：`/api/v1/`
- 向后兼容原则
- 废弃接口提前通知

---

## P4.3 接口影响

本阶段不新增或修改公开 HTTP API。新增的 `maas-config-check` 与 `maas-smoke --confirm-billable` 是容器内运维 CLI；现有 `/api/v1` 鉴权、论文、审阅和指标契约保持不变。默认 mock 模式下，health、认证与非 LLM 业务不依赖 MaaS 配置。

## P5.2 接口影响

新增 POST analysis 与 GET result 两条公开路由，`/api/v1` method+path 总数由 27 增至 29。既有任务详情用于轮询 EXPERIMENT_ANALYSIS；原论文任务列表自然包含该任务类型。

## P5.3a 接口影响

新增 `POST /api/v1/experiment-files/{file_id}/comparisons`，请求体只允许严格 UUID4 `metric_task_id`。首次成功 201，同源幂等 200，异源为 409；公开响应固定为 `file_id/experiment_result_id/metric_task_id/comparisons/duplicate`。

比较项的 `statistic` 只允许 `MEAN|MAX|null`，`status` 只允许 `MATCH|MISMATCH|UNVERIFIABLE`；diff 固定为实验值减论文值。`GET result` 在未交叉验证时返回 `metric_comparisons=null`，完成后返回同一严格数组。无指标返回 `NO_METRICS` 409，跨 USER/ADMIN 统一 404。

## P5.3b 接口影响

本阶段未新增公开 HTTP 路由，`/api/v1` method+path 仍为 30。前端完整使用既有 8 个调用：Paper、Task 列表/详情，以及实验文件上传/分页列表/可信详情、analysis、result、comparisons。

浏览器上传使用 FormData 且不手写 multipart Content-Type；列表 page/page_size 在客户端约束为合法整数。页面对 file detail、analysis task、result 和 comparison 响应执行 paper/file/task 上下文校验，未知服务端错误不直接展示。

## P6.1 接口影响

新增 3 条公开路由：`POST /api/v1/papers/{paper_id}/exports`、`GET /api/v1/exports/{export_id}`、`GET /api/v1/exports/{export_id}/download`。`/api/v1` method+path 总数由 30 增至 33。

创建导出请求体含 `report_type`（P6.1 仅 MARKDOWN）、`language`（zh/en，默认 zh）、`include_metrics`（默认 true）和 `include_experiment_analysis`（默认 true），并拒绝 extra 字段。相同用户/论文/选项/来源/内容的活跃或 READY 导出幂等返回 200；新来源返回 201；FAILED 可重试。非 PARSED、无合法审阅或来源图异常为固定 409，跨用户统一 404。公开响应不含 source_snapshot/source_hash/content_hash/storage_key；下载仅 READY 且回读 size/hash 一致时返回 attachment，其余固定 409/404，并带 nosniff 与 private,no-store。

## P6.2 接口影响

新增 1 条公开路由：`GET /api/v1/papers/{paper_id}/exports`（导出历史分页列表）。`/api/v1` method+path 总数由 33 增至 34。

`report_type` 扩展为 MARKDOWN|PDF|DOCX 三格式。三种格式在相同 user/paper/language/include/source 下各自独立 ExportReport；同格式同源同 bytes 幂等 200，不同来源 201，FAILED 可重试。列表 API 仅论文所有者可见，严格分页 1～100，按 created_at DESC/id DESC。下载按 report_type 返回对应 MIME（Markdown text/markdown、PDF application/pdf、DOCX application/vnd.openxmlformats-officedocument.wordprocessingml.document）；安全文件名只由 report id 和服务端固定扩展组成。012 迁移调整 ck_export_p61_source 约束使 source_snapshot 非空的 MARKDOWN/PDF/DOCX 均合法。

## 12. P7.1 阅读学习 API（COMPLETED）

| 方法与路径 | 用途 |
|------------|------|
| POST `/api/v1/papers/{paper_id}/learning-explanations` | 创建或复用章节/页面/Evidence 的总结、解释或翻译 |
| GET `/api/v1/learning-explanations/{explanation_id}` | 查询状态、结果、学习要点、术语和有序 Evidence 引用 |
| GET `/api/v1/papers/{paper_id}/learning-explanations?page=1&page_size=20` | 查询当前论文的个人学习解释历史 |

实现后的公开路由总数为 37。POST 新建为 201、幂等复用为 200+duplicate；详情仅在成功时公开答案、术语对象和安全 Citation 定位字段；列表不返回大正文。参数错误 422、论文/来源状态冲突 409、资源不存在或越权 404。

POST 请求仅接受 `mode`、`scope_type`、对应的 section_id/page_number/evidence_id 和 `output_language`，`extra=forbid`。客户端不得提交正文、Evidence 文本、prompt、模型名或 user_id。仅论文所有者且论文为 PARSED 时可创建；ADMIN 在普通学习 API 中不绕过所有权。

新建返回 201；活动或成功的同请求复用返回 200 并标记 duplicate。FAILED 可重新创建。全部详情和列表响应不公开 request_hash、source hash、原始 prompt/响应、内部错误或任何模型密钥。预计公开 `/api/v1` method+path 34 → 37。

**文档版本**：v1.8
**创建日期**：2026-07-13
**最后更新**：2026-07-15

## 13. P7.2 论文问答 API

| Method + Path | 契约 |
|---|---|
| POST `/api/v1/papers/{paper_id}/qa-conversations` | 严格空对象创建当前用户当前 PARSED 论文的空会话，201 |
| GET `/api/v1/papers/{paper_id}/qa-conversations?page&page_size` | 20 条分页，返回 turn_count、last_question_preview、last_status，不批量返回答案 |
| GET `/api/v1/qa-conversations/{conversation_id}?page&page_size` | owner-only，按 sequence ASC 分页返回 turns 和 total/page/page_size |
| POST `/api/v1/qa-conversations/{conversation_id}/turns` | 仅 question/output_language/client_request_id；新建 201，幂等复用 200，活动冲突 409 |
| GET `/api/v1/qa-turns/{turn_id}` | owner-only 轮询单轮安全详情 |

全部路径为 UUID4，page>=1，page_size 1～100。401 表示未认证，404 统一不存在/越权，409 表示未解析、无 Evidence 或已有活动轮次，422 表示非法字段/枚举/问题。响应不公开 client_request_id、context_hash、prompt、向量、模型参数、内部异常或 secret。路由基线预计 37→42，以最终统计为准。

## 14. P7.3 个人学习沉淀与论文库 API

新增 17 条公开路由，路由基线预计 42→59：

### 论文库（3 条）

| Method + Path | 契约 |
|---|---|
| GET `/api/v1/library/papers?page&page_size&reading_status&favorite&collection_name&q` | LEFT JOIN 论文库条目的分页列表；支持阅读状态、收藏、集合名和标题搜索过滤 |
| PATCH `/api/v1/papers/{paper_id}/library-entry` | 创建或更新论文库条目（reading_status、favorite、collection_name）；201 新建 / 200 更新 |
| PATCH `/api/v1/papers/{paper_id}/reading-progress` | 更新阅读进度（last_page、furthest_page、last_read_at）；自动推进 reading_status |

### 高亮（3 条）

| Method + Path | 契约 |
|---|---|
| POST `/api/v1/papers/{paper_id}/highlights` | 创建高亮；body 含 page_number、char_start、char_end、color；服务端派生 quoted_text 和 source_hash；重复返回既有对象、200 和 duplicate=true |
| GET `/api/v1/papers/{paper_id}/highlights?page_number` | 查询高亮列表；可选 page_number 过滤 |
| DELETE `/api/v1/highlights/{highlight_id}` | 删除高亮；被笔记或知识卡引用时返回 409 NOTE_OR_CARD_REFERENCES |

### 书签（3 条）

| Method + Path | 契约 |
|---|---|
| POST `/api/v1/papers/{paper_id}/bookmarks` | 创建书签；body 含 page_number、label；重复页码返回既有对象、200 和 duplicate=true |
| GET `/api/v1/papers/{paper_id}/bookmarks?page&page_size` | 查询书签分页列表 |
| DELETE `/api/v1/bookmarks/{bookmark_id}` | 删除书签 |

### 笔记（4 条）

| Method + Path | 契约 |
|---|---|
| POST `/api/v1/papers/{paper_id}/notes` | 创建笔记；anchor_type=PAGE 时只需 page_number，anchor_type=HIGHLIGHT 时需 highlight_id；互斥校验 422 |
| GET `/api/v1/papers/{paper_id}/notes?page_number&anchor_type` | 查询笔记列表；可选过滤 |
| PATCH `/api/v1/notes/{note_id}` | 更新笔记内容 |
| DELETE `/api/v1/notes/{note_id}` | 删除笔记 |

### 知识卡（4 条）

| Method + Path | 契约 |
|---|---|
| POST `/api/v1/papers/{paper_id}/knowledge-cards` | 创建知识卡；source_note_id / source_highlight_id 二选一；互斥校验 422 |
| GET `/api/v1/papers/{paper_id}/knowledge-cards?mastery_status&archived` | 查询知识卡列表；可选过滤 |
| PATCH `/api/v1/knowledge-cards/{card_id}` | 更新知识卡（front、back、mastery_status、archived）；last_reviewed_at 只在掌握状态真实变化时由服务端更新 |
| DELETE `/api/v1/knowledge-cards/{card_id}` | 删除知识卡 |

全部路由要求 Bearer 认证，资源按 user_id 严格隔离，跨用户统一 404。所有服务均为确定性 Python 代码，不调用 LLM/Embedding，不访问网络。

最终验收为 59 条 `/api/v1` method+path，其中 P7.3 恰为 17 条。所有列表均采用 page/page_size 稳定分页；公开响应不包含 user_id，PATCH 空对象、非法 null、控制字符和非法枚举统一 422。

## 15. P8.1 管理员 API

新增 8 条公开路由，路由基线预计 59→67，全部要求 ADMIN 角色：

| Method + Path | 契约 |
|---|---|
| GET `/api/v1/admin/dashboard` | 聚合计数：用户数、论文数、任务数、审阅数、报告数、最近审计条目 |
| GET `/api/v1/admin/users?page&page_size&role&status&q` | 用户列表，支持角色/状态/搜索过滤，分页 |
| GET `/api/v1/admin/users/{user_id}` | 用户详情，含角色、状态、创建时间、最近活动 |
| PATCH `/api/v1/admin/users/{user_id}` | 变更用户角色或状态；body 含 role/status/reason；reason 必填 8～500 字符；并发降级/禁用导致零 ACTIVE ADMIN 返回 409；同值 no-op 返回 200；审计日志 + 会话撤销在同一事务 |
| GET `/api/v1/admin/papers?page&page_size&status&user_id&q` | 跨用户只读论文列表，列投影仅返回管理员可见字段 |
| GET `/api/v1/admin/tasks?page&page_size&status&task_type&user_id` | 跨用户只读任务列表，列投影仅返回管理员可见字段 |
| GET `/api/v1/admin/exports?page&page_size&status&report_type&user_id` | 跨用户只读报告列表，列投影仅返回管理员可见字段 |
| GET `/api/v1/admin/audit-logs?page&page_size&action&actor_user_id&resource_id` | 审计日志分页列表，按 created_at DESC/id DESC 排序 |

全部路由 401 表示未认证，403 表示非 ADMIN，422 表示非法字段/枚举/UUID。PATCH 用户时 reason 必填且不含控制字符；before_state/after_state 仅含 role/status 键。跨用户只读查询不返回 storage_key、file_hash、source_snapshot、content_hash 等内部字段。

## 16. P8.2 恢复与一致性接口影响

P8.2 不新增公开 HTTP API。恢复由 RecoveryService 在 FastAPI lifespan 内部执行，不暴露管理端点。

恢复行为通过环境变量配置：
- `PAPERLENS_RECOVERY_ENABLED`：是否启用启动时恢复（默认 true）
- `PAPERLENS_RECOVERY_STALE_SECONDS`：陈旧判定阈值秒数（默认 300）
- `PAPERLENS_RECOVERY_BATCH_SIZE`：单类扫描行数上限（默认 50）

P8.2 不新增路由。既有 TaskDetail / TaskListItem 响应增加可空 `experiment_file_id`，仅在 EXPERIMENT_ANALYSIS 任务中有值，用于页面刷新后恢复文件上下文；不公开 storage_key、文件哈希或内容。前端共享 `usePolling` 不引入额外 API 类型。

P8.2 状态：已完成并经码道独立收口；无新增公开端点。

## 17. P8.3 性能、可靠性、限流与可观测性接口影响

新增 2 条公开路由，路由基线 67→69，均不要求认证且不计入限流：

| Method + Path | 契约 |
|---|---|
| GET `/api/v1/health/live` | 存活检查：进程存活返回 200 `{"status": "alive", "version": "..."}` |
| GET `/api/v1/health/ready` | 就绪检查：短事务 `SELECT 1` 成功返回 200 `{"status": "ready", "checks": {"database": "ok"}}`，失败返回 503 `{"status": "not_ready", "checks": {"database": "error"}}` |

既有 GET `/api/v1/health` 保持不变。三个 health 端点完全豁免限流。

限流超限统一返回 429 JSON envelope：`{"error": {"code": "RATE_LIMITED", "message": "请求过于频繁，请稍后重试", "details": null}}`，并设置整数 `Retry-After` 和 `X-Request-ID` 响应头。

所有 API 响应（含错误响应）均返回 `X-Request-ID` 响应头。

所有请求只接受规范小写 UUID4 `X-Request-ID`，其他输入替换为服务端新 UUID4。可信代理环境变量为 `PAPERLENS_TRUSTED_PROXY_CIDRS`，默认空；无条件信任转发头被禁止。

P8.3 状态：已完成并经码道独立收口；路由基线为 69。

## 18. P8.4 华为云部署接口影响

P8.4 不新增公开 HTTP API。OBSStorage 为内部存储层变更，不影响 API 契约。

生产环境变更：
- `PAPERLENS_ENV=production` 时关闭 `/api/docs`、`/api/openapi.json` 和 `/redoc`
- 三个 health 端点行为不变，但生产环境通过 Nginx/ELB 代理

P8.4 初版状态：代码、部署资产和文档实现完毕；随后已按 18.1 完成独立集中验收与直接收口，真实华为云发布仍由用户执行。

### 18.1 P8.4 收口校准

生产实际关闭 `/api/docs`、`/api/redoc` 和 `/api/openapi.json`，三者均返回 404。`/api/v1/health/live` 用于进程存活，`/api/v1/health/ready` 用于后端/RDS 就绪；Nginx 另提供不依赖后端的 `/healthz` 给 ELB。OBS 适配不新增公开 API 或改变响应 schema。P8.4 已完成本地轻量验收，真实域名与云服务验收留待部署。

## 19. 论文学习报告导出契约调整

`POST /api/v1/papers/{paper_id}/exports` 请求与响应 schema 保持兼容。行为调整如下：

- 论文状态为 `PARSED` 即可创建导出，不再因缺少成功审阅返回 `REVIEW_NOT_READY`。
- 报告固定包含论文信息、学习解释、高亮和笔记；成功审阅存在时自动加入“批判性阅读”章节。
- `include_metrics` 与 `include_experiment_analysis` 继续控制指标和实验分析扩展章节；来源缺失不阻断导出。
- `409` 仅保留论文未解析或来源完整性异常等真实冲突；前端不得把所有 `409` 映射为“请先审阅”。
- 列表、状态和下载 API 契约不变，三种格式的 MIME 与安全下载规则不变。

## 20. 学习解释退出接口影响

无 API 变更。退出操作不发送删除或导航请求，解释历史继续使用既有列表数据。
