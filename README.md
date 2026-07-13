# PaperLens

AI 驱动的学术论文审阅助手。

## 功能概述

- 论文上传与 PDF 解析
- 章节结构识别与表格提取
- 文本分块与向量索引
- 原文证据检索与页内定位（page-local，PyMuPDF block + real bbox）
- 结构化论文审阅（每条结论绑定 Evidence）
- 实验指标提取与 checkpoint 口径判断
- CSV/Excel 实验数据分析
- 审稿报告导出

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
- 所有数值统计由确定性 Python 代码完成，大模型不直接计算