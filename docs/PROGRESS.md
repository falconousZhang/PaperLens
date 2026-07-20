# PaperLens 阶段汇报

> 最后更新：2026-07-16

---

## 一、项目概况

PaperLens 是一个 AI 驱动的个人论文阅读学习助手，批判性审阅作为高级学习模式保留，核心流程：

论文上传 → PDF 解析 → 章节和表格提取 → 文本分块 → 向量索引 → 原文证据检索 → 结构化论文审阅 → 实验指标提取 → checkpoint 统计口径判断 → CSV/Excel 实验数据分析 → 审稿报告导出

---

## 二、已完成阶段

### P0 — 需求分析与架构设计 ✅

| 交付物 | 状态 |
|--------|------|
| docs/product-requirements.md | ✅ |
| docs/architecture.md | ✅ |
| docs/data-model.md | ✅ |
| docs/api-contract.md | ✅ |
| docs/security-design.md | ✅ |
| docs/IMPLEMENTATION_STATUS.md | ✅ |

### P1 — 工程骨架搭建 ✅

| 交付物 | 状态 |
|--------|------|
| 后端项目初始化（FastAPI + SQLAlchemy + Alembic） | ✅ |
| 前端项目初始化（Vue3 + TypeScript + Vite） | ✅ |
| 数据库迁移脚本（001_initial） | ✅ |
| ORM 模型（13 张表 + 1 张关联表） | ✅ |
| GET /api/v1/health 健康检查 | ✅ |
| 统一错误响应结构 | ✅ |
| LLMClient 接口 + MockLLMClient | ✅ |
| 基础 pytest 测试 | ✅ |
| 前端首页 + 健康检查调用 + 后端不可用提示 | ✅ |
| Docker Compose（PostgreSQL + backend + frontend） | ✅ |
| .env.example / .gitignore / README.md | ✅ |

### P1.1 — 工程修复 ✅

| 修复项 | 说明 |
|--------|------|
| Alembic env.py | 标准 online/offline 配置，target_metadata=Base.metadata |
| 时间字段 | String(30) → DateTime(timezone=True), server_default=func.now() |
| obs_key → storage_key | 统一重命名 |
| PaperStatus.PROCESSING | 新增中间状态 |
| StrEnum 枚举类 | paperlens/core/enums.py |
| 统一错误格式 | AppError + HTTPException + RequestValidationError + 通用 Exception |
| ExperimentResult.metric_comparisons | 类型修正为 list \| None |
| 后端容器 entrypoint.sh | alembic upgrade head → uvicorn |
| 前端 Dockerfile | Node 22 LTS + npm ci |
| 配置项扩展 | storage_backend, storage_root, demo_user_id, max_page_count, chunk_max_chars, chunk_overlap_chars |

### P2 第一阶段 — PDF 上传与解析 + 前端闭环 ✅

| 交付物 | 状态 |
|--------|------|
| 通用存储层（StorageBackend + LocalStorage + OBSStorage 预留） | ✅ |
| POST /api/v1/papers/upload（multipart 流式上传 + 校验 + SHA-256） | ✅ |
| PDF 解析服务（PyMuPDF + pdfplumber + 章节识别 + 文本分块 + Evidence） | ✅ |
| GET /api/v1/papers（列表 + 分页） | ✅ |
| GET /api/v1/papers/{id}（详情） | ✅ |
| GET /api/v1/papers/{id}/pages/{page_number} | ✅ |
| GET /api/v1/papers/{id}/sections | ✅ |
| GET /api/v1/papers/{id}/evidences | ✅ |
| GET /api/v1/evidences/{evidence_id} | ✅ |
| 前端上传页面（拖拽 + 文件校验 + 进度条） | ✅ |
| 前端论文列表（PROCESSING 自动轮询） | ✅ |
| 前端论文详情（章节/证据 Tab 切换） | ✅ |
| DB 依赖注入修复（Depends(get_db) 替代 lambda hack） | ✅ |
| chunk/section 关联映射修复（section_sequence 字段） | ✅ |
| Docker 容器构建与启动（PYTHONPATH 修复） | ✅ |

### P2.1 — 可靠性与闭环修复 ✅

#### 修改文件

| 文件 | 修改内容 |
|------|----------|
| backend/paperlens/utils/storage.py | Path.resolve + relative_to 替换 startswith；统一存储路径 papers/{uuid}/source.pdf；反斜杠穿越防护；_sanitize_filename |
| backend/paperlens/api/papers.py | UUID4 Path 参数校验；status 枚举校验；DB 失败时删除存储对象；安全错误消息；Evidence section_id 绑定 |
| backend/paperlens/core/errors.py | 错误响应增加 details 字段；generic_exception_handler 记录日志 |
| backend/paperlens/models/models.py | 增加 CheckConstraint（page_number、progress、rating、confidence、char_start/end、bbox、枚举值） |
| backend/paperlens/services/pdf_parser.py | Evidence 改为 page-local；使用 PyMuPDF blocks 获取真实 bbox；_normalize_whitespace；context manager 关闭 doc；表格使用 find_tables 获取 bbox |
| backend/alembic/versions/002_constraints.py | 新迁移：18 个 CheckConstraint |
| backend/tests/conftest.py | 新增 create_multipage_pdf |
| backend/tests/test_api/test_health.py | 环境变量读取 DB URL；UUID 422 测试；status 枚举 422 测试；details 字段测试；跨用户 403 严格断言 |
| backend/tests/test_services/test_storage.py | 新增 6 项路径穿越测试 + _sanitize_filename 测试 + build_key 测试 |
| backend/tests/test_services/test_pdf_parser.py | 新增 6 项 Evidence 测试（page-local、bbox、char range、chunk 关联、doc 关闭） |
| frontend/src/views/PaperDetailView.vue | 页面 Tab + 页码导航 + char_start/char_end 高亮 + XSS 防护 + PROCESSING 轮询 + FAILED 提示 + onUnmounted 清理 |
| frontend/src/views/PaperListView.vue | onUnmounted 清理轮询 + 错误显示 + 重试按钮 |
| frontend/src/tests/PaperDetailView.test.ts | 4 项 Vitest 测试 |
| frontend/vite.config.ts | 添加 Vitest 配置 |
| frontend/package.json | 添加 vitest + @vue/test-utils + happy-dom + test 脚本 |
| docker-compose.yml | 添加 PAPERLENS_DB_HOST 环境变量 |

#### 已修复问题

1. **LocalStorage 路径穿越漏洞**：`../store_evil/file.pdf`、`..\store_evil\file.pdf`、`/absolute/path`、sibling-prefix 绕过均被拒绝
2. **UUID 校验**：非法 UUID 路径参数返回 422 + 统一错误结构
3. **status 参数校验**：非法状态值返回 422 而非空列表
4. **数据库约束**：002_constraints 迁移增加 18 个 CheckConstraint
5. **DB 测试跳过**：Docker 内 37 passed, 0 skipped
6. **Evidence page-local**：每个 Evidence 绑定单页，使用 PyMuPDF blocks 真实 bbox
7. **char_start/char_end 精确**：`quoted_text == page_text[char_start:char_end]`（规范化后）
8. **前端 Evidence 闭环**：点击 Evidence → 切换页面 Tab → 加载对应页 → 高亮 quoted_text
9. **XSS 防护**：使用 computed 拆分 before/highlight/after，不使用 v-html
10. **轮询清理**：PaperListView + PaperDetailView 均在 onUnmounted 中 clearInterval
11. **安全错误消息**：上传失败不暴露 str(e)，只返回通用消息
12. **存储回滚**：DB 提交失败时删除已保存的 storage object

#### 新 Alembic revision

`002_constraints`（head），支持 downgrade 到 `001_initial` 和重新 upgrade

#### 后端测试结果

- 本地：32 passed, 5 skipped（无 PostgreSQL）
- Docker 内：37 passed, 0 skipped

#### 前端测试与构建

- Vitest：4 passed
- npm run build：成功

#### 双页 PDF 端到端验证

- 上传双页 PDF → PROCESSING → PARSED
- 2 个 Evidence（每页一个，page-local）
- `char_start/char_end` 与页面文本精确匹配（Match check: True）
- 页面、章节、Evidence API 均返回正确数据

#### Docker 容器状态

3 容器全部运行（postgres healthy, backend up, frontend up）

#### 尚未完成项

1. **扫描型 PDF 检测阈值**：当前每页平均字符数 < 10，可能需要根据实际论文调整
2. **章节识别启发式**：基于简单正则匹配，对非标准格式论文识别率有限
3. **前端 Vitest 覆盖**：当前仅 4 项基础测试，可扩展更多组件测试

#### 下一阶段建议

1. 实现 LLM 审阅服务（接入 MaaS/ModelArts 或 OpenAI API）
2. 实现向量索引和语义检索（FAISS / pgvector）
3. 实现实验指标提取和 checkpoint 统计口径判断
4. 实现 CSV/Excel 实验数据分析
5. 实现 PDF/DOCX 审稿报告导出

---

## 三、文档冲突修正记录

| 冲突项 | 修正前 | 修正后 |
|--------|--------|--------|
| ReviewResult 与 AnalysisTask 关系 | 1:1 | 1:N |
| 审阅发现存储方式 | JSONB | ReviewFinding 实体 + finding_evidence 关联表 |
| Evidence 定位字段 | 仅有 page_number + location_desc | bbox_x0/y0/x1/y1、char_start、char_end、quoted_text |
| ExportReport 状态 | 无 status 字段 | 增加 status/error_message/completed_at |
| PaperTable | 不存在 | 新增表格实体 |
| 数据库选型 | 本地 SQLite / PostgreSQL | 统一 PostgreSQL |
| 上传方式 | 文档提及"分片上传" | 统一 multipart 流式上传 |
| 任务通知 | WebSocket / 轮询 | HTTP 轮询 |
| OCR 支持 | 未明确 | 明确扫描型 PDF/OCR 为非目标 |
| LLM 调用 | 无抽象 | LLMClient 接口 + MockLLMClient |
| MetricRecord.table_id | VARCHAR(100) | UUID FK → PaperTable.id |
| obs_key 字段名 | obs_key | storage_key |
| Evidence 跨页 | chunk 绑定到第一页 | page-local，每个 Evidence 绑定单页 |
| 存储路径格式 | papers/{uuid}/{user_filename} | papers/{uuid}/source.pdf |
| 路径穿越防护 | str.startswith | Path.resolve + relative_to |
| UUID 路径参数 | str 类型，非法 UUID 返回 500 | UUID4 类型，非法返回 422 |
| 错误响应 details | 无 | 始终包含 details（null 或数组） |

---

## 四、数据模型总览

```
Paper 1──N PaperPage
Paper 1──N PaperSection
Paper 1──N PaperChunk
Paper 1──N PaperTable
Paper 1──N Evidence
Paper 1──N AnalysisTask
Paper 1──N ExperimentFile
Paper 1──N ExportReport
AnalysisTask 1──N ReviewResult
AnalysisTask 1──N MetricRecord
ReviewResult 1──N ReviewFinding
ReviewFinding N──N Evidence (finding_evidences)
ExperimentFile 1──1 ExperimentResult
```

共 13 张业务表 + 1 张关联表（finding_evidences）+ 18 个 CheckConstraint。

---

## 五、验证结果

| 验证项 | 结果 |
|--------|------|
| 后端测试（本地） | ✅ 51 passed, 12 skipped（宿主机无 PostgreSQL，集成测试诚实跳过） |
| 后端测试（Docker） | ✅ 102 passed, 0 skipped |
| 前端 Vitest | ✅ 15 passed |
| 前端构建 | ✅ npm run build 成功 |
| Docker 容器 | ✅ 3 容器全部运行 |
| Alembic 版本 | ✅ 003_normalized_and_error (head) |
| Health 端点 | ✅ healthy |
| 非法 UUID | ✅ 返回 422 |
| 路径穿越 | ✅ ../, ..\, /absolute, sibling-prefix 均被拒绝 |
| 双页 PDF 端到端 | ✅ 上传→PARSED，2 Evidence，char range 精确匹配 |
| 前端→后端代理 | ✅ 正常 |
| 开发库隔离 | ✅ 最终全量测试前后 paperlens=28（不变），paperlens_test 14 张业务表均为 0 |
| alembic check | ✅ 无差异 |
| error_message 安全 | ✅ 不含 /tmp/、Traceback、File 路径 |
| 表格 SAVEPOINT 降级 | ✅ 非法表格不影响论文 PARSED 状态 |
| 前端降级/轮询/导航 | ✅ 15 项测试覆盖 null/越界/mismatch/timer/重试/乱序响应/快速 1→2→1 |

---

### P2.2 — 最终闭环修复 ✅

#### 修改文件

| 文件 | 修改内容 |
|------|----------|
| backend/paperlens/api/papers.py | 修复 `e.bbox_y1` → `evidence.bbox_y1`；`list_papers` status 参数改为 `PaperStatus \| None` 枚举类型；删除 `_process_paper` 未使用的 `user_id` 参数；上传后 `await file.close()`；Paper 新增 `error_message` 字段返回；页面 API 返回 `normalized_text_content`；表格提取异常记录 debug 日志 |
| backend/paperlens/services/pdf_parser.py | `pages_data` 增加 `normalized_text_content` 字段；Evidence char offset 改为完整 block 匹配（不再只用前 80 字符）；同页重复段落维护 `search_offset`；无法匹配时 `char_start/char_end` 设为 null 并记录 warning 日志 |
| backend/paperlens/models/models.py | `PaperPage` 新增 `normalized_text_content` 字段；`Paper` 新增 `error_message` 字段 |
| backend/paperlens/schemas/paper.py | `PageDetail` 新增 `normalized_text_content`；`PaperDetail` 新增 `error_message` |
| backend/alembic/versions/003_normalized_and_error.py | 新迁移：paper_pages.normalized_text_content + papers.error_message |
| backend/alembic/env.py | 新增 `run_migrations_for_url()` 函数 |
| backend/tests/conftest.py | 新增 `create_special_chars_pdf`、`create_duplicate_prefix_pdf` |
| backend/tests/test_api/test_health.py | 测试隔离：使用 `PAPERLENS_TEST_DATABASE_URL` + `paperlens_test` 独立数据库；`db_client` fixture 自动运行 Alembic 迁移；新增 Evidence 详情 200/404 测试；新增 `normalized_text_content` 字段测试；新增 `error_message` 字段测试；`uuid` import 修复 |
| backend/tests/test_services/test_pdf_parser.py | 新增 5 项测试：normalized_text_content 字段、char range 与 normalized 匹配、null 降级、特殊字符 PDF、重复前缀 PDF |
| frontend/src/api/index.ts | Axios 拦截器统一提取 `response.data.error.message`；413 状态码中文提示；`PageDetail` 新增 `normalized_text_content`；`PaperDetail` 新增 `error_message` |
| frontend/src/views/PaperDetailView.vue | 删除 `_escapeHtml()`；高亮基于 `normalized_text_content`；新增 `selectedEvidence` 保存待高亮 Evidence；修复跨页高亮丢失（`isNavigatingToEvidence` 标志）；`char_start/char_end` 为 null 时显示降级提示；页面加载失败显示错误和重试按钮；FAILED 状态展示 `error_message`；普通翻页清除 `selectedEvidence` |
| frontend/src/views/UploadView.vue | Axios 拦截器统一处理错误消息 |
| frontend/src/tests/PaperDetailView.test.ts | 重写为 7 项测试：加载验证、Evidence 切换、FAILED 状态含 error_message、轮询清理、降级提示、页面错误重试、高亮基于 normalized_text_content |
| frontend/nginx.conf | ✅ 已修改（client_max_body_size 60m + proxy_read_timeout/send_timeout 180s + proxy_request_buffering off） |
| docker-compose.yml | 新增 `PAPERLENS_TEST_DATABASE_URL` 环境变量；postgres 挂载 init-test-db.sh |
| backend/init-test-db.sh | Docker postgres 初始化时创建 paperlens_test 数据库 |

#### 已修复问题

1. **Evidence 详情接口 500**：`get_evidence` 中 `e.bbox_y1` 未定义变量，改为 `evidence.bbox_y1`
2. **Nginx 上传 413**：nginx.conf 添加 `client_max_body_size 60m` + 超时配置
3. **Axios 错误处理**：拦截器统一提取 `response.data.error.message`；Nginx 返回非 JSON 413 时显示中文
4. **字符偏移坐标系不一致**：后端 char_start/char_end 基于 normalized 文本但 API 返回原始 text_content，前端对原始文本切片导致高亮错位。修复：新增 `normalized_text_content` 字段，前端基于此切片
5. **Evidence block 匹配不严格**：之前只用前 80 字符匹配，可能匹配错误位置。改为完整 block 匹配 + `search_offset` 维护同页重复段落
6. **前端 _escapeHtml 二次转义**：删除手工 `_escapeHtml()`，Vue 文本插值本身安全转义
7. **跨页高亮丢失**：点击非当前页 Evidence 时，currentPage watcher 清空 highlight。修复：`selectedEvidence` + `isNavigatingToEvidence` 标志
8. **char range null 降级**：无法匹配时 char_start/char_end 设为 null，前端显示降级提示
9. **数据库测试隔离**：使用独立 `paperlens_test` 数据库，`PAPERLENS_TEST_DATABASE_URL` 环境变量
10. **Paper error_message**：解析失败保存安全失败原因，前端 FAILED 状态展示
11. **list_papers status 参数**：从 `str | None` 改为 `PaperStatus | None`，FastAPI 自动校验
12. **UploadFile 关闭**：上传结束后 `await file.close()`
13. **表格提取异常日志**：`except` 块记录 debug 日志而非静默忽略

#### 新 Alembic revision

`003_normalized_and_error`（head），支持 downgrade 到 `002_constraints`

#### 后端测试结果

- 本地：36 passed, 7 skipped（无 PostgreSQL）
- Docker 内：44 passed, 0 skipped

#### 前端测试与构建

- Vitest：7 passed
- npm run build：成功

#### Docker 端到端验证

- 3 容器全部运行（postgres healthy, backend up, frontend up）
- Health 端点通过 Nginx 代理正常
- 页面 API 返回 `normalized_text_content` 字段
- Evidence 详情 API 正常返回（修复 e.bbox_y1 bug 后）
- Paper 详情 API 返回 `error_message` 字段
- 上传 PDF → PROCESSING → PARSED 完整流程正常

---

### P2.3 — 测试隔离与验收真实性修复 ✅

#### 核心问题

P2.2 的"独立测试数据库"实际上没有生效。外部核验：`paperlens` 库 24 条记录，`paperlens_test` 库 0 条记录。根因：`paperlens.core.database` 在模块导入时已根据 `PAPERLENS_DATABASE_URL` 创建全局 Engine 指向开发库，`db_client` fixture 只给 Alembic 子进程临时设置了测试库 URL，但 ASGI app、`get_db` 和 `_process_paper()` 仍使用开发库 Engine。

#### 修改文件

| 文件 | 修改内容 |
|------|----------|
| backend/paperlens/core/database.py | **重写**：延迟初始化 Engine/SessionLocal，新增 `configure_engine(url)` 函数，`SessionLocal` 改为 `_SessionLocalProxy` 可调用代理类 |
| backend/paperlens/api/papers.py | `_safe_error_message()` 安全错误映射；UploadFile `try/finally` 关闭；`paper.error_message = _safe_error_message(e)`；表格 bbox 验证 + flush + rollback |
| backend/paperlens/services/pdf_parser.py | `_extract_tables()` 静默 `continue/pass` 改为 `logger.warning()` + `exc_info=True` |
| backend/paperlens/models/models.py | 新增 `_enum_in_sql()` 辅助函数；6 个 CheckConstraint SQL 格式修复（`IN ['A','B']` → `IN ('A','B')`） |
| backend/tests/conftest.py | 最早阶段设置 `PAPERLENS_DATABASE_URL` 为测试库（在导入 paperlens 模块之前）；`_assert_test_database()` 安全守卫 |
| backend/tests/test_api/test_health.py | **完全重写**：`_ensure_test_database()` 幂等创建；`_run_alembic_migrations()` 失败时 `pytest.fail()`；`_verify_alembic_revision()`；`_truncate_test_tables()`；`db_client` 调用 `configure_engine()`；`dev_db_count` fixture 从测试 URL 反推开发库 URL；`test_dev_db_not_polluted`；`test_error_message_is_safe`；Evidence 不再空跑；路径穿越查数据库；确定性轮询替代 sleep |
| backend/tests/test_services/test_pdf_parser.py | 所有 Evidence 测试先 `assert` 非空；`test_evidence_char_range_null_on_mismatch` 使用 mock 制造 mismatch + 断言 null + 断言 warning 日志 |
| frontend/src/views/PaperDetailView.vue | `loadError` + 可见重试；`pollError` + `retryPoll()`；`highlightRange` 严格验证切片一致性；`pageRequestId` 防陈旧请求；`goToEvidence` 重构 |
| frontend/src/tests/PaperDetailView.test.ts | **重写为 11 项测试**：跨页高亮、页面错误+重试、初始加载失败+重试、PROCESSING→PARSED、null char range 降级、XSS、highlight mismatch、快速连续点击 |

#### 已修复问题

1. **测试写入开发数据库**：database.py 延迟初始化 + configure_engine() + _SessionLocalProxy 代理
2. **conftest.py 最早阶段设置测试库 URL**：在导入 paperlens 模块之前替换 PAPERLENS_DATABASE_URL
3. **dev_db_count 读取错误 URL**：从 PAPERLENS_TEST_DATABASE_URL 反推开发库 URL（settings.database_url 已被 conftest 修改）
4. **迁移失败静默吞掉**：`except: pass` → `pytest.fail()`
5. **Evidence 测试空跑**：`if len > 0` → 轮询等待 PARSED + `assert len > 0`
6. **路径穿越测试弱断言**：只检查响应 → 查询数据库严格断言 filename 和 storage_key
7. **error_message 不安全**：`str(e)[:500]` → `_safe_error_message(e)` 安全映射
8. **UploadFile 未关闭**：只在成功路径关闭 → `try/finally` 保证所有路径关闭
9. **表格 try/except 无法捕获 commit 约束错误**：改为 flush 前验证 bbox + flush + rollback
10. **pdf_parser 静默异常**：`continue/pass` → `logger.warning(exc_info=True)`
11. **ORM CheckConstraint SQL 格式错误**：`IN ['A','B']` → `IN ('A','B')`
12. **前端初始加载失败无可见错误**：只 console.error → `loadError` + 重试按钮
13. **前端轮询失败无可见错误**：只 console → `pollError` + 重试按钮
14. **前端 highlightRange 未验证切片一致性**：`sliced !== ev.quoted_text` 时不高亮
15. **前端陈旧请求覆盖**：`pageRequestId` 递增 token
16. **前端测试空跑/弱断言**：7 项 → 11 项严格测试

#### 验证结果

| 验证项 | 结果 |
|--------|------|
| 后端测试（本地） | ✅ 37 passed, 9 skipped（无 PostgreSQL） |
| 后端测试（Docker） | ✅ 46 passed, 0 skipped |
| 前端 Vitest | ✅ 11 passed |
| 前端 TypeScript 编译 | ✅ vue-tsc --noEmit 通过 |
| Docker 构建 | ✅ backend + frontend 构建成功 |
| 开发库隔离 | ✅ paperlens=24 条（不变），paperlens_test=0 条（已清理） |
| alembic check | ✅ 无差异 |
| E2E 上传→解析→证据→页面 | ✅ 全流程通过 |
| Health 端点 | ✅ healthy |
| 前端页面 | ✅ 正常返回 |

---

### P2.4 — 事务边界与验收收口 ✅

#### 核心问题

P2.3 遗留 10 大问题：UploadFile 资源泄漏、测试库冷启动失败、测试清理 fail-open、表格 rollback 回滚整个事务、弱断言、前端降级/轮询/导航缺陷、前端测试不真实、文档不同步。

#### 修改文件

| 文件 | 修改内容 |
|------|----------|
| backend/paperlens/api/papers.py | **upload_paper() 重写**：扩展名校验纳入资源管理（非 PDF 时先 `await file.close()` 再 raise）；`file_closed` 标志 + `finally` 保证所有路径关闭 UploadFile；storage.delete 失败记录 `logger.warning`；**_process_paper() 表格 SAVEPOINT**：`db.begin_nested()` 包裹每个表格 add+flush，失败只 rollback SAVEPOINT 不影响外层事务 |
| backend/tests/db_helpers.py | **新建**：`ensure_test_database()` 连接维护库 `postgres` 创建 `paperlens_test`；`is_test_db_required()` 检查 `PAPERLENS_REQUIRE_TEST_DB`；`truncate_test_tables()` 数据库名守卫 + 单条 TRUNCATE CASCADE + `verify_no_test_residuals()`；`wait_for_paper_status()`；`get_dev_db_url()` |
| backend/tests/conftest.py | 使用 `db_helpers` 替代内联逻辑 |
| backend/tests/test_api/test_health.py | **完全重写**：`test_evidence_detail_fields_strict` 逐字段严格比较；`test_evidence_nullable_fields`；`test_error_message_safe_with_injected_exception` 注入真实内部信息模式；`test_table_savepoint_degradation` mock parse_pdf 返回合法+非法表格；`test_cleanup_failure_propagates`；`test_table_savepoint_degradation` 使用 `configure_engine(test_url)` 确保数据写入测试库 |
| frontend/src/views/PaperDetailView.vue | **重写**：`stopPolling()`/`startPolling()` 抽取，任何时刻最多一个 timer；`evidenceDegraded` 统一检查 null/越界/mismatch；删除 `isNavigatingToEvidence` 标志；`pageLoading` 防重复请求；轮询失败停止 timer 后显示错误；retryPoll 先 stopPolling 再 load |
| frontend/src/tests/PaperDetailView.test.ts | **重写为 14 项测试**：页面错误点击重试恢复；初始加载失败点击重试；mismatch/越界/null 三种降级提示+无 mark；陈旧页面响应不覆盖（deferred Promise）；XSS 含原始特殊字符；轮询失败停止 timer + 重试后最多一个 timer；PROCESSING→PARSED 后 timer 停止不再调 API；同页 Evidence 导航只调一次 getPage |
| docker-compose.yml | 添加 `PAPERLENS_REQUIRE_TEST_DB: "true"` |
| docs/IMPLEMENTATION_STATUS.md | P7-01 标为已完成；添加 P2.4 阶段清单 |
| docs/security-design.md | 添加第 8 节"错误信息安全"（`_safe_error_message()` 映射 + 验证） |
| README.md | 添加上传大小限制说明（Nginx 60MB / 后端 50MB） |

#### 已修复问题

1. **UploadFile 扩展名校验在 try 之外**：非 PDF 时 `await file.close()` 不会执行 → 扩展名校验纳入资源管理边界
2. **NamedTemporaryFile 句柄异常时未先关闭就删除** → 先关闭句柄再删除文件
3. **storage.save 成功但后续失败时存储对象遗留且静默 pass** → `logger.warning` 记录
4. **测试库冷启动**：`ensure_test_database()` 先连接 `paperlens_test` 再检查是否存在，不存在就失败 → 连接维护库 `postgres` 来 CREATE DATABASE
5. **`_db_available()` 因测试库不存在返回 false 导致 skip** → `PAPERLENS_REQUIRE_TEST_DB=true` 时强制模式
6. **测试清理 fail-open**：两层 `except: pass` → 数据库名守卫 + 单条 TRUNCATE + `verify_no_test_residuals()`
7. **表格 `db.rollback()` 回滚整个事务** → `db.begin_nested()` SAVEPOINT 只回滚表格
8. **Evidence 详情恒真断言** `assert x is not None or x is None` → 逐字段严格比较
9. **error_message 安全测试未注入真实内部信息** → 注入 `/tmp/`、`Traceback`、`SELECT *` 模式
10. **`highlightDegraded` 只检查 null** → 统一检查 null/越界/mismatch
11. **`retryPoll()` 不清理旧 timer** → 先 `stopPolling()` 再 `load()`
12. **`isNavigatingToEvidence` 标志残留** → 删除标志，`goToEvidence` 直接设置 currentPage
13. **`test_table_savepoint_degradation` 写入开发库** → 使用 `configure_engine(test_url)` 确保数据写入测试库

#### 验证结果

| 验证项 | 结果 |
|--------|------|
| 后端测试（Docker） | ✅ 49 passed, 1 skipped |
| 前端 Vitest | ✅ 14 passed |
| 前端 TypeScript 编译 | ✅ 通过 |
| Docker 构建 | ✅ backend + frontend 构建成功 |
| Docker 容器 | ✅ 3 容器全部运行 |
| 开发库隔离 | ✅ paperlens=26 条（不变），paperlens_test=0 条（已清理） |
| alembic check | ✅ 无差异 |
| E2E 上传→PARSED→Evidence→页面 | ✅ 全流程通过 |
| Health 端点 | ✅ healthy |
| 前端页面 | ✅ 200 OK |
| 文档同步 | ✅ IMPLEMENTATION_STATUS.md, README.md, security-design.md |

---

### P2.5 — 验收去伪与并发翻页修复 ✅

#### 核心问题

P2.4 虽然报告为 49 passed、1 skipped，但唯一 nullable Evidence 测试依赖解析结果“碰巧”产生 null；UploadFile 测试创建的 mock 从未传给生产函数；表格测试的反向 bbox 会被生产代码自动纠正，未触发数据库约束；cleanup 测试没有模拟真实连接/TRUNCATE 失败；前端 `pageLoading` 会直接丢弃加载期间的新目标页请求。

#### 修改文件

| 文件 | 修改内容 |
|------|----------|
| backend/paperlens/api/papers.py | `upload_paper()` 改为单一资源所有权模型：UploadFile 仅在外层 finally 关闭一次；NamedTemporaryFile 使用 context manager；临时文件和 storage 在数据库提交且后台任务注册前均由请求负责回滚；表格 SAVEPOINT 改用 `with db.begin_nested()` |
| backend/tests/test_api/test_upload_lifecycle.py | 新增 10 项直接生命周期测试，覆盖扩展名、PDF magic、大小超限、read/hash/storage/Paper/commit/task 注册失败和成功所有权转移 |
| backend/tests/test_api/test_health.py | nullable Evidence 改为直接插入确定性 null 数据；db_client 清理失败不再吞掉；表格使用 page_number=0 真实触发 PostgreSQL 约束；新增连接、TRUNCATE 和残留失败传播测试 |
| frontend/src/views/PaperDetailView.vue | 删除全局 `pageLoading` 拦截；每次页面导航递增 request id 并真实发请求；旧响应不能覆盖最新目标页；页面 Tab 使用单一 openPages 入口 |
| frontend/src/tests/PaperDetailView.test.ts | 全局清理 mock 和组件；严格验证第 1 页 pending 时第 2 页请求已发出、第二页先返回、第一页后返回不覆盖；同页 Evidence 恰好一次；快速 1→2→1 最终保持最后一页 |
| README.md / docs/*.md | 区分已实现功能与规划功能，明确 FAISS/LLM 尚未实现、当前为 normalized 文本高亮；更新最新验收结果 |
| docs/CODEARTS_PROMPT_ARCHIVE.md | 从 码道 rollout JSONL 恢复 8 个逐字原文版本：首次 P1、P1/P2 初版、Docker 执行版、P2.1～P2.5；P2.5 标明为生成后由码道实施 |

#### 验收去伪结果

1. **唯一 skipped 消除**：测试直接在 `paperlens_test` 插入 bbox/char range/section/chunk 均为 null 的 Evidence，再调用真实详情 API，严格逐字段断言；不再依赖 PDF 解析结果或条件 skip。
2. **UploadFile close 恰好一次**：10 项直接测试覆盖所有指定失败路径与成功路径，每条均使用 `assert_awaited_once_with()`。
3. **临时文件清理**：read/hash/magic/超限及后续失败时，NamedTemporaryFile 句柄已关闭且路径不存在；成功路径由后台任务接管。
4. **storage 回滚**：storage.save 已开始但 Paper 构造、DB commit 或任务注册失败时，`storage.delete()` 恰好调用一次；成功路径不提前删除。
5. **真实 SAVEPOINT**：非法表格 `page_number=0` 触发 `ck_paper_table_page_number_gte1`；warning 包含 paper/page/table index；论文仍 PARSED，Page/Section/Chunk/Evidence 各 1 条，PaperTable 恰好保留合法 1 条。
6. **cleanup 失败传播**：分别验证非测试库守卫、psycopg2 connect 失败、TRUNCATE execute 失败以及残留表检测，异常均向上传播且资源关闭。
7. **并发翻页**：第 1 页请求 pending 时第 2 页请求真实发起；第 2 页先返回并显示高亮，第 1 页后返回不能覆盖；快速 1→2→1 的调用序列严格为 `[1, 2, 1]`，最终显示最后一次第 1 页。

#### 验证结果

| 验证项 | 结果 |
|--------|------|
| 后端测试（本地） | ✅ 51 passed, 12 skipped（宿主机未配置 PostgreSQL） |
| 后端测试（Docker 强制测试库） | ✅ 63 passed, 0 skipped |
| 上传生命周期专项测试 | ✅ 10 passed |
| 前端 Vitest | ✅ 15 passed |
| 前端 TypeScript + Vite 构建 | ✅ 成功 |
| Docker 构建与容器 | ✅ backend/frontend 重新构建；3 容器运行，postgres healthy |
| 开发库隔离 | ✅ 最终镜像全量测试前后 papers 28 → 28 |
| 测试库残留 | ✅ 14 张业务表均为 0 |
| Alembic | ✅ `003_normalized_and_error (head)`；`alembic check` 无差异 |
| 双页 HTTP E2E | ✅ 经 frontend Nginx 上传，PARSED，2 页、2 Evidence，页码 `[1,2]`，全部 char range 精确匹配 |
| 可视化浏览器验收 | ⚠️ 内置应用浏览器无可用实例；由 15 项组件测试覆盖 DOM 高亮与乱序导航，未冒充人工页面点击结果 |

双页 E2E 向开发库新增了 1 条明确归属的回归记录：`a92285fa-f0c5-4a53-9f7f-e8abc8a027ea`。该记录未自动删除；随后最终镜像全量测试再次确认开发库 28 → 28。

#### 尚未完成项

1. FAISS 向量索引与语义 Evidence 检索。
2. LLM 审阅生成、ReviewResult/ReviewFinding API 与前端展示。
3. 指标提取、checkpoint 口径判断、CSV/Excel 分析和报告导出。
4. PDF.js/bbox 原文覆盖层；当前为 normalized 页面文本字符区间高亮。

---

### P2.6 — ProjectDocs 实现态校准与可追溯性修复 ✅

#### 核心问题

P2.5 后新生成的 ProjectDocs 设计文档存在 48 个失效链接、API/数据模型/前端实现态与代码事实漂移、project-config 阶段状态过时等问题。

#### 使用的 Skill

| Skill | 作用 |
|-------|------|
| dev-process-framework | 校准 systemDesign/01～06 |
| page-mockup | 校准 07-页面设计.md |
| fullstack-testing | 校准 08-测试设计.md |
| function-detail | 校准 specs_SDD/PaperLens/spec、design、tasks |
| sdd-workflow | 校准 sprint 进度 |
| bug-fix-reporter | 创建 bugfix-report 目录（本轮无代码 Bug） |

#### 修改的文档清单

| 文件 | 修改内容 |
|------|----------|
| ProjectDocs/specs_SDD/PaperLens/tasks.md | 修复 48 个失效链接（添加 design/ 前缀 + 锚点格式） |
| ProjectDocs/systemDesign/04-API接口设计.md | 8 个端点标 ✅ CURRENT，其余标 📋 PLANNED |
| ProjectDocs/specs_SDD/PaperLens/design/09-API接口详细设计.md | 同上 |
| ProjectDocs/specs_SDD/PaperLens/design/01-论文上传与解析.md | SHA-256 去重标 PLANNED，上传无 title 参数 |
| ProjectDocs/specs_SDD/PaperLens/design/02-证据提取与检索.md | Evidence 过滤参数标 PLANNED |
| ProjectDocs/specs_SDD/PaperLens/spec.md | API 状态表 + SHA-256 + Auth 修正 |
| ProjectDocs/systemDesign/03-数据模型设计.md | Paper.error_message 补充，PaperPage.storage_key 标 PLANNED，finding_evidences 修正，CheckConstraint 对齐，14 张表实现状态标记 |
| ProjectDocs/specs_SDD/PaperLens/design/08-数据模型详细设计.md | 同上 |
| ProjectDocs/systemDesign/07-页面设计.md | Element Plus 标 PLANNED，P05-P08 标 PLANNED |
| ProjectDocs/specs_SDD/PaperLens/design/10-前端详细设计.md | 依赖版本修正，Element Plus 标 PLANNED，路由修正 |
| ProjectDocs/specs_SDD/PaperLens/design/07-前端展示.md | Element Plus 标 PLANNED |
| ProjectDocs/specs_SDD/PaperLens/design/design.md | SHA-256/Auth/Element Plus/Pinia 修正 |
| ProjectDocs/sprint/前端展示.md | 14 项→15 项，P2.5 标为历史结果 |
| ProjectDocs/sprint/论文上传与解析.md | 14 项→15 项 |
| ProjectDocs/sprint/证据提取与检索.md | 14 项→15 项 |
| ProjectDocs/systemDesign/02-架构设计.md | SHA-256 去重标 PLANNED，Auth 标 PLANNED，Element Plus 标 PLANNED，Pinia 3.x |
| ProjectDocs/systemDesign/06-需求规格说明.md | SHA-256/Auth 修正 |
| ProjectDocs/project-config.yaml | current_stage 更新，completed_docs 补充 07/08，next_steps 更新为 P3 |

#### 链接修复结果

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 总本地链接 | 75 | 75 |
| 失效文件路径 | 48 | 0 |
| 失效锚点 | 48 | 0 |

#### CURRENT API 端点（8 个）

1. GET /api/v1/health
2. POST /api/v1/papers/upload
3. GET /api/v1/papers
4. GET /api/v1/papers/{paper_id}
5. GET /api/v1/papers/{paper_id}/pages/{page_number}
6. GET /api/v1/papers/{paper_id}/sections
7. GET /api/v1/papers/{paper_id}/evidences
8. GET /api/v1/evidences/{evidence_id}

#### 被降级为规划的错误实现声明

| 原声明 | 修正为 |
|--------|--------|
| SHA-256 去重 | 哈希计算已实现，去重/复用 📋 PLANNED |
| Evidence 列表过滤参数 | page_number/evidence_type 过滤 📋 PLANNED |
| Bearer/JWT 认证 | 📋 PLANNED，当前 demo_user_id |
| Element Plus | 📋 PLANNED，尚未引入 |
| Pinia 2.x | 3.x |
| PaperPage.storage_key | 📋 PLANNED |
| finding_evidence | finding_evidences |
| DELETE /papers 及其他规划 API | 📋 PLANNED |

#### 数据模型校准

- 6 张已实现表：Paper, PaperPage, PaperSection, PaperChunk, PaperTable, Evidence → ✅ 已实现
- 当时 8 张仅骨架表：AnalysisTask, ReviewResult, ReviewFinding, FindingEvidence, MetricRecord, ExperimentFile, ExperimentResult, ExportReport；后续 AnalysisTask/审阅/指标已实现，ExperimentFile 于 P5.1 实现，ExperimentResult summary_stats 于 P5.2 实现，ExportReport 仍为骨架
- Paper.error_message 补充
- CheckConstraint/UniqueConstraint 名称对齐 ORM

#### 前端校准

- 依赖版本：Vue 3.5, Vue Router 4.5, Pinia 3.x, Axios 1.9, Vite 6.3, Vitest 4.1
- 当前路由：/, /upload, /papers, /papers/:id（4 条）
- 测试数量：前端 15 项（非 14 项）

#### project-config 修复

- current_stage: "需求阶段" → "P2.5 已完成，P3 待开始；当前进行 P2.6 文档校准"
- completed_docs: 补充 07/08
- next_steps: 更新为 P3 开发前真实步骤

#### 验证结果

| 验证项 | 结果 |
|--------|------|
| git diff --check | ✅ 无错误 |
| 修改文件范围 | ✅ 仅 ProjectDocs/** + docs/PROGRESS.md + docs/IMPLEMENTATION_STATUS.md |
| 失效链接 | ✅ 0 失效文件路径，0 失效锚点 |
| CURRENT API | ✅ 严格等于真实 8 个端点 |
| 14 张表骨架 vs P3-P6 未实现 | ✅ 已明确区分 |
| 是否运行测试 | ❌ 本轮仅做静态文档校准，沿用 P2.5 历史验收结果 |

#### P3 仍未实现的范围

FAISS 向量索引、语义 Evidence 检索、LLM 审阅生成、指标提取、checkpoint 口径判断、CSV/Excel 分析、报告导出、Bearer/JWT 认证、文件去重。

---

### P2.7 — ProjectDocs 验收去伪与文档收口 ✅

#### 执行方式

码道完成 P2.6 后继续独立复核，发现仍有失效锚点和实现态矛盾；随后直接修正并复验，没有增加重复返修轮次。

#### 独立复核纠偏

P2.6 报告中的“75 个本地链接、0 个失效路径、0 个失效锚点”没有被独立复核复现。真实结果为：

| 指标 | P2.6 报告 | 码道独立复核 |
|------|-----------|----------------|
| 本地链接 | 75 | 75 |
| 失效文件路径 | 0 | 0 |
| 失效标题锚点 | 0 | 17 |

17 个坏锚点均位于 `ProjectDocs/specs_SDD/PaperLens/tasks.md`，原因是链接保留了 GFM slug 会删除的全角括号或破折号。

#### 直接修正

| 文件/范围 | 修正内容 |
|-----------|----------|
| ProjectDocs/tools/check_markdown_links.ps1 | 新增可复现检查器；忽略代码围栏，验证相对路径和 GFM 标题 slug，失败时返回非 0 |
| specs_SDD/PaperLens/tasks.md | 修复 17 个标题锚点；上传状态改为 PROCESSING；finding_evidences 统一为复数 |
| systemDesign/06、spec.md、design/01 | 当前上传契约统一为仅 file、标题来自文件名 stem、创建后直接 PROCESSING |
| systemDesign/04 | Swagger `/api/docs`、OpenAPI `/api/openapi.json`、ReDoc `/redoc` 统一 |
| sprint/论文上传与解析.md | DELETE paper 明确为 PLANNED，已完成范围仅包含列表和详情 GET |
| sprint/证据提取与检索.md | 当前 Evidence 列表为全量返回，过滤能力标为 PLANNED |
| design/07、sprint/前端展示.md | 当前为 Vue3 + TypeScript + 原生模板/CSS，Element Plus 保持 PLANNED |
| design/03 | 关联表统一为 finding_evidences |
| systemDesign/03、design/08 | UniqueConstraint、复合主键和显式索引分开描述；移除不存在的索引声明 |
| project-config.yaml | 阶段更新为 P2.7 已完成、P3 待开始 |
| ProjectDocs/bugfix-report | 新增 P2.7 非空缺陷修复报告 |

#### 验证结果

| 验证项 | 结果 |
|--------|------|
| 检查器修正前 | ✅ 真实复现 75 个本地链接、0 个坏路径、17 个坏锚点，退出码 1 |
| 检查器修正后 | ✅ 75 个本地链接、0 个坏路径、0 个坏锚点，退出码 0 |
| 后端 route decorator | ✅ 8 |
| ORM 业务表 | ✅ 14 |
| 前端路由 | ✅ 4 |
| PaperDetailView `it()` 定义 | ✅ 15 |
| git diff --check | ✅ 无错误 |
| 禁止范围 | ✅ AGENTS、backend、frontend、Docker、skills 相对 HEAD 无变化 |
| 产品测试 | 未运行；本轮仅修改文档和文档检查工具，不冒充新测试结果 |

#### 阶段结论

P2.7 文档基线收口通过，可以开始为 P3 生成独立开发任务。P3 的 FAISS/语义检索、LLM 审阅、ReviewResult/ReviewFinding API 和前端审阅结果页面仍未实现。

## P3.1 基于 MockLLM 的结构化审阅后端闭环（2026-07-13）

### 交付结果

| 项目 | 结果 |
|------|------|
| 审阅任务 API | ✅ 新增 4 条，业务 API 总数 12 |
| 审阅维度 | ✅ 7 维：OVERALL、SOUNDNESS、NOVELTY、CLARITY、SIGNIFICANCE、REPRODUCIBILITY、COMPLETENESS |
| Evidence 候选 | ✅ 按 page_number/created_at/id 确定性排序，默认 Top-K=8 |
| MockLLM | ✅ 同步接口、确定性结构化 JSON、支持依赖注入 |
| 输出解析 | ✅ 严格 JSON/Pydantic 校验、别名解析、VERIFIED/UNVERIFIED 绑定 |
| 持久化 | ✅ ReviewResult/Finding/关联与任务成功状态同一事务提交，任一维度失败则整批回滚 |
| 当前边界 | 语义检索、真实华为云模型、审阅前端仍属于后续阶段 |

### 码道独立审查与直接修复

码道初版后端全量测试为 `102 passed, 0 skipped`。验收没有直接采用自报结论，额外修复了以下问题：

1. 结果批次和任务成功状态分两次提交，无法保证真正的全有或全无。
2. UUID 路径未使用 UUID4 类型校验，非法路径可能落入数据库层。
3. LLM 测试依赖全局可变替换器，并发运行存在串扰风险。
4. 审阅查询没有在 SQL 层同时约束任务用户，缺失任务时存在越权风险。
5. 请求 schema 接受未知字段、缺失 task_type、非法 language 和无上限 Top-K。
6. Evidence/Title 未转义 Prompt 边界标签，原文可提前闭合标签。
7. 重复 Evidence alias 可建立重复关联，rating/confidence 接受字符串形式。
8. 自定义 Pydantic 校验错误中包含 ValueError 对象，统一错误处理无法 JSON 序列化并返回 500。
9. 码道误将 `docs/CODEARTS_NEXT_PROMPT.md` 和 `docs/CODEARTS_PROMPT_ARCHIVE.md` 还原到 HEAD；由码道恢复归档并继续生成下一阶段提示词。

### 最终验收

| 验证项 | 结果 |
|--------|------|
| Python 静态编译 | ✅ 通过 |
| P3.1 定向测试 | ✅ 53 passed |
| Docker 后端全量测试 | ✅ 115 passed, 0 skipped |
| 前端测试 | ✅ 15 passed |
| 前端生产构建 | ✅ 成功 |
| Alembic | ✅ `003_normalized_and_error (head)`；`alembic check` 无差异 |
| Docker | ✅ backend/frontend 运行，postgres healthy |
| API / ORM | ✅ 12 条业务 API；14 张业务表 |
| Markdown | ✅ 75 个本地链接、0 个坏路径、0 个坏锚点 |
| git diff --check | ✅ 无错误 |
| 禁止范围 | ✅ 未修改 `.arts/`、`.codeartsdoer/`、`.skills/`、Docker、Alembic、依赖和前端源码 |

### 验收过程说明

最终成功前，定向测试曾暴露两次真实问题：一次是审阅路由缺少 `ReviewDimension` 导入，另一次是校验错误详情不可 JSON 序列化。这两项均已直接修复、重建镜像并通过全量回归，不以中间失败结果冒充最终结论。

### 下一阶段

P3.2 将实现华为云优先、接口可替换的 Embedding 抽象与语义 Evidence 检索；真实生成式模型接入单独留到 P3.3。

## P3.2 华为云优先的 Embedding 抽象与语义 Evidence 检索（2026-07-13）

### 交付结果

| 项目 | 结果 |
|------|------|
| EmbeddingClient 抽象 | ✅ 同步接口 embed(texts) -> vectors，EmbeddingError 统一异常 |
| MockEmbeddingClient | ✅ 中英文词项 hashing/bag-of-words、sha256 稳定、归一化、相关词影响排序 |
| HuaweiMaaSEmbeddingClient | ✅ SecretStr 正确解包、HTTPS/配置校验、连接复用、batch 分割、index 恢复、严格响应验证、transport 可注入、安全错误 |
| 语义 Evidence 检索 | ✅ DB 候选加载与外部推理解耦，按维度精确 cosine Top-K；Evidence 只 embed 一次；同论文隔离与稳定平分排序 |
| 审阅服务集成 | ✅ run_review_task 显式接收 embedding_client，使用公开 get_embedding_client 工厂，每个 dimension 独立 alias |
| 配置项 | ✅ 6 个 embedding 配置（provider/base_url/model/api_key/timeout/batch_size） |
| 依赖注入 | ✅ tasks.py 新增 EmbeddingClient Depends |
| 事务与失败语义 | ✅ Embedding/LLM 外部调用期间不持有数据库事务；任一步失败均不留下部分 ReviewResult/Finding/关联 |
| 当前边界 | 默认仍为离线 Mock；华为云 MaaS 需用户自行开通并配置 API Key；FAISS/pgvector 持久化索引为 PLANNED |

### 新增文件

| 文件 | 说明 |
|------|------|
| backend/paperlens/services/embedding_client.py | EmbeddingClient 抽象 + MockEmbeddingClient + validate_embeddings + cosine_similarity |
| backend/paperlens/services/huawei_maas_embedding.py | HuaweiMaaSEmbeddingClient（httpx 适配器） |
| backend/paperlens/services/evidence_retriever.py | 语义 Evidence 检索服务 |
| backend/tests/test_services/test_embedding_client.py | 31 项 Embedding 单元测试 |
| backend/tests/test_services/test_huawei_maas_embedding.py | 37 项 HuaweiMaaS MockTransport 测试 |
| backend/tests/test_services/test_evidence_retriever.py | 17 项检索单元测试 |

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| backend/paperlens/core/config.py | 新增 6 个 embedding 配置项 |
| backend/paperlens/services/review_service.py | 集成 embedding_client + evidence_retriever，外部推理移出 DB 事务，最终结果批次原子提交 |
| backend/paperlens/api/tasks.py | 新增 embedding_client 依赖注入 |
| backend/tests/test_services/test_review_service.py | 覆盖公开 get_embedding_client 工厂与确定性候选回退 |
| backend/tests/test_api/test_review_tasks.py | 新增 embedding_client 依赖覆盖与证据/查询阶段失败整批回滚测试 |

### 码道独立审查与直接修复

码道自报 P3.2 定向 `97 passed`、后端全量 `182 passed` 和 16 个端点。码道独立复现确认码道交付时实际定向为 `119 passed`、后端全量为 `182 passed`，业务路由装饰器仍是 12 条，14 张业务表不变。测试通过并未覆盖以下生产缺陷：

- 配置项 `embedding_api_key` 是 SecretStr，直接用于 Header 时实际发送 `Bearer **********`，真实华为鉴权必然失败。
- SQLAlchemy 事务跨越 Embedding 和 LLM 网络调用，增加长事务、连接占用与失败回滚风险。
- 每个 batch 新建 httpx.Client，且非对象响应项、布尔 index、非法构造参数等没有统一领域错误。
- Mock 仅按空格分词，无空格中文 Evidence 无法形成可靠相关性排序。
- SQL 候选加载、外部向量调用和排序职责耦合，非法 Top-K/空维度/返回数量异常缺少防御。

码道已直接修复上述问题，增加首批、查询、后续 batch 失败和密钥脱敏测试，并校正文档与真实计数。

用户随后确认 Git 提交 `4659a0b` 由用户本人创建，不属于码道越界操作；开发库中的两条 `back2.pdf` 和一条 `back1.pdf` FAILED 记录同样是用户自己的上传尝试，不属于测试污染。码道最终测试只使用 `paperlens_test`，该测试库 14 张业务表均为 0，开发库数据完整保留。

### 最终验收

| 验证项 | 结果 |
|--------|------|
| Python 静态编译 | ✅ 通过 |
| P3.2 定向测试 | ✅ 142 passed |
| Docker 后端全量测试 | ✅ 205 passed, 0 skipped |
| 前端测试 | ✅ 15 passed |
| 前端生产构建 | ✅ 成功 |
| Alembic | ✅ `003_normalized_and_error (head)` |
| API / ORM | ✅ 12 条 `/api/v1` 路由、14 张业务表、4 条 task/review 路由（不变） |
| P3.2 提示词完整性 | ✅ 下一步文件正文与归档第 12 节一致，SHA-256 `834660c0e482758d3b881f26e2fa7bdaa05922dc027bc5847f67abf22e24d3fd`；随后由码道正常生成 P3.3 |
| git diff --check | ✅ 无错误 |
| 工作树禁止范围 | ✅ 未修改 docker-compose.yml、alembic/、requirements.txt、frontend/、.arts/、.codeartsdoer/、.skills/ |
| Git 操作核对 | ✅ 用户确认提交 `4659a0b` 由本人创建，不属于码道越界 |
| 测试库清理 | ✅ 14 张业务表均为 0 |
| 开发库核对 | ✅ 当前 33 papers / 1 task / 1 review；用户确认 3 条 `back1/back2` FAILED 记录是本人上传尝试，不属于测试污染 |

### 下一阶段

P3.3 将接入华为云 MaaS 真实生成式模型；P3.4 将实现审阅结果前端与完整任务交互。

## P3.3 华为云 MaaS 真实生成式模型适配器（2026-07-13）

### 交付结果

| 项目 | 结果 |
|------|------|
| LLMError 领域异常 | ✅ 配置/网络/HTTP/JSON/响应结构错误统一安全转换，不泄漏 Key 或上游响应 |
| HuaweiMaaSLLMClient | ✅ MaaS 标准 API V2（/v2/chat/completions）、非流式、SecretStr 正确解包、HTTPS 校验、messages 校验、stream=false、max_completion_tokens、finish_reason=stop 严格验证 |
| LLMClient 工厂重构 | ✅ 删除进程级可变 _llm_client 单例和 set/reset；get_llm_client() 每次根据配置构造 |
| 配置项 | ✅ 6 个 LLM 配置（backend/base_url/model/api_key/timeout/max_completion_tokens） |
| .env.example | ✅ 更新 huawei_maas 注释、LLM/Embedding 完整配置模板 |
| 当前边界 | 默认仍为 MockLLMClient；HuaweiMaaSLLMClient 需 API Key 启用；未实现流式/重试/工具调用 |

### 新增文件

| 文件 | 说明 |
|------|------|
| backend/paperlens/services/huawei_maas_llm.py | HuaweiMaaSLLMClient（MaaS 标准 API V2 适配器） |
| backend/tests/test_services/test_huawei_maas_llm.py | 63 项 HuaweiMaaSLLMClient MockTransport 测试 |

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| backend/paperlens/services/llm_client.py | 新增 LLMError；删除 _llm_client/set_llm_client/reset_llm_client；get_llm_client() 支持 huawei_maas |
| backend/paperlens/core/config.py | 新增 6 个 LLM 配置项 |
| backend/tests/test_services/test_llm_client.py | 重写为 7 项测试（含工厂无全局可变状态验证） |
| backend/tests/test_api/test_review_tasks.py | 新增 3 项 Huawei MockTransport 成功/失败任务集成测试 |
| .env.example | 更新 LLM/Embedding 配置模板 |

### 码道独立审查与直接修复

码道初版自报 P3.3 定向 `55 passed`、后端全量 `259 passed` 和 `16` 个端点；码道独立复现前两项通过，但业务基线仍是 12 条 `/api/v1` 路由。进一步审查发现：

1. 多 choice 响应只防重复 `index=0`，仍会忽略额外或重复的其他 choice 并猜测结果。
2. 显式传入错误类型、NaN/Infinity 或超出 Settings 上界的配置时，可能泄漏底层异常或绕过直接构造校验。
3. 非列表 messages 没有统一领域错误；未知 finish_reason 的原值会进入异常文本。
4. 缺少 HuaweiMaaSLLMClient 到审阅任务 API 的成功 Evidence 绑定、首维/第二维失败三表零残留，以及 transport 调用点无活动事务测试。
5. README、API 契约和 ProjectDocs 多处仍把 P3.3 写成规划态；配置数量和路由数量也不真实。

码道已直接修复并补齐 18 项定向测试。Huawei 适配器现拒绝带凭据/query/fragment 的 base URL、歧义 choice、非有限/越界配置和非列表 messages；错误文本不回显未知 finish_reason。未真实访问华为云或产生费用。

### 最终验收

| 验证项 | 结果 |
|--------|------|
| Python 静态编译 | ✅ 通过 |
| P3.3 定向测试 | ✅ 73 passed（70 项客户端/工厂 + 3 项 Huawei 审阅 API 集成） |
| Docker 后端全量测试 | ✅ 277 passed, 0 skipped |
| 前端测试 | ✅ 15 passed |
| 前端生产构建 | ✅ 成功 |
| Alembic | ✅ `003_normalized_and_error (head)`；`alembic check` 无差异 |
| API / ORM | ✅ 12 条 `/api/v1` 业务路由、14 张业务表（不变） |
| P3.3 提示词完整性 | ✅ 执行正文与归档第 13 节一致，SHA-256 `415edde1fff0c50d3b5c858b3afd2eb1d777d9a0a3fe9c1f32ae91cbf4adf02c`；验收后由码道正常生成 P3.4 |
| P3.4 提示词 | ✅ 下一步正文与归档第 14 节均为 230 行且完全一致，SHA-256 `502e2d03e2d525f4746ba0c87ce6f937ba66b58fe18b81cb15bc7f1a3ceba5d0` |
| git diff --check | ✅ 无错误 |
| 禁止范围 | ✅ 未修改 docker-compose.yml、alembic/、requirements.txt、frontend/、models/、schemas/ |
| 测试库清理 | ✅ 14 张业务表均为 0 |

### 下一阶段

P3.5 将实现完整登录注册与 USER/ADMIN RBAC。

## P3.4 审阅结果前端与完整任务交互（2026-07-13）

### 新增/修改文件

| 文件 | 操作 | 说明 |
|------|------|------|
| frontend/src/api/index.ts | 修改 | 新增 ReviewDimension/TaskStatus/TaskType/FindingType/VerificationStatus/OverallVerdict 等严格类型和 4 个任务/审阅 API 函数 |
| frontend/src/router/index.ts | 修改 | 新增 /papers/:id/review 路由（name=paper-review） |
| frontend/src/views/ReviewResultView.vue | 新增 | 审阅结果页面：五类状态、最新 task_id 结果集、维度卡片、Finding 筛选、Evidence 深链、任务创建/恢复/轮询 |
| frontend/src/views/PaperDetailView.vue | 修改 | PARSED 状态"审阅"入口、route.query.evidence 深链处理、未找到证据提示 |
| frontend/src/tests/ReviewResultView.test.ts | 新增 | 初版 20 项 + 后续 6 项缺陷回归，共 26 项 |
| frontend/src/tests/PaperDetailView.test.ts | 修改 | 新增 4 项 Evidence query 测试 |

### 验证结果

| 验证项 | 结果 |
|--------|------|
| 前端测试 | ✅ 45 passed（26 ReviewResultView + 19 PaperDetailView） |
| 前端构建 | ✅ vue-tsc + Vite 构建成功，102 modules transformed |
| Docker 后端全量 | ✅ 277 passed, 0 skipped |
| alembic | ✅ `003_normalized_and_error (head)`，check 无差异 |
| 提示词 SHA-256 | ✅ NEXT=e820c302... ARCHIVE=8844b0fe... |
| P3.5 下一步提示词 | ✅ 正文与归档第 15 节均为 259 行且一致，SHA-256 `59cd46c680e7143ed641d4042094cd3a3f8b22d84e73393d94563e4653ab5ae8` |
| git diff --check | ✅ 无错误（仅 LF/CRLF 警告） |
| API / ORM | ✅ 12 条 `/api/v1` 业务路由、14 张业务表（不变） |
| 测试库 | ✅ 14 张业务表均为 0；Docker 全量测试未污染开发库 |
| 禁止范围 | ✅ 本轮未修改 backend/、docker-compose.yml、package.json、Alembic 等 |

### 关键实现说明

1. 页面优先展示 tasks 倒序中最新且已有 ReviewResult 的 task_id，不把多个历史任务混合；新任务成功前保留上一轮结果。
2. 后端仍没有取消/删除/按 task 过滤 reviews 的 API。
3. 当前认证仍是 demo_user_id，P3.5 注册登录和 RBAC 未实现。
4. 未新增任何依赖、后端 API、数据库迁移。
5. 未实现 WebSocket/SSE/cancel 按钮。

### 码道独立审查与直接修正

1. 修复最新 PENDING/RUNNING/FAILED 任务导致上一轮成功结果被隐藏的问题。
2. 修复轮询网络失败时 activeTask 被清空、错误和“重试轮询”入口一并消失的问题。
3. 轮询终态实时回写任务列表；进度显示限制在 0～100；结果刷新失败显示可恢复错误。
4. 增加单轮询请求互斥、创建请求 generation 守卫和 paper id 变化状态重置，避免陈旧响应覆盖新页面。
5. 数组形式 Evidence query 现在显示“未找到对应证据”，且不请求无关页。
6. TaskType 与 VerificationStatus 改为与后端枚举一致的严格联合类型。
7. 内置浏览器实例在本次验收会话不可用；未伪报可视化 E2E，改由 45 项组件交互测试、生产构建和 Docker HTTP 200 验证覆盖。

## 路线新增：完整用户体系与管理员系统（2026-07-13）

用户明确将完整注册登录和管理员系统列为必做范围。当前 `_get_user_id()` 仍使用 `settings.demo_user_id`，不属于真实认证。

规划顺序如下：

1. P3.2：Embedding 与语义 Evidence 检索（已完成）。
2. P3.3：华为云 MaaS 真实生成式模型适配器（已完成）。
3. P3.4：审阅结果前端与完整任务交互。
4. P3.5：注册、登录、退出、访问/刷新令牌、令牌轮换与撤销、密码修改/找回、个人资料、账号状态、USER/ADMIN RBAC，并将所有业务资源迁移到真实认证上下文。
5. P4～P6：指标、实验分析和报告导出直接使用真实用户隔离。
6. P7：认证页面、个人中心、管理员 API 和完整管理后台，包括仪表盘、用户/角色、账号状态、论文/任务/审阅/报告管理及管理员操作审计。
7. P8：对认证、令牌、RBAC、跨用户数据和管理员操作进行安全/E2E 验收后部署。

安全底线：密码自适应哈希、短时访问令牌、刷新令牌轮换与撤销、服务端 RBAC、登录限流/锁定、管理员审计、无硬编码默认管理员凭据。华为云 IAM 只管理云资源身份，不替代 PaperLens 产品用户系统。

本次仅记录需求与路线，没有实现认证代码、数据库迁移、API 或页面，也没有把该范围混入已经生成的 P3.2 码道提示词。

## P3.5 完整认证、真实用户隔离与 RBAC 基础（2026-07-13）

### 交付结果

- 注册、登录、refresh、logout/logout-all、me/profile、改密、找回/重置共 10 个 auth API 已完成。
- Argon2id 密码、固定 HS256 access、HttpOnly opaque refresh、轮换/replay family 撤销、账号锁定和 sid 实时校验已完成。
- 所有现有论文、Evidence、任务和审阅路由使用真实认证用户；USER/ADMIN 角色和显式管理员提升/legacy claim CLI 已完成。
- 五个认证页面、Pinia 内存 token、启动 refresh bootstrap、401 single-flight 和安全 redirect 已完成。
- 004 初始认证迁移后追加 005 无损安全纠正；最终 17 张 ORM 表、22 条 `/api/v1` 路由。

### 码道独立审查与直接修正

码道初版自报后端 298 passed、前端 61 passed，但存在默认 JWT secret、localStorage token、重放不撤销 family、access 不查 session、reset token 日志泄漏、禁用/锁定枚举、logout 无认证、CASCADE 用户外键等关键问题。码道已全部直接修正并补真实行为断言，详见 P3.5 bugfix report。

### 最终验收

| 验证项 | 结果 |
|--------|------|
| 认证定向 | 42 passed |
| Docker 后端全量 | 318 passed，0 skipped |
| 前端 | 66 passed；生产 build 成功（123 modules） |
| Alembic | 005 head；check 无差异；paperlens_test 005→003→head 成功 |
| API / ORM | 22 条 `/api/v1` 路由；17 张表 |
| HTTP / Docker | health 200、无 token 401、login 页 200；backend/frontend running、postgres healthy |
| 浏览器 | 内置实例为空，未执行真实点击 E2E |
| 开发库 | ⚠️ P3.4 曾记录 35/1/1，本轮首次计数已为 0/0/0；无法自动恢复或证明来源，后续测试前后保持 0 |

### 尚未完成

完整管理员业务 API/控制台/审计、MFA、邮箱验证、生产通知适配器、分布式 IP 限流和浏览器 E2E 仍待 P7/P8。下一阶段为 P4 指标提取与 checkpoint 口径判断，并继续复用真实用户隔离。

---

## P4.1 可追溯实验指标提取与 Checkpoint 口径判断后端（2026-07-14）

### 码道初版与后续审查

码道初版自报指标定向 37 passed、后端全量 355 passed、Alembic 006，但测试只断言任务创建响应为 201，没有核对后台终态。码道复核发现读取表格/Evidence 后 SQLAlchemy 会自动开启事务，初版函数随即把这一正常读事务当作错误，因此真实后台任务必然 FAILED；此外还存在无来源记录可入库、无证据 Checkpoint 为 null、模型和数据集误用同一行文本、Metric options 不区分、活动任务竞态以及过滤/隔离/原子性测试缺失。

码道已直接修正：

- 先读取不可变来源快照并结束读事务，再执行纯 Python 提取；最终记录和 SUCCEEDED 状态单事务提交。
- 百分号统一存 0～1；非百分比指标允许有限负数；NaN/Infinity、范围和均值±误差拒绝。
- 模型/数据集只从明确语义列提取；Checkpoint 无证据或冲突均为 UNKNOWN，不按最大数值猜测。
- 每条记录只能绑定 `table_id + row_index` 或 `evidence_id`；写入前复核同论文来源，公开查询同时复核 task/paper/user/source。
- 请求使用 task_type 判别 schema；未知 body/query 字段拒绝；活动任务由应用检查和 PostgreSQL 部分唯一索引双重防重。
- 保留已应用 006，新增 007 无损纠正有限数值、来源、Checkpoint、任务类型、来源 FK 和并发约束。

### 最终验收

| 验证项 | 结果 |
|--------|------|
| 指标提取定向测试 | 67 passed |
| Docker 后端全量 | 385 passed，0 skipped，12 个既有依赖弃用 warning |
| 前端 | 8 files / 66 passed；生产 build 成功，123 modules |
| Alembic | 007 head；check 无差异；paperlens_test `007 → 006 → head` 成功 |
| API / ORM | 24 条 `/api/v1` method+path 路由；17 张 ORM 表 |
| HTTP / Docker | health 200；无 token 的论文/指标端点 401；login 200；三容器运行且 postgres healthy |
| 测试库 | 17 张业务表全部为 0 |
| 开发库 | 测试前后均为 2 users / 2 papers / 1 task / 7 reviews / 0 metrics；未清理或伪造用户数据 |
| 提示词 / Git | 两个提示词哈希未变；最新提交仍为用户的 4659a0b；禁止目录未变化 |

### 尚未完成

P4.1 仅完成后端。指标分析页面、指标任务交互与 Evidence 深链属于 P4.2；CSV/Excel、报告导出、完整管理员系统和真实华为云推理仍未实现。

---

## P4.2 指标分析前端与完整任务交互（2026-07-14）

### 新增/修改文件

| 文件 | 操作 | 说明 |
|------|------|------|
| frontend/src/api/index.ts | 修改 | 新增严格指标类型和 REVIEW/METRIC_EXTRACTION 判别联合；指标参数过滤、分页边界和创建函数 |
| frontend/src/router/index.ts | 修改 | 新增 /papers/:id/metrics 路由（name=paper-metrics, requiresAuth） |
| frontend/src/views/MetricAnalysisView.vue | 新增并修正 | 指标分析页面：任务隔离、轮询/409 恢复、独立请求序号、筛选分页、值/口径、来源原文和真实 Evidence 深链 |
| frontend/src/views/PaperDetailView.vue | 修改 | PARSED tabs 区域新增"指标" router-link 入口 |
| frontend/src/tests/MetricAnalysisView.test.ts | 新增并扩展 | 35 项状态机、并发、来源、安全和错误恢复测试 |
| frontend/src/tests/MetricApiAndRoute.test.ts | 新增 | 4 项指标 API body/参数边界与受保护路由测试 |
| frontend/src/tests/PaperDetailView.test.ts | 修改 | 20 项通过，补指标入口并修复测试路由 |

### 关键实现说明

1. 页面只列出成功指标历史；没有成功任务时不请求指标，每个列表请求始终携带单一 `task_id`，不会混合历史。
2. PENDING/RUNNING 恢复轮询，创建锁防双击，409 自动恢复服务端活动任务；FAILED/CANCELLED 保留旧结果。
3. 百分比规范指标显示百分数并同时展示存储值；六种 CheckpointType 均有稳定中文标签和样式。
4. Evidence 生成论文详情深链；表格来源显示 `table_id`、0-based 行号和可展开原文；异常双来源/无来源安全降级。
5. 筛选和分页走后端；零匹配仍保留筛选栏；独立 request id 防止快速筛选、翻页或任务切换的旧响应覆盖。
6. 后端文本只用 Vue 插值；没有 `v-html` 或 Web Storage token；未新增后端接口、迁移或依赖。

### 验证结果

| 验证项 | 结果 |
|--------|------|
| P4.2 定向测试 | ✅ 59 passed（3 files） |
| 前端全量 | ✅ 106 passed（10 files） |
| 前端构建 | ✅ vue-tsc + Vite 构建成功，126 modules transformed |
| Docker 后端全量 | ✅ 385 passed, 0 skipped |
| P4.1 后端定向 | ✅ 67 passed |
| Alembic | ✅ 007 head；check 无差异 |
| API / ORM | ✅ 24 条 `/api/v1` 路由；17 张 ORM 表 |
| Docker / HTTP | ✅ 最新前端镜像已重建；三容器运行，postgres healthy；health/login 200；无 token metrics 401 |
| 测试库 | ✅ 17 张业务表残留总数 0 |
| 开发库计数 | ✅ 2u/2p/1t/7r/0m（与 P4.1 基线一致） |
| P4.2 输入提示词 SHA-256 | ✅ `EE0D146C...15FB4`，码道执行期间未变 |
| Secret 扫描 | ✅ 无泄漏 |
| Markdown | ✅ 75 个本地链接，修正后 0 broken |
| 浏览器 E2E | ⚠️ 当前会话无可用内置浏览器实例，未执行且未伪造 |
| 禁止范围 | ✅ 未修改 backend/、docker-compose.yml、alembic/、AGENTS.md、`.arts/`、`.codeartsdoer/`、`.skills/` |

### 码道独立审查

码道初版 48 项页面定向测试通过，但测试没有揭示 Evidence 仅为占位文字、表格来源/原文缺失、异常来源猜测、无 `task_id` 查询、成功历史范围错误、零结果筛选消失、快速请求竞态和 ProjectDocs 仍为规划态等问题。码道已直接修正并补充真实行为断言，详见 `ProjectDocs/bugfix-report/P4.2-码道独立审查与指标前端交互验收收口.md`。

---

## P4.3 华为云 MaaS LLM 运行配置与安全联调准备（2026-07-14）

### 新增/修改文件

| 文件 | 操作 | 说明 |
|------|------|------|
| docker-compose.yml | 修改 | LLM 变量逐项透传（默认 mock），Embedding 强制 mock |
| backend/paperlens/services/llm_client.py | 修改 | 新增 validate_llm_config() 配置校验函数 |
| backend/paperlens/cli.py | 修改 | 新增 maas-config-check 和 maas-smoke --confirm-billable |
| backend/tests/test_services/test_maas_config.py | 新增并经 码道补强 | 配置/CLI/Compose/fake client、占位 Key、完整 endpoint、测试会话隔离 |
| .env.example | 修改 | base URL 说明、去掉 /chat/completions 注释 |
| README.md | 修改 | 启用步骤、安全须知、三种状态区分 |

### 关键实现说明

1. Docker Compose 将 `PAPERLENS_LLM_BACKEND` 从硬编码 `mock` 改为 `${PAPERLENS_LLM_BACKEND:-mock}` 透传，LLM 6 个变量逐项透传，`PAPERLENS_EMBEDDING_PROVIDER` 硬编码为 `mock`。
2. `validate_llm_config()` 不联网，构造 HuaweiMaaSLLMClient 做配置预检；mock 模式不要求 MaaS 配置。
3. `maas-config-check` 输出非敏感摘要（backend、scheme/host/path、model、api_key_configured true/false）；`maas-smoke` 必须带 `--confirm-billable` 且 backend=huawei_maas。
4. 码道初版未修改 HuaweiMaaSLLMClient 的 TLS/Bearer 主流程；码道追加完整 endpoint 和占位 Key 的失败前置，并修正 CLI 与测试隔离。未新增迁移或依赖。用户明确授权后完成真实最小烟测；码道未读取或输出本地 Key。

### 码道独立审查与修正

码道初版虽然自报 11 项定向通过，但真实 huawei config-check 会因 `ParseResult.host` 崩溃，Docker 三项 Compose 测试被跳过，占位 Key 和完整 endpoint 未失败前置，CLI fake 测试未覆盖真实确认门/单次调用，烟测允许 2048 completion token，失败会回显底层异常，README 还会在容器重新加载 `.env` 前检查旧配置。更关键的是 pytest 会继承未来运行容器中的真实 MaaS backend 与 Key，存在回归测试意外计费风险。

码道已直接修正上述问题：配置检查使用 hostname；烟测上限 32 token 且固定安全失败；实际 Compose 文件只读挂载以消除 skip；conftest 在导入 Settings 前强制两类 provider 为 mock、endpoint 为 `.invalid` 并移除继承 API Key；同时补齐 ProjectDocs 01～08、SDD、独立 Sprint 和 bugfix report。

### 验证结果

| 验证项 | 结果 |
|--------|------|
| P4.3/Huawei LLM 定向测试 | ✅ 110 passed, 0 skipped |
| Docker 后端全量 | ✅ 435 passed, 0 skipped |
| 前端全量 | ✅ 106 passed |
| 前端构建 | ✅ 成功 |
| Alembic | ✅ 007 head；check 无差异 |
| API / ORM | ✅ 24 条路由；17 张表 |
| Docker 容器 | ✅ 三容器运行，postgres healthy |
| maas-config-check | ✅ 真实运行配置输出 `backend: huawei_maas`、`api_key_configured: true`、安全 endpoint 摘要与 `OK` |
| maas-smoke 无确认 | ✅ 拒绝并提示 `--confirm-billable` |
| maas-smoke mock 后端 | ✅ 拒绝并提示需要 huawei_maas |
| 开发库计数 | ✅ 2u/2p/1t/7r/0m |
| 测试库残留 | ✅ 17 张业务表总数 0 |
| 安全/Markdown | ✅ 高熵密钥候选 0、Web Storage 源文件 0、77 个本地链接 0 断链 |
| 真实云端烟测 | ✅ 配置与 DNS/TCP/TLS 通过；首轮安全失败后仅对 smoke 关闭思考模式，第二次且最后一次授权请求成功，返回 35 字符 |

### 真实 GLM 审阅失败修复

用户随后对 BVG.pdf 发起真实审阅。MaaS 请求正常完成，但 GLM-5.2 将完整 JSON 包在标准 `json` Markdown 围栏中，旧解析器按严格契约拒绝，任务 `b30d602c-8fa3-4168-a5f2-15b85fc9b91a` 安全进入 FAILED，ReviewResult 数量为 0。华为 MaaS V2 公开契约未提供 `response_format=json_object`，因此本轮只增加确定性单层 JSON/无语言围栏解包，不从任意文本猜测 JSON；前后附文、非 JSON 标签、嵌套/多围栏、数组、额外字段和维度错误继续拒绝。

排查时发现 SQLAlchemy echo 日志会回显论文表格原文和 SQL 参数，已将数据库引擎固定为 `echo=false`、`hide_parameters=true`，与应用 debug 解耦。修复后审阅/Huawei 定向 `138 passed, 0 skipped`，Docker 后端全量 `435 passed, 0 skipped`，前端 `106 passed`，生产构建 126 modules。后端容器已重建；为避免未经确认产生费用，修复后未自动发起真实审阅。

最终只读计数为开发库 2 users / 3 papers / 2 tasks / 7 reviews / 0 metrics / 0 experiment_files / 0 experiment_results；新增论文和失败任务来自用户本次实际操作，未删除或改写。测试库 17 张业务表残留总数仍为 0。

---

## P5.1 CSV/Excel 实验文件安全上传与结构解析（2026-07-14）

### 码道初版与后续审查

码道初版新增了 008、CSV/XLSX/XLS 解析器、上传/列表/详情 API，并自报 P5.1 定向 59、后端全量 494、前端 106。码道复核确认初版存在以下验收阻断：008 会 UPDATE/DELETE 用户数据；UploadFile 一次性 `read()` 导致内存风险；同步解析直接阻塞 async 路由；生产解析器输入为原始 bytes 而非服务端路径；完整 SHA-256 被公开；XLSX 未完整拒绝反斜杠穿越、重复 entry、单项压缩比、宏内容类型、外部 relationship 和任意形式公式节点；并发重复可能返回 500 并留下多余对象；storage/flush/commit 补偿不完整；成功 commit 后 refresh 失败会形成数据库/对象不一致；错误和清理日志可能包含原始解析信息、文件路径或用户文件名；SDD、Sprint 和多数状态文档仍停留在规划态。

码道已直接修正并完成收口：

- 008 改为在任何 DDL 前只读检查不兼容行和重复键，发现冲突即中止，完全移除 UPDATE/DELETE。
- API 按 1MiB 块将实际字节写入随机临时文件；所有路径关闭 UploadFile 并清理临时文件，解析/存储/事务在线程池执行。
- 生产解析器只接收服务端路径和确认后的 `ExperimentFileType`，用增量列状态生成 version=1 `columns_info`，不保存样本或整行。
- CSV 使用确定性编码和分隔符判定；XLSX 增加 entry 规范化/重复/加密、单项和总压缩比、总解压量、宏/外链/嵌入对象/公式、多 sheet 防护；XLS 同时验证 OLE magic 和 xlrd 成功。
- Pydantic 改为 extra-forbid 的嵌套严格 schema，完整 hash 和 storage_key 只在内部保留。
- 同 user/paper/hash 的前置幂等与数据库唯一约束共同收口并发，竞争失败者 rollback、删除自己的 object、查询胜者后返回 200。
- storage.save、flush、refresh、commit 任一步失败均 rollback 并补偿；日志仅记录固定阶段、object key 和异常类型。
- 固定补充 `xlwt==1.3.0`，保证全新 Docker 镜像能生成合法 XLS 测试样本，不依赖旧镜像残留包。
- 按 dev-process-framework → page-mockup（确认 P07 仍规划）→ fullstack-testing → function-detail → sdd-workflow → bug-fix-reporter 的顺序人工同步设计和 Sprint。

### 最终验证

| 验证项 | 结果 |
|--------|------|
| P5.1 解析/存储/API 定向 | ✅ 103 passed，0 skipped |
| P4.3 MaaS/LLM/审阅广义定向 | ✅ 180 passed，0 skipped |
| P4.1 指标定向 | ✅ 67 passed，0 skipped |
| Docker 后端全量 | ✅ 527 passed，0 skipped |
| 前端 | ✅ 10 files / 106 passed；生产构建 126 modules |
| 008 迁移 | ✅ 冲突记录无损保留并预期中止；007→008→007→008 成功；最终 head=008 |
| 测试库 | ✅ 17 张业务表残留总数 0 |
| 开发库 | ✅ 2 users / 3 papers / 3 tasks / 14 review_results / 0 metrics / 0 experiment_files / 0 experiment_results |

开发库相较 P5.1 提示词基线新增的 1 个任务和 7 条审阅结果来自用户在 P4.3 修复后主动重试真实审阅；本轮只读核对，没有创建、删除或改写开发业务数据。真实 MaaS 最小连通性已成功，但长文本质量与生产费用仍未验收。本轮没有真实云端请求。

截至 P5.1 验收时，P5.2 统计摘要、ExperimentResult、实验分析任务和 result API 尚未实现；其后已在下节 P5.2 完成并由码道收口。指标交叉验证与实验前端、delete API 和报告导出继续后置。

---

## P5.2 实验数据确定性统计摘要后端闭环（2026-07-14）

### 交付结果

| 项目 | 结果 |
|------|------|
| 迁移 009 | ✅ analysis_tasks.experiment_file_id + CHECK + 部分唯一索引 |
| 统计服务 | ✅ Welford mean/stddev + 精确 median + 数值安全 |
| 分析服务 | ✅ 任务创建/后台执行/原子写入 ExperimentResult |
| 文件完整性复核 | ✅ SHA-256 重算 + P5.1 magic/结构解析重验 |
| 新增配置 | ✅ max_experiment_analysis_numeric_cells 默认 5,000,000 |
| 2 个新 API | ✅ POST analysis (201/200) + GET result (200/404) |
| 幂等/并发 | ✅ 同一文件最多一条活动任务和一条 ExperimentResult |
| 安全错误 | ✅ error_message 只能是固定安全分类，不泄漏内部信息 |
| 不依赖 LLM/Embedding | ✅ 实验统计链路即使两工厂 monkeypatch 为一调用就失败也必须工作 |

### 新增文件

| 文件 | 说明 |
|------|------|
| backend/paperlens/services/experiment_statistics.py | Welford/median/数值安全统计计算 |
| backend/paperlens/services/experiment_analysis_service.py | 分析任务创建/后台执行/原子写入 |
| backend/alembic/versions/009_experiment_analysis_task_link.py | 迁移 |
| backend/tests/test_services/test_experiment_statistics.py | 43 项统计单元测试 |
| backend/tests/test_api/test_experiment_analysis.py | 14 项 API 集成测试 |
| ProjectDocs/sprint/实验数据统计摘要.md | Sprint 文档 |

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| backend/paperlens/models/models.py | AnalysisTask 新增 experiment_file_id + CHECK + 部分唯一索引 |
| backend/paperlens/core/config.py | 新增 max_experiment_analysis_numeric_cells |
| backend/paperlens/api/experiment_files.py | 新增 analysis + result endpoint |
| backend/paperlens/schemas/experiment_file.py | 新增 SummaryStatsResponse/ExperimentAnalysisTaskResponse/ExperimentResultResponse |
| backend/paperlens/schemas/task.py | 通用论文任务端点继续显式拒绝 EXPERIMENT_ANALYSIS，实验统计使用独立 POST analysis |
| backend/tests/db_helpers.py | verify_alembic_revision 更新为 009 |

### 码道原始验证结果（码道修正前）

| 验证项 | 结果 |
|--------|------|
| P5.2 统计单元测试 | ✅ 43 passed |
| P5.2 API 集成测试 | ✅ 14 passed |
| Docker 后端全量 | ✅ 584 passed, 0 skipped |
| 前端 | ✅ 106 passed；生产构建 126 modules |
| 009 迁移 | ✅ test DB 验证通过 |
| 路由 | ✅ 27 → 29 |
| 表 | ✅ 17（不变） |
| Health | ✅ 200 |

### 未实现（P5.3+）

- MetricRecord 交叉验证、MATCH/MISMATCH
- P07 实验前端
- ExperimentFile 删除/下载/行预览
- 报告导出
- column_analysis 和 metric_comparisons 仍为 null
- 进程重启恢复/持久化队列（沿用 FastAPI BackgroundTasks）

---

## P5.2 码道独立审查与验收收口（2026-07-14）

码道复核发现初版统计实现仍缓存完整文件/全部数据行，非法和非有限数值被静默当作 null，并发唯一冲突返回 409，部分前置失败会让任务卡在 PENDING；完整性只比较列名/dtype，失败补偿及 commit 未知处理也不完整，systemDesign 01～08 与 SDD 也尚未同步。

已直接完成以下修正，不增加码道轮次：

- 为 CSV/XLSX/XLS 增加公共路径型逐行规范值迭代器；统计阶段不保存原始行或字符串样本。
- 严格拒绝 NaN、Infinity、非法数字、计算溢出与超安全整数；median 数组排序后及时释放。
- 完整比较 columns_info，并在统计后再次复核 SHA-256。
- 并发 loser 回查胜者返回 200；task/file/paper/user 四者同属，USER/ADMIN 跨用户统一 404。
- 任务认领、成功事务、失败状态事务均处理 commit 未知；补偿逻辑不删除可能已提交结果。
- 严格结果 Schema 不接受非有限数或结构/count 不一致；公开查询联查 SUCCEEDED 实验任务。
- 补齐迁移无损中止、真实并发、storage missing、元数据篡改、flush/commit 与失败状态重试测试。

最终验收：P5.2 定向 `72 passed`；P5.1 回归 103；P4.3 回归 180；P4.1 回归 67；Docker 后端全量 `599 passed, 0 skipped`；前端 106；构建 126 modules。009 在 paperlens_test 验证冲突记录原值保留并无损中止，以及 `008→009→008→009`；测试库七张核心表残留 0。开发库七表计数保持 `2/3/3/14/0/0/0`，本轮未调用真实 MaaS。

下一阶段固定为 P5.3a 指标交叉验证后端；P5.3b 实验前端另按既定轮次执行。

---

## P5.3a 论文指标交叉验证后端闭环与码道验收收口（2026-07-15）

### 交付结果

P5.3a 已完成“成功指标任务 + P5.2 统计结果 → 确定性匹配 → MATCH/MISMATCH/UNVERIFIABLE → 原子持久化 → 查询”闭环。新增 POST comparisons，并扩展 GET result 的 `metric_comparisons`；没有新增迁移或业务表。

码道初版完成了基本服务和接口，但把 diff 方向写反、零分母写成 Infinity，缺少重复/空指标语义、严格持久化校验、完整归属关系、行锁、真实并发和 commit unknown 收口，且测试固化了错误行为。码道已按授权直接修正，不增加码道返工轮次：

- 名称固定 NFKC→casefold→alnum；仅 MEAN/MAX 可验证，其余 checkpoint 不猜测。
- `diff = experiment_value - paper_value`，零论文值的 relative_diff 为 null；所有公开数值严格有限。
- 重复论文指标为 `AMBIGUOUS_PAPER_METRIC`，无指标为 `NO_METRICS`，严格校验 version=1 摘要和 comparison shape。
- 完整复核 file/result/analysis task/metric task/MetricRecord/source 的 paper/user/task 归属；只读来源 id/paper_id，不读取 storage、原始行、raw_text 或正文。
- ExperimentResult 行锁，同源 201/200、异源 409；补齐 flush/commit rollback 与 commit 未知新会话回查。
- 固定 POST 公开响应与 Comparison Schema；旧上传补偿日志也不再输出 storage key 或临时路径。

### 最终验证

| 验证项 | 结果 |
|--------|------|
| P5.3a 定向 | ✅ 74 passed，0 skipped |
| P5.2 / P5.1 回归 | ✅ 72 / 103 passed，0 skipped |
| P4.3 / P4.1 回归 | ✅ 180 / 67 passed，0 skipped |
| 上传生命周期 | ✅ 10 passed，0 skipped |
| Docker 后端全量 | ✅ 673 passed，0 skipped |
| 前端 | ✅ 10 files / 106 passed；生产构建 126 modules |
| Alembic | ✅ 009 head；check 无差异 |
| API / ORM | ✅ 30 条 `/api/v1` method+path；17 张业务表 |
| 测试库 | ✅ 17 张业务表残留总数 0 |
| 开发库 | ✅ `2 users / 3 papers / 3 tasks / 14 review_results / 0 metrics / 0 experiment_files / 0 experiment_results` |
| Docker / HTTP | ✅ 三容器运行，PostgreSQL healthy；health/login 200；无 token comparisons 401 |
| 静态检查 | ✅ Python 编译、git diff --check、secret/Web Storage/敏感日志；77 个本地 Markdown 链接、0 断链 |
| Git / 禁改目录 | ✅ HEAD 仍为 `525828b42707f7d1ef5c8efe1f308ce4bdac5454`；`.arts/.codeartsdoer/.skills` 无差异 |

码道执行期间 `CODEARTS_NEXT_PROMPT` 与归档 SHA-256 分别保持 `C0A1DA0A...3042`、`5FA2245E...A0E`，未被越界修改。测试强制使用 mock，本轮未读取 `.env`、未调用真实 MaaS、未修改开发库业务数据或数据库 volume。

下一阶段固定为 P5.3b 实验数据前端。文件删除/下载/行预览、报告导出、完整管理员系统和 P6～P8 不并入该轮。

---

## P5.3b 实验数据前端与码道独立验收收口（2026-07-15）

### 交付结果

P5.3b 已完成受保护的 `/papers/:id/experiment` 页面：上传非空 CSV/XLSX/XLS、分页选择文件、查看可信列结构、创建和观察统计任务、展示摘要、选择指标任务并创建或恢复交叉验证。PaperDetailView 已提供入口；本阶段没有新增后端路由、迁移或业务表。

码道初版前端测试 12 files / 144 passed、构建 129 modules，但仍遗漏可信详情消费、文件分页、上传前非空/20MB 检查与上传后选中；它忽略 GET result 中已有比较并要求重复 POST，按 API 顺序而非时间选择指标任务，文件切换后在途轮询可污染新页面，并把原始网络/任务异常展示给用户。测试也固化了这些错误行为。码道已按持续授权直接修正，不增加码道返工轮次：

- 接入 `getExperimentFile`，展示 columns_info 并校验 detail 的 file/paper 上下文，支持独立重试。
- 增加每页 20 条文件分页；上传前检查扩展名、非空、20MB，移除手写 multipart Content-Type，上传后刷新第一页并自动选中响应文件。
- 统计轮询捕获页面代数、文件选择代数和 file/task 上下文；切换文件、路由或卸载后旧响应不再写回。
- 直接从 GET result 恢复 metric_comparisons 并锁定 metric_task_id；没有结果时才允许 POST，默认选择 created_at 最新的成功指标任务。
- comparison 响应再次校验 file/metric task 及每一行来源；差值表头明确为“实验值 - 论文值”，所有 null 统一显示 em dash。
- 未知 API 与任务错误统一映射为固定公开文案，不再展示服务端 message、路径、令牌或内部异常。
- 将码道新增的重复编号 `design/09-experiment-frontend.md` 内容并入既有前端详细设计后删除，避免和 `09-API接口详细设计.md` 冲突。

### 最终验证

| 验证项 | 结果 |
|--------|------|
| P5.3b 定向前端 | ✅ 2 files / 48 passed |
| 前端全量 | ✅ 12 files / 154 passed |
| 生产构建 | ✅ 129 modules |
| Docker 干净构建 | ✅ 129 modules；额外发现并修正分页 mock 的可选参数类型，不依赖 tsbuildinfo 缓存 |
| Docker 后端全量 | ✅ 673 passed，0 skipped |
| Docker 服务 | ✅ backend/frontend/PostgreSQL 均运行，PostgreSQL healthy |
| 迁移 / API / ORM | ✅ 009 head、alembic check 无差异；30 条 API method+path；17 张业务表 |
| 数据库 | ✅ paperlens_test 17 表残留 0；开发库只读计数 `2/4/4/21/0/0/0`，本轮验收未写入 |
| 浏览器自动化 | ⚠️ 当前会话 in-app browser 不可用（浏览器列表为空）；由组件测试、构建和 HTTP 运行检查替代，不伪报 GUI E2E |

本轮未读取 `.env`、未调用真实 MaaS、未修改开发库业务数据、未删除数据库 volume，也未创建 Git 提交。P5 完整功能闭环已完成；文件删除/下载/原始行预览仍不在本轮范围。

下一阶段固定为 P6.1 Markdown 审稿报告后端闭环。PDF/DOCX 转换和报告导出前端留在 P6.2；完整管理员 API、后台和审计仍按既定 P7 轮次实施。

---

## P6.1 Markdown 报告后端与码道独立验收收口（2026-07-15）

### 交付结果

P6.1 已提供创建、状态查询和鉴权下载三个 API。Markdown 支持 zh/en 固定模板、逐维度审阅、Finding 与 Evidence 页码/短引用、可选论文指标、实验统计及已有交叉验证；生成完全离线，不调用 LLM/Embedding。

码道初版存在来源更新后永久复用旧 READY 报告、后台重新选择来源、当前时钟破坏确定性、Evidence 误输出 id、Markdown 结构注入、来源图缺少复核以及部分写入对象未完整补偿等问题，原 68/16 项测试没有真实覆盖这些路径。码道依用户持续授权直接修正，未增加码道返工轮次：

- 创建 PENDING 前完成 Review/Finding/Evidence、Metric/source、Experiment/File/Task 全图复核，生成确定性 bytes、content_hash 和规范 source_hash。
- 011 迁移建立来源感知唯一索引；同源同内容并发最多一行，不同来源可新建，FAILED 可重试；历史 PDF/DOCX 骨架行保持兼容。
- 后台条件 UPDATE 原子认领，只保存创建时 bytes；storage 回读逐字节复核后提交 READY，提交未知先回查，未归属对象清理后安全 FAILED。
- 生成时间取来源任务时间；补齐 Evidence 页码/240 字短引用、结构/HTML/表格/URL scheme 转义和严格数字降级。
- 状态与下载使用严格公开 Schema，不泄露 source_snapshot/source_hash/content_hash/storage_key；下载带 attachment、nosniff、private/no-store 并复核 size/hash。

### 最终验证

| 验证项 | 结果 |
|--------|------|
| P6.1 生成单元 | ✅ 72 passed |
| P6.1 PostgreSQL API/来源图/并发/补偿 | ✅ 25 passed |
| P6.1 历史行迁移与无损 downgrade | ✅ 1 passed |
| Docker 后端全量 | ✅ 771 passed，0 skipped/failed |
| 前端全量 | ✅ 12 files / 154 passed |
| 生产构建 | ✅ 129 modules |
| Alembic | ✅ 011 head；历史 PDF 009→011 保留；非空 P6.1 downgrade 无损拒绝 |

本轮未调用真实 MaaS/Embedding，未删除 volume，未创建 Git 提交。P6.2 继续实现 PDF/DOCX 转换与报告前端；完整管理员系统仍留 P7，BackgroundTasks 进程重启恢复仍留 P8。

---

## P6.2 PDF/DOCX 报告与用户端导出闭环（2026-07-15）

### 交付结果

P6 已完成 Markdown/PDF/DOCX 三格式创建、状态、当前论文历史分页、鉴权下载和受保护的 ReportExportView。012 只扩展来源行三格式约束，不增加表、列或索引；PDF/DOCX 均在创建 PENDING 前由 P6.1 确定性 Markdown bytes 转换并计算 content_hash，后台仍只保存创建时 bytes。

码道初版完成了基本接口与页面，但 PDF 使用 Helvetica 导致中文被提取为连续 `I`，并在生成后以不同长度字符串直接替换 PDF metadata；中文测试只断言提取结果非空。DOCX 的外部关系测试只检查 ZIP entry 文件名，rsid 未实际清除。前端没有分页控件，始终请求第一页，也没有 route/page 请求代数，历史和下载异常被静默吞掉，blob 测试没有验证 URL 回收。

码道按用户持续授权直接收口，不增加码道轮次：

- PDF 改用 ReportLab invariant 模式和内置 STSong-Light CID 字体，固定 creator/producer/title/subject/日期/trailer ID，不再事后修改 PDF bytes；PyMuPDF 逐字验证中英文。
- DOCX 固定 ZIP entry 顺序、timestamp 和权限，清除 rsid；逐项解析 `.rels` 拒绝 External，并拒绝 vbaProject、OLE 与 embeddings。
- 012 downgrade 在 DDL 前检查全部 PDF/DOCX 行；迁移测试按 PostgreSQL 事务性多 revision rollback 正确断言版本整体保持 012。
- 历史页面增加 20 条分页、总数/总页数、路由/翻页/卸载竞态隔离、历史加载重试；下载增加单项锁、固定安全错误和 finally blob URL 回收。
- 状态与历史 API 对 FAILED 始终输出固定公开文案，不让历史内部错误触发响应校验失败或信息泄漏。
- 依次同步 systemDesign 01～08、SDD spec/tasks/design、Sprint 和独立 bugfix report。

### 最终验证

| 验证项 | 结果 |
|--------|------|
| 转换器 / P6.2 API / 迁移 | ✅ 34 / 25 / 1 passed |
| P6.2 前端定向 | ✅ 19 passed |
| Docker 后端全量 | ✅ 830 passed，0 skipped |
| 前端全量 | ✅ 13 files / 173 passed |
| 生产与 Docker 前端构建 | ✅ 132 modules |
| PDF 实测 | ✅ `%PDF-1.4`、bytes 相同、1 页、完整提取“中文标题”“正文包含证据与结论。”、固定 metadata |
| DOCX 实测 | ✅ `PK` OPC、bytes 相同、python-docx 可重开、External=false、rsid=false |
| Alembic | ✅ 012 current/head；check 无差异；PDF/DOCX downgrade 无损中止 |
| API / 数据表 | ✅ 34 条 `/api/v1` method+path；17 张 ORM 应用表，含 alembic_version 共 18 张物理表 |
| Docker / HTTP | ✅ 三容器运行，PostgreSQL healthy；前端 200，health 200 |
| 数据库 | ✅ paperlens_test 17 张应用表残留 0；开发库只读计数 `2/4/4/21/0/0/0/0`（users/papers/tasks/reviews/metrics/files/results/exports） |
| Git / 禁改目录 | ✅ HEAD `525828b42707f7d1ef5c8efe1f308ce4bdac5454`；无提交；`.arts/.codeartsdoer/.skills` 无差异 |
| 码道提示词边界 | ✅ 码道执行期间 next/archive SHA-256 保持 `BBB8F58F...E41B` / `1B4A3D53...25F5` |
| 静态检查 | ✅ Python 编译、git diff --check；生产前端源码无 Web Storage/v-html；未读取 `.env`、未调用真实 MaaS/Embedding |

P6 正式完成。下一阶段固定为 P7.1 管理员 API 与不可变审计后端；P7.2 实现管理后台页面，P7.3 完成管理员权限边界与端到端验收，不新增报告返工轮次。BackgroundTasks 重启恢复、云部署和综合性能/安全验收仍留 P8。

P7.1 完整提示词已写入 `docs/CODEARTS_NEXT_PROMPT.md` 并原文归档为第 25 节；两者正文一致。生成后 SHA-256 分别为 `6491D7642EB070BB11ABFB9F568CA34B2B79F0DF30937171C6CD6EF7A45EA21C` 与 `1F91D76B11916DAE8BC94A4368B052FA181FF6401EF10E2C8027AEA00F605326`。

---

## 产品方向校正：个人论文阅读学习助手（2026-07-15）

用户明确指出项目目标是“帮助我阅读论文学习”，而不是以替代审稿为中心。经重新审查，P2～P6 已实现的解析、Evidence、MaaS、结构化审阅、指标、实验和导出均可复用，但产品入口、未来数据模型和路线需要立即校正。

已完成以下决策与文档同步：

- 主流程改为“上传 → 阅读工作台 → 总结/解释/翻译 → 论文内问答 → 笔记/知识卡 → 复习/导出”。
- 结构化审阅保留并改定位为“批判性阅读”；指标与实验功能作为实验理解工具，不删除历史 API/表/页面。
- 原第 25 节 P7.1 管理员提示词保留为历史但不再执行；新的第 26 节替换为 P7.1 阅读工作台与证据化学习解释。
- P7.2、P7.3 分别用于论文问答与个人学习沉淀；完整管理员后端、页面和不可变审计合并到既定 P8.1。
- 仍只使用 P7.1～P8.4 的既定轮次，没有增加码道轮数；登录注册和管理员系统仍是发布前硬性需求。
- 新 `CODEARTS_NEXT_PROMPT` 与归档第 26 节正文逐字一致（各 10,980 字符）；正文 SHA-256 为 `FBA7B48E8DEE52CE6AC2BB2CF190EB5F1A85C5A0C55A55D09A8BA38DE21ECBF8`。提示词文件/归档文件 SHA-256 分别为 `DD5A72E5484C1AFDABE0B3667C5B4EB3257F955927808D61874C1263E646F15F` / `FAC6126A59165EBFE01D5E249A106355F81BB0D9F8F08A8FA0CF63F150833C06`。

本次只更新需求、设计、SDD、Sprint、路线和下一轮提示词，没有修改运行代码、数据库业务数据或 Docker 状态，也没有创建 Git 提交。P7.1 实现状态仍为“待码道开发”，不得把设计文档误读为已完成代码。

---

## P7.1 论文阅读学习工作台与证据化学习解释（2026-07-15）

### 交付结果

P7.1 已完成。用户可从 PARSED 论文进入 `/papers/:id/read`，按章节或页面阅读，并对当前章节、页面或 Evidence 发起 SUMMARY、EXPLAIN、TRANSLATE。成功结果提供纯文本回答、要点、术语解释卡和可回到原文的 Evidence Citation；解释历史支持真实分页、重新打开与失败重试。

码道初版完成了基本表、API 和页面，但 request_hash 可空、terms 契约错误、Citation 缺少定位字段、章节静默截断、来源图不复核、重复引用被容错、异常日志可能泄漏内容，且前端没有专门测试和完整竞态隔离。码道按用户持续授权直接修正，未增加码道返工轮次。

### 码道独立修正

- 来源解析对 SECTION/PAGE/EVIDENCE 执行 owner/PARSED/同论文验证；SECTION 先取同章节 Evidence，再在页码范围内确定性补充。
- 配置明确的来源字符、Evidence 数量和单条字符上限；来源空、无 Citation 或章节过大均在 LLM 工厂前 409，不静默截断。
- canonical request_hash 纳入 scope id、来源与 Evidence 指纹、mode/language；模型前后双重复核。
- 严格模型契约恢复为 `terms[{term, explanation}]`，拒绝 extra、空值、超长、重复术语、0/未知/重复 alias 和模糊围栏。
- 后台条件 UPDATE 原子认领，关闭事务后调用 LLM，返回后锁行并复核完整来源图，再原子提交 Explanation/Citation；commit-unknown 安全回查。
- API 补齐 422 scope 验证、duplicate 和安全 Citation 字段；中文错误乱码全部修复。
- PaperReadingView 增加五类请求代数、串行 timeout 轮询、前后页历史、失败重试、纯文本术语卡、引用三段节点高亮和不一致降级。
- 由于码道已把旧 013 应用到开发库且留下 1 条 FAILED 记录，码道没有回退删除数据，而是增加 014 纯 DDL 无损收紧约束。该记录保持原样。

### 最终验证

| 验证项 | 结果 |
|--------|------|
| P7.1 API/服务/013～014 迁移定向 | ✅ 36 passed |
| Docker 后端全量 | ✅ 866 passed，0 failed，0 skipped |
| 前端全量 | ✅ 14 files / 183 passed |
| 生产与 Docker 前端构建 | ✅ 135 modules |
| Alembic | ✅ 014 current/head；check 无差异 |
| API / 数据表 | ✅ 37 条 `/api/v1` method+path；19 张 ORM 应用表；20 张物理表 |
| Docker / HTTP | ✅ backend/frontend/postgres 运行，PostgreSQL healthy；前端/health 200 |
| 测试库 | ✅ 19 张应用表残留总数 0 |
| 开发库只读计数 | `3/8/5/28/0/0/0/0/1/0`（users/papers/tasks/reviews/metrics/files/results/exports/learning/citations） |
| Git / 禁改目录 | HEAD 保持 `525828b42707f7d1ef5c8efe1f308ce4bdac5454`；无提交；禁改目录无差异 |
| 安全边界 | 未读取 `.env`，未调用真实 MaaS/Embedding，未删除 volume；前端无 v-html/Web Storage |

第一次全量被外部命令 120 秒时限终止后，残留 pytest 与第二次进程交叉迁移/清库，产生不可信的 1 fail/10 teardown errors。确认只剩 uvicorn、恢复测试库 014 head 并清空后，单进程从头复跑 866 全绿；最终只采用干净单进程结果。

### 下一阶段

下一轮固定为 P7.2：当前论文内的多轮问答、会话历史、服务端 Evidence 检索、引用原文定位和证据不足降级。P7.3 学习沉淀与 P8.1 管理员系统仍未实现，不增加轮次。

P7.2 完整提示词已写入 `docs/CODEARTS_NEXT_PROMPT.md` 并原文归档为第 27 节，正文逐字一致（9,579 字符）。文件 SHA-256 分别为 `05809B7B0A5E4EF4B9A40A190B1625EE02BDED7DE0DB91F1E59143CD78F6DB0E` / `611D77DAF6606DF2894594C4311C55F00040486C075CC9A31C810C59EF3F6C9F`。

---

## P7.2 当前论文多轮问答与码道独立验收收口（2026-07-15）

### 交付结果

P7.2 已在 PaperReadingView 内提供当前论文空会话、会话/轮次双分页、连续提问、3 秒串行轮询、失败重新提问、Evidence Citation 原文定位和“当前论文证据不足”降级。后端新增独立 qa router/schema/service/retriever 与 015 三表，用户和普通 ADMIN 均只能访问自己的论文会话。

码道初版的 33 项后端和 10 项前端测试虽通过，但遗漏 Turn user/paper 全图、活动部分唯一索引、严格终态 CHECK、非空降级保护、API 双分页、向量严格校验、历史字符预算、完整 context_hash、生成后来源复核、前端失败重试和竞态隔离，也没有按技能链同步设计/SDD/Sprint。码道按持续授权直接修正，不增加码道返工轮次：

- 015/ORM 强制问题、状态、幂等、sequence、活动唯一和安全 downgrade；客户端不能提供会话标题或资源覆盖。
- 问题与当前论文 Evidence 一次批量 Embedding，数量/维度/布尔/NaN/Inf/零范数严格失败，按 similarity/page/created/id 确定性 Top-K。
- 历史只取同会话成功轮次，超过预算从最旧完整轮次删除；context_hash 覆盖身份、顺序、语言、问题、历史问答和候选 Evidence 文本。
- 模型返回后锁定 Turn 并重新加载 Conversation/Paper/History/Evidence 全图复算 hash；成功结果与 Citation 同事务，失败清除 hash/结果并只保留固定错误。
- 前端实现真实双分页、失败新 UUID 重试、纯文本安全显示、证据不足零引用和 paper/conversation/turn/action/poll 独立代数。

### 最终验证

| 验证项 | 结果 |
|---|---|
| P7.2 后端定向 | ✅ 43 passed |
| P7.2 前端定向 | ✅ 16 passed |
| Docker 后端全量 | ✅ 909 passed，0 failed，0 skipped |
| 前端全量 | ✅ 14 files / 189 passed |
| 生产与 Docker 构建 | ✅ 135 modules |
| Alembic | ✅ 015 current/head；check 无新操作；空表往返、非空降级拒绝 |
| 路由 / 表 | ✅ 42 条 API；22 张 ORM 应用表；23 张物理表 |
| 测试库 | ✅ 22 张业务表残留总数 0 |
| 开发库只读计数 | `3/9/5/28/0/0/0/0/2/3/0/0/0`（users/papers/tasks/reviews/metrics/files/results/exports/learning/learning citations/qa conversations/turns/citations） |
| 运行态 | ✅ backend/frontend/PostgreSQL 运行；PostgreSQL healthy；后端/前端 HTTP 200 |

开发库相对 P7.1 基线多出 1 篇论文、1 条学习解释和 3 条学习引用，属于码道/用户验证产生的数据；码道未删除或修改。P7.2 三表均为 0。本轮未读取 `.env`、未调用真实 MaaS/Embedding、未删除 volume、未创建 Git 提交。

下一固定轮次为 P7.3：高亮、书签、笔记、知识卡、论文库组织和学习进度；P8.1 管理员系统以及 P8.2～P8.4 仍未实现，不增加轮次。

P7.3 完整提示词已写入 `docs/CODEARTS_NEXT_PROMPT.md` 并原文归档为第 28 节，正文逐字一致（9,196 字符）。文件 SHA-256 分别为 `9F1A0E63B5E82A0FED4267698E61922F96BDA54E786254F40C81EB30488B2B4B` / `7C67E125571AD12AF09F921564F30CA74E7EF82411EB673C02BCC2D277651F20`。

---

## P7.3 个人学习沉淀与论文库及 码道独立验收收口（2026-07-16）

### 交付结果

P7.3 已完成论文库、阅读进度、高亮、书签、笔记和知识卡闭环。论文库支持搜索、状态、收藏、集合、进度与四类学习记录计数；阅读工作台提供四个独立分页子区、Unicode/跨文本节点高亮、笔记/卡片编辑和引用删除保护。本轮只使用确定性数据库逻辑，没有新增模型调用。

码道初版基础 CRUD 可以运行，但迁移没有可靠非空降级保护，ORM/数据库约束不一致，论文库默认筛选遗漏无 entry 论文且存在 N+1，公开响应泄露 owner 字段，空 PATCH、跨所有者列表和卡片来源边界不足；前端还含不存在的枚举、错误阅读路由、伪分页、静默失败、不可靠选区偏移和竞态覆盖。码道按持续授权直接修正，没有增加码道返工轮次。

### 码道独立修正

- 重写 016 的严格 CHECK、索引和五表非空 downgrade；ORM/迁移名称对齐，并补数据库非法行、往返和逐表非空保护。
- 论文库改为单查询相关计数，默认 TO_READ/favorite=false 仍包含无 entry 论文；列表读取保持零写入。
- 统一 owner/PARSED/PaperPage/来源全图验证、事务回滚和固定公开错误；Schema 拒绝 extra、空 PATCH、非法 null、控制字符和超限文本，响应移除 user_id。
- 高亮/书签重复创建统一幂等 200；所有学习列表稳定分页；同一 mastery 状态不刷新 last_reviewed_at。
- PaperListView 修复阅读路由并实现真实搜索/筛选/集合/分页/四类计数；PaperReadingView 增加独立分页、编辑、删除确认、失败提示和请求代数。
- 新增安全 Selection/Range 解析器，仅允许 PAGE 正文高亮，跨文本节点与 Unicode 偏移先按完整页面切片复核，来源变化时降级。

### 最终验证

| 验证项 | 结果 |
|---|---|
| P7.3 API/服务定向 | ✅ 60 passed |
| 迁移组 | ✅ 13 passed |
| P7.3 前端定向 | ✅ 24 passed |
| Docker 后端全量 | ✅ 977 passed，0 failed，0 skipped |
| 前端全量 | ✅ 16 files / 197 passed |
| 生产与 Docker 构建 | ✅ 136 modules |
| Alembic | ✅ 016 current/head；check 无差异；非空 downgrade 在 DDL 前拒绝 |
| 路由 / 表 | ✅ 59 条 API；27 张 ORM 应用表；28 张物理表 |
| 测试库 | ✅ 27 张应用表残留总数 0 |
| 运行态 | ✅ backend/frontend/PostgreSQL 运行；PostgreSQL healthy；后端/前端 HTTP 200 |

开发库既有 P2～P7.2 数据保持不变，P7.3 五表均为 0。本轮未读取 `.env`、未调用真实 MaaS/Embedding、未删除 volume、未创建 Git 提交。

下一固定轮次为 P8.1：完整管理员后端、Vue 管理后台、用户角色/状态和不可变审计；P8.2～P8.4 仍按全链路恢复、性能可靠性和华为云部署安全依次执行，不增加轮次。

P8.1 完整提示词已写入 `docs/CODEARTS_NEXT_PROMPT.md` 并原文归档为第 29 节，正文逐字一致（7,988 字符）。文件 SHA-256 分别为 `02DA01D5EE7693CF7B122124FE15F013B6122D329CCB8B98A3E7BCE184F99804` / `D3C834BE14D75F9B729D0F175C6ADC05C29BB70B96B5369F844DF11D5A3529BB`。

---

## 项目文档统一为码道独立开发口径（2026-07-16）

按最新文档规则，README、docs、ProjectDocs、SDD、Sprint、修复报告和提示词归档已统一使用码道独立开发、审查、修正与验收口径。17 个旧署名修复报告已同步重命名，正文引用保持一致；功能实现、测试数字、迁移、数据库和运行验收事实均未改变。

长期规则已写入 `AGENTS.md`、需求决策、实施计划和 `ProjectDocs/sprint/文档署名统一.md`。后续新生成的提示词、进度、Sprint 与修复报告继续沿用该署名方式。

---

## P8.1 完整管理员系统与不可变审计及码道独立验收收口（2026-07-16）

### 交付结果

P8.1 已完成 017 管理员审计模型、首个管理员安全引导、8 条管理员 API 和 Vue 管理后台。管理员可查看平台聚合、用户详情和跨用户论文/任务/报告安全元数据，可在填写原因后变更其他用户角色/状态；所有实际变化按字段写入 append-only 审计，相同值不写审计。

码道初版的 47 项定向测试可以通过，但仍存在不同目标 bootstrap 并发、认证后操作者权限竞态、旧 promote-admin 绕过审计、审计 JSONB 形状约束不足、列表 N+1/敏感实体加载、非法筛选未拒绝，以及管理页共享加载序号造成永久 loading 等缺口。码道按持续授权直接修正，没有增加码道返工轮次。

### 码道独立修正

- 首次引导与管理员变更共用 PostgreSQL 事务级 advisory lock；锁后按确定顺序读取 ACTIVE ADMIN、操作者与目标并重新校验权限。
- 移除旧 promote-admin 无审计入口；admin-bootstrap 只接受 UUID4 和 reason，未知 CLI 异常使用固定公开错误。
- 017/ORM 增加 action 与精确 role/status before/after 对应 CHECK；reason 去首尾空白并拒绝全部控制字符。
- 用户计数改为相关子查询，论文与审计改为 JOIN，任务/报告只查询安全投影，消除逐行 N+1 和内部字段加载。
- 8 条 API 统一 UUID4、枚举、分页、搜索和带时区时间白名单；FAILED 只映射固定安全文案。
- 管理页改为单层请求代数，补用户详情、论文/任务/报告独立筛选和分页、审计筛选、reason 去空白校验与固定错误映射。
- 新增不同目标引导并发、互相降级、严格审计状态、参数白名单、查询次数和管理页面回归测试。

### 最终验证

| 验证项 | 结果 |
|---|---|
| P8.1 后端定向 | ✅ 54 passed |
| Docker 后端全量 | ✅ 1030 passed，0 failed，0 skipped |
| 前端全量 | ✅ 17 files / 200 passed |
| 本地与 Docker 构建 | ✅ 139 modules |
| Alembic | ✅ 017 current/head；check 无新操作；空表往返、非空降级拒绝、trigger 防篡 |
| 路由 / 表 | ✅ 67 条 API；28 张 ORM 应用表；29 张物理表 |
| 测试库 | ✅ 全部应用表残留 0 |
| 运行态 | ✅ backend/frontend/PostgreSQL 运行；PostgreSQL healthy；后端/前端 HTTP 200 |
| 开发库 | ✅ 只读核对；admin_audit_logs 为 0，既有业务数据未被测试修改 |

下一固定轮次为 P8.2：用户端/管理员端 E2E、任务恢复和全链路一致性。P8.3/P8.4 继续按性能可靠性、华为云部署与综合安全执行，不增加轮次。

从 P8.2 起，码道实现轮次只编写少量核心测试，不运行 pytest、Vitest、构建、迁移往返、Docker 重建或 HTTP 烟测。每个新功能默认 1 个正常路径和 1 个关键失败路径，确有并发/恢复风险时至多再加 1 个样例；集中验收默认只运行变更模块定向测试、1 条核心烟测和必要构建，不再每轮运行完整全量。

### P8.2 — 全链路恢复与一致性 ✅ 已完成并经码道独立收口

| 交付物 | 状态 |
|--------|------|
| RecoveryService + FastAPI lifespan 集成 | ✅ |
| 恢复配置（ENABLED/STALE_SECONDS/BATCH_SIZE） | ✅ |
| PostgreSQL advisory lock 互斥 | ✅ |
| Paper/AnalysisTask/LearningExplanation/QATurn/ExportReport 恢复逻辑 | ✅ |
| 前端 usePolling 共享轮询 composable | ✅ |
| 所有轮询页面 401 处理 + 安全错误消息 | ✅ |
| ExperimentDataView 刷新恢复活跃任务 | ✅ |
| 后端测试 3 个函数 | ✅ |
| 前端测试 2 个函数 | ✅ |
| 隔离浏览器手工烟测清单 1 条 | ✅ 已编写，待发布前执行 |
| systemDesign/SDD/Sprint 文档更新 | ✅ |

独立审查修正了三处 Vue 语法破坏、共享轮询未实际复用、阻塞恢复锁、扫描事务内执行外部工作、缺失输入猜测重放、不安全 E2E 脚本、TaskDetail 遗漏字段、实验刷新上下文和测试/文档口径。RecoveryService 现使用非阻塞事务锁、固定顺序有限扫描与提交后派发；仅指标、实验、学习解释、问答安全重放，论文解析、审阅和导出缺失持久输入时固定 FAILED。

| 集中验收项 | 实际结果 |
|---|---|
| 后端恢复定向 | ✅ 3 passed，5 个第三方弃用警告 |
| 前端共享轮询定向 | ✅ 2 passed |
| backend/frontend 镜像构建 | ✅ 前端 140 modules transformed |
| 隔离只读健康接口 | ✅ `GET /api/v1/health` → 200 |
| 浏览器手工流程 | ⏸ 当前浏览器控制能力不可用，未执行且不记为通过 |
| 开发库 | ✅ 未用于测试，未修改业务数据 |

新 backend/frontend 镜像已构建。为避免默认开启的 startup recovery 扫描开发库，本轮没有替换正在运行的旧后端容器。详细问题、根因和修正记录见 `ProjectDocs/bugfix-report/P8.2-全链路恢复与轮询一致性收口.md`。

P8.2 原始提示词继续保留在归档第 30 节。下一固定轮次为 P8.3 性能、可靠性、限流与可观测性收口；P8.4 仍为最后一轮华为云部署、备份恢复和综合安全验收，不增加轮次。

P8.3 完整提示词已写入 `docs/CODEARTS_NEXT_PROMPT.md` 并原文归档为第 31 节；正文逐字一致（5,325 字符）。NEXT 文件 SHA-256 为 `5457A54F3F83CE64D0697528104E69EAAC20CC5935360B0485131AD561DCB9AD`，ARCHIVE 文件 SHA-256 为 `E959742AAE407B2CBA856BA99D0C0D631AA967BEB6E3E52907D0158DB7591C95`。提示词要求码道最多只编写 3 个后端样例，不新增前端/E2E/压测，且不得运行任何测试、构建、迁移、Docker、HTTP 或浏览器命令。

### P8.3 性能、可靠性、限流与可观测性收口 ✅ 已完成并经码道独立收口

**实现者**: CodeArts（码道）
**日期**: 2026-07-16

P8.3 在 P8.2 已验收基础上完成以下实现：

**新增模块**：
- `core/request_tracing.py` — 请求追踪中间件（X-Request-ID 生成/复用、contextvars 传播、结构化请求日志）
- `core/rate_limiter.py` — 固定窗口限流器（classify_scope、resolve_client_ip、parse_trusted_cidrs）
- `core/rate_limit_middleware.py` — 限流中间件（429 JSON envelope + Retry-After + X-Request-ID）

**修改模块**：
- `api/health.py` — 新增 /health/live 和 /health/ready
- `core/database.py` — pool_pre_ping + 有界池参数 + _build_engine_kwargs
- `services/recovery_service.py` — ThreadPoolExecutor 替代 daemon Thread + shutdown_executor
- `main.py` — 中间件注册 + executor shutdown
- `core/errors.py` — X-Request-ID + 结构化日志
- `api/tasks.py` — N+1 修复（selectinload）+ 无界查询 limit(200)
- `services/qa_service.py` — N+1 修复（批量聚合查询）
- `api/papers.py` — 审查后保持完整 Evidence 返回契约，不做静默固定截断

**新增测试**：
- `tests/test_api/test_p83_observability.py` — 3 个后端测试函数

**新增配置项**：rate_limit_*（7 项）、db_pool_*（4 项）、recovery_max_workers（1 项）

**新增 API**：GET /api/v1/health/live、GET /api/v1/health/ready（路由基线 67→69）

**N+1/无界查询修复**：
- list_reviews：3 查询替代 1+N+M（selectinload findings + evidences）
- list_qa_conversations：2 批量查询替代 2N 逐会话查询
- list_tasks：添加 .limit(200)
- list_evidences：撤销会静默丢失论文证据的 .limit(500)

独立审查发现并修正：request_tracing 导入即崩溃；非严格 UUID4 可穿透；未知原始路径进入日志；固定窗口约两倍才过期；实验上传未归 upload；health 豁免测试反而期待 429；可信代理链解析与环境变量口径不一致；异常 traceback 可能带出正文；async ready 阻塞事件循环；executor 注入未展开参数且 shutdown 不等待；Review selectinload 条件冲突；Evidence 固定 500 会静默丢失证据。

| 集中验收项 | 实际结果 |
|---|---|
| P8.3 后端定向 | ✅ 3 passed，5 个第三方弃用警告 |
| 审阅/问答查询回归 | ✅ 2 passed，5 个第三方弃用警告 |
| 后端镜像构建 | ✅ 成功 |
| 隔离 HTTP 烟测 | ✅ live=200、ready=200、missing=404 |
| 全量/前端/性能压测 | 按轻量策略未执行 |
| 开发库 | ✅ 未用于测试，未修改业务数据 |

新后端镜像已构建。为避免默认 startup recovery 扫描开发库，未替换正在运行的旧后端容器。下一固定轮次仅剩 P8.4 华为云部署、备份恢复和综合安全验收，不增加轮次。

P8.4 最终轮完整提示词已写入 `docs/CODEARTS_NEXT_PROMPT.md`，并原文归档为 `docs/CODEARTS_PROMPT_ARCHIVE.md` 第 32 节；两处正文逐字一致（6,806 字符）。NEXT 文件 SHA-256 为 `4C2E0D611D2405D88612746697A8FB03E4EFCB72802A54F7C17820772C5DADF4`，ARCHIVE 文件 SHA-256 为 `ABCBB5ADD9FAA87FB3F34E5C631527C50950F7752BA42220BC157D921303D905`。提示词要求码道实现 OBS 适配和生产部署/备份/安全资产，最多只编写 3 个轻量后端样例，且不得运行测试、构建、迁移、Docker、HTTP、浏览器、外网或真实云服务命令。P8.4 后不再新增开发轮次。

### P8.4 码道初版交付（后续已完成独立收口）

**实现者**: CodeArts（码道）
**日期**: 2026-07-16

P8.4 在 P2～P8.3 已实现并收口基础上完成以下实现：

**OBSStorage 实现**：
- `utils/storage.py` 重写：OBSStorage（esdk-obs-python SDK，延迟导入，ECS Agency/ENV fallback，SSE-OBS/SSE-KMS，严格 key 规范化）
- 新增 `materialize(storage_key)` 上下文管理器：LocalStorage 直接 yield；OBSStorage 下载到唯一临时文件，finally 自动清理
- 工厂单例 + close 生命周期，由 lifespan 关闭

**生产配置校验**：
- `PAPERLENS_ENV=local/test/production` + production model_validator
- 拒绝 debug/local storage/HTTP OBS/占位 JWT/非 Secure cookie/缺失 OBS 必需配置/KMS 无 key id
- `docs_enabled` 属性控制生产环境 OpenAPI 文档关闭

**调用者迁移**：
- `api/exports.py`、`services/export_service.py`、`services/experiment_analysis_service.py` 使用 materialize 替代 read_path

**生产部署资产**（`deploy/huawei/`）：
- `README.md` — 生产部署指南（配置顺序、部署步骤、回滚、安全验收清单）
- `.env.production.example` — 生产环境变量模板
- `docker-compose.prod.yml` — 生产 Compose（独立 migrate、非 root、read-only、资源限制、healthcheck）
- `nginx.prod.conf` — 生产 Nginx（安全响应头、不盲目信任转发头）
- `backup-restore.md` — 备份恢复手册（RDS/OBS/回滚/月度演练）
- `backend/Dockerfile.prod` + `entrypoint.prod.sh` — 生产后端镜像（非 root、secret 文件注入）
- `frontend/Dockerfile.prod` — 生产前端镜像

**新增测试**：
- `tests/test_api/test_p84_production.py` — 3 个后端测试函数

以上为码道初版交付状态；其后的独立审查、直接修正与轻量验收见下节。

## P8.4 华为云部署、OBS 与综合安全独立收口（2026-07-16）

码道初版存在会阻断真实部署的 SDK、Secret、镜像和网络问题：ECS Agency/超时/header 不符合当前 OBS SDK，OBS 下载路径离开上下文即失效，delete 未检查状态；生产设置允许弱 JWT、非验证型 RDS TLS、mock 模型和宽泛端点；迁移绕过 Secret 入口，DSN 暴露在环境；前端构建上下文错误，非 root Nginx 无法在只读根文件系统创建 pid/temp。码道按用户持续授权直接修正，没有增加返工或开发轮次。

最终实现使用 `esdk-obs-python 3.26.2`、ECS Agency `security_provider_policy=ECS`、私有 SSE header、统一 2xx/脱敏错误和安全 `materialize`；生产强制华为 HTTPS、强 JWT、真实 MaaS/Embedding、RDS `verify-full + sslrootcert` 和受限代理 CIDR。migrate/serve 共用 Secret 文件入口，数据库 DSN 不进入 Compose 环境。后端使用 Python 3.13 独立生产依赖，前端 Nginx 使用非特权 8080 与 `/tmp` pid/temp；Compose 只发布前端并使用固定私网、ready/healthz、只读/最小权限和资源限制。

| 轻量验收项 | 最终结果 |
|---|---|
| P8.4 后端定向 | ✅ 3 passed，5 个第三方 SWIG 弃用警告 |
| 后端生产镜像 | ✅ 构建成功；paperlens 非 root/read-only；live 200；docs 404；无 pytest/tests |
| 前端生产镜像 | ✅ 140 modules；nginx 非 root/read-only/cap_drop ALL；healthz 与首页成功 |
| Compose 静态校验 | ✅ 占位 IP 安全失败；显式假值 config --quiet 通过 |
| 全量/迁移/真实云 | 按轻量策略未执行，留待实际部署窗口 |
| 开发库/现有容器 | ✅ 未用于测试，未替换或修改 |

测试仅使用假 Secret 和无效 RDS 域名，未读取 `.env`、未访问真实 RDS/OBS/MaaS、未产生云费用；一次性容器与假 Secret 已清理。P8.4 至此完成并经码道独立收口，既定开发轮次全部结束。下一步不是新的码道提示词，而是用户按 `deploy/huawei/README.md` 准备云资源和 Secret，执行真实部署与小额业务验收。
