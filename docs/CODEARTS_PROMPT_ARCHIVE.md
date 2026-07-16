# PaperLens 码道提示词归档

> 建立日期：2026-07-13  
> 用途：集中保存实际生成给华为云码道的任务提示词，作为任务范围、验收标准和历史审计记录。

## 归档规则

1. 按生成时间顺序保存不同版本；相同内容在聊天展示并写入文件时只归档一次。
2. 后续每个开发任务都在本文件末尾追加对应提示词，并同步更新 `docs/CODEARTS_NEXT_PROMPT.md` 供用户提交给码道。
3. 码道负责按提示词独立实施、审查和复测；若发现问题，依据用户授权直接修正并验证，不增加重复返修轮次。当前阶段确认通过后，再生成下一步提示词。
4. 不以 `docs/PROGRESS.md` 的汇报代替代码、数据库、Docker 和测试结果核验。
5. 本文 01～08 均从项目历史开发记录的原始消息或补丁参数逐字恢复；仅统一换行为 LF，没有根据阶段汇报改写正文。
6. P2.5 之前实际执行的版本为 01～07；P2.5 已生成提示词且同样由码道实施。从 P2.6 起延续码道独立实施、审查与验收的开发方式。
7. 未实际提交给码道的提示词仍保留归档并明确标注；它们记录了当时的审查结论和任务边界，但不得记作码道执行记录。

## 索引

| 编号 | 任务 | 恢复状态 |
|------|------|----------|
| 01 | P1 工程骨架首次实施 | ✅ rollout 原文 |
| 02 | P1 缺陷修复与 P2 第一条闭环（初版） | ✅ rollout 原文 |
| 03 | Docker 就绪后的 P1/P2 执行版 | ✅ rollout 原文 |
| 04 | P2.1 可靠性与闭环修复 | ✅ rollout 原文 |
| 05 | P2.2 最终闭环修复 | ✅ rollout 原文 |
| 06 | P2.3 测试隔离与验收真实性修复 | ✅ rollout 原文 |
| 07 | P2.4 事务边界与验收收口 | ✅ rollout 原文 |
| 08 | P2.5 验收去伪与并发翻页修复 | ✅ rollout 原文 |
| 09 | P2.6 ProjectDocs 实现态校准 | ✅ 已提交并完成 |
| 10 | P2.7 ProjectDocs 验收去伪与文档收口 | ⚠️ 未提交；码道直接完成同等修正 |
| 11 | P3.1 基于 MockLLM 的结构化审阅后端闭环 | ✅ 已提交、完成并验收 |
| 12 | P3.2 华为云优先的 Embedding 抽象与语义 Evidence 检索 | ✅ 已提交、完成并验收 |
| 13 | P3.3 华为云 MaaS 真实生成式模型适配器 | ✅ 本轮生成，待提交 |
| 14 | P3.4 审阅结果前端与完整任务交互 | ✅ 已提交、完成并验收 |
| 15 | P3.5 完整认证、真实用户隔离与 RBAC 基础 | ✅ 已提交、完成并验收 |
| 16 | P4.1 可追溯实验指标提取后端 | ✅ 已提交、完成并验收 |
| 17 | P4.2 指标分析前端 | ✅ 已提交、完成并验收 |
| 18 | P4.3 华为云 MaaS 运行配置 | ✅ 已提交、完成并验收 |
| 19 | P5.1 CSV/Excel 安全上传与解析 | ✅ 已提交、完成并验收 |
| 20 | P5.2 确定性统计摘要 | ✅ 已提交、完成并验收 |
| 21 | P5.3a 指标交叉验证后端 | ✅ 已提交、完成并验收 |
| 22 | P5.3b 实验数据前端 | ✅ 已提交、完成并验收 |
| 23 | P6.1 Markdown 报告后端 | ✅ 已提交、完成并验收 |
| 24 | P6.2 PDF/DOCX 与导出前端 | ✅ 已提交、完成并验收 |
| 25 | 原 P7.1 管理员后端方案 | ⚠️ 历史方案，已被 26 取代，不执行 |
| 26 | P7.1 论文阅读学习工作台 | ✅ 已提交、完成并验收 |
| 27 | P7.2 当前论文多轮问答 | ✅ 已提交、完成并验收 |
| 28 | P7.3 个人学习沉淀与论文库 | ✅ 已提交、完成并验收 |
| 29 | P8.1 完整管理员系统与不可变审计 | ⬜ 本轮生成，待提交 |

---

## 01 — P1 工程骨架首次实施

> 来源：码道历史会话中的直接回复原文（2026-07-12，rollout 行 117）

~~~~text
你现在负责继续开发 D:\shixi\PaperLens 项目。

请先完整阅读以下现有文档，不要跳过：
- docs/product-requirements.md
- docs/architecture.md
- docs/data-model.md
- docs/api-contract.md
- docs/security-design.md
- docs/IMPLEMENTATION_STATUS.md

本轮目标不是一次性完成整个系统，而是完成“规格修正 + 可运行工程骨架”，为后续端到端 MVP 开发建立稳定基础。

一、必须采用的 MVP 决策

1. 技术栈保持不变：
   - 前端：Vue 3 + TypeScript + Vite + Pinia + Vue Router
   - 后端：FastAPI + Python + SQLAlchemy + Alembic
   - 数据库：PostgreSQL
   - 本地开发也使用 PostgreSQL，不使用 SQLite
   - 云端预留 OBS、MaaS/ModelArts、ECS 适配接口

2. 审阅数据关系调整为：
   - AnalysisTask 1:N ReviewResult
   - ReviewResult 1:N ReviewFinding
   - ReviewFinding N:N Evidence，通过 finding_evidence 关联
   - ReviewFinding 包含 finding_type、content、confidence、verification_status
   - finding_type：STRENGTH / WEAKNESS / SUGGESTION
   - 不再把 strengths、weaknesses、suggestions 作为难以维护的 JSONB 列表保存

3. Evidence 必须支持 PDF 精确定位，至少包含：
   - page_number
   - quoted_text
   - bbox_x0、bbox_y0、bbox_x1、bbox_y1
   - char_start、char_end
   - section_id、chunk_id
   - evidence_type
   前端后续必须能通过这些字段跳转并高亮原文。

4. ExportReport 增加：
   - status：PENDING / GENERATING / READY / FAILED
   - error_message
   - completed_at

5. MVP 上传方式统一为普通 multipart 流式上传，最大 50MB。
   暂不实现分片上传，删除文档中“前端必须分片上传”的冲突描述。

6. 后台任务进度通知统一使用 HTTP 轮询。
   暂不实现 WebSocket。

7. MVP 只承诺支持“包含可提取文本的 PDF”。
   扫描型 PDF/OCR 明确放入后续版本。

8. 增加最小表格实体 PaperTable，至少记录：
   - paper_id、page_number、table_index、caption
   - bbox
   - structured_data JSONB
   - raw_text
   暂不设计复杂的单元格关系模型。

9. LLM 必须通过统一 LLMClient 接口调用。
   默认提供 MockLLMClient，使项目没有云端密钥也可以完整演示。
   后续再实现 MaaSLLMClient 或 ModelArtsLLMClient。

10. 禁止大模型直接计算 mean、max、std 等统计值。
    所有数值统计必须由确定性 Python 代码完成。

二、本轮需要完成的修改

1. 修正现有设计文档之间的冲突：
   - 数据关系
   - API 返回结构
   - 导出状态
   - Evidence 定位字段
   - PostgreSQL 统一选型
   - multipart 上传
   - HTTP 轮询
   - OCR 非目标
   - PaperTable 数据模型

2. 创建可运行的项目骨架：
   - backend/
   - frontend/
   - docker-compose.yml
   - .env.example
   - .gitignore
   - README.md

3. 后端至少实现：
   - FastAPI 应用启动
   - GET /api/v1/health
   - 配置管理
   - SQLAlchemy 数据库连接
   - 修正后的 ORM 模型
   - 第一版 Alembic migration
   - 统一错误响应结构
   - 基础 pytest 测试

4. 前端至少实现：
   - Vue3 + TypeScript 项目初始化
   - 基础路由和 Pinia
   - 简洁的 PaperLens 首页
   - 健康检查调用
   - 后端不可用时显示明确错误
   - npm build 能够通过

5. Docker Compose 至少包含：
   - PostgreSQL
   - backend
   - frontend
   不要在本轮引入 Celery、Redis、Nginx、FAISS 或真实云服务，避免范围失控。

三、工程约束

- 不写入任何真实 AK/SK、API Key、JWT Secret。
- 不修改或删除 .arts 和 .codeartsdoer 目录。
- 不初始化或提交 Git。
- 不实现 P1 加分功能。
- 不生成大量空接口或只有 pass 的占位代码。
- 所有新接口、模型和文档必须保持一致。
- 文件统一使用 UTF-8。
- 关键代码需要中文注释，但不要给显而易见的代码添加冗余注释。
- 发现现有文件内容与本提示词冲突时，以本提示词的 MVP 决策为准。
- 不要谎报测试成功；无法执行时必须报告真实原因和完整命令。

四、验收标准

完成后必须尽可能执行并报告：

1. docker compose config
2. 后端测试
3. 后端 Python 语法/导入检查
4. 前端 npm build
5. GET /api/v1/health 返回：
   {
     "status": "healthy",
     "version": "0.1.0"
   }

五、执行流程

1. 先简要列出实施计划和预计修改文件。
2. 检查本机现有环境和文件，保护已有内容。
3. 直接开始实施，不要停留在建议层面。
4. 完成后列出：
   - 新增和修改的文件
   - 已解决的文档冲突
   - 实际执行的验证命令及结果
   - 尚未完成的问题
   - 下一阶段建议

本轮到“工程骨架可以启动、模型和契约自洽”为止，不要继续实现 PDF 解析和 LLM 审阅功能。
~~~~

---

## 02 — P1 缺陷修复与 P2 第一条闭环（初版）

> 来源：码道历史会话中的直接回复原文（2026-07-12，rollout 行 159）

~~~~text
继续开发 D:\shixi\PaperLens。

首先完整读取：
- docs/PROGRESS.md
- README.md
- docker-compose.yml
- backend/
- frontend/
- docs/ 下全部设计文档

不要只相信 PROGRESS.md 的汇报，必须核对实际代码。本轮分为两个连续阶段：

A. 修复 P1 工程骨架缺陷
B. 实现 P2 第一条可运行闭环：PDF 上传、解析、页面展示和 Evidence 定位

不要实现 LLM 审阅、FAISS、Celery、Redis、OCR、Excel 分析或云端服务。

一、必须先修复的 P1 问题

1. 修复 backend/alembic/env.py：
   - 正确设置 target_metadata=Base.metadata
   - 正确支持 online migration
   - 使用 context.configure(connection=connection, target_metadata=...)
   - 使用 context.begin_transaction()
   - 正确调用 context.run_migrations()
   - 不要通过 if __name__ == "__main__" 才执行迁移
   - 如保留 offline migration，也必须正确实现

2. 时间字段必须使用：
   - SQLAlchemy DateTime(timezone=True)
   - Python datetime
   - created_at 使用数据库 server_default=func.now()
   - updated_at 支持更新
   不允许继续使用 VARCHAR/String 存储时间。

3. docs/PROGRESS.md 已明确迁移从未实际执行，因此可以同步修正 001_initial.py，不要为了未执行过的错误迁移额外制造无意义的兼容迁移。

4. Backend 容器启动时必须先执行：
   alembic upgrade head
   然后再启动 uvicorn。
   数据库不可用或迁移失败时，容器必须失败，不能假装启动成功。

5. Frontend Dockerfile：
   - 使用稳定的 Node LTS 版本
   - 复制 package.json 和 package-lock.json
   - 使用 npm ci，不使用 npm install
   - 保证构建可复现

6. 修正 README 中与实际目录不一致的 backend/app 描述。

7. 完善统一错误响应：
   - AppError
   - RequestValidationError（422）
   - Starlette HTTPException
   所有错误统一为：
   {
     "error": {
       "code": "...",
       "message": "...",
       "details": ...
     }
   }
   details 可为空，但不能泄漏堆栈和服务器路径。

8. 增加必要的数据库约束或 Pydantic 校验：
   - page_number >= 1
   - progress 0~100
   - rating 1~5
   - confidence 0~1
   - char_start/char_end 合法
   - bbox 坐标顺序合法
   - finding_type、status 等枚举值合法

9. ExperimentResult.metric_comparisons 在文档示例中是数组，修正 Python 类型标注和 API schema，避免将其错误声明为 dict。

二、实现本地存储抽象

创建 StorageBackend 接口及 LocalStorage 实现。

要求：
- 本地文件根目录通过 PAPERLENS_STORAGE_ROOT 配置
- 默认使用 ./data
- 文件使用 UUID 路径存储，不直接使用用户文件名拼接路径
- 数据库中的存储字段不要只适用于 OBS；如继续保留 obs_key，必须在文档中说明它实际表示通用 storage_key，最好统一重命名为 storage_key
- 预留以后实现 OBSStorage 的接口，但本轮不要接入真实 OBS
- 删除文件、读取文件都必须验证最终路径位于存储根目录内

三、实现 PDF 上传 API

实现 POST /api/v1/papers/upload。

要求：
- multipart/form-data
- 最大 50MB
- 不能只依赖 Content-Length，必须流式读取并累计大小
- 校验 .pdf 扩展名和 %PDF- 文件头
- 计算 SHA-256
- 安全处理原始文件名
- 使用 UUID 存储路径
- 禁止路径穿越
- 文件写入失败时清理残留文件和数据库记录
- 没有认证系统时，统一从配置读取 DEMO_USER_ID，不接受前端传入 user_id
- 返回符合 api-contract.md 的 Pydantic 响应

Paper 状态统一为：
- UPLOADING
- PROCESSING
- PARSED
- FAILED

上传成功后启动本地后台解析。MVP 可以使用 FastAPI BackgroundTasks，但必须在文档中注明它不适合生产环境，后续再替换为 Celery。

四、实现 PDF 解析服务

使用 PyMuPDF 为主，pdfplumber 负责表格。

至少完成：

1. 页面解析
   - page_number
   - width、height
   - text_content
   - 保存文本块或单词的 bbox 信息供 Evidence 定位

2. 文本型 PDF 检查
   - 如果所有页面几乎没有可提取文本，返回明确的 OCR_NOT_SUPPORTED
   - 限制最大页数
   - 对解析增加异常处理

3. 章节识别
   - 使用可解释的规则识别 Abstract、Introduction、Method、Experiment、Result、Discussion、Conclusion、References
   - 规则识别失败时使用 OTHER
   - 不调用大模型

4. 文本分块
   - 优先按章节和段落分块
   - 设置合理的最大字符数和重叠
   - 记录 page_numbers、char_count、chunk_index
   - 分块结果必须可重复

5. 表格提取
   - 使用 pdfplumber
   - 保存 PaperTable 的页码、序号、bbox、raw_text、structured_data
   - 提取失败不能导致整篇论文解析失败

6. Evidence
   - 为可定位的段落生成 Evidence
   - 保存 quoted_text、page_number、bbox、char_start、char_end
   - quoted_text 必须确实来自对应页面文本
   - 不得伪造 bbox
   - 无法获得精确 bbox 时允许为空，但必须如实标记

五、实现查询 API

至少实现：

- GET /api/v1/papers
- GET /api/v1/papers/{paper_id}
- GET /api/v1/papers/{paper_id}/pages/{page_number}
- GET /api/v1/papers/{paper_id}/sections
- GET /api/v1/papers/{paper_id}/evidences
- GET /api/v1/evidences/{evidence_id}

所有查询必须使用 DEMO_USER_ID 过滤，禁止读取其他用户数据。

列表接口实现 page/page_size，并限制最大 page_size。

六、实现前端最小闭环

增加：

1. 论文上传页面
   - 拖拽或选择 PDF
   - 上传进度
   - 文件类型和大小提示
   - 错误提示

2. 论文列表
   - 显示标题、文件名、状态、页数、创建时间
   - PROCESSING 状态轮询
   - 解析成功后可以进入详情

3. 论文详情
   - 显示章节列表
   - 显示页面文本
   - 显示 Evidence 列表
   - 点击 Evidence 后切换到对应页，并高亮 quoted_text
   - 本阶段没有 PDF.js 时，可以先在页面文本中高亮；不要虚假宣称已经实现 PDF 坐标覆盖层

七、测试要求

必须增加真实有效的测试：

- Alembic 配置和 metadata 检查
- 非 PDF 上传被拒绝
- 伪造扩展名被拒绝
- 超过大小限制被拒绝
- 路径穿越文件名被安全处理
- 使用 PyMuPDF 在测试临时目录动态生成一个最小 PDF
- PDF 页面解析测试
- 章节识别测试
- 分块确定性测试
- Evidence quoted_text 与页面文本一致性测试
- 论文列表和详情 API 测试
- 跨用户数据不可访问测试
- 422 统一错误格式测试
- 前端 npm build

测试产生的临时文件必须放在 pytest tmp_path 或系统临时目录，不得污染项目目录。

八、文档和汇报

同步更新：
- docs/api-contract.md
- docs/data-model.md
- docs/architecture.md
- docs/security-design.md
- docs/IMPLEMENTATION_STATUS.md
- README.md

完成后在 docs/PROGRESS.md 中追加“P1.1 修复”和“P2 第一阶段”记录，不要删除旧记录。

PROGRESS.md 必须写明：
- 修改文件
- 实际完成功能
- 实际执行的命令
- 每条命令的真实结果
- 未执行项目及原因
- 已知限制
- 下一阶段建议

九、执行约束

- 不修改 .arts、.codeartsdoer 和 .git
- 不执行 git commit
- 不写入真实云密钥
- 不谎报 Docker、PostgreSQL 或迁移验证结果
- 如果本机没有 PostgreSQL/Docker，仍需完成代码和无数据库单元测试，并如实记录未验证项
- 不扩展到 LLM 审阅
- 不生成只有 pass 的空实现
- 开始前先列计划，随后直接实施
~~~~

---

## 03 — Docker 就绪后的 P1/P2 执行版

> 来源：首次写入 `docs/CODEARTS_NEXT_PROMPT.md` 的补丁原文（2026-07-12，rollout 行 326）

~~~~text
继续开发 D:\shixi\PaperLens 项目。

Docker Desktop 已安装并验证正常：
- Docker Server 29.6.1
- Docker Compose v5.2.0
- WSL 2 后端正常
- docker compose config 已通过
- hello-world 已运行成功

本轮必须完成：

1. 修复 P1 工程问题
2. 实现 PDF 上传、解析、页面/章节/Evidence 查询
3. 实现前端上传与论文详情最小闭环
4. 使用 Docker 真实验证 PostgreSQL、迁移、前后端联通
5. 将真实汇报追加到 docs/PROGRESS.md

开始前完整阅读：
- docs/PROGRESS.md
- README.md
- docker-compose.yml
- backend/
- frontend/
- docs/ 下所有设计文档

不要只依赖 PROGRESS.md，必须核对实际代码。

一、先修复已确认的问题

1. 修复 backend/alembic/env.py

当前迁移测试出现：
- alembic 命令可能找不到 paperlens 包
- python -m alembic upgrade head --sql 返回 0，但没有输出任何 SQL
- env.py 仅在 __main__ 下调用迁移
- target_metadata=None
- context.run_migrations 用法错误

改为标准 Alembic 配置：

- target_metadata=Base.metadata
- 支持 offline 和 online migration
- online 使用 context.configure(connection=connection, target_metadata=target_metadata)
- 使用 context.begin_transaction()
- 正确调用 context.run_migrations()
- 加载 env.py 时直接根据 context.is_offline_mode() 执行
- 不依赖 if __name__ == "__main__"
- 保证在 backend 目录执行 `python -m alembic` 和容器中执行 `alembic` 都能正常工作

2. 修正时间字段

所有时间字段改为：

- Python datetime
- SQLAlchemy DateTime(timezone=True)
- created_at 使用 server_default=func.now()
- updated_at 使用 server_default 和 onupdate
- 不再使用 String(30) 存储时间

PROGRESS.md 已说明初始迁移从未成功执行，因此同步修正 001_initial.py，不需要为未应用的错误迁移新增兼容迁移。

3. Backend 容器启动流程

容器启动时必须：

等待 PostgreSQL 健康 → alembic upgrade head → uvicorn

迁移失败时容器必须失败，不得继续启动。

4. 其他修复

- Frontend Dockerfile 使用 Node LTS、复制 package-lock.json、执行 npm ci
- README 目录结构改为真实的 backend/paperlens
- ExperimentResult.metric_comparisons 类型改为 list[dict] | None
- 统一 AppError、HTTPException、RequestValidationError 的错误格式
- 增加 page_number、progress、rating、confidence、bbox、char 范围校验
- 状态与类型字段使用 Python Enum 或 Pydantic Literal
- 不向客户端返回堆栈、数据库地址或本机路径

二、实现通用存储层

创建：

- StorageBackend 抽象接口
- LocalStorage 实现
- 预留 OBSStorage 接口，但不接入真实 OBS

配置：

```text
PAPERLENS_STORAGE_BACKEND=local
PAPERLENS_STORAGE_ROOT=./data
PAPERLENS_DEMO_USER_ID=demo-user
```

要求：

- 将模型中的 obs_key 统一重命名为 storage_key
- 使用 UUID 构造存储路径
- 原始文件名只作为元数据保存
- 不允许用户指定 storage_key
- 使用 Path.resolve 和 relative_to/commonpath 防止路径穿越
- 写入失败时清理残留文件
- 删除和读取时再次检查路径
- 不接受前端传入 user_id

三、实现 PDF 上传与解析

实现：

```text
POST /api/v1/papers/upload
```

要求：

- multipart/form-data
- 最大 50MB
- 流式读取并累计大小，不能只依赖 Content-Length
- 同时验证 .pdf 扩展名和 `%PDF-` 文件头
- 计算 SHA-256
- 安全处理 Windows 和 Linux 路径分隔符
- 文件保存到 UUID 路径
- 返回 Pydantic 响应
- 上传成功后状态为 PROCESSING
- 使用 FastAPI BackgroundTasks 触发解析
- 后台任务必须自己创建和关闭数据库 Session，不能复用请求 Session
- 解析完成改为 PARSED，失败改为 FAILED
- BackgroundTasks 仅用于 MVP，并在文档注明生产环境应替换为 Celery

Paper 状态统一为：

```text
UPLOADING / PROCESSING / PARSED / FAILED
```

四、PDF 解析服务

使用 PyMuPDF 为主，pdfplumber 提取表格。

至少实现：

1. 页面解析
   - page_number、width、height、text_content
   - 提取文本块及 bbox

2. 文本检查
   - 最大页数可配置
   - 页面几乎无文本时返回 OCR_NOT_SUPPORTED
   - 扫描型 PDF 不做 OCR

3. 章节识别
   - 规则识别 Abstract、Introduction、Method、Experiment、Result、Discussion、Conclusion、References
   - 无法识别时使用 OTHER
   - 不调用 LLM

4. 文本分块
   - 按章节和段落分块
   - 最大字符数和重叠量可配置
   - 保存 chunk_index、content、char_count、page_numbers
   - 对同一输入结果必须稳定

5. 表格
   - pdfplumber 提取
   - 保存 PaperTable 的页码、序号、bbox、raw_text、structured_data
   - 单张表失败不能让整篇解析失败

6. Evidence
   - 为可定位段落生成 Evidence
   - 保存 quoted_text、page_number、bbox、char_start、char_end
   - quoted_text 必须存在于对应页面文本中
   - 无法确定 bbox 时保存 null，禁止伪造坐标

五、查询 API

实现并与 api-contract.md 保持一致：

```text
GET /api/v1/papers
GET /api/v1/papers/{paper_id}
GET /api/v1/papers/{paper_id}/pages/{page_number}
GET /api/v1/papers/{paper_id}/sections
GET /api/v1/papers/{paper_id}/evidences
GET /api/v1/evidences/{evidence_id}
```

要求：

- 所有查询强制使用 PAPERLENS_DEMO_USER_ID
- 禁止跨用户读取
- 列表支持 page/page_size
- page_size 设置上限
- 不存在资源返回统一 404
- 时间字段输出 ISO 8601

六、前端最小闭环

实现：

1. PDF 上传页面
   - 选择或拖拽文件
   - 文件类型和大小校验
   - 上传进度
   - 清晰的错误提示

2. 论文列表
   - 标题、文件名、状态、页数、创建时间
   - PROCESSING 时自动轮询
   - PARSED 后进入详情

3. 论文详情
   - 章节列表
   - 页面文本
   - Evidence 列表
   - 点击 Evidence 切换到对应页面
   - 在页面文本中高亮 quoted_text
   - 本阶段不使用 PDF.js，不得宣称已实现 PDF 坐标覆盖层

七、测试

必须新增真实测试：

- Alembic offline SQL 能产生 CREATE TABLE SQL
- ORM metadata 与迁移表一致
- 非 PDF 被拒绝
- 伪造扩展名被拒绝
- 超大文件被拒绝
- 路径穿越文件名被安全处理
- 使用 PyMuPDF 在 pytest tmp_path 动态生成测试 PDF
- 页面解析
- OCR_NOT_SUPPORTED
- 章节识别
- 分块确定性
- Evidence 文本与页面一致
- 论文列表和详情 API
- 跨用户访问被拒绝
- 422 统一错误格式
- 前端构建

测试文件只能写入 pytest tmp_path 或系统临时目录。

八、Docker 真实验证

本轮必须实际执行：

```powershell
cd D:\shixi\PaperLens
docker compose config
docker compose up --build -d
docker compose ps
docker compose logs --tail 200
docker compose exec backend alembic current
docker compose exec backend python -m pytest -q
```

还要验证：

```text
GET http://localhost:8000/api/v1/health
前端 http://localhost:3000
PostgreSQL 中已创建业务表
```

如果启动失败，必须根据日志修复，不能只记录失败后结束。

禁止执行：

```powershell
docker compose down -v
docker volume rm
```

不要删除数据库卷。

九、范围限制

本轮不实现：

- LLM 审阅
- MaaS/ModelArts
- FAISS
- Celery/Redis
- OCR
- CSV/Excel
- PDF/DOCX 报告
- JWT 多用户认证

不得修改：

```text
.arts/
.codeartsdoer/
.git/
```

不要执行 git commit，不写入任何真实密钥。

十、汇报

完成后更新：

- README.md
- docs/api-contract.md
- docs/data-model.md
- docs/architecture.md
- docs/security-design.md
- docs/IMPLEMENTATION_STATUS.md

在 docs/PROGRESS.md 末尾追加：

```text
P1.1 工程修复
P2 第一阶段：PDF 上传与解析
```

必须记录：

- 新增和修改文件
- 已完成的真实功能
- 测试命令与真实结果
- Docker 容器状态
- Alembic 当前 revision
- API 验证结果
- 未完成项和原因
- 下一阶段建议

先输出简短实施计划，然后直接开始执行，不要停留在建议阶段。
~~~~

---

## 04 — P2.1 可靠性与闭环修复

> 来源：`docs/CODEARTS_NEXT_PROMPT.md` 覆盖补丁原文（2026-07-12，rollout 行 438）

~~~~text
继续修复 D:\shixi\PaperLens 项目。

本轮定义为 P2.1：可靠性、安全性、Evidence 定位和前端闭环修复。

禁止进入 LLM、MaaS/ModelArts、FAISS、指标提取、Excel 分析和报告导出阶段。先把当前 P2 做到真实可用、测试无跳过、文档与代码一致。

开始前必须完整阅读：

- docs/PROGRESS.md
- README.md
- docs/ 下所有设计文档
- backend/paperlens/
- backend/tests/
- backend/alembic/
- frontend/src/
- docker-compose.yml

不要只依据 PROGRESS.md；以下问题均已通过外部静态审查或实际命令确认，必须逐项修复。

一、修复 LocalStorage 路径穿越漏洞

当前 `_resolve()` 使用字符串 `startswith`，已实测出现：

```text
root=/tmp/store
storage_key=../store_evil/escaped.pdf
结果=/tmp/store_evil/escaped.pdf
```

要求：

1. 使用 `Path.resolve()` 后配合 `Path.relative_to(root)` 判断目标是否位于根目录。
2. 禁止使用字符串 `startswith` 判断路径归属。
3. 同时正确处理 `/` 和 `\` 两种用户文件名分隔符。
4. 存储路径不再使用用户原始文件名，统一采用：

```text
papers/{paper_uuid}/source.pdf
```

5. 原始文件名只保存在数据库 filename 字段。
6. `read_path`、`save`、`delete` 都必须经过同一安全解析函数。
7. 上传过程中如果数据库提交失败，必须删除已经保存的 storage object。
8. 增加测试：
   - `../store_evil/file.pdf` 必须被拒绝
   - `..\store_evil\file.pdf` 必须被拒绝
   - `/absolute/path` 必须被拒绝
   - sibling-prefix 绕过必须被拒绝
   - Windows 风格上传名 `C:\fake\paper.pdf` 最终 filename 只能是 `paper.pdf`

二、修复 UUID 与查询参数校验

当前实测：

```text
GET /api/v1/papers/not-a-uuid
HTTP 500
```

要求：

1. 所有 paper_id、evidence_id、task_id 等 API 路径参数使用 Pydantic `UUID` 类型。
2. 非法 UUID 返回统一 422：

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "...",
    "details": []
  }
}
```

3. 列表 status 参数使用 `PaperStatus | None`，非法状态返回 422，不能返回空列表掩盖错误。
4. 统一错误响应始终包含 `details`，可以为 null 或数组。
5. 上传接口捕获未知异常时不得把 `str(e)` 返回给客户端；服务器记录日志，客户端只收到安全的通用消息。

三、修复数据库约束与枚举未落地问题

当前 ORM 和 migration 中 `CheckConstraint` 数量为 0，虽然定义了 StrEnum，但模型字段仍是任意 String。

数据库中的 `001_initial` 已经实际应用，禁止直接篡改已应用迁移来假装修复。

要求：

1. 新建 Alembic revision，例如 `002_constraints_and_hardening.py`。
2. 为以下内容增加数据库约束：
   - page_number >= 1
   - table_index >= 1
   - progress BETWEEN 0 AND 100
   - rating BETWEEN 1 AND 5
   - confidence BETWEEN 0 AND 1
   - char_start >= 0
   - char_end >= char_start
   - bbox_x1 >= bbox_x0
   - bbox_y1 >= bbox_y0
3. 状态、finding_type、evidence_type 等字段至少增加合法值 CheckConstraint，或正确使用 SQLAlchemy Enum。
4. ORM metadata 与新迁移保持一致。
5. `alembic upgrade head` 后当前 revision 应为新 revision。
6. `alembic downgrade 001_initial` 和重新 upgrade 必须可执行，但禁止删除 Docker volume。

四、修复数据库测试被错误跳过

当前 5 个数据库测试在 backend 容器中全部 skip，因为测试把数据库地址硬编码为 localhost；容器内数据库主机名实际是 postgres。

要求：

1. 删除 `_db_available()` 中硬编码的 localhost DSN。
2. 测试数据库连接从 `PAPERLENS_TEST_DATABASE_URL` 或当前环境配置读取。
3. Docker 环境使用独立测试数据库，不能污染 paperlens 开发库。
4. 测试运行前对测试库执行迁移。
5. 每个测试使用事务回滚或可靠清理。
6. 不允许用扩大 status code 接受范围的方式让错误测试通过。
7. 路径测试必须断言实际 filename、storage_key 和最终路径，而不是只检查 `201/400/415` 之一。
8. 非法 UUID 测试必须严格断言 422 和统一错误结构。
9. 跨用户测试必须严格断言 403，并验证没有返回资源内容。
10. Docker 内最终必须达到 0 skipped；如确有平台无关的合理 skip，必须逐条说明，不能把核心 DB/API 测试跳过。

五、重新设计 Evidence 生成，使引用与页面严格一致

当前实现把可能跨页的 chunk 整体绑定到第一页，只查找前 100 字符，并可能产生超出页面文本的 char_end；bbox 永远为 null，section_id 也未绑定。

要求：

1. Evidence 必须是 page-local，禁止一个 Evidence 的 quoted_text 横跨多页。
2. 优先使用 PyMuPDF：

```python
page.get_text("blocks")
```

生成页面文本块 Evidence。

3. 每个 Evidence 必须满足：

```python
evidence.quoted_text == page_text[evidence.char_start:evidence.char_end]
```

允许统一规范化换行或空白，但必须有明确、可测试的规范化函数。
4. bbox 使用 PyMuPDF 文本块的真实坐标，禁止伪造。
5. char_start/char_end 必须位于对应页面文本范围内。
6. Evidence 正确绑定 chunk_id 和 section_id。
7. chunk 可以跨页，但必须通过多个 page-local Evidence 关联，不能用一个跨页 Evidence 代替。
8. PDF 文档必须使用 context manager 或 try/finally，任何异常都保证关闭。
9. 表格尽可能使用 pdfplumber `find_tables()` 获得真实 bbox；无法获得时允许 null，但必须如实记录。
10. 后台解析失败时记录服务端日志和安全的失败原因，不允许完全吞掉异常。

增加测试：

- 单页 Evidence 精确文本切片
- 两页同一章节的 Evidence 不跨页
- 每个 Evidence bbox 位于页面尺寸内
- char_start/char_end 不越界
- Evidence 正确关联 section 和 chunk
- PDF 解析异常后文件句柄关闭

六、真正完成前端 Evidence 闭环

当前 `PaperDetailView.vue` 点击 Evidence 后切换到章节 Tab，并查找不存在的 `[data-page]`，没有调用 `getPage()`，没有页面文本，也没有高亮。

要求：

1. 论文详情页至少包含：
   - 章节 Tab
   - 页面 Tab
   - Evidence Tab
2. 页面 Tab 支持上一页、下一页和页码跳转。
3. 使用已有 `getPage(paperId, pageNumber)` 加载页面文本。
4. 点击 Evidence 时：
   - 切换到页面 Tab
   - 加载 Evidence 对应页
   - 使用 char_start/char_end 精确高亮 quoted_text
   - 将高亮区域滚动到可见位置
5. 禁止直接用未经转义的 `v-html` 渲染论文内容，避免 XSS。
6. 可以通过 Vue computed 将文本拆成 before/highlight/after 三部分进行安全渲染。
7. PROCESSING 详情页需要轮询状态，变为 PARSED 后自动加载章节与 Evidence。
8. FAILED 状态显示清晰失败信息和返回入口。
9. PaperListView 在 `onUnmounted()` 中清除轮询定时器，避免内存泄漏。
10. 所有 catch 块不得静默忽略错误；页面应显示用户可理解的错误。

增加至少必要的前端单元测试；如果当前未配置 Vitest，先添加最小 Vitest + Vue Test Utils 配置，覆盖：

- 点击 Evidence 后请求正确页码
- 高亮文本正确
- PROCESSING 轮询在卸载时停止
- API 错误显示

七、同步文档

当前文档仍大量使用 obs_key，并且 PROGRESS.md 自己注明文档未同步。

必须同步：

- docs/product-requirements.md
- docs/architecture.md
- docs/data-model.md
- docs/api-contract.md
- docs/security-design.md
- docs/IMPLEMENTATION_STATUS.md
- README.md

要求：

1. 全部通用存储字段统一为 storage_key。
2. OBSStorage 仅作为未来实现说明。
3. 状态统一包含 PROCESSING。
4. 写清 FastAPI BackgroundTasks 只适用于 MVP。
5. API 契约包含 Evidence 列表接口、错误 details、UUID 422。
6. 文档不得宣称尚未实现的 PDF 坐标覆盖层或云服务已经完成。

八、真实验证

完成修改后必须执行：

```powershell
cd D:\shixi\PaperLens
docker compose config
docker compose up --build -d
docker compose ps
docker compose logs --tail 200
docker compose exec -T backend alembic current
docker compose exec -T backend python -m pytest -q -rs
```

要求：

- 后端核心测试 0 failed、0 skipped
- 前端测试全部通过
- `npm run build` 通过
- 非法 UUID 返回 422
- sibling-prefix 路径绕过被拒绝
- 上传一份动态生成的双页 PDF
- 轮询到 PARSED
- 页面、章节、Evidence API 均有正确数据
- 每条 Evidence 的 quoted_text/char range 与页面内容一致
- 前端通过 Nginx 代理访问 API 正常

禁止执行：

```powershell
docker compose down -v
docker volume rm
```

不得删除现有数据库卷。

九、范围与汇报

本轮只修复 P2.1，不实现任何新业务阶段。

不得修改：

```text
.arts/
.codeartsdoer/
.git/
```

不要执行 git commit，不写入真实云密钥。

完成后在 docs/PROGRESS.md 末尾追加 `P2.1 — 可靠性与闭环修复`，必须如实记录：

- 修改文件
- 每个已修复问题
- 新 Alembic revision
- 后端通过/失败/跳过数量
- 前端测试与构建结果
- 双页 PDF 端到端验证结果
- Docker 容器状态
- 尚未完成项
- 下一阶段建议

先输出简短计划，然后直接实施。遇到失败必须查看日志、修复并复测，不能只记录失败后结束。
~~~~

---

## 05 — P2.2 最终闭环修复

> 来源：`docs/CODEARTS_NEXT_PROMPT.md` 覆盖补丁原文（2026-07-12，rollout 行 560）

~~~~text
继续修复 D:\shixi\PaperLens 项目。

本轮定义为 P2.2：PDF 上传、Evidence API、字符定位、前端高亮和测试隔离的最终收尾。

P2.1 的大部分改动已经落地，但外部代码审查确认仍有运行级缺陷。禁止开始 LLM、MaaS/ModelArts、FAISS、指标提取、Excel 或报告导出；必须先逐项修复并真实复测。

开始前完整阅读：

- docs/PROGRESS.md
- backend/paperlens/api/papers.py
- backend/paperlens/services/pdf_parser.py
- backend/paperlens/utils/storage.py
- backend/tests/
- frontend/nginx.conf
- frontend/src/api/index.ts
- frontend/src/views/UploadView.vue
- frontend/src/views/PaperDetailView.vue
- frontend/src/tests/
- docker-compose.yml

一、修复 Nginx 上传 413

已通过真实浏览器复现：经 `http://localhost:3000` 上传 11.3MB PDF 返回 HTTP 413。后端限制是 50MB，但 `frontend/nginx.conf` 没有 `client_max_body_size`，请求在到达 FastAPI 前被 Nginx 默认限制拒绝。

要求：

1. 在 server 作用域配置：

```nginx
client_max_body_size 60m;
```

2. `/api/` 代理至少配置：

```nginx
proxy_pass http://backend:8000;
proxy_read_timeout 180s;
proxy_send_timeout 180s;
proxy_request_buffering off;
```

3. 代理层允许 multipart 额外开销，但后端仍严格执行 50MB 流式限制。
4. 前端 Axios 错误处理统一提取 `response.data.error.message`。
5. Nginx 返回非 JSON 413 时显示中文“文件超过上传限制”，不能显示 `Request failed with status code 413`。
6. 重新构建 frontend 镜像后，必须通过 3000 端口成功上传 11.3MB PDF。
7. 大于 50MB 的文件仍必须由前端预检或后端拒绝。

二、修复 Evidence 详情接口 500

当前 `GET /api/v1/evidences/{evidence_id}` 返回结构中存在：

```python
bbox_y1=e.bbox_y1
```

变量 `e` 未定义，应使用 `evidence.bbox_y1`。该错误会让有效 Evidence 详情请求返回 500。

要求：

1. 修正变量引用。
2. 增加真实数据库 API 测试：创建 Evidence 后调用详情接口，严格断言 200 和所有 bbox/char 字段。
3. 增加不存在但格式合法 UUID 的 404 测试。
4. 不允许仅测试非法 UUID 422 来代替有效资源测试。

三、统一 Evidence 字符偏移坐标系

当前后端 `char_start/char_end` 基于 `_normalize_whitespace(page_text)` 计算，API 的 `PaperPage.text_content` 却返回原始文本；前端直接对原始文本切片。因此包含换行、多空格、制表符或特殊字符时，高亮位置会错误。

必须选择并实现一种唯一、明确的坐标系。MVP 推荐：

1. PaperPage 增加或明确提供 `normalized_text_content`。
2. Evidence 的 `quoted_text`、char_start、char_end 全部相对于 `normalized_text_content`。
3. 页面 API 同时返回：
   - `text_content`：原始提取文本，可选用于保留格式
   - `normalized_text_content`：用于 Evidence 精确定位和前端高亮
4. 如果新增数据库字段，创建新的 Alembic `003_*` 迁移，禁止改写已应用的 001/002。
5. 前端高亮必须对 `normalized_text_content` 切片。
6. 文档明确 char range 对应哪个字段。

后端 Evidence 生成还必须修复：

1. 不再只执行：

```python
normalized_page.find(normalized_block[:80])
```

必须匹配完整 normalized block，避免相同前缀绑定错误段落。
2. 只有完整 quoted_text 与页面切片一致时才能保存 char range：

```python
normalized_text_content[char_start:char_end] == quoted_text
```

3. 无法完整匹配时 char_start/char_end 设为 null，并记录日志；禁止截断 char_end 后假装精确匹配。
4. 对同页重复段落制定稳定策略，例如结合 block 顺序维护搜索起点。
5. 增加包含多空格、换行、制表符、重复前缀、`<`、`>`、`&` 的测试 PDF。

四、修复前端高亮逻辑

当前存在两个问题：

1. `_escapeHtml()` 后又使用 Vue `{{ }}` 插值，导致二次转义，正文可能显示 `&lt;` 等字面文本；字符偏移也会因转义后长度变化而错误。
2. 点击非当前页 Evidence 时，先设置 highlight，再修改 currentPage；currentPage watcher 会把 highlight 清空，所以跨页点击后没有高亮。

要求：

1. 删除手工 `_escapeHtml()`。Vue 文本插值本身会安全转义，禁止使用 v-html。
2. 高亮切片必须基于 API 返回的 `normalized_text_content` 原文字符串。
3. 使用 `selectedEvidence` 保存待高亮 Evidence。
4. `goToEvidence()` 应按顺序：
   - 保存 selectedEvidence
   - 切换页面 Tab
   - 切换/加载目标页
   - 等待页面数据返回
   - 再设置或计算 highlight range
   - `nextTick()` 后滚动 `<mark>` 到可见位置
5. 普通手工翻页时清除 selectedEvidence；Evidence 导航触发的翻页不得提前清除。
6. char range 为 null 时，显示 Evidence 文本并提示“该证据暂不支持精确高亮”，不能错误高亮。
7. 页面加载失败、论文详情加载失败不得只写 console，必须显示可见错误和重试入口。

前端测试必须真正断言：

- 点击位于第 2 页的 Evidence 后调用 `getPage(id, 2)`
- 页面加载完成后 `<mark>` 文本严格等于 quoted_text
- 包含 `<script>`、`&` 等字符时不会生成可执行 HTML，也不会显示双重转义文本
- char range 为 null 时显示降级提示
- FAILED 状态测试必须断言失败提示真实存在，不能只有 mount 没有 assertion
- PROCESSING 轮询解析完成后加载章节和 Evidence
- unmount 后定时器停止

五、改进数据库测试隔离

当前测试虽可在 Docker 内运行，但 `_get_test_db_url()` 会回退到开发数据库，核心测试可能污染 paperlens 开发库；路径上传测试也没有直接验证数据库 storage_key。

要求：

1. 增加独立 `PAPERLENS_TEST_DATABASE_URL`，数据库名使用 `paperlens_test`。
2. Docker 中明确创建/使用测试数据库，不允许回退到开发库执行写测试。
3. 测试启动前对测试库执行 Alembic upgrade head。
4. 每个测试事务回滚或可靠清理。
5. 如果没有 TEST_DATABASE_URL，数据库集成测试应明确失败并提示配置，不能悄悄改用开发库，也不能 skip 后宣称全量通过。
6. 路径文件名测试必须查询数据库并严格断言：

```text
filename == passwd.pdf
storage_key == papers/{paper_uuid}/source.pdf
```

7. 测试完成后开发库中的论文数量不能因 pytest 增加。

六、加强后端接口类型与错误处理

1. `list_papers` 的 status 参数直接声明为 `PaperStatus | None`，不要手工使用 `PaperStatus.__members__` 判断。
2. `_process_paper` 的 user_id 当前未使用；要么删除参数，要么用于校验 paper 所属用户，避免误导。
3. 后台解析失败应保存可展示的安全失败原因。若 Paper 尚无 error_message 字段，新增字段及迁移，前端 FAILED 状态展示安全原因。
4. 表格提取异常可以降级，但至少记录 debug/warning 日志，不能完全静默 pass。
5. 上传结束后正确关闭 UploadFile/临时文件，任何路径都不得遗留临时文件。

七、同步文档和汇报准确性

同步：

- README.md
- docs/api-contract.md
- docs/architecture.md
- docs/data-model.md
- docs/security-design.md
- docs/IMPLEMENTATION_STATUS.md

必须说明：

- Nginx 60MB 只是代理上限，业务上限仍是 50MB
- Evidence char range 对应 normalized_text_content
- BackgroundTasks 仅用于 MVP
- 测试使用独立 paperlens_test 数据库
- 当前未实现 LLM、向量检索和真实 PDF.js 坐标覆盖层

八、真实验证

完成后重新构建，不得沿用旧容器结果：

```powershell
cd D:\shixi\PaperLens
docker compose up --build -d
docker compose ps
docker compose logs --tail 200
docker compose exec -T backend alembic current
docker compose exec -T backend python -m pytest -q -rs
docker compose exec -T frontend-or-build-stage npm test -- --run
```

如果 runtime frontend 镜像不含 Node 测试环境，可在宿主机 frontend 目录执行：

```powershell
npm ci
npm test -- --run
npm run build
```

必须进行真实端到端验证：

1. 通过 `http://localhost:3000` 上传原来的约 11.3MB PDF，必须成功进入 PROCESSING，不能 413。
2. 轮询到 PARSED。
3. 页面、章节、Evidence 列表和 Evidence 详情接口均返回 200。
4. 点击第 2 页 Evidence，前端正确跳到第 2 页并高亮完整 quoted_text。
5. 有效 Evidence 详情接口不再 500。
6. 非法 UUID 返回 422。
7. 大于 50MB 文件仍被拒绝并显示中文错误。
8. pytest 后开发数据库记录数不变。

禁止执行：

```powershell
docker compose down -v
docker volume rm
```

不得删除现有数据库卷。

九、范围限制与汇报

本轮只完成 P2.2，不进入 P3。

不得修改：

```text
.arts/
.codeartsdoer/
.git/
```

不要 git commit，不写入真实密钥。

完成后在 docs/PROGRESS.md 末尾追加 `P2.2 — 最终闭环修复`，必须如实记录：

- Nginx 11.3MB 上传验证结果
- Evidence 详情接口结果
- 新 Alembic revision
- 字符偏移坐标系定义
- 后端通过/失败/跳过数量
- 前端测试断言和构建结果
- 独立测试数据库验证
- 端到端跨页高亮结果
- 尚未完成项

先给出简短计划，然后直接实施。所有失败必须修复并复测，不得仅记录失败后结束。
~~~~

---

## 06 — P2.3 测试隔离与验收真实性修复

> 来源：`docs/CODEARTS_NEXT_PROMPT.md` 覆盖补丁原文（2026-07-13，rollout 行 841）

~~~~text
继续修复 D:\shixi\PaperLens 项目。

本轮定义为 P2.3：修复测试数据库隔离、无效测试断言、资源清理、失败信息安全和前端错误闭环，确保 P2 的验收结果真实可信。

P2.2 已实现 normalized_text_content、Evidence 详情接口、Nginx 上传配置和部分前端高亮逻辑，但外部代码审查及只读数据库核验确认，P2.2 的“独立测试数据库”实际上没有生效，部分测试即使没有执行目标代码也会通过。因此禁止开始 P3、LLM、MaaS/ModelArts、FAISS、指标提取、Excel 或报告导出；必须先完成本轮修复并真实复测。

开始前完整阅读：

- docs/PROGRESS.md
- docs/CODEARTS_NEXT_PROMPT.md
- docs/IMPLEMENTATION_STATUS.md
- README.md
- backend/paperlens/core/config.py
- backend/paperlens/core/database.py
- backend/paperlens/api/papers.py
- backend/paperlens/services/pdf_parser.py
- backend/paperlens/models/models.py
- backend/alembic/env.py
- backend/tests/conftest.py
- backend/tests/test_api/test_health.py
- backend/tests/test_services/test_pdf_parser.py
- frontend/src/api/index.ts
- frontend/src/views/UploadView.vue
- frontend/src/views/PaperDetailView.vue
- frontend/src/tests/PaperDetailView.test.ts
- docker-compose.yml
- backend/init-test-db.sh

先给出简短计划，然后直接实施。不得只修改文档或测试数量，必须修复真实运行路径。

一、修复测试实际写入开发数据库的严重问题

当前代码的真实问题：

1. `backend/tests/test_api/test_health.py` 在模块顶部先导入：

```python
from paperlens.main import app
```

2. `paperlens.core.database` 在导入时已经根据 `PAPERLENS_DATABASE_URL` 创建全局 Engine 和 SessionLocal；Docker 中该 URL 指向开发库 `paperlens`。
3. `db_client` 只给 Alembic 子进程临时设置了测试库 URL，但 ASGI app、`get_db` 和 `_process_paper()` 仍使用已经创建好的开发库 Engine。
4. 外部只读核验结果为：

```text
paperlens      papers = 24
paperlens_test papers = 0
```

5. 开发库中已出现明显由 pytest 产生的记录：`test.pdf`、`passwd.pdf`、`detail_test.pdf`、`ev_test.pdf`、`norm_test.pdf`。

要求：

1. 保证测试数据库环境在导入任何 `paperlens` 模块、settings、database、app 之前就已确定。
2. Docker 全量测试运行时，以下对象必须全部指向 `paperlens_test`：
   - FastAPI 请求依赖使用的 Session
   - 后台 `_process_paper()` 使用的 Session
   - Alembic migration 使用的连接
   - 测试直接查询数据库使用的 Session
3. 可选择以下任一种可靠方案，优先使用清晰、可维护的实现：
   - 在 pytest 根 conftest 最早阶段将 `PAPERLENS_DATABASE_URL` 设置为 `PAPERLENS_TEST_DATABASE_URL`，再导入应用；同时增加强制断言，证明 Engine 的数据库名为 `paperlens_test`。
   - 或重构为 Engine/Session 工厂和 FastAPI dependency override，但必须同时覆盖后台任务 Session，不能只覆盖请求依赖。
4. 增加强制安全守卫：执行任何会写数据库的集成测试前，解析连接 URL 并严格断言数据库名恰好为 `paperlens_test`；如果是 `paperlens`、postgres 或其他数据库，立即 fail，禁止继续。
5. 不允许通过 monkeypatch 掉所有数据库写入来伪造集成测试通过。
6. 不允许继续使用“迁移测试库，但应用写开发库”的双连接状态。
7. 不要自动删除当前开发库的 24 条记录，因为其中可能混有用户真实上传数据；只记录污染事实，由用户后续人工决定清理范围。

二、让测试数据库创建、迁移和清理真正可靠

当前 `backend/init-test-db.sh` 仅在 PostgreSQL 数据卷第一次初始化时执行；已有 volume 上新增 init 脚本不会自动运行。当前测试 fixture 还存在：

```python
try:
    subprocess.run(..., check=True)
except Exception:
    pass
```

这会吞掉迁移失败。

要求：

1. 为 Docker 开发环境提供幂等的测试数据库确保机制：数据库不存在时创建，存在时不报错；不得依赖删除 volume 后重新初始化。
2. 测试数据库创建失败必须明确失败，不得 skip 后宣称全量通过。
3. Alembic `upgrade head` 失败必须让 pytest 失败，并输出 stdout/stderr；禁止 `except: pass`。
4. 测试开始前验证 `paperlens_test` 的 Alembic revision 为 `003_normalized_and_error` 或当时真实 head。
5. 每个集成测试后可靠清理测试数据。由于 BackgroundTasks 会使用独立 Session 并 commit，可使用针对测试库的 TRUNCATE ... CASCADE、确定性删除或其他可靠方案；不得依赖只回滚请求 Session。
6. Docker 全量测试必须 0 skipped。宿主机没有 PostgreSQL 时可以跳过明确标记的 integration 测试，但汇报必须如实写通过数和跳过数，不能称为全量通过。
7. 建议增加 Docker 专用强制变量，例如 `PAPERLENS_REQUIRE_TEST_DB=true`；该模式下 TEST URL 缺失、测试库不可连接或数据库名不正确都必须 fail。
8. 验证开发库隔离：
   - 测试前记录 `paperlens.papers` 数量
   - 运行完整 Docker pytest
   - 测试后再次查询
   - 两次数量必须严格相等
   - 同时证明测试期间数据真实进入过 `paperlens_test`，并在测试结束后被清理
9. 禁止执行 `docker compose down -v` 或删除现有数据库卷。

三、重写会空跑或弱断言的后端测试

当前测试存在以下失真：

1. Evidence 详情测试使用：

```python
if len(evidences) > 0:
    ...
```

如果没有 Evidence，测试直接通过，根本不会调用详情接口。
2. 路径穿越文件名测试只检查响应中的 filename，没有查询数据库 storage_key。
3. 多项 PDF 测试只在 `for evidence in evidences` 中断言，但未先断言 Evidence 非空，可能空跑。
4. `test_evidence_char_range_null_on_mismatch` 没有制造 mismatch，只重复验证正常匹配。
5. `test_pdf_parse_exception_closes_doc` 只是测试 PyMuPDF 自己的 context manager，没有调用 `parse_pdf()`，并未验证被测代码关闭文档。
6. API 测试依赖 `time.sleep(3)`，慢且不确定。

要求：

1. Evidence 详情 API 测试必须确定性地在测试库创建 Paper 和 Evidence，或确定性地产生 Evidence；禁止 `if len(...) > 0`。
2. 严格断言有效 Evidence 详情返回 200，且逐字段验证：
   - id
   - quoted_text
   - page_number
   - bbox_x0/y0/x1/y1
   - char_start/char_end
   - evidence_type
   - section_id
   - chunk_id
3. 404 测试使用格式合法但不存在的 UUID；422 测试继续覆盖非法 UUID。
4. 路径文件名测试必须从当前测试 Session 查询 Paper，严格断言：

```text
filename == passwd.pdf
storage_key == papers/{paper_uuid}/source.pdf
```

并证明查询连接的数据库名为 `paperlens_test`。
5. 所有依赖 Evidence 的 parser 测试先 `assert evidences`，不得通过空列表绕过。
6. 真正构造 char range mismatch，严格断言 char_start 和 char_end 均为 null，并断言 warning 日志存在。
7. 真正调用 `parse_pdf()` 的异常路径并验证文档被关闭，可通过受控 mock/spy 实现；不得只测试第三方 context manager。
8. 删除固定 `time.sleep()`。对 BackgroundTasks/状态轮询使用确定性等待、直接调用服务或有上限的轮询 helper，超时必须 fail。
9. 增加测试证明后台解析使用测试库：上传后最终 Paper、Page、Evidence 均只能在 `paperlens_test` 查到，开发库数量不变。
10. 测试名、测试内容和 PROGRESS 汇报必须一致，不得把“字段存在”写成“完整闭环已验证”。

四、修复 UploadFile、临时文件和失败信息安全

当前 `upload_paper()` 只在成功读完文件后调用 `await file.close()`：扩展名错误、超限 AppError、读取异常等路径不能保证关闭。当前 `_process_paper()` 还执行：

```python
paper.error_message = str(e)[:500]
```

这可能把服务器路径、库错误或内部实现细节展示给前端，与“安全失败原因”要求冲突。

要求：

1. 使用外层 `try/finally` 保证 UploadFile 在所有路径关闭，包括：
   - 扩展名错误
   - 魔数错误
   - 文件超限
   - `file.read()` 异常
   - storage.save 异常
   - DB commit 异常
   - 正常成功
2. NamedTemporaryFile 必须在所有路径关闭；临时文件必须在所有失败路径删除；成功交给后台任务后只由后台任务最终删除，避免重复删除和遗留。
3. 增加针对上述关键路径的资源清理测试，至少证明 UploadFile.close 被调用且临时文件不存在。
4. 实现安全错误映射函数。允许前端展示的示例：
   - `OCR_NOT_SUPPORTED` → “扫描型 PDF 暂不支持，请上传可提取文本的 PDF”
   - 页数超限 → “PDF 页数超过系统限制”
   - 其他解析异常 → “论文解析失败，请稍后重试或重新上传”
5. 完整异常堆栈仅写服务器日志；禁止把原始 `str(e)` 保存到 Paper.error_message 或返回给客户端。
6. 增加测试，使用包含本地路径、SQL 或内部异常文本的异常，断言 API/数据库中的 error_message 不包含这些内部信息。
7. `_extract_tables()` 中目前仍有静默 `continue/pass`。对页级和文件级表格提取异常记录 debug 或 warning 日志，包含 paper/page 上下文；允许降级为空表格，但不得完全静默。
8. `papers.py` 中对 PaperTable 执行 `db.add()` 的 try/except 并不能捕获 commit 时的约束错误。应在加入前验证数据，或用可靠的降级边界；不得保留看似容错、实际无法捕获的代码并在文档中宣称已修复。

五、修复 ORM metadata 与已应用约束不一致

当前 models.py 使用：

```python
f"status IN {PaperStatus._member_names_}"
```

Python list 会生成方括号形式，和 002 migration 中正确的 SQL `IN ('A', 'B')` 不一致，也可能让 `Base.metadata.create_all()` 生成非法 SQL。

要求：

1. 修复 PaperStatus、TaskStatus、EvidenceType、FindingType、VerificationStatus、ExportStatus 的 ORM CheckConstraint SQL。
2. ORM metadata 表达式必须与 002_constraints.py 的实际约束一致。
3. 不要改写已应用的 002 migration；如果数据库实际结构不需要变化，则不新增无意义 migration。
4. 增加 metadata DDL 编译或临时测试库 create_all 测试，证明不会生成 `IN [...]`。
5. 执行 `alembic check` 或等价核验，确保 model metadata 与 migration head 没有意外差异。

六、修复前端错误闭环和高亮防御

当前 PaperDetailView 仍有以下问题：

1. 初始 `getPaper()` 失败只 `console.error`，页面永久显示“加载中...”，没有可见错误或重试。
2. 轮询失败也只写 console。
3. `highlightRange` 只检查 offset 边界，没有验证切片结果是否等于 selectedEvidence.quoted_text；数据不一致时会错误高亮。
4. 同页 Evidence 导航时，tab watcher 与 `applyHighlightAndScroll()` 可能重复调用 `loadPage()`。
5. 快速切页或连续点击 Evidence 时，旧请求可能晚返回并覆盖新页面。

要求：

1. 增加论文详情加载错误状态和可见重试按钮；重试成功后恢复正常视图。
2. 轮询请求失败时显示可见错误和重试/继续入口，且不会泄漏计时器。
3. 高亮前严格验证：

```text
normalized_text_content[char_start:char_end] == quoted_text
```

不相等时不得高亮错误文本，显示“该证据暂不支持精确高亮”。
4. 重构 Evidence 导航，保证每次导航只发起一次目标页请求。
5. 点击第 2 页 Evidence 的顺序必须是：保存 Evidence → 切到页面 Tab → 加载第 2 页 → 验证完整 quoted_text → 渲染 mark → nextTick 后滚动。
6. 普通翻页清除选中 Evidence；Evidence 导航翻页保留选中 Evidence。
7. 防止陈旧请求覆盖当前页，可使用递增 request token、AbortController 或等价方案。
8. 继续禁止 `v-html` 和手工 HTML 转义；使用 Vue 文本插值。

七、把前端测试改成真正覆盖需求

当前 7 项 Vitest 虽然通过，但存在：

1. “正确跨页”测试点击的是第 1 页 Evidence，只断言 `getPage(id, 1)`。
2. 页面错误测试使用：

```typescript
expect(error.exists() || pageContent.exists()).toBe(true)
```

即使错误 UI 没出现也能通过。
3. 没有特殊字符/XSS 测试。
4. 没有 PROCESSING → PARSED 后加载章节和 Evidence 的测试。
5. 没有论文详情初次加载失败和重试测试。

要求新增或重写测试，严格覆盖：

1. 点击第 2 页、且 char range 非 null 的 Evidence：
   - 严格断言 `getPage(paperId, 2)` 恰好调用一次
   - 页面指示变为第 2 页
   - `<mark>` 存在
   - `<mark>` 完整文本严格等于 quoted_text
2. 页面 API 失败：
   - 严格断言 `.error-msg` 存在
   - 严格断言错误文本和“重试”按钮存在
   - 点击重试后成功展示页面
   - 禁止 `A || B` 弱断言
3. 初始论文详情 API 失败：显示错误和重试；重试成功后加载论文。
4. PROCESSING → PARSED：使用 fake timers 和顺序 mock，严格断言轮询停止，并调用 listSections、listEvidences。
5. 跨页 char range 为 null：显示准确降级提示，不渲染 mark。
6. offset 在范围内但切片不等于 quoted_text：同样降级，不允许错误高亮。
7. normalized 文本包含 `<script>alert(1)</script>`、`<`、`>`、`&`：
   - DOM 中不存在可执行 script 元素
   - 页面显示原始可读文本
   - 不显示 `&lt;`、`&amp;` 等双重转义字面量
8. 快速连续点击不同页 Evidence：最终只显示最后一次选择的页和高亮。
9. unmount 后 timer 清理，且后续不再调用 API。

测试必须有明确 assertion；不得通过条件分支跳过核心断言。

八、同步文档，纠正虚假的完成状态

当前文档仍存在明显不一致：

1. docs/IMPLEMENTATION_STATUS.md 将“向量索引服务（FAISS）”标为已完成，但仓库中没有 FAISS、embedding 或向量检索实现。
2. P7 上传页面和论文详情/Evidence 高亮已经部分实现，却仍全部标为未开始。
3. data-model.md 的 PaperPage 没有记录 normalized_text_content，char_start/char_end 也没有说明相对于哪个字段。
4. API 页面响应文档没有完整记录 normalized_text_content。
5. 全局验证表仍保留 P2.1 的 32/37/4 和 migration 002，和 P2.2 的 36/44/7、migration 003 冲突。
6. README 没有清楚说明 Nginx 60MB 是代理上限、业务限制仍为 50MB。

要求同步：

- README.md
- docs/api-contract.md
- docs/architecture.md
- docs/data-model.md
- docs/security-design.md
- docs/IMPLEMENTATION_STATUS.md
- docs/PROGRESS.md

必须做到：

1. 将未实现的 FAISS/向量索引改为未开始或进行中，不得虚报完成。
2. 如实标记前端已完成和部分完成项。
3. 记录 `003_normalized_and_error` migration。
4. 明确 Evidence 的 quoted_text、char_start、char_end 相对于 PaperPage.normalized_text_content。
5. 明确 Nginx 60MB 代理上限与后端 50MB 业务上限。
6. 明确 BackgroundTasks 仅为 MVP，当前不保证进程崩溃后的任务恢复。
7. 明确测试强制使用 paperlens_test，且后台任务也使用同一测试库。
8. 明确当前未实现真实 PDF.js 坐标覆盖层、FAISS、LLM 审阅、指标提取和报告导出。
9. 历史 P2.1/P2.2 记录可以保留，但“当前验证结果”必须只展示最新、真实结果，并注明测试环境。

九、真实验证

完成后重新构建并复测，不得沿用旧输出。

1. 启动并查看容器：

```powershell
cd D:\shixi\PaperLens
docker compose up --build -d
docker compose ps
docker compose logs --tail 200
```

2. 记录开发库测试前数量：

```powershell
docker compose exec -T postgres psql -U paperlens -d paperlens -Atc "SELECT count(*) FROM papers"
```

3. 核对测试库存在、迁移到 head，并证明应用测试 Engine 数据库名为 paperlens_test。

4. 运行 Docker 后端全量测试：

```powershell
docker compose exec -T backend python -m pytest -q -rs
```

必须 0 failed、0 errors、0 skipped。输出中必须包含真正执行的数据库集成测试。

5. 测试后再次查询开发库 papers 数量，必须与测试前严格相等。

6. 查询 paperlens_test，证明测试清理结束后业务表无残留测试数据。

7. 运行：

```powershell
docker compose exec -T backend alembic current
docker compose exec -T backend alembic check
cd frontend
npm test -- --run
npm run build
```

8. 真实端到端回归：
   - 通过 `http://localhost:3000` 上传文本型 PDF，进入 PROCESSING 并最终 PARSED
   - 页面、章节、Evidence 列表、Evidence 详情均为 200
   - 点击第 2 页 Evidence，跳页并高亮完整 quoted_text
   - 11.3MB PDF 经 Nginx 上传不返回 413
   - 大于 50MB 文件仍被前端或后端拒绝并显示中文错误
   - 解析失败只展示安全错误，不出现服务器路径或内部异常

任何失败都必须修复后重新执行对应验证，不得只把失败写进 PROGRESS 后结束。

十、范围限制与汇报

本轮只完成 P2.3，不进入 P3，不实现 FAISS 或 LLM。

不得修改：

```text
.arts/
.codeartsdoer/
.git/
```

不要 git commit，不写入真实密钥，不删除数据库 volume，不自动清理无法确认归属的开发库旧记录。

完成后在 docs/PROGRESS.md 末尾追加 `P2.3 — 测试隔离与验收真实性修复`，必须如实记录：

- 测试前后开发库 papers 数量及是否一致
- 测试期间应用 Engine、后台任务和 Alembic 实际连接的数据库名
- paperlens_test 的创建、迁移和清理方式
- 后端通过/失败/跳过数量
- 前端测试数量、关键断言和构建结果
- UploadFile/临时文件清理验证
- 安全 error_message 验证
- ORM CheckConstraint metadata 验证
- 第 2 页 Evidence 跨页高亮结果
- 11.3MB 上传和大于 50MB 拒绝结果
- 尚未完成项

禁止把未执行的条件分支、skip、空循环或弱断言计为已验证。只有真实执行且严格断言通过的项目才能标记为完成。
~~~~

---

## 07 — P2.4 事务边界与验收收口

> 来源：`docs/CODEARTS_NEXT_PROMPT.md` 覆盖补丁原文（2026-07-13，rollout 行 966）

~~~~text
继续修复 D:\shixi\PaperLens 项目。

本轮定义为 P2.4：修复 P2.3 遗留的事务边界、测试库冷启动、资源关闭和前端轮询/高亮降级问题，完成 P2 解析闭环的最后收口。

P2.3 的数据库隔离主目标已经真实生效。外部独立复测结果：

```text
Docker backend pytest: 46 passed, 0 skipped
frontend Vitest:        11 passed
frontend build:         success
开发库 papers:          测试前 25，测试后 25
测试库 papers:          测试后 0
alembic check:          No new upgrade operations detected
```

不要推翻或重复重写已经正确的测试库 Engine 隔离方案。但代码审查确认仍有数个运行级缺陷和弱断言，P2 暂不能结束。禁止开始 P3、LLM、MaaS/ModelArts、FAISS、指标提取、Excel 或报告导出。

开始前完整阅读：

- docs/PROGRESS.md
- backend/paperlens/core/database.py
- backend/paperlens/api/papers.py
- backend/paperlens/services/pdf_parser.py
- backend/tests/conftest.py
- backend/tests/test_api/test_health.py
- backend/tests/test_services/test_pdf_parser.py
- frontend/src/views/PaperDetailView.vue
- frontend/src/tests/PaperDetailView.test.ts
- docker-compose.yml
- README.md
- docs/IMPLEMENTATION_STATUS.md
- docs/api-contract.md
- docs/architecture.md
- docs/data-model.md
- docs/security-design.md

先给出简短计划，然后直接实施。所有测试必须验证真实行为，禁止只增加测试名称或放宽断言。

一、真正保证 UploadFile 和临时文件在所有路径关闭

当前 `upload_paper()` 仍有明确缺陷：

```python
filename = _sanitize_filename(raw_filename)

if not filename.lower().endswith(".pdf"):
    raise AppError(...)

try:
    ...
```

扩展名错误发生在 `try/finally` 之外，因此服务端 UploadFile 没有执行 `await file.close()`。另外，读取循环异常时 NamedTemporaryFile 句柄也不一定先关闭，外层代码就尝试删除路径。

要求：

1. 将扩展名校验也纳入最外层资源管理边界。
2. UploadFile 在以下每条路径都必须且只能关闭一次：
   - 非 PDF 扩展名
   - PDF 扩展名但魔数错误
   - 文件超过业务上限
   - `await file.read()` 抛异常
   - hash 计算异常
   - storage.save 异常
   - DB commit 异常
   - 正常上传并交给 BackgroundTasks
3. NamedTemporaryFile 使用明确的 context/finally 管理，任何异常发生前先关闭句柄，再删除文件。
4. 未成功交给后台任务的临时文件必须由请求路径删除；已成功交给后台任务的临时文件只能由 `_process_paper()` 最终删除。
5. storage.save 成功但后续 Paper 构造、DB commit 或响应构造失败时，存储对象不能遗留。删除失败要记录 warning，不能静默 `pass`。
6. 增加直接针对服务端 UploadFile 的单元测试或可靠 spy。仅关闭客户端上传文件句柄不能证明服务端 `UploadFile.close()` 被调用。
7. 每个资源测试严格断言 close 调用次数和临时路径不存在，不能只断言 HTTP 状态码。

二、修复测试数据库“已存在时可用、缺失时无法创建”的冷启动问题

当前 `_ensure_test_database()` 先连接 `paperlens_test`，再检查该数据库是否存在：

```python
conn = psycopg2.connect(test_database_url)
SELECT 1 FROM pg_database ...
CREATE DATABASE paperlens_test
```

如果 `paperlens_test` 根本不存在，第一步连接已经失败，无法执行 CREATE DATABASE。更早的 `_db_available()` 也会返回 false，使集成测试直接 skip，`_ensure_test_database()` 根本不会运行。

要求：

1. 测试库确保逻辑必须连接维护库 `postgres` 或已知存在的开发库，只使用同一 host/user/password，然后查询并幂等创建 `paperlens_test`。
2. 创建完成后再连接 `paperlens_test`、执行 Alembic upgrade head、校验 revision。
3. Docker 强制模式不得在 `_db_available()` 阶段因为测试库尚不存在而 skip。
4. 在 docker-compose backend 环境中显式增加：

```text
PAPERLENS_REQUIRE_TEST_DB=true
```

5. 当强制模式为 true 时，缺失 TEST URL、数据库名不是严格的 `paperlens_test`、创建失败、迁移失败或连接失败都必须 fail，禁止 skip。
6. 宿主机没有 PostgreSQL 时仍可诚实 skip integration 测试，但 Docker 全量测试必须 0 skipped。
7. 不要通过删除当前 `paperlens_test` 或 PostgreSQL volume 来测试冷启动。使用 mock、独立辅助函数测试，或创建和删除一个不会碰业务数据的专用临时数据库名；任何临时数据库操作必须有严格命名守卫。
8. 测试库初始化代码应放在可复用 helper/fixture 中，不要把数据库管理逻辑继续堆在 `test_health.py`。

三、测试清理必须 fail-closed，禁止继续吞异常

当前 `_truncate_test_tables()` 有两层静默异常：

```python
for t in tables:
    try:
        TRUNCATE ...
    except Exception:
        pass
...
except Exception:
    pass
```

这意味着清理失败后测试仍会显示通过，残留数据可能污染后续测试。

要求：

1. 删除所有 cleanup `except: pass`。
2. fixture 使用 `try/finally`，无论测试通过或失败都执行清理。
3. 优先使用一条 `TRUNCATE table1, table2, ... CASCADE`，或从 SQLAlchemy metadata/数据库 schema 安全获得业务表集合，避免逐表失败后继续。
4. 清理连接和 cursor 也必须用 context manager/finally 关闭。
5. 清理失败必须让测试 session 明确失败，并输出数据库名和原始异常。
6. 清理前后都严格断言当前数据库名为 `paperlens_test`；禁止对开发库执行 TRUNCATE。
7. 清理结束后查询所有业务表，严格断言无测试残留；至少不能只查 papers 一张表。
8. 增加 cleanup 失败测试，证明异常不会被吞掉。

四、修复 PaperTable 降级时回滚整篇论文的问题

当前 `_process_paper()` 对每张表执行 `db.flush()`，失败后调用：

```python
db.rollback()
```

这会回滚当前整个事务，连此前已加入的 PaperPage、PaperSection、PaperChunk 也一起撤销。随后代码继续添加 Evidence，而 `chunk_id_map` 仍引用已回滚的 chunk ID，最终可能导致外键失败并把整篇论文标为 FAILED。该实现不是“表格失败可降级”。

要求：

1. 表格单项失败只能回滚该表格，不能回滚页面、章节、分块和其他表格。
2. 使用 `db.begin_nested()`/SAVEPOINT 或先完成严格数据验证后跳过非法表格；禁止在表格循环的局部异常中调用整个 Session 的 `rollback()`。
3. 单张表失败后：
   - 论文仍可 PARSED
   - PaperPage/PaperSection/PaperChunk/Evidence 均正常保存
   - 合法表格正常保存
   - 仅非法表格被跳过
   - warning 日志包含 paper_id、page_number、table_index
4. 如果页面/章节/分块/Evidence 等核心数据失败，仍应回滚整篇解析并将 Paper 标为 FAILED。
5. 增加真实 PostgreSQL 集成测试：受控 mock `parse_pdf()` 返回页面、章节、分块、Evidence、一个合法表格和一个违反约束的表格，严格断言上述降级行为。
6. 测试必须能在旧实现上失败，不能只直接调用 bbox 交换代码。

五、修正后端仍然存在的弱断言

当前 Evidence 详情测试包含永远为真的断言：

```python
assert detail["char_start"] is not None or detail["char_start"] is None
assert detail["char_end"] is not None or detail["char_end"] is None
```

它没有严格验证 bbox、char range、section_id 和 chunk_id，与 P2.3 汇报不一致。

要求：

1. 删除所有恒真断言。
2. Evidence 详情测试确定性插入完整字段值，严格逐字段比较：
   - id
   - quoted_text
   - page_number
   - bbox_x0/y0/x1/y1
   - char_start/char_end
   - evidence_type
   - section_id
   - chunk_id
3. 另设 nullable 字段测试，不要把 nullable 和完整字段测试混在一起。
4. error_message 安全测试必须注入包含真实内部信息模式的异常，例如：

```text
/tmp/private/source.pdf
C:\secret\source.pdf
postgresql://user:password@host/db
SELECT * FROM secret_table
Traceback ...
```

严格断言数据库和 API 均只包含安全映射后的中文消息，不包含任何注入内容。
5. 为非 PDF 扩展名、读取异常、临时文件清理、表格 SAVEPOINT、cleanup 失败分别增加能失败的行为测试。
6. 整理重复的“等待 Paper 终态”代码为有超时、返回终态并在超时/FAILED 时给出明确信息的 helper。

六、修复前端降级提示、Evidence 导航和轮询定时器

当前 PaperDetailView 仍有以下问题：

1. `highlightDegraded` 只在 char_start/char_end 为 null 时为 true。offset 越界或切片与 quoted_text 不一致时，`highlightRange` 返回 null，但不会显示“该证据暂不支持精确高亮”。
2. `retryPoll()` 直接调用 `load()`，但原有 interval 在轮询失败时没有停止。重试后可能再创建一个 interval，造成重复轮询和计时器泄漏。
3. `load()` 每次看到 PROCESSING 都直接 `setInterval()`，没有先清理既有 timer。
4. 点击当前页 Evidence 时 `isNavigatingToEvidence = true`，但 currentPage 没变化，watcher 不会复位该标志；后续普通跳页可能被错误当成 Evidence 导航。
5. 切换到页面 Tab 的 watcher和 `goToEvidence()` 都可能调用 `loadPage()`，造成重复请求。

要求：

1. 只要已选择 Evidence 且无法形成严格匹配的 highlightRange，包括 null、越界、start>=end、文本 mismatch，都显示统一降级提示，且不渲染 mark。
2. 抽取 `stopPolling()` 和 `startPolling()`：任何时刻最多一个 timer。
3. 轮询失败时停止当前 timer，再显示错误；点击重试先清理旧 timer，再立即请求一次，根据结果决定是否重新开始轮询。
4. PROCESSING → PARSED/FAILED、详情重新加载、组件卸载时都必须停止 timer。
5. 重构页面导航为单一入口，普通翻页/跳页清除 Evidence，Evidence 导航保留 Evidence；不要依赖可能残留的布尔标志。
6. 每次用户动作只请求一次目标页。tab watcher、page watcher 和 goToEvidence 不得竞争发请求。
7. 继续保留 pageRequestId 或等价的陈旧响应防护。

七、把 11 项前端测试改为真实验收测试

当前测试仍有以下缺口：

1. 页面错误测试只检查“重试”按钮存在，没有点击重试并验证恢复。
2. 初始详情失败测试也没有点击重试。
3. mismatch 测试只断言没有 mark，没有断言降级提示存在。
4. rapid evidence 测试顺序等待每个请求完成，没有制造“旧请求晚于新请求返回”，因此没有验证 pageRequestId。
5. 没有轮询失败 → 点击重试 → 只有一个 timer 的测试。
6. XSS mock 使用字符串 `&amp;`，没有验证原始 `&` 字符的显示。

要求新增或重写严格测试：

1. 页面加载失败后点击重试，断言第二次 getPage 成功、错误消失、页面内容出现。
2. 初始 getPaper 失败后点击重试，断言论文详情、章节和 Evidence 正常加载。
3. mismatch、越界和 null range 三种情况都断言：降级提示存在、mark 不存在。
4. 使用可控 deferred Promise：先请求第 1 页，再请求第 2 页；让第 2 页先返回、第 1 页后返回，最终 DOM 必须仍显示第 2 页及其高亮。
5. 同一 Evidence 导航严格断言目标 `getPage()` 调用一次，禁止仅使用 `toHaveBeenCalledWith`。
6. 轮询失败后断言旧 timer 已停止；点击重试后任意时刻只有一个 timer；PARSED 后 timer 清零且不再调用 API。
7. XSS 文本包含原始 `<script>`、`<b>`、`<`、`>`、`&`，断言无可执行元素、无双重转义字面量、原始可读字符存在。
8. 每项测试结束恢复 fake timers 并 unmount，避免测试间泄漏。

八、完成文档同步

P2.3 后文档仍有未同步项：

1. docs/IMPLEMENTATION_STATUS.md 的 P7-01“论文上传页面”仍标为未开始，但 UploadView 已实现。
2. P7-02 将“审阅结果展示”和“Evidence 高亮”混在一个条目中；审阅结果尚未实现，但论文详情、页面与 Evidence 高亮已经部分实现，应拆分或标为部分完成。
3. README 没有明确记录 Nginx 60MB 代理上限与后端 50MB 业务上限。
4. README/文档没有清楚说明测试强制使用 paperlens_test 以及清理失败会使测试失败。
5. architecture/security-design 中 FAISS 描述容易被读成当前实现，应明确标注为规划方案。

同步以下文件：

- README.md
- docs/IMPLEMENTATION_STATUS.md
- docs/api-contract.md
- docs/architecture.md
- docs/data-model.md
- docs/security-design.md
- docs/PROGRESS.md

要求：

1. 如实标记已实现、部分实现和未实现功能。
2. 明确当前前端只展示 normalized 文本高亮，不是 PDF.js bbox 覆盖层。
3. 明确 FAISS、LLM 审阅、指标提取、实验数据分析和报告导出均未实现。
4. “当前验证结果”使用本轮最新实测数据；历史阶段数据可以保留但不能与当前表混淆。

九、真实验证

完成后重新构建容器并独立复测，禁止沿用旧输出：

```powershell
cd D:\shixi\PaperLens
docker compose up --build -d
docker compose ps
docker compose logs --tail 200
```

记录开发库测试前数量：

```powershell
docker compose exec -T postgres psql -U paperlens -d paperlens -Atc "SELECT count(*) FROM papers"
```

运行：

```powershell
docker compose exec -T backend python -m pytest -q -rs
docker compose exec -T backend alembic current
docker compose exec -T backend alembic check
cd frontend
npm test -- --run
npm run build
```

验收要求：

1. Docker backend：0 failed、0 errors、0 skipped。
2. 测试前后开发库 papers 数量严格相等。
3. 测试库所有业务表清理后无测试残留。
4. 非 PDF 扩展名等所有上传路径均证明服务端 UploadFile 已关闭。
5. 受控非法表格只被跳过，论文仍 PARSED，核心解析数据完整。
6. cleanup 失败测试证明异常不会被吞掉。
7. 前端页面/详情重试真正恢复。
8. 轮询始终最多一个 timer。
9. 陈旧页面响应不能覆盖最后选择。
10. mismatch/越界/null 均显示降级提示。
11. Alembic 无未生成差异。
12. 通过 `http://localhost:3000` 完成一次真实 PDF 上传 → PARSED → Evidence → 跨页高亮回归。

任何失败必须修复并重新执行对应验证，不得仅记录失败后结束。

十、范围限制与汇报

本轮只完成 P2.4，不进入 P3，不实现 FAISS 或 LLM。

不得修改：

```text
.arts/
.codeartsdoer/
.git/
```

不要 git commit，不写入真实密钥，不删除数据库 volume，不自动清理无法确认归属的开发库记录。

完成后在 docs/PROGRESS.md 末尾追加 `P2.4 — 事务边界与验收收口`，必须如实记录：

- 开发库测试前后数量
- 测试库冷启动与强制守卫验证
- 测试库全业务表清理结果
- UploadFile 每条路径的关闭验证
- 临时文件与存储对象清理验证
- PaperTable SAVEPOINT 降级结果
- 后端通过/失败/跳过数量
- 前端测试数量及新增的严格场景
- 轮询 timer 数量验证
- 陈旧请求防护验证
- 前端构建结果
- 文档状态修正
- 尚未完成项

禁止把 skip、恒真断言、未点击的重试按钮、未制造乱序的并发测试或被吞掉的异常计为验证通过。
~~~~

---

## 08 — P2.5 验收去伪与并发翻页修复

> 来源：`docs/CODEARTS_NEXT_PROMPT.md` 覆盖补丁原文（2026-07-13，rollout 行 1058）；生成后改由码道实施，未再投递码道

~~~~text
继续修复 D:\shixi\PaperLens 项目。

本轮定义为 P2.5：消除 P2.4 中仍然存在的 skip、未触发被测路径的假测试和并发翻页竞态，完成 P2 的可信验收。

P2.4 的主要实现方向正确，外部独立复测确认：

```text
Docker backend pytest: 49 passed, 1 skipped
frontend Vitest:        14 passed
frontend build:         success
开发库 papers:          测试前 27，测试后 27
测试库 papers:          测试后 0
alembic check:          No new upgrade operations detected
```

但代码审查确认多项测试没有真正触发其声称验证的路径，且前端仍会丢弃加载中的后续翻页请求。因此禁止开始 P3、LLM、MaaS/ModelArts、FAISS、指标提取、Excel 或报告导出，先完成本轮。

开始前完整阅读：

- docs/PROGRESS.md
- backend/paperlens/api/papers.py
- backend/tests/db_helpers.py
- backend/tests/conftest.py
- backend/tests/test_api/test_health.py
- frontend/src/views/PaperDetailView.vue
- frontend/src/tests/PaperDetailView.test.ts
- docker-compose.yml
- README.md
- docs/IMPLEMENTATION_STATUS.md
- docs/architecture.md
- docs/data-model.md
- docs/api-contract.md
- docs/security-design.md

先给出简短计划，然后直接实施。不得通过删除测试、放宽断言或新增无关测试来改变数字。

一、消除 Docker 中唯一的 skipped 测试

当前唯一跳过项是：

```text
SKIPPED tests/test_api/test_health.py:284:
No evidence with null char_start in this test run
```

对应测试先上传普通 PDF，再查询解析器是否“碰巧”产生 char_start=null；没有就 `pytest.skip()`。这不是确定性测试。

要求：

1. `test_evidence_nullable_fields` 必须直接、确定性地在 `paperlens_test` 创建 Paper 和 Evidence，明确设置：

```text
char_start = null
char_end = null
bbox 可设为 null 或指定固定值
section_id = null
chunk_id = null
```

2. 调用真实 `GET /api/v1/evidences/{id}`，严格断言 200 和所有 nullable 字段。
3. 禁止依赖 PDF 解析结果产生 null，禁止条件 skip。
4. Docker 全量测试必须 0 skipped。强制测试库模式下任何数据库测试都不得 skip。
5. 同时检查其他 `pytest.skip`/`skipif`：宿主机无 PostgreSQL时可以诚实跳过 integration；Docker `PAPERLENS_REQUIRE_TEST_DB=true` 时必须 fail 或真实执行。

二、修复 UploadFile 资源测试“创建了 mock 但从未使用”的问题

当前测试：

```python
with patch("paperlens.api.papers.UploadFile"):
    mock_file = AsyncMock()
    ...
    resp = await client.post(...)
```

`mock_file` 从未传给 `upload_paper()`，FastAPI 仍使用请求解析产生的真实 UploadFile；测试也没有任何 `mock_file.close.assert_*`。因此测试名称虽然是 `test_upload_non_pdf_closes_file`，实际只验证了 HTTP 415。

要求：

1. 删除无效的 `patch("...UploadFile")` 测试写法。
2. 对资源关闭行为直接调用 `upload_paper()` 或提取可单测的上传服务函数，将真正的 AsyncMock UploadFile、BackgroundTasks 和受控 DB/Storage 传入。
3. 分别验证以下路径，每条路径严格断言服务端 `close` 恰好调用一次：
   - 非 PDF 扩展名
   - PDF 魔数错误
   - 超过大小限制
   - `file.read()` 抛异常
   - hash 抛异常
   - storage.save 抛异常
   - DB commit 抛异常
   - 正常成功交给后台任务
4. HTTP 集成测试可保留，但不能代替资源单元测试。
5. 测试必须在旧实现或移除 close 时失败。

三、修复 NamedTemporaryFile 和 storage object 的真实清理边界

当前读取异常路径：

```python
tmp = tempfile.NamedTemporaryFile(...)
try:
    chunk = await file.read(...)
except Exception:
    os.unlink(tmp_path)
```

读取抛异常时没有先执行 `tmp.close()` 就删除路径。在 Linux 中 unlink 可能成功，但文件句柄仍未正确关闭；Windows 下可能直接删除失败。

此外，storage.save 成功后如果 Paper 构造、非 commit 的 DB 操作、background task 注册或响应构造失败，外层异常路径没有统一删除 storage object。

要求：

1. 重构 `upload_paper()` 为单一、清晰的资源所有权模型，尽量避免 `file_closed` 标志和多处分散 close。
2. NamedTemporaryFile 必须通过 context manager 或外层 finally 保证先关闭句柄，再尝试删除路径。
3. 所有未成功交给 BackgroundTasks 的路径都删除临时文件。
4. storage object 保存成功后，只有 Paper 已提交且后台任务已成功注册才转移所有权；此前任何异常都删除 storage object。
5. storage.delete 失败记录 warning，但不泄露内部信息给客户端。
6. 增加真实测试：
   - 读取异常后临时文件句柄关闭且路径不存在
   - storage.save 后 Paper 构造/DB/任务注册失败，storage.delete 被调用一次
   - 成功路径不会被请求 finally 提前删除临时文件或 storage object
7. 不允许只 patch `os.path.exists` 后断言 HTTP 状态。

四、让 SAVEPOINT 测试真正触发数据库约束错误

当前 `test_table_savepoint_degradation` 的所谓非法表格只是 bbox 反向：

```python
bbox_x0 = 200
bbox_x1 = 72
```

但生产代码在写数据库之前会交换 x0/x1 和 y0/y1，使其变成合法表格。因此 SAVEPOINT 从未发生 IntegrityError，测试只断言 `len(tables) >= 1`，即使两个表都成功也会通过。

要求：

1. 构造不会被预处理修复、且确定违反 PostgreSQL 约束的非法表格，例如：
   - `page_number = 0`
   - 或 `table_index = 0`
   - 或与合法表格制造确定性的唯一键冲突
2. 同一 parse result 包含一个合法表格和一个非法表格。
3. 使用真实 PostgreSQL 和真实 `_process_paper()`，严格断言：
   - warning 日志确实出现且包含 paper/page/table index
   - 论文最终为 PARSED
   - Page、Section、Chunk、Evidence 各自数量准确
   - PaperTable 恰好只有 1 条
   - 保存的是合法表格的固定字段
   - 非法表格不存在
4. 测试必须证明旧的全局 `db.rollback()` 实现会失败。
5. 生产实现可使用 `with db.begin_nested():` 简化 SAVEPOINT 生命周期，避免手工 transaction 对象在异常边界上遗漏状态。

五、清理失败测试必须真正模拟 TRUNCATE/连接失败

当前：

```python
def test_cleanup_failure_propagates():
    with pytest.raises(AssertionError, match="Refusing to truncate"):
        truncate_test_tables(dev_url)
```

它只测试“拒绝开发库”守卫，并没有测试连接或 TRUNCATE 失败是否传播。`test_table_savepoint_degradation` 的 finally 仍有：

```python
try:
    truncate_test_tables(...)
except Exception:
    pass
```

这再次把清理失败吞掉。

要求：

1. 删除测试 finally 中所有 cleanup `except: pass`。
2. 使用 pytest fixture 的 `yield` + `finally` 统一清理，或让清理异常自然使测试失败。
3. 分开测试：
   - 非测试库 URL 被安全守卫拒绝
   - psycopg2 connect 失败向上传播
   - cursor.execute(TRUNCATE) 失败向上传播
   - verify residuals 发现任一业务表非空时失败并指出表名
4. mock 必须作用于 db_helpers 实际调用的对象，严格断言异常类型/消息，不得仅测试自己构造的 AssertionError。
5. Docker 全量测试完成后真实查询所有业务表为 0。

六、修复 `pageLoading` 导致后续翻页请求被直接丢弃

当前：

```typescript
async function loadPage(pageNumber: number) {
  if (!paper.value || pageLoading) return
  const requestId = ++pageRequestId
  ...
}
```

当第 1 页请求仍在进行时，用户点击第 2 页，第二次 `loadPage(2)` 直接 return，甚至不会递增 requestId。随后第 1 页返回后仍会写入 DOM，造成页码显示第 2 页、正文却是第 1 页。

要求：

1. 不得用全局 `pageLoading` 阻止新的目标页请求。
2. 每次导航都递增 requestId，并真实发起最新目标页请求；旧响应返回时因为 token 过期而被忽略。
3. loading 状态只由最新 request 管理，旧请求 finally 不得关闭新请求的 loading。
4. 可使用 AbortController 取消旧 Axios 请求，或保留 request token；无论方案都不能丢弃最新导航。
5. 页面、Evidence、普通翻页和输入跳页应走单一导航入口，避免 tab watcher 与 currentPage watcher竞争。
6. 同一个用户动作对目标页最多发起一次请求。

七、重写陈旧响应和“恰好一次”测试

当前陈旧响应测试创建了 deferred Promise，但没有先证明第 1 页请求实际使用了该 Promise。Promise executor 在创建时就给 `resolvePage1` 赋值，因此调用 resolver 并不能证明任何请求正在等待它。

当前“exactly once”测试实际写的是：

```typescript
expect(page1Calls).toBeLessThanOrEqual(1)
```

0 次也会通过。

要求：

1. 陈旧响应测试必须按以下顺序：
   - 触发并严格断言 `getPage(id, 1)` 已调用且 Promise 未 resolve
   - 在第 1 页仍 pending 时触发第 2 页导航
   - 严格断言 `getPage(id, 2)` 已调用一次
   - 先 resolve 第 2 页，断言 DOM 显示第 2 页内容/高亮
   - 再 resolve 第 1 页，断言 DOM 仍保持第 2 页
2. 测试要在当前 `if (pageLoading) return` 实现上失败。
3. “恰好一次”使用：

```typescript
expect(pageCalls).toHaveLength(1)
```

或 `toHaveBeenCalledTimes(1)`，禁止 `<= 1`。
4. 额外覆盖快速点击第 1→2→1 页，最终只显示最后一次选择。
5. 每个测试 unmount，deferred Promise 必须在结束前 settle，避免悬挂任务。

八、补齐文档状态

P2.4 只同步了部分文档，仍需修正：

1. docs/IMPLEMENTATION_STATUS.md 的 P2.4-09 将 `49 passed, 1 skipped` 标为“已完成”，应在 P2.5 真实达到 0 skipped 后更新当前结果。
2. P7-02 同时包含“审阅结果展示”和“Evidence 高亮”；审阅结果未实现，但论文详情/页面文本/Evidence 高亮已经完成。拆分条目或明确标为部分完成。
3. architecture.md 和 security-design.md 中 FAISS 仍像当前方案，应明确是规划、尚未实现。
4. 明确当前是 normalized 文本高亮，不是 PDF.js bbox 覆盖层。
5. 当前验证表只写最新结果；历史 P2.2/P2.3/P2.4 数据保留在各自历史小节。

同步：

- README.md
- docs/IMPLEMENTATION_STATUS.md
- docs/architecture.md
- docs/security-design.md
- docs/PROGRESS.md

九、真实验证

完成后重新构建，不得沿用旧结果：

```powershell
cd D:\shixi\PaperLens
docker compose up --build -d
docker compose ps
docker compose logs --tail 200
```

记录开发库测试前数量，然后运行：

```powershell
docker compose exec -T backend python -m pytest -q -rs
docker compose exec -T backend alembic current
docker compose exec -T backend alembic check
cd frontend
npm test -- --run
npm run build
```

测试后再次查询开发库和测试库。

验收要求：

1. Docker backend：0 failed、0 errors、0 skipped。
2. 不再出现 `No evidence with null char_start`。
3. 开发库 papers 测试前后严格相等。
4. paperlens_test 所有业务表清理后为 0。
5. UploadFile 每条指定路径 close 恰好一次。
6. 读取异常时临时文件句柄和路径都已清理。
7. storage 保存后任何未完成所有权转移的失败路径都会回滚。
8. 非法 PaperTable 真正触发数据库约束，最终仅合法表格保存且论文 PARSED。
9. cleanup 连接/TRUNCATE/残留异常均不能被吞掉。
10. 第 1 页 pending 时第 2 页请求真实发起，旧响应不能覆盖新页面。
11. 目标页请求次数严格准确。
12. 前端构建成功，Alembic 无差异。
13. 通过 `http://localhost:3000` 完成真实上传 → PARSED → Evidence → 跨页高亮回归。

任何失败必须修复并重跑对应验证，不得只记录失败后结束。

十、范围限制与汇报

本轮只完成 P2.5，不进入 P3，不实现 FAISS 或 LLM。

不得修改：

```text
.arts/
.codeartsdoer/
.git/
```

不要 git commit，不写入真实密钥，不删除数据库 volume，不自动清理无法确认归属的开发库记录。

完成后在 docs/PROGRESS.md 末尾追加 `P2.5 — 验收去伪与并发翻页修复`，必须如实记录：

- 唯一 skipped 的消除方式
- Docker 后端通过/失败/跳过数量
- 确定性 nullable Evidence API 结果
- UploadFile 各路径 close 调用次数
- 临时文件和 storage 回滚结果
- 真正触发的 PaperTable 约束及 SAVEPOINT 结果
- cleanup 失败传播测试
- 开发库测试前后数量
- 测试库全表清理结果
- 并发翻页请求顺序和最终页面
- 前端严格测试数量与构建结果
- 文档同步结果
- 尚未完成项

禁止把 skip、未使用的 mock、被预处理修复掉的“非法数据”、`>= 1`、`<= 1`、未被请求等待的 deferred Promise 或 cleanup `except: pass` 计为验收通过。
~~~~

---

## 09 — P2.6 ProjectDocs 实现态校准

> 来源：码道根据 ProjectDocs 静态审查结果生成（2026-07-13）

~~~~text
继续维护 D:\shixi\PaperLens 项目。

本轮定义为 P2.6：ProjectDocs 实现态校准与可追溯性修复。目标是让新生成的设计文档准确区分“当前已实现”“仅有数据模型骨架”“规划功能”，修复失效链接和事实漂移，为 P3 开发建立可信基线。

本轮只允许修改文档和项目级研发约定，不修改 backend、frontend、alembic、Docker 配置或业务代码，不实现 P3，不实现 FAISS、语义检索、MaaS/LLM 审阅、指标提取、Excel 分析或报告导出。

开始前完整阅读并以真实代码为准，不得只相信 docs/PROGRESS.md：

- AGENTS.md
- ProjectDocs/project-config.yaml
- ProjectDocs/systemDesign/01-需求细化与决策发现.md 至 08-测试设计.md
- ProjectDocs/specs_SDD/PaperLens/spec.md
- ProjectDocs/specs_SDD/PaperLens/tasks.md
- ProjectDocs/specs_SDD/PaperLens/design/ 下全部文档
- ProjectDocs/sprint/ 下全部文档
- docs/PROGRESS.md
- docs/IMPLEMENTATION_STATUS.md
- README.md
- backend/paperlens/main.py
- backend/paperlens/api/health.py
- backend/paperlens/api/papers.py
- backend/paperlens/models/models.py
- backend/paperlens/schemas/paper.py
- backend/paperlens/core/enums.py
- backend/alembic/versions/ 下全部迁移
- frontend/package.json
- frontend/src/api/index.ts
- frontend/src/router/index.ts
- frontend/src/views/ 下现有页面
- frontend/src/tests/PaperDetailView.test.ts
- backend/tests/ 下现有测试

先给出简短计划，然后直接实施。使用已安装的相关 skill 完成对应文档校准：

1. dev-process-framework：校准 systemDesign/01～06。
2. page-mockup：校准 07-页面设计.md，保留有价值的线框图。
3. fullstack-testing：校准 08-测试设计.md 的当前测试事实和规划测试。
4. function-detail：校准 specs_SDD/PaperLens/ 的 spec、design、tasks。
5. sdd-workflow：校准 sprint 进度。
6. bug-fix-reporter：在 ProjectDocs/bugfix-report/ 生成本轮文档缺陷修复报告。

不得运行 dev-eco-setup，不得安装或更新 skill，不得修改 .arts/、.codeartsdoer/ 或 .skills/。校准应在现有文档上做最小、可审查的修改，不要无差别重写全部文档。

一、修复 SDD 本地链接

当前 ProjectDocs 中检查到 75 个 Markdown 本地链接，其中 48 个目标路径失效，主要集中在 ProjectDocs/specs_SDD/PaperLens/tasks.md：链接文字写着 design/...，实际 target 却缺少 design/ 前缀。

要求：

1. 修复 tasks.md 以及 ProjectDocs 其他文档中的所有失效本地链接。
2. 同时检查锚点，不仅检查目标文件是否存在；标题锚点必须能对应实际章节。
3. 相对路径必须从链接所在 Markdown 文件的位置正确解析。
4. 完成后用可复现的只读检查统计：本地链接总数、失效文件路径数、失效锚点数。
5. 验收必须为失效文件路径 0、失效锚点 0。

二、明确 API 的当前实现态与规划态

真实后端当前只有以下 8 个端点：

- GET /api/v1/health
- POST /api/v1/papers/upload
- GET /api/v1/papers
- GET /api/v1/papers/{paper_id}
- GET /api/v1/papers/{paper_id}/pages/{page_number}
- GET /api/v1/papers/{paper_id}/sections
- GET /api/v1/papers/{paper_id}/evidences
- GET /api/v1/evidences/{evidence_id}

在 systemDesign/04、SDD design/09、各模块设计、tasks、sprint 中统一校准：

1. 将以上端点标为“已实现”。
2. DELETE paper、GET paper tables、tasks、reviews、metrics、experiment-files、exports、FAISS index 等接口可以保留为目标设计，但必须逐项标为“规划/未实现”，不能混在已实现清单中。
3. 当前上传接口只接收 file，不接收可选 title；title 使用清洗后的文件名 stem；成功记录和响应状态是 PROCESSING，而不是 UPLOADING。
4. 当前只计算并保存 SHA-256 file_hash，没有按哈希查询、复用或拒绝重复文件。所有“已实现 SHA-256 去重”改为“哈希计算已实现，去重策略未实现/规划”。
5. 当前 Evidence 列表接口不接受 page_number 或 evidence_type 过滤参数。过滤能力只能标为规划。
6. 当前没有 Bearer/JWT 认证；_get_user_id() 固定返回 settings.demo_user_id。认证和用户隔离目标保留为规划，不得写成已启用。
7. FastAPI 当前 Swagger 为 /api/docs，OpenAPI 为 /api/openapi.json；其他地址必须按 main.py 的真实配置描述。
8. 目标 API 契约可以保留，但每个章节或表格必须能一眼区分 CURRENT 与 PLANNED。

三、校准数据模型和“表已存在”与“功能已实现”的边界

以 models.py、Alembic migration 和数据库约束为准：

1. Paper 文档补充真实存在的 error_message。
2. PaperPage 不得把当前不存在的 storage_key 写成已实现字段；如保留，明确标为规划。
3. 关联表真实名称为 finding_evidences，不是 finding_evidence。
4. 字段 nullable、外键 ondelete、唯一约束、CheckConstraint、索引和名称应与 ORM/Alembic 一致；不要编造实际不存在的索引。
5. 明确 14 张业务表的数据库骨架已经存在，但 AnalysisTask、ReviewResult、ReviewFinding、MetricRecord、ExperimentFile、ExperimentResult、ExportReport 对应的服务/API/前端仍未实现。
6. 不得因为 ORM 表存在就把 P3～P6 业务功能标成已完成。

四、校准前端设计和依赖

1. frontend/package.json 当前没有 Element Plus，不能写“基于 Element Plus 构建”。
2. Pinia 当前为 3.x，不是 2.x；Vue、Vue Router、Axios、Vite 等版本按 package.json 描述。
3. 当前实际路由只有 /、/upload、/papers、/papers/:id；P05～P08 路由和页面必须标为规划。
4. 不存在的 components、utils、PollingWrapper、未来 Layout 等可作为建议结构保留，但必须明确是“规划目录/拟新增组件”。
5. 保留 07-页面设计.md 中有价值的 8 页面线框图、交互状态、共享布局和颜色规范，不要把目标原型误写成当前页面已经具备的组件库实现。
6. PaperDetailView.test.ts 当前有 15 个 it 用例。修复 3 份 sprint 文档中“14 项”的旧数字，并全局检查测试数量表述。
7. P2.5 的历史验收结果为 Docker backend 63 passed、0 skipped，frontend 15 passed，build 成功。若本轮未实际重跑，必须标为“P2.5 历史验收结果”，不得冒充本轮新测试。

五、修复项目工作流元数据

更新 ProjectDocs/project-config.yaml：

1. current_stage 不得仍为“需求阶段”，应准确表达“P2.5 已完成，P3 待开始；当前进行 P2.6 文档校准”或完成后的等价状态。
2. completed_docs 应列出已经生成并校准的 01～08 文档。
3. next_steps 删除“填写已存在文档、再次生成 SDD”等过期事项，改为 P3 开发前的真实下一步。
4. 保留 created_at，可增加 updated_at。

审查 AGENTS.md：

1. 保留 7 个 CodeArts skill 的用途、测试命令和安全约束。
2. 确认其中路径与真实目录一致。
3. ProjectDocs/bugfix-report/ 若尚不存在，由 bug-fix-reporter 创建本轮报告；AGENTS 中注明该目录按首次报告创建即可。
4. 不要把本轮提示词或 码道职责改写进 AGENTS.md。

六、跨文档一致性要求

至少全局检查这些关键词并逐项确认语境：

- 已实现、已完成、当前、规划、未实现
- SHA-256、去重
- DELETE、tables、page_number、evidence_type
- Bearer、JWT、demo_user_id
- Element Plus、Pinia
- 14 passed、15 passed、63 passed
- P2.5、P3、FAISS、LLM

要求：

1. 需求文档可以描述目标，设计文档可以描述未来方案，但必须带清晰状态。
2. systemDesign、specs_SDD、sprint、README/docs 的实现状态不得互相冲突。
3. 不删除 P3～P6 设计内容，只修正状态和当前事实。
4. 避免在多份文档复制相互冲突的测试数字；必要时注明事实来源和验证日期。
5. docs/PROGRESS.md 中既有历史记录不得篡改，只在末尾追加 P2.6 记录。
6. docs/CODEARTS_NEXT_PROMPT.md 和 docs/CODEARTS_PROMPT_ARCHIVE.md 由码道管理，本轮不得修改。

七、验证与允许修改范围

本轮允许修改：

- AGENTS.md
- ProjectDocs/**
- docs/PROGRESS.md
- docs/IMPLEMENTATION_STATUS.md

禁止修改：

- backend/**
- frontend/**
- alembic/**
- docker-compose.yml
- .arts/**
- .codeartsdoer/**
- .skills/**
- .git/**
- docs/CODEARTS_NEXT_PROMPT.md
- docs/CODEARTS_PROMPT_ARCHIVE.md

完成前执行并记录：

1. git diff --check。
2. git diff --name-only，确认只有允许范围内文件。
3. Markdown 本地文件链接与锚点检查，结果必须为 0 失效。
4. 从后端 route decorator 重新列出端点，与文档 CURRENT 清单逐项比对。
5. 从 models.py/Alembic 重新列出表和关键字段，与数据模型文档逐项比对。
6. 从 package.json、router 和测试文件重新核对前端依赖、路由和 15 个用例。

本轮没有业务代码或测试代码变更，因此不要求为了制造新数字而重建 Docker。若主动运行测试，必须记录真实命令和结果；未运行则明确写“沿用 P2.5 历史验收，本轮仅做静态文档校准”。

八、完成汇报

在 docs/PROGRESS.md 末尾追加：

P2.6 — ProjectDocs 实现态校准与可追溯性修复

至少如实记录：

- 调用的 skill 及其作用
- 修改的文档清单
- 修复前后失效链接和锚点数量
- CURRENT API 端点数量及清单
- 被降级为规划的错误实现声明
- 数据模型校准内容
- 前端依赖、路由、测试数量校准内容
- project-config 状态修复
- git diff --check 和允许范围检查结果
- 本轮是否实际运行测试
- P3 仍未实现的范围

在 docs/IMPLEMENTATION_STATUS.md 增加 P2.6 文档校准记录，但不得改变 P3～P6 未开始状态。

最终回复必须明确：

1. 没有修改业务代码。
2. 失效链接和锚点是否为 0。
3. 哪些原“已实现”声明被纠正。
4. CURRENT API 是否严格等于真实 8 个端点。
5. 14 张表骨架与 P3～P6 业务未实现是否已明确区分。
6. 是否运行测试；若未运行，不得声称本轮测试通过。

不要 git commit，不要删除数据库 volume，不写入密钥，不自动清理开发库数据。
~~~~

---

---

## 10 — P2.7 ProjectDocs 验收去伪与文档收口

> 来源：码道对 P2.6 开发结果独立复核后生成（2026-07-13）
> 状态：未提交给码道；用户调整协作流程后，由码道直接完成同等修正并独立验证。

~~~~text
继续维护 D:\shixi\PaperLens 项目。

本轮定义为 P2.7：ProjectDocs 验收去伪与文档收口。P2.6 的主要方向正确，但外部独立复核没有复现“0 个失效锚点”，并发现多处实现态矛盾。因此禁止进入 P3，先把文档基线真正收口。

外部独立复核结果：

- Markdown 本地链接总数：75
- 失效文件路径：0
- 失效标题锚点：17
- 真实后端 route decorator：8
- 两份 API 设计中的 CURRENT 标记：各 8
- ORM 业务表：14
- 前端实际路由：4
- PaperDetailView 测试：15
- git diff --check：通过
- P2.6 工作区未修改 backend、frontend、alembic 或 Docker 配置
- ProjectDocs/bugfix-report/ 为空，没有生成提示词要求的实际 bugfix 报告

P2.6 的 8 API、14 表分层、前端版本和大部分 CURRENT/PLANNED 校准可以保留。本轮只修复独立复核确认的残留问题，不无差别重写文档，不开发任何业务功能。

开始前完整阅读：

- AGENTS.md
- docs/PROGRESS.md 中 P2.6 记录
- docs/IMPLEMENTATION_STATUS.md 中 P2.6 清单
- ProjectDocs/project-config.yaml
- ProjectDocs/specs_SDD/PaperLens/tasks.md
- ProjectDocs/specs_SDD/PaperLens/spec.md
- ProjectDocs/specs_SDD/PaperLens/design/01-论文上传与解析.md
- ProjectDocs/specs_SDD/PaperLens/design/02-证据提取与检索.md
- ProjectDocs/specs_SDD/PaperLens/design/03-审阅生成.md
- ProjectDocs/specs_SDD/PaperLens/design/07-前端展示.md
- ProjectDocs/specs_SDD/PaperLens/design/08-数据模型详细设计.md
- ProjectDocs/specs_SDD/PaperLens/design/09-API接口详细设计.md
- ProjectDocs/specs_SDD/PaperLens/design/10-前端详细设计.md
- ProjectDocs/systemDesign/03-数据模型设计.md
- ProjectDocs/systemDesign/04-API接口设计.md
- ProjectDocs/systemDesign/06-需求规格说明.md
- ProjectDocs/sprint/论文上传与解析.md
- ProjectDocs/sprint/证据提取与检索.md
- ProjectDocs/sprint/前端展示.md
- backend/paperlens/main.py
- backend/paperlens/api/papers.py
- backend/paperlens/models/models.py
- backend/alembic/versions/001_initial.py
- frontend/package.json
- frontend/src/router/index.ts
- frontend/src/tests/PaperDetailView.test.ts

先给出简短计划，然后实施。按 AGENTS.md 调用相关 skill：

1. dev-process-framework：修正 systemDesign 中残留的当前事实。
2. page-mockup：只修正前端设计文档的实现态描述，不重做线框图。
3. fullstack-testing：校准可复现的静态验收方法。
4. function-detail：修正 SDD spec/design/tasks。
5. sdd-workflow：更新 sprint 与阶段追踪。
6. bug-fix-reporter：必须生成一个非空、可追踪的 P2.7 报告文件。

不得运行 dev-eco-setup，不得修改或安装 skill。

一、先实现可靠的 Markdown 文件路径与 GFM 标题锚点检查

在 ProjectDocs/tools/check_markdown_links.ps1 新增可复现的只读检查器。该工具不是业务代码，只用于验证 ProjectDocs。

检查器必须：

1. 递归读取 ProjectDocs 下所有 Markdown。
2. 忽略 http、https、mailto 等外部链接。
3. 从链接所在文件目录解析相对路径，并 URL decode。
4. 同时验证目标文件和 #anchor。
5. 按 GitHub 风格 slug 处理标题：
   - 转为小写；
   - 删除点号、圆括号、全角括号、破折号等标点；
   - 空格逐个替换为连字符；
   - 保留中文、英文字母、数字、下划线和已有连字符；
   - 重复标题按 -1、-2 后缀处理。
6. 输出总本地链接数、失效文件路径数、失效锚点数和每个失败目标。
7. 任一失效时退出码非 0；全部有效时退出码 0。

先在修改链接前运行检查器。它必须复现：

- 总本地链接 75
- 失效文件路径 0
- 失效锚点 17

如果不能复现 17，说明检查器仍然错误，不得把结果写成通过。

当前 17 个坏锚点均在 tasks.md，至少包括：

1. design/02 中带全角括号的目标：
   - #21-evidence-提取服务（已实现） 应为 #21-evidence-提取服务已实现，共 3 处。
   - #22-向量索引服务（未实现） 应为 #22-向量索引服务未实现，共 2 处。
2. design/07 的 P02～P08 目标保留了 “—”：
   - 例如 #32-p02-论文上传-uploadview-—-已实现 应为 #32-p02-论文上传-uploadview--已实现。
   - P03、P04 以及 P05～P08 同理，共 8 处。
3. design/10 的 P05～P08 目标：
   - 例如 #45-p05-审阅结果-reviewresultview-—-规划 应为 #45-p05-审阅结果-reviewresultview--规划。
   - 共 4 处。

修复后再次运行同一个检查器，必须得到：

- 总本地链接 75
- 失效文件路径 0
- 失效锚点 0
- 退出码 0

不得用“目标文件存在”代替锚点验证，不得手工宣称 0。

二、纠正上传接口当前契约和状态流转

当前 upload_paper()：

- multipart 只接收 file；
- 不接收可选 title；
- title 由清洗后文件名去扩展名生成，不从 PDF 元数据提取；
- Paper 创建时直接设为 PROCESSING；
- 201 响应状态也是 PROCESSING；
- UPLOADING 虽然是允许枚举值，但当前上传路径没有写入该状态。

统一修正以下残留：

1. systemDesign/06：
   - “论文标题选填，默认从 PDF 提取”不能写成当前输入；如保留必须标 PLANNED。
   - 输出状态改为 PROCESSING。
   - 已勾选验收项改为“上传后状态为 PROCESSING 并注册后台解析任务”。
2. specs_SDD/PaperLens/spec.md：
   - F01 验收标准不得再写 UPLOADING。
   - 当前流程不得再写 UPLOADING → PROCESSING；应写 PROCESSING → PARSED / FAILED。
   - 可以注明 UPLOADING 是允许值但当前端点未使用。
3. tasks.md 第 1.1 节验收标准改为 PROCESSING，并与该文件顶部 CURRENT 摘要一致。
4. design/01 第 2.1 节不得把当前流程写成“创建 Paper 状态 UPLOADING → PROCESSING”。
5. 全局检查“状态为 UPLOADING”“UPLOADING → PROCESSING”“标题选填”“从 PDF 提取标题”；若描述未来目标必须明确标 PLANNED，不能与当前实现混写。

三、修复剩余 API、Sprint 和前端矛盾

1. systemDesign/04 开头仍写 Swagger 为 /docs 或 /redoc，与文末 /api/docs 冲突。当前地址统一为：
   - Swagger UI：/api/docs
   - OpenAPI：/api/openapi.json
   - ReDoc 若保留，按 FastAPI main.py 的真实默认配置说明。
2. sprint/证据提取与检索.md 的“已完成”仍写 Evidence 列表支持 page_number/evidence_type 过滤。改为当前返回全部证据，过滤为 PLANNED。
3. sprint/论文上传与解析.md 在已完成任务 API 引用中仍无标记列出 DELETE paper。明确标为 PLANNED，T-1.1.2 的已完成范围只包括列表和详情 GET。
4. design/07-前端展示.md 第 14 行仍写“基于 Element Plus 构建”，但同文第 24 行又写尚未引入。当前实现描述应为 Vue3 + TypeScript + 原生模板/CSS；Element Plus 只保留为 PLANNED。
5. 全局确认 P2.5 历史 14 项记录和当前 15 项记录的阶段语义，不能把 P2.4 的历史 14 项机械改成 15。

四、修复关联表名和物理模型伪索引

真实关联表是 finding_evidences。修复仍然存在的单数写法：

- specs_SDD/PaperLens/design/03-审阅生成.md
- specs_SDD/PaperLens/tasks.md
- 其他通过全局搜索发现的 finding_evidence 单数引用

注意：匹配 finding_evidence 但排除合法 finding_evidences。

以 models.py 和 001_initial.py 为准重新校准 systemDesign/03 与 SDD design/08 的物理模型：

1. uq_paper_page、uq_paper_chunk、uq_paper_table、uq_review_dimension 是 UniqueConstraint 名称，不要伪写成 Alembic 的 op.create_index。
2. finding_evidences 使用 finding_id + evidence_id 复合主键，迁移中没有 idx_finding_evidence。
3. experiment_results.file_id 使用 unique=True，迁移中没有名为 idx_exp_result_file_id 的显式索引。
4. 只有真实 op.create_index/ORM Index 才列入“显式索引”。
5. 主键、唯一约束、CheckConstraint 和显式索引分栏或分节描述，不能混为一谈。
6. 删除或更正不存在的 CREATE UNIQUE INDEX 示例。
7. 14 张表“6 张功能已用 + 8 张仅模型骨架”的分层保持不变。

五、修正阶段状态和补齐 bugfix 报告

1. ProjectDocs/project-config.yaml 在完成后将 current_stage 更新为：
   - P2.7 文档收口已完成，P3 待开始
   - 或语义完全等价的最终状态
   不得继续写“当前进行 P2.6”。
2. 使用 bug-fix-reporter 创建非空文件：
   - ProjectDocs/bugfix-report/P2.7-ProjectDocs验收去伪与文档收口.md
3. 报告必须记录：
   - P2.6 为何误报 0 锚点；
   - 可靠检查器如何复现 17 → 0；
   - 剩余实现态矛盾；
   - 修改文件；
   - 静态验证结果；
   - 未修改业务代码、未运行测试。
4. 空目录不算 bugfix 报告。

六、进度记录必须纠正 P2.6 的误报

docs/PROGRESS.md 中既有 P2.6 内容保留作为码道原始报告，不删除、不偷偷改成另一个数字。在其后追加：

P2.7 — ProjectDocs 验收去伪与文档收口

明确记录：

- 码道独立复核发现 P2.6 的“0 失效锚点”不成立，实际为路径 0、锚点 17。
- 新检查器修改前真实复现 75/0/17。
- 修复后真实结果 75/0/0。
- 上传状态、标题、Swagger、Evidence 过滤、DELETE、Element Plus、finding_evidences 和物理约束/索引的修正。
- bugfix 报告路径。
- 修改范围和 git diff --check。
- 本轮没有业务代码变更。
- 本轮没有运行产品测试，只进行静态文档验收。

更新 docs/IMPLEMENTATION_STATUS.md：

1. P2.6-01 应标为“文件路径已修，仍遗留 17 个锚点”，不能继续写完全通过。
2. P2.6-07 应标出原锚点检查不可靠。
3. 新增 P2.7 清单，只有可靠检查器输出 0 后才能标完成。
4. P3～P6 保持未开始。

七、验证和范围

本轮允许修改：

- ProjectDocs/**
- docs/PROGRESS.md
- docs/IMPLEMENTATION_STATUS.md

禁止修改：

- AGENTS.md
- backend/**
- frontend/**
- backend/alembic/**
- docker-compose.yml
- .arts/**
- .codeartsdoer/**
- .skills/**
- .git/**
- docs/CODEARTS_NEXT_PROMPT.md
- docs/CODEARTS_PROMPT_ARCHIVE.md

注意：上述两个提示词文件可能已经包含 码道在本轮开始前生成的未提交变更。开始工作前先记录 git status --short，并分别记录这两个文件的 SHA-256；它们可以作为既有基线出现在 git diff 中，但本轮不得修改、还原或覆盖，结束时 SHA-256 必须与开始前完全相同。禁止范围中的其他代码和配置应使用 git diff --quiet 单独验证。

完成前依次执行：

1. 修改前运行新检查器并保存 75/0/17 结果。
2. 修改后运行同一检查器并保存 75/0/0 结果。
3. git diff --check，必须无错误。
4. 对比开始前后的状态：P2.7 新增修改必须只有允许范围；两个 码道提示词文件只作为既有基线且 SHA-256 不变。
5. git diff --quiet -- AGENTS.md backend frontend docker-compose.yml .arts .codeartsdoer .skills，必须确认这些禁止范围相对 HEAD 无变化。
6. 从 route decorator 重新确认 8 个后端端点。
7. 从 models.py 重新确认 14 张表。
8. 从 router 确认 4 条前端路由。
9. 从测试文件确认当前 15 个 it 用例。
10. 全局搜索下列残留并逐项解释或消除：
   - 状态为 UPLOADING
   - UPLOADING → PROCESSING
   - 支持 page_number / evidence_type 过滤
   - 基于 Vue3 + TypeScript + Element Plus 构建
   - finding_evidence 单数
   - idx_finding_evidence
   - idx_exp_result_file_id
   - Swagger /docs

本轮不修改产品代码，不要求运行 Docker、pytest、Vitest 或 build。不得把 P2.5 历史测试结果冒充本轮执行结果。

最终回复必须逐项报告：

1. 检查器路径和实现规则。
2. 修改前是否真实复现 75/0/17。
3. 修改后是否真实达到 75/0/0。
4. 所有残留事实矛盾的修复位置。
5. 物理模型中约束和索引如何区分。
6. bugfix 报告实际文件路径。
7. git diff --check 和修改范围。
8. 明确没有修改业务代码、没有运行产品测试、没有进入 P3。

不要 git commit，不要删除数据库 volume，不写入密钥，不清理开发库数据。
~~~~

---

## 11 — P3.1 基于 MockLLM 的结构化审阅后端闭环

> 来源：码道在直接完成 P2.7 收口并独立验收后生成（2026-07-13）
> 状态：已提交给码道并完成；码道独立审查、直接修复并于 2026-07-13 验收通过。

~~~~text
继续维护 D:\shixi\PaperLens 项目。

本轮定义为 P3.1：基于现有 MockLLMClient 和已提取 Evidence，完成“创建审阅任务 → 后台生成结构化审阅 → 查询任务 → 查询审阅结果”的后端最小闭环。

这是一轮受控的后端垂直切片。不得在本轮接入 FAISS、Embedding、MaaS、ModelArts、OpenAI 或任何真实云模型；不得实现审阅前端、指标提取、实验分析、报告导出。P3.1 的目标是先把 Prompt、严格解析、Evidence 绑定、事务边界和 API 契约做成确定性、可测试的基础，后续 P3.2 再接语义检索，P3.3 再接真实模型适配器。

当前可信基线：

- P2.7 文档收口已经完成，`ProjectDocs/tools/check_markdown_links.ps1` 当前检查结果为本地链接 75、坏路径 0、坏锚点 0。
- 当前后端有 8 个实际 route decorator、14 张 ORM 业务表；审阅相关 4 张表骨架已经存在：`analysis_tasks`、`review_results`、`review_findings`、`finding_evidences`。
- `LLMClient.chat(messages, **kwargs)` 和默认 `MockLLMClient` 已存在，但 Mock 返回内容尚不足以支撑完整审阅。
- `PaperStatus`、`TaskStatus`、`TaskType`、`FindingType`、`VerificationStatus`、`OverallVerdict` 已存在。
- 当前没有 FAISS、Embedding 或真实 LLM SDK 依赖，不要为了本轮新增它们。
- P2.5 历史验收曾为后端 63 passed / 0 skipped、前端 15 passed、build 成功；这些只是历史基线，不能冒充本轮测试结果。

开始前必须完整阅读：

- AGENTS.md
- docs/PROGRESS.md 中 P2.5～P2.7 记录
- docs/IMPLEMENTATION_STATUS.md
- docs/product-requirements.md
- docs/architecture.md
- docs/data-model.md
- docs/api-contract.md
- docs/security-design.md
- ProjectDocs/project-config.yaml
- ProjectDocs/systemDesign/01-需求细化与决策发现.md
- ProjectDocs/systemDesign/02-架构设计.md
- ProjectDocs/systemDesign/03-数据模型设计.md
- ProjectDocs/systemDesign/04-API接口设计.md
- ProjectDocs/systemDesign/05-实施计划.md
- ProjectDocs/systemDesign/06-需求规格说明.md
- ProjectDocs/systemDesign/08-测试设计.md
- ProjectDocs/specs_SDD/PaperLens/spec.md
- ProjectDocs/specs_SDD/PaperLens/tasks.md
- ProjectDocs/specs_SDD/PaperLens/design/03-审阅生成.md
- ProjectDocs/specs_SDD/PaperLens/design/08-数据模型详细设计.md
- ProjectDocs/specs_SDD/PaperLens/design/09-API接口详细设计.md
- backend/paperlens/main.py
- backend/paperlens/core/config.py
- backend/paperlens/core/database.py
- backend/paperlens/core/enums.py
- backend/paperlens/core/errors.py
- backend/paperlens/models/models.py
- backend/paperlens/api/papers.py
- backend/paperlens/schemas/paper.py
- backend/paperlens/services/llm_client.py
- backend/tests/conftest.py
- backend/tests/db_helpers.py
- backend/tests/test_api/test_health.py
- backend/tests/test_api/test_upload_lifecycle.py
- backend/tests/test_services/test_llm_client.py

先检查 `git status --short`，记录工作区已有修改，不得覆盖、回退或清理用户/码道的既有改动。先给出简短实施计划和预计修改文件，然后直接实施，不要停留在建议层面。

按 AGENTS.md 实际执行相关 skill 工作流：

1. `dev-process-framework`：先校准本轮相关 systemDesign 文档，明确 P3.1 CURRENT 与 P3.2/P3.3 PLANNED 的边界。
2. `fullstack-testing`：先补充 P3.1 后端单元、服务和 API 集成测试设计，再编写测试。
3. `function-detail`：更新 SDD spec/design/tasks，使实现步骤、错误语义、事务边界和验收标准可执行。
4. `sdd-workflow`：创建或更新 `ProjectDocs/sprint/审阅生成.md`，记录真实进度与测试结果。

本轮没有 UI 变更，不运行 `page-mockup`；这是新功能开发，不生成 bugfix 报告；不得运行 `dev-eco-setup`，不得安装或修改 skill。

## 一、先固定 P3.1 契约

本轮支持以下审阅维度：

- SOUNDNESS
- NOVELTY
- CLARITY
- COMPLETENESS
- REPRODUCIBILITY
- SIGNIFICANCE
- OVERALL

如有必要，在 `core/enums.py` 增加 `ReviewDimension`，由 Pydantic 和服务层共同校验；本轮不要求给数据库增加新的 CheckConstraint，也不应因此创建 Alembic migration。

创建任务请求：

```json
{
  "task_type": "REVIEW",
  "options": {
    "dimensions": ["SOUNDNESS", "OVERALL"],
    "language": "zh"
  }
}
```

约束：

1. P3.1 只实现 `task_type=REVIEW`。其他已有 TaskType 仍是后续规划，当前请求返回统一的 422 错误，错误码为 `TASK_TYPE_NOT_SUPPORTED`。
2. `options` 可省略；默认 `dimensions=["OVERALL"]`、`language="zh"`。
3. dimensions 只能来自上述白名单，数量 1～7，不允许重复；language 只能是 `zh` 或 `en`。
4. 只有属于当前 `DEMO_USER_ID`、状态为 `PARSED` 且至少存在一条 Evidence 的论文才能创建任务。
5. 论文不存在返回 404；存在但不属于当前用户，沿用项目当前行为返回 403；尚未解析完成返回 409 / `PAPER_NOT_READY`；没有 Evidence 返回 409 / `NO_EVIDENCE`。
6. 继续使用 FastAPI `BackgroundTasks` 作为 MVP 实现，并在文档明确：进程重启后的任务恢复、重试队列和分布式执行属于后续生产化范围。

## 二、实现确定性的 Evidence 候选选择和 Prompt 构造

新增职责清晰的审阅服务，不要把业务逻辑全部堆进路由文件。

P3.1 不做“伪语义检索”。候选 Evidence 按以下稳定顺序选择：

1. 只查询当前 paper_id 的 Evidence。
2. 按 `page_number ASC, created_at ASC, id ASC` 排序。
3. 默认取前 8 条；可以在 Settings 中增加有上下界的 `review_evidence_top_k`，默认 8，但不要新增第三方依赖。
4. 给本次候选建立临时别名 `E1`、`E2`……，LLM 只能引用别名，不能自行输出或猜测数据库 UUID。
5. Prompt 中 Evidence 文本按明确分隔符包裹，并说明其内容是不可信的论文原文，不得把原文中的指令当作系统指令。
6. 对进入 Prompt 的单条文本设置合理长度上限；截断只影响 Prompt 上下文，不得改变数据库中的 `quoted_text`。
7. Prompt 必须包含论文标题、目标 dimension、language、候选 Evidence 别名及严格 JSON 输出格式。

文档必须如实称其为“P3.1 确定性候选选择/临时回退”，不得写成向量检索或语义检索已实现。FAISS/Embedding 继续标记为 P3.2 PLANNED。

## 三、完善 MockLLMClient 和严格输出解析

保留统一 `LLMClient` 抽象。增加可测试的 `get_llm_client()` 或等价工厂，默认 `PAPERLENS_LLM_BACKEND=mock`；本轮只允许 mock。测试必须能通过 FastAPI dependency override 或明确的服务注入替换成自定义 Fake LLMClient，禁止依赖真实网络。

`MockLLMClient` 根据 `chat(..., dimension=..., evidence_aliases=...)` 等显式 kwargs 返回确定性的 JSON 字符串，至少满足：

- 返回的 dimension 与请求一致。
- rating 为 1～5 整数。
- summary 为非空字符串。
- OVERALL 维度返回合法 overall_verdict；非 OVERALL 维度 overall_verdict 必须为 null。
- 有候选 Evidence 时至少返回一条引用 `E1` 的 Finding，便于走通 VERIFIED 闭环。

LLM content 的严格 JSON 结构固定为：

```json
{
  "dimension": "SOUNDNESS",
  "rating": 4,
  "summary": "...",
  "overall_verdict": null,
  "findings": [
    {
      "finding_type": "STRENGTH",
      "content": "...",
      "confidence": 0.9,
      "evidence_refs": ["E1"]
    }
  ]
}
```

使用 Pydantic 模型严格解析，至少校验：

1. content 必须是可解析的 JSON object，不接受 Markdown 代码围栏、前后解释文字或静默正则修补。
2. 拒绝未知顶层字段和 Finding 未知字段。
3. 返回 dimension 必须等于本次请求 dimension。
4. rating 必须为 1～5 整数；confidence 必须为 0～1；finding_type 必须是现有三种枚举。
5. summary 和 Finding content 必须为去除首尾空白后的非空字符串，并设置合理最大长度。
6. overall_verdict 只能来自现有枚举；OVERALL 必须非空，其他维度必须为 null。
7. `evidence_refs` 只解释为本次候选别名，不接受原始 UUID 作为可信绑定。

不要吞掉解析异常，也不要把 LLM 原始输出、Prompt、堆栈、数据库地址或内部路径返回给客户端。

## 四、实现 Evidence 绑定和原子持久化

每个任务可按请求 dimensions 生成多个 ReviewResult。顺序按请求 dimensions 保持稳定；Finding.sequence 从 1 开始。

绑定规则必须固定：

1. Finding 的 `evidence_refs` 非空，且每个别名都在本次候选映射中时，标记 `VERIFIED`，并通过 `finding_evidences` 关联真实 Evidence。
2. `evidence_refs` 为空、含未知别名、含原始 UUID、或混合了合法与非法引用时，整条 Finding 标记 `UNVERIFIED`，不得建立任何部分关联。
3. 候选映射只来自同一 paper_id，因此不得把其他论文 Evidence 绑定进来。
4. UNVERIFIED Finding 可以保存在数据库用于审计，但所有公开审阅查询必须过滤掉它。

任务状态和事务要求：

1. POST 创建 `AnalysisTask` 时写入 `PENDING`、progress=0、当前 user_id，并先提交，使后台任务使用独立 Session。
2. 后台任务开始时更新为 `RUNNING`，填写 timezone-aware `started_at`。
3. 所有 dimensions 的 ReviewResult、ReviewFinding 和 finding_evidences 必须作为一个原子结果批次写入。
4. 任一 LLM 调用、严格解析或数据库写入失败时，回滚本任务全部新审阅结果，不得残留部分 dimension；随后把任务更新为 `FAILED`，填写安全的统一 error_message 和 `completed_at`。
5. 成功时状态为 `SUCCEEDED`、progress=100、error_message=null，并填写 `completed_at`。
6. 内部异常写日志；公开失败信息统一使用安全文案，例如“审阅生成失败，请稍后重试”，不得泄露原始 LLM 输出或内部异常。

现有 4 张审阅表已经能承载本轮数据。除非实际模型与迁移不一致，否则不要修改 ORM 结构、不要创建新表、不要生成空迁移。

## 五、实现 4 个后端 API

新增独立路由模块并在 `main.py` 注册。完成后实际端点应由当前 8 个增加到 12 个。

1. `POST /api/v1/papers/{paper_id}/tasks`
   - 响应 201。
   - 返回 id、paper_id、task_type、status=`PENDING`、progress=0、created_at。
   - 后台任务在响应序列化后执行，不得把耗时审阅直接阻塞在请求事务中。

2. `GET /api/v1/papers/{paper_id}/tasks`
   - 先校验论文归属。
   - 仅返回当前用户、当前论文的任务，按 created_at DESC、id DESC 稳定排序。
   - 返回任务状态、进度、error_message、started_at、completed_at、created_at。

3. `GET /api/v1/tasks/{task_id}`
   - 只能查询当前 user_id 的任务。
   - 不存在返回 404；其他用户任务不得泄露详情，采用与项目既有归属语义一致的安全处理并写入文档。
   - 用于 HTTP 轮询，字段与实际 ORM 一致。

4. `GET /api/v1/papers/{paper_id}/reviews`
   - 先校验论文归属，并通过 AnalysisTask.user_id 再次约束结果归属。
   - 返回该论文已持久化的 ReviewResult，排序必须确定；响应包含 review id、task_id、dimension、rating、summary、overall_verdict、created_at 和 findings。
   - findings 只返回 `VERIFIED`，按 sequence ASC、id ASC 排序；至少返回 id、finding_type、content、confidence、verification_status、sequence、evidence_ids。
   - `evidence_ids` 顺序必须稳定，只能是同论文真实 Evidence UUID。

`POST /api/v1/tasks/{task_id}/cancel` 本轮不实现，文档继续明确标记 PLANNED。不要顺手实现 DELETE paper、Evidence 过滤或其他无关 API。

所有请求、响应使用独立 Pydantic schema；UUID 路径参数继续使用项目当前校验方式；错误响应继续使用现有统一结构：

```json
{
  "error": {
    "code": "...",
    "message": "...",
    "details": null
  }
}
```

## 六、测试必须覆盖真实风险

先更新测试设计，再编写测试。测试不得只断言状态码或字段存在，至少覆盖：

### 单元/服务测试

1. MockLLMClient 对普通维度和 OVERALL 返回严格合法结构。
2. Evidence 候选只来自目标论文，Top-K 和三字段排序确定。
3. Prompt 中 alias 映射稳定，包含安全边界，不包含未选 Evidence。
4. 合法 JSON 解析成功。
5. 非 JSON、代码围栏、额外字段、错误 dimension、rating 越界、confidence 越界、非法 finding_type、错误 overall_verdict 规则分别失败。
6. 全部合法 alias 绑定为 VERIFIED；空引用、未知 alias、原始 UUID、合法与非法混合引用均为 UNVERIFIED 且无部分关联。

### Docker/PostgreSQL API 集成测试

1. 构造当前用户的 PARSED Paper 和真实 Evidence，POST 创建 REVIEW 任务返回 201/PENDING；后台执行后 GET task 为 SUCCEEDED/100。
2. GET paper tasks 能看到该任务，GET reviews 返回 ReviewResult、VERIFIED Finding 和正确 evidence_ids。
3. 多 dimension 请求生成对应数量和稳定顺序的 ReviewResult；OVERALL verdict 规则正确。
4. PROCESSING/FAILED Paper 不能创建审阅任务，返回 `PAPER_NOT_READY`。
5. PARSED 但没有 Evidence 的 Paper 返回 `NO_EVIDENCE`。
6. 非法 task_type、空/重复/非法 dimensions、非法 language 被拒绝。
7. 其他用户论文、任务、审阅结果不能被当前用户读取或触发。
8. 注入返回未知 alias 的 Fake LLM：任务可以成功，数据库中 Finding 为 UNVERIFIED、没有关联行，公开 reviews 不返回该 Finding。
9. 注入畸形 JSON 或第二个 dimension 失败的 Fake LLM：任务为 FAILED，error_message 不含注入的秘密字符串或内部路径，且数据库不存在本任务的任何部分 ReviewResult/Finding/关联行。
10. UUID 非法路径继续返回统一 422；不存在资源返回约定的 404。
11. 测试只使用 `paperlens_test`，结束后 14 张业务表无残留，开发库 papers 数量测试前后不变；Docker 全量必须 0 skipped。

不要通过删除断言、放宽严格校验、条件 skip、吞异常、mock 掉持久化，或只测试服务不测试真实 API 来获得绿色结果。

## 七、同步文档，但只宣称真实完成内容

至少更新：

- docs/api-contract.md
- docs/IMPLEMENTATION_STATUS.md
- docs/PROGRESS.md
- README.md（如运行说明或端点列表受影响）
- ProjectDocs/project-config.yaml
- ProjectDocs/systemDesign 中与需求、架构、API、实施计划、需求规格和测试设计相关的文件
- ProjectDocs/specs_SDD/PaperLens/spec.md
- ProjectDocs/specs_SDD/PaperLens/tasks.md
- ProjectDocs/specs_SDD/PaperLens/design/03-审阅生成.md
- ProjectDocs/specs_SDD/PaperLens/design/09-API接口详细设计.md
- ProjectDocs/sprint/审阅生成.md

文档要求：

1. 把实际完成的 4 个端点标为 CURRENT；取消任务继续 PLANNED；当前总实际端点写为 12。
2. 明确 P3.1 使用确定性 Evidence 候选选择，不得声称 FAISS、Embedding、语义检索或真实 MaaS 已实现。
3. P3-02 Prompt、P3-04 解析与绑定、P3-05 本轮 API 按真实完成情况更新；P3-01 必须区分“P3.1 确定性候选选择已完成”和“P3.2 语义检索未开始”；P3-03 MaaSLLMClient 保持未开始。
4. `ProjectDocs/project-config.yaml` 完成后更新为“P3.1 已完成，P3.2 待开始”或语义等价状态。
5. 记录真实测试命令、pass/skip 数量、Alembic 状态、开发库隔离结果；失败或未运行的命令必须如实写，不得复用 P2.5 历史数字。
6. 不生成 bugfix 报告，不修改 AGENTS.md，不修改任何 skill 配置。
7. 运行 `ProjectDocs/tools/check_markdown_links.ps1`，允许本轮新增链接导致总数变化，但坏路径和坏锚点必须都为 0。

## 八、修改范围和保护规则

允许修改：

- backend/paperlens/core/config.py
- backend/paperlens/core/enums.py
- backend/paperlens/main.py
- backend/paperlens/api/**
- backend/paperlens/schemas/**
- backend/paperlens/services/llm_client.py
- backend/paperlens/services/ 中本轮新增审阅服务
- backend/tests/**
- README.md
- docs/api-contract.md
- docs/IMPLEMENTATION_STATUS.md
- docs/PROGRESS.md
- ProjectDocs/**（仅设计、SDD、Sprint、项目状态和现有只读检查器相关文档；不得改 skill）

原则上禁止修改，除非先用实际证据证明契约无法由现有结构承载：

- backend/paperlens/models/models.py
- backend/alembic/**
- backend/requirements.txt
- backend/pyproject.toml
- docker-compose.yml

绝对禁止修改：

- frontend/**
- AGENTS.md
- .arts/**
- .codeartsdoer/**
- .skills/**
- .git/**
- docs/CODEARTS_NEXT_PROMPT.md
- docs/CODEARTS_PROMPT_ARCHIVE.md

开始工作前分别记录两个 码道提示词文件的 SHA-256；它们可以作为既有未提交修改出现在 git diff 中，但本轮不得修改、还原或覆盖，结束时 SHA-256 必须完全相同。不得清理其他既有工作区修改。

不要 git commit，不要执行 `docker compose down -v`，不要删除数据库 volume，不要清空或改写开发库，不要写入任何真实密钥。

## 九、完成前的真实验收

在 Docker 已运行的前提下，至少执行并报告：

1. `docker compose ps`
2. `docker compose config`
3. `docker compose exec -T backend python -m pytest -q -rs`
4. `docker compose exec -T backend alembic current`
5. `docker compose exec -T backend alembic check`
6. `docker compose exec -T frontend npm test -- --run`
7. `docker compose exec -T frontend npm run build`
8. `powershell -ExecutionPolicy Bypass -File ProjectDocs/tools/check_markdown_links.ps1`
9. 从 route decorator 统计实际端点，必须为 12，并逐项列出新增 4 个端点。
10. 从 SQLAlchemy metadata/模型重新确认仍为 14 张表；如果没有 schema 变化，明确说明未新增 migration 的理由。
11. 核验 `paperlens_test` 测试后 14 张业务表无残留，开发库 papers 数量测试前后不变。
12. `git diff --check`
13. 对比开始前后两个提示词文件 SHA-256，必须不变。
14. 审查最终 diff：不得包含 frontend、AGENTS.md、Docker 配置、依赖文件、Alembic、skill 目录或其他越界修改；如果确有必要修改“原则上禁止”文件，必须在最终报告给出不可替代的证据。

如果 Docker 命令失败，不得伪造结果或改用历史数字；报告完整命令、退出码和真实错误，并继续完成不依赖该阻塞的静态检查。

最终回复必须逐项报告：

1. 实际使用了哪些 skill，以及各自更新了什么设计/测试/Sprint 内容。
2. 新增和修改的代码文件。
3. 4 个新增 API 的真实契约与当前总端点数。
4. Evidence 候选顺序、alias、Prompt 和严格解析规则。
5. VERIFIED/UNVERIFIED 绑定规则及公开过滤规则。
6. 成功与失败事务如何保证没有部分审阅结果。
7. 用户隔离、错误安全和无真实密钥/网络依赖的证据。
8. 每条验收命令的实际退出码、passed/skipped/build/Alembic/Markdown 链接结果。
9. 测试库清理和开发库未污染结果。
10. 两个提示词文件 SHA-256 是否保持不变，以及最终修改范围。
11. 明确本轮没有实现 FAISS、真实 LLM、取消任务、审阅前端、指标、实验分析或报告导出。
12. 尚未完成的问题和建议的 P3.2 下一步，但不要自行进入 P3.2。
~~~~

---

## 12 — P3.2 华为云优先的 Embedding 抽象与语义 Evidence 检索

> 来源：码道在 P3.1 独立审查、直接修复并验收通过后生成（2026-07-13）
> 状态：待用户提交给码道实施；完成后由码道审查并在授权范围内直接修正。

~~~~text
继续维护 D:\shixi\PaperLens 项目。

本轮定义为 P3.2：华为云优先的 Embedding 抽象与语义 Evidence 检索。P3.1 已完成 MockLLM 结构化审阅后端闭环并经 码道独立验收；当前真实基线为 Docker 后端 115 passed、0 skipped，P3.1 定向测试 53 passed，前端 15 passed 且构建成功，12 条 /api/v1 业务端点、14 张业务表，Alembic 位于 003 head 且 check 无差异，Markdown 链接 75/0/0。

本轮目标是把 P3.1 的“固定排序取前 8 条 Evidence”升级为按审阅维度进行语义相关性检索，同时建立可替换的 EmbeddingClient。生产适配方向优先华为云 MaaS；默认本地和测试仍使用确定性的 MockEmbeddingClient，不调用真实网络、不要求用户提供密钥、不产生云费用。

先完整阅读并以当前真实代码为准：

- AGENTS.md
- README.md
- docs/PROGRESS.md
- docs/IMPLEMENTATION_STATUS.md
- docs/architecture.md
- docs/api-contract.md
- docs/data-model.md
- backend/requirements.txt
- backend/paperlens/core/config.py
- backend/paperlens/core/errors.py
- backend/paperlens/core/enums.py
- backend/paperlens/models/models.py
- backend/paperlens/services/llm_client.py
- backend/paperlens/services/review_service.py
- backend/paperlens/api/tasks.py
- backend/tests/conftest.py
- backend/tests/test_services/test_review_service.py
- backend/tests/test_api/test_review_tasks.py
- ProjectDocs/project-config.yaml
- ProjectDocs/systemDesign/01-需求细化与决策发现.md
- ProjectDocs/systemDesign/02-架构设计.md
- ProjectDocs/systemDesign/03-数据模型设计.md
- ProjectDocs/systemDesign/04-API接口设计.md
- ProjectDocs/systemDesign/05-实施计划.md
- ProjectDocs/systemDesign/06-需求规格说明.md
- ProjectDocs/systemDesign/08-测试设计.md
- ProjectDocs/specs_SDD/PaperLens/spec.md
- ProjectDocs/specs_SDD/PaperLens/tasks.md
- ProjectDocs/specs_SDD/PaperLens/design/02-证据提取与检索.md
- ProjectDocs/specs_SDD/PaperLens/design/03-审阅生成.md
- ProjectDocs/sprint/证据提取与检索.md
- ProjectDocs/sprint/审阅生成.md

必须遵守 AGENTS.md 的研发流程，按顺序实际使用并记录对应 skill：

1. dev-process-framework：先更新 01～06 中与 Embedding、语义检索和华为云选型有关的需求、架构、实施计划与边界。
2. fullstack-testing：先补充 08-测试设计.md 的 P3.2 测试矩阵，再写测试。
3. function-detail：更新 SDD spec/design/tasks，使接口、算法、错误语义和验收标准可执行。
4. sdd-workflow：更新“证据提取与检索”和“审阅生成”Sprint 的真实进度。
5. 若实施中修复缺陷，使用 bug-fix-reporter 在 ProjectDocs/bugfix-report/ 生成对应报告。

一、严格任务边界

本轮只允许修改：

- backend/paperlens/core/config.py
- backend/paperlens/services/ 下与 Embedding、Evidence 检索、审阅集成直接相关的文件
- backend/tests/ 下与 P3.2 直接相关的测试
- README.md
- docs/PROGRESS.md
- docs/IMPLEMENTATION_STATUS.md
- docs/architecture.md
- 必要的 ProjectDocs/systemDesign、specs_SDD、sprint 和 bugfix-report 文档

原则上不要修改 API 路由、请求/响应 schema、ORM 模型、Alembic、Docker、前端和依赖文件。当前 requirements.txt 已包含 httpx，标准库足以实现精确余弦相似度；本轮禁止新增 numpy、FAISS、pgvector 或其他第三方依赖。

以下范围禁止修改、删除、还原或覆盖：

- AGENTS.md
- .arts/
- .codeartsdoer/
- .skills/
- docs/CODEARTS_NEXT_PROMPT.md
- docs/CODEARTS_PROMPT_ARCHIVE.md
- docker-compose.yml
- backend/alembic/
- backend/requirements.txt
- frontend/

开始工作前先记录 `git status --short`，并分别记录两个 码道提示词文件的 SHA-256。它们可以作为既有未提交基线出现在 git diff 中，但本轮结束时 SHA-256 必须完全不变。不要清理或覆盖其他既有未提交修改。

二、实现 EmbeddingClient 抽象

新增独立的 Embedding 服务模块，例如 `backend/paperlens/services/embedding_client.py`。命名可按现有风格微调，但职责必须清晰。

1. 定义同步、可替换的 EmbeddingClient 接口或 Protocol：

   `embed(texts: list[str]) -> list[list[float]]`

2. 输入和输出契约：

   - 输入必须是非空文本列表；不得静默删除、重排或合并元素。
   - 输出向量数量必须与输入数量完全一致，顺序一致。
   - 每个向量必须非空、维度一致，只包含有限数值，不接受 NaN、Infinity、布尔值或字符串数值。
   - 零范数向量必须作为明确错误处理，不能参与余弦计算后得到伪结果。
   - 面向外部的错误不得泄漏 API Key、Authorization header、完整响应体、服务器路径或堆栈。

3. 实现 `MockEmbeddingClient`：

   - 完全离线、确定性、无全局可变替换器。
   - 不得使用 Python 进程随机化的内置 `hash()`；使用 hashlib 或等价稳定算法。
   - 同一文本跨实例、跨调用产生相同向量；不同文本通常可区分。
   - 向量维度固定且经过归一化，适合精确余弦检索。
   - 必须让测试可以构造可预测的语义排序；如果纯哈希不足以表达词项相关性，应使用确定性的词项 hashing/bag-of-words 方案，而不是返回与文本语义无关的随机向量。

4. 工厂函数只根据配置创建默认客户端，不提供进程级 `set/reset` 可变单例。测试使用显式依赖注入、构造参数或受控 transport。

三、实现华为云 MaaS Embedding 适配器

实现 `HuaweiMaaSEmbeddingClient`，遵循华为云当前“创建文本向量化”接口契约：

- 官方参考：https://support.huaweicloud.com/usermanual-maas/usermanual_maas_0029.html
- 请求：`POST {base_url}/embeddings`
- 默认 base_url：`https://api.modelarts-maas.com/v1`
- Authorization：`Bearer <API Key>`
- JSON 请求至少包含 `model`、`input`、`encoding_format: "float"`
- 默认模型参数可设为 `bge-m3`，但必须可配置；自定义接入点模型名同样通过配置传入，禁止散落硬编码。

在 Settings 中增加有类型和上下界的配置，环境变量沿用 `PAPERLENS_` 前缀，至少包括：

- embedding_provider，默认 `mock`，只允许 `mock` 或 `huawei_maas`
- embedding_base_url，默认官方 v1 base URL
- embedding_model，默认 `bge-m3`
- embedding_api_key，可选、使用 SecretStr 或等价安全类型；provider 为 huawei_maas 时缺失必须明确失败
- embedding_timeout_seconds，正数且有合理上限
- embedding_batch_size，正整数且有合理上限

具体要求：

1. 使用现有 httpx，不新增 SDK 或依赖。
2. TLS 校验保持开启，禁止照抄 `verify=False`。
3. API Key 只从配置/环境读取，禁止写入仓库、日志、异常、测试快照和文档示例值。
4. 对输入按 batch_size 分批，但最终结果必须恢复全局原始顺序。
5. 按响应 `data[].index` 恢复每个 batch 内顺序，拒绝缺失、重复、越界或不连续 index。
6. 统一验证所有 batch 的向量维度；任一 batch 异常则整次 embed 失败，不返回部分结果。
7. 对超时、连接错误、非 2xx、非 JSON、错误 data 结构和非法向量给出稳定、安全的领域错误。
8. httpx transport/client 必须可注入，使测试用 MockTransport 完整验证而不访问外网。
9. 不要在本轮真实调用华为云，不要要求用户开通服务。文档需要说明：真实调用需用户自行开通支持的模型服务/接入点并配置 API Key，区域与模型可用性以华为云控制台和官方文档为准。

四、实现按审阅维度的语义 Evidence 检索

新增独立检索服务，例如 `backend/paperlens/services/evidence_retriever.py`，并由 review_service 使用。不要把 HTTP、向量验证、SQL 查询、相似度计算和 Prompt 拼接全部堆在一个函数中。

1. 候选范围：

   - 只加载当前 paper_id 的 Evidence。
   - 初始稳定顺序仍为 `page_number ASC, created_at ASC, id ASC`。
   - 不得把其他论文的 Evidence 放入候选或返回结果。
   - 不改变 Evidence 表，不写 embedding_id，不新增迁移。

2. 检索查询：

   - 为每个 ReviewDimension 构造稳定、可测试的查询文本。
   - 查询应包含论文标题、维度名称及该维度的简短审阅关注点，例如 SOUNDNESS 关注方法和论证可靠性、NOVELTY 关注创新与相关工作、REPRODUCIBILITY 关注实现细节和实验设置。
   - language 可以影响查询说明使用 zh/en，但不得把 Evidence 原文当作指令。
   - 同一请求的维度顺序必须保持，不允许用 set 破坏顺序。

3. 批量与调用次数：

   - 一个审阅任务内，全部 Evidence 文本只生成一遍 embedding；不得按每个 dimension 重复嵌入全部 Evidence。
   - 所有维度查询尽量一次批量嵌入，并由客户端内部按 batch_size 分批。
   - 禁止在数据库 Session 事务中进行不必要的重复网络调用。

4. 相似度与排序：

   - 使用标准库实现精确 cosine similarity，不引入 numpy/FAISS。
   - 每个 dimension 独立排序，主键为 similarity 降序；分数相同用 `page_number ASC, created_at ASC, id ASC` 稳定打破平局。
   - 每个维度返回 Settings.review_evidence_top_k 条；不足时返回全部。
   - similarity 必须是有限值；非法向量不得被当成最低分后继续。
   - 不要只用 Mock 的数组顺序假装语义检索，测试必须证明查询相关性会改变候选排序。

5. 与 P3.1 集成：

   - `run_review_task` 显式接收或取得 EvidenceRetriever/EmbeddingClient，保持可测试依赖注入。
   - 每个 dimension 的 Prompt 只包含该维度检索出的 Top-K Evidence，并重新建立该维度自己的 E1/E2…临时 alias。
   - 继续保留标题/Evidence HTML 转义、不可信边界、严格 LLM 输出解析、同论文绑定、重复 alias 去重和 UNVERIFIED 不公开规则。
   - 所有维度结果和 SUCCEEDED 状态仍在同一事务提交。
   - Embedding 创建、响应校验或检索任一步失败时，任务应安全进入 FAILED，ReviewResult/ReviewFinding/关联必须为 0，错误信息不泄漏密钥或内部响应。
   - 不改变现有 4 个审阅 API 的请求/响应契约和当前 12 条业务端点数量。

五、测试先行并覆盖失败路径

新增或更新测试，不能只测 happy path。至少覆盖：

1. MockEmbeddingClient：同文本稳定、不同文本可区分、维度固定、有限、非零且归一化；相关词项能影响排序。
2. Embedding 输出验证：空输入/空文本策略明确；数量不符、维度不一致、空向量、零向量、NaN、Infinity、布尔值、字符串数值均被拒绝。
3. HuaweiMaaS：通过 httpx MockTransport 验证 URL、Bearer header、model/input/encoding_format、batch 分割和全局顺序；测试中不得真实联网。
4. HuaweiMaaS 响应：按乱序 index 正确恢复；重复/缺失/越界 index、非 JSON、非 2xx、超时、连接失败、非法向量均安全失败。
5. 密钥安全：异常字符串、任务 error_message 和日志捕获中不得出现测试 API Key、Authorization header 或完整服务响应体。
6. 检索隔离：只返回同一 paper 的 Evidence；另一个 paper 即使更相似也不得进入候选。
7. 检索排序：不同 dimension/query 可产生不同 Top-K；相同分数按 page/created_at/id 稳定排序；Top-K 上下界和不足 K 正确。
8. 调用次数：多 dimension 任务中 Evidence embedding 不按维度重复，查询保持请求顺序。
9. 审阅集成：每个 dimension 的 Prompt 只包含其检索结果；alias 从 E1 重新开始且稳定；LLM 引用正确绑定回真实 Evidence。
10. 原子失败：Embedding 在首批、后续 batch 或查询阶段失败时任务 FAILED，所有审阅结果/发现/关联为 0，开发库不受测试污染。
11. provider 配置：默认 mock 无网络；huawei_maas 缺少 key 明确失败；非法 provider 和越界 batch/timeout 返回配置校验错误。
12. 现有 P3.1 严格类型、UUID4、用户隔离、Prompt 边界、UNVERIFIED 过滤和第二维失败回滚测试继续通过。

测试不得使用全局 set/reset 客户端，不得依赖执行顺序，不得访问真实华为云。需要数据库的测试继续强制使用 paperlens_test，并在结束后验证所有业务表无测试残留；不要清理 paperlens 开发库已有数据。

六、文档必须区分当前实现和后续规划

按实际完成情况更新 README、docs/PROGRESS.md、docs/IMPLEMENTATION_STATUS.md、docs/architecture.md 以及相关 ProjectDocs：

1. P3.2 CURRENT：EmbeddingClient、MockEmbeddingClient、HuaweiMaaSEmbeddingClient 配置适配器、精确余弦检索、按维度 Top-K、P3.1 集成。
2. 默认运行态明确为 mock，不得声称已开通或真实调用华为云。
3. 华为云方向明确为优先使用 MaaS 文本向量化 API；API Key 仅来自环境变量。
4. 当前实现是任务内即时精确余弦检索，不是 FAISS/pgvector 持久化索引；PaperChunk.embedding_id 本轮不回填。
5. FAISS/pgvector/华为云向量数据库、持久化缓存、增量索引和大规模检索继续标为 PLANNED，不得冒充已实现。
6. P3.3 华为云真实生成式 LLM 适配器仍为 PLANNED，不要在本轮实现。
7. 前端审阅展示、取消任务、Celery/Redis、指标提取、实验分析和报告导出继续为 PLANNED。
8. Sprint 和 IMPLEMENTATION_STATUS 的测试数量必须按 pytest 实际 collection/result 填写，不得手算后冒充执行结果。
9. docs/PROGRESS.md 追加 P3.2 的修改、验证命令、真实结果和已知边界，不得覆盖历史记录。
10. 运行 `ProjectDocs/tools/check_markdown_links.ps1`，允许新增链接使总数变化，但坏路径和坏锚点必须都是 0。

七、验收顺序

完成实现后依次执行并记录真实退出码和输出：

1. 对新增/修改 Python 文件运行 `python -m py_compile`。
2. 在 Docker backend 内运行新增 P3.2 定向测试；报告 passed/failed/skipped。
3. `docker compose exec -T backend python -m pytest -q -rs`，必须全量通过且 0 skipped。
4. `docker compose exec -T backend alembic current`。
5. `docker compose exec -T backend alembic check`，必须确认无模型差异。
6. `npm test -- --run`，必须报告真实 passed 数量。
7. `npm run build`，必须成功。
8. `docker compose ps`，确认 backend/frontend 运行且 postgres healthy。
9. 核对 `/api/v1` 业务端点仍为 12、ORM 业务表仍为 14。
10. 运行 Markdown 链接检查器并报告本地链接/坏路径/坏锚点。
11. `git diff --check`，必须无错误。
12. 对禁止范围执行独立 diff 检查，证明没有修改前端、Docker、Alembic、依赖、skills 和 AGENTS。
13. 比较两个 码道提示词文件开始前后的 SHA-256，必须完全不变。
14. 检查测试库所有业务表无测试残留，并确认开发库 papers 数量与本轮测试前一致。

如果 Docker、Node 或网络不可用，必须报告真实原因和完整命令，禁止把未执行写成通过。华为云真实网络测试本轮本来就禁止执行，不能将“未调用真实云”记为缺陷或 skip。

八、最终回复必须逐项报告

1. 实际调用的 skill 及对应更新文档。
2. 新增/修改文件清单。
3. EmbeddingClient、Mock 和 HuaweiMaaS 适配器的真实契约。
4. 当前配置默认值、启用 huawei_maas 所需环境变量，但不得显示真实密钥。
5. 语义检索查询、批量、相似度、稳定排序、Top-K 和同论文隔离实现。
6. 与 P3.1 集成后每维 Prompt、alias、Evidence 绑定和事务失败行为。
7. HuaweiMaaS MockTransport 测试、错误安全和无真实网络/费用的证据。
8. 新增测试数量及定向、全量后端、前端测试和构建的实际结果。
9. Alembic、Docker、端点、表、Markdown、diff check 结果。
10. 测试库清理、开发库未污染和提示词 SHA-256 不变的证据。
11. 明确本轮没有新增依赖/迁移，没有实现 FAISS/pgvector、真实生成式 LLM、前端审阅、取消任务或 P4～P6 功能。
12. 尚未完成的问题和建议的 P3.3 下一步，但不要自行进入 P3.3。

不要 git commit，不要删除数据库 volume，不写入任何真实密钥，不清理开发库已有数据，不要修改或还原 码道提示词文件。
~~~~

---

## 13 — P3.3 华为云 MaaS 真实生成式模型适配器

> 来源：码道在 P3.2 独立审查、直接修复并验收通过后生成（2026-07-13）

~~~~text
继续维护 D:\shixi\PaperLens 项目。

本轮定义为 P3.3：实现华为云 MaaS 标准 API V2 的真实生成式模型适配器，并接入现有结构化审阅链路。P3.2 已完成可替换 EmbeddingClient、华为云 MaaS Embedding 适配器和按维度语义 Evidence 检索，并经 码道独立修正与验收；当前真实基线为 Docker 后端全量 205 passed、0 skipped，P3.2 定向测试 142 passed，前端 15 passed 且生产构建成功，12 条 /api/v1 路由、14 张业务表，Alembic 位于 003_normalized_and_error head 且 check 无差异，Markdown 本地链接 75/0/0。

本轮目标是在不改变现有审阅 API、数据库模型和前端的前提下，把 LLMClient 从“只有 Mock 实现”扩展为可配置的 HuaweiMaaSLLMClient。默认本地和测试仍使用 MockLLMClient；所有华为接口测试必须使用 httpx MockTransport，禁止真实联网、禁止要求用户提供密钥、禁止产生云费用。

先完整阅读并以当前真实代码为准：

- AGENTS.md
- README.md
- .env.example
- docs/PROGRESS.md
- docs/IMPLEMENTATION_STATUS.md
- docs/architecture.md
- docs/api-contract.md
- docs/security-design.md
- ProjectDocs/project-config.yaml
- ProjectDocs/systemDesign/01-需求细化与决策发现.md
- ProjectDocs/systemDesign/02-架构设计.md
- ProjectDocs/systemDesign/05-实施计划.md
- ProjectDocs/systemDesign/06-需求规格说明.md
- ProjectDocs/systemDesign/08-测试设计.md
- ProjectDocs/specs_SDD/PaperLens/spec.md
- ProjectDocs/specs_SDD/PaperLens/tasks.md
- ProjectDocs/specs_SDD/PaperLens/design/03-审阅生成.md
- ProjectDocs/sprint/审阅生成.md
- ProjectDocs/bugfix-report/P3.2-码道独立审查与验收收口.md
- backend/requirements.txt
- backend/paperlens/core/config.py
- backend/paperlens/core/errors.py
- backend/paperlens/services/llm_client.py
- backend/paperlens/services/huawei_maas_embedding.py
- backend/paperlens/services/embedding_client.py
- backend/paperlens/services/review_service.py
- backend/paperlens/api/tasks.py
- backend/tests/conftest.py
- backend/tests/test_services/test_llm_client.py
- backend/tests/test_services/test_review_service.py
- backend/tests/test_api/test_review_tasks.py

不要只根据 docs/PROGRESS.md 判断完成度；必须检查真实实现、git 状态、Docker、数据库和 pytest collection/result。当前工作区包含用户和码道的既有修改，码道不得清理、还原、覆盖或顺手提交。

一、研发流程和允许范围

必须遵守 AGENTS.md，按顺序实际使用并记录对应 skill：

1. dev-process-framework：先更新 01～06 中 P3.3 的需求、架构、华为云选型、配置和边界。
2. fullstack-testing：先补充 08-测试设计.md 的 P3.3 测试矩阵，再写测试。
3. function-detail：更新 SDD spec/design/tasks，使接口、错误语义和验收标准可执行。
4. sdd-workflow：更新“审阅生成”Sprint 的真实进度。
5. bug-fix-reporter：如果开发或测试中修复缺陷，在 ProjectDocs/bugfix-report/ 生成报告。

本轮允许修改：

- backend/paperlens/core/config.py
- backend/paperlens/services/llm_client.py
- backend/paperlens/services/ 下新增的华为 MaaS LLM 适配器
- backend/paperlens/services/review_service.py 中与 LLM 依赖和安全失败直接相关的最小改动
- backend/tests/ 下与 P3.3 直接相关的测试
- .env.example
- README.md
- docs/PROGRESS.md
- docs/IMPLEMENTATION_STATUS.md
- docs/architecture.md
- docs/api-contract.md
- docs/security-design.md
- 必要的 ProjectDocs/systemDesign、specs_SDD、sprint 和 bugfix-report 文档

原则上不要修改 API 路由、请求/响应 schema、ORM 模型、Alembic、Docker、前端和依赖文件。当前 requirements.txt 已包含 httpx，本轮禁止新增 openai SDK、requests、重试库或其他第三方依赖。

以下范围禁止修改、删除、还原或覆盖：

- docs/CODEARTS_NEXT_PROMPT.md
- docs/CODEARTS_PROMPT_ARCHIVE.md
- .arts/
- .codeartsdoer/
- .skills/
- .git/
- AGENTS.md
- frontend/
- docker-compose.yml
- backend/alembic/
- backend/requirements.txt
- backend/paperlens/models/
- backend/paperlens/schemas/

开始工作前先记录 `git status --short`，并分别记录两个 码道提示词文件的 SHA-256。它们可以作为既有修改出现在 diff 中，但本轮结束时内容和 SHA-256 必须完全不变。不要执行 git add、git commit、git reset、git checkout、git restore、git clean、rebase 或其他会改写索引、历史或既有工作区的操作。现有提交历史由用户管理，本轮不要尝试整理或重写。

二、以华为云当前官方 V2 契约为准

实现前核对华为云官方文档，不要沿用 V1 或 OpenAI 兼容接口的旧契约：

- 中国站 MaaS 标准 API V2：https://support.huaweicloud.com/model-call-maas/model-call-019.html
- 国际站 MaaS 标准 API V2：https://support.huaweicloud.com/intl/zh-cn/model-call-maas/model-call-019.html

截至当前官方文档，中国站示例端点为 `https://api.modelarts-maas.com/v2/chat/completions`，国际站中国-香港示例为 `https://api-ap-southeast-1.modelarts-maas.com/v2/chat/completions`，鉴权头为 `Authorization: Bearer $MaaS_API_Key`。区域、模型和可用性可能变化，因此端点和模型必须可配置，文档必须提示用户以控制台和官方文档为准，不得声称项目已经开通服务。

本轮只实现非流式 `stream=false` 的 MaaS 标准 API V2。不要实现 V1、OpenAI SDK 兼容层、SSE 流式、Function Call、联网搜索或多供应商路由。

三、重构 LLMClient 工厂与配置

1. 保持同步接口：

   `chat(messages: list[dict], **kwargs) -> dict`

   返回现有内部契约 `{"role": "assistant", "content": "..."}`，不得把华为响应结构泄漏到 review_service。

2. 定义稳定的 LLMError 领域异常。配置、网络、HTTP、JSON 和响应结构错误都转为安全、可测试的 LLMError；公开错误不得包含 API Key、Authorization header、完整响应体、服务器路径或 traceback。

3. 删除 `llm_client.py` 中进程级可变 `_llm_client` 单例以及 `set_llm_client/reset_llm_client`。`get_llm_client()` 每次只根据配置构造客户端，不提供测试篡改全局状态的入口。测试继续使用 FastAPI dependency_overrides、显式构造参数或注入 transport。

4. 配置至少包含并严格校验：

   - `PAPERLENS_LLM_BACKEND=mock|huawei_maas`，默认 mock。
   - `PAPERLENS_LLM_BASE_URL`，默认中国站 V2 base URL `https://api.modelarts-maas.com/v2`。
   - `PAPERLENS_LLM_MODEL`，使用当前官方支持值作为可修改示例，例如 `glm-5.2`；不得在业务代码中散落硬编码。
   - `PAPERLENS_LLM_API_KEY`，SecretStr 或等价秘密类型，默认空，仅 huawei_maas 必需。
   - `PAPERLENS_LLM_TIMEOUT_SECONDS`，正数且有合理上下界。
   - `PAPERLENS_LLM_MAX_COMPLETION_TOKENS`，正整数且有合理上下界。

5. `.env.example` 只给变量名、非秘密默认值和注释，不写任何真实或看似真实的 Key。把现有 `maas` 注释和值校准为实际支持的 `huawei_maas`。

四、实现 HuaweiMaaSLLMClient

建议新增 `backend/paperlens/services/huawei_maas_llm.py`，不要把华为 HTTP 细节堆进 review_service。

1. 构造时支持显式传入 base_url、model、api_key、timeout 和 `httpx.BaseTransport` 或等价可注入 client 参数。真实 API Key 从 SecretStr 正确解包；不得出现 P3.2 已修复过的 `Bearer **********` 问题。

2. 只允许绝对 HTTPS base URL。安全拼接 `/chat/completions`，既不能重复 `/v2` 或路径，也不能通过 `urljoin` 让恶意绝对路径覆盖已校验 host。不要关闭 TLS 验证。

3. 输入 messages 必须是非空列表；每项必须是对象，role 只接受当前审阅需要的 system/user/assistant，content 必须是非空字符串。不得静默删除、重排或原地修改调用方 messages。

4. 请求必须至少包含：

   - `model`
   - 原顺序 `messages`
   - `stream: false`
   - `max_completion_tokens`

   不要同时发送 `max_tokens`。`dimension`、`evidence_aliases` 等 PaperLens 内部 kwargs 不得泄漏进华为请求体。官方 V2 页面没有通用 `response_format` 契约，本轮不要臆造或发送该字段。

5. 使用 `Content-Type: application/json` 和 Bearer 鉴权。同步调用必须设置明确 timeout；本轮不自动重试，避免一次审阅在超时边界重复计费。后续如引入重试应单独设计预算和幂等策略。

6. 对非流式响应严格验证：

   - HTTP 必须为 2xx，body 必须是 JSON object。
   - `choices` 必须是非空数组，目标 choice 必须有合法整数 index、对象 message、`role=assistant` 和非空字符串 content。
   - 当前未请求多 choice；缺失 index 0、重复 index、错误类型或歧义响应必须失败，不得猜测。
   - `finish_reason=stop` 才视为完整结果；`length`、`tool_calls`、缺失或未知原因都作为安全失败，防止截断 JSON 被当成正常审阅。
   - reasoning_content、usage 等字段可以忽略，但不得替代 content，也不得记录完整思维链。

7. 成功时只返回现有内部 assistant/content 结构。review_service 继续使用 P3.1 的严格 JSON/Pydantic 解析、dimension 校验和 Evidence 全有或全无绑定；不能因为接入真实模型而放宽解析器、接受代码围栏、从自然语言中“抢救 JSON”或信任模型生成的 UUID。

五、接入现有审阅链路并保持原子失败

1. `PAPERLENS_LLM_BACKEND=mock` 时行为与现有测试兼容且完全离线；`huawei_maas` 时由公开工厂创建 HuaweiMaaSLLMClient。未知 backend 或缺少 Key 必须明确、安全失败。

2. 不改变 4 个 task/review API 契约、12 条 `/api/v1` 路由数量和 14 张业务表。

3. 保持 P3.2 事务边界：Evidence 查询事务结束后才允许 Embedding/LLM 外部调用；所有维度推理与解析完成后，才在一个最终事务中写入全部 ReviewResult、ReviewFinding、FindingEvidence 和 SUCCEEDED。

4. Huawei 请求在首个或后续 dimension 发生超时、连接错误、非 2xx、非法 JSON、错误结构、`finish_reason=length/tool_calls` 或 content 不符合审阅 JSON 时，任务必须安全进入 FAILED；本任务 ReviewResult、ReviewFinding、FindingEvidence 均为 0，error_message 不泄漏 Key 或上游响应。

5. 不真实调用华为云，不把“未做真实网络验收”记为 skip 或缺陷。本轮完成的是生产适配代码、离线契约测试和审阅集成测试；实际开通、费用、模型选择与区域配置由用户后续单独完成。

六、测试要求

新增或更新测试，不能只测 happy path，至少覆盖：

1. MockLLMClient 现有确定性输出继续通过，工厂默认 mock 且无全局可变单例。
2. Huawei 成功请求：URL、Bearer Header、model、messages 原顺序、stream=false、max_completion_tokens；内部 kwargs 不进入 payload，输入 messages 不被修改。
3. SecretStr Settings 真实路径：捕获 Header 并断言发送 sentinel 原值而不是 `**********`。
4. 构造和输入校验：HTTP/相对 URL、空 model、空 Key、零/负/布尔 timeout 或 token 限制、空 messages、错误 role/content 类型均被拒绝。
5. 成功响应：解析 `choices[index=0].message.role/content`，只返回内部 assistant/content。
6. 异常响应：非 2xx、非 JSON、顶层非对象、choices 缺失/空/非数组、choice/message 非对象、index 缺失/布尔/重复/无 0、错误 role、空或非字符串 content 均安全失败。
7. 完成原因：stop 成功；length、tool_calls、缺失和未知 finish_reason 失败。
8. 超时和连接失败统一为 LLMError；异常、任务 error_message 和日志捕获中不出现测试 Key、Authorization 或完整上游响应体。
9. review_service/API 集成：成功的 Huawei MockTransport 响应能经过严格解析并绑定真实 Evidence；首个和第二个 dimension 的 Huawei 失败都整批回滚，三类结果表计数为 0。
10. 在 Fake LLM 或 transport 调用点断言数据库没有活动事务，最终成功批次仍为原子提交。
11. P3.2 的 Embedding、检索、中文排序、SecretStr 和失败回滚测试继续通过；测试库清理和开发库隔离继续成立。

所有 HTTP 测试必须使用 MockTransport 或自定义 BaseTransport；不得访问 DNS、华为云或其他公网。

七、文档同步

按实际完成情况更新 README、.env.example、docs/PROGRESS.md、docs/IMPLEMENTATION_STATUS.md、docs/architecture.md、docs/api-contract.md、docs/security-design.md 和相关 ProjectDocs：

1. P3.3 CURRENT：HuaweiMaaSLLMClient、MaaS 标准 API V2、非流式、安全响应解析、可替换工厂和审阅集成。
2. 默认运行态仍为 MockEmbeddingClient + MockLLMClient，不得声称已真实开通、调用或验证华为云。
3. 写清中国站与国际站示例端点不同，base URL、model、region 可用性以用户控制台和官方文档为准。
4. API Key 只来自环境变量/后续密钥管理，不记录、不回显、不提交。
5. P3.4 审阅结果前端、P3.5 完整登录注册与 USER/ADMIN RBAC、P4～P8 继续为 PLANNED，不得提前实现。
6. FAISS/pgvector 持久化索引、Celery/Redis、流式输出、重试、工具调用、指标提取、实验分析和报告导出继续为 PLANNED。
7. 测试计数必须来自 pytest 实际 collection/result，不得手算后冒充执行结果。
8. docs/PROGRESS.md 追加 P3.3 的修改、验证命令、真实结果和已知边界，不覆盖 P3.1/P3.2 历史记录。
9. 运行 `ProjectDocs/tools/check_markdown_links.ps1`；允许链接总数变化，但坏路径和坏锚点必须都是 0。

八、最终验收必须实际执行

1. 对新增/修改 Python 文件运行 `python -m py_compile`。
2. 在 Docker backend 内运行 P3.3 定向测试，报告真实 passed/failed/skipped。
3. `docker compose exec -T backend python -m pytest -q -rs`，必须全量通过且 0 skipped。
4. `docker compose exec -T backend alembic current`。
5. `docker compose exec -T backend alembic check`，必须无模型差异。
6. `npm test -- --run`，必须报告真实 passed 数量。
7. `npm run build`，必须成功。
8. `docker compose ps`，确认 backend/frontend 运行且 postgres healthy。
9. 核对 `/api/v1` 路由仍为 12、ORM 业务表仍为 14。
10. 运行 Markdown 链接检查器并报告本地链接/坏路径/坏锚点。
11. `git diff --check`，必须无错误。
12. 对禁止范围执行独立 diff 检查，证明没有修改前端、Docker、Alembic、依赖、skills、AGENTS 和码道提示词文件。
13. 比较两个 码道提示词文件开始前后的 SHA-256，必须完全不变。
14. 检查测试库所有业务表无测试残留，并确认开发库 papers 数量与本轮测试前一致。

如果 Docker、Node 或网络不可用，必须报告真实原因和完整命令，禁止把未执行写成通过。真实华为网络测试本轮明确禁止，不能以未联网为由修改测试要求或伪造云端结果。

九、最终回复必须逐项报告

1. 实际调用的 skill 及对应更新文档。
2. 新增/修改文件清单。
3. LLMClient、Mock 和 HuaweiMaaSLLMClient 的真实契约与工厂行为。
4. 当前配置默认值、启用 huawei_maas 所需环境变量，但不得显示真实密钥。
5. 官方 V2 URL、请求字段、响应校验、finish_reason 和错误安全实现。
6. 与 P3.2 集成后的每维 Prompt、Evidence 绑定、事务边界和整批失败行为。
7. MockTransport 测试与无真实网络、无费用、无密钥泄漏的证据。
8. 新增测试数量及定向、全量后端、前端测试和构建的实际结果。
9. Alembic、Docker、端点、表、Markdown、diff check 结果。
10. 测试库清理、开发库未污染和提示词 SHA-256 不变的证据。
11. 明确本轮没有新增依赖/迁移，没有实现前端、认证/RBAC、持久化向量索引、流式/重试/工具调用或 P4～P8 功能。
12. 尚未完成的问题和建议的 P3.4 下一步，但不要自行进入 P3.4。

不要 git commit，不要修改 .git，不要删除数据库 volume，不写入任何真实密钥，不真实调用华为云，不清理开发库已有数据，不要修改或还原 码道提示词文件。
~~~~

---

## 14 — P3.4 审阅结果前端与完整任务交互

> 来源：码道在 P3.3 独立审查、直接修复并验收通过后生成（2026-07-13）

~~~~text
继续维护 D:\shixi\PaperLens 项目。

本轮定义为 P3.4：实现审阅结果前端页面和完整 REVIEW 任务交互。P3.3 已完成华为云 MaaS 标准 API V2 非流式 LLM 适配器，并经 码道独立修正与验收；当前真实基线为 Docker 后端全量 277 passed、0 skipped，P3.3 精确定向测试 73 passed，前端 15 passed 且生产构建成功，12 条 /api/v1 业务路由、14 张业务表，Alembic 位于 003_normalized_and_error head 且 check 无差异，Markdown 本地链接 75/0/0。Docker backend/frontend 正在运行，postgres healthy；独立测试库 14 张业务表均为空，开发库当前为 33 papers / 1 task / 1 review。

本轮只实现现有后端契约之上的前端：新增 `/papers/:id/review` 页面、审阅任务创建/恢复/轮询、结果展示与筛选、Evidence 深链到现有 PaperDetail 高亮。不得修改后端契约来迁就页面，不得进入 P3.5 认证/RBAC，不得实现 P4～P8。

先完整阅读并以当前真实代码为准：

- AGENTS.md
- README.md
- docs/PROGRESS.md
- docs/IMPLEMENTATION_STATUS.md
- docs/api-contract.md
- docs/architecture.md
- docs/security-design.md
- ProjectDocs/project-config.yaml
- ProjectDocs/systemDesign/04-API接口设计.md
- ProjectDocs/systemDesign/07-页面设计.md
- ProjectDocs/systemDesign/08-测试设计.md
- ProjectDocs/specs_SDD/PaperLens/design/03-审阅生成.md
- ProjectDocs/specs_SDD/PaperLens/design/07-前端展示.md
- ProjectDocs/specs_SDD/PaperLens/design/09-API接口详细设计.md
- ProjectDocs/specs_SDD/PaperLens/design/10-前端详细设计.md
- ProjectDocs/specs_SDD/PaperLens/tasks.md
- ProjectDocs/sprint/审阅生成.md
- ProjectDocs/bugfix-report/P3.3-码道独立审查与验收收口.md
- frontend/package.json
- frontend/src/api/index.ts
- frontend/src/router/index.ts
- frontend/src/views/PaperDetailView.vue
- frontend/src/tests/PaperDetailView.test.ts
- backend/paperlens/core/enums.py
- backend/paperlens/schemas/task.py
- backend/paperlens/api/tasks.py

一、严格执行工作流和边界

1. 按已安装 skill 的真实约定执行：
   - dev-process-framework：先把 01～06 中与 P3.4 直接相关的需求、架构和实现边界更新为设计态。
   - page-mockup：先校准 07-页面设计中 P05 ReviewResultView 的布局、状态和交互；沿用现有原生 Vue/CSS 视觉，不生成脱离项目的静态原型。
   - fullstack-testing：先在 08-测试设计中补齐 P3.4 测试矩阵，再实现测试。
   - frontend-detail：按现有 Vue 3 Composition API、TypeScript、Vue Router、Axios 和 Vitest 风格实现。
   - sdd-workflow：同步 specs_SDD 和 sprint 状态。
2. 如果某个 skill 实际不可用，明确记录并按同样顺序手工完成，不得假装调用成功。
3. 不新增 Element Plus、UI 框架、状态库、轮询库或测试依赖。当前 package.json 已足够。
4. 开始前记录 `git status --short`，并分别记录两个 码道提示词文件的 SHA-256。
5. 不执行 git add、git commit、git reset、git checkout、git restore、git clean、rebase 或任何改写索引、历史、既有工作区的操作。现有提交和修改全部由用户管理。

允许修改：

- frontend/src/api/index.ts
- frontend/src/router/index.ts
- frontend/src/views/PaperDetailView.vue
- frontend/src/views/ 下新增的 ReviewResultView.vue
- frontend/src/tests/ 下与 P3.4 直接相关的测试
- README.md、docs/PROGRESS.md、docs/IMPLEMENTATION_STATUS.md、docs/api-contract.md、docs/architecture.md、docs/security-design.md
- 与 P3.4 直接相关的 ProjectDocs/systemDesign、specs_SDD、sprint 和 bugfix-report 文档

以下范围禁止修改、删除、还原或覆盖：

- docs/CODEARTS_NEXT_PROMPT.md
- docs/CODEARTS_PROMPT_ARCHIVE.md
- .arts/
- .codeartsdoer/
- .skills/
- .git/
- AGENTS.md
- backend/paperlens/
- backend/tests/
- backend/alembic/
- backend/requirements.txt
- docker-compose.yml
- frontend/package.json
- frontend/package-lock.json
- frontend/Dockerfile
- frontend/nginx.conf

二、只使用当前真实后端契约

不得新增、猜测或改写 API。frontend/src/api/index.ts 新增严格 TypeScript 类型和函数，必须与以下契约一致：

1. `GET /api/v1/papers/{paper_id}`：读取论文标题、状态、页数等现有 PaperDetail。
2. `GET /api/v1/papers/{paper_id}/tasks`：返回 `{ items: TaskDetail[] }`，当前按 created_at/id 倒序。
3. `POST /api/v1/papers/{paper_id}/tasks`：请求：

   `{"task_type":"REVIEW","options":{"dimensions":[...],"language":"zh|en"}}`

4. `GET /api/v1/tasks/{task_id}`：轮询单个任务。
5. `GET /api/v1/papers/{paper_id}/reviews`：返回 `{ reviews: ReviewResult[] }`。
6. `GET /api/v1/papers/{paper_id}/evidences` 和现有页面 API：仅由 PaperDetail Evidence 深链复用。

前端类型必须覆盖：

- ReviewDimension：SOUNDNESS、NOVELTY、CLARITY、COMPLETENESS、REPRODUCIBILITY、SIGNIFICANCE、OVERALL。
- TaskStatus：PENDING、RUNNING、SUCCEEDED、FAILED、CANCELLED。
- FindingType：STRENGTH、WEAKNESS、SUGGESTION。
- OverallVerdict：ACCEPT、WEAK_ACCEPT、BORDERLINE、WEAK_REJECT、REJECT。
- TaskDetail 的 id/paper_id/task_type/status/progress/error_message/started_at/completed_at/created_at。
- ReviewResult 的 id/task_id/dimension/rating/summary/overall_verdict/created_at/findings。
- Finding 的 id/finding_type/content/confidence/verification_status/sequence/evidence_ids。

当前没有 task cancel API、单个 review API、按 task_id 过滤 reviews 的 API，也没有删除审阅历史 API。不得调用不存在的接口。公开 reviews 已只包含 VERIFIED Finding，前端仍应按真实字段渲染，不能信任或使用模型生成 UUID 以外的证据标识。

三、实现 ReviewResultView

1. 新增路由：

   `/papers/:id/review`，name 建议为 `paper-review`。

2. 页面顶部显示论文标题、文件名、页数和解析状态，并提供“返回论文详情”和“返回论文列表”。PaperDetail 在 PARSED 状态增加清晰的“查看审阅”入口。
3. 初次加载并行获取 paper、tasks、reviews。错误必须显示可重试状态，不能让页面永久停在 loading。
4. 论文不是 PARSED 时不得创建 REVIEW 任务，显示与状态一致的说明和返回入口。
5. 结果集合按 task_id 归组。优先展示 tasks 倒序中最新且已有 ReviewResult 的任务；如果 tasks 暂无匹配但 reviews 非空，可按 ReviewResult.created_at 选择最新 task_id 作为安全降级。不要把多个历史任务的维度混成一个结果集。
6. 结果展示至少包含：
   - 概览：OVERALL 评分（无则显示 `-`）、维度数、Finding 总数、overall_verdict（仅存在时显示）。
   - 维度卡片：按固定维度顺序展示 dimension、rating、summary。
   - Finding 卡片：类型、内容、confidence（null 安全）、sequence，以及全部 evidence_ids。
   - Finding 类型筛选：全部 / STRENGTH / WEAKNESS / SUGGESTION。
   - 类型、维度、verdict 提供稳定中文标签，同时保留无法识别值的安全回退。
7. 所有服务端文本只用 Vue 文本插值渲染，禁止 `v-html`；LLM content、summary、error_message 中的 HTML/script 必须作为纯文本显示。
8. 空状态区分：
   - 没有结果且没有任务：显示配置区和“发起审阅”。
   - 有 PENDING/RUNNING：显示任务状态和进度，不出现第二个创建按钮。
   - 最新任务 FAILED/CANCELLED 且没有新结果：显示安全错误和“重新发起审阅”。
   - SUCCEEDED 但刷新后仍无结果：显示明确的不一致提示和“重新加载”，不要自动无限创建任务。
9. 允许已有历史结果时发起“重新审阅”，但任何时刻最多存在一个由页面跟踪的活动任务；新任务成功前继续显示旧结果和单独的进度区域，成功后切换到新 task_id 的结果集。

四、任务创建、恢复和轮询

1. 提供维度选择和语言选择：
   - 默认选择全部 7 个维度，顺序固定且无重复。
   - 至少选择一个维度，未选择时前端阻止提交并显示提示。
   - language 只允许 zh/en，默认 zh。
2. 创建按钮需要同步防重复锁：请求进行中和活动任务期间 disabled；快速双击只能发出一次 POST。
3. 页面加载时从 tasks 中恢复最新的 PENDING/RUNNING REVIEW 任务并继续轮询，不得因刷新页面再创建任务。
4. 每 3 秒调用 `GET /tasks/{task_id}`：
   - PENDING/RUNNING：更新状态和 0～100 之间的进度。
   - SUCCEEDED：立即停止 timer，重新获取 tasks + reviews，切换到新结果集。
   - FAILED/CANCELLED：停止 timer，显示 error_message 或固定回退文案，允许用户重新发起。
5. 轮询请求失败时停止 timer，显示“重试轮询/重新加载”按钮；重试前必须先清理旧 timer，任何时刻最多一个 timer。
6. 组件卸载、paper id 路由变化或任务进入终态时必须清理 timer，并使已经发出的旧请求结果失效。使用 request generation/id 或等价机制，防止旧论文/旧任务响应覆盖当前页面。
7. 不实现 WebSocket、SSE、自动指数重试或 cancel 按钮。

五、Evidence 深链与现有 PaperDetail 高亮

1. 每个 Finding 的每个 evidence_id 都显示独立“查看证据”入口。
2. 点击后导航到现有论文详情路由，并使用 query，例如：

   `/papers/{paper_id}?evidence={evidence_id}`

3. 修改 PaperDetailView：论文和 evidences 加载完成后读取 `route.query.evidence`，只在已加载的同论文 Evidence 列表中按 id 精确匹配，然后复用现有 `goToEvidence`，切换到页面 Tab、加载对应页并高亮。
4. 监听同一组件内 query 的变化，支持从另一个 Finding 再次跳转；不得产生重复 getPage 请求、重复 timer 或旧响应覆盖。
5. query id 不存在、类型不是单个字符串或 Evidence 不属于当前加载列表时，不调用错误页码 API，显示“未找到对应证据”的可见提示，并保留正常论文详情功能。
6. 不把 evidence_id 当作 HTML、CSS selector 或文件路径，不新增直接访问数据库或任意 URL 的逻辑。

六、组件与样式约束

1. 继续使用 Vue 3 `<script setup lang="ts">`、Composition API 和 scoped CSS，模仿 PaperDetailView 的简单原生样式。
2. 不引入 Element Plus，不复制未来 P06～P08 的导航或占位页面。
3. loading、empty、error、active task、success results 五类状态必须视觉可区分。
4. 按钮提供明确文本和 disabled 状态；筛选按钮使用可观察 active 状态；进度区域使用可访问的 `role="progressbar"` 和 aria-valuenow/aria-valuemin/aria-valuemax，或等价语义。
5. 长 summary/content 自动换行；confidence 显示为百分比时必须处理 null、NaN 和边界值，不得让 UI 出现 `NaN%`。
6. 响应式布局至少保证 360px 宽度不横向溢出，桌面端维度卡片保持清晰层级。

七、测试要求

先写/更新测试设计，再实现 Vitest。新增 `frontend/src/tests/ReviewResultView.test.ts`，并更新 PaperDetailView.test.ts。至少覆盖：

1. 路由和初始加载：getPaper/listTasks/listReviews 参数正确，成功展示标题与空状态。
2. 默认 7 维 + zh 的创建 payload 完全正确。
3. 未选择维度时不发 POST；快速双击只创建一个任务。
4. 初始发现 PENDING/RUNNING 任务时恢复轮询，不重复创建。
5. RUNNING → SUCCEEDED：进度更新、只保留一个 timer、终态停止、刷新 reviews 并展示新 task_id 结果。
6. FAILED/CANCELLED：停止轮询、显示安全错误、允许重试创建。
7. 轮询网络失败：停止 timer，重试不会叠加 timer。
8. 卸载和 paper id 变化：timer 清理，旧异步响应不能覆盖新页面。
9. 多任务 reviews 只展示最新选中 task_id，不混合历史维度。
10. OVERALL 概览、维度固定顺序、verdict、空 summary/rating/confidence 的安全展示。
11. Finding 类型筛选正确，多个 evidence_ids 均渲染为独立入口。
12. LLM 输出中的 `<script>`、`<img onerror>` 等只显示文本，不生成危险 DOM。
13. 点击证据后 router 导航到正确 paper detail + evidence query。
14. PaperDetail 首次携带合法 evidence query 时加载对应页并高亮。
15. PaperDetail query 在组件内变化时跳转新 Evidence，且不重复调用 getPage。
16. 未知/数组 evidence query 显示可见提示，不调用无关页面 API。
17. 现有 PaperDetailView 15 项测试全部继续通过。

使用 fake timers 时必须在 afterEach 清理 timer、unmount wrapper、恢复 real timers 和 mocks，不能留下未处理 Promise 或测试串扰。不要只做 snapshot；断言 API 参数、timer 数量、DOM 状态和路由 query。

八、文档同步

按真实实现更新 README、docs 和相关 ProjectDocs：

1. P3.4 CURRENT：ReviewResultView、`/papers/:id/review`、任务创建/恢复/轮询、结果筛选和 Evidence 深链。
2. systemDesign/07、design/07、design/10 将 P05 从 PLANNED 改为 CURRENT；P06～P08 和 Element Plus 继续保持 PLANNED。
3. 写清页面展示最新 task_id 结果集，不把多个历史任务混合；后端仍没有取消/删除/按 task 过滤 reviews 的 API。
4. 当前认证仍是 demo_user_id，P3.5 注册登录和 RBAC 未实现；不得把 P3.4 前端当作真实多用户系统。
5. 更新真实测试数量、构建结果、路由数量和已知边界，不覆盖 P3.1～P3.3 历史记录。

九、最终验证

必须实际执行并报告：

1. `npm test -- --run`，报告测试文件数和 passed/failed。
2. `npm run build`，报告类型检查和 Vite 构建结果。
3. Docker backend 全量测试，基线应仍为 277 passed、0 skipped；如数量变化必须解释原因，本轮原则上不应修改 backend。
4. `alembic current` 与 `alembic check`，应仍为 003 head 且无差异。
5. `/api/v1` 路由仍为 12，ORM 业务表仍为 14。
6. Markdown 链接检查仍为 75/0/0，或如新增真实本地链接则报告新的准确总数且坏路径/锚点必须为 0。
7. `git diff --check`。
8. Docker backend/frontend 运行、postgres healthy。
9. 测试库 14 张业务表均为空；不清理开发库，记录开发库前后计数并确认无测试污染。
10. 两个 码道提示词文件内容和 SHA-256 与开始前完全一致。
11. 检查禁止范围相对本轮开始没有变化；不得把既有 P3.1～P3.3 修改误报为本轮产生。

十、最终回复必须逐项报告

1. 实际调用的 skill 及对应更新文档。
2. 新增/修改文件清单。
3. 路由、API TypeScript 类型和函数。
4. 页面五类状态、最新 task_id 选择规则和历史结果处理。
5. 创建防重复、任务恢复、轮询终止、失败重试、timer/旧请求清理机制。
6. Finding 筛选、空字段安全显示和 XSS 纯文本证据。
7. Evidence query 深链、同论文匹配和 PaperDetail 高亮行为。
8. 新增测试数量、前端全量和构建真实结果。
9. 后端回归、Alembic、Docker、端点、表、Markdown、diff check 结果。
10. 测试库清理、开发库未污染和提示词 SHA-256 不变证据。
11. 明确没有新增依赖/后端 API/迁移，没有实现认证/RBAC、P4～P8、WebSocket/SSE/cancel。
12. 尚未完成的问题和建议的 P3.5 下一步，但不要自行进入 P3.5。

不要 git commit，不要修改 .git，不要删除数据库 volume，不写入任何真实密钥，不真实调用华为云，不清理开发库已有数据，不要修改或还原 码道提示词文件。
~~~~

---

## 15 — P3.5 完整认证、真实用户隔离与 USER/ADMIN RBAC 基础

> 来源：码道在 P3.4 独立审查、直接修复并验收通过后生成（2026-07-13）

~~~~text
继续维护 D:\shixi\PaperLens 项目。

本轮定义为 P3.5：实现可实际使用的注册、登录、刷新、退出、密码与个人资料流程，把论文/任务/审阅从 demo_user_id 迁移到真实认证上下文，并建立 USER/ADMIN RBAC 基础。P3.4 已完成审阅结果前端与完整任务交互并经 码道独立修正与验收；当前真实基线为 Docker 后端全量 277 passed、0 skipped，前端 45 passed 且生产构建成功，12 条 /api/v1 业务路由、14 张业务表，Alembic 位于 003_normalized_and_error head 且 check 无差异，Markdown 本地链接 75/0/0。Docker backend/frontend 正在运行，postgres healthy；独立测试库 14 张业务表均为空。开发库数据属于用户，开始时重新只读计数，不得假定仍固定为某个数字，也不得清理。

本轮必须形成认证端到端基础，不能只新增 User 表或只签发一个不可撤销 JWT。完整管理员资源管理 API、管理员仪表盘/控制台仍属于 P7；P3.5 只实现角色模型、服务端鉴权依赖、无默认凭据的管理员提升命令，以及现有业务资源的真实用户隔离。不得进入 P4～P8 的指标、实验、报告或管理员业务页面。

先完整阅读并以当前真实代码为准：

- AGENTS.md
- README.md
- .gitignore
- .env.example
- docker-compose.yml
- backend/requirements.txt
- backend/paperlens/main.py
- backend/paperlens/core/config.py
- backend/paperlens/core/database.py
- backend/paperlens/core/enums.py
- backend/paperlens/core/errors.py
- backend/paperlens/models/models.py
- backend/paperlens/api/papers.py
- backend/paperlens/api/tasks.py
- backend/paperlens/schemas/
- backend/tests/conftest.py
- backend/tests/test_api/test_health.py
- backend/tests/test_api/test_review_tasks.py
- backend/alembic/versions/001_initial.py
- backend/alembic/versions/003_normalized_and_error.py
- frontend/src/api/index.ts
- frontend/src/router/index.ts
- frontend/src/App.vue
- frontend/src/stores/app.ts
- frontend/src/views/PaperListView.vue
- frontend/src/views/ReviewResultView.vue
- frontend/src/tests/PaperDetailView.test.ts
- frontend/src/tests/ReviewResultView.test.ts
- docs/api-contract.md
- docs/security-design.md
- docs/PROGRESS.md
- docs/IMPLEMENTATION_STATUS.md
- ProjectDocs/systemDesign/01-需求细化与决策发现.md
- ProjectDocs/systemDesign/03-数据模型设计.md
- ProjectDocs/systemDesign/04-API接口设计.md
- ProjectDocs/systemDesign/05-实施计划.md
- ProjectDocs/systemDesign/06-需求规格说明.md
- ProjectDocs/systemDesign/07-页面设计.md
- ProjectDocs/systemDesign/08-测试设计.md
- ProjectDocs/specs_SDD/PaperLens/spec.md
- ProjectDocs/specs_SDD/PaperLens/tasks.md
- ProjectDocs/sprint/前端展示.md
- ProjectDocs/bugfix-report/P3.4-码道独立审查与验收收口.md

一、严格执行工作流和边界

1. 按 AGENTS.md 中已安装 skill 的真实约定执行：
   - dev-process-framework：先更新 systemDesign/01～06 的认证需求、威胁边界、数据模型、API 和实施顺序。
   - page-mockup：先在 07-页面设计中补齐登录、注册、找回/重置密码和个人资料页面状态，不生成脱离项目的静态 HTML。
   - fullstack-testing：先在 08-测试设计中补齐认证、会话、RBAC、跨用户隔离和前端路由守卫矩阵。
   - function-detail：同步 specs_SDD 的 spec/tasks/design 后再写业务代码。
   - backend-detail、frontend-detail：分别遵循现有 FastAPI/SQLAlchemy 与 Vue3/TypeScript 风格。
   - sdd-workflow：同步认证和前端 Sprint。
2. 如果某个 skill 实际不可用，明确记录并按相同顺序手工产出文档，不得假装调用成功。
3. 开始前记录 `git status --short`、最新提交、Docker 状态、开发库只读计数，以及两个 码道提示词文件 SHA-256。
4. 不执行 git add、git commit、git reset、git checkout、git restore、git clean、rebase 或任何改写索引、历史和既有工作区的操作。
5. 不修改、删除或还原 `.arts/`、`.codeartsdoer/`、`.skills/`、`.git/`、AGENTS.md、两个 码道提示词文件和用户已有数据。
6. 不引入外部身份平台、社交登录、MFA、Redis、Celery、Element Plus、管理员 UI、P4～P8 功能或真实邮件/短信云调用。

允许按本轮需要修改：

- backend/paperlens 下认证、配置、枚举、模型、schema、API、依赖和管理命令相关文件
- backend/paperlens/api/papers.py、tasks.py 中取得当前用户与资源隔离的代码
- backend/tests 下认证及既有 API 测试适配
- backend/alembic/versions 下新增且仅新增一份 004 迁移
- backend/requirements.txt
- frontend/src 下 API、router、store、App、认证/个人资料视图及对应测试
- docker-compose.yml 中仅认证必需的环境变量映射
- `.env.example`、README、docs 和相关 ProjectDocs

原则上不要修改 LLM、Embedding、Evidence 检索、Review 解析和 PDF 解析核心逻辑；若真实用户依赖传递确有需要，只做最小改动并用测试证明未改变业务契约。

二、安全基线与依赖

1. 密码哈希使用当前 FastAPI 官方安全教程采用的 `pwdlib[argon2]`，调用 `PasswordHash.recommended()`；不得自行实现哈希、不得使用 SHA/MD5 存密码、不得新增 passlib。
2. JWT 使用 PyJWT，只允许代码中固定配置的单一算法，不得根据 token header 动态选择算法，不接受 `alg=none`。
3. 邮箱校验可增加 `email-validator`。除 `pwdlib[argon2]`、PyJWT、email-validator 外，不新增认证依赖；将实际可安装兼容版本精确固定到 requirements.txt，并通过 Docker 冷构建验证。
4. 密码作为当前单因素认证：长度 15～128 个 Unicode code point，允许空格和可打印 Unicode，不做大小写/数字/特殊字符组合强制，不 trim、不截断。至少拒绝项目名、邮箱本身及一组明确的常见弱口令；文档必须诚实说明尚未接入完整泄露口令语料库。
5. 参考并落实以下当前官方边界，而不是只把链接写进文档：
   - FastAPI OAuth2/JWT 教程：https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
   - NIST SP 800-63B-4 密码要求：https://pages.nist.gov/800-63-4/sp800-63b/authenticators/
   - OWASP Password Storage：https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
   - OWASP Forgot Password：https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html
   - OWASP REST Security JWT：https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html

三、配置与密钥

1. 增加认证配置，至少包含：JWT secret、固定 algorithm、issuer、audience、access token 分钟数、refresh session 天数、reset token 分钟数、cookie secure、登录失败阈值和锁定分钟数。
2. access 默认 15 分钟、refresh 默认 30 天、reset 默认 15 分钟、失败阈值默认 5 次、锁定默认 15 分钟；全部做类型、有限值和合理上下界校验。
3. JWT secret 必须是 SecretStr 且至少 32 bytes，不允许生产默认值，不得写进仓库、日志、响应、测试快照或最终回复。
4. docker-compose 通过 `${PAPERLENS_JWT_SECRET:?set PAPERLENS_JWT_SECRET in .env}` 之类的显式变量注入。若工作区没有本地 `.env`，可在确认 `.env` 已被 gitignore 后生成一次密码学随机 secret 写入被忽略的 `.env`，禁止打印其内容；`.env.example` 只保留空变量名与生成说明。
5. 测试必须在应用模块导入前设置独立的 test-only secret；禁止让测试依赖用户本地 secret，也禁止降低生产校验。

四、数据模型与 004 迁移

新增且只新增一份 Alembic 004 迁移，模型与迁移必须严格一致。至少新增：

1. `users`：
   - id（String(128)，新账号使用 UUID4 字符串，同时兼容迁移后的 legacy `demo-user`）
   - email、email_normalized（大小写无关唯一约束）
   - display_name
   - password_hash（legacy disabled 账号可为 null，正常账号必须由服务层保证非空）
   - role：USER / ADMIN，数据库 CHECK
   - status：ACTIVE / DISABLED，数据库 CHECK
   - failed_login_count、locked_until
   - created_at、updated_at、password_changed_at
2. `auth_sessions`：每一代 refresh token 一行，至少含 id/sid、family_id、user_id、token_hash 唯一、expires_at、created_at、last_used_at、revoked_at、revoke_reason、replaced_by_id；建立用户、family、token_hash 和有效期索引。
3. `password_reset_tokens`：id、user_id、token_hash 唯一、expires_at、created_at、used_at；只存摘要，不存明文 token。
4. 为 papers、analysis_tasks、experiment_files、export_reports 的 user_id 增加到 users.id 的 FK 和必要索引，删除用户使用 RESTRICT 或等价安全策略，禁止级联删除用户全部论文。
5. 迁移必须保留现有所有数据：幂等插入一个 `id='demo-user'`、DISABLED、不可登录的 legacy 占位用户，使已有 user_id 满足 FK。不得生成或硬编码可用密码，不得自动把 legacy 数据给任意新注册账号。
6. 提供显式管理命令，例如 `python -m paperlens.cli promote-admin --email <email> [--claim-legacy-data]`：
   - 目标邮箱必须是已注册账号；事务内提升 ADMIN。
   - 只有显式 `--claim-legacy-data` 才把四类资源的 `demo-user` 归属迁到该账号。
   - 不接受命令行明文密码，不创建默认管理员，不在启动时自动提升任何人。
   - 本轮只实现和测试命令，不替用户实际执行。
7. upgrade/downgrade 都要可执行；upgrade 后旧 papers/tasks/reviews 数量和值保持不变，新增表和 FK 与 ORM 一致。

五、Token、会话与密码服务

1. Access token 是短时 JWT，至少含 sub、sid、jti、typ=access、iat、nbf、exp、iss、aud。解析时固定校验算法、签名、typ 和全部必需 claim。
2. Refresh token 使用 `secrets` 生成至少 256 bit 的不透明随机值，只通过名为 `paperlens_refresh` 的 HttpOnly cookie 传输；数据库只保存 SHA-256 摘要。不得把 refresh token 放进 JSON、URL、localStorage、sessionStorage或日志。
3. Cookie 默认 `HttpOnly; SameSite=Lax; Path=/api/v1/auth`；生产 `Secure=true`，本地 debug 可由显式配置关闭。登录、注册和刷新设置 cookie；退出清除 cookie。
4. 刷新必须单次轮换：旧 session 行标记 revoked/used，新建同 family 的下一代 session并设置 replaced_by。再次使用已轮换 token 视为重放，事务内撤销整个 family。
5. Access 鉴权不仅验证 JWT，还查询 sid 对应 session 和当前 User：session 已撤销/过期、用户禁用/锁定或不存在时立即拒绝。因此退出、logout-all、密码修改/重置能立即使相关 access token 失效。
6. 登录成功重置失败计数并创建新 session family；错误密码使用 Argon2 验证。不存在、禁用和锁定账号也执行 dummy hash 验证并返回相同 401 文案，禁止邮箱枚举。
7. 连续失败达到阈值后设置 locked_until；到期可再次登录，成功后清零。使用行锁或等价事务机制避免并发绕过；文档诚实说明当前只有账号级数据库锁定，分布式 IP 限流仍待部署层实现。
8. 修改密码必须验证旧密码、写入新 Argon2id hash、更新 password_changed_at，并撤销该用户全部 session，要求重新登录。
9. 找回密码请求始终返回相同 202 文案。token 使用 `secrets` 生成、只存 SHA-256、单次使用、15 分钟过期；成功重置后撤销全部 session。
10. 建立可注入的 PasswordResetNotifier 接口；自动测试使用 capture fake 获取明文 token。默认运行实现不得把 token 写入日志或 HTTP 响应，也不得真实联网。本轮未配置邮件投递时必须在文档中明确边界，后续生产实现优先可替换的华为云通知/邮件适配器。

六、API 契约

在 `/api/v1/auth` 下实现严格 Pydantic schema，所有请求 `extra='forbid'`，所有响应禁止 password_hash、token hash、失败计数和内部 session 字段。至少实现：

1. `POST /register`：email、password、display_name；规范化邮箱，创建 ACTIVE/USER，返回 access token + 安全 UserPublic，并设置 refresh cookie，201。
2. `POST /login`：email、password；成功返回 access token + UserPublic 并设置 refresh cookie；失败统一 401。
3. `POST /refresh`：只从 refresh cookie 读取并轮换，返回新 access token并更新 cookie；缺失/无效/过期/重放统一 401。
4. `POST /logout`：要求 access token，撤销当前 family 或当前设备 session，清 cookie；幂等安全响应。
5. `POST /logout-all`：要求 access token，撤销当前用户全部 session并清 cookie。
6. `GET /me`：返回当前 UserPublic。
7. `PATCH /me`：只允许修改 display_name；邮箱修改和验证流程本轮不开放。
8. `POST /change-password`：old_password/new_password，成功撤销全部 session并清 cookie。
9. `POST /forgot-password`：email；无论账号是否存在均返回相同 202，调用 notifier 但不回传 token。
10. `POST /reset-password`：reset token/new_password；成功单次消费 token、改 hash、撤销全部 session，不自动登录。

错误继续使用现有 AppError 信封；认证失败使用正确 401 并含 `WWW-Authenticate: Bearer`，已认证但角色不足使用 403。不要在错误中区分邮箱不存在、密码错误、账号禁用、锁定或 token 失败细节。

七、真实用户依赖与 RBAC

1. 新增统一 `get_current_user`、`get_current_user_id`、`require_admin` 依赖，禁止 papers.py/tasks.py 各自复制 token 解析。
2. 删除或停止业务路由使用 `_get_user_id()`/`settings.demo_user_id`。除 health 和 auth 公开端点外，现有 papers、pages、sections、evidences、tasks、reviews 路由全部要求 Bearer access token。
3. 创建 Paper/AnalysisTask 时 user_id 只能来自认证依赖，绝不接受 body/query/header 自报 user_id。
4. 保留当前资源所有权语义：跨用户访问不得返回资源内容；所有列表、详情、Evidence、task 和 reviews 查询继续同时过滤当前用户。
5. role 必须以数据库当前值为准，不能只信任 JWT 里的 role。实现并单元测试 `require_admin`，但本轮不新增管理员用户/论文/任务管理 API，也不允许 ADMIN 默认绕过普通资源所有权。
6. CORS/HTTPS 边界按当前部署诚实记录；不得用 `Access-Control-Allow-Origin: *` 配合凭据。

八、前端最小可用认证闭环

1. 新增 `/login`、`/register`、`/forgot-password`、`/reset-password`、`/profile` 页面，继续使用 Vue3 `<script setup lang="ts">`、原生 scoped CSS 和现有视觉，不引入 UI 库。
2. Pinia auth store 只在内存保存 access token 和 UserPublic。refresh token 由 HttpOnly cookie 管理，任何前端代码和测试都不得读取或写入 refresh token，不使用 localStorage/sessionStorage 保存 token。
3. API 请求拦截器在有 access token 时加 Bearer；401 时使用一个共享 single-flight refresh Promise，成功后只重放原请求一次。auth/login/register/refresh 本身不得进入无限拦截循环。
4. 应用启动调用一次 auth bootstrap：尝试 refresh cookie；成功加载用户，失败进入匿名状态。Router guard 必须等待 bootstrap 完成，避免刷新页面时误跳登录。
5. 现有 `/upload`、`/papers`、`/papers/:id`、`/papers/:id/review` 标记 requiresAuth；匿名访问带 redirect query 跳 `/login`。登录成功回到安全的站内 redirect，拒绝 `//evil`、绝对 URL 或任意外站开放重定向。
6. 已登录用户访问 login/register 跳到 papers；导航区显示当前 display_name、个人资料和退出。退出无论后端响应如何都清理本地 access/user并回登录页。
7. 表单至少具备：email 格式、密码 15～128、确认密码一致、提交锁、防快速双击、后端安全错误和明确 loading/disabled 状态。密码不得进入 URL、DOM 长期回显或 console。
8. forgot 页面始终显示统一提示；reset 页面从 query 读取单个 token 字符串，非字符串/空 token 阻止提交。不要宣称邮件已发送，文案说明“若账号存在且通知服务可用，将发送重置指引”。
9. profile 显示 email/role/status，允许修改 display_name、修改密码和 logout-all；密码成功修改后回登录。
10. 现有 45 项 PaperDetail/ReviewResult 测试必须继续通过；mock API 时不得因全局 bootstrap 产生串扰。

九、测试要求

先写测试设计，再实现。测试不得访问公网、真实邮件、真实华为云或开发库。至少覆盖：

后端单元/服务：

1. Argon2 hash 不含明文，同密码不同盐，正确/错误验证；dummy hash 路径。
2. 密码 15/128 边界、Unicode/空格、不得 trim/截断、常见弱口令拒绝且不强制组合规则。
3. JWT 必需 claims、固定算法、过期/nbf/issuer/audience/typ/签名错误全部拒绝，错误不泄漏 token。
4. refresh/reset 明文只出现于调用边界，数据库只存 64 位十六进制摘要。
5. require_admin 对 USER=403、ADMIN=通过、禁用账号=401，并以数据库角色为准。

后端 API/PostgreSQL：

6. 注册成功、邮箱大小写重复、非法/额外字段、响应绝不含 hash；cookie 属性正确。
7. 登录成功；错误密码/不存在/禁用/锁定统一响应；5 次失败锁定、到期恢复、成功清零。
8. refresh 正常轮换；旧 token 重放撤销 family；并发刷新最多一个成功；过期/伪造统一失败。
9. logout 后原 access 立即失败；logout-all、修改密码、重置密码撤销全部 session。
10. forgot 不枚举账号，capture notifier 可取得测试 token；reset 单次使用、过期失败、数据库不存明文。
11. 未认证访问每类现有业务路由为 401；用户 A 创建/读取自己的论文和任务成功，用户 B 列表不可见且详情/Evidence/task/review 不可越权。
12. body/header/query 伪造 user_id 无效；ADMIN 默认也不能读取其他用户业务资源。
13. legacy demo-user 迁移存在且 DISABLED；现有四类资源 FK 完整；管理命令无 flag 不转移数据，有 flag 才原子 claim。
14. 所有既有后端测试适配 Authorization 后继续真实执行，不能 mass skip、删除断言或把 db_client 变成绕过鉴权的应用后门。
15. 测试结束 `paperlens_test` 新旧全部业务表为 0，开发库计数在 pytest 前后不变。

前端 Vitest：

16. register/login 表单验证、payload、提交防重复和安全错误显示。
17. token 只在内存，localStorage/sessionStorage 无 token；Authorization header 正确。
18. bootstrap refresh 成功/失败；路由守卫等待初始化、redirect 安全校验、已登录访问公开认证页跳转。
19. 并发多个 401 只发一个 refresh；每个请求只重放一次；refresh 401 不递归。
20. logout、logout-all、修改密码后的 store/cookie契约和路由状态。
21. forgot/reset token 非法 query、统一文案、密码确认和成功状态。
22. profile 加载和 display_name 更新，模型/服务端文本只作纯文本渲染。
23. 现有 ReviewResultView 26 项与 PaperDetailView 19 项继续通过。

禁止只断言状态码或 snapshot；必须断言数据库摘要/撤销状态、cookie、JWT claims、跨用户查询、请求次数、并发轮换、DOM、store 和 router 行为。fake time/timer/mock 必须在 afterEach 恢复。

十、文档同步

1. 按真实实现更新 README、API 契约、安全设计、架构、进度和 IMPLEMENTATION_STATUS。
2. ProjectDocs 的 systemDesign、specs_SDD、Sprint、页面和测试设计统一标记 P3.5 CURRENT/完成状态，保留 P3.1～P3.4 历史数字。
3. 写清 access/refresh/reset 生命周期、cookie、轮换/重放、锁定、密码规则、错误最小披露、legacy 数据和管理员提升命令。
4. 明确当前没有默认管理员、MFA、邮箱验证、生产通知适配器、分布式 IP 限流、管理员业务 API/控制台；这些不能写成已完成。
5. 明确华为云 IAM 管云资源身份，不替代 PaperLens 产品账号；PasswordResetNotifier 后续生产适配优先华为云能力，但本轮不真实联网。

十一、最终验证

必须实际执行并报告：

1. 新依赖 Docker 无缓存或能证明依赖重新安装的构建成功；不得只用宿主机偶然已有包。
2. 认证定向后端测试的真实 collection/result。
3. `docker compose exec -T backend python -m pytest -q -rs` 全量，必须 0 failed、0 skipped；数量按实际报告，不预设。
4. `npm test -- --run` 前端全量，现有 45 项加新增认证测试全部通过。
5. `npm run build` 类型检查和 Vite 生产构建成功。
6. `alembic current` 为新 004 head；`alembic check` 无差异；在独立临时/测试库验证 downgrade 到 003 再 upgrade 004，不对开发库 downgrade。
7. 实际统计新的 `/api/v1` 路由数和 ORM 业务表数，不沿用 12/14 旧数字。
8. Docker backend/frontend 运行、postgres healthy；health 公开可用，受保护端点无 token 为 401。
9. Markdown 检查坏路径/坏锚点均为 0；`git diff --check` 无错误。
10. 测试库所有新旧业务表均为 0；开发库测试前后计数不变，legacy 数据仍完整。
11. 检查响应、日志、git diff 和测试快照中没有 JWT secret、密码、refresh/reset 明文 token或 hash。
12. 两个 码道提示词文件内容和开始时 SHA-256 完全不变。
13. 检查禁止范围和最新 Git 提交没有变化；不得把用户或 码道既有修改归因于本轮。

如果 Docker、依赖下载、Node 或数据库不可用，报告真实命令和原因，禁止把未执行写成通过。不要为了保住旧测试数字而 skip、xfail、删测试、放宽安全断言或恢复 demo_user_id 后门。

十二、最终回复必须逐项报告

1. 实际调用的 skill 及先后产出的文档。
2. 新增/修改文件、三张新表、004 迁移和 legacy 数据策略。
3. 依赖与密码/JWT/refresh/reset 安全实现，不显示任何 secret/token。
4. 10 类 auth API 的请求、响应、cookie和错误语义。
5. session 轮换、重放检测、logout/logout-all、锁定和密码变更撤销行为。
6. 真实用户依赖、现有资源迁移和 USER/ADMIN RBAC 边界。
7. 前端 store、single-flight refresh、路由守卫和五个页面。
8. 新增测试数、定向/全量后端、前端全量和 build 真实结果。
9. Alembic downgrade/upgrade、Docker、路由、表、Markdown、diff check 结果。
10. 测试库清理、开发库未污染、secret 扫描和提示词 SHA-256 不变证据。
11. 明确没有自动创建/提升管理员，没有真实发送通知，没有实现管理员业务 API/控制台、MFA、P4～P8。
12. 尚未完成的问题和建议的下一阶段，但不要自行进入下一阶段。

不要 git commit，不要修改 .git，不要删除数据库 volume，不要打印或提交任何真实密钥/密码/token，不要真实调用华为云或邮件服务，不要清理开发库已有数据，不要修改或还原 码道提示词文件。
~~~~

---

## 16 — P4.1 可追溯实验指标提取与 Checkpoint 口径判断后端

> 来源：码道在 P3.5 独立安全纠正并完成代码验收后生成（2026-07-13）

~~~~text
继续维护 D:\shixi\PaperLens 项目。

本轮定义为 P4.1：在 P3.5 完整认证和真实用户隔离基础上，实现从已解析论文表格/原文 Evidence 中提取实验指标、判断 checkpoint 统计口径、保存可追溯 MetricRecord，并提供任务与查询 API。P3.5 已经 码道独立安全纠正：认证定向 42 passed，Docker 后端全量 318 passed、0 skipped，前端 66 passed 且生产构建成功；Alembic 为 005_auth_security_corrections head 且 check 无差异，22 条 `/api/v1` 路由、17 张 ORM 表。Docker backend/frontend 正在运行，postgres healthy。

特别注意：P3.4 文档曾记录开发库 35 papers / 1 task / 1 review，但 码道在 P3.5 本轮首次只读计数时已经是 0 / 0 / 0，原持久卷仍存在，现有证据无法自动恢复或精确归因。P4.1 开始和结束都必须重新只读计数，只能诚实记录当前值；禁止把“0→0”描述成 P3.5 历史数据保留成功，禁止自动恢复、伪造、清理开发库或删除 volume。

本轮只做指标提取后端、任务执行和查询契约，不实现 CSV/Excel 实验文件分析、报告导出、指标前端页面、管理员业务 API/控制台、FAISS/pgvector、真实邮件、MFA 或 P5～P8 功能。不得削弱 P3.5 认证、会话撤销和真实用户隔离。

先完整阅读并以当前真实代码为准：

- AGENTS.md
- README.md
- .gitignore
- .env.example
- docker-compose.yml
- backend/requirements.txt
- backend/paperlens/core/config.py、enums.py、deps.py、errors.py、database.py
- backend/paperlens/models/models.py
- backend/paperlens/api/papers.py、tasks.py、auth.py
- backend/paperlens/schemas/task.py
- backend/paperlens/services/review_service.py、llm_client.py、embedding_client.py
- backend/paperlens/services/auth_service.py、token_service.py
- backend/alembic/versions/004_auth_tables.py
- backend/alembic/versions/005_auth_security_corrections.py
- backend/tests/test_api/test_auth.py、test_review_tasks.py、test_health.py
- backend/tests/test_services/
- docs/api-contract.md、security-design.md、PROGRESS.md、IMPLEMENTATION_STATUS.md
- ProjectDocs/systemDesign/01～08
- ProjectDocs/specs_SDD/PaperLens/spec.md、tasks.md、design/
- ProjectDocs/sprint/用户认证与权限.md、审阅生成.md
- ProjectDocs/bugfix-report/P3.5-码道独立审查与安全验收收口.md

一、工作流与边界

1. 严格按 AGENTS.md 的 skill 顺序执行：先用 dev-process-framework 更新 systemDesign/01～06 的 P4.1 需求、数据流、API 和实施计划；本轮无新页面，page-mockup 只需确认 07 中指标页面仍为规划，不生成静态页面；用 fullstack-testing 先更新 08 测试矩阵；再用 function-detail/backend-detail 更新 SDD 后编码；最后用 sdd-workflow 更新或新增指标提取 Sprint。
2. 某个 skill 不可用时明确记录，并按同一顺序手工产出，不能假装调用成功。
3. 开始前记录 git status、最新提交、Docker 状态、开发库/测试库只读计数、Alembic 状态，以及两个 码道提示词文件 SHA-256。
4. 不执行 git add/commit/reset/checkout/restore/clean/rebase，不修改 `.git/`、`.arts/`、`.codeartsdoer/`、`.skills/`、AGENTS.md 和码道提示词文件。
5. 不删除 volume、不 downgrade 开发库、不清理或重建用户数据。测试只能写 `paperlens_test`，任何数据库保护断言失败都必须立即停止。
6. 不修改认证安全语义：access 必须继续查 sid/AuthSession/User，refresh 继续轮换与重放撤销，token 不得进入 Web Storage 或日志，业务 user_id 继续只来自认证依赖。

二、需求和确定性口径

1. 使用现有 `TaskType.METRIC_EXTRACTION` 和 `MetricRecord` 模型，形成 `PENDING → RUNNING → SUCCEEDED/FAILED` 后台任务闭环。不得把 REVIEW 任务逻辑复制成不可维护的第二套状态机；提取服务应有清晰独立边界。
2. 数据源仅限当前用户、当前论文已持久化的 `PaperTable.structured_data/raw_text` 与可追溯 Evidence/页面文本。论文必须 PARSED；没有候选来源时返回明确 409，不启动空任务。
3. 每条公开 MetricRecord 必须能回溯到 `table_id + row_index` 或 `evidence_id`，并保存最小必要 `raw_text`。不得生成无来源数值，不得让模型自行计算或猜测缺失指标。
4. 至少支持常见指标名称及别名的规范化：accuracy/acc、precision、recall、F1/F1-score、AUC/AUROC、mAP/AP、BLEU、ROUGE、IoU/mIoU、RMSE、MAE、loss。规范名、原始名和单位/百分号处理必须文档化；不要把同名但语义不同的字段盲目合并。
5. 数值解析必须使用确定性 Python：支持整数、小数、前导小数、科学计数法和百分号；拒绝 NaN/Infinity、空值、范围文本、± 误差整体被误当单值、年份/样本量等明显非指标值。百分号采用统一存储口径并在 API 文档写清，不允许同一字段有时 0.91、有时 91。
6. CheckpointType 使用现有 FINAL/MAX/MEAN/BEST/LAST/UNKNOWN。只根据同一表头、行名、caption 或紧邻原文中的明确词汇判断；保存 `checkpoint_source`，冲突或无证据时必须 UNKNOWN，禁止凭“数值最大”自动推断 BEST/MAX。
7. model_name、dataset_name 只能从明确表头/行列上下文提取；无法可靠判断则为 null。不得把章节名、指标名或任意长文本误当模型/数据集。
8. 对同一 task 内候选做稳定去重，去重键和优先级必须明确且确定性；保留来源更具体的记录。排序必须稳定，不能依赖数据库未指定顺序。
9. 默认实现完全离线、不得访问真实华为云。若复用 LLMClient，只允许它产生严格候选结构，所有数值、来源、枚举和 Evidence/table 绑定仍由确定性代码复核；Mock 必须可测试，Huawei 只能 MockTransport，禁止真实请求和费用。
10. 外部推理或耗时解析不得持有数据库事务；最终写入 MetricRecord 必须单事务 all-or-nothing。失败时 task=FAILED 且本 task 的 MetricRecord 为 0，error_message 使用安全映射，不泄漏 prompt、论文原文、密钥、URL、SQL 或堆栈。

三、API 契约

1. 扩展 `POST /api/v1/papers/{paper_id}/tasks` 支持 `task_type=METRIC_EXTRACTION`。REVIEW 原契约和测试必须保持不变；不同 task_type 的 options 使用严格可区分 schema，extra=forbid。
2. 对同一用户/论文的并发活动 METRIC_EXTRACTION 任务实施明确策略：建议若已有 PENDING/RUNNING 则返回 409，避免重复后台写入；已终态允许重跑并产生独立 task 历史。
3. 新增 `GET /api/v1/papers/{paper_id}/metrics`：要求 Bearer，先校验论文所有权；支持严格、有限的 task_id、metric_name、dataset_name、checkpoint_type 过滤和稳定排序，分页上限不超过 100。
4. 可新增 `GET /api/v1/metrics/{metric_id}` 获取单条详情；跨用户不得返回记录内容。不存在与越权语义沿用当前项目既有安全约定并用测试固定。
5. 响应 schema 至少包含 id、paper_id、task_id、model_name、dataset_name、metric_name、metric_value、checkpoint_type、checkpoint_source、evidence_id、table_id、row_index、raw_text、created_at；不得返回内部 prompt 或未校验候选。
6. ADMIN 默认仍不能绕过普通资源所有权；不得新增管理员指标管理接口。

四、数据库与迁移

1. 先比较现有 MetricRecord ORM 和 001～005 schema。若当前字段/约束足够，优先不新增迁移，并用 `alembic check` 证明一致。
2. 只有真实缺少不可由服务层表达的约束/索引时，才新增单一 006 迁移；不得编辑已应用的 001～005，不得为了“有迁移”而迁移。
3. 若新增 006，upgrade/downgrade 只能在 paperlens_test 往返验证；开发库只 upgrade，禁止 downgrade。迁移必须保留所有既有表和数据。
4. MetricRecord 的 task_id/paper_id/source 参照完整性、必要索引和数值有限性必须由模型、迁移和服务层共同保证；不要使用删除 User 时级联清空业务数据。

五、测试要求

先更新测试设计，再实现。不得联网、不得真实调用华为云、不得写开发库、不得 mass skip/xfail/删除旧断言。至少覆盖：

1. 指标别名规范化、大小写、Unicode 表头和未知指标拒绝/保留策略。
2. 0、负数、前导小数、科学计数法、百分号、NaN/Infinity、范围、均值±标准差、年份和样本量边界。
3. 百分号统一口径和 API 序列化不漂移。
4. FINAL/MAX/MEAN/BEST/LAST/UNKNOWN 明确上下文、冲突上下文和“仅数值最大不得推断”规则。
5. model/dataset 上下文提取、null 降级、重复候选稳定去重与稳定排序。
6. 每条成功记录具备合法 table_id/row_index 或 evidence_id；伪造/不存在/跨论文来源拒绝。
7. 创建 METRIC_EXTRACTION 任务成功、论文非 PARSED/无候选/重复活动任务失败；REVIEW 任务不回归。
8. 后台成功写 task+records；候选解析、第二来源、数据库写入失败时 task FAILED 且该 task records=0。
9. 指标列表/详情过滤、分页、UUID、extra 字段、未认证 401、用户 A/B 隔离、ADMIN 不默认越权。
10. body/query/header 伪造 user_id 无效；task/paper/source 必须属于当前用户。
11. 全部 P3.5 认证安全测试继续通过，尤其 logout/refresh replay/改密撤销/无 Web Storage token。
12. 测试结束 paperlens_test 17 张业务表全部为 0；开发库开始/结束当前计数严格一致。

测试不能只断言状态码或 snapshot；必须断言 MetricRecord 字段、来源绑定、数据库条数、事务回滚、任务状态、排序、过滤和所有权。

六、文档同步

1. 更新 README、API 契约、security-design、PROGRESS、IMPLEMENTATION_STATUS。
2. 同步 systemDesign/01～06、08；07 只保持指标页面为规划，不虚构已实现 UI。
3. 更新 specs_SDD spec/tasks/design，新增或更新“指标提取”详细设计和 Sprint。
4. 写清指标规范名、百分号存储口径、checkpoint 判断证据、UNKNOWN 降级、来源追溯、去重和失败原子性。
5. 明确 P4.1 没有实现指标前端、CSV/Excel、报告、管理员系统、真实 Huawei 推理。
6. 不覆盖 P3.5 历史验收数字；开发库历史数据异常必须继续诚实保留。

七、最终验证

必须实际执行并报告：

1. 指标提取定向单元/服务/API 测试的 collection/result。
2. `docker compose exec -T backend python -m pytest -q -rs`，0 failed、0 skipped，数量按实际。
3. `npm test -- --run` 全量 66 项基线继续通过；`npm run build` 成功。即使本轮不改前端也必须执行。
4. `alembic current`、`alembic check`；如有 006，在 paperlens_test 验证 downgrade/upgrade，绝不 downgrade 开发库。
5. 实际统计 `/api/v1` 路由数和 ORM 表数，不沿用旧数字。
6. Docker backend/frontend running、postgres healthy；health=200，受保护指标/论文端点无 token=401。
7. Markdown 本地坏路径/坏锚点均为 0，`git diff --check` 无错误。
8. paperlens_test 全部业务表 0；开发库各业务计数测试前后相等，同时明确历史 35/1/1 已不在库中的既知事实。
9. 扫描响应、日志、diff、测试快照，无 JWT secret、密码、refresh/reset 明文、Huawei Key、论文原文或内部 prompt 泄漏。
10. 两个 码道提示词 SHA-256 与开始时一致；最新 Git 提交和禁止范围未变化。

八、最终回复

逐项报告实际 skill/手工替代、修改文件、提取口径、checkpoint 规则、API、任务原子性、认证/所有权、测试、迁移、Docker、路由/表、Markdown、测试库/开发库、secret 扫描和未实现边界。失败或未执行项必须如实写，禁止复用历史数字或把计划写成完成。

不要 git commit，不要修改 .git，不要删除 volume，不要清理/伪造/自动恢复开发库数据，不要写入或打印 secret/token/password，不要真实调用华为云，不要修改或还原 码道提示词文件，不要自行进入 P4.2/P5～P8。
~~~~

---

## 17 — P4.2 指标分析前端与完整任务交互

> 来源：码道在 P4.1 独立纠正并完成代码验收后生成（2026-07-14）

~~~~text
继续维护 D:\shixi\PaperLens 项目。

本轮定义为 P4.2：在 P4.1 已完成且经 码道独立纠正验收的指标后端上，实现用户可操作的指标分析页面、指标任务创建/恢复/轮询、历史结果选择、严格筛选分页和来源追溯交互。P4.1 最终基线为：指标定向 67 passed；Docker 后端全量 385 passed、0 skipped；前端 8 files / 66 passed 且生产构建成功；Alembic 为 007_metric_integrity_corrections head，check 无差异；24 条 `/api/v1` method+path 路由、17 张 ORM 表；Docker backend/frontend running、postgres healthy。

当前开发库在本轮开始前为 2 users / 2 papers / 1 task / 7 reviews / 0 metrics，这是用户注册、上传和审阅产生的真实数据。P4.2 开始和结束必须只读计数并保持完全一致；禁止为截图、E2E 或演示创建账号、上传论文、发起开发库任务、伪造指标、清理记录或删除 volume。P3.4→P3.5 的历史数据异常继续保留在文档中，不要改写或重新归因。

本轮只做指标前端和必要的前端 API 类型，不实现 CSV/Excel、实验数据分析、报告导出、管理员业务 API/控制台、FAISS/pgvector、真实邮件、MFA 或 P5～P8。不得削弱 P3.5 认证安全和 P4.1 指标来源/原子性/用户隔离；不得新增表格详情等后端接口来扩大范围。

先完整阅读并以当前真实代码为准：

- AGENTS.md
- README.md
- frontend/src/api/index.ts、router/index.ts、App.vue
- frontend/src/views/PaperDetailView.vue、ReviewResultView.vue
- frontend/src/tests/ReviewResultView.test.ts、PaperDetailView.test.ts、ApiAuth.test.ts、AuthStore.test.ts
- backend/paperlens/api/tasks.py、metrics.py
- backend/paperlens/schemas/task.py、metric.py
- backend/paperlens/services/metric_service.py
- backend/paperlens/models/models.py
- backend/alembic/versions/006_metric_user_and_constraints.py、007_metric_integrity_corrections.py
- backend/tests/test_api/test_metrics.py、test_review_tasks.py
- docs/api-contract.md、security-design.md、PROGRESS.md、IMPLEMENTATION_STATUS.md
- ProjectDocs/systemDesign/01～08
- ProjectDocs/specs_SDD/PaperLens/spec.md、tasks.md、design/04、07、09、10
- ProjectDocs/sprint/指标提取与口径判断.md
- ProjectDocs/bugfix-report/P4.1-码道独立审查与指标完整性验收收口.md

一、工作流与边界

1. 严格按 AGENTS.md 的 skill 顺序执行：先用 dev-process-framework 校准 P4.2 需求与前端数据流；用 page-mockup 更新 systemDesign/07 和 SDD 前端设计；用 fullstack-testing 先更新 08 测试矩阵；再用 function-detail/frontend-detail 更新 SDD 后编码；最后用 sdd-workflow 更新指标 Sprint。
2. 某个 skill 不可用时明确记录，并按同一顺序手工产出，不能假装调用成功。
3. 开始前记录 git status、最新提交、Docker 状态、开发库/测试库计数、Alembic 状态，以及两个 码道提示词文件 SHA-256。
4. 不执行 git add/commit/reset/checkout/restore/clean/rebase，不修改 `.git/`、`.arts/`、`.codeartsdoer/`、`.skills/`、AGENTS.md 和码道提示词文件。
5. 测试只能写 paperlens_test；不得修改开发库数据，不得 downgrade 开发库，不得删除 volume。
6. 不改变 access 内存存储、refresh HttpOnly/single-flight、sid 会话撤销、真实 user_id 来源或 ADMIN 默认不越权语义。

二、前端 API 与类型

1. 在 frontend/src/api/index.ts 增加严格 CheckpointType、MetricRecord、MetricListResponse、MetricListParams；字段与当前后端完全一致，不沿用旧文档的 `metrics` 包装或 83.1 百分比口径。
2. TaskCreateRequest 改为可区分 union：REVIEW 仍要求原 options；METRIC_EXTRACTION 只允许 `options?: {}`。不得用 any 绕过类型。
3. 新增 `listMetrics(paperId, params)`、`getMetric(metricId)` 和清晰的 `createMetricExtractionTask(paperId)`；查询只发送后端支持的 task_id、metric_name、dataset_name、checkpoint_type、page、page_size，不发送 model_name 或 user_id。
4. 参数为空时不发送空字符串；page_size 不超过 100；错误继续走现有安全 Axios 拦截和认证刷新机制。
5. 不为 P4.2 修改后端响应字段、百分号口径、Checkpoint UNKNOWN、来源二选一或过滤契约。

三、页面与路由

1. 新增受保护路由 `/papers/:id/metrics`，name 建议 `paper-metrics`，实现 `MetricAnalysisView.vue`；PaperDetailView 的 PARSED 导航增加“指标”入口，保持审阅、章节、页面、证据现有行为不回归。
2. 页面先加载 Paper 和同论文 tasks，只处理 task_type=METRIC_EXTRACTION，绝不能把 REVIEW 任务当作指标任务。
3. 默认选择最新一个 SUCCEEDED 指标 task，并始终用 task_id 查询结果，禁止把多个历史任务的 MetricRecord 混在一起。提供历史成功任务选择；排序使用后端返回的 created_at/id 语义。
4. 若存在最新 PENDING/RUNNING 指标任务，恢复轮询 GET /tasks/{id}；任务进行中继续显示上一轮成功结果，不能清空历史结果。
5. 没有指标结果时展示明确空状态和“提取指标”按钮；创建请求固定为 `{task_type:'METRIC_EXTRACTION', options:{}}`，按钮在请求和活动任务期间锁定，快速双击只能创建一次。
6. 新任务 SUCCEEDED 后停止轮询、刷新 tasks、自动选择新 task_id 并加载指标；FAILED/CANCELLED 后停止轮询、显示安全错误并保留上一轮结果，允许用户显式重试。
7. 轮询网络失败不得把任务伪装成 FAILED；显示可恢复错误，用户重试时不能叠加 timer。路由 paper id 变化和组件卸载必须清理 timer，并让旧异步响应失效。
8. 论文 PROCESSING/FAILED/非 PARSED、初始加载失败、tasks 失败、metrics 失败、结果刷新失败分别提供真实可恢复状态；不要把所有错误压成“暂无指标”。

四、指标展示、筛选与追溯

1. 表格至少展示模型、数据集、指标名、指标值、Checkpoint、来源、创建时间；null 使用明确占位，不显示 `null/undefined`。
2. 对 accuracy、precision、recall、F1、AUC、mAP、BLEU、ROUGE、IoU、mIoU 等百分比型规范指标，把后端 0～1 值显示为百分数，并保留可见或可访问的存储值/原始 raw_text；RMSE、MAE、loss 和未知指标不得乘 100。
3. CheckpointType 六种值都有稳定中文标签和样式，UNKNOWN 必须明显但中性；不要根据数值在前端重新推断 BEST/MAX。
4. 提供 metric_name、dataset_name 精确文本筛选、checkpoint_type 下拉和清空操作；筛选变化回到第 1 页，通过后端查询，不做会漏数据的当前页伪过滤。
5. 分页使用 total/page/page_size，上一页/下一页边界正确；快速连续筛选、翻页或 task 切换时，旧响应不得覆盖新目标。
6. Evidence 来源显示“查看证据”，跳转 `{name:'paper-detail', query:{evidence:evidence_id}}`；表格来源显示 table_id、0-based row_index 和 raw_text。当前没有表格详情 API，不生成无效深链。
7. 每条 MetricRecord 理论上只会有一种来源；若服务返回异常的双来源/无来源结构，前端应安全降级显示“来源不可用”，不能崩溃或猜测。
8. raw_text 和所有后端文本只用 Vue 文本插值，不使用 v-html；长文本截断但可展开/查看，避免布局失控和 XSS。
9. 页面需要基本可访问性：表单 label、按钮 disabled/aria 状态、任务进度可读、键盘可操作、颜色不是唯一状态信息；窄屏可横向滚动或卡片降级。

五、状态一致性与复用

1. 优先抽取小型纯函数或 composable 复用 ReviewResultView 已验证的轮询、终态和 request-id 思路，但不要为“复用”大改现有审阅页面。
2. task 进度限制在 0～100；后端未知状态安全显示并停止无限轮询。
3. 页面只信任当前 route paper id、当前 selected task id 和当前请求序号；所有异步回写都先核对上下文。
4. 登录过期继续由全局 auth failure handler 清理内存凭据并安全跳转；页面不得自行把 token 写入 Web Storage。

六、测试要求

先更新测试设计，再实现。不得联网、不得真实调用华为云、不得写开发库、不得 mass skip/xfail/删除旧断言。至少覆盖：

1. API 类型与请求序列化：METRIC_EXTRACTION body、全部过滤、空参数省略、分页边界。
2. 新路由 requiresAuth、PaperDetail 指标入口，以及原审阅/证据链接不回归。
3. 首次无结果、最新成功任务、多个历史任务严格按 task_id 分组，不混合结果。
4. PENDING/RUNNING 恢复轮询；SUCCEEDED 刷新并切换；FAILED/CANCELLED 停止且保留旧结果。
5. 创建锁、防双击、409 活动任务、网络失败重试、timer 不叠加与卸载清理。
6. paper id、task、筛选、翻页快速变化下旧响应失效。
7. 百分比与非百分比显示、六类 Checkpoint、null 字段和异常来源降级。
8. Evidence 深链包含单一 evidence query；表格来源不生成不存在路由。
9. raw_text/模型/数据集含 HTML 时按纯文本显示，不执行脚本。
10. 401 继续走现有 single-flight refresh/登录跳转，token 不进入 localStorage/sessionStorage。
11. 现有 ReviewResultView、PaperDetailView、认证 store/API 测试全部继续通过。
12. 后端 P4.1 定向和全量回归继续通过；测试结束 paperlens_test 17 张业务表全部为 0，开发库计数前后一致。

测试不能只断言组件存在或 snapshot；必须断言请求参数、task_id 选择、状态迁移、timer、旧响应、结果保留、格式化、来源链接和错误恢复。

七、文档同步

1. 更新 README、PROGRESS、IMPLEMENTATION_STATUS，明确 P4.2 指标页面已实现及当前真实测试数。
2. 同步 systemDesign/01～08，重点更新 07 页面状态和 08 交互测试矩阵。
3. 更新 specs_SDD spec/tasks/design/04、07、09、10 和指标 Sprint；不要把 CSV/Excel、表格详情 API 或报告写成已实现。
4. 写清历史 task_id 隔离、百分比显示规则、UNKNOWN、来源降级、轮询生命周期和 Evidence 深链。

八、最终验证

必须实际执行并报告：

1. 新增指标前端定向测试的 collection/result。
2. `npm test -- --run` 全量实际数量；`npm run build` 成功。
3. `docker compose exec -T backend python -m pytest -q -rs`，0 failed、0 skipped；P4.1 指标定向继续通过。
4. `alembic current` 为 007，`alembic check` 无差异；本轮不新增迁移。
5. 实际统计 `/api/v1` method+path 路由和 ORM 表数，不沿用旧数字。
6. Docker 三容器正常、health=200、无 token 论文/指标端点=401、前端 `/papers/<uuid>/metrics` history fallback=200。
7. 若 browser skill 可用，只在不创建/修改开发库数据的既有会话下验证路由、布局和控制台；否则明确记录未执行，不能伪造浏览器 E2E。
8. Markdown 本地坏路径/坏锚点为 0，`git diff --check` 无错误。
9. paperlens_test 业务表为 0；开发库开始/结束严格保持 2/2/1/7/0，除非用户在并行操作，若变化必须只读核对并如实报告。
10. 扫描 diff、构建产物和日志，无 token、密码、JWT secret、Huawei Key、论文原文或内部 prompt 泄漏。
11. 两个 码道提示词 SHA-256 与开始时一致；最新 Git 提交和禁止范围未变化。

九、最终回复

逐项报告实际 skill/手工替代、页面与状态机、API 类型、历史结果隔离、筛选分页、来源追溯、安全、测试、构建、后端回归、迁移、Docker、路由/表、Markdown、测试库/开发库和未实现边界。失败或未执行项必须如实写，禁止复用历史数字或把计划写成完成。

不要 git commit，不要修改 .git，不要删除 volume，不要清理/伪造开发库数据，不要写入或打印 secret/token/password，不要真实调用华为云，不要修改或还原 码道提示词文件，不要自行进入 P5～P8。
~~~~

---

## 18 — P4.3 华为云 MaaS LLM 运行配置与安全联调准备

> 来源：码道在 P4.2 独立纠正并完成代码验收后生成（2026-07-14）

~~~~text
继续维护 D:\shixi\PaperLens 项目。

本轮定义为 P4.3：不改写已完成的 HuaweiMaaSLLMClient，而是把当前 Docker Compose 强制 `PAPERLENS_LLM_BACKEND=mock` 的部署缺口收口，使用户能够在不提交密钥、不影响默认离线测试的前提下，通过本地 `.env` 明确切换华为云 ModelArts Studio（MaaS）LLM，并提供“只检查配置”和“用户显式确认后才产生费用”的最小烟测命令。本轮先接 LLM；Embedding 必须继续保持 mock，等待 LLM 真实小额联调成功后再单独切换。

P4.2 最终基线：P4.2 前端定向 59 passed；前端全量 106 passed（10 files）；生产构建 126 modules；P4.1 后端定向 67 passed；Docker 后端全量 385 passed、0 skipped；Alembic 为 007 head 且 check 无差异；24 条 `/api/v1` method+path 路由、17 张 ORM 表；测试库残留 0；开发库为 2 users / 2 papers / 1 task / 7 reviews / 0 metrics；Docker 三容器运行且 PostgreSQL healthy。

本轮开始前先完整阅读并以当前代码为准：

- AGENTS.md、README.md、.env.example、.gitignore、docker-compose.yml
- backend/paperlens/core/config.py
- backend/paperlens/services/llm_client.py、huawei_maas_llm.py
- backend/paperlens/services/embedding_client.py、huawei_maas_embedding.py
- backend/paperlens/cli.py、api/tasks.py、services/review_service.py
- backend/tests/test_services/test_huawei_maas_llm.py、test_llm_client.py、test_review_service.py
- ProjectDocs/systemDesign/01～08、specs_SDD/PaperLens、相关 Sprint
- docs/PROGRESS.md、IMPLEMENTATION_STATUS.md、architecture.md、security-design.md

用户已在“西南-贵阳一”控制台的调用说明中确认：API 地址为 `https://api.modelarts-maas.com/v2/chat/completions`，model 参数为 `glm-5.2`。项目配置使用去掉末尾 `/chat/completions` 的 base URL，即 `https://api.modelarts-maas.com/v2`。控制台实际调用说明优先于可能滞后的公开区域列表。用户曾在聊天中粘贴过一把 API Key，该 Key 必须视为已泄露并由用户在控制台删除重建；禁止读取、恢复、使用、测试或写入那把旧 Key。新 Key 只能由用户稍后直接写入本机忽略的 `.env`，不得发送给码道或 码道。

一、工作流与边界

1. 严格按 AGENTS.md 的 skill 顺序执行：dev-process-framework 校准运行配置与运维边界；本轮无新 UI，page-mockup 只记录不需要页面变更；fullstack-testing 先补配置/CLI/回归测试设计；function-detail 更新 SDD 后编码；sdd-workflow 更新独立 Sprint。skill 不可用时明确记录并按同一顺序手工产出。
2. 开始前记录 git status、最新提交、Docker 状态、开发库/测试库只读计数、Alembic 状态和两个 码道提示词文件 SHA-256。
3. 禁止 git add/commit/reset/checkout/restore/clean/rebase；禁止修改 `.git/`、`.arts/`、`.codeartsdoer/`、`.skills/`、AGENTS.md 和两个 码道提示词文件。
4. 不真实访问华为云，不产生推理费用，不创建/读取用户 API Key，不向用户索要或打印 secret。本轮所有自动测试必须离线，使用 MockTransport/假 client。
5. 不修改开发库业务数据，不发起真实 REVIEW/METRIC 任务，不创建账号/论文，不删除 volume，不 downgrade 开发库。
6. 不进入 CSV/Excel、实验分析、报告导出、管理员系统、OBS、FAISS/pgvector、Embedding 真实切换或其他 P5～P8 功能。

二、Docker Compose 安全切换

1. 将 backend 当前硬编码 `PAPERLENS_LLM_BACKEND: mock` 改为带安全默认值的单项环境变量透传：未配置时仍必须是 mock。
2. 只逐项透传 LLM 所需变量：`PAPERLENS_LLM_BACKEND`、`PAPERLENS_LLM_BASE_URL`、`PAPERLENS_LLM_MODEL`、`PAPERLENS_LLM_API_KEY`、`PAPERLENS_LLM_TIMEOUT_SECONDS`、`PAPERLENS_LLM_MAX_COMPLETION_TOKENS`。不要用宽泛 `env_file` 把本地所有变量注入容器。
3. `PAPERLENS_LLM_API_KEY` 在 mock 模式下允许为空；huawei_maas 模式必须由被 Git 忽略的 `.env` 或部署平台 secret 注入。Compose 和代码不得包含真实值、示例真值或可用 token。
4. 本轮显式保持 `PAPERLENS_EMBEDDING_PROVIDER=mock`，即使宿主 `.env` 中误设 embedding 变量也不得提前产生向量化费用。
5. 保持数据库 URL、JWT secret、cookie、安全认证、卷和端口现有行为；不得为了 MaaS 改成开发弱口令或关闭 TLS 校验。
6. 不在含真实 key 的环境执行会展开并打印全部环境的 `docker compose config`、`docker inspect`、`env`、`set` 或日志命令。测试 Compose 展开时只能使用明显无效的测试占位值，并确保输出不进入文档。

三、配置校验与失败行为

1. 保持 `llm_api_key` 为 Pydantic `SecretStr`，异常、repr、日志和 CLI 输出都不得包含 key、Authorization header 或请求 body。
2. huawei_maas 模式必须在真正创建 client 前对 base URL、model、API Key、timeout 和 max tokens 做清晰的 fail-fast 校验；mock 模式不得要求 MaaS 配置。
3. base URL 必须是绝对 HTTPS，禁止 credentials、query、fragment；接受用户控制台给出的 `/v1`、`/v2` 或区域域名，但配置说明要求移除末尾 `/chat/completions`。不得硬编码仅允许某一个华为域名，因为用户可能使用区域或专属服务地址。
4. API Key 去除首尾空白后不能为空；拒绝 `.env.example` 中的说明性占位文本。错误只能说明缺少或无效的配置项，不能回显值。
5. 不修改 HuaweiMaaSLLMClient 已验证的 TLS 默认校验、Bearer 鉴权、非流式请求、无自动重试、响应大小/结构校验和安全错误归一化，除非新增测试先证明真实缺陷。
6. health、登录、论文、指标等不使用 LLM 的接口在 mock 默认配置下必须正常；huawei_maas 缺配置时应在配置检查/创建 LLM client 时安全失败，不产生半创建 REVIEW 任务。

四、CLI 运维入口

1. 在现有 `python -m paperlens.cli` 中新增 `maas-config-check`：完全不联网，只验证当前 LLM 配置和 client 可构造性。
2. config-check 成功只输出非敏感摘要：backend、base URL 的 scheme/host/path、model、timeout、max tokens、`api_key_configured=true/false`、embedding_provider。绝不输出 key 长度、前后缀、hash、header 或完整环境。
3. 新增 `maas-smoke --confirm-billable`：没有该显式 flag 必须拒绝并且不构造/调用 client；backend 不是 huawei_maas 也拒绝。
4. smoke 使用极小固定提示进行一次非流式 chat，只判断返回 content 为非空文本；成功仅输出固定成功消息和可选字符数，不打印模型原文。失败使用固定安全摘要，不打印 response body、URL query、header、key 或论文内容。
5. 自动测试绝不能执行真实 smoke。测试通过 fake client/MockTransport 断言确认门、单次调用、非空响应、异常安全和 stdout/stderr 无 secret。
6. 不让 CLI 读取、修改数据库；`promote-admin` 现有行为和测试不得回归。

五、环境示例与文档

1. `.env.example` 保持 `PAPERLENS_LLM_BACKEND=mock`，提供空 API Key 和注释化 MaaS 示例；明确 base URL/model 必须复制用户控制台“调用说明”，base URL 不含 `/chat/completions`。
2. README 给出顺序：在华为云目标 Region 开通服务与最小权限 API Key → 立即安全保存只显示一次的 key → 写入本地忽略的 `.env` → 运行 config-check → 重建 backend/frontend → 用户明确确认计费后手工运行 smoke。
3. README 明确 API Key 与 Region/服务权限相关；优先自定义最小访问范围/IP 白名单；删除 key 后立即失效；不把 key 粘贴到聊天、提示词、命令参数、截图、日志或 Git。
4. 说明 v1/v2、区域域名、模型名都可能不同，项目不替用户选择付费模型；禁止把 `glm-5.2` 或任意模型写成所有区域保证可用。
5. 更新 docs/architecture.md、security-design.md、PROGRESS.md、IMPLEMENTATION_STATUS.md；同步 systemDesign 01～08、SDD spec/tasks/design 和新 Sprint `ProjectDocs/sprint/华为云MaaS运行接入.md`。
6. 新文档区分“适配器已实现”“Compose 可配置”“真实账号网络/计费烟测尚未由用户执行”三种状态；本轮结束不能写成已完成真实云端验收。

六、测试要求

1. 先更新 `ProjectDocs/systemDesign/08-测试设计.md`，再实现测试；不得联网、mass skip/xfail 或删除旧断言。
2. 覆盖 mock 默认无需 MaaS key，huawei_maas 缺 key/空白/占位值安全失败，合法 HTTPS/区域 base URL 可构造。
3. 覆盖 Compose 默认 mock、显式 huawei_maas 逐项透传、embedding 始终 mock；测试值必须明显无效且不记录为真实 secret。
4. 覆盖 config-check 不联网且不泄密；smoke 缺确认拒绝、错误 backend 拒绝、fake client 只调用一次、空内容失败、异常不泄露 response/key。
5. 继续覆盖 Huawei MaaS LLM MockTransport 的 endpoint、Bearer、payload、超时、4xx/5xx、非 JSON、超大响应和 secret-safe 异常。
6. 运行 Docker 后端全量、前端全量和生产构建；测试结束 paperlens_test 17 张业务表残留总数必须为 0，开发库计数必须保持 2/2/1/7/0。

七、最终验证

必须实际执行并报告：

1. 新增 MaaS 配置/CLI 定向测试 collection/result，以及现有 Huawei MaaS LLM 定向回归。
2. `docker compose exec -T backend python -m pytest -q -rs`，0 failed、0 skipped。
3. `npm test -- --run` 全量与 `npm run build` 成功，P4.2 106 项基线不得减少。
4. `alembic current` 为 007、`alembic check` 无差异；本轮不新增迁移。
5. `/api/v1` method+path 仍为 24，ORM 表仍为 17；health 200、login 200、无 token metrics 401。
6. 默认 mock 模式启动三容器且 PostgreSQL healthy；只运行不联网的 config-check。禁止运行真实 `maas-smoke`。
7. 测试库残留 0；开发库前后 2 users / 2 papers / 1 task / 7 reviews / 0 metrics。
8. `git diff --check`、secret/Web Storage/敏感日志扫描、Markdown 路径和锚点检查；提示词文件哈希不得被码道修改；最新 Git 提交不得变化。

八、最终回复

逐项报告 skill/手工替代、Compose 变量、默认 mock、Embedding 强制 mock、配置校验、CLI 确认门、secret 防护、离线测试、全量回归、构建、迁移、Docker、路由/表、Markdown、测试库/开发库和未执行的真实云端烟测。任何未执行项必须如实写明。

不要 git commit，不要修改 码道提示词，不要真实调用华为云，不要生成或读取真实 API Key，不要打印环境或 secret，不要修改开发库，不要删除 volume，不要提前切换 Embedding，不要进入 P5～P8。
~~~~

## 19 — P5.1 CSV/Excel 实验文件安全上传与结构解析

> 来源：码道在 P4.3 独立纠正、真实 MaaS 最小烟测及 GLM 审阅围栏修复后更新（2026-07-14）

~~~~text
继续维护 D:\shixi\PaperLens 项目。

本轮定义为 P5.1：实现 CSV/XLSX/XLS 实验文件的安全上传、确定性结构解析、元数据列表和详情 API。只完成“文件进入系统并得到可信结构描述”的后端闭环，不实现统计摘要、论文指标交叉验证、ExperimentResult、实验分析任务、实验前端或报告导出。

P4.3 最终基线：MaaS 配置/CLI/Huawei LLM 定向 110 passed、0 skipped；真实审阅围栏修复定向 138 passed、0 skipped；Docker 后端全量 435 passed、0 skipped；前端 10 files / 106 passed；生产构建 126 modules；Alembic 为 007 head 且 check 无差异；24 条 `/api/v1` method+path 路由、17 张 ORM 表；测试库 17 张业务表残留 0；开发库为 2 users / 3 papers / 2 tasks / 7 reviews / 0 metrics；三容器运行且 PostgreSQL healthy；health/login 200、无 token metrics 401；77 个本地 Markdown 链接、0 断链；最新提交仍为 `4659a0b8e634ec539c3d96994cf55e745c8d8b39`。用户明确授权的真实华为云 `glm-5.2` 最小烟测已成功；首次完整审阅因模型返回标准 JSON 围栏而安全失败，码道已完成严格单层围栏兼容和 SQL 参数日志脱敏，但未自动进行修复后的真实计费重试，长文本质量与生产费用仍未验收。

开始前完整阅读并以当前代码为准：AGENTS.md、README.md、.gitignore、docker-compose.yml、backend/paperlens/core/config.py、models/models.py、core/enums.py、api/papers.py、utils/storage.py、core/deps.py、tests/conftest.py、alembic 001～007、ProjectDocs/systemDesign/01～08、specs_SDD/PaperLens/spec.md、tasks.md、design/05、08、09、docs/api-contract.md、security-design.md、PROGRESS.md、IMPLEMENTATION_STATUS.md。

## 一、工作流和边界

1. 严格按 AGENTS.md：dev-process-framework 先更新 systemDesign 01～06；本轮无 UI，page-mockup 只把 P07 标记为仍未实现；fullstack-testing 先更新 08；function-detail 更新 SDD 后再编码；sdd-workflow 新建 `ProjectDocs/sprint/实验数据上传与解析.md`。skill 不可用时明确记录并按相同顺序手工完成。
2. 开始前记录 git status、最新提交、Docker 状态、007 Alembic 状态、路由/表数量、测试库残留、开发库只读计数和两个 码道提示词 SHA-256。
3. 禁止 git add/commit/reset/checkout/restore/clean/rebase；禁止修改 `.git/`、`.arts/`、`.codeartsdoer/`、`.skills/`、AGENTS.md 和两个 码道提示词文件；不得还原现有未提交改动。
4. 禁止读取、搜索、打印或复制本机 `.env`、API Key、JWT secret、Authorization、cookie 或完整环境；禁止运行 `docker compose config`、`docker inspect`、`env`、`set` 或可能展开 secret 的日志命令。
5. 禁止真实调用华为云，禁止运行 `maas-smoke`。pytest 必须继续由 conftest 强制 LLM/Embedding mock、`.invalid` endpoint 并移除继承 API Key；实验解析不得调用 LLMClient、EmbeddingClient 或任何网络。
6. 不实现统计摘要、ExperimentResult、EXPERIMENT_ANALYSIS 任务、指标交叉验证、P07 前端、报告、管理员系统、OBS、FAISS/pgvector 或 P5.2～P8；不修改开发库业务数据，不删除 volume。

## 二、先校准设计和数据契约

1. 将 P5.1 定义为同步上传与结构预检：临时文件完整落盘并校验后，在工作线程中解析；成功才进入持久存储和数据库。本轮不创建 AnalysisTask。
2. 新增 `ExperimentFileType`：CSV、XLSX、XLS。`columns_info` 采用带版本的稳定 JSON 对象，至少包含 `version`、`encoding`（Excel 为 null）、`delimiter`（Excel 为 null）、`sheet_name`（CSV 为 null）和按原始顺序排列的 `columns`。每列只保存 `name`、规范化 `dtype`、`nullable`、`null_count`，不得保存样本值或整行数据。
3. 规范化 dtype 仅允许 `integer|float|boolean|datetime|string|empty`；混合或不确定类型降级为 string。所有计数必须是普通有限 JSON 数字，不得产生 NaN/Infinity。
4. 单文件限制：实际读取字节 1～20MB；数据行 1～100000（不含表头）；列 1～256；列名去除 BOM 后不得为空、重复、含控制字符或超过 128 code point。文件名只保留 basename，不得含控制字符，长度不超过 255。
5. CSV 明确支持 UTF-8/UTF-8 BOM，必要时可确定性回退 GB18030；分隔符只允许逗号、分号或 Tab，解析结果必须唯一稳定。拒绝 NUL、无法完整解码、行字段数不一致、无表头和仅表头文件。
6. XLSX 必须是合法 ZIP 且含 `[Content_Types].xml`、`xl/workbook.xml`；限制 ZIP entry 数、总解压大小和压缩比，拒绝路径穿越、加密 entry、宏、externalLinks、嵌入对象和多个非空 worksheet。公式单元格本轮拒绝，避免缓存值不确定。
7. XLS 必须同时满足 `.xls` 扩展名、OLE Compound File magic 和解析器成功；解析器不得执行宏、DDE、外部链接或网络。`.xlsm`、`.xlsb`、压缩 CSV、伪装扩展名一律 415。
8. 更新 `ProjectDocs/specs_SDD/PaperLens/design/05-实验数据分析.md` 为“P5.1 上传/结构解析已实现，统计与交叉验证仍规划”；同步 design/08 数据约束、design/09 API、spec/tasks 和 docs 契约。

## 三、迁移 008 与 ORM 完整性

1. 新建单一迁移 `008_experiment_file_integrity.py`，revision 链接 007；不要修改 001～007。
2. 在迁移前只读检查开发库 experiment_files 是否为空或是否存在冲突；不得删除、修补或伪造用户数据。若已有数据与约束冲突，立即停止并如实报告。
3. 为 experiment_files 增加并在 ORM 镜像：file_type 枚举值 CHECK；file_size > 0；file_hash 恰为 64 个小写十六进制字符；row_count 为 1～100000；column_count 为 1～256；`UNIQUE(user_id, paper_id, file_hash)` 防止同用户同论文重复文件。
4. columns_info 上传成功后必须非空 JSON object；如果 PostgreSQL CHECK 无法安全验证完整 JSON schema，只在服务/Pydantic 严格验证，不写伪强约束。
5. 迁移 upgrade/downgrade 可逆，名称稳定；`alembic check` 必须无差异。表数量仍为 17，最终 head 应为 008。

## 四、安全上传、解析与存储

1. 新建独立 experiment file parser/service，不把大量逻辑塞进 API。解析器输入只能是服务端临时文件路径和已确认类型，输出纯元数据；不得持有数据库 Session、不得访问网络。
2. UploadFile 必须按固定块流式写入随机临时文件，不能只信 Content-Length/MIME；超过限制立即 413。所有成功、校验失败、解析失败、数据库失败和客户端断开路径都要关闭 UploadFile 并删除临时文件。
3. 校验顺序：安全文件名/扩展名 → 实际字节上限 → magic/容器预检 → SHA-256 → 确定性解析 → 重复检查 → 保存 storage → 插入数据库并提交。解析失败不能留下 storage object 或 ExperimentFile。
4. 泛化 `StorageBackend.build_key`，PDF 现有 key 必须仍为 `papers/{paper_id}/source.pdf`；实验文件使用不可猜 UUID 目录和内部固定名 `source.csv|source.xlsx|source.xls`，绝不使用用户路径。新增/修改测试证明 PDF 行为未回归。
5. 同一 user/paper/file_hash 重复上传返回已有资源且不得重复保存；明确新建 201、幂等重复 200 的响应语义。并发重复依赖数据库唯一约束收口，最终只能有一行和一个 storage object。
6. storage.save、flush、commit 任一步失败都必须 rollback 并清理未归属对象；清理失败只记录 object key 和异常类型，不能记录数据内容、文件名、路径、SQL 参数或 secret。
7. 仅允许给当前用户自己的 `PARSED` 论文上传；不存在、跨用户或 ADMIN 访问他人论文统一 404，未解析论文 409。user_id 只来自认证上下文，不能接受客户端传入。

## 五、P5.1 API

1. 新增 `POST /api/v1/papers/{paper_id}/experiment-files/upload`：multipart file；成功返回 id、paper_id、filename、file_type、file_size、file_hash（不要公开完整 hash，可省略或只在内部保留）、row_count、column_count、columns_info、duplicate、created_at。
2. 新增分页 `GET /api/v1/papers/{paper_id}/experiment-files?page=1&page_size=20`：稳定按 created_at DESC、id DESC；page 1 起，page_size 1～100；只返回当前用户论文下资源。
3. 新增 `GET /api/v1/experiment-files/{file_id}` 返回单条结构元数据；不存在和跨用户统一 404。不要新增原始文件下载、预览行数据或 result API。
4. 统一 Pydantic schema，禁止直接返回 ORM/任意 dict；错误使用 AppError 稳定 code/status：415 类型或 magic 不符、413 超限、422 内容/结构不可解析、409 论文状态冲突、404 不存在/跨用户、500 固定安全上传失败。
5. 将 router 注册到 main；预计 `/api/v1` method+path 从 24 增至 27。不要修改现有论文、审阅、指标和认证响应。

## 六、离线测试要求

1. 先更新测试设计，再写测试；不得联网、skip/xfail 或删除旧断言。新增依赖必须固定版本并与 Python 3.13 兼容，Docker 构建成功。
2. 解析单元测试覆盖：UTF-8/BOM/中文/GB18030 CSV、三种 delimiter、合法 XLSX、合法 XLS；dtype/null_count/顺序；空文件、仅表头、重复/空/超长列名、不同行宽、错误编码、NUL、超行/列。
3. 容器安全覆盖：扩展名/magic 不匹配，伪 XLSX ZIP、路径穿越、zip bomb、过高压缩比、encrypted、macro、externalLinks、嵌入对象、多非空 sheet、公式单元格、错误 OLE。
4. API/PostgreSQL 覆盖：无 token 401；新建 201；重复 200 且一行/一对象；并发重复只一行；列表分页稳定；详情；不存在/跨用户/ADMIN 他人均 404；非 PARSED 409；真实 413/415/422。
5. 失败注入覆盖临时文件、parser、storage.save、flush、commit、cleanup；断言数据库与 storage 不残留。不得通过 mock 跳过目标生产函数。
6. 明确 monkeypatch LLM/Embedding 工厂为“一旦调用即失败”，证明实验上传解析完全离线。另加断言测试会话仍强制 mock 且环境中两类 API Key 对 Settings 不可见。
7. 继续运行 P4.3/Huawei LLM 定向、P4.1 指标定向、Docker 后端全量、前端全量和构建；后端基线不得少于 435，前端不得少于 106。

## 七、文档和最终验收

1. 同步 systemDesign 01～08、SDD spec/tasks/design 05/08/09、Sprint、README、docs/api-contract.md、data-model.md、architecture.md、security-design.md、PROGRESS.md、IMPLEMENTATION_STATUS.md。
2. 所有文档必须区分：P5.1 上传/结构解析已实现；统计、ExperimentResult、交叉验证、实验前端仍未实现；真实 MaaS 最小连通性烟测已成功，但长文本审阅质量和生产费用未验收。
3. 实际执行并报告：P5.1 定向 collection/result；P4.3 定向；`docker compose exec -T backend python -m pytest -q -rs` 为 0 failed/0 skipped；前端 106+；生产构建成功。
4. Alembic current=head 008，check 无差异；API method+path=27，ORM 表=17；默认三容器运行、PostgreSQL healthy；health/login 200、无 token experiment-files 401。
5. 测试结束 paperlens_test 17 张业务表残留总数 0；开发库仍为 2 users / 3 papers / 2 tasks / 7 reviews / 0 metrics，且 experiment_files/experiment_results 不得因验证新增数据。
6. 执行 git diff --check、通用高熵 secret 候选文件扫描、Web Storage/敏感日志扫描、Markdown 本地路径和锚点检查；禁改目录、提示词哈希和最新提交必须不变。
7. 不运行真实 MaaS config 展开或 smoke，不读取 `.env`。任何受权限或环境限制未执行的项目必须如实标明，不能用历史结果冒充。

最终逐项报告 skill/手工替代、依赖、迁移、解析边界、ZIP/OLE 安全、API、用户隔离、幂等/并发、storage 补偿、离线保证、定向/全量测试、前端、迁移、路由/表、HTTP、数据库残留、secret/Markdown 和明确未实现项。

不要 git commit，不要修改 码道提示词，不要读取或使用 API Key，不要真实调用华为云，不要修改开发库，不要删除 volume，不要提前实现 P5.2～P8。
~~~~

## 20 — P5.2 实验数据确定性统计摘要后端闭环

> 来源：码道在 P5.1 独立审查、安全纠正和全量验收后更新（2026-07-14）

~~~~text
# 码道下一阶段提示词：P5.2 实验数据确定性统计摘要后端闭环

继续维护 D:\shixi\PaperLens 项目。

本轮定义为 P5.2：在已验收的 P5.1 CSV/XLSX/XLS 安全上传与可信结构解析基础上，实现实验文件的确定性统计任务、ExperimentResult 原子写入和结果查询 API。只完成“已上传实验文件 → 后台统计任务 → 可查询严格统计摘要”的后端闭环；不做论文 MetricRecord 交叉验证、不做 P07 实验前端、不做删除/下载/行预览或报告导出。指标交叉验证单独留到 P5.3，避免在没有明确匹配语义时猜测 BEST/FINAL/LAST。

P5.1 最终真实基线：解析/存储/API 定向 103 passed、0 skipped；P4.3 MaaS/LLM/审阅广义定向 180 passed、0 skipped；P4.1 指标定向 67 passed、0 skipped；Docker 后端全量 527 passed、0 skipped；前端 10 files / 106 passed；生产构建 126 modules；Alembic 为 008 head 且 check 无差异；27 条 `/api/v1` method+path 路由、17 张 ORM 表；测试库 17 表残留 0；开发库为 2 users / 3 papers / 3 tasks / 14 review_results / 0 metrics / 0 experiment_files / 0 experiment_results；三容器运行且 PostgreSQL healthy；health/login 200、无 token experiment-file 401；77 个本地 Markdown 链接、0 断链；最新提交仍为 `4659a0b8e634ec539c3d96994cf55e745c8d8b39`。008 已实际验证不兼容记录原值保留并无损中止，以及 007→008→007→008 可逆。真实华为云 `glm-5.2` 最小烟测已成功，但长文本质量和生产费用仍未验收；本轮禁止真实云端调用。

开始前完整阅读并以当前代码为准：AGENTS.md、README.md、.gitignore、docker-compose.yml、backend/paperlens/core/config.py、core/enums.py、models/models.py、schemas/task.py、schemas/experiment_file.py、api/tasks.py、api/experiment_files.py、services/experiment_file_parser.py、services/experiment_file_service.py、utils/storage.py、tests/conftest.py、tests/db_helpers.py、alembic 001～008、ProjectDocs/systemDesign/01～08、specs_SDD/PaperLens/spec.md、tasks.md、design/04/05/08/09、Sprint、docs/api-contract.md、data-model.md、architecture.md、security-design.md、PROGRESS.md、IMPLEMENTATION_STATUS.md 和 P5.1 bugfix report。

## 一、工作流、基线和禁止事项

1. 严格按 AGENTS.md：dev-process-framework 先更新 systemDesign 01～06；本轮无 UI，page-mockup 只确认 P07 继续 PLANNED；fullstack-testing 先更新 08；function-detail 更新 SDD 后再编码；sdd-workflow 新建 `ProjectDocs/sprint/实验数据统计摘要.md`。skill 不可用时明确记录并按同序手工完成。
2. 开始前记录 git status、HEAD、Docker 状态、008 current/check、路由/表数、测试库残留、开发库七表只读计数和两个 码道提示词 SHA-256。
3. 禁止 git add/commit/reset/checkout/restore/clean/rebase；禁止修改 `.git/`、`.arts/`、`.codeartsdoer/`、`.skills/`、AGENTS.md 和两个 码道提示词文件；不得还原现有未提交改动。
4. 禁止读取、搜索、打印或复制 `.env`、API Key、JWT secret、Authorization、cookie 或完整环境；禁止 `docker compose config`、`docker inspect`、`env`、`set` 和可能展开 secret 的日志命令。
5. 禁止真实调用华为云和 `maas-smoke`。pytest 继续强制 LLM/Embedding mock、`.invalid` endpoint 并移除继承 Key；统计服务不得构造 LLM/Embedding client 或访问网络。
6. 不实现 MetricRecord 交叉验证、MATCH/MISMATCH、P07 前端、ExperimentFile 删除/下载、原始行预览、报告、管理员系统、OBS、FAISS/pgvector 或 P5.3～P8；不修改开发库业务数据，不删除 volume。

## 二、先校准 P5.2 数据与统计契约

1. 将阶段拆分写清：P5.1 上传/结构解析已实现；P5.2 只做统计摘要；P5.3 才做论文指标交叉验证和实验前端。不得继续把三者混写成同一已完成能力。
2. 统计输入必须来自 ExperimentFile 的内部 storage_key。读取后重新计算 SHA-256，并重新执行 P5.1 magic/容器安全和结构解析；hash、file_type、row_count、column_count、columns_info 任一与数据库不一致都按文件损坏安全失败，不能基于被替换文件计算。
3. 复用/扩展 P5.1 路径型解析边界，提供逐行规范值读取；不得回退为 `UploadFile.read()`、原始 bytes 生产入口、pandas DataFrame 或一次性保存全部原始行。
4. `summary_stats` 采用 version=1 严格 JSON object，按原列顺序返回 `columns`。每列包含 `name`、P5.1 `dtype`、`count`（非空数）、`null_count` 和 `stats`；只有 integer/float 列的 stats 为对象，其余 dtype 的 stats 必须为 null。
5. 数值 stats 固定字段：`mean`、`stddev`、`min`、`max`、`median`。stddev 明确定义为样本标准差（ddof=1），count<2 时为 null；median 为精确中位数，偶数样本取中间两值均值。boolean 不按 0/1 参与数值统计。
6. 所有公开数字必须是有限 JSON number；拒绝 NaN/Infinity、计算溢出和超过 JavaScript 安全整数范围的 integer，不允许静默截断、转 0 或转字符串。空列 count=0/null_count=row_count/stats=null。
7. 用 Welford 或同等稳定算法计算 mean/stddev；中位数只保存紧凑数值数组，逐列排序并及时释放，不保留原始字符串/整行。新增配置 `max_experiment_analysis_numeric_cells`，默认 5,000,000，合法范围 1～10,000,000；以 `row_count × numeric_column_count` 做保守前置限制，超限不创建任务并返回 413 `ANALYSIS_TOO_LARGE`。
8. ExperimentResult 本轮只写 `summary_stats`；`column_analysis` 和 `metric_comparisons` 保持 null。公开结果 schema 不暴露这两个规划字段、文件 hash、storage key、样本或原始行。

建议的稳定结果形状：

```json
{
  "version": 1,
  "row_count": 3,
  "column_count": 2,
  "columns": [
    {
      "name": "accuracy",
      "dtype": "float",
      "count": 2,
      "null_count": 1,
      "stats": {
        "mean": 0.9,
        "stddev": 0.0282842712474619,
        "min": 0.88,
        "max": 0.92,
        "median": 0.9
      }
    },
    {
      "name": "model",
      "dtype": "string",
      "count": 3,
      "null_count": 0,
      "stats": null
    }
  ]
}
```

## 三、迁移 009 与 ORM

1. 新建单一 `009_experiment_analysis_task_link.py`，revision 连接 008；不要改 001～008。
2. 迁移前只读检查开发库是否存在 `EXPERIMENT_ANALYSIS` 历史任务或其他冲突；不得删除、修补或伪造数据，发现不兼容立即中止并如实报告。
3. 为 `analysis_tasks` 新增 nullable `experiment_file_id` UUID FK → `experiment_files.id`，`ON DELETE RESTRICT`；已有 REVIEW/METRIC_EXTRACTION 任务保持 null。
4. 增加并在 ORM 镜像：普通索引 `idx_task_experiment_file_id`；CHECK 保证 `task_type='EXPERIMENT_ANALYSIS'` 当且仅当 experiment_file_id 非空；部分唯一索引 `uq_active_experiment_task_per_user_file(user_id, experiment_file_id)`，仅覆盖 PENDING/RUNNING 的 EXPERIMENT_ANALYSIS。
5. 不新增表。ExperimentResult 既有 `file_id UNIQUE` 保证每文件最多一个结果；服务还必须验证 task、file、paper、user 四者同属，不能只依赖 FK。
6. upgrade/downgrade 可逆、命名稳定；对 paperlens_test 测试冲突无损中止和 008→009→008→009；`alembic check` 无差异，表数仍为 17。

## 四、统计任务服务与原子性

1. 新建独立 experiment analysis service/statistics 模块，不把算法塞进 API 或 P5.1 上传 service。
2. 任务创建只允许当前用户自己的 ExperimentFile，且其 Paper 仍为 PARSED；不存在、跨用户和 ADMIN 访问他人统一 404，论文状态冲突 409。
3. 后台函数只接收 task_id，并自行创建/关闭 Session；原子 PENDING→RUNNING，重新加载 task/file/paper/user 关系，再读 storage、验 hash/结构、计算统计。
4. 成功时在同一事务插入唯一 ExperimentResult 并把任务设为 SUCCEEDED/progress=100/completed_at；失败时 rollback 所有结果，单独把任务设为 FAILED，error_message 只能是固定安全分类，不得包含值、行、文件名、路径、storage key、SQL、底层异常正文或 secret。
5. missing object、hash/结构不一致、parser 失败、数值不安全、统计超限、flush/commit 失败都不能留下 ExperimentResult 半成品。commit 结果未知时必须先重新查询归属，不能误删或覆盖已提交结果。
6. 同一文件已有结果或活动任务时幂等返回既有资源；并发创建依赖 009 唯一索引收口，最终最多一条活动任务和一条 ExperimentResult。不得删除或覆盖已存在结果来“重跑”。
7. 本轮沿用 FastAPI BackgroundTasks，文档诚实说明进程重启恢复/持久化队列仍未实现，不伪报生产级任务可靠性。

## 五、P5.2 API

1. 新增 `POST /api/v1/experiment-files/{file_id}/analysis`。新建任务返回 201；活动任务或已有结果返回对应 task 且 200，响应含 task 基本字段和 `duplicate`，不接收 user_id/paper_id/任意统计选项。
2. 新增 `GET /api/v1/experiment-files/{file_id}/result`。结果存在返回 200 和严格 `id/file_id/task_id/summary_stats/created_at`；结果尚不存在返回 404 固定错误，不返回伪造空摘要。
3. 任务状态继续通过现有 `GET /api/v1/tasks/{task_id}` 查询；现有论文任务列表自然包含 EXPERIMENT_ANALYSIS。不要改变既有认证、论文、审阅、指标、P5.1 上传/列表/详情响应。
4. 新 POST 路由不得依赖 `get_llm_client` 或 `get_embedding_client`；实验统计链路即使两工厂被 monkeypatch 为一调用就失败也必须工作。
5. 预计 `/api/v1` method+path 从 27 增至 29；以实际统计为准。

## 六、离线测试要求

1. 先更新 08 测试设计，再写测试；不得联网、skip/xfail 或删除旧断言。尽量只用标准库和现有 openpyxl/xlrd，不新增 pandas/numpy 等重依赖；若确有新增依赖必须固定版本、解释必要性并验证 Python 3.13 干净镜像。
2. 统计单元覆盖 CSV/XLSX/XLS；integer/float、负数、0、null、混合非数值、boolean、datetime、string、empty；奇偶 median、单值/双值 stddev、列顺序、确定性重复结果、无样本泄漏。
3. 数值安全覆盖 NaN/Infinity 文本、超大浮点导致的非有限结果、超 JS 安全整数、count=0/1、5,000,000 cell 边界和前置 413；不得用近似 median 冒充精确结果。
4. 完整性覆盖 storage missing、hash 被替换、file_type/magic/row/column/columns_info 不一致、解析失败；任务 FAILED 且 ExperimentResult 为 0，错误响应/任务 error 不泄漏注入内容。
5. API/PostgreSQL 覆盖无 token 401、新建 201、活动/已有 200、结果 200、未就绪 404、跨用户/ADMIN 他人 404、非 PARSED 409、并发一任务一结果、任务/文件/论文/user 同属校验。
6. 失败注入覆盖 result flush、任务成功 commit、失败状态 commit；断言事务原子、重试查询不产生第二结果。不得 mock 掉目标统计函数来制造“成功”。
7. 迁移覆盖只读冲突中止、数据原值保留、009 downgrade/upgrade；测试结束 17 张业务表残留 0。
8. P5.1 定向继续 103+；P4.3 广义定向 180；P4.1 指标定向 67；Docker 后端全量不少于 527 且 0 skipped；前端 106 和生产构建继续通过。

## 七、文档与最终验收

1. 同步 systemDesign 01～08、SDD spec/tasks/design 05/08/09、独立 Sprint、README、docs/api-contract.md、data-model.md、architecture.md、security-design.md、PROGRESS.md、IMPLEMENTATION_STATUS.md。
2. 文档必须区分：P5.1 上传/结构解析已实现；P5.2 统计摘要已实现；P5.3 交叉验证与实验前端未实现；ExperimentResult 本轮 metric_comparisons 仍为空；真实 MaaS 最小连通性成功但长文本质量/费用未验收。
3. 实际报告 P5.2 定向 collection/result、P5.1/P4.3/P4.1 回归、Docker 全量、前端全量和构建；不能用历史结果冒充。
4. 验证 009 current/head、check、可逆性；实际路由/表数；三容器/健康状态；health/login 200、无 token analysis/result 401。
5. 测试库 17 表残留 0；开发库七表计数必须与开始时一致，experiment_files/results 不得因验证新增。
6. 执行 Python 编译、git diff --check、高熵 secret 候选、生产 Web Storage/v-html、敏感日志、Markdown 路径/锚点检查；禁改目录和 HEAD 不变。两个 码道提示词在码道执行期间 hash 必须不变。
7. 不读取 `.env`，不运行真实 MaaS，不修改开发库。受权限限制未执行的项目必须如实标明。

最终逐项报告工作流、迁移、任务关联、统计定义、数值/内存边界、文件完整性复核、API、用户隔离、幂等并发、事务失败、离线保证、定向/全量测试、前端、迁移/路由/表、HTTP、数据库残留、secret/Markdown 和明确未实现项。

不要 git commit，不要修改 码道提示词，不要读取或使用 API Key，不要真实调用华为云，不要修改开发库，不要删除 volume，不要提前实现交叉验证、实验前端或 P5.3～P8。
~~~~

## 21 — P5.3a 论文指标交叉验证后端闭环

> 来源：码道独立审查 P5.2 后生成（2026-07-14）

~~~~text
# 码道下一阶段提示词：P5.3a 论文指标交叉验证后端闭环

继续维护 D:\shixi\PaperLens 项目。

本轮定义为 P5.3a：在已验收的 P4.1 MetricRecord 与 P5.2 ExperimentResult 确定性统计摘要基础上，实现“指定成功指标任务 → 确定性匹配统计列 → 生成可审计 MATCH/MISMATCH/UNVERIFIABLE 比较 → 原子写入 metric_comparisons → 查询”的纯后端闭环。不得猜测 BEST/FINAL/LAST 的实验含义；不做 P5.3b 实验前端，不做文件删除/下载/行预览，不做报告导出。

P5.2 最终真实基线：P5.2 定向 72 passed、P5.1 回归 103、P4.3 MaaS/LLM/审阅回归 180、P4.1 指标回归 67，均 0 skipped；Docker 后端全量 599 passed、0 skipped；前端 10 files / 106 passed；生产构建 126 modules；Alembic 009 head 且 check 无差异；29 条 `/api/v1` method+path 路由、17 张业务表（18 张含 alembic_version）；测试库七张核心表残留 0；开发库为 2 users / 3 papers / 3 tasks / 14 review_results / 0 metrics / 0 experiment_files / 0 experiment_results；三容器运行且 PostgreSQL healthy；health/login 200、无 token analysis 401。009 已验证冲突原值保留并无损中止，以及 008→009→008→009。当前 HEAD 为 `525828b42707f7d1ef5c8efe1f308ce4bdac5454`，这是 P5.2 开始前已有提交；本轮禁止新增提交。真实华为云 glm-5.2 最小烟测成功，但本轮禁止任何真实云调用。

开始前完整阅读并以当前代码为准：AGENTS.md、README.md、docker-compose.yml、backend/paperlens/core/enums.py、config.py、models/models.py、schemas/metric.py、schemas/experiment_file.py、api/metrics.py、api/experiment_files.py、services/metric_service.py、experiment_statistics.py、experiment_analysis_service.py、tests/conftest.py、tests/db_helpers.py、alembic 001～009、ProjectDocs/systemDesign/01～08、specs_SDD/PaperLens/spec.md、tasks.md、design/04/05/08/09、Sprint、P5.2 bugfix report、docs/api-contract.md、data-model.md、architecture.md、security-design.md、PROGRESS.md、IMPLEMENTATION_STATUS.md。

## 一、工作流与禁止事项

1. 严格按 AGENTS.md：dev-process-framework 先更新 systemDesign 01～06；page-mockup 只确认本轮无 UI；fullstack-testing 更新 08；function-detail 更新 SDD；sdd-workflow 新建 `ProjectDocs/sprint/论文指标交叉验证.md`。skill 不可用时明确记录并手工同序完成。
2. 开始前记录 git status/HEAD、Docker、009 current/check、路由/表数、测试库残留、开发库七表只读计数和两个 码道提示词 SHA-256。
3. 禁止 git add/commit/reset/checkout/restore/clean/rebase；禁止修改 `.git/`、`.arts/`、`.codeartsdoer/`、`.skills/`、AGENTS.md 和两个 码道提示词；不得还原现有未提交改动。
4. 禁止读取、搜索、打印或复制 `.env`、API Key、JWT secret、Authorization、cookie 或完整环境；禁止 `docker compose config`、`docker inspect`、`env`、`set` 和可能展开 secret 的日志命令。
5. 禁止真实调用 MaaS。pytest 强制 LLM/Embedding mock 与 `.invalid` endpoint；交叉验证不得构造 LLM/Embedding client 或访问网络。
6. 不实现 P5.3b 前端、删除/下载/行预览、报告、管理员系统、OBS、FAISS/pgvector、持久化任务队列或 P6～P8；不修改开发库业务数据，不删除 volume。

## 二、确定性交叉验证契约

1. 新增严格请求 `{"metric_task_id":"uuid"}`。metric_task 必须为当前用户、同一论文、SUCCEEDED 的 METRIC_EXTRACTION；其 MetricRecord 必须再次联查 paper/task/user 和来源归属。不存在、跨用户及 ADMIN 他人统一 404；类型、状态或论文冲突返回固定 409。
2. ExperimentFile、P5.2 ExperimentResult、其 EXPERIMENT_ANALYSIS task、Paper 和 User 必须同属；result 必须为严格 version=1 摘要。不得读取 storage 文件、原始行、MetricRecord.raw_text 或 Evidence 正文来猜匹配。
3. 指标名规范化固定为 Unicode NFKC → casefold → 仅保留 `char.isalnum()` 字符。`F1_score` 与 `f1 score` 可匹配；不得添加 acc→accuracy、ppl→perplexity、翻译或模糊相似度别名。规范化结果为空则 UNVERIFIABLE。
4. 只使用 integer/float 摘要列。每个 MetricRecord 独立生成一个 comparison；同一规范指标名必须恰好对应 1 条该任务 MetricRecord 和 1 个数值列，否则状态 UNVERIFIABLE，reason 分别固定为 `AMBIGUOUS_PAPER_METRIC`、`NO_EXPERIMENT_COLUMN` 或 `AMBIGUOUS_EXPERIMENT_COLUMN`。
5. checkpoint 映射仅允许：MEAN→summary stats.mean，MAX→stats.max。BEST、FINAL、LAST、UNKNOWN、null 或其他值均为 UNVERIFIABLE / `UNSUPPORTED_CHECKPOINT`，不得拿 mean/median/max 代替。
6. 新增配置 `experiment_comparison_absolute_tolerance` 默认 1e-6、范围 0～1e12；`experiment_comparison_relative_tolerance` 默认 0.01、范围 0～1。同步 `.env.example` 与 Compose 默认透传，不输出配置环境。
7. 可比较项：`diff = experiment_value - paper_value`；`absolute_diff = abs(diff)`；paper_value 非 0 时 `relative_diff = absolute_diff / abs(paper_value)`，为 0 时 relative_diff=null；`allowed_diff = max(abs_tolerance, abs(paper_value) * relative_tolerance)`；边界 `absolute_diff <= allowed_diff` 为 MATCH，否则 MISMATCH。
8. 所有输入、过程和公开数字必须为有限 JSON number；拒绝 NaN/Infinity、溢出和布尔伪数值，不静默转 null/0/字符串。只允许 UNVERIFIABLE 项的 statistic、experiment_value、diff、absolute_diff、relative_diff、allowed_diff 为 null。
9. 每项固定字段：metric_record_id、metric_task_id、metric_name、checkpoint_type、column_name、statistic（MEAN/MAX/null）、paper_value、experiment_value、diff、absolute_diff、relative_diff、allowed_diff、status、reason。MATCH/MISMATCH 的 reason=null；UNVERIFIABLE 必须有固定 reason。
10. 输出按 `normalized_metric_name, metric_record.created_at, metric_record.id` 稳定排序。不得暴露 model output、raw_text、Evidence 正文、文件 hash、storage key、数据行或内部异常。

## 三、持久化、幂等和事务

1. 不新增迁移或表。P5.3a 只把严格 comparison 列表写入既有 `ExperimentResult.metric_comparisons`，保持 summary_stats 完全不变，column_analysis 继续 null。
2. 新增独立 comparison service，不把匹配算法塞进 API、metric_service 或 P5.2 统计服务。
3. POST 时锁定 ExperimentResult 行并重新验证全部归属与 metric task。metric_comparisons 为 null 时原子写入；已有且所有项 metric_task_id 与本次相同则 200 幂等返回；已有其他 task 来源则 409 `COMPARISON_ALREADY_EXISTS`，不得覆盖、删除或拼接。
4. 两个同 metric_task_id 并发请求最终只写一份且响应为 201/200；不同 metric_task_id 竞争最多一方成功，另一方固定 409。
5. flush/commit 失败必须 rollback，metric_comparisons 仍为 null；commit 结果未知时以新 Session 重查 result 和请求 task_id，已提交则返回成功，不得回滚式覆盖或删除。
6. 没有 MetricRecord 返回 409 `NO_METRICS`。即使所有记录均 UNVERIFIABLE，也应成功持久化诚实结果，不伪造 MATCH/MISMATCH。

## 四、API 与 Schema

1. 新增 `POST /api/v1/experiment-files/{file_id}/comparisons`：首次 201，幂等 200。响应含 file_id、experiment_result_id、metric_task_id、comparisons、duplicate。
2. 扩展 `GET /api/v1/experiment-files/{file_id}/result`，保留全部 P5.2 字段并新增 `metric_comparisons: list | null`；P5.2 尚未交叉验证时必须明确 null。
3. comparison、POST 响应和 GET result 均使用 extra=forbid 严格 Pydantic Schema、有限数验证及跨字段 validator；UNVERIFIABLE 与可比较项字段关系必须被 Schema 强制。
4. 既有认证、论文、审阅、指标、上传、P5.2 analysis/result 的其他行为不变。预计 method+path 路由 29→30，以实际为准。

## 五、离线测试

1. 先更新 08 测试设计再写测试；不得联网、skip/xfail、删除旧断言或 mock 掉目标匹配函数。
2. 单元覆盖 NFKC/casefold/alnum、大小写和分隔符等价、禁止语义别名、MEAN/MAX、BEST/FINAL/LAST/UNKNOWN、零 paper value、负数、容差边界、MATCH/MISMATCH、稳定顺序和非有限/溢出。
3. 覆盖 0/1/多 MetricRecord 与 0/1/多数值列；重复论文指标、重复规范列名、非数值列、空规范名均诚实 UNVERIFIABLE 且 reason 精确。
4. PostgreSQL/API 覆盖 401、201、同源 200、不同源 409、无 P5.2 result、NO_METRICS、错误 task type/status/paper、跨 USER/ADMIN 404、关系篡改和严格响应无泄漏。
5. 用真实两线程覆盖同源/异源并发；注入 JSON flush、commit 前失败和 commit 后抛错，验证原子性及 commit 未知回查。
6. monkeypatch LLM/Embedding 工厂为一调用即失败，交叉验证仍通过；测试库结束 17 张业务表残留 0。
7. P5.2 定向不少于 72；P5.1 103；P4.3 180；P4.1 67；Docker 后端全量不少于 599 且 0 skipped；前端 106 和生产构建继续通过。

## 六、文档与最终验收

1. 同步 systemDesign 01～08、SDD spec/tasks/design 05/08/09、独立 Sprint、README、docs/api-contract.md、data-model.md、architecture.md、security-design.md、PROGRESS.md、IMPLEMENTATION_STATUS.md。
2. 文档区分：P5.2 统计摘要已实现；P5.3a 确定性交叉验证已实现；P5.3b 实验前端未实现；BEST/FINAL/LAST 不可验证而非猜测。
3. 实际报告 P5.3a 定向、P5.2/P5.1/P4.3/P4.1 回归、Docker 全量、前端和构建；不得用历史结果冒充。
4. 验证 009 current/head/check、路由/表数、三容器/健康、health/login 200、无 token comparisons 401；不新增迁移。
5. 测试库残留 0；开发库七表计数与开始一致，不得因验证新增 metrics/files/results。
6. 执行 Python 编译、git diff --check、高熵 secret 候选、生产 Web Storage/v-html、敏感日志、Markdown 路径/锚点检查；禁改目录和 HEAD 不变。两个 码道提示词执行期间 hash 必须不变。

最终逐项报告工作流、匹配规范、checkpoint 诚实降级、容差、Schema、API、用户隔离、幂等并发、事务失败、离线保证、全部测试、迁移/路由/表、HTTP、数据库残留、secret/Markdown 和明确未实现项。

不要 git commit，不要修改 码道提示词，不要读取或使用 API Key，不要真实调用华为云，不要修改开发库，不要删除 volume，不要提前实现 P5.3b 前端、文件操作、报告或 P6～P8。
~~~~

## 22 — P5.3b 实验数据前端与完整任务交互

> 来源：码道独立审查并收口 P5.3a 后生成（2026-07-15）

~~~~text
# 码道下一阶段提示词：P5.3b 实验数据前端与完整任务交互

继续维护 `D:\shixi\PaperLens` 项目。

本轮定义为 P5.3b：在已验收的 P5.1 文件上传/可信结构、P5.2 确定性统计和 P5.3a 指标交叉验证后端基础上，实现论文级实验数据 Vue 页面，使登录用户能够上传和选择实验文件、发起/观察统计任务、查看统计摘要、选择成功指标任务并生成/查看交叉验证结果。本轮是前端闭环，不新增后端业务能力；不得实现文件删除/下载/原始行预览、column_analysis、报告导出、管理员系统或 P6～P8。

P5.3a 最终真实基线：P5.3a 定向 74、P5.2 72、P5.1 103、P4.3 MaaS/LLM/审阅 180、P4.1 指标 67，均 0 skipped；Docker 后端全量 673 passed、0 skipped；前端 10 files / 106 passed；生产构建 126 modules；Alembic 009 head 且 check 无差异；30 条 `/api/v1` method+path、17 张业务表；测试库 17 表残留总数 0；开发库为 2 users / 3 papers / 3 tasks / 14 review_results / 0 metrics / 0 experiment_files / 0 experiment_results；三容器运行且 PostgreSQL healthy；health/login 200、无 token comparisons 401；77 个本地 Markdown 链接、0 断链。当前 HEAD 为 `525828b42707f7d1ef5c8efe1f308ce4bdac5454`，本轮禁止新增提交。真实华为云 glm-5.2 最小烟测已成功，但本轮禁止任何真实云调用。

开始前完整阅读并以当前代码为准：AGENTS.md、README.md、docker-compose.yml、frontend/src/api/index.ts、router/index.ts、App.vue、views/PaperDetailView.vue、MetricAnalysisView.vue、对应 tests、backend 的 experiment_files/tasks/metrics API 与 experiment_file/task/metric Schema、ProjectDocs/systemDesign/01～08、specs_SDD/PaperLens/spec.md、tasks.md、design/05/09、Sprint、P5.3a bugfix report、docs/api-contract.md、PROGRESS.md、IMPLEMENTATION_STATUS.md。

## 一、工作流、基线和禁止事项

1. 严格按 AGENTS.md：先用 dev-process-framework 更新 systemDesign 01～06；用 page-mockup 将 07 的 P07 设计校准为本轮实际 UI；用 fullstack-testing 先更新 08；用 function-detail 更新 SDD；开发过程中用 sdd-workflow 新建或更新 `ProjectDocs/sprint/实验数据前端.md`。skill 不可用时记录原因并手工按同序完成。
2. 开始前记录 git status/HEAD、Docker、009 current/check、路由/表数、测试库残留、开发库七表只读计数和两个 码道提示词 SHA-256。现有未提交改动属于用户/码道，不得还原、覆盖或重新格式化无关文件。
3. 禁止 git add/commit/reset/checkout/restore/clean/rebase；禁止修改 `.git/`、`.arts/`、`.codeartsdoer/`、`.skills/`、AGENTS.md 和两个 码道提示词文件；不得删除 volume 或修改开发库业务数据。
4. 禁止读取、搜索、打印或复制 `.env`、API Key、JWT secret、Authorization、cookie 或完整环境；禁止 `docker compose config`、`docker inspect`、`env`、`set` 和可能展开 secret 的日志命令。
5. 禁止真实调用 MaaS 或运行 maas-smoke。前端不得出现模型、endpoint、API Key 配置，不得把 token 或业务响应写入 localStorage/sessionStorage，不得使用 `v-html`。
6. 本轮不新增迁移、表或后端路由；不实现文件删除/下载/原始行预览、拖取后台原始文件、column_analysis、报告导出、管理员系统、持久化任务队列、OCR、FAISS/pgvector 或 P6～P8。

## 二、API 客户端与严格类型

1. 在 `frontend/src/api/index.ts` 增加与后端当前 Schema 一致的 TypeScript 类型和函数：ExperimentFile 列表/详情/上传、ExperimentAnalysisTask、SummaryStats、ComparisonItem、ExperimentResult、POST comparisons。字段名、枚举、null 语义和 201/200 duplicate 必须与后端完全一致，不得自造兼容字段。
2. 复用现有 axios 实例、HttpOnly refresh cookie 与内存 access token；不创建第二套认证客户端，不手工读取 cookie，不把认证状态持久化到 Web Storage。
3. 上传使用 `multipart/form-data` 的 `file` 字段；列表只发送后端支持的 page/page_size；所有 paper_id/file_id/task_id 只来自受保护路由、服务端响应或当前选择，不允许用户输入任意资源 ID。
4. 统一识别 401 刷新流程和现有错误结构。404 result 仅表示“尚无统计结果”；409/413/415/422 必须显示固定、可理解的页面提示，不展示底层 response、堆栈、路径、哈希或服务端内部详情。

## 三、路由、入口与页面状态

1. 新增受保护路由 `/papers/:id/experiment`，name 固定 `paper-experiment`，组件 `ExperimentDataView.vue`。在已 PARSED 的论文详情页新增“实验数据”入口；不重构现有 review/metrics 路由和全局认证守卫。
2. 页面加载当前论文、实验文件列表和论文任务列表。只接受当前 route paper id 的响应；路由参数切换、文件切换、筛选切换和组件卸载后，旧请求不得覆盖新状态。
3. 明确区分 loading、空列表、加载失败、未分析、PENDING/RUNNING、FAILED、SUCCEEDED、无成功指标任务、已有 comparison 和 comparison 失败。每个可恢复错误提供重试入口，不允许无限 loading 或静默失败。
4. 文件列表按后端顺序展示文件名、CSV/XLSX/XLS、大小、行列数和创建时间。选择文件后加载详情并展示可信列结构（列名、dtype、nullable、null_count）；不显示完整 SHA-256、storage key、原始数据行或本机路径。

## 四、上传与统计任务交互

1. 上传控件只允许 `.csv,.xlsx,.xls`，前端提供 1～20MB 快速提示和重复点击锁，但服务端仍是最终校验者。上传成功或 duplicate 后刷新文件列表、选中返回文件并展示明确状态；失败后保留可重试能力，不缓存文件内容。
2. 对选中文件调用 POST analysis。201 新建和 200 duplicate/复用都进入同一任务状态机；按钮在请求期间锁定，双击不得创建两次前端请求。
3. 复用 GET task 轮询，固定单一计时器；PENDING/RUNNING 持续显示 progress，SUCCEEDED 停止轮询并刷新 result，FAILED 停止并显示安全错误。文件/路由切换、组件卸载和终态必须清理计时器；网络暂时失败显示可重试，不得后台无限高速重试。
4. 页面初次加载若 GET result 已有 200，直接显示结果；若为 404 则显示“尚未分析”。不要为了探测状态自动创建分析任务。

## 五、统计摘要与交叉验证 UI

1. 统计表按后端 columns 原顺序展示 name、dtype、count、null_count、mean/stddev/min/max/median。非数值列的 stats 为 null，统一显示 `—`；零、负数和小数必须如实显示，格式化不能把有限值变成 NaN/Infinity 或擅自改成百分比。
2. 指标任务选择器只包含当前论文、`METRIC_EXTRACTION`、`SUCCEEDED` 的任务，默认选最新一条；没有成功指标任务时显示前往现有指标页的链接，不调用 comparisons。
3. 只有统计 result 已存在且选择了成功指标任务，才允许 POST comparisons。201 与 duplicate 200 都刷新/使用返回 comparisons；请求锁防双击。已有 metric_comparisons 时直接展示，并从 comparison 的 metric_task_id 确认来源；不得让用户误以为可覆盖为另一任务。
4. comparison 表固定展示 metric_name、checkpoint_type、paper_value、column_name、statistic、experiment_value、diff、absolute_diff、relative_diff、allowed_diff、status/reason。MATCH 绿色、MISMATCH 红色、UNVERIFIABLE 中性/黄色；null 显示 `—`。
5. reason 固定映射 `AMBIGUOUS_PAPER_METRIC`、`NO_EXPERIMENT_COLUMN`、`AMBIGUOUS_EXPERIMENT_COLUMN`、`UNSUPPORTED_CHECKPOINT`、`EMPTY_NORMALIZED_NAME` 为中文说明；不得把 UNVERIFIABLE 渲染成失败或伪造 MATCH/MISMATCH。`diff` 明确标注为“实验值 - 论文值”。
6. 页面使用语义化 table、label、button、aria-live/status；键盘可操作，颜色不是唯一状态信号。沿用现有页面视觉，不引入新 UI 框架或大依赖。

## 六、前端测试

1. 先更新测试设计再写测试。新增 `ExperimentDataView.test.ts` 和 API/route 契约测试；不得联网、skip/xfail、删除旧断言或用空断言冒充覆盖。
2. 覆盖受保护路由与论文详情入口、类型/API URL/参数/FormData、初始 loading/空/错误/404、文件列表和可信结构、上传成功/duplicate/校验失败/双击锁。
3. 覆盖 analysis 201/200、PENDING→RUNNING→SUCCEEDED、FAILED、临时轮询错误重试、终态/切换/unmount 清理计时器、旧请求晚到不覆盖新文件或新 route。
4. 覆盖统计表数值/null/顺序；指标任务只筛 SUCCEEDED METRIC_EXTRACTION、默认最新、无任务入口；comparisons 201/200/409、已有结果来源锁定、三种状态和五种 reason、零值与 null 格式。
5. 断言不使用 localStorage/sessionStorage/v-html，不显示 storage key/hash/原始行/API Key/底层错误；现有认证、论文、审阅和指标前端测试全部保持通过。
6. 实际运行 `npm test -- --run` 和 `npm run build`，报告真实 test files/tests/modules。后端 P5.3a 定向不得少于 74，Docker 后端全量不得少于 673 且 0 skipped；测试继续强制 mock，不调用真实云。

## 七、文档与最终验收

1. 同步 systemDesign 01～08、SDD spec/tasks/design 05/09、独立 Sprint、README、docs/api-contract.md、architecture.md、security-design.md、PROGRESS.md、IMPLEMENTATION_STATUS.md。文档必须区分 P5.3a 后端已完成、P5.3b 前端本轮完成，以及仍未实现的文件操作/报告/管理员能力。
2. 实际验证 009 current/head/check、30 条路由、17 张表、三容器和 PostgreSQL healthy、health/login 200、无 token experiment API 401；本轮无迁移、无后端路由变化。
3. 测试结束 paperlens_test 17 表残留总数 0；开发库七表计数必须与开始时一致，不得因 UI/API 验收上传真实文件或创建任务。禁止用手工开发库点击冒充自动测试。
4. 执行 TypeScript/Vite、Python/后端回归、git diff --check、secret 候选、生产 Web Storage/v-html、敏感日志、Markdown 本地路径/锚点检查；禁改目录和 HEAD 不变。两个 码道提示词在码道执行期间哈希必须不变。
5. 最终逐项报告工作流、页面/API、上传、轮询与竞态、统计、比较、认证安全、前端与后端测试、迁移/路由/表、HTTP、数据库残留、静态扫描和明确未实现项。任何未执行项如实说明，不用历史结果冒充。

不要 git commit，不要修改 码道提示词，不要读取或使用 API Key，不要真实调用华为云，不要修改开发库业务数据，不要删除 volume，不要提前实现文件删除/下载/预览、报告、管理员系统或 P6～P8。
~~~~

## 23 — P6.1 Markdown 审稿报告后端闭环

> 来源：码道独立审查并收口 P5.3b 后生成（2026-07-15）

~~~~text
# 码道下一阶段提示词：P6.1 Markdown 审稿报告后端闭环

继续维护 `D:\shixi\PaperLens` 项目。

本轮定义为 P6.1：在已验收的论文解析、Evidence、结构化审阅、指标提取和 P5 实验分析闭环基础上，实现“选择确定性来源快照 → 生成安全 Markdown → ExportReport 原子状态机 → 状态查询 → 鉴权下载”的纯后端闭环。报告只汇总已持久化结构化结果，不调用 LLM/Embedding，不翻译模型原文。本轮只支持 MARKDOWN；不得实现 PDF/DOCX、报告前端、文件删除/行预览、管理员系统或 P8 部署能力。

P5.3b 最终真实基线：P5.3b 前端定向 2 files / 48 passed；前端全量 12 files / 154 passed；生产构建 129 modules；Docker 后端全量 673 passed、0 skipped；Alembic 009 head、30 条 `/api/v1` method+path、17 张业务表；三容器运行且 PostgreSQL healthy。当前 HEAD 为 `525828b42707f7d1ef5c8efe1f308ce4bdac5454`，工作区包含用户/码道已验收的 P5 未提交改动，本轮禁止创建提交或还原现有改动。真实华为云 glm-5.2 最小烟测曾成功，但本轮禁止任何真实云调用。

开始前完整阅读并以当前代码为准：AGENTS.md、README.md、docker-compose.yml、backend/paperlens/models/models.py、enums.py、api/papers.py、api/tasks.py、api/experiment_files.py、services/review/metric/experiment 相关实现、utils/storage.py、schemas、现有 Alembic 001～009 和测试模式；ProjectDocs/systemDesign/01～08、specs_SDD/PaperLens/spec.md、tasks.md、design/03/04/05/06/08/09；docs/product-requirements.md、api-contract.md、data-model.md、architecture.md、security-design.md、PROGRESS.md、IMPLEMENTATION_STATUS.md，以及 P5.3b bugfix report。

## 一、工作流、基线与禁止事项

1. 严格按 AGENTS.md：先用 dev-process-framework 更新 systemDesign 01～06；本轮无页面改动，在 07 明确记录“无 UI 影响”；用 fullstack-testing 先更新 08；用 function-detail 更新 SDD；用 sdd-workflow 新建 `ProjectDocs/sprint/Markdown审稿报告后端.md`。skill 不可用时如实记录并按相同顺序手工完成。
2. 开始前记录 git status/HEAD、Docker、009 current/head/check、路由/表数、测试库残留、开发库关键表只读计数、`docs/CODEARTS_NEXT_PROMPT.md` 与归档 SHA-256。现有改动均属于用户/码道，不得覆盖、还原或批量格式化无关文件。
3. 禁止 git add/commit/reset/checkout/restore/clean/rebase；禁止修改 `.git/`、`.arts/`、`.codeartsdoer/`、`.skills/`、AGENTS.md 和两个 码道提示词；不得删除 volume 或修改开发库业务数据。
4. 禁止读取、搜索、打印或复制 `.env`、API Key、JWT secret、Authorization、cookie 或完整环境；禁止 `docker compose config`、`docker inspect`、`env`、`set` 等可能展开 secret 的命令。
5. 禁止真实 MaaS/Embedding/外部网络。测试必须强制 mock，并让 LLM/Embedding 工厂一旦被调用就失败。
6. 不实现 PDF/DOCX 转换、报告 Vue 页面、报告列表 UI、文件删除/下载/原始行预览、column_analysis、管理员 API/后台/审计、Celery/Redis、OBS 改造、OCR、FAISS/pgvector 或 P8。不要修改 P5 已验收行为。

## 二、P6.1 来源选择与 Markdown 契约

1. POST 只接受当前登录用户自己的 PARSED 论文。必须存在至少一个 `SUCCEEDED REVIEW` 任务且该任务至少有一条合法 ReviewResult，否则固定 409 `REVIEW_NOT_READY`，不创建 ExportReport。
2. 审阅来源固定选 `completed_at NULLS LAST/created_at/id` 最新的成功 REVIEW 任务，只汇总该 task 的 ReviewResult，按固定维度顺序再按 id 排序；Finding 按 sequence/id 排序，Evidence 引用按 id 稳定排序。不得混合多个历史审阅任务。
3. `include_metrics=true` 时只选择最新成功 METRIC_EXTRACTION 任务，并复核 task/record/source 的 paper/user 关系；无成功任务或零记录时生成明确“暂无指标数据”，不猜测或回退到其他任务。
4. `include_experiment_analysis=true` 时汇总该用户/论文所有合法 SUCCEEDED ExperimentResult，按 ExperimentFile created_at/id 稳定排序；每个结果复核 file/result/analysis task/paper/user 关系。无结果时生成明确“暂无实验分析数据”。已有 comparisons 原样汇总，不重新计算、不覆盖。
5. `language` 仅允许 `zh|en`，只切换模板标题、表头、固定状态/原因标签；论文标题、审阅 summary/finding、模型/数据集/指标名和文件名保持原文，不调用模型翻译。
6. Markdown 固定包含：报告标题与生成信息、论文信息、逐维度评分/摘要/结论、按类型分组的 findings 与 Evidence 页码/短引用；可选指标表；可选实验文件统计摘要与交叉验证表。缺少可选数据要诚实显示空状态。
7. 所有数据库文本先规范换行并做 Markdown/HTML 安全转义；表格单元格转义 `|` 和换行，禁止原始 HTML、脚本、data/javascript URL 或未转义标题破坏结构。不得把 storage_key、hash、内部路径、token、原始异常、MetricRecord.raw_text、整页正文或实验原始行写入报告。
8. 输出必须确定性：同一来源快照与选项生成逐字节相同的 UTF-8（无 BOM、LF 换行、末尾单个换行）内容和 SHA-256。限制输出大小，使用配置的安全上限；超限固定失败，不静默截断审阅结论。

## 三、ExportReport 模型、迁移与状态机

1. 审查现有 ExportReport。通过 010 迁移补足 P6.1 必需的 `language`、两个 include 选项和严格 `source_snapshot`；为 report_type、状态/字段关系、file_size/content_hash 增加数据库约束。迁移必须兼容空表和可能的历史行，upgrade/downgrade 不得静默丢失非空报告数据。
2. `source_snapshot` 只保存审计所需 id 与版本信息：review_task_id、可选 metric_task_id、按顺序的 experiment_result/file/task id；不得保存正文、Finding 内容、storage_key 或 secret。API 不公开 source_snapshot、content_hash、storage_key。
3. 在写入前计算确定性 Markdown bytes/content_hash。相同 user/paper/report_type/language/include 选项/来源内容的 PENDING/GENERATING/READY 请求必须数据库级收口为一条：首个 201，复用 200 `duplicate=true`；FAILED 不永久阻止相同来源重试。
4. 并发不能依赖进程锁。使用约束/索引与 IntegrityError 回查；同源两线程最多一行和一个对象。不同来源快照可各自创建，不互相覆盖。
5. 状态固定 `PENDING → GENERATING → READY` 或 `FAILED`。后台任务原子认领；临时文件只在受控临时目录创建，storage key 只由服务端随机 report id 组成，绝不拼接用户文件名或标题。
6. 写入存储后重新读取并验证 size/SHA-256，再原子提交 READY、file_size、completed_at。flush/commit/storage 失败必须 rollback/清理未归属对象；commit 结果未知用新 Session 回查，已 READY 时不得删除已提交对象。失败只保存固定安全 error_message。
7. 如继续使用 FastAPI BackgroundTasks，文档必须明确它不是持久化队列，进程重启恢复后置到 P8；不得伪报生产级可靠性。

## 四、API、Schema 与下载安全

1. 新增 `POST /api/v1/papers/{paper_id}/exports`。请求 extra=forbid：`report_type` 本轮只允许 MARKDOWN，`language=zh|en`，两个 include 布尔默认 true。返回固定 `id/paper_id/report_type/language/include_metrics/include_experiment_analysis/status/file_size/error_message/created_at/completed_at/duplicate`；不返回内部字段。
2. 新增 `GET /api/v1/exports/{export_id}`，仅所有者可见，USER/ADMIN 访问他人统一 404。PENDING/GENERATING/READY/FAILED 使用同一严格公开 Schema，error_message 只能是固定安全集合。
3. 新增 `GET /api/v1/exports/{export_id}/download`。仅 READY 且完整性复核成功可下载；未就绪固定 409，缺失/损坏对象固定安全失败且不得返回本机路径。响应为 attachment、`text/markdown; charset=utf-8`、`X-Content-Type-Options: nosniff`，下载名经安全规范化并提供合理 UTF-8 兼容策略。
4. 下载必须通过现有 StorageBackend/read_path，不绕过抽象直接拼接上传根目录；在发送前复核数据库 file_size/content_hash。不得提供任意 Range/路径参数或把 storage_key 暴露为 URL。
5. 全部 UUID 路径保持严格 UUID4 和现有统一错误结构。既有认证、论文、审阅、指标、实验 API 行为不变。预计公开路由 30→33，以实际收集结果为准。

## 五、离线测试

1. 先更新 08 测试设计再写测试。不得联网、skip/xfail、删除旧断言、用 SQLite 代替需要锁/约束的 PostgreSQL 测试，或 mock 掉目标报告生成器。
2. 单元覆盖 zh/en 模板、稳定排序、换行/表格/Markdown/HTML 转义、Unicode、零/负/小数/null、五种 comparison reason、空可选章节、确定性 bytes/hash、输出上限和禁止字段。
3. 来源图覆盖：无 REVIEW、多个历史 review 只取最新、review/result/finding/evidence 篡改；metrics 最新任务与 source 篡改；多个实验结果稳定排序及 file/task/user/paper 篡改。关系异常必须固定失败，不能跨用户汇总。
4. API/PostgreSQL 覆盖 401、UUID 422、他人 USER/ADMIN 404、非 PARSED/无 review 409、PDF/DOCX/extra 字段 422、首次 201、同源 200、状态查询、未就绪 409、READY 下载 headers/body、FAILED 安全错误、对象缺失/损坏。
5. 用真实两线程覆盖同源请求；注入 render、临时文件、storage save/read/delete、flush、commit 前失败和 commit 后抛错，验证一行一对象、状态原子性、补偿和 commit unknown 回查。
6. 断言报告/API/日志不含 storage_key、content_hash、本机路径、SQL/Traceback、API Key/token/Authorization、raw_text、整页正文或实验原始行；monkeypatch LLM/Embedding 工厂为一调用即失败，生成仍通过。
7. 实际运行 P6.1 定向、P5.3a 74、P5.2 72、P5.1 103、P4.3 180、P4.1 67 和 Docker 后端全量；不得少于现有 673 且 0 skipped。前端 12 files / 154 与构建 129 modules 必须继续通过。

## 六、文档与最终验收

1. 同步 systemDesign 01～08、SDD spec/tasks/design 06/08/09、独立 Sprint、README、docs/api-contract.md、data-model.md、architecture.md、security-design.md、PROGRESS.md、IMPLEMENTATION_STATUS.md。07 只记录本轮无页面变化；P08 报告页面仍为规划。
2. 文档明确 P6.1 只完成 Markdown 后端；PDF/DOCX 与报告前端留 P6.2；管理员系统留 P7；BackgroundTasks 重启恢复留 P8。
3. 实际验证 010 upgrade/head/check 与 `009→010→009→010`；如果 downgrade 会因已有报告数据而无损中止，必须单独测试。报告真实路由和业务表数。
4. 测试结束 paperlens_test 全部业务表残留 0；开发库关键表计数与开始一致，不得用开发库手工生成报告冒充验收。三容器/PostgreSQL healthy、health/login 200、无 token exports 401。
5. 执行 Python 编译、前端 TypeScript/Vite、git diff --check、高熵 secret 候选、Web Storage/v-html、敏感日志和 Markdown 本地路径/锚点检查；禁改目录与 HEAD 不变。两个 码道提示词在码道执行期间 SHA-256 必须不变。
6. 最终逐项报告来源选择、模板/转义、模型/迁移、幂等并发、状态机与事务恢复、API/下载安全、全部测试、路由/表、HTTP、数据库残留、静态扫描和未实现项。未执行项必须如实说明，不得用历史结果冒充。

不要 git commit，不要修改 码道提示词，不要读取或使用 API Key，不要真实调用华为云，不要修改开发库业务数据，不要删除 volume，不要提前实现 PDF/DOCX、报告前端、管理员系统或 P8。
~~~~

## 24 — P6.2 PDF/DOCX 报告与用户端导出闭环

~~~~markdown
# 码道下一阶段提示词：P6.2 PDF/DOCX 报告与用户端导出闭环

继续维护 `D:\shixi\PaperLens` 项目。

本轮固定为 P6.2，且必须在一个轮次内完成：在已验收的 P6.1 Markdown 来源快照、确定性 bytes、ExportReport 原子状态机和安全下载基础上，增加确定性 PDF/DOCX 生成、当前论文的报告历史分页 API，以及受保护的 P08 报告导出 Vue 页面。不得把 PDF、DOCX、列表 API 或前端拆成额外返工轮次。不得实现管理员系统、持久化任务队列或 P8 部署能力。

P6.1 码道最终真实基线：Docker 后端全量 `771 passed`、0 skipped/failed；P6.1 生成单元 72、PostgreSQL API/来源/并发/补偿 25、迁移 1；前端 12 files / 154 passed，生产构建 129 modules；Alembic `011_export_report_p61_integrity` head 且 check 无差异；33 条 `/api/v1` method+path、18 张业务表；三容器运行且 PostgreSQL healthy；开发库只读计数 `2u/4p/4t/21rr/0m/0ef/0er/0export`，paperlens_test 全表残留 0。当前 HEAD 仍为 `525828b42707f7d1ef5c8efe1f308ce4bdac5454`，工作区包含用户、码道已验收的 P5/P6.1 未提交改动，禁止创建提交、覆盖或还原。

开始前完整阅读并以当前代码为准：AGENTS.md、P6.1 新增/修改代码、010/011 迁移、P6.1 单元/API/迁移测试、P6.1 Sprint 与 bugfix report；ProjectDocs/systemDesign/01～08、specs_SDD/PaperLens/spec.md、tasks.md、design/06/07/08/09/10；docs/product-requirements.md、api-contract.md、data-model.md、architecture.md、security-design.md、PROGRESS.md、IMPLEMENTATION_STATUS.md；前端现有 api/router/PaperDetailView、ReviewResultView、MetricAnalysisView、ExperimentDataView 及其竞态隔离测试。

## 一、工作流、基线与禁止事项

1. 严格按 AGENTS.md：先用 dev-process-framework 更新 systemDesign 01～06；用 page-mockup 更新 07 的 P08 最终页面；用 fullstack-testing 先更新 08；用 function-detail 更新 SDD spec/tasks/design 06/07/08/09/10；用 sdd-workflow 新建 `ProjectDocs/sprint/PDF-DOCX报告与导出前端.md`。skill 不可用时如实记录并按同一顺序手工完成。
2. 开始前记录 git status/HEAD、Docker、011 current/head/check、路由/表数、测试库残留、开发库关键表只读计数，以及两个 码道提示词 SHA-256。现有改动均属于用户/码道，不得覆盖、还原或批量格式化无关文件。
3. 禁止 git add/commit/reset/checkout/restore/clean/rebase；禁止修改 `.git/`、`.arts/`、`.codeartsdoer/`、`.skills/`、AGENTS.md 和两个 码道提示词；不得删除 volume 或修改开发库业务数据。
4. 禁止读取、搜索、打印或复制 `.env`、API Key、JWT secret、Authorization、cookie 或完整环境；禁止 `docker compose config`、`docker inspect`、`env`、`set` 等可能展开 secret 的命令。
5. 禁止真实 MaaS/Embedding/外部网络。测试必须强制 mock，并让 LLM/Embedding 工厂一旦被调用就失败。
6. 不实现报告删除、批量导出、邮件分享、模板自定义、管理员 API/后台/审计、Celery/Redis、BackgroundTasks 重启恢复、OBS 改造、OCR、FAISS/pgvector、实验原始行/column_analysis 或 P8。不得改变 P5 与 P6.1 已验收语义。

## 二、共享报告文档与确定性 PDF/DOCX

1. 保留 P6.1 的来源选择、完整来源图复核、Evidence 页码/短引用、安全转义、创建前渲染、source_hash/content_hash、同源并发和存储补偿契约。PDF/DOCX 必须使用同一个可信结构化报告文档或 P6.1 的确定性输出作为来源，禁止重新查询或重新解释数据库内容。
2. 请求 `report_type` 扩展为严格 `MARKDOWN|PDF|DOCX`。三种格式在相同 user/paper/language/include/source 下各自拥有独立 ExportReport；同格式同源同 bytes 幂等 200，不同来源 201，FAILED 可重试。
3. PDF/DOCX bytes 必须在插入 PENDING 前完成生成并计算 SHA-256；后台任务只保存创建时 bytes，不得在后台再次转换。超过 max_report_size_bytes 固定 413 且不建行。
4. 转换必须是纯 Python、离线且无 shell。可以在 requirements.txt 固定加入兼容 Python 3.13 的 `reportlab` 与 `python-docx`，禁止调用 pandoc、LibreOffice、浏览器打印、远端字体或系统命令。新增依赖必须锁定版本并记录许可证/用途。
5. PDF 必须具备 `%PDF-` 签名、可选择/提取的中英文文本、稳定分页、页码、标题和表格；不得包含 JavaScript、附件、表单、外部资源或可执行动作。使用内置或仓库内合法字体，禁止下载运行时字体；必须用 PyMuPDF 真实解析验证文本与页数。
6. DOCX 必须是合法 OPC ZIP，可由 python-docx 重开；保留标题层级、段落、列表和表格，不包含宏、OLE、外部 relationship、远程图片或自定义 XML。任何 ZIP entry 名必须固定且无路径穿越。
7. 输出必须逐字节确定性。PDF 固定 creator/producer/creation/modification 信息和文档 id，不读取当前时钟；DOCX 固定 core properties，清除易变 rsid/修订信息，并按 entry 名排序、固定 ZIP timestamp/权限/压缩参数重新打包。同一来源和选项即使跨秒、跨 Session 生成也必须 bytes/hash 相同。
8. 论文标题、summary/finding、模型/数据集/指标名和文件名保持原文，不调用模型翻译。长文本、长单词、Unicode、空可选章节、表格跨页必须布局可读，不允许静默丢段、截断审阅结论或生成空白页风暴。

## 三、012 迁移、模型与状态机

1. 新增 `012_export_report_pdf_docx.py`，不得改写已应用 011 的 revision id。调整 P6.1 source 行的 report_type CHECK，使 source_snapshot 非空的 MARKDOWN/PDF/DOCX 均合法；保留历史 source_snapshot=null 骨架行兼容。
2. 不新增业务表。优先不新增列；若转换确有必要，必须先证明无法由 report_type/content_hash/source_hash 表达，并提供兼容迁移。最终 Alembic head 应为 012、业务表仍 18 张。
3. 既有 `uq_active_export_source` 已包含 report_type，继续保证三格式分别幂等。不得退化为只按用户/论文/选项永久锁死，也不得删除 READY 文件来覆盖旧来源。
4. 012 upgrade 必须兼容空表、历史 PDF/DOCX 骨架行和已有 P6.1 MARKDOWN 行；downgrade 遇到 source_snapshot 非空的 PDF/DOCX 行必须在修改 schema 前无损中止，不能 DELETE/UPDATE 报告或对象。
5. PENDING→GENERATING 的条件 UPDATE 单认领、storage 回读逐字节/size/hash 校验、READY commit unknown 回查、未归属对象清理与固定 FAILED 文案必须覆盖全部三种格式。不得复制出三套互相漂移的状态机。

## 四、API、报告历史与下载契约

1. 扩展现有 POST，仍为 extra=forbid。公开 ExportReportResponse 保持同一严格字段集合且不返回 source_snapshot/source_hash/content_hash/storage_key。
2. 新增 `GET /api/v1/papers/{paper_id}/exports?page=1&page_size=20`。仅论文所有者可见，USER/ADMIN 访问他人统一 404；严格分页 1～100，按 created_at DESC/id DESC；返回固定 `items/total/page/page_size`，item 复用公开 ExportReport 字段且 duplicate 固定 false。
3. 状态 GET 行为不变。FAILED 只返回固定安全错误；历史骨架异常数据不能导致 500 或泄露内部字段。
4. 下载按 report_type 返回：Markdown `text/markdown; charset=utf-8`、PDF `application/pdf`、DOCX `application/vnd.openxmlformats-officedocument.wordprocessingml.document`。安全文件名只由 report id 和服务端固定扩展组成；保留 attachment、nosniff、private/no-store 和发送前 size/hash 复核。
5. 不增加任意路径、文件名、模板、URL、Range 或转换参数。预计公开路由 33→34，以实际收集结果为准。

## 五、P08 用户端导出页面

1. 新增受认证路由 `/papers/:id/export` 与 `ReportExportView.vue`，在 PaperDetailView 增加“导出报告”入口；复用现有论文元信息和视觉语言，不重构无关页面或引入新 UI 库。
2. 页面配置包含格式 MARKDOWN/PDF/DOCX、语言 zh/en、include_metrics、include_experiment_analysis；仅 PARSED 论文允许提交。没有成功审阅时展示可行动提示并链接审阅页，不在前端伪造结果。
3. 页面从新的分页 API恢复报告历史，显示格式、状态、文件大小、创建/完成时间与操作。PENDING/GENERATING 只显示“等待生成/生成中”，不得伪造百分比；FAILED 显示固定安全文案并允许用户重新提交相同配置。
4. POST 201/200 均 upsert 到列表；只轮询当前页中的 PENDING/GENERATING id，默认 3 秒。使用 paper generation、request generation 和 export id 拒绝路由切换、翻页、重复提交或组件卸载后的陈旧响应；终态立即停止对应轮询，卸载清理 timer。
5. 下载必须走现有认证 Axios，使用 blob/arraybuffer 和服务端 Content-Disposition 或安全 fallback 文件名；创建对象 URL 后触发下载并在 finally revoke。禁止把 access token 放进查询串、window.open URL、local/session storage 或 DOM。
6. 创建、列表、状态和下载错误映射为固定、可行动的中文文案；不得展示原始后端 message、SQL、Traceback、路径或响应正文。按钮具备 loading/disabled，重复点击不得创建额外请求。
7. 更新前端 API TypeScript 严格联合类型和分页响应，所有响应再次校验 paper/export 上下文。不得使用 `any`、`v-html`、Web Storage 或长期缓存报告 blob。

## 六、离线测试

1. 先更新 08 测试设计再写测试。不得联网、skip/xfail、删除旧断言、用 SQLite 代替 PostgreSQL 约束测试，或 mock 掉目标转换器/报告状态机。
2. 转换单元覆盖 zh/en、Unicode、长文本/分页、Evidence、指标/实验表格、空章节；PDF 用 PyMuPDF 解析真实文本/页数，DOCX 用 zipfile/XML 与 python-docx 重开验证结构。
3. 确定性测试必须跨秒或注入不同时钟重复生成，分别断言 PDF/DOCX bytes 和 SHA-256 完全相同；扫描 PDF metadata、DOCX core properties/ZIP timestamps/rsid，禁止当前时间、绝对路径、secret、外部关系、宏、脚本或原始 HTML。
4. PostgreSQL/API 覆盖三格式 201/200、新来源、FAILED 重试、真实两线程同格式只一行一对象、不同格式各一行；012 历史行 upgrade、空库往返、非空 PDF/DOCX downgrade 无损中止。
5. 下载覆盖三种 MIME、扩展名、headers、body/hash、未就绪、缺失和损坏；列表覆盖分页/排序/空列表、严格参数、USER/ADMIN 跨用户 404、内部字段不公开。
6. 注入 PDF/DOCX render、临时文件、storage save/read/delete、flush、commit 前失败和 commit 后抛错，验证固定 FAILED、无未归属对象、commit unknown READY 不误删。
7. 前端组件覆盖三格式配置、严格请求、201/200 upsert、历史分页、轮询终止、路由/翻页/重复请求竞态、FAILED 重试、blob 下载与 revoke、401/404/409/413 固定文案、无 v-html/Web Storage/token URL。
8. 实际运行 P6.2 定向、P6.1 72+25+1、P5.3a 74、P5.2 72、P5.1 103、P4.3 180、P4.1 67 和 Docker 后端全量；不得少于当前 771 且 0 skipped。前端全量不得少于 12 files / 154，生产构建不得少于 129 modules。

## 七、文档与最终验收

1. 同步 systemDesign 01～08、SDD spec/tasks/design 06/07/08/09/10、独立 Sprint、README、docs/api-contract.md、data-model.md、architecture.md、security-design.md、PROGRESS.md、IMPLEMENTATION_STATUS.md。页面文档必须与最终组件一致，不保留伪进度百分比。
2. 文档明确 P6 完成 Markdown/PDF/DOCX 与用户端导出闭环；报告删除/分享不在范围；完整管理员系统下一阶段 P7；BackgroundTasks 重启恢复仍留 P8。
3. 实际验证 012 upgrade/head/check、空库 `011→012→011→012`、历史行兼容和非空 PDF/DOCX downgrade 无损中止；报告真实路由/表数。
4. 测试结束 paperlens_test 全部业务表残留 0；开发库关键表计数与开始一致。三容器/PostgreSQL healthy、backend/frontend HTTP 200、无 token 创建/列表/下载 401。
5. 执行 Python 编译、前端 TypeScript/Vite、git diff --check、高熵 secret 候选、PDF/DOCX 外部关系/宏/脚本、Web Storage/v-html、敏感日志、绝对路径和锚点检查；禁改目录与 HEAD 不变。两个 码道提示词在码道执行期间 SHA-256 必须不变。
6. 最终逐项报告转换器与确定性、012/模型、三格式幂等状态机、列表/下载 API、P08 竞态与下载安全、全部测试、路由/表、HTTP、数据库残留、静态扫描和明确未实现项。未执行项必须如实说明，不得用历史结果冒充。

不要 git commit，不要修改 码道提示词，不要读取或使用 API Key，不要真实调用华为云，不要修改开发库业务数据，不要删除 volume，不要拆分 P6.2，也不要提前实现管理员系统或 P8。
~~~~

---

## 25 — P7.1 管理员 API 与不可变审计后端

> 来源：码道独立审查并收口 P6.2 后生成（2026-07-15）

~~~~text
# 码道下一阶段提示词：P7.1 管理员 API 与不可变审计后端

## 任务目标

本轮固定为 P7.1，且必须在一个码道轮次内完成：在 P3.5 已验收的注册登录、AuthSession、USER/ADMIN RBAC 与 P6 已完成的全部用户功能基础上，实现管理员专用的仪表盘、用户管理、论文/任务/报告只读管理列表，以及用户角色/账号状态变更和不可变审计日志。不得把迁移、管理员权限、用户变更、审计或只读管理 API 拆成额外返工轮次。

本轮是纯后端闭环。P7.2 管理后台 Vue 页面、P7.3 管理员端到端权限验收仍按既定轮次执行；不得提前实现或增加新轮次。

## 一、开始前边界与固定基线

1. 先完整阅读根目录 `AGENTS.md`，并严格按 `dev-process-framework → page-mockup → fullstack-testing → function-detail → sdd-workflow` 执行；如技能脚本不可用，如实记录并按同一顺序手工完成。P7.1 不改页面，但仍需由 page-mockup 明确记录“P7.2 才新增管理员页面”。
2. 开始前记录 git status/HEAD、Docker、012 current/head/check、路由/表数、测试库残留、开发库关键表只读计数，以及两个 码道提示词 SHA-256。现有改动均属于用户/码道，不得覆盖、还原或批量格式化无关文件。
3. 当前验收基线：HEAD `525828b42707f7d1ef5c8efe1f308ce4bdac5454`；Alembic 012；34 条 `/api/v1` method+path；17 张 ORM 应用表、含 alembic_version 共 18 张物理表；Docker 后端 830 passed/0 skipped；前端 13 files/173 passed；构建 132 modules；开发库只读计数 `2/4/4/21/0/0/0/0`；测试库零残留；三个容器运行且 PostgreSQL healthy。变化必须按实际结果报告，不得机械写预估数。
4. 禁止 git add/commit/reset/checkout/restore/clean/rebase；禁止修改 `.git/`、`.arts/`、`.codeartsdoer/`、`.skills/`、AGENTS.md 和两个 码道提示词；禁止删除 volume 或修改既有开发库业务数据。
5. 禁止读取、搜索、打印或复制 `.env`、API Key、JWT secret、Authorization、cookie、密码/refresh/reset token 或完整环境；禁止 `docker compose config`、`docker inspect`、`env`、`set` 等可能展开 secret 的命令。
6. 禁止真实 MaaS/Embedding/外部网络。测试必须强制 mock，并让 LLM/Embedding 工厂一旦被调用就失败。
7. 不实现管理后台 Vue 页面、管理员冒充用户、密码查看/重置、默认管理员、邮件、MFA、论文/报告删除、任务取消、批量操作、报告分享、任意 SQL/排序字段、Celery/Redis、OBS、FAISS/pgvector 或 P8。ADMIN 在普通业务 API 中仍不得绕过资源所有权；跨用户访问只能走本轮显式 `/admin` API。

## 二、先更新设计与 SDD

1. 在编码前更新 `ProjectDocs/systemDesign/01～08`：确定管理员用例、显式管理边界、013 数据模型、API、实施计划、需求规格、P7.1 无页面影响和测试矩阵。
2. 更新 `ProjectDocs/specs_SDD/PaperLens/spec.md`、`tasks.md` 与相关 design 文档；新建 `ProjectDocs/sprint/管理员API与审计后端.md`，状态先置进行中，验收后再完成。
3. 设计必须明确：P7.1 仅提供管理员后端；P7.2 使用这些 API 构建管理页面；P7.3 做权限/E2E 收口。不得把已有 P3.5 认证错误标为未实现。

## 三、013 迁移与不可变审计模型

1. 新增 `013_admin_audit_log.py`，不得改写 001～012 revision id。新增 `admin_audit_logs` 一张表，不修改或回填既有业务行；最终应为 18 张 ORM 应用表、含 alembic_version 共 19 张物理表。
2. 最小字段：UUID id；`actor_user_id` String(128) FK users.id RESTRICT；固定 action；固定 resource_type；`resource_id` String(128)；长度 8～500 的 reason；非空、严格小对象 `before_state`/`after_state` JSONB；created_at。不得保存密码哈希、token/hash、cookie、论文正文、storage_key、source_snapshot/content_hash、原始异常、请求 header/IP/user-agent 或任意环境值。
3. action 本轮只允许 `USER_ROLE_CHANGED`、`USER_STATUS_CHANGED`；resource_type 本轮只允许 `USER`。before/after 只能是 `{"role": ..., "status": ...}`，不得保存 email/display_name 等可变 PII 快照。
4. 建立 actor、resource、action、created_at DESC/id DESC 所需索引和 CHECK。ORM 与迁移必须一致。
5. 审计表必须 append-only：应用无 UPDATE/DELETE 路径；数据库以 PostgreSQL trigger 拒绝 UPDATE/DELETE，TRUNCATE 仅测试清理使用。变更用户、撤销 session/reset token 和插入审计必须在同一事务内，任一步失败全部回滚。
6. 013 upgrade 兼容空库和现有 012 数据，不得 UPDATE/DELETE 用户或业务表。downgrade 若审计表非空，必须在修改 schema 前无损中止；空表允许 `012→013→012→013` 往返。不得为通过 downgrade 测试删除审计记录。

## 四、管理员认证与用户变更规则

1. 复用现有 `require_admin` 和真实 AuthContext。未认证统一 401；已认证 USER 统一 403；DISABLED、已撤销 session、refresh replay 等继续由 P3.5 拒绝，不能只相信 JWT role claim。
2. 新增 `PATCH /api/v1/admin/users/{user_id}`，请求 extra=forbid，字段为可选 `role: USER|ADMIN`、可选 `status: ACTIVE|DISABLED`、必填 reason 8～500；role/status 至少一个出现。空变更或值相同返回 200、`changed=false`，不写审计。
3. 用户变更必须数据库串行化：以确定顺序 `FOR UPDATE` 锁定当前 ACTIVE ADMIN 集合与目标用户，处理并发管理员操作。任何提交结果未知都用新 Session 回查用户状态和对应 audit id，不能重复审计或误报失败。
4. 禁止管理员把自己降为 USER 或设为 DISABLED；任何操作后必须至少保留一个 ACTIVE ADMIN。两个管理员并发互相降级/禁用时最多一个成功，另一个固定 409，绝不能出现零 ACTIVE ADMIN。
5. 目标不存在固定 404；不泄露是否存在于非管理员接口。角色/状态非法、extra、reason 过短/过长/控制字符为 422；最后管理员/自操作冲突为固定安全 409。
6. 实际 role 或 status 变化后，在同一事务中撤销目标用户全部未撤销 AuthSession，固定 revoke_reason，不输出 sid/token_hash；使旧 access/refresh 立即失败。设为 DISABLED 时同时使未使用且未过期的 PasswordResetToken 失效；重新启用不会恢复旧 session/token。
7. 同一次 PATCH 同时改变 role/status 只创建一条还是两条审计必须固定：要求每个实际变化字段各一条 audit，使用同一事务和同一 reason，排序由 created_at/id 确定。不得审计失败或 no-op 请求。
8. API 只能返回严格公开 UserAdminResponse 与本次 `changed/audit_ids`；不得返回 password_hash、session/token hash、reset token、内部 SQL/路径或底层异常。

## 五、8 条管理员 API

本轮新增以下 8 条 method+path，预期总数 34→42，以实际收集为准：

1. `GET /api/v1/admin/dashboard`：返回固定聚合计数。用户按 role/status，论文按 status，任务按 task_type/status，报告按 report_type/status；数字均为非负整数，不返回用户内容或最近原文。
2. `GET /api/v1/admin/users?page=1&page_size=20&role=&status=&q=`：q 只匹配 normalized email/display_name，长度 1～100；按 created_at DESC/id DESC。item 可含 id/email/display_name/role/status/failed_login_count/locked_until/created_at/updated_at、active_session_count、paper/task/export_count，不含任何 secret/hash。
3. `GET /api/v1/admin/users/{user_id}`：同一严格用户字段与资源计数；目标不存在 404。
4. `PATCH /api/v1/admin/users/{user_id}`：按第四节执行角色/状态变更、session/reset 失效与原子审计。
5. `GET /api/v1/admin/papers?page&page_size&status&user_id&q`：只读管理列表，固定字段 id/user_id/owner_email/title/filename/file_size/page_count/status/created_at/updated_at；FAILED 只映射固定公开错误，不返回 storage_key/file_hash/正文/表格/Evidence。
6. `GET /api/v1/admin/tasks?page&page_size&task_type&status&user_id&paper_id`：只读列表，固定字段 id/user_id/paper_id/task_type/status/progress/固定安全 error_message/created_at/started_at/completed_at；不返回模型输入输出、论文内容或 token usage。
7. `GET /api/v1/admin/exports?page&page_size&report_type&status&user_id&paper_id`：只读列表，复用安全公开字段并补 user_id；FAILED 固定文案；不返回 storage_key/source_snapshot/source_hash/content_hash。
8. `GET /api/v1/admin/audit-logs?page&page_size&actor_user_id&action&resource_id&created_from&created_to`：按 created_at DESC/id DESC，返回 actor 的当前 id/email、固定 action/resource、reason、严格 before/after、created_at；时间必须带时区且 from<=to。

所有列表统一严格 page>=1、1<=page_size<=100、固定 total/page/page_size/items；只接受白名单 filter，不接受任意 sort/order/field/include。不存在的关联不得导致 500；使用聚合/批量查询避免逐行 N+1。所有响应 schema `extra=forbid`。

## 六、事务、隐私与并发边界

1. 管理员列表是显式跨用户能力，但只暴露运维所需最小元数据。普通论文/任务/报告 API 的 USER/ADMIN 所有权行为必须保持原样，禁止把 `require_admin` 变成全局旁路。
2. role/status 变更、session/reset 失效、两条可能的 audit 插入必须单事务。flush/commit 前失败 rollback；commit 后抛错用 audit id + target state 回查。并发请求不得产生重复 audit、部分变更或漏撤销 session。
3. before/after 来自锁定后的数据库值，不接受客户端 JSON。reason 只保存到数据库和管理员响应，不写应用日志。日志仅允许固定阶段、actor id、target id、action 与异常类型，不记录 email/reason/header/token/内容。
4. Dashboard 和列表必须使用有限投影，不加载 deferred raw_text、structured_data、source_snapshot 或文件对象。任何计数/筛选不得调用 LLM、Embedding、StorageBackend 或网络。
5. 失败响应只使用固定公开 AppError code/message；数据库异常、constraint 名、SQL、Traceback、绝对路径和审计 reason 不得回显给普通用户或日志。

## 七、测试要求

1. 新增 013 migration、admin service、schemas、router 的单元与 PostgreSQL API 测试；更新 `_BUSINESS_TABLES`、默认 Alembic revision 和清理/零残留检查。
2. 覆盖 8 路由的 401、USER 403、ADMIN 200、UUID/路径/分页/筛选/时间/extra 422，以及响应禁止字段递归扫描。
3. 覆盖 dashboard 精确计数、users q/filter/pagination/stable order、paper/task/export 跨用户聚合、空列表和孤立/历史兼容行，不得用 vacuous `len>0` 冒充字段正确。
4. 覆盖用户 role/status 单变更、双变更、no-op、目标 404、自降级/自禁用、最后 ACTIVE ADMIN、DISABLED 旧 access/refresh/reset 立即失效、重新启用不恢复旧凭据。
5. 至少使用真实 PostgreSQL 两线程验证：两个管理员并发互相降级/禁用不能产生零 ACTIVE ADMIN；同目标并发请求只有串行一致结果；audit 数量、before/after、session 撤销与最终用户状态完全一致。
6. 注入 audit flush、user flush、session/reset update、commit 前失败和 commit 后抛错；验证原子 rollback 或 commit unknown 回查，不出现用户变了但无 audit、audit 有了但 session 未撤销、重复 audit。
7. 直接 SQL 尝试 UPDATE/DELETE audit 必须被 trigger 拒绝；API 不存在 audit mutation 路由。013 测试覆盖现有 012 数据不变、空库往返、非空 audit downgrade 无损中止。
8. 测试中 LLM/Embedding/Storage 工厂一旦被管理员路径调用就失败。不得读取真实 Key，不得向外网发请求。
9. 实际运行 P7.1 定向、P6.2 34+25+1、P6.1、P5、P4、P3.5 认证回归和 Docker 后端全量；不得少于当前 830 且 0 skipped。前端全量必须保持至少 13 files/173，构建至少 132 modules。

## 八、文档、运行验收与交付

1. 完成后同步 `ProjectDocs/systemDesign/01～08`、SDD spec/tasks/design、Sprint、`docs/IMPLEMENTATION_STATUS.md`、`docs/PROGRESS.md`、`docs/api-contract.md`、`docs/architecture.md`、`docs/data-model.md`、`docs/security-design.md` 和 README；不得把 P7.2 页面或 P7.3 E2E 写成已完成。
2. 文档明确 P7.1 只完成管理员后端；P7.2 下一轮实现管理后台仪表盘、用户与内容列表、角色/状态操作和审计查询；P7.3 做权限与危险操作确认/E2E。
3. 实际验证 013 current/head/check、空库往返、现有数据兼容、非空 audit downgrade 无损中止；报告真实路由、ORM/物理表数。
4. 只读核对开发库关键表计数，不创建管理员、不变更任何现有用户 role/status、不写审计；测试数据只进入 `paperlens_test`，结束必须 18 张应用表残留总数 0。
5. 执行 Python 编译、前端 TypeScript/Vite、git diff --check、secret/Web Storage/v-html/敏感日志/绝对路径扫描、Markdown 链接检查；禁改目录与 HEAD 不变。两个 码道提示词在码道执行期间 SHA-256 必须不变。
6. 最终逐项报告 013/审计不可变性、管理员认证、用户变更与凭据失效、8 API、并发/事务、全部测试、迁移、路由/表、HTTP、数据库残留和明确未实现项。未执行项必须如实说明，不得用历史结果冒充。

不要 git commit，不要修改 码道提示词，不要读取或使用 API Key，不要真实调用华为云，不要修改开发库业务数据，不要删除 volume，不要拆分 P7.1，也不要提前实现 P7.2/P7.3 或 P8。
~~~~

---

## 26 — P7.1 论文阅读学习工作台与证据化学习解释

> 来源：用户校正产品目标为“帮助我阅读论文学习”后，由码道重新整理产品方向与固定轮次并生成（2026-07-15）。本节取代第 25 节作为下一轮执行提示词；第 25 节仅保留历史，不应再交给码道。

~~~~text
# 码道下一阶段提示词：P7.1 论文阅读学习工作台与证据化学习解释

## 任务目标

本轮固定为 P7.1，且必须在一个码道轮次内完成：把 PaperLens 的产品主线从“辅助审稿”校正为“帮助个人用户阅读论文并学习”，在已验收的 PDF 解析、章节/页面、Evidence、认证隔离和 Huawei MaaS LLMClient 基础上，实现受保护的论文阅读工作台，以及针对当前章节、当前页面或单条 Evidence 的中文/英文总结、通俗解释和翻译闭环。

结构化审阅、指标提取、实验分析和三格式报告全部保留，分别作为“批判性阅读”“实验理解”和“学习成果导出”的既有高级能力；不得删除、改表重做或破坏 P2～P6。原 P7.1 管理员后端提示词已被本轮替代，但不增加总轮数：P7.2 仍用于论文内多轮问答，P7.3 用于高亮/书签/笔记/知识卡/论文库与学习进度，完整管理员后端+前端+不可变审计合并到既定 P8.1，P8.2～P8.4 继续用于全链路、可靠性性能和华为云部署安全收口。

## 一、开始前边界与固定基线

1. 先完整阅读根目录 `AGENTS.md` 和当前真实代码，再严格按 `dev-process-framework → page-mockup → fullstack-testing → function-detail → sdd-workflow` 执行。先核对 码道已写入的产品方向校正文档；如技能脚本不可用，如实记录并按相同顺序手工完成，不得跳过文档阶段直接编码。
2. 开始前记录 git status/HEAD、Docker、Alembic 012 current/head/check、路由/表数、测试库残留、开发库关键表只读计数，以及 `docs/CODEARTS_NEXT_PROMPT.md` 和 `docs/CODEARTS_PROMPT_ARCHIVE.md` 的 SHA-256。现有全部修改属于用户/码道，不得覆盖、还原或批量格式化无关文件。
3. 当前验收基线：HEAD `525828b42707f7d1ef5c8efe1f308ce4bdac5454`；Alembic 012；34 条 `/api/v1` method+path；17 张 ORM 应用表、含 alembic_version 共 18 张物理表；Docker 后端 830 passed/0 skipped；前端 13 files/173 passed；构建 132 modules；开发库只读计数 `2/4/4/21/0/0/0/0`（users/papers/tasks/reviews/metrics/files/results/exports）；测试库 17 张应用表残留总数 0；backend/frontend/postgres 运行且 PostgreSQL healthy。所有新结果必须按实际收集值报告，不得机械复制预估数字。
4. 禁止 git add/commit/reset/checkout/restore/clean/rebase；禁止修改 `.git/`、`.arts/`、`.codeartsdoer/`、`.skills/`、`AGENTS.md` 和两个 码道提示词文件；禁止删除 Docker volume、删除用户文件或修改既有开发库业务数据。
5. 禁止读取、搜索、打印、复制或推断 `.env`、API Key、JWT secret、Authorization、cookie、密码、refresh/reset token 或完整环境；禁止运行 `docker compose config`、`docker inspect`、`env`、`set` 等可能展开 secret 的命令。
6. 本轮禁止真实 MaaS、真实 Embedding 和任何外部网络。所有自动测试强制使用可控 Mock/注入客户端；不得因为本机已配置 huawei_maas 就产生付费调用。
7. 不实现自由文本提问、多轮会话、联网补充、笔记/高亮/书签/知识卡、论文库标签搜索、管理员 API/页面/审计、报告重做、文件删除、Celery/Redis、OBS、FAISS/pgvector、OCR 或 P8 能力；不得将上述内容拆成 P7.1 的额外返工轮次。

## 二、先同步设计、SDD 与 Sprint

1. 编码前复核并按实际方案更新 `ProjectDocs/systemDesign/01～08`：个人论文阅读学习助手定位、P7.1 架构、013 数据模型、3 个 API、固定轮次、FR-13、P09 页面和完整测试矩阵。
2. 更新 `ProjectDocs/specs_SDD/PaperLens/spec.md`、`tasks.md`、`design/design.md`、`design/07～10` 和 `design/13-论文阅读学习.md`。每个任务必须引用具体 FR、设计、API、数据表和页面章节。
3. 更新 `ProjectDocs/sprint/论文阅读学习工作台.md`：开始编码时置为进行中，只有本轮真实验收全部通过后才置为完成；未执行项不得打勾。
4. 更新 README、`docs/product-requirements.md`、architecture、api-contract、data-model、security-design、IMPLEMENTATION_STATUS 和 PROGRESS。历史 P2～P6 结果保留；规划中的 P7.2/P7.3/P8.1 不得写成已实现。

## 三、013 迁移与学习数据模型

1. 新增单一 Alembic revision `013_learning_explanations.py`，down_revision=012；禁止修改 001～012 revision id 或在旧迁移中塞新逻辑。
2. 新增 `learning_explanations`：
   - `id` UUID 主键；`user_id` String(128) FK users RESTRICT；`paper_id` UUID FK papers CASCADE。
   - `mode` 仅 `SUMMARY|EXPLAIN|TRANSLATE`；`scope_type` 仅 `SECTION|PAGE|EVIDENCE`；`output_language` 仅 `zh|en`。
   - nullable `section_id`、`page_number`、`evidence_id`，通过 CHECK 保证 scope 严格互斥：SECTION 只允许 section_id；PAGE 只允许 page_number 且 >=1；EVIDENCE 只允许 evidence_id。section/evidence 外键删除策略必须与论文级 CASCADE 一致且由迁移/ORM 同步定义。
   - `request_hash` 固定 64 位小写十六进制，由服务端 canonical scope + source hash + mode + language 生成，不从请求接收且不公开。
   - `status` 仅 `PENDING|RUNNING|SUCCEEDED|FAILED`；nullable `answer` Text、`key_points` JSONB、`terms` JSONB、`error_message` Text、`started_at`、`completed_at`，以及 UTC `created_at`。
   - CHECK 保证终态：PENDING 不声明结果/错误/完成时间；RUNNING 已有 started_at 且无结果/错误/完成时间；SUCCEEDED 有 started_at/completed_at、非空 answer、非空 JSON 数组 key_points/terms、无错误；FAILED 有 started_at/completed_at、固定非空 error_message、无 answer/key_points/terms。
   - 索引覆盖 user/paper、paper/created_at DESC/id DESC、status；部分唯一索引 `user_id + paper_id + request_hash` 只覆盖 PENDING/RUNNING/SUCCEEDED，使同请求活动/成功最多一行，FAILED 可重试。
3. 新增 `learning_citations`：`explanation_id` FK learning_explanations CASCADE、`evidence_id` FK evidences RESTRICT、`sequence` 正整数；复合主键 explanation_id+evidence_id，且 explanation_id+sequence 唯一。服务层必须验证 Citation 与 Explanation 属于同一 paper/user。
4. ORM、枚举、关系、约束名、索引名与迁移完全一致。不得把学习结果写进 ReviewResult/ReviewFinding，不得给 AnalysisTask 伪造 REVIEW 类型，也不得存 prompt、全文快照、模型原始响应、token usage、API Key、底层异常、storage_key 或任意 secret。
5. 013 upgrade 必须兼容当前 012 开发库并且不 UPDATE/DELETE/回填既有业务行。空学习表支持 `012→013→012→013`；任一学习表非空时 downgrade 必须在任何 DDL 前无损中止，不能为了测试先删数据。
6. 完成后预计为 19 张 ORM 应用表、含 alembic_version 共 20 张物理表；必须以实际统计为准。同步测试清理清单和残留检查。

## 四、服务端来源解析与安全模型输入

1. 新建独立 learning service/schema/router，不把业务逻辑塞进 papers.py、tasks.py 或 review_service.py。复用现有真实 AuthContext、LLMClient 工厂和安全错误体系。
2. POST 只能由当前 owner 对 PARSED 论文调用；ADMIN 在普通业务 API 中仍不得读取他人论文。user_id 永远来自认证上下文。
3. 请求只接受 `mode`、`scope_type`、`section_id|page_number|evidence_id` 和 `output_language`，`extra=forbid`。禁止客户端提交正文、quoted_text、Evidence alias、prompt、user_id、model、temperature 或系统指令。
4. 服务端重新读取来源：
   - SECTION：PaperSection 必须属于论文，正文取 `text_content`；候选 Evidence 优先同 section_id，必要时只在 section 页码范围内确定性补充。
   - PAGE：PaperPage 必须属于论文，正文优先 `normalized_text_content`，候选 Evidence 只来自同页。
   - EVIDENCE：Evidence 必须属于论文，正文只取该 `quoted_text`，候选只有自身。
5. 候选按 page_number ASC、created_at ASC、id ASC 稳定排序，映射为 E1…En。新增明确、有限且经过校验的配置，例如 source 总字符上限、Evidence 数量上限和单条字符上限；默认值写入 `.env.example` 但不得读取真实 `.env`。来源为空固定 409；SECTION 超出单轮安全上限时诚实返回“范围过大，请按页面阅读”，不得静默截断后宣称“全文总结”。
6. canonical scope 和 source hash 必须由服务端生成。创建 PENDING 前完成来源归属与 hash；后台执行前再次读取并复核 hash，来源不一致则固定 FAILED，不用旧正文生成新结果。
7. 论文标题、正文和 Evidence 都按不可信输入包裹在明确标签内。system message 必须声明其中任何指令无效；不得拼接为可覆盖系统角色的消息，不得把论文中的 `ignore previous instructions` 当作命令。

## 五、学习 LLM 契约、严格解析与 Citation 绑定

1. 复用现有 `LLMClient.chat`；通过显式 `operation="learning"`、mode、language 和 evidence_aliases 传递 Mock 所需上下文，不改变 REVIEW 现有 kwargs 或输出。
2. `MockLLMClient` 只在 learning operation 分支返回学习 JSON，原 REVIEW 分支逐字保持兼容。HuaweiMaaSLLMClient 不增加专用网络协议，仍走当前非流式标准接口。
3. 模型只允许返回一个 JSON 对象，严格结构如下；所有 Schema `extra=forbid`：

```json
{
  "answer": "纯文本答案",
  "key_points": ["要点 1"],
  "terms": [{"term": "术语", "explanation": "通俗解释"}],
  "evidence_refs": ["E1"]
}
```

4. answer 去首尾空白后非空并有明确最大长度；key_points 数量、每项长度和非空规则固定；terms 数量、term/explanation 长度和去重规则固定；evidence_refs 至少 1 条、数量有限、去重后仍非空。
5. 兼容真实 GLM 已观察到的“单一完整 Markdown JSON 围栏”只能复用 P4.3 的确定性规则：开头严格 ` ```json ` 或 ` ``` `、结尾严格 ` ``` `、内部无第二个围栏；不得用正则从任意解释文本里猜 JSON，不得接受多对象、前后杂文或 inline code。
6. 全部 alias 必须存在于本次候选并映射到同论文 Evidence；只要一个未知、跨论文或重复冲突引用，整次结果失败且不写部分 answer/Citation。成功结果至少一个 Citation。
7. SUMMARY 要概括当前范围；EXPLAIN 要用学习者可理解的语言说明含义、方法和术语；TRANSLATE 要忠实翻译，不额外添加论文未表达的结论。三种模式都必须只基于给定来源，证据不足时在 answer 中明确说明，不能伪造外部知识。

## 六、状态机、幂等、并发与事务

1. 创建阶段在短事务内完成 owner/PARSED/scope/source/hash 校验并插入 PENDING。先查同 request_hash 的 PENDING/RUNNING/SUCCEEDED；并发冲突由部分唯一索引最终裁决，捕获 IntegrityError 后回查既有行并返回 200 duplicate=true。FAILED 不阻止新建 201。
2. 后台只通过 `UPDATE ... WHERE status='PENDING'` 原子认领 RUNNING；未认领不得调用模型。认领提交后结束事务，再加载只读来源、rollback/close 事务后调用 LLM，外部网络期间绝不能持有数据库事务或行锁。
3. 模型响应先在内存完整解析、验证和绑定。随后用新事务重新加载 Explanation、Paper、scope 和全部 Evidence，复核 user/paper/request_hash/source hash；一次性写 answer/key_points/terms、全部 Citation、SUCCEEDED 和 completed_at。
4. 任一 flush/commit 前错误整批 rollback，再用独立会话安全写 FAILED。commit 抛错或结果未知时必须用新 Session 回查终态、结果和 Citation 数量：已成功则不得覆盖为 FAILED，未成功才补偿；不得产生 SUCCEEDED 无 Citation、Citation 部分写入或重复 Citation。
5. FAILED 只保存固定“学习解释生成失败，请稍后重试”等公开文案；日志只写 explanation id、paper id、固定阶段和异常类型，不记录正文、标题、answer、prompt、原始响应、引用文本、email、header、token、hash 或 secret。

## 七、3 个 API 契约

本轮只新增以下 3 条 method+path，预计总数 34→37，以实际收集为准：

1. `POST /api/v1/papers/{paper_id}/learning-explanations`
   - 严格请求字段按第四节；新建返回 201，复用活动/成功返回 200，并返回 `duplicate`。
   - 响应返回 id/paper_id/mode/scope/status/timestamps/duplicate，不返回 request_hash、source hash、prompt 或来源正文。
2. `GET /api/v1/learning-explanations/{explanation_id}`
   - 仅 owner；不存在/跨用户统一 404。
   - PENDING/RUNNING 不返回结果；FAILED 只返回固定 error_message；SUCCEEDED 返回 answer、key_points、terms 和按 sequence 排序的 citations。
   - Citation 仅返回安全字段 `evidence_id/page_number/evidence_type/quoted_text/char_start/char_end`，并可供前端原文定位。
3. `GET /api/v1/papers/{paper_id}/learning-explanations?page=1&page_size=20`
   - 严格 `page>=1`、`1<=page_size<=100`，按 created_at DESC/id DESC，返回 items/total/page/page_size。
   - list item 只返回元数据、状态、固定错误和时间，不批量返回完整 answer、terms 或引用正文；点击历史再调用详情，避免列表放大。

全部路径 UUID 保持严格 UUID4 和现有统一错误结构；非法 extra/scope/mode/language/page 为 422，论文未解析、来源为空/过大为固定 409，认证 401，资源不存在或越权 404。不得让底层 Pydantic/SQL/网络异常原文进入 API。

## 八、P09 论文阅读学习工作台

1. 新增受保护路由 `/papers/:id/read` 和 `PaperReadingView.vue`。PaperDetailView 对 PARSED 论文增加醒目的“开始阅读”入口；原“审阅”显示文案改为“批判性阅读”，route name、URL、API 和历史数据保持兼容。
2. 桌面端三栏：左侧章节目录，中间正文阅读区，右侧学习助手；阅读区是视觉主体。窄屏允许目录/助手折叠或按顺序堆叠，但不得遮挡正文。
3. 左栏按 sequence 展示章节层级和页码；默认选择首章节。中栏支持章节全文与页面模式、上一页/下一页/合法页码跳转；不要在页面初次加载时请求所有页。
4. 右栏固定提供总结/解释/翻译、当前章节/当前页面/已选 Evidence 三种范围（只有上下文存在时可选）、zh/en 和开始按钮。提交内容只含实体 id，不含正文。
5. 创建后每 3 秒轮询详情，仅 PENDING/RUNNING 继续；成功显示纯文本 answer、要点列表、术语卡和引用，失败显示固定错误与重试。禁止 `v-html`、不执行模型 Markdown、脚本、URL 或样式。
6. Citation 点击后在当前工作台切到对应页，使用 `normalized_text_content + char_start/char_end + quoted_text` 的安全三段文本节点高亮并 scrollIntoView；区间不一致时显示降级提示且不猜错误位置。不得通过 v-html 高亮。
7. 提供解释历史，每页 20 条、总数、上一页/下一页、状态和重新打开详情；历史失败有独立重试，不阻断正文阅读。
8. paper、section/page、explanation create/poll、history page 各自使用请求代数和明确的 paper/scope/id 校验。切换论文、章节、页面、历史项或卸载后，旧 Promise/Timer 不得覆盖新状态；所有 timer 在终态和卸载时清理。
9. 使用现有 Axios 鉴权与安全错误映射，不使用 localStorage/sessionStorage、token query、v-html 或原始服务端 error。不要引入新 UI 框架或无关依赖。

## 九、测试要求

1. 新增 013 migration、models、schemas、source resolver、prompt/parser、service、router 和 Vue 页面/API/路由测试；更新 `_BUSINESS_TABLES`、默认 Alembic revision 和清理逻辑。
2. 迁移测试覆盖：现有 012 数据不变；空表往返；非空任一学习表 downgrade 在 DDL 前无损中止；ORM/数据库 CHECK/FK/索引一致；19 张应用表最终零残留。
3. 来源测试覆盖 SECTION/PAGE/EVIDENCE 正常路径、跨用户、跨论文、错误 section/evidence、页码越界、空正文、无 Evidence、超长 SECTION、source hash 变化，且所有拒绝发生在 LLM 工厂调用前。
4. 模型测试覆盖三 mode/双语言、prompt 注入论文内容、HTML、控制字符、严格 JSON、允许的单围栏，以及多对象、前后杂文、额外围栏、extra、空 answer、超长字段、错误类型、0 引用、未知/重复/跨论文 alias。不得用只断言“非空”的 vacuous 测试冒充契约验证。
5. API 覆盖 3 路由的 401/404/409/422/200/201、UUID4、extra、scope 互斥、分页稳定排序、响应禁止字段和 USER/ADMIN 所有权；断言拒绝路径不构造 LLM/Embedding/Storage。
6. PostgreSQL 并发至少验证：同 request_hash 两线程最多一条活动/成功行且双方得到同 id；FAILED 可重试；后台双认领只调用一次 LLM；成功写入与 Citation 原子一致；flush/commit/commit-unknown 故障不产生部分结果或误报 FAILED。
7. 前端覆盖：受保护路由和详情入口、三栏/空态、章节与页面切换、scope 请求体不含正文、创建/轮询/成功/失败重试、历史真实分页参数、Citation 高亮/降级、乱序响应、路由切换、卸载 timer 清理、纯文本渲染和安全错误。
8. 测试必须注入 Mock；LLM/Embedding/Storage 工厂在不应触发的路径一旦调用就失败。不得读取真实 Key，不得向外网发请求。
9. 实际运行 P7.1 定向、P6/P5/P4/P3.5 回归和 Docker 后端全量；后端不得少于当前 830 且 0 skipped。前端全量不得少于 13 files/173，生产构建不得少于 132 modules。只能报告本轮真实执行结果。

## 十、运行验收与交付

1. 实际执行 Python 编译、Docker 后端全量、前端全量、生产构建、`alembic current/heads/check`、013 空/非空 downgrade 测试、路由/ORM/物理表统计、测试库残留和 `git diff --check`。
2. 只读核对开发库既有关键表计数；允许正常 Alembic schema upgrade，但不得创建学习结果、修改用户/论文/任务/审阅/指标/实验/报告业务行。测试数据只进入 `paperlens_test`，结束 19 张应用表残留总数必须为 0。
3. 只检查前端/后端源码是否存在 Web Storage、v-html、secret、敏感日志、绝对路径和原始模型响应泄漏；不要搜索或读取 `.env`。
4. 验收完成后同步全部设计、SDD、Sprint、README 和 docs 状态。明确：P7.1 已完成哪些学习能力；P7.2 问答、P7.3 学习沉淀、P8.1 管理员系统仍未实现。
5. 最终逐项报告 013、来源解析、模型契约/Citation、状态机/并发、3 API、P09 页面、全部测试、迁移、路由/表、HTTP、数据库残留、Git/禁改目录和未实现项。未执行项必须如实说明，不得用历史结果冒充。
6. HEAD 必须不变；两个 码道提示词文件在码道执行期间 SHA-256 必须与开始记录一致。

不要 git commit，不要修改 码道提示词，不要读取或使用 API Key，不要真实调用华为云，不要修改既有开发库业务数据，不要删除 volume，不要把 P7.1 拆成新轮次，也不要提前实现 P7.2/P7.3/P8.1～P8.4。

~~~~

---

## 27 — P7.2 当前论文多轮问答与证据化会话

> 来源：P7.1 经 码道独立修正和全量验收后生成（2026-07-15）。本节为下一轮唯一执行提示词。

~~~~text
# 码道下一阶段提示词：P7.2 当前论文多轮问答与证据化会话

## 任务目标

本轮固定为 P7.2，且必须在一个码道轮次内完成：在已验收的 P7.1 阅读工作台、LearningExplanation、Evidence、认证隔离、LLMClient 和 EmbeddingClient 基础上，实现只围绕当前用户当前论文的多轮问答。用户可以新建会话、连续提问、查看会话与轮次历史；每个有依据的回答必须绑定服务端检索到的真实 Evidence，无足够论文依据时必须明确降级，不能用模型常识伪装成论文结论。

不得返工 P2～P7.1，不得删除或改写现有学习解释。P7.3 的高亮/书签/笔记/知识卡/论文库/进度、P8.1 管理员后端+页面+不可变审计以及 P8.2～P8.4 均保持后续轮次，不因本轮扩张或增加轮数。

## 一、开始前边界与固定基线

1. 完整阅读根目录 `AGENTS.md` 和真实代码，严格按 `dev-process-framework → page-mockup → fullstack-testing → function-detail → sdd-workflow` 执行。先更新设计，再编码；如技能脚本不可用，记录后按相同顺序手工完成。
2. 开始前记录 git status/HEAD、Docker、Alembic 014 current/head/check、路由/表、测试库残留、开发库关键表只读计数，以及两个 码道提示词文件 SHA-256。现有全部未提交改动属于用户/码道，不得覆盖、还原或批量格式化。
3. 当前真实基线：HEAD `525828b42707f7d1ef5c8efe1f308ce4bdac5454`；Alembic `014_learning_contract_hardening`；37 条 `/api/v1` method+path；19 张 ORM 应用表、20 张物理表；Docker 后端 866 passed/0 failed/0 skipped；前端 14 files/183 passed；生产构建 135 modules；测试库 19 张应用表残留 0；开发库只读计数 `3/8/5/28/0/0/0/0/1/0`（users/papers/tasks/reviews/metrics/files/results/exports/learning/citations）；三容器运行且 PostgreSQL healthy。最终只能报告实际结果。
4. 禁止 git add/commit/reset/checkout/restore/clean/rebase；禁止修改 `.git/`、`.arts/`、`.codeartsdoer/`、`.skills/`、`AGENTS.md` 和两个 码道提示词文件；禁止删除 Docker volume、用户文件或开发库业务数据。
5. 禁止读取、搜索、打印、复制或推断 `.env`、API Key、JWT secret、Authorization、cookie、密码或 token；禁止 `docker compose config`、`docker inspect`、`env`、`set` 等可能展开 secret 的命令。
6. 本轮禁止真实 MaaS、真实 Embedding 和外网。自动测试只用可控 Mock/注入客户端；不得因本机配置 huawei_maas 产生计费调用。
7. 不实现开放域/联网问答、跨论文问答、消息编辑/删除/分享、会话删除、流式输出、语音、附件、笔记/知识卡、管理员功能、Celery/Redis、FAISS/pgvector、OCR、OBS 或 P8 能力。

## 二、设计、SDD 与 Sprint

1. 编码前更新 `ProjectDocs/systemDesign/01～08`：P7.2 用例、架构、015 数据模型、5 个 API、实施计划、FR-14、P09 问答区域和完整测试矩阵。
2. 更新 `ProjectDocs/specs_SDD/PaperLens/spec.md`、`tasks.md`、`design/design.md`、`design/07～10`，新增 `design/14-论文内问答.md`。任务必须引用具体 FR、API、表和页面章节。
3. 新建/更新 `ProjectDocs/sprint/论文内多轮问答.md`，编码时置为进行中，只有真实全量验收通过后才标记完成。
4. 完成后同步 README、product-requirements、architecture、api-contract、data-model、security-design、IMPLEMENTATION_STATUS 和 PROGRESS。P7.3/P8.1 不得写成已实现。

## 三、015 会话、轮次与引用模型

1. 新增单一 revision `015_paper_qa_conversations.py`，down_revision=014；不得修改 001～014。
2. `paper_qa_conversations`：UUID id；user_id FK users RESTRICT；paper_id FK papers CASCADE；UTC created_at/updated_at；索引 user+paper、paper+updated_at DESC/id DESC。普通业务 API 中 USER/ADMIN 都只能访问自己论文的会话。
3. `paper_qa_turns`：UUID id；conversation_id FK conversation CASCADE；user_id RESTRICT；paper_id CASCADE；sequence 正整数；client_request_id UUID；question Text；output_language zh/en；status PENDING/RUNNING/SUCCEEDED/FAILED；nullable context_hash 64 位小写十六进制、answer Text、grounded bool、error_message、started_at/completed_at；UTC created_at。
4. CHECK 保证 question 去空白后非空且有明确上限；conversation_id+sequence 唯一；user_id+conversation_id+client_request_id 唯一；同一 conversation 只允许一个 PENDING/RUNNING 的部分唯一索引。状态约束：PENDING 无上下文/答案/错误/时间；RUNNING 有 started_at、其余结果为空；SUCCEEDED 有 started/completed/context_hash、非空 answer、grounded，且无错误；FAILED 有 started/completed、固定“论文问答生成失败，请稍后重试”，无 answer/grounded/context_hash。
5. `paper_qa_citations`：turn_id CASCADE、evidence_id RESTRICT、sequence 正整数；复合主键 turn+evidence，turn+sequence 唯一；服务层验证 Turn/Conversation/Paper/User/Evidence 全图一致。
6. 有依据结果 `grounded=true` 必须至少一个 Citation；证据不足结果 `grounded=false` 必须零 Citation。该跨表规则由同一成功事务与服务测试强制。
7. 不存 prompt、完整上下文快照、Embedding 向量、模型原始响应、token usage、API Key、底层异常或 secret。ORM/迁移的列、FK、CHECK、索引名完全一致。
8. 015 upgrade 不修改任何既有业务行。空 P7.2 表支持 `014→015→014→015`；任一 P7.2 表非空时 downgrade 在任何 DDL 前无损中止。预计 22 张 ORM 应用表、23 张物理表，以实测为准。

## 四、问题创建、检索与上下文

1. 新建独立 qa schema/router/service/retriever，不把逻辑塞入 learning_service、papers.py 或 review_service。复用真实 AuthContext、LLMClient、EmbeddingClient 和安全错误体系。
2. 新建会话只允许 owner 的 PARSED 论文。会话不接收 user_id、paper_id 覆盖、system prompt、model 或任意正文。
3. 提交问题只接受 `question`、`output_language` 和必填 UUID4 `client_request_id`，`extra=forbid`。问题去首尾空白、非空且默认最多 2000 字符；配置上限写 `.env.example`。
4. 创建 PENDING 前确认 conversation/user/paper 全图、PARSED、论文至少有一条非空 Evidence。相同 client_request_id 返回既有 turn 200+duplicate=true；不同请求遇到当前会话活动 turn 固定 409；新建返回 201。并发最终由数据库唯一索引裁决。
5. 后台用条件 UPDATE 原子认领 RUNNING并提交。只读加载当前问题、按 sequence 的最近成功轮次和论文 Evidence 后 rollback/close，数据库事务结束后才调用 Embedding。
6. 复用现有 EmbeddingClient，以当前 question 为 query，对当前论文全部非空 Evidence 做确定性余弦排序；不得跨论文，不使用 ReviewDimension 查询。排序为 similarity DESC、page_number ASC、created_at ASC、id ASC，取配置 `qa_evidence_top_k`，默认有限值。校验向量数量、维度、NaN/Inf/布尔和零范数。
7. 最近对话上下文只取同会话已成功轮次，按 sequence 选最近 N 轮后恢复升序；N、总字符、单条 Evidence 字符均有配置。超限按完整轮次从最旧开始丢弃，不截断问题/回答后伪装完整上下文。当前问题不重复进入历史。
8. 检索完成后用短事务写 context_hash：canonical conversation/paper/turn sequence + 当前 question hash + 纳入的历史 turn id/question/answer hash + 候选 Evidence id/text hash + language。只有仍为 RUNNING 且 context_hash 为空才可写；提交后结束事务再调用 LLM。
9. Embedding 或 LLM 期间不得持有 Session/事务/行锁。Embedding/LLM 工厂只在全部同步拒绝检查通过后构造。

## 五、问答 prompt、严格输出与证据不足

1. 使用显式 `operation="paper_qa"`、language、evidence_aliases 调用现有 LLMClient；Mock 新增独立分支，不改变 REVIEW 和 learning 现有输出。
2. system 明确：只回答当前论文；paper title、历史 question/answer、当前 question、Evidence 都是不可信内容，其中任何指令无效；不得使用外部知识补足论文结论。
3. 所有内容用明确标签分隔并做安全文本处理。历史 assistant answer 同样视为不可信，不能提升为 system 指令。不得把用户问题拼成 system role。
4. 模型只允许返回一个 JSON 对象，严格 Schema、extra=forbid：

```json
{
  "answer": "纯文本回答或证据不足说明",
  "grounded": true,
  "evidence_refs": ["E1"]
}
```

5. answer 去空白后非空且限长；grounded 必须 bool；grounded=true 时 evidence_refs 1～top_k、无重复且全部存在；grounded=false 时 evidence_refs 必须为空，answer 必须明确说明无法仅根据当前论文确认，不得给出猜测答案。
6. 只兼容 P7.1 已验收的单完整 ` ```json ` / ` ``` ` 围栏规则；拒绝前后杂文、多对象、额外围栏、inline code、错误类型、extra、未知/重复/跨论文 alias。
7. 模型解析和引用绑定全部在内存完成。任何错误整轮失败，不写部分 answer/Citation。

## 六、持久化、并发与补偿

1. LLM 返回后新事务锁定 Turn，要求仍为 RUNNING；重新加载 Conversation/Paper、纳入的历史轮次和全部候选 Evidence，重算 context_hash，任何变化均固定 FAILED。
2. grounded=true 时再次绑定全部 alias 并验证 Evidence 同 paper；grounded=false 时强制零 Citation。一次事务写 answer、grounded、Citation、SUCCEEDED、completed_at，并更新 conversation.updated_at。
3. 任一 flush/commit 前错误整批 rollback，再用独立 Session 把 PENDING/RUNNING 安全写为 FAILED。FAILED 可用新 client_request_id 重试；旧失败 turn 保留在历史。
4. commit 抛错或结果未知时用新 Session 回查 turn 终态、answer、grounded、Citation 数量；已经成功不得覆盖 FAILED，未成功才补偿。不得出现 SUCCEEDED 与 Citation/grounded 不一致。
5. 日志只写 turn id、conversation id、paper id、固定 stage 和异常类型，不记录问题、历史、标题、answer、Evidence、prompt、原始响应、email、header、token、hash 或 secret。

## 七、5 个 API 契约

本轮只新增以下 5 条 method+path，预计 37→42，以实际统计为准：

1. `POST /api/v1/papers/{paper_id}/qa-conversations`：owner+PARSED 新建空会话，201。
2. `GET /api/v1/papers/{paper_id}/qa-conversations?page=1&page_size=20`：按 updated_at DESC/id DESC 返回当前用户会话元数据、turn_count、last_question_preview/last_status；不批量返回答案正文。
3. `GET /api/v1/qa-conversations/{conversation_id}?page=1&page_size=20`：owner-only；按 sequence ASC 分页返回 turns。PENDING/RUNNING 无结果；FAILED 固定错误；SUCCEEDED 返回 answer、grounded 和安全 Citation 字段 `evidence_id/sequence/page_number/evidence_type/quoted_text/char_start/char_end`。
4. `POST /api/v1/qa-conversations/{conversation_id}/turns`：严格请求字段；新建 201，client_request_id 复用 200+duplicate，其他活动冲突 409。
5. `GET /api/v1/qa-turns/{turn_id}`：轮询单轮详情，响应规则与会话详情中的 turn 一致。

全部路径严格 UUID4；分页 page>=1、1<=page_size<=100。认证 401，非法请求 422，未解析/无 Evidence/活动冲突 409，不存在或跨用户统一 404。响应不得公开 question 之外的 prompt/context_hash/向量/模型参数/内部错误；普通 ADMIN 也不能通过业务 API 读取他人会话。

## 八、P09 前端问答区

1. 不新建割裂的页面；在 PaperReadingView 右侧助手增加“学习解释 / 论文问答”切换。P7.1 总结/解释/翻译行为和测试保持不变。
2. 问答区提供会话分页列表、新建会话、当前会话消息时间线、问题输入、zh/en、发送和失败重试。首次进入不自动创建空会话或调用模型。
3. 每次发送由浏览器 `crypto.randomUUID()` 生成 client_request_id；重试失败问题生成新 id。请求只发 question/language/id，不发论文正文、历史、Evidence 或 token query。
4. 新 turn 每 3 秒串行轮询；终态停止。grounded=true 显示纯文本 answer 和可点 Citation；grounded=false 显示明确“当前论文证据不足”样式且没有伪引用。
5. Citation 复用 P7.1 已验收的切页、三段文本节点高亮、scrollIntoView 和区间不一致降级，不使用 v-html。
6. 会话列表和 turn 历史均真实 20 条分页。切换 paper/tab/conversation/page、发送新问题或卸载时，paper/conversation/turn/poll 各自代数令牌使旧 Promise/Timer 失效；timer 全部清理。
7. 模型和用户文本一律 Vue 文本插值；不执行 Markdown/HTML/URL/CSS。错误使用固定安全映射，不展示原始服务端 error。不得使用 localStorage/sessionStorage、引入 UI 框架或无关依赖。

## 九、测试要求

1. 覆盖 015 migration、ORM/数据库约束、schema、conversation/turn service、Evidence 检索、上下文预算、prompt/parser、5 API 和 Vue 问答交互；更新测试表清理与默认 revision。
2. 迁移覆盖 014 既有数据不变、空表往返、任一 P7.2 表非空 downgrade 无损中止、CHECK/FK/索引一致、22 张应用表最终零残留。
3. 拒绝测试覆盖 401、USER/ADMIN 跨用户、跨论文 conversation/evidence、非 PARSED、无 Evidence、空/超长问题、extra/UUID/分页，且 LLM/Embedding/Storage 工厂一旦被调用就失败。
4. 检索测试覆盖当前论文隔离、确定性排序、top_k、双语言问题、注入文本、向量数量/维度/NaN/Inf/布尔/零范数；不得只断言“返回非空”。
5. 上下文测试覆盖只取成功轮次、最近 N 轮、完整轮次预算、顺序、context_hash 在问题/历史/Evidence 变化后改变，以及模型前后来源变化固定失败。
6. 模型测试覆盖有依据/证据不足、严格 JSON/单围栏、HTML/控制字符、extra、多对象、杂文、空/超长、grounded 类型、0/未知/重复 alias 和 grounded/ref 冲突。
7. PostgreSQL 并发覆盖相同 client_request_id 同 id、不同 id 同会话最多一个活动 turn、sequence 唯一、双认领只调用一次 Embedding/LLM、FAILED 新 id 可重试、成功/Citation 原子性及 flush/commit/commit-unknown 补偿。
8. 前端覆盖 tab 不破坏 P7.1、会话新建/列表分页/切换、turn 历史分页、请求体无正文、client_request_id、创建/轮询/成功/证据不足/失败重试、Citation 高亮/降级、乱序响应、路由/tab/会话切换和卸载清理、纯文本/XSS 与安全错误。
9. 实际运行 P7.2 定向、P7.1/P6/P5/P4/P3.5 回归和 Docker 后端全量；后端不得少于 866 且 0 skipped，前端不得少于 14 files/183，构建不得少于 135 modules。只报告真实结果。

## 十、运行验收与交付

1. 执行 Python 编译、Docker 后端全量、前端全量、生产构建、alembic current/heads/check、015 往返/无损中止、路由/ORM/物理表、测试库残留和 git diff --check。
2. 只读核对开发库关键表计数；允许 schema upgrade，不得创建会话/turn、修改既有业务行。测试数据只进 `paperlens_test`，结束 22 张应用表残留总数为 0。
3. 静态检查 Web Storage、v-html、secret、敏感日志、绝对路径、原始问题/模型响应泄漏，但不得搜索或读取 `.env`。
4. 同步设计、SDD、Sprint、README 和 docs；明确 P7.2 已实现、P7.3/P8.1～P8.4 未实现。
5. 最终逐项报告 015、检索/上下文/模型契约、状态机/并发、5 API、P09 问答区、测试、迁移、路由/表、HTTP、数据库、Git/禁改目录和未实现项。未执行项如实说明。
6. HEAD 保持不变；两个 码道提示词文件在码道执行期间 SHA-256 保持开始值。

不要 git commit，不要修改 码道提示词，不要读取或使用 API Key，不要真实调用华为云，不要修改开发库业务数据，不要删除 volume，不要把 P7.2 拆成新轮次，也不要提前实现 P7.3/P8.1～P8.4。
~~~~

---

## 28 — P7.3 个人学习沉淀与论文库

> 来源：码道在 P7.2 独立审查与修正完成后生成（2026-07-15）

~~~~text
# 码道下一阶段提示词：P7.3 个人学习沉淀与论文库

## 任务目标

本轮固定为 P7.3，且必须在一个码道轮次内完成：在已验收的 P7.1 阅读工作台和 P7.2 当前论文问答基础上，实现用户自己的高亮、书签、笔记、知识卡、论文库组织与阅读进度。用户应能在阅读论文时保存学习痕迹，在论文库查看和整理学习状态，并从原文高亮/笔记继续制作与复习知识卡。

P7.3 是纯用户学习数据闭环，不调用 LLM/Embedding，不返工审阅、指标、实验、导出、认证或问答。P8.1 完整管理员后端+前端+不可变审计和 P8.2～P8.4 仍保持后续固定轮次，不增加码道轮数。

## 一、开始前边界与固定基线

1. 完整阅读根目录 `AGENTS.md` 和真实代码，严格按 `dev-process-framework → page-mockup → fullstack-testing → function-detail → sdd-workflow` 执行：先同步设计，再编码，最后同步 Sprint 和状态文档。
2. 开始前记录 git status/HEAD、Docker、Alembic current/heads/check、路由/表、测试库残留、开发库只读计数，以及两个 码道提示词文件 SHA-256。现有未提交改动全部属于用户/码道，不得覆盖、还原或批量格式化。
3. 当前验收基线：HEAD `525828b42707f7d1ef5c8efe1f308ce4bdac5454`；Alembic `015_paper_qa_conversations`；42 条 `/api/v1` method+path；22 张 ORM 应用表、23 张物理表；Docker 后端 909 passed/0 failed/0 skipped；前端 14 files/189 passed；生产与 Docker 构建 135 modules；测试库 22 张业务表残留 0；三容器运行且 PostgreSQL healthy。
4. 当前开发库只读计数为 `3/9/5/28/0/0/0/0/2/3/0/0/0`（users/papers/tasks/reviews/metrics/files/results/exports/learning/learning citations/qa conversations/turns/citations）。不得删除、修正或伪造这些业务数据；P7.3 自动测试只进 `paperlens_test`。
5. 禁止 git add/commit/reset/checkout/restore/clean/rebase；禁止修改 `.git/`、`.arts/`、`.codeartsdoer/`、`.skills/`、`AGENTS.md` 和两个 码道提示词文件；禁止删除 volume、用户文件或开发库业务行。
6. 禁止读取、搜索、打印、复制或推断 `.env`、API Key、JWT secret、Authorization、cookie、密码或 token；禁止可能展开 secret 的命令。本轮禁止真实 MaaS、Embedding 和外网，也不得新增任何模型调用。
7. 不实现管理员能力、协作分享、公开笔记、自动知识卡生成、间隔重复算法、全文搜索引擎、富文本/Markdown 编辑器、PDF.js/bbox 覆盖层、WebSocket、Celery/Redis、FAISS/pgvector、OBS 或 P8 能力。

## 二、设计、SDD 与 Sprint

1. 编码前更新 `ProjectDocs/systemDesign/01～08`：P7.3 用例、架构、016 数据模型、17 个 API、实施计划、FR-15、论文库与 P09 学习记录区域、测试矩阵。
2. 更新 `ProjectDocs/specs_SDD/PaperLens/spec.md`、`tasks.md`、`design/design.md`、`design/07～10`，新增 `design/15-个人学习沉淀与论文库.md`；任务必须引用 FR、API、表和页面章节。
3. 新建 `ProjectDocs/sprint/个人学习沉淀与论文库.md`，编码时为进行中，只有真实全量验收通过后才标记完成。
4. 完成后同步 README、product-requirements、architecture、api-contract、data-model、security-design、IMPLEMENTATION_STATUS 和 PROGRESS；P8.1～P8.4 不得写成已实现。

## 三、016 数据模型与不变量

新增单一 revision `016_personal_learning_library.py`，down_revision=015；不得修改 001～015。只新增以下 5 张表，预计 27 张 ORM 应用表、28 张物理表，以实测为准。

1. `paper_library_entries`：`user_id + paper_id` 复合主键；paper CASCADE、user RESTRICT；`reading_status` 仅 TO_READ/READING/COMPLETED/ARCHIVED；`favorite` bool；nullable `collection_name` 去空白后 1～100；nullable `last_page`、`furthest_page` 正整数且 last_page<=furthest_page；nullable UTC `last_read_at/completed_at`；created_at/updated_at。COMPLETED 必须有 completed_at，其他状态必须无 completed_at。
2. `paper_highlights`：UUID id；user_id/paper_id；page_number 正整数；char_start>=0、char_end>char_start；服务端派生的非空 quoted_text 与 64 位小写 `source_hash`；color 仅 YELLOW/GREEN/BLUE/PINK；created_at/updated_at。唯一 `user+paper+page+char_start+char_end`。
3. `paper_bookmarks`：UUID id；user_id/paper_id；page_number 正整数；nullable label 去空白后 1～100；created_at。唯一 `user+paper+page`。
4. `paper_notes`：UUID id；user_id/paper_id；anchor_type 仅 PAPER/PAGE/HIGHLIGHT；nullable page_number、highlight_id；content 去空白后 1～20000；created_at/updated_at。CHECK：PAPER 两个锚点均空；PAGE 只有 page_number；HIGHLIGHT 只有 highlight_id。服务层复核 Highlight/User/Paper 全图。
5. `paper_knowledge_cards`：UUID id；user_id/paper_id；nullable source_note_id、source_highlight_id，最多一个来源；front 去空白 1～2000；back 去空白 1～10000；mastery_status 仅 NEW/LEARNING/MASTERED；nullable last_reviewed_at；archived bool；created_at/updated_at。服务层复核来源同 user/paper。
6. 所有索引覆盖 owner+paper、分页排序和论文库筛选；ORM、迁移的列/FK/CHECK/unique/index 名完全一致。普通业务 API 中 USER/ADMIN 都只能访问自己的论文和学习数据。
7. 不保存任意 CSS、HTML、Markdown、URL、客户端 quoted_text、论文正文快照、prompt、向量、模型输出或 secret。016 upgrade 不修改既有业务行。
8. 空 P7.3 表支持 `015→016→015→016`；任一 P7.3 表非空时 downgrade 必须在任何 DDL 前无损中止。

## 四、论文库与阅读进度规则

1. 论文库列表以当前用户全部 Paper 为真集，LEFT JOIN 可选 library entry；没有 entry 时返回默认 TO_READ、favorite=false、无 collection/progress，不能为列表读取而写库。
2. library entry PATCH 只接受 `reading_status/favorite/collection_name` 的可选字段，至少一个字段；extra=forbid。collection_name 空白转 null。设置 COMPLETED 时服务端写 completed_at；离开 COMPLETED 时清空。
3. reading progress PATCH 只接受 `page_number`。论文必须 PARSED 且 1<=page<=page_count；upsert entry，`last_page=page_number`、`furthest_page=max(old,page)`、last_read_at=now；TO_READ 自动变 READING，COMPLETED/ARCHIVED 不被自动改写。
4. 响应的 `progress_percent` 由 furthest_page/page_count 确定性计算并限制 0～100，不持久化；page_count 为空时为 0。列表同时返回 highlight/bookmark/note/card 数量，禁止 N+1 无上限查询。
5. 论文库支持 page/page_size、reading_status、favorite、精确 collection_name 和 title/filename 关键字；排序为 favorite DESC、last_read_at DESC NULLS LAST、paper.created_at DESC、paper.id DESC。所有筛选长度有上限。

## 五、高亮、书签、笔记与知识卡规则

1. 高亮创建只接受 `page_number/char_start/char_end/color`；服务端加载当前论文 `PaperPage.normalized_text_content`（无则 text_content），校验范围与最大选中文本 5000 字，派生 quoted_text 和 `source_hash=sha256(paper_id+page+全文hash+范围+quoted_text)`。不得相信客户端引文。
2. 高亮列表按 page_number ASC、char_start ASC、id ASC，可选 page_number，20 条分页。删除只允许 owner；被 Note/Card 引用时固定 409，不级联丢学习数据。
3. 书签创建只接受 page_number 和可选 label，校验论文页范围；相同页重复返回既有 200+duplicate=true，新建 201。列表按 page ASC，删除 owner-only。
4. Note 创建严格按 anchor_type 接受对应锚点和 content；PATCH 只允许 content 且至少一个字段；锚点创建后不可偷换。列表可按 anchor_type/page_number/highlight_id 筛选，created_at DESC/id DESC 分页；删除被 Card 引用时 409。
5. Card 创建接受 front/back、可选且互斥的 source_note_id/source_highlight_id；PATCH 只允许 front/back/mastery_status/archived，至少一个字段。mastery_status 变化时服务端更新 last_reviewed_at；列表支持 mastery_status/archived，updated_at DESC/id DESC 分页；删除必须 owner-only。
6. 所有写入前复核 User/Paper/Page/Highlight/Note/Card 全图；flush/commit 失败 rollback，公开固定错误，不泄漏底层异常。并发重复高亮/书签由数据库唯一约束裁决并恢复既有对象。
7. 所有用户内容为纯文本。后端限制控制字符和长度；日志只写资源 id、paper id、固定 stage、异常类型，不写 quoted_text、note、front/back、标题、email、header、token 或 secret。

## 六、17 个 API 契约

预计公开路由 42→59，以实测为准。全部路径 UUID4、owner-only；未认证 401，非法请求 422，不存在/越权统一 404，来源被引用或资源状态冲突 409；分页 page>=1、1<=page_size<=100。

1. `GET /api/v1/library/papers`：论文库筛选分页和确定性进度/计数。
2. `PATCH /api/v1/papers/{paper_id}/library-entry`：upsert 组织状态。
3. `PATCH /api/v1/papers/{paper_id}/reading-progress`：记录当前页与最远页。
4. `POST /api/v1/papers/{paper_id}/highlights`。
5. `GET /api/v1/papers/{paper_id}/highlights`。
6. `DELETE /api/v1/highlights/{highlight_id}`：204。
7. `POST /api/v1/papers/{paper_id}/bookmarks`：201 或重复 200。
8. `GET /api/v1/papers/{paper_id}/bookmarks`。
9. `DELETE /api/v1/bookmarks/{bookmark_id}`：204。
10. `POST /api/v1/papers/{paper_id}/notes`。
11. `GET /api/v1/papers/{paper_id}/notes`。
12. `PATCH /api/v1/notes/{note_id}`。
13. `DELETE /api/v1/notes/{note_id}`：204。
14. `POST /api/v1/papers/{paper_id}/knowledge-cards`。
15. `GET /api/v1/papers/{paper_id}/knowledge-cards`。
16. `PATCH /api/v1/knowledge-cards/{card_id}`。
17. `DELETE /api/v1/knowledge-cards/{card_id}`：204。

列表统一返回 `items/total/page/page_size`。响应不公开 source_hash、内部所有权冗余字段或底层错误。删除 API 必须真实 204 空 body；不得用 GET 产生写入。

## 七、前端论文库与学习记录

1. 不新增割裂的重复论文页：把现有 PaperListView/`/papers` 升级为“论文库”，导航“论文”改为“论文库”。保留旧 route name 和深链兼容。首页副标题从过时的“学术论文审阅助手”改为“AI 驱动的个人论文阅读学习助手”。
2. 论文库提供关键字、状态、收藏、集合筛选，真实 20 条分页；卡片显示解析状态、reading_status、收藏、collection、最远阅读进度、最后阅读时间和四类学习记录数量。更新失败不得乐观伪成功。
3. PaperReadingView 右侧增加第三个“学习记录”标签，不破坏 P7.1/P7.2。提供当前页书签、高亮列表、笔记列表/编辑/删除、知识卡创建/编辑/掌握状态/归档/删除，各列表真实分页、加载、空态、安全错误和确认删除。
4. 高亮仅在 PAGE 模式允许。使用浏览器 Selection/Range 计算 contentRef 内纯文本的 normalized 字符区间；拒绝跨容器、折叠、空白、反向无效或 >5000 字选择。请求不发送 quoted_text。创建后从服务端响应显示并可再次定位。
5. 保存的 Highlight/Citation 点击均复用切页、三段文本节点 `<mark>`、scrollIntoView 和区间不一致降级；不得 v-html。多来源同时存在时只突出当前选择，避免重叠 mark 破坏 offset。
6. 每次成功加载真实页面后串行调用 reading-progress；路由/页码变化使用代数令牌，旧进度响应不能覆盖新论文。进度失败显示非阻断可重试提示，不影响正文阅读。
7. 创建 Note 可锚定论文、当前页或当前高亮；创建 Card 可手填 front/back 并可选择当前 Note/Highlight 来源。用户文本只用 Vue 文本插值，不执行 Markdown/HTML/URL/CSS。
8. paper/library/highlight/bookmark/note/card/progress 各自请求代数；切换 paper/tab/page/filter/pagination 或卸载时旧 Promise 失效，timer/listener 全部清理。不得 localStorage/sessionStorage、UI 框架或无关依赖。

## 八、测试要求

1. 覆盖 016 migration、ORM/数据库约束、全部 schema/service/17 API、PaperListView、PaperReadingView 和 Selection offset 工具；更新测试表清理与默认 revision。
2. 迁移覆盖 015 既有数据不变、空表往返、任一新表非空降级无损中止、CHECK/FK/unique/index 一致和 27 张应用表最终零残留。
3. owner/拒绝测试覆盖 USER/ADMIN 跨用户、跨论文 page/highlight/note/card、非 PARSED、页越界、空/超长/控制字符、extra、非法 enum/UUID/分页，以及错误路径零部分写。
4. 高亮覆盖服务端派生引文/source_hash、normalized fallback、Unicode/换行 offset、重复并发、来源文本变化后的定位降级、被引用删除 409；不得只断言“创建成功”。
5. 论文库/进度覆盖默认 LEFT JOIN 零写入、筛选排序、计数无串用户、furthest 单调、last_page 可回退、TO_READ→READING、COMPLETED/ARCHIVED 保持、并发 upsert。
6. Note/Card 覆盖锚点 CHECK、来源全图、PATCH 字段白名单、mastery 时间、被引用删除、纯文本/XSS 和分页。
7. 前端覆盖首页/导航文案、论文库筛选分页/更新失败、学习记录 tab、Selection 正反例、请求体无引文、书签重复、CRUD、确认删除、进度竞态、Citation/Highlight 定位、乱序响应与卸载清理。
8. 回归 P7.2 会话/问答、P7.1 学习解释、认证、导出、实验、指标和审阅。自动测试禁止真实 LLM/Embedding/Storage/外网。
9. 实际运行 P7.3 定向、Docker 后端全量、前端全量和生产/Docker 构建；后端不得少于 909 且 0 skipped，前端不得少于 14 files/189，构建不得少于 135 modules。只报告实际结果。

## 九、运行验收与交付

1. 执行 Python 编译、Docker 后端全量、前端全量、生产与 Docker 构建、alembic current/heads/check、016 往返/无损中止、路由/ORM/物理表、测试库残留和 git diff --check。
2. 只读核对开发库关键表计数；允许 schema upgrade，不得创建任何 P7.3 业务行或修改既有数据。测试数据只进 `paperlens_test`，结束 27 张应用表残留总数为 0。
3. 静态检查 Web Storage、v-html、secret、敏感日志、绝对路径、原始用户文本泄漏和危险 URL，但不得搜索或读取 `.env`。
4. 最终逐项报告 016、论文库/进度、四类学习记录、17 API、页面、测试、迁移、路由/表、HTTP、数据库、Git/禁改目录和未实现项。未执行项如实说明。
5. HEAD 保持不变；两个 码道提示词文件在码道执行期间 SHA-256 必须保持开始值。

不要 git commit，不要修改 码道提示词，不要读取或使用 API Key，不要真实调用华为云，不要修改开发库业务数据，不要删除 volume，不要把 P7.3 拆成新轮次，也不要提前实现 P8.1～P8.4。
~~~~

---

## 29 — P8.1 完整管理员系统与不可变审计

> 来源：P7.3 经 码道独立修正和全量验收后生成（2026-07-16）。本节为下一轮唯一执行提示词。

~~~~text
# 码道下一阶段提示词：P8.1 完整管理员系统与不可变审计

## 任务目标

本轮固定为 P8.1，且必须在一个码道轮次内完成：在 P3.5 已验收的注册、登录、AuthSession、USER/ADMIN RBAC，以及 P2～P7.3 全部用户能力基础上，实现可实际使用的管理员后端、Vue 管理页面、用户角色/状态管理、跨用户内容只读治理和不可变审计。不得把后端、前端、迁移、权限、并发或审计拆成额外码道返工轮次。

P8.2 仍只用于用户端/管理员端 E2E、任务恢复和全链路一致性，P8.3 用于性能可靠性，P8.4 用于华为云部署和综合安全；不得提前实现或增加轮次。

## 一、开始前边界与固定基线

1. 完整阅读根目录 `AGENTS.md` 和真实代码，严格按 `dev-process-framework → page-mockup → fullstack-testing → function-detail → sdd-workflow` 执行：先更新设计与页面/测试方案，再编码，最后同步 Sprint；修复缺陷时按 `bug-fix-reporter` 留痕。
2. 开始前记录 git status/HEAD、Docker、Alembic current/heads/check、API/表数、测试库残留、开发库关键表只读计数，以及两个 码道提示词文件 SHA-256。现有未提交改动都属于用户/码道，不得覆盖、还原或批量格式化。
3. 当前真实基线：HEAD `525828b42707f7d1ef5c8efe1f308ce4bdac5454`；Alembic `016_personal_learning_library`；59 条 `/api/v1` method+path；27 张 ORM 应用表、28 张物理表；Docker 后端 977 passed/0 failed/0 skipped；前端 16 files/197 passed；生产与 Docker 构建 136 modules；测试库 27 张应用表残留 0；三容器运行且 PostgreSQL healthy，后端/前端 HTTP 200。最终只报告实际结果。
4. 开发库只读计数为 `3/9/5/28/0/0/0/0/2/3/0/0/0/0/0/0/0/0`，依次为 users/papers/tasks/reviews/metrics/files/experiment results/exports/learning explanations/learning citations/qa conversations/qa turns/qa citations/library entries/highlights/bookmarks/notes/cards。不得修改、删除或伪造这些业务数据；自动测试只进入 `paperlens_test`。
5. 禁止 git add/commit/reset/checkout/restore/clean/rebase；禁止修改 `.git/`、`.arts/`、`.codeartsdoer/`、`.skills/`、`AGENTS.md` 和两个 码道提示词文件；禁止删除 volume、用户文件或开发库业务数据。
6. 禁止读取、搜索、打印或复制 `.env`、API Key、JWT secret、Authorization、cookie、密码、refresh/reset token 或完整环境；禁止可能展开 secret 的命令。禁止真实 MaaS/Embedding/外网，管理员路径若构造 LLM/Embedding/Storage client，测试必须立即失败。
7. 本轮不做管理员冒充、查看/重置密码、默认管理员、批量操作、论文/报告删除、任务取消、任意 SQL/排序字段、用户内容预览、邮件/MFA、Celery/Redis、OBS 或 P8.2～P8.4。ADMIN 在普通业务 API 中仍不能绕过 owner；跨用户访问只能走显式 `/admin` API。

## 二、设计、SDD 与 Sprint 先行

1. 编码前同步 `ProjectDocs/systemDesign/01～08`，明确管理员用例、017 模型、8 条 API、页面状态/危险操作确认、权限边界、并发事务和测试矩阵。
2. 更新 `ProjectDocs/specs_SDD/PaperLens/spec.md`、`tasks.md` 与相关 design；新增管理员系统详细设计和 `ProjectDocs/sprint/完整管理员系统与不可变审计.md`，开始时置进行中，真实验收后再完成。
3. 文档不得把 P3.5 登录注册或 P7.3 学习闭环写成未实现；不得把 P8.2 的 E2E/恢复、P8.3 性能或 P8.4 部署提前声明完成。

## 三、017 迁移与 append-only 审计

1. 新增 `017_admin_audit_logs.py`，只新增 `admin_audit_logs`，不改写 001～016 revision，不回填既有业务行。预期为 28 张 ORM 应用表、29 张物理表，以实际为准。
2. 最小字段：UUID id；actor_user_id String(128) FK users.id RESTRICT；固定 action；resource_type；resource_id；8～500 字且无控制字符的 reason；非空严格小对象 before_state/after_state JSONB；created_at。建立 actor、resource、action、created_at DESC/id DESC 查询索引和严格 CHECK，ORM/迁移名称完全一致。
3. action 只允许 `ADMIN_BOOTSTRAPPED`、`USER_ROLE_CHANGED`、`USER_STATUS_CHANGED`；resource_type 只允许 USER。before/after 只允许 role/status，不保存 email、display_name、密码/hash/token/cookie、正文、storage key、source snapshot、请求 header/IP/user-agent、异常或环境值。
4. 表必须 append-only：应用层无 UPDATE/DELETE 路由；PostgreSQL trigger 拒绝 UPDATE/DELETE。用户变更、session/reset 失效和 audit 插入必须同一事务，任一步失败全部回滚。
5. upgrade 兼容现有 016 数据。downgrade 先统计审计表，非空时在任何 DDL 前无损拒绝；空表允许 `016→017→016→017` 往返，不得为通过测试删除真实审计记录。

## 四、管理员授权、首次引导与用户变更

1. 复用真实 AuthContext/require_admin。无认证 401，已认证 USER 403；DISABLED、session 撤销、refresh replay 等继续由 P3.5 服务端状态拒绝，不能只信 JWT role claim。前端路由守卫只改善体验，后端始终权威。
2. 提供显式运维 CLI `python -m paperlens.cli admin-bootstrap --user-id <UUID> --reason <text>`：只允许把已存在、ACTIVE 的 USER 提升为首个 ADMIN，且仅当数据库没有 ACTIVE ADMIN 时成功；锁定用户集合，以目标用户 id 作为 actor_user_id，创建一条 ADMIN_BOOTSTRAPPED 审计并撤销旧 session，同事务完成。已有 ACTIVE ADMIN、目标非法/不存在/禁用、并发第二次执行都安全失败。不得创建默认账号、读取密码或接受 email 模糊匹配。自动验收不得在开发库执行该 CLI。
3. `PATCH /api/v1/admin/users/{user_id}` 只接受可选 role USER|ADMIN、可选 status ACTIVE|DISABLED 和必填 reason；extra=forbid，role/status 至少一个。相同值返回 200/changed=false 且不写审计。
4. 以确定顺序 `FOR UPDATE` 锁定 ACTIVE ADMIN 集合和目标。禁止管理员自降级或自禁用；任何提交后至少保留一个 ACTIVE ADMIN。两个管理员并发互相降级/禁用时最多一个成功，另一个固定 409，绝不能出现零 ACTIVE ADMIN。
5. 每个实际变化字段各写一条 audit；before/after 来自锁定后的数据库。角色或状态变化后撤销目标全部活动 AuthSession；禁用时同时使未使用 PasswordResetToken 失效，重新启用不恢复旧凭据。失败/no-op 不审计。
6. flush/commit 前异常 rollback；commit 后抛错用新 Session 和预生成 audit id 回查最终状态，不能重复审计或误报。日志不记录 email、reason、token、内容、SQL，只允许 stage/actor id/target id/action/异常类型。

## 五、恰好 8 条管理员 API

新增以下 8 条 method+path，预计总数 59→67，以最终收集为准。所有响应 Schema extra=forbid；列表统一 page>=1、1<=page_size<=100、固定 total/page/page_size/items，按 created_at DESC/id DESC 稳定排序；只接受白名单筛选，不接受任意 sort/order/include；聚合/批量查询避免逐行 N+1。

1. `GET /api/v1/admin/dashboard`：用户按 role/status、论文按 status、任务按 task_type/status、报告按 report_type/status的非负聚合计数，不返回用户内容或最近正文。
2. `GET /api/v1/admin/users?page&page_size&role&status&q`：q 长度 1～100，只匹配规范化 email/display_name；返回 id/email/display_name/role/status/failed_login_count/locked_until/created_at/updated_at，以及 active_session、paper、task、export 计数，禁止任何 hash/token。
3. `GET /api/v1/admin/users/{user_id}`：同一严格用户字段和资源计数；不存在 404。
4. `PATCH /api/v1/admin/users/{user_id}`：执行第四节角色/状态变更、凭据失效与原子审计，返回 changed 和本次 audit_ids。
5. `GET /api/v1/admin/papers?page&page_size&status&user_id&q`：只读跨用户元数据；仅 id/user_id/owner_email/title/filename/file_size/page_count/status/created_at/updated_at；不得返回 storage_key/file_hash/正文/Table/Evidence，FAILED 只映射固定安全错误。
6. `GET /api/v1/admin/tasks?page&page_size&task_type&status&user_id&paper_id`：只读固定元数据；不返回模型输入输出、论文内容、原始错误或 token usage。
7. `GET /api/v1/admin/exports?page&page_size&report_type&status&user_id&paper_id`：只读安全字段；不返回 storage_key/source_snapshot/source_hash/content_hash，FAILED 只显示固定文案。
8. `GET /api/v1/admin/audit-logs?page&page_size&actor_user_id&action&resource_id&created_from&created_to`：返回 actor 当前 id/email、固定 action/resource、reason、严格 before/after 和 created_at；时间必须带时区且 from<=to。

普通论文、任务、导出、学习、问答等 API 的 USER/ADMIN owner 行为必须保持不变。管理员只读查询使用有限列投影，不加载 deferred raw_text、structured_data、source_snapshot 或文件对象。

## 六、Vue 管理后台

1. 新增受保护 `/admin` 路由和 `AdminDashboardView`；导航仅对当前 ADMIN 显示“管理后台”。刷新页面时等待认证恢复后再判定，USER 进入显示无权限并返回安全页面；401 清理本地认证状态，403 不泄露数据。不得把角色写入 Web Storage 或只靠前端授权。
2. 页面包含四个一级区域：总览、用户、内容、审计。内容区含论文/任务/报告三个子页签。每个列表必须有加载、空、错误、重试、筛选、真实分页和防快速切换乱序覆盖；离开页面/切页/筛选时旧响应不得覆盖当前状态。
3. 总览展示固定计数卡，不展示正文、问题、笔记或最近用户内容。用户列表/详情展示第五节白名单字段和资源计数。
4. 角色/状态操作必须打开确认对话框，明确目标与后果，要求输入 8～500 字 reason；提交中禁用重复操作。成功后只按服务端响应刷新；失败/no-op 显示明确安全文案。前端也禁止自降级/自禁用按钮，但以后端 409 为准。
5. 论文/任务/报告只读，不能链接到绕过 owner 的普通详情页，也不提供删除、下载、取消或冒充入口。审计列表只读展示 before→after，不提供编辑/删除。
6. 全部服务端文本使用 Vue 转义插值；禁止 v-html、Web Storage、token query、直接 innerHTML、服务端错误透传。复用现有视觉样式并保证桌面/窄屏可用。

## 七、测试要求

1. 新增 017 迁移、admin schema/service/router/CLI 的 PostgreSQL 测试；更新 `_BUSINESS_TABLES`、默认 revision 和零残留检查。覆盖空表往返、任一 audit 非空降级拒绝、ORM/DB 约束索引同名、直接 SQL UPDATE/DELETE 被 trigger 拒绝。
2. 8 条 API 全覆盖 401、USER 403、ADMIN 200、UUID/分页/筛选/时间/extra 422，以及响应禁止字段递归扫描。Dashboard 用精确计数；各列表验证筛选、空页、稳定排序、真实分页和无 N+1，不能用 vacuous 断言。
3. 覆盖 CLI 首次提升、已有管理员、目标异常和真实 PostgreSQL 并发仅一次成功；不得在开发库运行。覆盖 role/status 单变更、双变更、no-op、404、自降级/自禁用、最后管理员、旧 access/refresh/reset 立即失效及不恢复。
4. 两线程验证互相降级/禁用不能产生零 ACTIVE ADMIN；同目标并发结果串行一致。注入 audit/user/session/reset flush、commit 前失败与 commit 后抛错，验证用户、凭据和 audit 不出现部分提交或重复。
5. 前端覆盖路由/导航权限、四区域、三内容页签、精确请求参数、分页/筛选、确认 reason、成功/no-op/401/403/409/422/未知错误、重复点击、乱序响应和卸载清理；递归确认无危险字段、v-html/Web Storage/token URL。
6. 运行 P8.1 后端定向、全部迁移测试、P3.5 认证与 P2～P7.3 关键回归、Docker 后端完整全量；必须不少于 977、0 failed、0 skipped。运行前端定向和完整全量，不少于 16 files/197 passed，并执行本地及 Docker 生产构建，不少于 136 modules。
7. 自动测试只使用测试库和 Mock。管理员路径若访问真实网络、MaaS、Embedding、Storage 或开发库业务行必须失败。

## 八、文档、运行验收与交付

1. 完成后同步 `ProjectDocs/systemDesign/01～08`、SDD spec/tasks/design、Sprint、`docs/IMPLEMENTATION_STATUS.md`、`docs/PROGRESS.md`、api-contract/architecture/data-model/security-design 和 README。明确 P8.1 实际完成项以及 P8.2～P8.4 未完成项。
2. 实际验证 017 current/head/check、空表往返、非空审计降级拒绝、trigger 不可变性、路由/表数、Python 编译、前端 TypeScript/Vite、Markdown 本地链接、git diff --check 和敏感信息/危险渲染扫描。
3. 只读核对开发库关键表计数；允许正常 schema upgrade，但不得引导管理员、变更角色/状态或写审计。测试结束 `paperlens_test` 的全部应用表残留必须为 0。
4. 重建并保持 backend/frontend/postgres 运行，PostgreSQL healthy，后端 health 和前端 HTTP 200。不得以宿主机通过代替 Docker 结果。
5. HEAD 必须不变、不得创建提交；禁改目录无差异；两个 码道提示词在执行期间 SHA-256 必须保持开始值。
6. 最终逐项报告 017/不可变审计、CLI、授权与最后管理员并发、8 API、管理页面、全部测试、迁移、路由/表、HTTP、测试库残留、开发库只读计数、Git/禁改目录和未实现项。未执行必须如实说明，不能用历史结果冒充。

不要 git commit，不要修改 码道提示词，不要读取或使用 API Key，不要真实调用华为云，不要修改开发库业务数据，不要删除 volume，不要拆分 P8.1，也不要提前实现 P8.2～P8.4。
~~~~
