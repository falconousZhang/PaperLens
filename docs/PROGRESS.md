# PaperLens 阶段汇报

> 最后更新：2026-07-13

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
| 后端测试（Docker） | ✅ 63 passed, 0 skipped |
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
