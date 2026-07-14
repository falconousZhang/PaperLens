# PaperLens 阶段汇报

> 最后更新：2026-07-14

---

## 一、项目概况

PaperLens 是一个 AI 驱动的学术论文审阅助手，核心流程：

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
| docs/CODEARTS_PROMPT_ARCHIVE.md | 从 Codex rollout JSONL 恢复 8 个逐字原文版本：首次 P1、P1/P2 初版、Docker 执行版、P2.1～P2.5；P2.5 标明为生成后由 Codex 实施 |

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
- 当时 8 张仅骨架表：AnalysisTask, ReviewResult, ReviewFinding, FindingEvidence, MetricRecord, ExperimentFile, ExperimentResult, ExportReport；后续 AnalysisTask/审阅/指标已实现，ExperimentFile 服务/API 于 P5.1 实现，ExperimentResult/ExportReport 仍为骨架
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

码道完成 P2.6 后，Codex 独立复核发现仍有失效锚点和实现态矛盾。经用户授权，本轮由 Codex 直接修正并复验，不再将同一批修复循环交回码道。

#### 独立复核纠偏

P2.6 报告中的“75 个本地链接、0 个失效路径、0 个失效锚点”没有被独立复核复现。真实结果为：

| 指标 | P2.6 报告 | Codex 独立复核 |
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

### Codex 独立审查与直接修复

码道初版后端全量测试为 `102 passed, 0 skipped`。验收没有直接采用自报结论，额外修复了以下问题：

1. 结果批次和任务成功状态分两次提交，无法保证真正的全有或全无。
2. UUID 路径未使用 UUID4 类型校验，非法路径可能落入数据库层。
3. LLM 测试依赖全局可变替换器，并发运行存在串扰风险。
4. 审阅查询没有在 SQL 层同时约束任务用户，缺失任务时存在越权风险。
5. 请求 schema 接受未知字段、缺失 task_type、非法 language 和无上限 Top-K。
6. Evidence/Title 未转义 Prompt 边界标签，原文可提前闭合标签。
7. 重复 Evidence alias 可建立重复关联，rating/confidence 接受字符串形式。
8. 自定义 Pydantic 校验错误中包含 ValueError 对象，统一错误处理无法 JSON 序列化并返回 500。
9. 码道误将 `docs/CODEARTS_NEXT_PROMPT.md` 和 `docs/CODEARTS_PROMPT_ARCHIVE.md` 还原到 HEAD；由 Codex 恢复归档并继续生成下一阶段提示词。

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

### Codex 独立审查与直接修复

码道自报 P3.2 定向 `97 passed`、后端全量 `182 passed` 和 16 个端点。Codex 独立复现确认码道交付时实际定向为 `119 passed`、后端全量为 `182 passed`，业务路由装饰器仍是 12 条，14 张业务表不变。测试通过并未覆盖以下生产缺陷：

- 配置项 `embedding_api_key` 是 SecretStr，直接用于 Header 时实际发送 `Bearer **********`，真实华为鉴权必然失败。
- SQLAlchemy 事务跨越 Embedding 和 LLM 网络调用，增加长事务、连接占用与失败回滚风险。
- 每个 batch 新建 httpx.Client，且非对象响应项、布尔 index、非法构造参数等没有统一领域错误。
- Mock 仅按空格分词，无空格中文 Evidence 无法形成可靠相关性排序。
- SQL 候选加载、外部向量调用和排序职责耦合，非法 Top-K/空维度/返回数量异常缺少防御。

Codex 已直接修复上述问题，增加首批、查询、后续 batch 失败和密钥脱敏测试，并校正文档与真实计数。

用户随后确认 Git 提交 `4659a0b` 由用户本人创建，不属于码道越界操作；开发库中的两条 `back2.pdf` 和一条 `back1.pdf` FAILED 记录同样是用户自己的上传尝试，不属于测试污染。Codex最终测试只使用 `paperlens_test`，该测试库 14 张业务表均为 0，开发库数据完整保留。

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
| P3.2 提示词完整性 | ✅ 下一步文件正文与归档第 12 节一致，SHA-256 `834660c0e482758d3b881f26e2fa7bdaa05922dc027bc5847f67abf22e24d3fd`；随后由 Codex 正常生成 P3.3 |
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

### Codex 独立审查与直接修复

码道初版自报 P3.3 定向 `55 passed`、后端全量 `259 passed` 和 `16` 个端点；Codex 独立复现前两项通过，但业务基线仍是 12 条 `/api/v1` 路由。进一步审查发现：

1. 多 choice 响应只防重复 `index=0`，仍会忽略额外或重复的其他 choice 并猜测结果。
2. 显式传入错误类型、NaN/Infinity 或超出 Settings 上界的配置时，可能泄漏底层异常或绕过直接构造校验。
3. 非列表 messages 没有统一领域错误；未知 finish_reason 的原值会进入异常文本。
4. 缺少 HuaweiMaaSLLMClient 到审阅任务 API 的成功 Evidence 绑定、首维/第二维失败三表零残留，以及 transport 调用点无活动事务测试。
5. README、API 契约和 ProjectDocs 多处仍把 P3.3 写成规划态；配置数量和路由数量也不真实。

Codex 已直接修复并补齐 18 项定向测试。Huawei 适配器现拒绝带凭据/query/fragment 的 base URL、歧义 choice、非有限/越界配置和非列表 messages；错误文本不回显未知 finish_reason。未真实访问华为云或产生费用。

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
| P3.3 提示词完整性 | ✅ 执行正文与归档第 13 节一致，SHA-256 `415edde1fff0c50d3b5c858b3afd2eb1d777d9a0a3fe9c1f32ae91cbf4adf02c`；验收后由 Codex 正常生成 P3.4 |
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
| frontend/src/tests/ReviewResultView.test.ts | 新增 | 码道 20 项 + Codex 6 项缺陷回归，共 26 项 |
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

### Codex 独立审查与直接修正

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

### Codex 独立审查与直接修正

码道初版自报后端 298 passed、前端 61 passed，但存在默认 JWT secret、localStorage token、重放不撤销 family、access 不查 session、reset token 日志泄漏、禁用/锁定枚举、logout 无认证、CASCADE 用户外键等关键问题。Codex 已全部直接修正并补真实行为断言，详见 P3.5 bugfix report。

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

### 码道初版与 Codex 审查

码道初版自报指标定向 37 passed、后端全量 355 passed、Alembic 006，但测试只断言任务创建响应为 201，没有核对后台终态。Codex 复核发现读取表格/Evidence 后 SQLAlchemy 会自动开启事务，初版函数随即把这一正常读事务当作错误，因此真实后台任务必然 FAILED；此外还存在无来源记录可入库、无证据 Checkpoint 为 null、模型和数据集误用同一行文本、Metric options 不区分、活动任务竞态以及过滤/隔离/原子性测试缺失。

Codex 已直接修正：

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

### Codex 独立审查

码道初版 48 项页面定向测试通过，但测试没有揭示 Evidence 仅为占位文字、表格来源/原文缺失、异常来源猜测、无 `task_id` 查询、成功历史范围错误、零结果筛选消失、快速请求竞态和 ProjectDocs 仍为规划态等问题。Codex 已直接修正并补充真实行为断言，详见 `ProjectDocs/bugfix-report/P4.2-Codex独立审查与指标前端交互验收收口.md`。

---

## P4.3 华为云 MaaS LLM 运行配置与安全联调准备（2026-07-14）

### 新增/修改文件

| 文件 | 操作 | 说明 |
|------|------|------|
| docker-compose.yml | 修改 | LLM 变量逐项透传（默认 mock），Embedding 强制 mock |
| backend/paperlens/services/llm_client.py | 修改 | 新增 validate_llm_config() 配置校验函数 |
| backend/paperlens/cli.py | 修改 | 新增 maas-config-check 和 maas-smoke --confirm-billable |
| backend/tests/test_services/test_maas_config.py | 新增并经 Codex 补强 | 配置/CLI/Compose/fake client、占位 Key、完整 endpoint、测试会话隔离 |
| .env.example | 修改 | base URL 说明、去掉 /chat/completions 注释 |
| README.md | 修改 | 启用步骤、安全须知、三种状态区分 |

### 关键实现说明

1. Docker Compose 将 `PAPERLENS_LLM_BACKEND` 从硬编码 `mock` 改为 `${PAPERLENS_LLM_BACKEND:-mock}` 透传，LLM 6 个变量逐项透传，`PAPERLENS_EMBEDDING_PROVIDER` 硬编码为 `mock`。
2. `validate_llm_config()` 不联网，构造 HuaweiMaaSLLMClient 做配置预检；mock 模式不要求 MaaS 配置。
3. `maas-config-check` 输出非敏感摘要（backend、scheme/host/path、model、api_key_configured true/false）；`maas-smoke` 必须带 `--confirm-billable` 且 backend=huawei_maas。
4. 码道初版未修改 HuaweiMaaSLLMClient 的 TLS/Bearer 主流程；Codex 追加完整 endpoint 和占位 Key 的失败前置，并修正 CLI 与测试隔离。未新增迁移或依赖。用户明确授权后完成真实最小烟测；Codex 未读取或输出本地 Key。

### Codex 独立审查与修正

码道初版虽然自报 11 项定向通过，但真实 huawei config-check 会因 `ParseResult.host` 崩溃，Docker 三项 Compose 测试被跳过，占位 Key 和完整 endpoint 未失败前置，CLI fake 测试未覆盖真实确认门/单次调用，烟测允许 2048 completion token，失败会回显底层异常，README 还会在容器重新加载 `.env` 前检查旧配置。更关键的是 pytest 会继承未来运行容器中的真实 MaaS backend 与 Key，存在回归测试意外计费风险。

Codex 已直接修正上述问题：配置检查使用 hostname；烟测上限 32 token 且固定安全失败；实际 Compose 文件只读挂载以消除 skip；conftest 在导入 Settings 前强制两类 provider 为 mock、endpoint 为 `.invalid` 并移除继承 API Key；同时补齐 ProjectDocs 01～08、SDD、独立 Sprint 和 bugfix report。

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

### 码道初版与 Codex 审查

码道初版新增了 008、CSV/XLSX/XLS 解析器、上传/列表/详情 API，并自报 P5.1 定向 59、后端全量 494、前端 106。Codex 复核确认初版存在以下验收阻断：008 会 UPDATE/DELETE 用户数据；UploadFile 一次性 `read()` 导致内存风险；同步解析直接阻塞 async 路由；生产解析器输入为原始 bytes 而非服务端路径；完整 SHA-256 被公开；XLSX 未完整拒绝反斜杠穿越、重复 entry、单项压缩比、宏内容类型、外部 relationship 和任意形式公式节点；并发重复可能返回 500 并留下多余对象；storage/flush/commit 补偿不完整；成功 commit 后 refresh 失败会形成数据库/对象不一致；错误和清理日志可能包含原始解析信息、文件路径或用户文件名；SDD、Sprint 和多数状态文档仍停留在规划态。

Codex 已直接修正并完成收口：

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

P5.2 统计摘要、ExperimentResult、实验分析任务和 result API 仍未实现；指标交叉验证与实验前端属于 P5.3，delete API 和报告导出继续后置。
