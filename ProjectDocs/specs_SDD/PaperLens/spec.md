# PaperLens - 需求规格说明书

## 文档信息

| 项目 | 内容 |
|------|------|
| 项目名称 | PaperLens |
| 文档版本 | v1.0 |
| 创建日期 | 2026-07-13 |
| 最后更新 | 2026-07-13 |
| 文档状态 | 已完成 |
| 关联设计 | design/ |

## 1. 引言

### 1.1 编写目的

本文档为 PaperLens 项目的 SDD 需求规格说明书，用于指导系统设计、开发和测试。所有开发任务必须可追溯到本文档中的需求 ID。

### 1.2 项目背景

学术论文审阅是科研工作的核心环节，但当前面临以下问题：

- 人工审稿耗时，阅读一篇论文并撰写审稿意见通常需要 2-4 小时
- 论文中实验指标常以 final/max/mean/best 等不同口径报告，人工难以快速识别和统一对比
- PDF 中的表格结构复杂，复制粘贴后格式错乱，手工转录易出错
- 论文报告的指标与原始实验日志之间可能存在偏差，缺乏自动化交叉验证手段
- AI 生成的审稿意见常出现幻觉，无法追溯到论文原文，可信度低

PaperLens 旨在通过 AI 辅助论文审阅、指标提取和实验数据交叉验证，解决上述痛点。

### 1.3 术语定义

| 术语 | 定义 |
|------|------|
| Evidence | 原文证据，审阅结论的依据，包含页码、bbox 坐标和字符偏移 |
| ReviewFinding | 审阅发现，每条发现绑定 Evidence，类型为 STRENGTH / WEAKNESS / SUGGESTION |
| Checkpoint Type | 统计口径，如 FINAL / MAX / MEAN / BEST / LAST |
| PaperChunk | 文本分块，用于向量索引和证据检索 |
| page-local | 页内定位，Evidence 不涉及跨页 span |

### 1.4 参考资料

- design/01-论文上传与解析.md — 论文上传与解析模块设计
- design/02-证据提取与检索.md — 证据提取与检索模块设计
- design/03-审阅生成.md — 审阅生成模块设计
- design/04-指标提取与口径判断.md — 指标提取与口径判断模块设计
- design/05-实验数据分析.md — 实验数据分析模块设计
- design/06-报告导出.md — 报告导出模块设计
- design/07-前端展示.md — 前端展示模块设计
- design/08-数据模型详细设计.md — 数据模型详细设计
- design/09-API接口详细设计.md — API 接口详细设计
- design/10-前端详细设计.md — 前端详细设计

## 2. 项目概述

### 2.1 项目目标

通过开发 PaperLens，实现：

- AI 辅助论文审阅，每条结论绑定原文 Evidence，消除幻觉
- 自动从论文表格和正文中提取实验指标，识别统计口径
- 实验数据文件（CSV/Excel）与论文指标交叉验证，标记偏差
- 审阅报告多格式导出（Markdown / PDF / DOCX）

### 2.2 项目范围

**包含范围:**

- 论文 PDF 上传与解析（文本、页面、章节、表格）
- 文本分块与 Evidence 提取（page-local 定位）
- 向量索引与语义检索（FAISS）
- 结构化论文审阅（按维度生成 Finding，绑定 Evidence）
- 实验指标提取与 Checkpoint 口径判断
- CSV/Excel 实验数据上传与统计分析
- 指标交叉验证（论文 vs 实验数据）
- 审阅报告多格式导出（Markdown / PDF / DOCX）

**不包含范围:**

- 论文自动投稿
- 论文写作辅助
- 学术搜索引擎
- 实时协作编辑
- 论文查重
- 模型训练平台
- 通用文档问答
- 扫描型 PDF / OCR
- 分片上传

### 2.3 用户特征

| 用户角色 | 描述 | 技术水平 | 使用频率 |
|----------|------|----------|----------|
| 研究者（Researcher） | 需要审阅论文、提取实验指标、对比实验结果的科研人员 | 高 | 每天 |
| 审稿人（Reviewer） | 需要快速生成结构化审稿意见的学术审稿人 | 中-高 | 每周 |
| 实验分析师（Analyst） | 需要从论文和实验数据中提取、汇总、对比指标的数据分析人员 | 中 | 每周 |

### 2.4 约束条件

**技术约束:**

- 开发语言: Python 3.10+（后端）、TypeScript（前端）
- 开发框架: FastAPI（后端）、Vue3（前端）
- 数据库: PostgreSQL 15+
- ORM: SQLAlchemy 2.x + Alembic
- 部署环境: 华为云 ECS + RDS + OBS + ModelArts

**业务约束:**

- 所有审阅结论必须绑定 Evidence，不允许无依据的结论
- 大模型不直接计算统计数据，所有数值统计由确定性 Python 代码计算
- 仅支持包含可提取文本的 PDF，不支持扫描型 PDF / OCR
- 文件上传使用普通 multipart 流式上传，暂不实现分片上传
- 任务进度通知使用 HTTP 轮询，暂不实现 WebSocket
- 后台任务使用 FastAPI BackgroundTasks（仅 MVP），暂不引入 Celery + Redis

**设计约束:**

- LLM 必须通过统一 LLMClient 接口调用，默认提供 MockLLMClient
- 存储层通过 StorageBackend 接口抽象，LocalStorage 为当前实现
- Evidence 采用 page-local 定位，不涉及跨页 span
- 向量索引使用 FAISS，后续可迁移至 Milvus

## 3. 功能需求

### 3.1 论文上传与解析 (P0)

#### 3.1.1 论文上传 (F01)

**功能描述:** 支持 PDF 文件上传（multipart 流式上传），文件类型校验，大小限制 50MB。

**功能需求:**
- FR-01.1.1: 支持单文件 PDF 上传（multipart/form-data）
- FR-01.1.2: 文件类型校验（仅接受包含可提取文本的 PDF）
- FR-01.1.3: 文件大小限制 50MB
- FR-01.1.4: 路径穿越防护
- FR-01.1.5: SHA-256 文件哈希计算与存储（去重/复用逻辑 📋 PLANNED）
- FR-01.1.6: 上传后自动触发后台解析任务

**验收标准:**
- PDF 文件可成功上传
- 非 PDF 文件返回 415 错误
- 超过 50MB 返回 413 错误
- 上传后状态为 PROCESSING，并注册后台解析任务

#### 3.1.2 PDF 解析 (F02)

**功能描述:** 提取文本、页面信息，识别章节结构。

**功能需求:**
- FR-01.2.1: 使用 PyMuPDF + pdfplumber 提取页面文本
- FR-01.2.2: 生成 normalized_text_content（空白字符合并）
- FR-01.2.3: 识别章节结构（ABSTRACT / INTRODUCTION / METHOD 等）
- FR-01.2.4: 提取页面尺寸（width / height）
- FR-01.2.5: 仅支持包含可提取文本的 PDF

**验收标准:**
- 上传 PDF 后状态变为 PARSED
- 页面文本和章节结构可查询
- 解析失败状态变为 FAILED，含 error_message

#### 3.1.3 表格提取 (F03)

**功能描述:** 从 PDF 中提取表格并结构化存储。

**功能需求:**
- FR-01.3.1: 使用 pdfplumber 提取表格
- FR-01.3.2: 存储为 structured_data（JSONB）和 raw_text（兜底）
- FR-01.3.3: 记录表格 bbox 坐标和 caption
- FR-01.3.4: 非法表格（page_number=0）使用 SAVEPOINT 降级跳过

**验收标准:**
- 表格可提取并结构化存储
- 非法表格不影响论文整体解析状态

#### 3.1.4 文本分块 (F04)

**功能描述:** 按语义段落/章节对论文文本进行分块。

**功能需求:**
- FR-01.4.1: 按章节/段落分块，生成 PaperChunk 记录
- FR-01.4.2: 记录块序号、字符数、涉及页码
- FR-01.4.3: 预留 embedding_id 字段（向量索引 ID）

**验收标准:**
- 文本分块可查询
- 每个块关联所属章节

### 3.2 证据提取与检索 (P0)

#### 3.2.1 向量索引 (F05)

**功能描述:** 对文本块进行 Embedding 并建立向量索引。

**功能需求:**
- FR-02.1.1: 调用 Embedding 模型向量化 PaperChunk
- FR-02.1.2: 使用 FAISS 建立向量索引
- FR-02.1.3: 索引可序列化持久化

**验收标准:**
- 文本块可向量化并索引

#### 3.2.2 原文证据检索 (F06)

**功能描述:** 基于问题/关键词检索相关文本块，返回 Evidence（含 PDF 精确定位）。

**功能需求:**
- FR-02.2.1: Evidence 为 page-local 定位，基于 PyMuPDF block 提取
- FR-02.2.2: 使用真实 bbox 坐标和字符偏移（char_start / char_end）
- FR-02.2.3: 支持 TEXT / TABLE / FIGURE_CAPTION / EQUATION 类型
- FR-02.2.4: 前端基于 normalized_text_content 字符区间高亮

**验收标准:**
- Evidence 可提取并查询（page-local, real bbox）
- 前端可高亮跳转到 Evidence 位置
- 语义检索功能

### 3.3 审阅生成（P1，P3.1 后端基础闭环已实现）

#### 3.3.1 结构化论文审阅 (F07)

**功能描述:** 生成包含优缺点、改进建议的审阅结果，每条 Finding 绑定 Evidence。

**功能需求:**
- FR-03.1.1: 按维度生成审阅结果（SOUNDNESS / NOVELTY / CLARITY 等）
- FR-03.1.2: 每条 ReviewFinding 必须关联至少一个 Evidence
- FR-03.1.3: 未关联 Evidence 的 Finding 标记为 UNVERIFIED，不展示给用户
- FR-03.1.4: 支持 STRENGTH / WEAKNESS / SUGGESTION 类型
- FR-03.1.5: 评分 1-5，含 overall_verdict

**验收标准:**
- P3.1 已实现 REVIEW 任务创建/查询、MockLLM 结构化结果和 VERIFIED Evidence 绑定
- UNVERIFIED Finding 保留审计但不通过公开 API 返回
- P3.2 语义检索和 P3.3 华为云真实模型仍为规划

### 3.4 指标提取与口径判断 (P1, 规划)

#### 3.4.1 实验指标提取 (F08)

**功能描述:** 从表格和正文中提取实验指标，记录指标名、值、数据集、模型名。

**功能需求:**
- FR-04.1.1: 从 PaperTable 的 structured_data 中提取指标
- FR-04.1.2: 记录模型名、数据集名、指标名、指标值
- FR-04.1.3: 关联来源 Evidence 和表格行号

**验收标准:**
- 指标记录 API 返回结构化数据

#### 3.4.2 Checkpoint 口径判断 (F09)

**功能描述:** 识别 final/max/mean/best 等统计口径并标注。

**功能需求:**
- FR-04.2.1: 基于规则引擎判断 checkpoint_type（关键词匹配 + 上下文分析）
- FR-04.2.2: 标注口径来源（EXPLICIT_TEXT / IMPLICIT_CONTEXT / TABLE_HEADER / UNKNOWN）
- FR-04.2.3: LLM 仅辅助歧义消解，不参与数值计算

**验收标准:**
- 指标记录含 checkpoint_type 和 checkpoint_source

### 3.5 实验数据分析 (P2, 规划)

#### 3.5.1 CSV/Excel 实验数据分析 (F11)

**功能描述:** 上传 CSV/Excel 文件，解析数据列，计算统计摘要。

**功能需求:**
- FR-05.1.1: 支持 CSV / XLSX / XLS 文件上传（最大 20MB）
- FR-05.1.2: 使用 pandas 解析数据列，自动识别指标列与条件列
- FR-05.1.3: 使用确定性 Python 代码计算统计摘要（mean、std、min、max、median）
- FR-05.1.4: LLM 不参与任何数值计算

**验收标准:**
- 实验数据文件可上传并解析

#### 3.5.2 指标交叉验证 (F12)

**功能描述:** 对比论文报告指标与实验数据文件中的指标，标记偏差。

**功能需求:**
- FR-05.2.1: 匹配论文 MetricRecord 与实验数据中的指标
- FR-05.2.2: 计算偏差值（diff）
- FR-05.2.3: 标记验证状态（MATCH / MISMATCH）

**验收标准:**
- 交叉验证结果可查询

### 3.6 报告导出 (P2, 规划)

#### 3.6.1 审稿报告导出 (F10)

**功能描述:** 导出 Markdown 格式的审阅报告。

**功能需求:**
- FR-06.1.1: 生成包含审阅结果、指标记录的报告
- FR-06.1.2: 支持 Markdown 格式导出
- FR-06.1.3: 支持中英文语言选择

**验收标准:**
- 报告可导出下载

#### 3.6.2 PDF/DOCX 报告导出 (F13)

**功能描述:** 支持导出为 PDF 和 DOCX 格式。

**功能需求:**
- FR-06.2.1: 支持 PDF 格式导出
- FR-06.2.2: 支持 DOCX 格式导出

**验收标准:**
- 多格式报告可导出下载

## 4. 非功能需求

### 4.1 性能需求

| 性能指标 | 要求 | 说明 |
|----------|------|------|
| PDF 解析时间 | < 30 秒 | 单篇论文解析时间 |
| Evidence 检索时间 | < 2 秒 | Top-K 语义检索 |
| API 响应时间 | < 500ms | 常规查询响应 |
| 文件上传限制 | 50MB (PDF) / 20MB (CSV/Excel) | 最大文件大小 |

### 4.2 安全需求

**文件安全:**
- 文件类型验证（仅 PDF / CSV / XLSX / XLS）
- 文件大小限制
- 路径穿越防护
- 文件名安全处理

**数据安全:**
- 用户数据隔离（不同用户的论文和审阅结果严格隔离）
- HTTPS 传输加密（云端部署）
- SQL 注入防护（ORM 参数化查询）
- 错误信息不泄露内部异常（_safe_error_message()）

**认证安全:**
- Bearer Token（JWT）认证（📋 PLANNED: 当前 `_get_user_id()` 返回 `settings.demo_user_id`，无实际鉴权）
- MVP 阶段使用简单 Token，后续集成 IAM

### 4.3 可用性需求

**用户体验:**
- 论文上传后自动解析，无需手动触发
- Evidence 高亮跳转，精确定位原文
- 后端不可用时显示明确错误提示
- 任务进度通过 HTTP 轮询展示

**易用性:**
- 上传论文仅需选择文件和可选标题
- 审阅结果按维度组织，Finding 绑定 Evidence 可追溯

### 4.4 兼容性需求

**浏览器兼容:**
- Chrome / Firefox / Edge / Safari 最新版本

**设备兼容:**
- PC 端: 完整功能

## 5. 业务规则

### 5.1 数据规则

- Paper.status 只允许 UPLOADING / PROCESSING / PARSED / FAILED
- AnalysisTask.status 只允许 PENDING / RUNNING / SUCCEEDED / FAILED / CANCELLED
- AnalysisTask.progress 必须在 0-100 之间
- ReviewResult.rating 必须在 1-5 之间
- ReviewFinding.confidence 必须在 0.0-1.0 之间
- Evidence.evidence_type 只允许 TEXT / TABLE / FIGURE_CAPTION / EQUATION
- ExportReport.status 只允许 PENDING / GENERATING / READY / FAILED

### 5.2 流程规则

- 当前上传接口创建 Paper 时直接进入 PROCESSING，随后状态流转为 PROCESSING → PARSED / FAILED；UPLOADING 是允许的枚举值，但当前上传路径未使用
- P3.1 审阅生成流程: 同论文 Evidence 稳定排序取 Top-K → E1/E2 alias → MockLLM → 严格 JSON 解析 → 全有或全无 Evidence 绑定 → 原子存储结果与任务成功状态
- P3.2/P3.3 规划: 华为云优先的 Embedding 语义检索 → HuaweiMaaSLLMClient
- 指标提取流程: 从 structured_data 提取 → 规则引擎判断口径 → LLM 辅助歧义消解 → 存储记录

### 5.3 权限规则

- 不同用户的论文和审阅结果严格隔离（user_id 过滤）
- MVP 阶段使用配置项 `demo_user_id` 做数据隔离；Token/JWT 认证尚未实现

## 6. 约束条件

### 6.1 技术约束

- 后端: Python 3.10+ / FastAPI / SQLAlchemy 2.x / Alembic
- 前端: Vue3 / TypeScript / Element Plus（📋 PLANNED） / Pinia / Axios
- 数据库: PostgreSQL 15+
- 向量索引: FAISS（后续可迁移至 Milvus）
- 任务队列: FastAPI BackgroundTasks（后续迁移至 Celery + Redis）

### 6.2 业务约束

- 所有公开审阅结论必须完整绑定 Evidence；无法绑定的记录为 UNVERIFIED 且不展示
- 大模型不直接计算统计数据
- 仅支持包含可提取文本的 PDF
- 文件上传使用普通 multipart 流式上传
- 任务进度通知使用 HTTP 轮询

### 6.3 时间约束

- P2.5（历史）: 论文上传与解析、Evidence 提取已实现
- P3.1（当前）: MockLLM 结构化审阅后端闭环已实现
- P3.2/P3.3（规划）: 华为云优先的语义检索和真实模型接入
- P4.0（规划）: 实验数据分析、报告导出

## 7. 验收标准

### 7.1 功能验收

**已实现（P2.5）:**
- [x] F01 论文上传
- [x] F02 PDF 解析
- [x] F03 表格提取
- [x] F04 文本分块
- [x] F06 Evidence 提取（page-local）

**API 实现状态:**

| 状态 | 接口 |
|------|------|
| ✅ CURRENT | GET /api/v1/health |
| ✅ CURRENT | POST /api/v1/papers/upload（仅 file 字段，title=文件名stem，status=PROCESSING） |
| ✅ CURRENT | GET /api/v1/papers |
| ✅ CURRENT | GET /api/v1/papers/{paper_id} |
| ✅ CURRENT | GET /api/v1/papers/{paper_id}/pages/{page_number} |
| ✅ CURRENT | GET /api/v1/papers/{paper_id}/sections |
| ✅ CURRENT | GET /api/v1/papers/{paper_id}/evidences（无 page_number/evidence_type 过滤） |
| ✅ CURRENT | GET /api/v1/evidences/{evidence_id} |
| ✅ CURRENT | POST /api/v1/papers/{paper_id}/tasks（仅 REVIEW） |
| ✅ CURRENT | GET /api/v1/papers/{paper_id}/tasks |
| ✅ CURRENT | GET /api/v1/tasks/{task_id} |
| ✅ CURRENT | GET /api/v1/papers/{paper_id}/reviews（仅 VERIFIED Finding） |
| 📋 PLANNED | DELETE /api/v1/papers/{paper_id} |
| 📋 PLANNED | GET /api/v1/papers/{paper_id}/tables |
| 📋 PLANNED | POST /api/v1/tasks/{task_id}/cancel |
| 📋 PLANNED | GET /api/v1/papers/{paper_id}/metrics |
| 📋 PLANNED | POST/GET/DELETE /api/v1/papers/{paper_id}/experiment-files/* |
| 📋 PLANNED | POST/GET /api/v1/papers/{paper_id}/exports, GET download |
| 📋 PLANNED | POST /api/v1/papers/{paper_id}/index（FAISS） |

**关键实现细节:**
- SHA-256 哈希已计算并存储，去重/复用逻辑 📋 PLANNED
- 认证: `_get_user_id()` 返回 `settings.demo_user_id`，Bearer/JWT 📋 PLANNED
- Swagger: `/api/docs`，OpenAPI: `/api/openapi.json`

**已实现（P3.1）:**
- [x] F07 结构化论文审阅后端基础闭环

**待实现:**
- [ ] F05 向量索引（FAISS）
- [ ] F07 真实华为云模型、语义检索和审阅前端
- [ ] F08 实验指标提取
- [ ] F09 Checkpoint 口径判断
- [ ] F10 审稿报告导出
- [ ] F11 CSV/Excel 实验数据分析
- [ ] F12 指标交叉验证
- [ ] F13 PDF/DOCX 报告导出

### 7.2 性能验收

- [ ] PDF 解析时间 < 30 秒
- [ ] Evidence 检索时间 < 2 秒
- [ ] API 响应时间 < 500ms

### 7.3 安全验收

- [ ] 文件安全校验通过
- [ ] 用户数据隔离验证通过
- [ ] 错误信息不泄露内部异常
- [ ] 路径穿越防护有效

---

**文档版本**: v1.0
**创建日期**: 2026-07-13
**最后更新**: 2026-07-13
