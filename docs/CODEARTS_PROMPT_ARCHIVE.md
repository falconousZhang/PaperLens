# PaperLens 码道提示词归档

> 建立日期：2026-07-13  
> 用途：集中保存实际生成给华为云码道的任务提示词，作为任务范围、验收标准和历史审计记录。

## 归档规则

1. 按生成时间顺序保存不同版本；相同内容在聊天展示并写入文件时只归档一次。
2. 后续每个开发任务都在本文件末尾追加对应提示词，并同步更新 `docs/CODEARTS_NEXT_PROMPT.md` 供用户提交给码道。
3. 码道负责按提示词实施；Codex 在码道完成后审查真实代码并独立复测。若发现问题，依据用户的持续授权由 Codex 直接修正并验证，不再让码道反复返修；当前阶段确认通过后，再生成下一步提示词。
4. 不以 `docs/PROGRESS.md` 的汇报代替代码、数据库、Docker 和测试结果核验。
5. 本文 01～08 均从本机 Codex rollout JSONL 的原始消息或 `apply_patch` 参数逐字恢复；仅统一换行为 LF，没有根据阶段汇报改写正文。
6. P2.5 之前实际交给码道的版本为 01～07；P2.5 已生成提示词，但该轮由 Codex 直接实施。从 P2.6 起恢复码道实施、Codex 审查的协作方式。
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
| 10 | P2.7 ProjectDocs 验收去伪与文档收口 | ⚠️ 未提交，改由 Codex 直接修正 |
| 11 | P3.1 基于 MockLLM 的结构化审阅后端闭环 | ✅ 已提交并完成；Codex 审查通过 |
| 12 | P3.2 华为云优先的 Embedding 抽象与语义 Evidence 检索 | ✅ 本轮生成，待提交 |

---

## 01 — P1 工程骨架首次实施

> 来源：Codex 历史会话中的直接回复原文（2026-07-12，rollout 行 117）

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

> 来源：Codex 历史会话中的直接回复原文（2026-07-12，rollout 行 159）

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

> 来源：`docs/CODEARTS_NEXT_PROMPT.md` 覆盖补丁原文（2026-07-13，rollout 行 1058）；生成后改由 Codex 实施，未再投递码道

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

> 来源：Codex 根据 ProjectDocs 静态审查结果生成（2026-07-13）

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
4. 不要把本轮提示词或 Codex/码道职责改写进 AGENTS.md。

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
6. docs/CODEARTS_NEXT_PROMPT.md 和 docs/CODEARTS_PROMPT_ARCHIVE.md 由 Codex 管理，本轮不得修改。

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

## 10 — P2.7 ProjectDocs 验收去伪与文档收口

> 来源：Codex 对 P2.6 码道结果独立复核后生成（2026-07-13）
> 状态：未提交给码道；用户调整协作流程后，由 Codex 直接完成同等修正并独立验证。

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

- Codex 独立复核发现 P2.6 的“0 失效锚点”不成立，实际为路径 0、锚点 17。
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

注意：上述两个提示词文件可能已经包含 Codex 在本轮开始前生成的未提交变更。开始工作前先记录 git status --short，并分别记录这两个文件的 SHA-256；它们可以作为既有基线出现在 git diff 中，但本轮不得修改、还原或覆盖，结束时 SHA-256 必须与开始前完全相同。禁止范围中的其他代码和配置应使用 git diff --quiet 单独验证。

完成前依次执行：

1. 修改前运行新检查器并保存 75/0/17 结果。
2. 修改后运行同一检查器并保存 75/0/0 结果。
3. git diff --check，必须无错误。
4. 对比开始前后的状态：P2.7 新增修改必须只有允许范围；两个 Codex 提示词文件只作为既有基线且 SHA-256 不变。
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

> 来源：Codex 在直接完成 P2.7 收口并独立验收后生成（2026-07-13）
> 状态：已提交给码道并完成；Codex 独立审查、直接修复并于 2026-07-13 验收通过。

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

先检查 `git status --short`，记录工作区已有修改，不得覆盖、回退或清理用户/Codex 的既有改动。先给出简短实施计划和预计修改文件，然后直接实施，不要停留在建议层面。

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

开始工作前分别记录两个 Codex 提示词文件的 SHA-256；它们可以作为既有未提交修改出现在 git diff 中，但本轮不得修改、还原或覆盖，结束时 SHA-256 必须完全相同。不得清理其他既有工作区修改。

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

> 来源：Codex 在 P3.1 独立审查、直接修复并验收通过后生成（2026-07-13）
> 状态：待用户提交给码道实施；完成后由 Codex 审查并在授权范围内直接修正。

~~~~text
继续维护 D:\shixi\PaperLens 项目。

本轮定义为 P3.2：华为云优先的 Embedding 抽象与语义 Evidence 检索。P3.1 已完成 MockLLM 结构化审阅后端闭环并经 Codex 独立验收；当前真实基线为 Docker 后端 115 passed、0 skipped，P3.1 定向测试 53 passed，前端 15 passed 且构建成功，12 条 /api/v1 业务端点、14 张业务表，Alembic 位于 003 head 且 check 无差异，Markdown 链接 75/0/0。

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

开始工作前先记录 `git status --short`，并分别记录两个 Codex 提示词文件的 SHA-256。它们可以作为既有未提交基线出现在 git diff 中，但本轮结束时 SHA-256 必须完全不变。不要清理或覆盖其他既有未提交修改。

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
13. 比较两个 Codex 提示词文件开始前后的 SHA-256，必须完全不变。
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

不要 git commit，不要删除数据库 volume，不写入任何真实密钥，不清理开发库已有数据，不要修改或还原 Codex 提示词文件。
~~~~
