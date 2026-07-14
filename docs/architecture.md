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
- 触发报告导出并下载（规划，尚未实现）
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
- 可追溯指标提取后端（P4.1 已实现，完全离线）；指标前端、实验分析和报告导出仍为规划

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

> 当前已完成 PDF 解析、page-local Evidence 提取、基于 MockLLM 的结构化审阅后端闭环、基于 Embedding 抽象的语义 Evidence 检索，以及华为云 MaaS 标准 API V2 的 LLM 适配器。FAISS/pgvector 向量数据库、指标分析和报告导出尚未实现。

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
| 13 | ECS | LocalStorage/OBS 抽象 + RDS | source.ext + ExperimentFile | 幂等保存和失败补偿；OBS 实现仍规划 |
| 14 | ECS | RDS | ExperimentResult | P5.2 确定性统计结果，尚未实现 |
| 15 | ECS | 用户 | 导出报告 | 报告下载（规划） |

## 5. 本地开发与云端部署的差异

| 维度 | 本地开发 | 云端部署 |
|------|---------|---------|
| 文件存储 | 本地文件系统 `./data/uploads/` | 华为云 OBS（OBSStorage 未实现，后续版本） |
| 数据库 | 本地 PostgreSQL（Docker Compose） | 华为云 RDS PostgreSQL |
| Evidence 检索 | MockEmbeddingClient + 任务内精确余弦 Top-K | 可配置华为云 MaaS Embedding；持久化 FAISS/pgvector 仍为规划 |
| LLM 推理 | MockLLMClient 结构化审阅闭环；HuaweiMaaSLLMClient 已实现需配置 API Key 启用 | 华为云 MaaS 标准 API V2 |
| PDF 解析 | 本地 PyMuPDF / pdfplumber | 同左（ECS 上运行） |
| 任务队列 | FastAPI BackgroundTasks（MVP，非生产级） | Celery + Redis（后续版本） |
| 前端 | Vite dev server | Nginx 静态托管 |
| HTTPS | 无（HTTP localhost） | 华为云 ELB + SSL 证书 |
| 认证 | 无 / 简单 Token | IAM 集成 / JWT |
| 日志 | 控制台输出 | 云日志服务 LTS |

### 环境配置策略

- 通过环境变量 `PAPERLENS_ENV=local|cloud` 切换
- 存储层抽象：`StorageBackend` 接口，`LocalStorage` 为当前实现，`OBSStorage` 为后续云端部署实现（未实现）
- 数据库：SQLAlchemy 统一 ORM，通过 `DATABASE_URL` 切换，统一使用 PostgreSQL
- LLM：统一 `LLMClient` 接口，通过 `LLM_BACKEND` 切换（mock / huawei_maas）

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
