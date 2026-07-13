# PaperLens 实施状态文档

## 阶段定义

| 阶段 | 名称 | 目标 | 状态 |
|------|------|------|------|
| P0 | 需求分析与架构设计 | 完成需求文档、架构设计、数据模型、API 契约、安全设计 | ✅ 已完成 |
| P1 | 工程骨架搭建 | 可运行的项目骨架、ORM 模型、数据库迁移、健康检查 | ✅ 已完成 |
| P2 | 核心解析流程 | PDF 上传、解析、分块、向量索引 | 🔄 进行中 |
| P3 | 审阅生成 | 证据检索、LLM 审阅、Evidence 绑定 | ⬜ 未开始 |
| P4 | 指标提取 | 表格提取、指标识别、口径判断 | ⬜ 未开始 |
| P5 | 实验数据分析 | CSV/Excel 上传、统计计算、交叉验证 | ⬜ 未开始 |
| P6 | 报告导出 | Markdown/PDF/DOCX 导出 | ⬜ 未开始 |
| P7 | 前端开发 | Vue3 页面开发、交互优化 | 🔄 进行中 |
| P8 | 集成测试与部署 | 端到端测试、云端部署、性能调优 | ⬜ 未开始 |

## P0 阶段清单

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P0-01 | docs/product-requirements.md | ✅ 已完成 |
| P0-02 | docs/architecture.md | ✅ 已完成 |
| P0-03 | docs/data-model.md | ✅ 已完成 |
| P0-04 | docs/api-contract.md | ✅ 已完成 |
| P0-05 | docs/security-design.md | ✅ 已完成 |
| P0-06 | docs/IMPLEMENTATION_STATUS.md | ✅ 已完成 |

## P1 阶段清单

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P1-01 | 后端项目初始化（FastAPI + SQLAlchemy + Alembic） | ✅ 已完成 |
| P1-02 | 前端项目初始化（Vue3 + TypeScript + Vite） | ✅ 已完成 |
| P1-03 | 数据库迁移脚本（001_initial） | ✅ 已完成 |
| P1-03b | 数据库迁移脚本（002_constraints，CheckConstraints） | ✅ 已完成 |
| P1-04 | ORM 模型（13 张表 + 1 张关联表） | ✅ 已完成 |
| P1-05 | GET /api/v1/health 健康检查 | ✅ 已完成 |
| P1-06 | 统一错误响应结构 | ✅ 已完成 |
| P1-07 | LLMClient 接口 + MockLLMClient | ✅ 已完成 |
| P1-08 | 基础 pytest 测试 | ✅ 已完成 |
| P1-09 | 前端首页 + 健康检查调用 + 后端不可用提示 | ✅ 已完成 |
| P1-10 | Docker Compose（PostgreSQL + backend + frontend） | ✅ 已完成 |
| P1-11 | .env.example / .gitignore / README.md | ✅ 已完成 |

## P2 阶段清单

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P2-01 | 论文上传 API | ✅ 已完成 |
| P2-02 | PDF 解析服务（PyMuPDF + pdfplumber） | ✅ 已完成 |
| P2-03 | 章节识别服务 | ✅ 已完成 |
| P2-04 | 表格提取服务 | ✅ 已完成 |
| P2-05 | 文本分块服务 | ✅ 已完成 |
| P2-06 | 向量索引服务（FAISS） | ⬜ 未实现（仅预留接口） |
| P2-07 | 后台任务框架（FastAPI BackgroundTasks，仅 MVP） | ✅ 已完成 |
| P2-08 | Evidence 提取（page-local，PyMuPDF block + real bbox） | ✅ 已完成 |
| P2-09 | 本地存储服务（LocalStorage，storage_key 格式 papers/{uuid}/source.pdf） | ✅ 已完成 |
| P2-10 | 统一错误响应（含 details 字段） | ✅ 已完成 |
| P2-11 | Evidence 列表 API（GET /papers/{paper_id}/evidences） | ✅ 已完成 |
| P2-12 | UUID 路径参数校验（无效 UUID 返回 422） | ✅ 已完成 |
| P2-13 | 数据库迁移脚本（003_normalized_and_error，normalized_text_content + error_message） | ✅ 已完成 |
| P2-14 | 前端论文详情页（章节/页面/证据 Tab、高亮跳转、轮询） | ✅ 已完成 |
| P2-15 | 前端论文上传页 | ✅ 已完成 |
| P2-16 | 前端论文列表页 | ✅ 已完成 |

## P2.3 阶段清单（测试隔离与验收真实性修复）

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P2.3-01 | database.py 延迟初始化 + configure_engine() + _SessionLocalProxy | ✅ 已完成 |
| P2.3-02 | conftest.py 最早阶段设置测试库 URL + _assert_test_database() | ✅ 已完成 |
| P2.3-03 | test_health.py 完全重写（幂等建库、迁移失败 pytest.fail、轮询等待、dev_db 隔离断言） | ✅ 已完成 |
| P2.3-04 | test_pdf_parser.py 重写（Evidence 非空断言、mock mismatch 测试、char range 验证） | ✅ 已完成 |
| P2.3-05 | _safe_error_message() 安全错误映射 | ✅ 已完成 |
| P2.3-06 | UploadFile try/finally 关闭 | ✅ 已完成 |
| P2.3-07 | 表格 bbox 验证 + flush + rollback | ✅ 已完成 |
| P2.3-08 | pdf_parser.py 静默异常改为 logger.warning() | ✅ 已完成 |
| P2.3-09 | models.py _enum_in_sql() 修复 CheckConstraint SQL 格式 | ✅ 已完成 |
| P2.3-10 | PaperDetailView.vue 重写（loadError + pollError + highlightRange 验证 + pageRequestId） | ✅ 已完成 |
| P2.3-11 | PaperDetailView.test.ts 重写为 11 项测试 | ✅ 已完成 |
| P2.3-12 | Docker 全量测试 46/46 通过（含 dev_db_not_polluted + error_message_is_safe） | ✅ 已完成 |
| P2.3-13 | alembic check 无差异 | ✅ 已完成 |
| P2.3-14 | E2E 回归验证通过 | ✅ 已完成 |
| P2.3-15 | 文档同步（data-model.md, api-contract.md, IMPLEMENTATION_STATUS.md） | ✅ 已完成 |

## P2.4 阶段清单（事务边界与验收收口）

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P2.4-01 | upload_paper() 重写：扩展名校验纳入资源管理 + file_closed 标志 + finally 关闭 UploadFile + storage.delete 失败记录 warning | ✅ 已完成 |
| P2.4-02 | db_helpers.py 新建：ensure_test_database() 连接维护库 postgres 创建 paperlens_test；is_test_db_required()；强制模式 fail 不 skip | ✅ 已完成 |
| P2.4-03 | truncate_test_tables() 重写：数据库名守卫 + 单条 TRUNCATE CASCADE + verify_no_test_residuals() + test_cleanup_failure_propagates | ✅ 已完成 |
| P2.4-04 | _process_paper() 表格 SAVEPOINT：db.begin_nested() 包裹每个表格，失败只 rollback SAVEPOINT 不影响外层事务 | ✅ 已完成 |
| P2.4-05 | test_health.py 完全重写：test_evidence_detail_fields_strict 逐字段严格比较；test_error_message_safe_with_injected_exception 注入真实内部信息模式 | ✅ 已完成 |
| P2.4-06 | test_table_savepoint_degradation：mock parse_pdf 返回合法+非法表格，断言论文仍 PARSED、核心数据完整 | ✅ 已完成 |
| P2.4-07 | PaperDetailView.vue 重写：stopPolling()/startPolling() 抽取；evidenceDegraded 统一检查 null/越界/mismatch；删除 isNavigatingToEvidence | ✅ 已完成 |
| P2.4-08 | PaperDetailView.test.ts 重写为 14 项测试 | ✅ 已完成 |
| P2.4-09 | Docker 全量后端测试 49 passed, 1 skipped | ⚠️ 历史结果（skip 已在 P2.5 消除） |
| P2.4-10 | 前端测试 14/14 通过 | ✅ 已完成 |
| P2.4-11 | 开发库隔离验证通过（测试前后 papers 数量不变） | ✅ 已完成 |
| P2.4-12 | alembic check 无差异 | ✅ 已完成 |
| P2.4-13 | E2E 回归验证通过（上传→PARSED→Evidence→页面数据） | ✅ 已完成 |
| P2.4-14 | 文档同步（IMPLEMENTATION_STATUS.md, README.md） | ✅ 已完成 |

## P2.5 阶段清单（验收去伪与并发翻页修复）

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P2.5-01 | 确定性 nullable Evidence 数据与真实详情 API 严格断言，移除条件 skip | ✅ 已完成 |
| P2.5-02 | upload_paper() 单一 UploadFile close 出口、NamedTemporaryFile 上下文管理和资源所有权转移 | ✅ 已完成 |
| P2.5-03 | 上传扩展名、magic、超限、read/hash/storage/Paper/commit/task 失败及成功路径生命周期测试 | ✅ 已完成（10 项） |
| P2.5-04 | PaperTable `page_number=0` 真实触发 PostgreSQL 约束，SAVEPOINT 仅跳过非法表格 | ✅ 已完成 |
| P2.5-05 | 测试清理的数据库名守卫、连接失败、TRUNCATE 失败和残留检测传播测试 | ✅ 已完成 |
| P2.5-06 | 前端移除 pageLoading 丢请求逻辑，使用 request id 防陈旧响应覆盖 | ✅ 已完成 |
| P2.5-07 | 严格乱序响应、同页恰好一次、快速 1→2→1 导航测试 | ✅ 已完成 |
| P2.5-08 | Docker 后端全量测试 | ✅ 63 passed, 0 skipped |
| P2.5-09 | 前端测试与构建 | ✅ 15 passed，生产构建成功 |
| P2.5-10 | 开发库隔离与测试库清理 | ✅ 最终全量测试开发库 28→28，测试库 14 张业务表均为 0 |
| P2.5-11 | Alembic 与双页 HTTP E2E | ✅ head/无差异；2 页、2 Evidence、char range 全匹配 |
| P2.5-12 | 码道提示词统一归档 | ✅ 从 Codex rollout 恢复 8 个原文版本到 `docs/CODEARTS_PROMPT_ARCHIVE.md` |

## P3 阶段清单（待细化）

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P3-01 | Evidence 检索服务 | ⬜ 未开始 |
| P3-02 | Prompt 模板设计 | ⬜ 未开始 |
| P3-03 | MaaSLLMClient 实现 | ⬜ 未开始 |
| P3-04 | 审阅结果解析与 Evidence 绑定验证 | ⬜ 未开始 |
| P3-05 | 审阅结果 API | ⬜ 未开始 |

## P4 阶段清单（待细化）

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P4-01 | 表格指标提取服务 | ⬜ 未开始 |
| P4-02 | Checkpoint 口径判断规则引擎 | ⬜ 未开始 |
| P4-03 | 指标记录 API | ⬜ 未开始 |

## P5 阶段清单（待细化）

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P5-01 | CSV/Excel 文件上传 API | ⬜ 未开始 |
| P5-02 | 实验数据解析服务（pandas） | ⬜ 未开始 |
| P5-03 | 统计计算服务 | ⬜ 未开始 |
| P5-04 | 指标交叉验证服务 | ⬜ 未开始 |

## P6 阶段清单（待细化）

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P6-01 | Markdown 报告生成 | ⬜ 未开始 |
| P6-02 | PDF 报告生成 | ⬜ 未开始 |
| P6-03 | DOCX 报告生成 | ⬜ 未开始 |
| P6-04 | 报告导出 API | ⬜ 未开始 |

## P7 阶段清单（待细化）

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P7-01 | 论文上传页面 | ✅ 已完成 |
| P7-02a | 论文详情、页面文本与 Evidence normalized 字符区间高亮 | ✅ 已完成 |
| P7-02b | LLM 审阅结果展示页面 | ⬜ 未开始 |
| P7-03 | 指标分析页面 | ⬜ 未开始 |
| P7-04 | 报告导出页面 | ⬜ 未开始 |

## P8 阶段清单（待细化）

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P8-01 | 端到端集成测试 | ⬜ 未开始 |
| P8-02 | 云端部署（ECS + RDS + OBS + ModelArts） | ⬜ 未开始 |
| P8-03 | 性能调优 | ⬜ 未开始 |
| P8-04 | 安全审计 | ⬜ 未开始 |
