# API 接口详细设计

## 文档信息

| 项目 | 内容 |
|------|------|
| 项目名称 | PaperLens |
| 文档版本 | v1.0 |
| 创建日期 | 2026-07-13 |
| 最后更新 | 2026-07-14 |

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

> ✅ **P3.5 CURRENT**：所有现有业务路由使用 Bearer JWT + sid/AuthSession/User 数据库校验。

当前 Bearer Token 认证: `Authorization: Bearer <token>`

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

✅ **CURRENT**: `POST /api/v1/papers/{paper_id}/tasks`（P3.3 仍仅支持 REVIEW）

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

P3.3 只返回当前用户论文下、通过 AnalysisTask.user_id 再次隔离的结果。公开 findings 仅包含 VERIFIED 项；UNVERIFIED 项不展示。Evidence 使用按维度语义 Top-K；LLM 默认使用 MockLLMClient，也可配置 HuaweiMaaSLLMClient，二者输出均经过同一严格解析与 Evidence 绑定流程。

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

✅ **CURRENT**: `GET /api/v1/papers/{paper_id}/metrics`

**查询参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| task_id | UUID | 按任务过滤 |
| metric_name | String | 按规范指标名精确过滤 |
| dataset_name | String | 按数据集过滤 |
| checkpoint_type | String | FINAL / MAX / MEAN / BEST / LAST / UNKNOWN |
| page / page_size | Integer | 分页，page_size 最大 100 |

**响应** `200`:

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

✅ **CURRENT**: `GET /api/v1/metrics/{metric_id}` 返回单条同结构详情。创建任务使用 `POST /papers/{paper_id}/tasks` 和 `task_type=METRIC_EXTRACTION`；options 只能省略或为空对象。百分号统一返回 0～1，跨用户详情返回 404。P4.2 页面查询始终携带已选成功任务的 `task_id`，空筛选不序列化，分页限制为 1～100。

## 8. 实验数据文件 API

### 8.1 上传实验数据文件

✅ **CURRENT (P5.1)**: `POST /api/v1/papers/{paper_id}/experiment-files/upload`

**请求类型**: `multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | CSV/XLSX/XLS 文件，最大 20MB |

仅当前用户自己的 PARSED 论文可上传。新建返回 `201`；同一 user/paper/SHA-256 重复返回已有资源和 `200`。类型/magic 不符为 415，实际字节或安全解析上限为 413，结构不可解析为 422，非 PARSED 为 409，不存在/跨用户为 404。

**响应** `201` 或幂等 `200`:

```json
{
  "id": "uuid",
  "paper_id": "uuid",
  "filename": "experiment_results.csv",
  "file_type": "CSV",
  "file_size": 1024,
  "row_count": 50,
  "column_count": 2,
  "columns_info": {
    "version": 1,
    "encoding": "utf-8",
    "delimiter": ",",
    "sheet_name": null,
    "columns": [
      {"name": "model", "dtype": "string", "nullable": false, "null_count": 0},
      {"name": "accuracy", "dtype": "float", "nullable": false, "null_count": 0}
    ]
  },
  "duplicate": false,
  "created_at": "2026-07-14T00:00:00Z"
}
```

完整 `file_hash`、`storage_key`、样本值和数据行不公开。

### 8.2 获取实验数据文件列表

✅ **CURRENT (P5.1)**: `GET /api/v1/papers/{paper_id}/experiment-files?page=1&page_size=20`

**响应** `200`:

```json
{
  "items": [
    {
      "id": "uuid",
      "paper_id": "uuid",
      "filename": "experiment_results.csv",
      "file_type": "CSV",
      "file_size": 1024,
      "row_count": 50,
      "column_count": 2,
      "created_at": "2026-07-12T11:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

按 `created_at DESC, id DESC` 稳定排序，page 从 1 开始，page_size 为 1～100。论文不存在和跨用户统一 404。

### 8.3 获取实验文件结构详情

✅ **CURRENT (P5.1)**: `GET /api/v1/experiment-files/{file_id}`

**响应** `200`:

```json
{
  "id": "uuid",
  "paper_id": "uuid",
  "filename": "experiment_results.xlsx",
  "file_type": "XLSX",
  "file_size": 4096,
  "row_count": 50,
  "column_count": 1,
  "columns_info": {
    "version": 1,
    "encoding": null,
    "delimiter": null,
    "sheet_name": "Sheet1",
    "columns": [
      {"name": "accuracy", "dtype": "float", "nullable": false, "null_count": 0}
    ]
  },
  "created_at": "2026-07-14T00:00:00Z"
}
```

不存在和跨用户统一 404。

### 8.4 创建实验统计任务

✅ **CURRENT (P5.2)**: `POST /api/v1/experiment-files/{file_id}/analysis`

新建返回 201；活动任务或已有结果返回 200 与 `duplicate=true`。非 PARSED 为 409，规模超限为 413；不存在、跨用户及 ADMIN 他人访问统一 404。

### 8.5 获取实验统计结果

✅ **CURRENT (P5.3a)**: `GET /api/v1/experiment-files/{file_id}/result`

返回 `id/file_id/task_id/summary_stats/metric_comparisons/created_at`。未执行交叉验证时 metric_comparisons=null，完成后为严格比较数组；不暴露文件哈希、storage key、原始行、column_analysis 或来源正文。

### 8.6 创建指标交叉验证

✅ **CURRENT (P5.3a)**: `POST /api/v1/experiment-files/{file_id}/comparisons`

请求只允许 `{"metric_task_id":"uuid4"}`。首次 201、同源幂等 200；响应固定 `file_id/experiment_result_id/metric_task_id/comparisons/duplicate`。异源 `COMPARISON_ALREADY_EXISTS`、无指标 `NO_METRICS`、错误类型/状态/论文均为固定 409；不存在及跨 USER/ADMIN 为 404。

### 8.7 删除实验数据文件

📋 **PLANNED**: `DELETE /api/v1/experiment-files/{file_id}`

**响应** `204`: 无内容

## 9. 报告导出 API

### 9.1 生成导出报告

✅ **CURRENT (P6.1～P6.2)**: `POST /api/v1/papers/{paper_id}/exports`

**请求参数:**

```json
{
  "report_type": "MARKDOWN",
  "include_metrics": true,
  "include_experiment_analysis": true,
  "language": "zh"
}
```

新来源返回 `201`；相同用户/论文/格式/选项/source_hash/content_hash 的 PENDING/GENERATING/READY 幂等返回 `200`，FAILED 可重试。非 PARSED、无合法审阅或来源图异常为 409，不存在/跨用户为 404。请求 extra=forbid，report_type 只允许 MARKDOWN/PDF/DOCX。

**响应** `201` 或幂等 `200`:

```json
{
  "id": "uuid",
  "paper_id": "uuid",
  "report_type": "MARKDOWN",
  "status": "PENDING",
  "language": "zh",
  "include_metrics": true,
  "include_experiment_analysis": true,
  "file_size": null,
  "error_message": null,
  "created_at": "2026-07-12T12:00:00Z",
  "completed_at": null,
  "duplicate": false
}
```

### 9.2 获取导出状态

✅ **CURRENT (P6.1～P6.2)**: `GET /api/v1/exports/{export_id}`

**响应** `200`:

```json
{
  "id": "uuid",
  "paper_id": "uuid",
  "report_type": "MARKDOWN",
  "status": "READY",
  "language": "zh",
  "include_metrics": true,
  "include_experiment_analysis": true,
  "file_size": 20480,
  "error_message": null,
  "created_at": "2026-07-12T12:00:00Z",
  "completed_at": "2026-07-12T12:01:00Z",
  "duplicate": false
}
```

### 9.3 下载导出报告

✅ **CURRENT (P6.1～P6.2)**: `GET /api/v1/exports/{export_id}/download`

**响应** `200`: 文件流

- Content-Type: MARKDOWN `text/markdown; charset=utf-8`；PDF `application/pdf`；DOCX `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- Content-Disposition: `attachment; filename="{sanitized_filename}"`
- X-Content-Type-Options: `nosniff`
- Cache-Control: `private, no-store`
- 仅 status=READY 可下载；非 READY 为 409，不存在/跨用户为 404
- 发送前通过 StorageBackend 回读并复核 file_size/content_hash；公开 API 永不返回 source_snapshot/source_hash/content_hash/storage_key

### 9.4 获取论文导出历史

✅ **CURRENT (P6.2)**: `GET /api/v1/papers/{paper_id}/exports?page=1&page_size=20`

- page 从 1 开始，page_size 范围 1～100
- 仅论文所有者可见，USER/ADMIN 跨用户统一 404
- 按 created_at DESC、id DESC 排序
- 返回 `items/total/page/page_size`；item 不含 duplicate 和任何内部快照、哈希或对象 key
- 页面只轮询当前页；PENDING/GENERATING 全部结束后停止

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

## 12. 阅读学习 API（P7.1 COMPLETED）

### 12.1 创建解释

`POST /api/v1/papers/{paper_id}/learning-explanations`

```json
{
  "mode": "EXPLAIN",
  "scope_type": "SECTION",
  "section_id": "uuid",
  "page_number": null,
  "evidence_id": null,
  "output_language": "zh"
}
```

客户端不能发送 text、prompt、user_id、evidence_refs 或 model。新建 201；同活动/成功请求复用 200。论文不存在、跨用户或 scope 不归属统一 404；论文未解析或来源不足为固定 409；非法互斥字段为 422。

### 12.2 获取解释

`GET /api/v1/learning-explanations/{explanation_id}` 返回 id/paper_id/mode/scope/status/answer/key_points/terms/citations/error_message/timestamps/duplicate。Citation 只含安全 Evidence 字段；PENDING/RUNNING 不含结果，FAILED 只含固定错误。

### 12.3 获取历史

`GET /api/v1/papers/{paper_id}/learning-explanations?page=1&page_size=20` 按 created_at DESC/id DESC，返回 items/total/page/page_size；page_size 1～100。全部接口都要求真实登录用户和资源所有权。

**文档版本**: v1.3
**创建日期**: 2026-07-13
**最后更新**: 2026-07-15

## 13. P7.2 论文问答接口

1. `POST /api/v1/papers/{paper_id}/qa-conversations`：请求 `{}`，创建空会话。
2. `GET /api/v1/papers/{paper_id}/qa-conversations?page=1&page_size=20`：items/total/page/page_size 和摘要元数据。
3. `GET /api/v1/qa-conversations/{conversation_id}?page=1&page_size=20`：按 sequence ASC 返回 turns/total/page/page_size。
4. `POST /api/v1/qa-conversations/{conversation_id}/turns`：只接受 question/output_language/client_request_id；201 或幂等 200。
5. `GET /api/v1/qa-turns/{turn_id}`：轮询安全详情。

UUID4、分页、401/404/409/422 和响应字段遵循 systemDesign/04。GET 不公开 client_request_id/context_hash；Citation 只公开 Evidence 定位安全字段。
