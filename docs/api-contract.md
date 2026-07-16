# PaperLens REST API 契约文档

## 通用约定

- 基础路径：`/api/v1`
- 认证：Bearer Token（JWT access token），通过 `/api/v1/auth/login` 获取；refresh token 通过 `paperlens_refresh` HttpOnly cookie 传输
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

## 0. 认证

公开端点仅为 register、login、refresh、forgot-password、reset-password。logout、logout-all、me、change-password 以及其他业务端点都要求 `Authorization: Bearer <access_token>`；认证失败返回 401 和 `WWW-Authenticate: Bearer`。

### POST /auth/register

注册新用户。

**请求**：
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| email | String | 是 | 邮箱地址 |
| password | String | 是 | 15~128 Unicode code point |
| display_name | String | 是 | 显示名称，去除首尾空白后 1～100 字符 |

**响应** `201`：
```json
{
  "access_token": "jwt...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "display_name": "User",
    "role": "USER",
    "status": "ACTIVE",
    "created_at": "2026-07-13T10:00:00Z"
  }
}
```
同时设置 refresh HttpOnly cookie，响应不会包含 password/session/token hash。

### POST /auth/login

登录。成功返回 access token 和 refresh cookie。

**请求**：
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| email | String | 是 | 邮箱地址 |
| password | String | 是 | 密码 |

**响应** `200`：
```json
{
  "access_token": "jwt...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": { "id": "...", "email": "...", "display_name": "...", "role": "USER", "status": "ACTIVE", "created_at": "..." }
}
```
Set-Cookie: `paperlens_refresh=<opaque>; HttpOnly; SameSite=Lax; Path=/api/v1/auth; Max-Age=2592000`。生产 HTTPS 必须含 `Secure`；本地 HTTP 仅可通过显式配置关闭。

### POST /auth/refresh

刷新 access token。读取 `paperlens_refresh` cookie，单次轮换，重放检测撤销整个 family。

**响应** `200`：同 login 响应格式。

### POST /auth/logout

登出当前 session family。**需认证**；服务端依据 access token 的 sid/family 撤销，不信任客户端自报身份。

**响应** `200`：`{ "message": "Logged out" }`

### POST /auth/logout-all

登出所有 session。**需认证**。

**响应** `200`：`{ "message": "Logged out from all sessions" }`

### GET /auth/me

获取当前用户信息。**需认证**。

**响应** `200`：
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "display_name": "User",
  "role": "USER",
  "status": "ACTIVE",
  "created_at": "2026-07-13T10:00:00Z"
}
```

### PATCH /auth/me

更新个人资料。**需认证**。

**请求**：
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| display_name | String | 否 | 显示名称 |

**响应** `200`：同 GET /auth/me 响应格式。

### POST /auth/change-password

修改密码。**需认证**。修改后撤销所有 session。

**请求**：
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| old_password | String | 是 | 当前密码 |
| new_password | String | 是 | 新密码（15~128 Unicode code point） |

**响应** `200`：`{ "message": "Password changed" }`

### POST /auth/forgot-password

请求密码重置。统一返回 202，不泄露邮箱是否存在。

**请求**：
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| email | String | 是 | 邮箱地址 |

**响应** `202`：`{ "message": "If the email exists, a reset link will be sent" }`

### POST /auth/reset-password

重置密码。单次 token，使用后失效。

**请求**：
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| token | String | 是 | 重置令牌 |
| new_password | String | 是 | 新密码（15~128 Unicode code point） |

**响应** `200`：`{ "message": "Password reset successful" }`

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

> P3.3 CURRENT：当前仅支持 `task_type=REVIEW`，使用 FastAPI BackgroundTasks 和按维度语义 Evidence 检索；LLM 默认使用离线 MockLLMClient，也可配置非流式 HuaweiMaaSLLMClient。`METRIC_EXTRACTION`、`EXPERIMENT_ANALYSIS` 与任务取消仍为规划功能。

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

当前公开响应只返回 `VERIFIED` Finding；引用为空、未知 alias、原始 UUID 或混合非法引用的 Finding 保存为 `UNVERIFIED` 且不展示。P3.2 对同论文 Evidence 执行任务内即时 Embedding、按审阅维度精确余弦排序和 Top-K 选择；默认客户端为离线 MockEmbeddingClient，也可配置华为云 MaaS Embedding。P3.3 在统一 LLMClient 下增加 HuaweiMaaSLLMClient，响应仍必须经过现有严格 JSON、维度和 Evidence 绑定校验。FAISS/pgvector 持久化索引仍为规划。

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

### POST /papers/{paper_id}/tasks

创建指标提取任务：

```json
{
  "task_type": "METRIC_EXTRACTION",
  "options": {}
}
```

`options` 可省略或为空对象，其他字段返回 422。论文必须属于当前用户且状态为 PARSED；无真实候选或已有活动任务返回 409。

### GET /papers/{paper_id}/metrics
获取论文的实验指标记录。

**查询参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| task_id | UUID | 按指标任务过滤 |
| metric_name | String | 按规范指标名精确过滤 |
| dataset_name | String | 按数据集过滤 |
| checkpoint_type | String | FINAL / MAX / MEAN / BEST / LAST / UNKNOWN |
| page | Integer | 页码，默认 1 |
| page_size | Integer | 1～100，默认 20 |

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
      "table_id": "uuid",
      "row_index": 2,
      "raw_text": "F1: 83.1%",
      "created_at": "2026-07-14T00:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

百分号统一序列化为 0～1。Checkpoint 没有明确证据时返回 UNKNOWN。每条记录只能存在表格行来源或 Evidence 来源之一。

### GET /metrics/{metric_id}

返回单条同结构指标详情。不存在或跨用户访问返回 404；ADMIN 默认也不能越过普通资源所有权。

## 7. 实验数据文件

### POST /papers/{paper_id}/experiment-files/upload
✅ P5.1 CURRENT。上传 CSV/XLSX/XLS；仅当前用户自己的 PARSED 论文可用。

**请求**：`multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | CSV/XLSX/XLS 文件，最大 20MB |

新建返回 `201`；同一 user/paper/SHA-256 重复上传返回已有资源和 `200`。公开响应不包含完整 file_hash、storage_key、样本或数据行。

**响应** `201` 或 `200`：

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

错误：无 token 401；不存在/跨用户 404；非 PARSED 409；扩展名或 magic 415；实际字节/容器安全上限 413；内容结构不可解析 422；内部上传失败为固定安全 500。

### GET /papers/{paper_id}/experiment-files
✅ P5.1 CURRENT。查询参数 `page` 默认 1，`page_size` 默认 20、最大 100；按 `created_at DESC, id DESC` 稳定排序。

**响应** `200`：

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

### GET /experiment-files/{file_id}
✅ P5.1 CURRENT。返回单条结构元数据；不存在、跨用户和 ADMIN 访问他人资源统一 404。

**响应** `200`：

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

### POST /experiment-files/{file_id}/analysis
✅ P5.2 CURRENT。新建 EXPERIMENT_ANALYSIS 返回 201；已有活动任务或结果返回 200 与 `duplicate=true`。论文非 PARSED 返回 409，数值单元格超限返回 413；不接收 user_id、paper_id 或统计选项。

### GET /experiment-files/{file_id}/result
✅ P5.3a CURRENT。返回严格 `id/file_id/task_id/summary_stats/metric_comparisons/created_at`；未就绪 404。summary_stats 为 version=1 列数组；metric_comparisons 为 `null`（尚未交叉验证）或比较项数组。不公开哈希、storage key、原始行或 column_analysis。

### POST /experiment-files/{file_id}/comparisons
✅ P5.3a CURRENT。对实验文件执行论文指标交叉验证。首次返回 201，同源幂等返回 200；异源冲突返回 409。

**请求**：
```json
{
  "metric_task_id": "uuid"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| metric_task_id | String(UUID) | 是 | 已完成的 METRIC_EXTRACTION 任务 ID |

**响应** `201`：
```json
{
  "file_id": "uuid",
  "experiment_result_id": "uuid",
  "metric_task_id": "uuid",
  "comparisons": [
    {
      "metric_record_id": "uuid",
      "metric_task_id": "uuid",
      "metric_name": "accuracy",
      "checkpoint_type": "MEAN",
      "column_name": "accuracy",
      "statistic": "MEAN",
      "paper_value": 0.92,
      "experiment_value": 0.9,
      "diff": -0.02,
      "absolute_diff": 0.02,
      "relative_diff": 0.0217,
      "allowed_diff": 0.0092,
      "status": "MISMATCH",
      "reason": null
    }
  ],
  "duplicate": false
}
```

| status 值 | 说明 |
|-----------|------|
| MATCH | absolute_diff <= allowed_diff |
| MISMATCH | absolute_diff > allowed_diff |
| UNVERIFIABLE | 无法比较（AMBIGUOUS_PAPER_METRIC/UNSUPPORTED_CHECKPOINT/NO_EXPERIMENT_COLUMN/AMBIGUOUS_EXPERIMENT_COLUMN/EMPTY_NORMALIZED_NAME） |

**容差计算**：`allowed_diff = max(abs_tolerance, abs(paper_value) * relative_tolerance)`，默认 `abs_tolerance=1e-6`，`relative_tolerance=0.01`。

**错误响应**：
| 状态码 | code | 说明 |
|--------|------|------|
| 404 | NOT_FOUND | 实验文件/指标任务不存在或跨用户 |
| 404 | RESULT_NOT_READY | 实验分析结果尚未就绪 |
| 409 | TASK_TYPE_MISMATCH | 任务类型不是 METRIC_EXTRACTION |
| 409 | TASK_NOT_SUCCEEDED | 指标任务未完成 |
| 409 | PAPER_MISMATCH | 指标任务与论文不匹配 |
| 409 | NO_METRICS | 指标任务没有记录，且不写入空数组 |
| 409 | COMPARISON_ALREADY_EXISTS | 已有不同来源的交叉验证结果 |
| 409 | COMPARISON_STATE_INVALID / METRIC_STATE_INVALID | 结果、任务或来源关系异常 |

### DELETE /experiment-files/{file_id}
📋 PLANNED。当前未注册。

### P5.3b 前端消费约束

实验数据前端不新增接口。上传使用浏览器 FormData 且不得手写 multipart Content-Type；列表 page/page_size 在客户端限制为合法范围。选择文件后同时调用可信详情和 result；已有 `metric_comparisons` 直接展示并锁定 `metric_task_id`，不得再次 POST 覆盖。任务、详情、结果和比较响应若不匹配当前 paper/file/task 上下文必须丢弃，未知服务端错误不得原样进入页面。

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
| report_type | String | 是 | 严格允许 MARKDOWN / PDF / DOCX |
| include_metrics | Boolean | 否 | 是否包含指标记录，默认 true |
| include_experiment_analysis | Boolean | 否 | 是否包含实验分析，默认 true |
| language | String | 否 | 报告语言：zh / en，默认 zh |

**响应** `201`：
```json
{
  "id": "uuid",
  "paper_id": "uuid",
  "report_type": "MARKDOWN",
  "language": "zh",
  "include_metrics": true,
  "include_experiment_analysis": true,
  "status": "PENDING",
  "file_size": null,
  "error_message": null,
  "created_at": "2026-07-12T12:00:00Z",
  "completed_at": null,
  "duplicate": false
}
```

新来源首次创建为 `201 duplicate=false`；相同用户/论文/格式/选项/来源/内容的 PENDING/GENERATING/READY 返回 `200 duplicate=true`；FAILED 可重试。三种格式均在创建 PENDING 前完成确定性 bytes/hash，后台只保存创建时 bytes。无合法审阅或来源关系异常为固定 409。请求拒绝 extra 字段，响应不公开任何内部快照、哈希或对象 key。

### GET /papers/{paper_id}/exports

当前论文的导出历史。查询参数 `page>=1`、`1<=page_size<=100`，默认 1/20；仅论文所有者可见，按 `created_at DESC, id DESC` 返回 `items/total/page/page_size`。PENDING/GENERATING 页面每 3 秒重新请求当前页，完成后停止。

### GET /exports/{export_id}
获取导出状态（用于 HTTP 轮询）。

**响应** `200`：
```json
{
  "id": "uuid",
  "paper_id": "uuid",
  "report_type": "MARKDOWN",
  "language": "zh",
  "include_metrics": true,
  "include_experiment_analysis": true,
  "status": "READY",
  "file_size": 20480,
  "error_message": null,
  "created_at": "2026-07-12T12:00:00Z",
  "completed_at": "2026-07-12T12:01:00Z",
  "duplicate": false
}
```

### GET /exports/{export_id}/download
下载导出的报告文件。

**响应** `200`：MARKDOWN 为 `text/markdown; charset=utf-8`，PDF 为 `application/pdf`，DOCX 为 `application/vnd.openxmlformats-officedocument.wordprocessingml.document`。均包含 attachment、nosniff 与 private/no-store。仅 READY 且 StorageBackend 回读 size/hash 一致时下载；未就绪、缺失或损坏固定 409。

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

## P7.1 阅读学习接口（COMPLETED）

| 方法与路径 | 说明 |
|------------|------|
| POST `/api/v1/papers/{paper_id}/learning-explanations` | 创建/复用 SECTION、PAGE 或 EVIDENCE 的 SUMMARY、EXPLAIN、TRANSLATE |
| GET `/api/v1/learning-explanations/{explanation_id}` | 查询状态、严格结果和 Evidence Citation |
| GET `/api/v1/papers/{paper_id}/learning-explanations?page&page_size` | 当前用户的论文解释历史分页 |

客户端只提交实体 id、模式和输出语言，不提交论文正文、prompt、user_id 或模型参数。新建返回 201；相同活动/成功请求复用并返回 200 与 `duplicate=true`。非法 extra、scope 互斥、枚举或分页返回 422；论文未解析、来源为空/没有 Citation 或章节过大返回 409；不存在与越权统一 404。

详情在 PENDING/RUNNING 时不返回结果，FAILED 只返回固定公开错误，SUCCEEDED 返回纯文本 answer、key_points、`[{term, explanation}]` 和按 sequence 排序的 Citation。Citation 只公开 `evidence_id/sequence/page_number/evidence_type/quoted_text/char_start/char_end`，不公开 request_hash、source hash、prompt 或模型原始响应。当前公开路由数为 37。

## P7.2 当前论文问答 API（COMPLETED）

| Method + Path | 说明 |
|---|---|
| POST `/api/v1/papers/{paper_id}/qa-conversations` | 严格 `{}` 创建空会话 |
| GET `/api/v1/papers/{paper_id}/qa-conversations?page&page_size` | 会话摘要、轮数、最新状态分页 |
| GET `/api/v1/qa-conversations/{conversation_id}?page&page_size` | sequence ASC 的轮次分页 |
| POST `/api/v1/qa-conversations/{conversation_id}/turns` | question/output_language/UUID4 client_request_id；201 或幂等 200 |
| GET `/api/v1/qa-turns/{turn_id}` | 单轮状态与安全结果 |

所有业务访问 owner-only；ADMIN 不绕过所有权。无 Evidence、未解析或已有活动轮次返回 409；不存在/越权统一 404。GET 响应不公开 client_request_id/context_hash/prompt/向量/模型参数/内部错误。grounded=true 至少一个安全 Citation；grounded=false Citation 为空且 answer 明确当前论文证据不足。当前公开 `/api/v1` method+path 为 42。

## P7.3 个人学习 API（COMPLETED）

新增 17 条路由：论文库列表、library entry、阅读进度共 3 条；高亮/书签各 3 条；笔记/知识卡各 4 条。全部要求认证并严格 owner-only，普通 ADMIN 不绕过所有权；不存在与跨用户统一 404，非 PARSED/引用删除冲突返回固定 409，非法 UUID、枚举、空 PATCH、null、控制字符和长度返回 422。

论文库及四类记录列表均使用 page/page_size 稳定分页。高亮和书签重复创建返回既有对象、200 与 duplicate=true；公开响应不包含 user_id、source 内部快照或底层异常。最终公开 `/api/v1` method+path 为 59。
