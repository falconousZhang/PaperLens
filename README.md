# PaperLens

AI 驱动的学术论文审阅助手。

## 当前已实现

- 论文上传与 PDF 解析
- 章节结构识别与表格提取
- 文本分块与 page-local Evidence 提取（PyMuPDF block + real bbox）
- 论文列表、详情、页面、章节和 Evidence API
- Vue 论文上传、列表和详情页面
- 基于 `normalized_text_content` 字符区间的 Evidence 高亮与跨页导航
- PostgreSQL 测试库隔离、Docker Compose 运行环境

## 规划中（尚未实现）

- FAISS 向量索引和语义 Evidence 检索
- LLM 结构化论文审阅与 ReviewFinding 绑定
- 实验指标提取、checkpoint 口径判断和 CSV/Excel 分析
- Markdown/PDF/DOCX 审稿报告导出

## 技术栈

- **前端**：Vue 3 + TypeScript + Vite + Pinia + Vue Router
- **后端**：FastAPI + Python + SQLAlchemy + Alembic
- **数据库**：PostgreSQL
- **LLM**：统一 LLMClient 接口，默认 MockLLMClient

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
docker compose up --build
```

## API 文档

后端启动后访问 `http://localhost:8000/api/docs` 查看 Swagger 文档。

## 测试

Docker 后端测试强制使用独立的 `paperlens_test` 数据库；数据库连接、迁移或清理失败会直接使测试失败，不会回退到开发库或静默跳过。

```bash
docker compose exec -T backend python -m pytest -q -rs
cd frontend
npm test -- --run
npm run build
```

当前 P2.5 验收结果：Docker 后端 `63 passed, 0 skipped`，前端 `15 passed`，Alembic 无未生成差异。宿主机未配置 PostgreSQL 时，数据库集成测试会诚实跳过；Docker 强制测试模式要求全部执行。

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
- LLM 默认使用 MockLLMClient，无需云端密钥即可运行
- 存储使用 LocalStorage（OBSStorage 为后续云端部署方案，未实现）
- FAISS、语义检索和 LLM 审阅尚未实现
- 当前 Evidence 高亮基于 normalized 页面文本字符区间，不是 PDF.js/bbox 覆盖层
- 所有数值统计由确定性 Python 代码完成，大模型不直接计算
