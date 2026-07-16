# PaperLens - 需求规格说明书

## 文档信息

| 项目 | 内容 |
|------|------|
| 项目名称 | PaperLens |
| 文档版本 | v1.0 |
| 创建日期 | 2026-07-13 |
| 最后更新 | 2026-07-15 |
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
- 任务内 Evidence 语义检索（当前）与持久化向量索引（FAISS/pgvector，规划）
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

- LLM 必须通过统一 LLMClient 接口调用，默认提供 MockLLMClient，并可配置 HuaweiMaaSLLMClient
- 存储层通过 StorageBackend 接口抽象，LocalStorage 为当前实现
- Evidence 采用 page-local 定位，不涉及跨页 span
- 当前审阅链路通过 EmbeddingClient 对 Evidence 做任务内精确余弦检索；持久化索引计划使用 FAISS/pgvector，后续可迁移至 Milvus

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
- P3.2 语义 Evidence 检索和 P3.3 华为云 MaaS 非流式生成式模型适配器均已实现

### 3.4 指标提取与口径判断（P4.1 后端、P4.2 前端已实现）

#### 3.4.1 实验指标提取 (F08)

**功能描述:** 从表格和正文中提取实验指标，记录指标名、值、数据集、模型名。

**功能需求:**
- FR-04.1.1: 从 PaperTable 的 structured_data 中提取指标
- FR-04.1.2: 记录模型名、数据集名、指标名、指标值
- FR-04.1.3: 关联来源 Evidence 和表格行号

**验收标准:**
- 指标记录 API 返回带 task、paper、来源和创建时间的分页结构化数据
- 每条记录且仅绑定表格行或 Evidence；百分号统一存 0～1
- 当前确定性后端不调用 LLM 或真实华为云

#### 3.4.2 Checkpoint 口径判断 (F09)

**功能描述:** 识别 final/max/mean/best 等统计口径并标注。

**功能需求:**
- FR-04.2.1: 基于规则引擎判断 checkpoint_type（关键词匹配 + 上下文分析）
- FR-04.2.2: 标注实际命中来源；冲突和无证据均降级 UNKNOWN
- FR-04.2.3: P4.1 完全离线，LLM 不参与候选、数值或口径生成

**验收标准:**
- 指标记录含 checkpoint_type 和 checkpoint_source
- 不按数值最大推断 BEST/MAX

### 3.5 实验数据分析（P5.3b 前端已实现）

#### 3.5.1 CSV/Excel 实验数据分析 (F11)

**功能描述:** P5.1 已实现 CSV/XLSX/XLS 安全上传和可信结构解析；P5.2 已实现离线确定性统计任务、原子 ExperimentResult 和结果查询 API；P5.3b 已实现完整前端页面与交互。

**功能需求:**
- FR-05.1.1: 支持 CSV / XLSX / XLS 文件上传（最大 20MB）
- FR-05.1.2: 使用只接收服务端路径和确认类型的确定性解析器识别列结构
- FR-05.1.3: 使用确定性 Python 代码计算统计摘要（mean、std、min、max、median）
- FR-05.1.4: LLM 不参与任何数值计算

**验收标准:**
- [x] 实验数据文件可安全上传并得到 version=1 `columns_info`
- [x] 资源按真实用户隔离，重复上传幂等，并发最终一行一对象
- [x] 统计摘要由确定性代码计算（P5.2）
- [x] 前端页面实现非空/20MB 上传预检、分页文件列表、可信详情、分析轮询、统计摘要和交叉验证展示（P5.3b）

#### 3.5.2 指标交叉验证 (F12)

**功能描述:** 对比论文报告指标与实验数据文件中的指标，标记偏差。

**功能需求:**
- FR-05.2.1: 按 NFKC、casefold、字母数字过滤唯一匹配论文 MetricRecord 与数值实验列
- FR-05.2.2: 按 MEAN/MAX 口径计算 `experiment_value - paper_value`、绝对差、相对差和允许差
- FR-05.2.3: 标记 MATCH / MISMATCH / UNVERIFIABLE，BEST/FINAL/LAST/UNKNOWN 不猜测

**验收标准:**
- [x] P5.3a 交叉验证结果可查询，同源幂等且异源不覆盖
- [x] 用户、任务、结果和来源完整性校验通过，所有公开数字有限
- [x] 前端页面默认最新成功指标任务，恢复并锁定已有比较来源，支持交叉验证创建和三类状态展示（P5.3b）

### 3.6 报告导出 (P6.1 Markdown 后端已实现)

#### 3.6.1 审稿报告导出 (F10)

**功能描述:** 导出 Markdown 格式的审阅报告。P6.1 已实现 Markdown 导出后端完整闭环。

**功能需求:**
- FR-06.1.1: 生成包含审阅结果、指标记录的报告
- FR-06.1.2: 支持 Markdown 格式导出
- FR-06.1.3: 支持中英文语言选择（zh/en 模板）
- FR-06.1.4: 创建导出 API（POST /api/v1/papers/{paper_id}/exports），新建 201、幂等 200
- FR-06.1.5: 查询导出状态 API（GET /api/v1/exports/{export_id}）
- FR-06.1.6: 下载导出报告 API（GET /api/v1/exports/{export_id}/download），Content-Type: text/markdown; charset=utf-8，Content-Disposition: attachment，X-Content-Type-Options: nosniff
- FR-06.1.7: Markdown 生成服务：按维度排序审阅详情、可选指标表格、可选实验分析（统计摘要与交叉验证比较）
- FR-06.1.8: 确定性输出：相同输入生成相同字节 + SHA-256 哈希
- FR-06.1.9: HTML/Markdown 转义，禁止输出 storage_key、content_hash、raw_text、内部路径、tokens 等字段
- FR-06.1.10: 状态机 PENDING → GENERATING → READY / FAILED；FAILED 允许重试
- FR-06.1.11: 幂等创建：部分唯一索引 (user_id, paper_id, report_type, language, include_metrics, include_experiment_analysis) WHERE status IN ('PENDING','GENERATING','READY')

**验收标准:**
- [x] 报告可创建、查询状态、下载（P6.1）
- [x] 中英文模板正确渲染（P6.1）
- [x] 确定性输出：相同输入 → 相同字节 + SHA-256（P6.1）
- [x] 禁止字段不出现在导出内容中（P6.1）
- [x] 幂等创建和 FAILED 重试（P6.1）
- [x] 72 生成单元 + 25 API/来源/并发/补偿 + 1 迁移测试通过（P6.1 码道收口）

#### 3.6.2 PDF/DOCX 报告导出 (F13)

**功能描述:** 支持导出为 PDF 和 DOCX 格式。

**功能需求:**
- FR-06.2.1: 支持 PDF 格式导出
- FR-06.2.2: 支持 DOCX 格式导出
- FR-06.2.3: 支持当前论文导出历史分页列表与三格式安全下载
- FR-06.2.4: PDF/DOCX 相同来源与选项生成逐字节一致的文件
- FR-06.2.5: 用户端页面隔离翻页、轮询、路由和下载异步竞态

**验收标准:**
- [x] PDF 中英文文本可由 PyMuPDF 逐字提取，固定元数据且无脚本/附件/动作
- [x] DOCX 可由 python-docx 重开，无宏/OLE/外部 relationship/rsid
- [x] 历史分页、三格式 MIME、轮询、FAILED 重试与 blob URL 回收完成
- [x] 转换器 34、P6.2 API 25、导出页 19 项定向测试通过

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
- Bearer JWT access + 数据库 AuthSession 认证（✅ P3.5 CURRENT）
- P3.5 已实现注册、登录、退出、短时访问令牌、刷新令牌轮换/撤销、密码修改/找回、个人资料和账号状态
- 密码使用可靠自适应哈希，登录和密码流程具备限流、失败锁定与防账号枚举
- USER/ADMIN RBAC 由后端逐接口校验，管理员敏感操作写入审计日志
- 禁止硬编码默认管理员凭据；华为云 IAM 不代替 PaperLens 产品用户系统

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
- ExportReport.language 只允许 'zh' / 'en'
- ExportReport.report_type 只允许 'MARKDOWN' / 'PDF' / 'DOCX'
- ExportReport 幂等约束包含 user_id、paper_id、report_type、language、两个 include 选项、source_hash 和 content_hash，且只覆盖 PENDING/GENERATING/READY

### 5.2 流程规则

- 当前上传接口创建 Paper 时直接进入 PROCESSING，随后状态流转为 PROCESSING → PARSED / FAILED；UPLOADING 是允许的枚举值，但当前上传路径未使用
- P3.3 审阅生成流程: 同论文 Evidence 稳定加载 → 结束只读事务 → Evidence/维度 query Embedding → 精确余弦 Top-K → E1/E2 alias → 根据配置调用 MockLLMClient 或 HuaweiMaaSLLMClient → 严格 JSON 解析 → 全有或全无 Evidence 绑定 → 原子存储结果与任务成功状态
- 指标提取流程: 从 structured_data 提取 → 规则引擎判断口径 → LLM 辅助歧义消解 → 存储记录

### 5.3 权限规则

- 不同用户的论文和审阅结果严格隔离（user_id 过滤）
- `demo_user_id` 仅保留为 disabled legacy 数据占位，不参与运行时认证
- 所有业务资源 user_id 只从认证上下文取得，不接受客户端自报
- 普通用户不能访问管理员 API；管理员数据管理操作必须通过服务端 RBAC 并记录审计
- 不允许删除或降级最后一个有效管理员；首个管理员通过受控初始化流程创建

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
- P3.1（已完成）: MockLLM 结构化审阅后端闭环
- P3.2（已完成）: 华为云优先、接口可替换的 Embedding 与语义 Evidence 检索
- P3.3（当前已完成）: 华为云 MaaS 标准 API V2 非流式生成式模型适配器
- P5.3b（已完成）: 实验数据前端页面与完整交互
- P6.1（已完成）: Markdown 导出报告后端闭环

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
| ✅ CURRENT | POST /api/v1/papers/{paper_id}/tasks（REVIEW / METRIC_EXTRACTION） |
| ✅ CURRENT | GET /api/v1/papers/{paper_id}/tasks |
| ✅ CURRENT | GET /api/v1/tasks/{task_id} |
| ✅ CURRENT | GET /api/v1/papers/{paper_id}/reviews（仅 VERIFIED Finding） |
| 📋 PLANNED | DELETE /api/v1/papers/{paper_id} |
| 📋 PLANNED | GET /api/v1/papers/{paper_id}/tables |
| 📋 PLANNED | POST /api/v1/tasks/{task_id}/cancel |
| ✅ CURRENT | GET /api/v1/papers/{paper_id}/metrics、GET /api/v1/metrics/{metric_id} |
| ✅ CURRENT | P5.1 upload/list/detail；P5.2 POST analysis 与 GET result |
| ✅ CURRENT | P5.3a POST comparisons 与扩展 GET result；P5.3b 实验前端已实现 |
| ✅ CURRENT | P6.1 POST/GET /api/v1/papers/{paper_id}/exports, GET /api/v1/exports/{export_id}/download |
| 📋 PLANNED | POST /api/v1/papers/{paper_id}/index（FAISS） |
| ✅ CURRENT | 注册/登录/刷新/退出、密码重置、个人资料和会话管理 API（P3.5） |
| 📋 PLANNED | 管理员用户/角色、账号状态、资源任务管理和审计日志 API（P7 细化） |

**关键实现细节:**
- SHA-256 哈希已计算并存储，去重/复用逻辑 📋 PLANNED
- 认证: 统一 Bearer JWT + sid/AuthSession/User 校验，refresh 为 HttpOnly cookie（✅ P3.5）
- Swagger: `/api/docs`，OpenAPI: `/api/openapi.json`

**已实现（P3.1～P3.5）:**
- [x] F07 结构化论文审阅后端基础闭环
- [x] F06 按审阅维度的语义 Evidence 检索（Mock/Huawei Embedding、精确余弦 Top-K）
- [x] F07 HuaweiMaaSLLMClient（非流式、严格响应校验、MockTransport 集成与原子失败）
- [x] F07 审阅结果前端与完整任务交互（ReviewResultView、轮询恢复、历史结果归组、Evidence 深链）
- [x] F21 完整用户认证、密码/资料流程、真实资源隔离和 USER/ADMIN RBAC 基础
- [x] F08 可追溯实验指标提取后端、任务闭环与查询 API（P4.1）
- [x] F09 确定性 Checkpoint 口径判断与 UNKNOWN 降级（P4.1）

**已实现（P6.1）:**
- [x] F10 Markdown 审稿报告导出后端（创建/状态/下载 API、zh/en 模板、确定性生成、幂等创建、状态机、安全下载）
- [x] ExportReport 数据模型扩展（010 language/include/source_snapshot；011 source_hash、严格状态/哈希约束与来源感知唯一索引）

**待实现:**
- [ ] F05 向量索引（FAISS）
- [x] F08/F09 指标分析前端页面与交互（P4.2）
- [x] F10 审稿报告导出（P6.1～P6.2）
- [ ] F22 管理员系统
- [x] F11/P5.1 CSV/Excel 安全上传与结构解析
- [x] F11/P5.2 统计摘要
- [x] F12/P5.3a 指标交叉验证后端
- [x] F11/F12 P5.3b 实验数据前端页面与交互（上传、分析轮询、统计摘要、交叉验证）
- [x] F13 PDF/DOCX 报告导出

### 7.2 性能验收

- [ ] PDF 解析时间 < 30 秒
- [ ] Evidence 检索时间 < 2 秒
- [ ] API 响应时间 < 500ms

### 7.3 安全验收

- [ ] 文件安全校验通过
- [x] 用户数据隔离验证通过
- [ ] 错误信息不泄露内部异常
- [ ] 路径穿越防护有效

---

## P4.3 华为云 MaaS LLM 运行配置规格

- Compose 默认 `PAPERLENS_LLM_BACKEND=mock`，只透传六个 LLM 变量，Embedding 固定为 mock。
- `maas-config-check` 只验证配置与 client 可构造性，输出非敏感摘要，不访问网络或数据库。
- `maas-smoke` 必须显式确认计费，只允许 huawei_maas，固定一次短提示并限制 completion 上限。
- SecretStr 不得通过 repr、异常、stdout/stderr 或测试输出泄露；常见占位 Key 必须拒绝。
- 真实账号与计费验收不属于自动测试完成状态。

详细设计见 [design/12-华为云MaaS运行配置.md](design/12-华为云MaaS运行配置.md)。

## 8. 产品方向校正与阅读学习规格

PaperLens 的主产品定义改为“个人论文阅读学习助手”。P2～P6 已实现能力保持兼容：结构化审阅在 UI 和路线图中作为“批判性阅读”，指标、实验与报告作为高级学习工具。不得删除历史模型、路由或用户数据。

### FR-13.1 阅读工作台（P7.1）

- [x] FR-13.1.1 受保护的 `/papers/:id/read` 三栏工作台。
- [x] FR-13.1.2 章节目录、章节正文、页面导航和 Evidence 原文定位。
- [x] FR-13.1.3 论文详情以“开始阅读”为主操作，旧审阅路由保持兼容并显示为“批判性阅读”。
- [x] FR-13.1.4 页面/章节/任务/历史异步请求具有路由代数和卸载清理。

### FR-13.2 证据化学习解释（P7.1）

- [x] FR-13.2.1 SUMMARY / EXPLAIN / TRANSLATE，输出语言 zh / en。
- [x] FR-13.2.2 SECTION / PAGE / EVIDENCE 来源只由服务端读取和校验，客户端不发送正文。
- [x] FR-13.2.3 模型输出为严格单 JSON 对象：answer、key_points、terms、evidence_refs。
- [x] FR-13.2.4 所有 evidence_refs 必须完整绑定同一论文 Evidence；至少一个引用，否则整次失败。
- [x] FR-13.2.5 独立 PENDING → RUNNING → SUCCEEDED / FAILED 状态机，活动/成功同请求幂等，FAILED 可重试。
- [x] FR-13.2.6 结果历史严格分页；响应不泄露正文快照、prompt、hash、模型原始响应或内部异常。

### 固定后续轮次

- P7.2：论文内多轮问答、Evidence 检索、会话历史和证据不足降级。
- P7.3：高亮、书签、笔记、知识卡、论文库标签/搜索和学习进度。
- P8.1：完整管理员后端、页面、用户/角色/状态和不可变审计，一轮合并完成。
- P8.2～P8.4：全链路与恢复、性能可靠性、华为云部署和综合安全。

P7.1 实际验收：Alembic 014、37 条 API、19 张 ORM 应用表、后端 866 passed、前端 183 passed。固定后续轮次均未提前实现。

**文档版本**: v1.5
**创建日期**: 2026-07-13
**最后更新**: 2026-07-15

## 14. 当前论文多轮问答（P7.2）

### FR-14.1 会话与历史

当前用户只能为自己 PARSED 论文创建空会话；会话元数据与轮次均 20 条分页。普通 ADMIN 不绕过业务所有权。

### FR-14.2 证据化生成

服务端只检索当前论文非空 Evidence，历史只包含同会话预算内的成功轮次。`grounded=true` 至少一个 Citation；`grounded=false` 零 Citation 并明确当前论文证据不足。模型返回后必须复算 context_hash。

### FR-14.3 安全交互

客户端只发送 question、zh/en 和 UUID4 client_request_id；模型/用户文本只按纯文本渲染。页面支持新建、双分页、串行轮询、失败新 id 重试和 Citation 原文定位，并隔离论文/会话/页码/轮询竞态。

该段为 P7.2 验收时边界：当时 P7.2 已实现、P7.3 尚未开始。当前 P7.3 已完成；P8.1～P8.4 未提前实现。

## 15. 个人学习沉淀与论文库（P7.3）

### FR-15.1 论文库管理

当前用户论文库列表以全部 Paper 为真集 LEFT JOIN 可选 library entry；无 entry 时返回默认 TO_READ/favorite=false，不为列表读取而写库。Library entry PATCH 只接受 reading_status/favorite/collection_name；extra=forbid；collection_name 空白转 null；COMPLETED 时服务端写 completed_at。

### FR-15.2 阅读进度

Reading progress PATCH 只接受 page_number；upsert entry；TO_READ→READING 自动变；COMPLETED/ARCHIVED 不被自动改写。前端翻页后串行调用 reading-progress。

### FR-15.3 高亮

高亮创建只接受 page_number/char_start/char_end/color；服务端加载 PaperPage 文本校验范围，派生 quoted_text 和 source_hash；不得相信客户端引文。相同 user+paper+page+range 的重复高亮返回既有 200。高亮被 Note 或 Card 引用时删除 409。

### FR-15.4 书签

书签相同页重复返回既有 200+duplicate=true。CRUD 遵循用户隔离。

### FR-15.5 笔记

Note 锚点创建后不可偷换；PAPER 锚点不能有 page_number/highlight_id；PAGE 锚点需要 page_number；HIGHLIGHT 锚点需要 highlight_id。Note 被 Card 引用时删除 409。

### FR-15.6 知识卡

Card source_note_id/source_highlight_id 互斥（含双 null）。Card mastery_status 变化时服务端更新 last_reviewed_at。支持 archived 切换。

### FR-15.7 安全与隔离

所有 P7.3 数据按 user_id 隔离；跨用户不可见不可删。016 迁移空表支持往返；任一 P7.3 表非空时 downgrade 无损中止。

P7.3 已实现。P8.1～P8.4 未提前实现。

## 16. 完整管理员系统与不可变审计（P8.1）

### FR-16.1 管理员仪表盘

GET /api/v1/admin/dashboard 返回用户按 role/status、论文按 status、任务按 task_type/status、报告按 report_type/status 的非负聚合计数，不返回用户内容或最近正文。仅 ADMIN 可访问。

### FR-16.2 用户管理

GET /api/v1/admin/users 列表支持 role/status/q 筛选，q 只匹配规范化 email/display_name。GET /api/v1/admin/users/{user_id} 返回严格白名单字段和资源计数。PATCH /api/v1/admin/users/{user_id} 只接受可选 role USER|ADMIN、可选 status ACTIVE|DISABLED 和必填 reason；extra=forbid；role/status 至少一个。相同值返回 200/changed=false 不写审计。

### FR-16.3 只读治理

GET /api/v1/admin/papers、/admin/tasks、/admin/exports 提供跨用户只读元数据，使用有限列投影，不返回 storage_key/file_hash/source_snapshot/正文/模型输入输出。FAILED 只映射固定安全错误。

### FR-16.4 不可变审计

admin_audit_logs 表 append-only：应用层无 UPDATE/DELETE 路由；PostgreSQL trigger 拒绝 UPDATE/DELETE。action 只允许 ADMIN_BOOTSTRAPPED/USER_ROLE_CHANGED/USER_STATUS_CHANGED；resource_type 只允许 USER。before/after 只允许 role/status。每个实际变化字段各写一条 audit。

### FR-16.5 CLI 初始化

python -m paperlens.cli admin-bootstrap --user-id UUID --reason text：只允许把已存在 ACTIVE 的 USER 提升为首个 ADMIN，且仅当数据库没有 ACTIVE ADMIN 时成功。以目标用户 id 作为 actor_user_id，创建 ADMIN_BOOTSTRAPPED 审计并撤销旧 session，同事务完成。已有 ACTIVE ADMIN、目标非法/不存在/禁用、并发第二次执行都安全失败。

### FR-16.6 安全与并发

禁止管理员自降级或自禁用；任何提交后至少保留一个 ACTIVE ADMIN。FOR UPDATE 锁定 ACTIVE ADMIN 集合和目标。两管理员并发互相降级/禁用时最多一个成功，另一个 409。角色或状态变化后撤销目标全部活动 AuthSession；禁用时同时使未使用 PasswordResetToken 失效。017 迁移空表支持往返，非空审计降级拒绝。

P8.1 进行中。P8.2～P8.4 未提前实现。
