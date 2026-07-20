# PaperLens 架构设计文档

## 1. 系统上下文图

```
┌─────────────────────────────────────────────────────────────┐
│                        外部系统                              │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │  用户浏览器 │  │  OBS 存储  │  │  RDS 数据库│  │ModelArts │  │
│  │  (前端SPA) │  │ (文件存储) │  │ (PostgreSQL)│ │ (LLM推理) │  │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  │
│        │              │              │              │         │
└────────┼──────────────┼──────────────┼──────────────┼─────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────┐
│                     PaperLens 系统                           │
│                                                             │
│  ┌─────────────────┐    ┌──────────────────────────────┐   │
│  │   前端 (Vue3)    │    │       后端 (FastAPI)          │   │
│  │                 │    │                              │   │
│  │  - 论文上传页面  │    │  ┌────────┐  ┌───────────┐  │   │
│  │  - 审阅结果页面  │◄──►│  │ API 层  │  │ 任务调度层 │  │   │
│  │  - 指标分析页面  │    │  └───┬────┘  └─────┬─────┘  │   │
│  │  - 报告导出页面  │    │      │             │        │   │
│  └─────────────────┘    │  ┌───▼─────────────▼────┐   │   │
│                         │  │      业务逻辑层        │   │   │
│                         │  │  - PDF解析  - 分块索引  │   │   │
│                         │  │  - 审阅生成  - 指标提取  │   │   │
│                         │  │  - 报告导出            │   │   │
│                         │  └───────────┬───────────┘   │   │
│                         │              │               │   │
│                         │  ┌───────────▼───────────┐   │   │
│                         │  │      数据访问层         │   │   │
│                         │  └───────────┬───────────┘   │   │
│                         └──────────────┼───────────────┘   │
└────────────────────────────────────────┼────────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    ▼                    ▼                    ▼
              ┌──────────┐        ┌──────────┐        ┌──────────┐
              │   OBS    │        │   RDS    │        │ModelArts │
              │  文件存储  │        │  元数据   │        │ LLM 推理  │
              └──────────┘        └──────────┘        └──────────┘
```

## 2. 前后端架构

### 2.1 前端架构（Vue3 + TypeScript）

```
frontend/
├── src/
│   ├── api/              # API 请求封装
│   ├── components/       # 通用组件
│   ├── views/            # 页面视图
│   │   ├── HomeView      # 首页
│   │   ├── UploadView    # 论文上传
│   │   ├── ReviewResultView # 审阅结果
│   │   ├── MetricsView   # 指标分析
│   │   └── ExportView    # 报告导出
│   ├── stores/           # Pinia 状态管理
│   ├── router/           # 路由配置
│   └── utils/            # 工具函数
```

前端职责：
- 文件上传（multipart 流式上传，最大 50MB）
- 展示论文解析结果与 Evidence 定位（当前基于 `normalized_text_content` 字符区间高亮，不是 PDF.js/bbox 覆盖层）
- 展示审阅结果、任务进度、Finding 筛选与 Evidence 深链；指标表格和统计口径标注仍在规划
- 创建 Markdown/PDF/DOCX 报告、分页查看历史、轮询状态并安全下载（P6.2 已实现）
- 后端不可用时显示明确错误

### 2.2 后端架构（FastAPI + Python）

```
backend/
├── app/
│   ├── api/              # REST API 路由
│   ├── core/             # 配置、安全、依赖注入
│   ├── models/           # SQLAlchemy ORM 模型
│   ├── schemas/          # Pydantic 请求/响应模型
│   ├── services/         # 业务逻辑
│   │   ├── pdf_parser    # PDF 解析服务
│   │   ├── chunker       # 文本分块服务
│   │   ├── embedder      # 向量化服务
│   │   ├── retriever     # 证据检索服务
│   │   ├── reviewer      # 审阅生成服务
│   │   ├── metric_extractor  # 指标提取服务
│   │   ├── experiment_file_parser/service  # P5.1 安全上传与结构解析
│   │   └── exporter      # 报告导出服务
│   ├── tasks/            # 后台任务定义
│   └── utils/            # 工具函数
```

后端职责：
- 文件接收与校验
- PDF 解析与结构化
- 文本分块与 page-local Evidence 提取（已实现）
- Embedding 抽象与语义 Evidence 检索（已实现，默认 MockEmbedding，华为云 MaaS 适配器已就绪）
- 向量索引与持久化（规划，FAISS/pgvector，尚未实现）
- 通过可替换 LLMClient 生成结构化审阅意见（已实现，默认 Mock、可配置华为 MaaS）
- 可追溯指标提取、实验分析和三格式报告导出均已实现；确定性链路不调用 LLM/Embedding

### 2.3 LLM 调用抽象

LLM 必须通过统一 `LLMClient` 接口调用：

```python
class LLMClient(ABC):
    @abstractmethod
    def chat(self, messages: list[dict], **kwargs) -> dict: ...

class MockLLMClient(LLMClient):
    """默认实现，返回固定结构化响应，无需云端密钥即可演示"""

class HuaweiMaaSLLMClient(LLMClient):
    """华为云 MaaS 标准 API V2 适配器，httpx 同步调用，非流式，transport 可注入"""
```

当前默认 `PAPERLENS_LLM_BACKEND=mock`；华为云 MaaS 适配器已实现但需配置 API Key 启用。所有配置/网络/HTTP/JSON/响应错误统一转为安全 LLMError，不泄漏 Key 或上游响应。

### 2.4 Embedding 调用抽象

Embedding 必须通过统一 `EmbeddingClient` 接口调用：

```python
class EmbeddingClient(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...

class MockEmbeddingClient(EmbeddingClient):
    """默认实现，基于词项 hashing/bag-of-words，确定性、归一化"""

class HuaweiMaaSEmbeddingClient(EmbeddingClient):
    """华为云 MaaS Embedding 适配器，httpx 同步调用，batch 分割，transport 可注入"""
```

当前默认 `PAPERLENS_EMBEDDING_PROVIDER=mock`；华为云 MaaS 适配器已实现但需配置 API Key 启用。FAISS/pgvector 向量数据库为 PLANNED。

## 3. 后台任务处理流程

> 当前已完成 PDF 解析、page-local Evidence、结构化审阅、指标与实验分析、Markdown/PDF/DOCX 报告闭环，以及华为云 MaaS 标准 API V2 适配器。FAISS/pgvector 持久化向量数据库仍未实现。

```
用户上传 PDF
     │
     ▼
┌─────────────┐
│ 1. 文件校验  │  类型检查、大小限制、路径穿越检测
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 2. 存储到本地  │  原始 PDF 存入本地存储，记录 Paper 记录到 RDS
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 3. PDF 解析  │  提取文本、页面、章节结构、表格
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 4. 文本分块  │  按章节/段落分块，生成 PaperChunk 记录
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 5. 向量索引  │  调用 Embedding 模型，索引到向量数据库
└──────┬──────┘
       │
       ├──────────────────────────────┐
       ▼                              ▼
┌─────────────┐                ┌─────────────┐
│ 6a. 审阅生成 │                │ 6b. 指标提取  │
│              │                │              │
│ - 构造Prompt │                │ - 表格解析    │
│ - 检索Evidence│               │ - 口径判断    │
│ - 调用LLM    │                │ - 确定性计算  │
│ - 绑定Evidence│               │              │
└──────┬──────┘                └──────┬──────┘
       │                              │
       └──────────────┬───────────────┘
                      │
                      ▼
              ┌─────────────┐
              │ 7. 结果存储  │  ReviewResult + ReviewFinding + Evidence 写入 RDS
              └──────┬──────┘
                     │
                     ▼
              ┌─────────────┐
              │ 8. 通知前端  │  HTTP 轮询通知任务完成
              └─────────────┘
```

### 任务状态机

```
PENDING → RUNNING → SUCCEEDED
                 → FAILED
                 → CANCELLED
```

每个 AnalysisTask 记录包含：
- task_type: REVIEW / METRIC_EXTRACTION / EXPERIMENT_ANALYSIS
- status: PENDING / RUNNING / SUCCEEDED / FAILED / CANCELLED
- progress: 0-100 百分比
- error_message: 失败原因

## 4. OBS、RDS、ModelArts、ECS 之间的数据流

```
┌──────────────────────────────────────────────────────────────────┐
│                          ECS (后端服务)                           │
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ 文件上传   │    │ PDF解析   │    │ 审阅生成   │    │ 指标提取   │  │
│  │ Handler  │    │ Service  │    │ Service  │    │ Service  │  │
│  └──┬───┬───┘    └──┬───┬───┘    └──┬───┬───┘    └──┬───┬───┘  │
│     │   │           │   │           │   │           │   │       │
└─────┼───┼───────────┼───┼───────────┼───┼───────────┼───┼───────┘
      │   │           │   │           │   │           │   │
      │   ▼           │   ▼           │   │           │   │
      │ ┌─────────┐   │ ┌─────────┐   │   │           │   │
      │ │  OBS    │   │ │  OBS    │   │   │           │   │
      │ │ 原始PDF  │   │ │ 解析结果 │   │   │           │   │
      │ └─────────┘   │ └─────────┘   │   │           │   │
      │               │               │   │           │   │
      ▼               ▼               ▼   ▼           ▼   ▼
    ┌─────────────────────────────────────────────────────────┐
    │                    RDS (PostgreSQL)                      │
    │                                                         │
    │  Paper │ PaperPage │ PaperSection │ PaperChunk          │
    │  PaperTable │ Evidence │ AnalysisTask                    │
    │  ReviewResult │ ReviewFinding │ MetricRecord             │
    │  ExperimentFile │ ExperimentResult │ ExportReport        │
    └─────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                              ┌──────────┐
                              │ModelArts │
                              │          │
                              │ - Embedding 推理  │
                              │ - Chat 推理       │
                              └──────────┘
```

### 数据流说明

> 步骤 1～5 为当前解析闭环；步骤 6～14 是后续阶段规划。

| 步骤 | 源 | 目标 | 数据 | 说明 |
|------|----|------|------|------|
| 1 | 用户 | ECS | PDF 文件 | HTTP multipart 上传 |
| 2 | ECS | OBS | PDF 原文 | 存储原始文件 |
| 3 | ECS | RDS | Paper 元数据 | 记录文件信息 |
| 4 | ECS | OBS | 解析后文本/表格 | 存储中间结果 |
| 5 | ECS | RDS | PaperPage/PaperSection/PaperChunk/PaperTable | 结构化数据 |
| 6 | ECS | ModelArts | 文本块 | Embedding 向量化 |
| 7 | ECS | RDS | 向量索引引用 | 存储向量 ID |
| 8 | ECS | ModelArts | Prompt + Evidence | Chat 推理生成审阅 |
| 9 | ECS | RDS | ReviewResult + ReviewFinding + Evidence | 审阅结果与证据绑定 |
| 10 | ECS | RDS | MetricRecord | 指标提取结果 |
| 11 | 用户 | ECS | CSV/XLSX/XLS | P5.1 固定块临时落盘和认证校验 |
| 12 | ECS worker | ECS | 临时路径 | magic/ZIP/OLE 安全、SHA-256、确定性结构解析 |
| 13 | ECS | LocalStorage/OBS + RDS | source.ext + ExperimentFile | 幂等保存和失败补偿；P8.4 OBSStorage 已实现 |
| 14 | ECS | RDS | ExperimentResult | P5.2 确定性流式统计与原子结果已实现 |
| 15 | ECS | 用户 | 导出报告 | P6.2 三格式历史分页与安全下载已实现 |

## 5. 本地开发与云端部署的差异

| 维度 | 本地开发 | 云端部署 |
|------|---------|---------|
| 文件存储 | 本地文件系统 `./data/` | 已实现的华为云 OBSStorage（ECS Agency/ENV、私有 SSE） |
| 数据库 | 本地 PostgreSQL（Docker Compose） | 华为云 RDS PostgreSQL |
| Evidence 检索 | MockEmbeddingClient + 任务内精确余弦 Top-K | 可配置华为云 MaaS Embedding；持久化 FAISS/pgvector 仍为规划 |
| LLM 推理 | MockLLMClient 结构化审阅闭环；HuaweiMaaSLLMClient 已实现需配置 API Key 启用 | 华为云 MaaS 标准 API V2 |
| PDF 解析 | 本地 PyMuPDF / pdfplumber | 同左（ECS 上运行） |
| 任务队列 | FastAPI BackgroundTasks + P8.2 安全恢复 | 同左；多实例队列仍为可选增强 |
| 前端 | Vite dev server | Nginx 静态托管 |
| HTTPS | 无（HTTP localhost） | 华为云 ELB + SSL 证书 |
| 认证 | JWT access + HttpOnly refresh cookie | 同左；DEW/文件 Secret 注入 |
| 日志 | 安全结构化控制台日志 | 可由容器平台采集到 LTS |

### 环境配置策略

- 通过环境变量 `PAPERLENS_ENV=local|test|production` 切换
- 存储层抽象：`StorageBackend` 支持 LocalStorage 与 OBSStorage，下载统一使用 `materialize`
- 数据库：SQLAlchemy 统一 ORM，通过 `PAPERLENS_DATABASE_URL` 切换；生产强制 RDS verify-full + CA
- LLM：统一 `LLMClient`，通过 `PAPERLENS_LLM_BACKEND` 切换；生产强制 Huawei MaaS

P8.4 生产资产见 `deploy/huawei/`：仅发布非 root Nginx 8080，backend 位于固定 Compose 私网；migrate/serve 共用 Secret 文件入口，两类镜像均使用只读根文件系统和最小能力集。

## 6. 关键设计决策

### 6.1 向量索引规划（尚未实现）

计划选择 FAISS 而非独立向量数据库（如 Milvus），原因：
- MVP 阶段数据量可控（单篇论文 ~数百 chunk）
- 避免引入额外基础设施依赖
- FAISS 索引可序列化到 OBS 持久化

后续可迁移至 Milvus / OpenSearch 向量检索。

### 6.2 审阅生成的 Evidence 绑定机制

```
1. 根据审阅维度构造检索 query（build_dimension_query，含中英文维度术语）
2. 使用 EmbeddingClient 将 query 和 Evidence 文本向量化
3. 计算 cosine similarity 排序，取 Top-K 相关 Evidence
4. 将 Evidence 内容以别名（E1/E2/…）传入 Prompt
5. 要求 LLM 在输出中标注引用的 Evidence 别名
6. 后处理验证：每条 ReviewFinding 必须关联至少一个 Evidence 别名
7. 未关联 Evidence 的 Finding 标记为 verification_status=UNVERIFIED，不展示给用户
```

当前使用 MockEmbeddingClient（词项 hashing/bag-of-words），华为云 MaaS Embedding 适配器已就绪（需配置 API Key）。
当前实现直接读取同论文 Evidence，在一次任务中将 Evidence 文本只向量化一次，再对各维度查询分别排序；没有写入 `PaperChunk.embedding_id`，也没有持久化向量索引。

### 6.3 指标提取的确定性保证

- 从已持久化 PaperTable 与 Evidence 创建来源快照，结束读事务后执行纯 Python 解析，不依赖 LLM
- 百分号统一存 0～1；非百分比指标允许有限负数，范围、均值±误差和非有限值拒绝
- Checkpoint 只按完整关键词及当前 caption/行标签/Evidence 判断；冲突或无证据为 UNKNOWN
- 每条记录绑定表格行或 Evidence，并在原子写入前复核 task/paper/user/source
- P4.1 不使用 pandas/numpy，也不调用 LLMClient、EmbeddingClient 或外部网络

### 6.4 MVP 范围约束

- 仅支持包含可提取文本的 PDF，不支持扫描型 PDF / OCR
- 文件上传使用普通 multipart 流式上传，暂不实现分片上传
- 任务进度通知使用 HTTP 轮询，暂不实现 WebSocket
- 后台任务使用 FastAPI BackgroundTasks（仅 MVP 阶段，非生产级方案），暂不引入 Celery + Redis

### 6.5 P4.3 MaaS 运行开关

- Compose 默认使用 MockLLMClient，只逐项透传 LLM backend/base URL/model/API Key/timeout/max tokens。
- Embedding 在 LLM 首次真实验收前强制为 mock，避免意外双重计费。
- `maas-config-check` 只验证配置；`maas-smoke --confirm-billable` 才允许一次最多 32 completion token 的真实请求。
- Compose 源文件只读挂载到 backend，仅供 Docker 测试核对实际配置，文件中不含展开后的 secret。

### 6.6 P5.3a 确定性交叉验证

交叉验证服务位于独立 `experiment_comparison_service`。API 只传入文件和指标任务 id；服务锁定 ExperimentResult，复核文件、论文、用户、分析任务、指标任务、记录和来源后，使用结构化 summary_stats 完成纯 Python 比较。

名称匹配不使用 LLM、Embedding 或模糊算法。MetricRecord.raw_text 延迟加载，PaperTable/Evidence 只投影 id 与 paper_id；服务不访问实验 storage。结果以严格 JSONB 数组写回，行锁负责同源/异源竞争，独立 Session 负责提交结果未知恢复。

### 6.7 P5.3b 实验数据前端编排

ExperimentDataView 只组合现有 Paper、Task、ExperimentFile、ExperimentResult 和 comparison API。文件列表分页，选择文件后并行读取可信 columns_info 与已有结果；统计任务以 3 秒 HTTP 轮询观察。页面代数、文件选择代数和明确的 paper/file/task 校验共同隔离陈旧响应。已有比较直接恢复并锁定来源；未知错误映射为固定公开文案。该阶段不新增后端组件、数据库迁移、任务队列或云端调用。

### 6.8 P6.1 Markdown 导出闭环

创建接口先复核 ReviewResult/Finding/Evidence、MetricRecord/source、ExperimentResult/File/AnalysisTask 的完整用户与论文关系，再形成只含 id 的 source_snapshot。Markdown bytes、content_hash 与 source_hash 均在插入 PENDING 前确定；后台任务通过条件 UPDATE 原子认领，并只保存创建时 bytes，不重新查询“最新来源”。

存储后必须通过 StorageBackend 回读并逐字节复核，再原子提交 READY。提交结果未知时用独立 Session 确认 READY 归属；否则清理未归属对象并安全 FAILED。FastAPI BackgroundTasks 仍不是持久化队列，进程重启恢复留 P8。

### 6.9 P6.2 多格式报告与用户端闭环

PDF/DOCX 由 P6.1 创建时 Markdown bytes 离线转换，不重新查询数据库。PDF 使用 ReportLab invariant 模式与内置 STSong-Light CID 字体，固定元数据并由 PyMuPDF 验证中英文提取；DOCX 使用 python-docx 后按固定 entry 顺序、时间和权限重打包，清除 rsid，并拒绝宏、OLE、嵌入对象与外部 relationship。

012 只扩展来源行格式约束，三格式复用同一来源感知幂等索引和状态机。ReportExportView 通过当前论文历史接口执行 20 条分页和状态轮询，以请求代数隔离路由/翻页乱序响应；READY 文件通过 blob 下载并在所有路径回收对象 URL。

### 6.10 产品方向校正与 P7.1 阅读学习架构

PaperLens 的主产品定义改为个人论文阅读学习助手。现有 reviewer、metric、experiment 和 export 模块保持兼容，分别作为批判性阅读、实验理解和学习成果导出能力。P7.1 新增独立 learning service，不把学习解释写入 ReviewResult，也不继续使用评分/审稿结论作为主页面语义。

阅读工作台复用 Paper/Section/Page/Evidence API，并通过独立 LearningExplanation 状态机调用统一 LLMClient。服务端根据 section/page/evidence id 获取不可信论文内容，确定性选择候选 Evidence，模型返回严格 JSON，全部 alias 校验成功后才原子写入结果与 Citation。外部模型调用期间不持有数据库事务；自动测试只使用 Mock。

P7.2 在同一证据边界上增加论文内问答，P7.3 增加个人学习记录。完整管理员系统重排到 P8.1 合并交付，剩余轮次总数不变。

P7.1 已实现：013 建表后由 014 无损收紧契约；创建前和模型返回后都复核 canonical scope、来源及 Evidence 指纹；推理期间没有数据库事务；结果与 Citation 原子提交。PaperReadingView 对 paper/page/history/explanation/poll 分别做竞态隔离。

## P7.2 当前论文问答架构（COMPLETED）

015 新增 conversation/turn/citation 三表和独立 qa router/schema/service/retriever。问题创建在同步事务中完成 owner、PARSED、非空 Evidence、UUID 幂等与活动轮次门禁；后台条件认领后关闭事务，批量嵌入问题和当前论文 Evidence，严格验证向量并确定性 Top-K。预算内历史与候选来源组成 context_hash，LLM 返回后锁定 Turn、重新加载全图并复算，匹配后才原子保存 grounded 结果与 Citation。

前端继续使用 PaperReadingView，通过会话/轮次真实分页、3 秒串行轮询、失败新 id 重试和 Citation 原文定位完成闭环；paper/conversation/turn/action/poll 分别做竞态隔离。自动测试只使用 Mock，不访问真实云端。

## P7.3 个人学习沉淀架构（COMPLETED）

016 新增论文库条目、高亮、书签、笔记和知识卡五表。library router 使用全部 owner Paper LEFT JOIN 可选 entry，并在同一查询中计算四类记录数；默认 TO_READ/favorite=false 不排除尚无 entry 的论文。personal_learning router 统一复核 owner、PARSED、PaperPage 和来源全图，所有写入为确定性数据库逻辑，不构造 LLM/Embedding client。

PaperListView 提供搜索、状态/收藏/集合过滤、进度与四类计数；PaperReadingView 的学习记录区分别维护高亮、书签、笔记和知识卡分页与请求代数。高亮只从服务端 Page 文本派生，浏览器选区通过跨文本节点偏移解析与原文切片复核，来源变化时降级而不是错误标注。

## P8.1 管理员系统架构（COMPLETED）

017 新增 append-only `admin_audit_logs`。首次引导与管理员集合变更先取得 PostgreSQL 事务级 advisory lock，再按 id 锁定 ACTIVE ADMIN、操作者和目标并重新校验权限；用户状态、角色、AuthSession/PasswordResetToken 失效和逐字段审计在同一事务提交。提交结果未知时以预生成 audit id 回查最终状态，避免重复写入。

8 条 `/admin` API 与普通 owner-only API 完全分离。用户资源计数使用相关子查询，论文与审计使用 JOIN 和有限列投影，任务/报告不加载模型输出、原始错误、source_snapshot 或 storage 字段。Vue 管理页以一级区域和内容子页签的请求代数隔离快速切换，服务端错误只映射固定安全文案。

## P8.2 后台任务恢复架构（已完成）

新增 `RecoveryService`，在 FastAPI lifespan startup 执行一次有限扫描。扫描事务使用 `pg_try_advisory_xact_lock` 非阻塞互斥，按固定实体顺序、created_at/id 和默认 50 行批次加 `FOR UPDATE SKIP LOCKED`；提交后才派发 worker，因此 PDF、模型、文件和报告处理不持有扫描事务或全局锁。

指标、实验分析、学习解释和问答复用现有原子 claim 重放；审阅缺少原始 options、论文解析缺少可靠执行代次、导出缺少生成 bytes 时固定 FAILED，由用户从原入口重试。前端七类轮询实际复用共享 usePolling。TaskDetail 增加可空 `experiment_file_id`，用于刷新后恢复实验文件上下文；无新路由或迁移。

## P8.3 运行可靠性架构（已完成）

`RequestTracingMiddleware` 位于限流外层，严格复用规范 UUID4，并为成功、错误和 429 响应添加 `X-Request-ID`。请求日志只使用路由模板；未匹配或路由前返回统一记 `<unmatched>`，不记录原始路径、查询、IP、头或正文。

`RateLimitMiddleware` 使用单调时钟、有限 key 容量和真实固定窗口，按 auth/upload/read/write 分组，health 豁免。默认以 TCP peer 为 key；仅显式可信 CIDR 的直接代理可解析 X-Forwarded-For。该实现只提供单进程防护，多实例总限流留给 P8.4 华为云入口层。

数据库 engine 共用有界 pool 构造参数。恢复扫描提交后通过 lifespan 管理的 ThreadPoolExecutor 派发，shutdown 取消排队任务并等待已运行任务结束；任务记录仍由原有 claim/恢复状态机保证一致性。
