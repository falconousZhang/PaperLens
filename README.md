# PaperLens

AI 驱动的学术论文审阅助手。

## 当前已实现

- 论文上传与 PDF 解析
- 章节结构识别与表格提取
- 文本分块与 page-local Evidence 提取（PyMuPDF block + real bbox）
- 论文列表、详情、页面、章节和 Evidence API
- 可替换的 LLMClient 审阅后端闭环：默认离线 MockLLMClient，可配置 HuaweiMaaSLLMClient（MaaS 标准 API V2、非流式），含任务创建/轮询、严格 JSON 解析、Finding-Evidence 绑定与结果查询
- 可替换的 EmbeddingClient、离线 MockEmbeddingClient、华为云 MaaS Embedding 适配器，以及按审阅维度的 Evidence 精确余弦 Top-K 检索
- Vue 论文上传、列表、详情和审阅结果页面
- REVIEW 任务创建/恢复/轮询、历史结果切换、Finding 筛选和安全错误重试
- 基于 `normalized_text_content` 字符区间的 Evidence 高亮、跨页导航和审阅结果 Evidence 深链
- 完整认证闭环：注册/登录/刷新/登出/改密/找回密码/个人资料，Argon2 密码哈希，JWT access + opaque refresh token（HttpOnly cookie），失败锁定，refresh 单次轮换+重放检测
- 真实用户隔离：所有业务路由要求 Bearer access token，资源按 user_id 归属，USER/ADMIN RBAC 基础
- 可追溯实验指标提取后端：从表格结构化数据和 Evidence 文本中确定性提取指标，百分号统一存为 0～1，无明确 Checkpoint 证据时使用 UNKNOWN；每条记录绑定表格行或 Evidence，并具备并发防重和真实用户隔离
- 指标分析页面：创建/恢复/轮询指标任务，成功历史按 `task_id` 隔离，支持筛选分页、百分比/Checkpoint 展示、来源原文和 Evidence 深链
- PostgreSQL 测试库隔离、Docker Compose 运行环境

## 规划中（尚未实现）

- FAISS/pgvector 持久化向量索引、大规模检索与缓存
- 管理员系统（用户管理、内容审核、审计日志）
- CSV/Excel 统计与指标交叉验证（安全上传与结构解析后端已在 P5.1 完成）
- Markdown/PDF/DOCX 审稿报告导出

## 技术栈

- **前端**：Vue 3 + TypeScript + Vite + Pinia + Vue Router
- **后端**：FastAPI + Python + SQLAlchemy + Alembic
- **数据库**：PostgreSQL
- **LLM**：统一 LLMClient 接口，默认 MockLLMClient，可配置 HuaweiMaaSLLMClient

## 本地开发

### 前置条件

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose（可选，用于 PostgreSQL）

### 1. 启动数据库

```bash
docker compose up postgres -d
```

### 2. 后端

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
alembic upgrade head
uvicorn paperlens.main:app --reload --port 8000
```

### 3. 前端

```bash
cd frontend
npm install
npm run dev
```

### 4. Docker Compose 一键启动

```bash
python scripts/ensure_local_env.py
docker compose up --build
```

`PAPERLENS_JWT_SECRET` 是必填配置且至少 32 字节。上述脚本只在被 Git 忽略的本地 `.env` 中生成随机值，不会显示密钥；生产环境应由部署平台注入，并保持 `PAPERLENS_AUTH_COOKIE_SECURE=true`。本地 HTTP 开发可显式设为 `false`。

## API 文档

后端启动后访问 `http://localhost:8000/api/docs` 查看 Swagger 文档。

## LLM 配置

默认 `PAPERLENS_LLM_BACKEND=mock`，无需密钥且完全离线。启用华为云 MaaS 标准 API V2 适配器时，在本地 `.env` 或部署环境中设置：

```dotenv
PAPERLENS_LLM_BACKEND=huawei_maas
PAPERLENS_LLM_BASE_URL=https://api.modelarts-maas.com/v2
PAPERLENS_LLM_MODEL=glm-5.2
PAPERLENS_LLM_API_KEY=
PAPERLENS_LLM_TIMEOUT_SECONDS=60
PAPERLENS_LLM_MAX_COMPLETION_TOKENS=2048
```

**启用步骤**：

1. 在华为云目标 Region 开通 ModelArts Studio 服务并创建最小权限 API Key
2. 立即安全保存只显示一次的 Key，写入本地被 Git 忽略的 `.env`
3. 运行 `docker compose up -d --build --force-recreate backend`，让 backend 加载新的本地配置
4. 运行 `docker compose exec -T backend python -m paperlens.cli maas-config-check` 验证配置，确认输出 `backend: huawei_maas`、`api_key_configured: true` 和 `OK`
5. 用户明确确认计费后手工运行 `docker compose exec backend python -m paperlens.cli maas-smoke --confirm-billable`

**安全须知**：API Key 与 Region/服务权限相关；优先自定义最小访问范围/IP 白名单；删除 Key 后立即失效；不要把 Key 粘贴到聊天、提示词、命令参数、截图、日志或 Git。base URL 从控制台"调用说明"复制，去掉末尾 `/chat/completions`；不同 Region/服务可能使用 `/v1`、`/v2` 或区域域名，项目不替用户选择付费模型。

当前仅实现 `stream=false` 的 `/chat/completions`，不自动重试，不支持流式、工具调用或联网搜索。Docker Compose 默认 mock 模式，Embedding 强制保持 mock。2026-07-14 已在用户明确授权下完成华为云 `glm-5.2` 最小真实烟测；这只验证当前账号与模型的连通性，不代表长文本审阅质量或生产费用已验收。

## Embedding 配置

默认 `PAPERLENS_EMBEDDING_PROVIDER=mock`，完全离线运行。启用华为云 MaaS 文本向量化适配器时，在本地 `.env` 或部署环境中设置：

```dotenv
PAPERLENS_EMBEDDING_PROVIDER=huawei_maas
PAPERLENS_EMBEDDING_BASE_URL=https://api.modelarts-maas.com/v1
PAPERLENS_EMBEDDING_MODEL=bge-m3
PAPERLENS_EMBEDDING_API_KEY=由用户环境安全注入
PAPERLENS_EMBEDDING_TIMEOUT_SECONDS=30
PAPERLENS_EMBEDDING_BATCH_SIZE=32
```

不要把真实 API Key 写入 `.env.example` 或提交到仓库。模型、区域和服务可用性以用户实际开通时的华为云控制台与官方文档为准；自动测试不会访问华为云。

## 测试

Docker 后端测试强制使用独立的 `paperlens_test` 数据库；数据库连接、迁移或清理失败会直接使测试失败，不会回退到开发库或静默跳过。

```bash
docker compose exec -T backend python -m pytest -q -rs
cd frontend
npm test -- --run
npm run build
```

当前 P5.1：CSV/XLSX/XLS 安全上传、结构解析、列表和详情后端已完成；P5.1 解析/存储/API 定向 `103 passed`，P4.3/MaaS/审阅广义定向 `180 passed`，P4.1 指标定向 `67 passed`，Docker 后端全量 `527 passed`，均为 0 skipped；前端 `106 passed`，生产构建 126 modules。008 已验证冲突只读中止和 007↔008 可逆。统计、ExperimentResult、交叉验证和实验前端仍未实现。真实 `glm-5.2` 最小烟测已成功，长文本质量和生产费用仍未验收。

## 项目结构

```
PaperLens/
├── docs/                    # 设计文档
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── api/             # REST API 路由
│   │   ├── core/            # 配置、数据库、错误处理
│   │   ├── models/          # SQLAlchemy ORM 模型
│   │   ├── schemas/         # Pydantic 请求/响应模型
│   │   ├── services/        # 业务逻辑
│   │   └── utils/           # 工具函数
│   ├── alembic/             # 数据库迁移
│   └── tests/               # 测试
├── frontend/                # 前端服务
│   └── src/
│       ├── api/             # API 请求封装
│       ├── views/           # 页面视图
│       ├── stores/          # Pinia 状态管理
│       └── router/          # 路由配置
├── docker-compose.yml
└── .env.example
```

## MVP 约束

- 仅支持包含可提取文本的 PDF，不支持扫描型 PDF / OCR
- 文件上传使用普通 multipart 流式上传，暂不实现分片上传
- 上传大小限制：Nginx client_max_body_size 60MB，后端 MAX_UPLOAD_SIZE 50MB
- 任务进度通知使用 HTTP 轮询，暂不实现 WebSocket
- 后台任务使用 FastAPI BackgroundTasks（仅 MVP，非生产级），暂不引入 Celery + Redis
- LLM 默认使用 MockLLMClient，无需云端密钥即可运行；HuaweiMaaSLLMClient 已完成最小真实连通性烟测，但模型质量、长文本效果和生产费用未在自动测试中验证
- 存储使用 LocalStorage（OBSStorage 为后续云端部署方案，未实现）
- 当前语义检索是任务内对同论文 Evidence 做即时 Embedding 和精确余弦 Top-K，不是 FAISS/pgvector 持久化索引；默认使用离线 MockEmbeddingClient，可配置华为云 MaaS Embedding 适配器
- 当前 Evidence 高亮基于 normalized 页面文本字符区间，不是 PDF.js/bbox 覆盖层
- 所有数值统计由确定性 Python 代码完成，大模型不直接计算
