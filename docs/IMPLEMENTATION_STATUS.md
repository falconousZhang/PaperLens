# PaperLens 实施状态文档

## 阶段定义

| 阶段 | 名称 | 目标 | 状态 |
|------|------|------|------|
| P0 | 需求分析与架构设计 | 完成需求文档、架构设计、数据模型、API 契约、安全设计 | ✅ 已完成 |
| P1 | 工程骨架搭建 | 可运行的项目骨架、ORM 模型、数据库迁移、健康检查 | ✅ 已完成 |
| P2 | 核心解析流程 | PDF 上传、解析、分块、向量索引 | ✅ 已完成 |
| P3 | 审阅生成与身份基础 | 证据检索、LLM 审阅、Evidence 绑定、真实用户认证与 RBAC | ✅ 已完成 |
| P4 | 指标提取与 MaaS 运行准备 | 表格提取、指标识别、口径判断、LLM 安全运行配置 | ✅ 已完成（真实 MaaS 最小烟测成功） |
| P5 | 实验数据分析 | CSV/Excel 上传、统计计算、交叉验证 | ✅ 已完成（P5.1～P5.3b） |
| P6 | 报告导出 | Markdown/PDF/DOCX 导出 | ✅ P6.1～P6.2 已完成 |
| P7 | 用户端与管理端应用 | Vue3 用户页面、认证页面、管理员 API 与管理后台 | 🔄 进行中 |
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
| P2.5-12 | 码道提示词统一归档 | ✅ 从 码道 rollout 恢复 8 个原文版本到 `docs/CODEARTS_PROMPT_ARCHIVE.md` |

## P2.6 阶段清单（ProjectDocs 实现态校准）

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P2.6-01 | SDD 本地链接修复 | ⚠️ 文件路径 48→0，但独立复核仍有 17 个失效锚点 |
| P2.6-02 | API 实现态校准（8 CURRENT + PLANNED 标记） | ✅ 04/09/模块设计/spec/tasks |
| P2.6-03 | 数据模型校准（14 表实现状态 + CheckConstraint 对齐） | ✅ 03/08 |
| P2.6-04 | 前端校准（依赖版本/路由/测试数量/Element Plus PLANNED） | ✅ 07/10/sprint |
| P2.6-05 | project-config.yaml 状态修复 | ✅ |
| P2.6-06 | 跨文档一致性检查 | ✅ SHA-256/Auth/Element Plus/Pinia 等修正 |
| P2.6-07 | 验证（git diff --check + 允许范围 + 链接检查） | ⚠️ diff/范围通过，原锚点检查未按 GFM slug 验证 |
| P2.6-08 | 本轮未运行测试 | 沿用 P2.5 历史验收结果 |

## P2.7 阶段清单（ProjectDocs 验收去伪与文档收口）

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P2.7-01 | 可复现的 Markdown 路径与 GFM 标题锚点检查器 | ✅ 修正前 75/0/17，修正后 75/0/0 |
| P2.7-02 | tasks.md 17 个失效标题锚点修复 | ✅ 已完成 |
| P2.7-03 | 上传 title/PROCESSING 状态及 Swagger 地址校准 | ✅ 已完成 |
| P2.7-04 | Evidence 过滤、DELETE paper、Element Plus 实现态校准 | ✅ 已完成 |
| P2.7-05 | finding_evidences 表名与物理约束/显式索引分层 | ✅ 已完成 |
| P2.7-06 | project-config、Sprint 与 bugfix 报告收口 | ✅ 已完成 |
| P2.7-07 | 独立静态验收 | ✅ 8 API、14 表、4 路由、15 测试定义；diff check 与禁止范围通过 |
| P2.7-08 | 业务代码和产品测试 | ✅ 无业务代码变更；本轮未运行产品测试 |

## P3 阶段清单

### P3.1 — 基于 MockLLM 的结构化审阅后端闭环

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P3.1-01 | ReviewDimension 枚举（7 维度：OVERALL/SOUNDNESS/NOVELTY/CLARITY/SIGNIFICANCE/REPRODUCIBILITY/COMPLETENESS） | ✅ 已完成 |
| P3.1-02 | Evidence 候选选择（确定性排序 page_number/created_at/id ASC，Top-K=8） | ✅ 已完成 |
| P3.1-03 | Prompt 构造（临时别名 E1/E2…、安全边界、语言指令） | ✅ 已完成 |
| P3.1-04 | MockLLMClient 重写（按 dimension/evidence_aliases 返回确定性 JSON） | ✅ 已完成 |
| P3.1-05 | Pydantic 严格输出解析（extra=forbid、代码围栏拒绝、dimension 匹配、rating 1-5、confidence 0-1、OVERALL verdict 规则） | ✅ 已完成 |
| P3.1-06 | Evidence 绑定（VERIFIED/UNVERIFIED 规则、全有或全无原子写入、失败回滚） | ✅ 已完成 |
| P3.1-07 | 4 个后端 API（POST/GET /papers/{id}/tasks、GET /tasks/{id}、GET /papers/{id}/reviews） | ✅ 已完成 |
| P3.1-08 | P3.1 定向测试（1 项 LLM Client + 30 项 Review Service + 22 项 API） | ✅ 53 passed |
| P3.1-09 | Docker 后端全量回归 | ✅ 115 passed, 0 skipped |
| P3.1-10 | 前端测试 15 passed，构建成功 | ✅ 已完成 |
| P3.1-11 | alembic check 无差异 | ✅ 已完成 |
| P3.1-12 | Markdown 链接检查 75/0/0 | ✅ 已完成 |
| P3.1-13 | 开发库隔离验证 | ✅ 已完成 |
| P3.1-14 | 码道独立审查与直接修复（事务原子性、UUID4、依赖注入、越权查询、严格 schema、Prompt 边界、统一 422） | ✅ 已完成 |

### P3.2 — 华为云优先的 Embedding 抽象与语义 Evidence 检索

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P3.2-01 | EmbeddingClient 抽象接口（embed(texts) -> vectors） | ✅ 已完成 |
| P3.2-02 | MockEmbeddingClient（中英文词项 hashing/bag-of-words、sha256 稳定、归一化、相关词影响排序） | ✅ 已完成 |
| P3.2-03 | validate_embeddings() + cosine_similarity() 工具函数 | ✅ 已完成 |
| P3.2-04 | HuaweiMaaSEmbeddingClient（SecretStr 正确解包、HTTPS/配置校验、单客户端批处理、index 恢复、严格响应验证、安全错误） | ✅ 已完成 |
| P3.2-05 | evidence_retriever.py（DB 候选加载与外部推理解耦、按维度精确余弦检索、Evidence 只 embed 一次、Top-K、同论文隔离） | ✅ 已完成 |
| P3.2-06 | review_service.py 集成（公开 get_embedding_client 工厂；外部 Embedding/LLM 调用期间不持有数据库事务；结果批次原子提交） | ✅ 已完成 |
| P3.2-07 | config.py 新增 6 个 embedding 配置项（provider/base_url/model/api_key/timeout/batch_size） | ✅ 已完成 |
| P3.2-08 | tasks.py 新增 embedding_client 依赖注入 | ✅ 已完成 |
| P3.2-09 | P3.2 定向测试（31 EmbeddingClient + 37 HuaweiMaaS + 17 EvidenceRetriever + 34 ReviewService + 23 API） | ✅ 142 passed |
| P3.2-10 | Docker 后端全量回归 | ✅ 205 passed, 0 skipped |
| P3.2-11 | 前端测试 15 passed，构建成功 | ✅ 已完成 |
| P3.2-12 | alembic check 无差异 | ✅ 已完成 |
| P3.2-13 | P3.2 执行后提示词正文与归档第 12 节 SHA-256 一致；验收后由码道正常生成 P3.3 并归档第 13 节 | ✅ 已完成 |
| P3.2-14 | 端点/表计数不变（12 条 `/api/v1` 路由、14 张业务表、4 条 task/review 路由） | ✅ 已完成 |
| P3.2-15 | 码道独立审查与直接修复（密钥解包、事务边界、华为响应校验、中文检索、原子失败与文档去伪） | ✅ 已完成 |
| P3.2-16 | 测试库清理与开发库隔离 | ✅ 测试库 14 表为 0；用户确认开发库 3 条 back1/back2 FAILED 记录是本人上传尝试 |

### P3.3 — 华为云 MaaS 真实生成式模型适配器

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P3.3-01 | LLMError 领域异常（配置/网络/HTTP/JSON/响应结构错误统一安全转换） | ✅ 已完成 |
| P3.3-02 | HuaweiMaaSLLMClient（MaaS 标准 API V2、非流式、SecretStr 正确解包、HTTPS 校验、messages 校验、stream=false、max_completion_tokens、finish_reason=stop 严格验证） | ✅ 已完成 |
| P3.3-03 | 删除进程级可变 _llm_client 单例和 set_llm_client/reset_llm_client；get_llm_client() 每次根据配置构造 | ✅ 已完成 |
| P3.3-04 | config.py 新增 6 个 LLM 配置项（backend/base_url/model/api_key/timeout/max_completion_tokens） | ✅ 已完成 |
| P3.3-05 | Huawei MockTransport 走完整审阅任务：成功绑定、首维/第二维失败零残留、外部调用无活动事务 | ✅ 3 passed |
| P3.3-06 | .env.example 更新（huawei_maas 注释、LLM/Embedding 完整配置模板） | ✅ 已完成 |
| P3.3-07 | P3.3 定向测试（70 项客户端/工厂 + 3 项 Huawei 审阅 API 集成） | ✅ 73 passed |
| P3.3-08 | Docker 后端全量回归 | ✅ 277 passed, 0 skipped |
| P3.3-09 | 前端测试 15 passed，构建成功 | ✅ 已完成 |
| P3.3-10 | alembic check 无差异 | ✅ 已完成 |
| P3.3-11 | 执行提示词正文与归档第 13 节 SHA-256 一致；验收后正常生成 P3.4 | ✅ `415edde1...f02c` |
| P3.3-12 | 端点/表计数不变（12 条 `/api/v1` 路由、14 张业务表） | ✅ 已完成 |
| P3.3-13 | 码道修复歧义 choice、参数类型/上下界、非列表 messages、错误回显并校准文档 | ✅ 已完成 |
| P3.3-14 | 生成 P3.4 提示词并归档第 14 节，230 行正文一致 | ✅ `502e2d03...ba5d0` |

### P3.4 — 审阅结果前端与完整任务交互

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P3.4-01 | api/index.ts 新增严格 TypeScript 类型（含 TaskType/VerificationStatus）和 API 函数（listTasks/createTask/getTask/listReviews） | ✅ 已完成 |
| P3.4-02 | router/index.ts 新增 /papers/:id/review 路由（name=paper-review） | ✅ 已完成 |
| P3.4-03 | ReviewResultView.vue：完整状态、最新有结果 task_id 选择、历史结果保留、Finding 筛选、Evidence 深链、创建防重复、进度钳制、3 秒轮询、失败重试、timer/旧请求清理 | ✅ 已完成 |
| P3.4-04 | PaperDetailView.vue：PARSED 状态"审阅"入口、route.query.evidence 深链处理（初始加载+watch 变化）、未找到证据提示 | ✅ 已完成 |
| P3.4-05 | ReviewResultView.test.ts：初版 20 项 + 后续 6 项回归（历史结果保留、轮询终态/错误、进度边界、刷新异常、路由陈旧响应） | ✅ 26 passed |
| P3.4-06 | PaperDetailView.test.ts：新增 4 项 Evidence query 测试（初始加载高亮、未知/数组提示、query 变化跳转） | ✅ 19 passed（原 15 + 新 4） |
| P3.4-07 | Docker 后端全量回归 | ✅ 277 passed, 0 skipped |
| P3.4-08 | 前端测试 45 passed，生产构建成功（102 modules transformed） | ✅ 已完成 |
| P3.4-09 | alembic check 无差异 | ✅ head=003 |
| P3.4-10 | 提示词文件 SHA-256 不变 | ✅ NEXT=e820c302... ARCHIVE=8844b0fe... |
| P3.4-11 | 码道独立审查与直接修复（历史结果、轮询错误可见性、终态同步、进度边界、刷新失败、数组 query、严格类型） | ✅ 已完成 |
| P3.4-12 | 生成 P3.5 提示词并归档第 15 节，259 行正文一致 | ✅ `59cd46c6...5ae8` |

### P3.5 — 完整认证、真实用户隔离与 USER/ADMIN RBAC 基础

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P3.5-01 | 后端依赖新增：pwdlib[argon2]==0.2.1、PyJWT==2.9.0、email-validator==2.2.0 | ✅ 已完成 |
| P3.5-02 | config.py 认证配置（必填 32-byte SecretStr、固定 HS256、TTL 上界、cookie secure、锁定参数） | ✅ 码道已纠正 |
| P3.5-03 | enums.py 新增 UserRole（USER/ADMIN）和 UserStatus（ACTIVE/DISABLED） | ✅ 已完成 |
| P3.5-04 | models.py 新增 User（id=String(128)）/AuthSession/PasswordResetToken；Paper/AnalysisTask/ExperimentFile/ExportReport 的 user_id 加 FK 到 users.id | ✅ 已完成 |
| P3.5-05 | 004 初始认证迁移 + 005 无损安全纠正（nullable、唯一索引、RESTRICT FK、demo-user disabled） | ✅ head=005 |
| P3.5-06 | password_service.py（hash_password/verify_password/hash_token/generate_token/is_password_breached/validate_password_strength） | ✅ 已完成 |
| P3.5-07 | token_service.py（create_access_token/decode_access_token） | ✅ 已完成 |
| P3.5-08 | auth_service.py（register/authenticate/refresh/logout/logout-all/change-password/forgot-password/reset-password/update-profile + PasswordResetNotifier 接口） | ✅ 已完成 |
| P3.5-09 | schemas/auth.py（Register/Login/ForgotPassword/ResetPassword/ChangePassword/UpdateProfile 请求 + UserResponse/AuthTokenResponse/MessageResponse） | ✅ 已完成 |
| P3.5-10 | api/auth.py（10 个端点 + refresh cookie 管理） | ✅ 已完成 |
| P3.5-11 | core/deps.py（get_current_user/get_current_user_id/require_admin） | ✅ 已完成 |
| P3.5-12 | cli.py promote-admin 命令（--email --claim-legacy-data） | ✅ 已完成 |
| P3.5-13 | papers.py/tasks.py 删除 `_get_user_id()`，所有端点添加 `user_id: str = Depends(get_current_user_id)` | ✅ 已完成 |
| P3.5-14 | 认证 API/服务/JWT/密码/CLI 安全测试 | ✅ 定向 42 passed |
| P3.5-15 | test_health.py/test_review_tasks.py 适配（创建测试用户+auth headers、覆盖依赖、other-user FK） | ✅ 已完成 |
| P3.5-16 | db_helpers.py 更新（17 张业务表、verify_alembic_revision 默认 005） | ✅ 已完成 |
| P3.5-17 | docker-compose.yml 强制显式 JWT secret；本地 `.env` 安全生成且被忽略 | ✅ 码道已纠正 |
| P3.5-18 | .env.example 仅空变量名与生成说明，无默认 secret | ✅ 码道已纠正 |
| P3.5-19 | 前端 Bearer 拦截器 + 401 single-flight refresh + 每请求最多重放一次 | ✅ 码道已纠正 |
| P3.5-20 | Pinia 纯内存 access/User；bootstrap 只尝试 HttpOnly refresh cookie | ✅ 码道已纠正 |
| P3.5-21 | 前端 router/index.ts 5 个认证路由 + beforeEach 守卫（bootstrap + requiresAuth/guest meta） | ✅ 已完成 |
| P3.5-22 | 前端 LoginView/RegisterView/ForgotPasswordView/ResetPasswordView/ProfileView | ✅ 已完成 |
| P3.5-23 | 前端 App.vue 导航栏+用户信息+退出按钮 | ✅ 已完成 |
| P3.5-24 | 前端 store/API single-flight/安全 redirect/登录注册测试 | ✅ 66 passed |
| P3.5-25 | Docker 后端全量回归 | ✅ 318 passed, 0 skipped |
| P3.5-26 | 前端测试 66 passed，生产构建成功 | ✅ 已完成 |
| P3.5-27 | 独立测试库 005→003→head 往返；开发库不 downgrade | ✅ head=005_auth_security_corrections |
| P3.5-28 | 路由计数 22 条业务路由（12 既有 + 10 auth） | ✅ 已完成 |
| P3.5-29 | 表计数 17 张业务表（14 既有 + 3 auth） | ✅ 已完成 |
| P3.5-30 | 开发库历史数据核对 | ⚠️ P3.4 记录 35/1/1；码道本轮首次计数已为 0/0/0，无法自动恢复或证明删除来源 |

### P3 后续（待细化）

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P3-01 | Evidence 检索服务 | ✅ 已完成（P3.2 语义检索：按维度 cosine similarity 排序 Top-K） |
| P3-02 | Prompt 模板设计 | ✅ 已完成（P3.1 基础版） |
| P3-03 | MaaSLLMClient 实现 | ✅ 已完成（P3.3 HuaweiMaaSLLMClient，MaaS 标准 API V2） |
| P3-04 | 审阅结果解析与 Evidence 绑定验证 | ✅ 已完成（P3.1 MockLLM 版） |
| P3-05 | 审阅结果 API | ✅ 已完成（P3.1 基础版） |
| P3-06 | P3.5 完整用户注册登录、令牌生命周期、密码与个人资料 | ✅ 已完成 |
| P3-07 | P3.5 USER/ADMIN RBAC 与真实资源归属 | ✅ 已完成 |

## P4 阶段清单

### P4.1 — 可追溯实验指标提取与 Checkpoint 口径判断后端

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P4.1-01 | metric_service.py（别名规范化、数值解析、百分号口径统一、Checkpoint 判断、表格/Evidence 提取、去重、后台任务执行） | ✅ 已完成 |
| P4.1-02 | schemas/metric.py（MetricRecordResponse/MetricListResponse/MetricExtractionOptions） | ✅ 已完成 |
| P4.1-03 | api/metrics.py（GET /papers/{id}/metrics + GET /metrics/{id}，用户隔离） | ✅ 已完成 |
| P4.1-04 | tasks.py 扩展支持 METRIC_EXTRACTION（并发活动任务 409 防护） | ✅ 已完成 |
| P4.1-05 | models.py MetricRecord 新增 user_id 列 + CheckConstraint + 索引 | ✅ 已完成 |
| P4.1-06 | 006_metric_user_and_constraints 迁移 | ✅ 已完成 |
| P4.1-07 | main.py 注册 metrics_router | ✅ 已完成 |
| P4.1-08 | 指标规范化、数值、Checkpoint、上下文、来源与去重测试 | ✅ 码道扩充后定向共 67 passed |
| P4.1-09 | API、后台终态、原子失败、严格 schema、过滤、USER/ADMIN 隔离与数据库约束测试 | ✅ 已完成 |
| P4.1-10 | test_review_tasks.py 适配（EXPERIMENT_ANALYSIS 替代 METRIC_EXTRACTION） | ✅ 已完成 |
| P4.1-11 | Docker 后端全量回归 | ✅ 385 passed, 0 skipped |
| P4.1-12 | 前端测试 66 passed，生产构建成功 | ✅ 已完成 |
| P4.1-13 | Alembic 测试库 downgrade/upgrade 往返验证 | ✅ 007→006→head；开发库只向前升级 |
| P4.1-14 | 路由计数 24 条（22 既有 + 2 metrics） | ✅ 已完成 |
| P4.1-15 | 表计数 17 张（006 只加列/索引不加表） | ✅ 已完成 |
| P4.1-16 | 文档同步（README/IMPLEMENTATION_STATUS/PROGRESS） | ✅ 已完成 |
| P4.1-17 | 码道修复后台任务必然失败、来源完整性、UNKNOWN、判别 schema、过滤及并发竞态 | ✅ 007_metric_integrity_corrections |

### P4.2 — 指标分析前端与完整任务交互

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P4.2-01 | api/index.ts 新增严格指标类型、REVIEW/METRIC_EXTRACTION 判别联合、参数边界和指标 API 函数 | ✅ 已完成 |
| P4.2-02 | router/index.ts 新增 /papers/:id/metrics 路由（name=paper-metrics, requiresAuth） | ✅ 已完成 |
| P4.2-03 | MetricAnalysisView.vue：单 task_id 隔离、轮询/409 恢复、独立请求序号、筛选分页、值/口径、来源原文和 Evidence 深链 | ✅ 已完成 |
| P4.2-04 | PaperDetailView.vue：PARSED tabs 区域新增"指标" router-link 入口 | ✅ 已完成 |
| P4.2-05 | MetricAnalysisView.test.ts 扩展状态机、旧响应、409、异常来源、XSS 和零结果筛选 | ✅ 35 passed |
| P4.2-06 | MetricApiAndRoute 4 项 + PaperDetail 20 项，覆盖 body/参数、受保护路由和指标入口 | ✅ 24 passed |
| P4.2-07 | Docker 后端全量回归 | ✅ 385 passed, 0 skipped |
| P4.2-08 | 前端定向 59、全量 106 passed（10 files），生产构建 126 modules | ✅ 已完成 |
| P4.2-09 | Alembic head=007 且 check 无差异，路由 24 条，表 17 张 | ✅ 已完成 |
| P4.2-10 | 测试库残留 0；开发库计数不变（2u/2p/1t/7r/0m） | ✅ 已完成 |
| P4.2-11 | P4.2 输入提示词 SHA-256 在码道执行期间不变 | ✅ EE0D146C...15FB4 |
| P4.2-12 | systemDesign 01～08、SDD、Sprint、README/STATUS/PROGRESS 同步 | ✅ 已完成 |
| P4.2-13 | 码道修正 Evidence 占位、来源详情、task_id 隔离、历史范围、零结果筛选、请求竞态与 409 恢复 | ✅ 已完成 |
| P4.2-14 | 最新前端容器重建；health/login 200、无 token metrics 401、PostgreSQL healthy | ✅ 已完成 |
| P4.2-15 | 浏览器可视化 E2E | ⚠️ 当前会话无可用内置浏览器实例，未执行 |

### P4.3 — 华为云 MaaS LLM 运行配置与安全联调准备

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P4.3-01 | docker-compose.yml LLM 变量安全透传（默认 mock，逐项透传，Embedding 强制 mock） | ✅ 已完成 |
| P4.3-02 | validate_llm_config() 配置校验函数（mock 无需 key，huawei_maas fail-fast） | ✅ 已完成 |
| P4.3-03 | CLI maas-config-check（不联网、非敏感摘要） | ✅ 已完成 |
| P4.3-04 | CLI maas-smoke --confirm-billable（确认门、backend 检查、单次调用、安全输出） | ✅ 已完成 |
| P4.3-05 | .env.example 更新（base URL 说明、去掉 /chat/completions 注释） | ✅ 已完成 |
| P4.3-06 | README 更新（启用步骤、安全须知、三种状态区分） | ✅ 已完成 |
| P4.3-07 | P4.3 定向测试（配置校验/CLI 确认门/FakeTransport/异常安全/Compose 默认） | ✅ 110 passed, 0 skipped |
| P4.3-08 | Docker 后端全量回归 | ✅ 435 passed, 0 skipped |
| P4.3-09 | 前端全量 106 passed，生产构建成功 | ✅ 已完成 |
| P4.3-10 | Alembic head=007，路由 24，表 17，无新迁移 | ✅ 已完成 |
| P4.3-11 | 开发库计数不变（2u/2p/1t/7r/0m） | ✅ 已完成 |
| P4.3-12 | 真实云端最小烟测（首轮安全失败；smoke 关闭思考模式后第二轮成功，35 字符） | ✅ 已完成 |
| P4.3-13 | 码道修正 huawei config-check AttributeError、占位 Key/full endpoint、CLI 单次调用与固定安全失败 | ✅ 已完成 |
| P4.3-14 | Compose 实际文件只读挂载，Docker 三项 skip 消除 | ✅ 已完成 |
| P4.3-15 | pytest 强制两类 provider mock、`.invalid` endpoint，并移除继承 API Key | ✅ 已完成 |
| P4.3-16 | ProjectDocs 01～08、SDD、独立 Sprint 与 bugfix report 收口 | ✅ 已完成 |
| P4.3-17 | smoke 专用 `thinking.type=disabled`、安全失败分类与无第三次请求边界 | ✅ 已完成 |
| P4.3-18 | 真实 GLM 单层 JSON 围栏兼容、防绕过测试及 SQL 参数日志脱敏 | ✅ 138 定向 / 435 全量，0 skipped |

## P5 阶段清单

### P5.1 — CSV/Excel 实验文件安全上传与结构解析 ✅ 已完成

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P5.1-01 | ExperimentFileType 枚举（CSV/XLSX/XLS） | ✅ 已完成 |
| P5.1-02 | ExperimentFile ORM 约束增强（file_type CHECK、file_size>0、file_hash hex64、row_count 1-100000、column_count 1-256、UNIQUE user+paper+hash） | ✅ 已完成 |
| P5.1-03 | 迁移 008_experiment_file_integrity（NOT NULL + CheckConstraints + UniqueConstraint） | ✅ 已完成 |
| P5.1-04 | CSV 解析器（UTF-8/BOM/GB18030、逗号/分号/Tab、dtype 推断、null_count、列名校验） | ✅ 已完成 |
| P5.1-05 | XLSX 解析器（ZIP 安全：entry 数/解压大小/压缩比/路径穿越/加密/宏/外部链接/嵌入对象/公式检测） | ✅ 已完成 |
| P5.1-06 | XLS 解析器（OLE magic 校验、xlrd 解析） | ✅ 已完成 |
| P5.1-07 | columns_info 稳定 JSON（version/encoding/delimiter/sheet_name/columns） | ✅ 已完成 |
| P5.1-08 | StorageBackend.build_key 泛化（PDF 不回归、实验文件 source.csv/xlsx/xls） | ✅ 已完成 |
| P5.1-09 | 实验文件上传服务（流式写临时文件→magic 校验→SHA-256→解析→重复检查→storage→DB→幂等 200/新建 201） | ✅ 已完成 |
| P5.1-10 | POST /api/v1/papers/{paper_id}/experiment-files/upload | ✅ 已完成 |
| P5.1-11 | GET /api/v1/papers/{paper_id}/experiment-files（分页、created_at DESC） | ✅ 已完成 |
| P5.1-12 | GET /api/v1/experiment-files/{file_id}（跨用户 404） | ✅ 已完成 |
| P5.1-13 | Pydantic schema（UploadResponse/ListResponse/Detail） | ✅ 已完成 |
| P5.1-14 | AppError 错误码（415 类型/magic 不符、413 超限、422 内容不可解析、409 论文状态冲突、404 不存在/跨用户） | ✅ 已完成 |
| P5.1-15 | 解析安全测试（编码/分隔符/dtype/limits、ZIP 路径/重复/压缩比/active content/公式、多 sheet、OLE） | ✅ 已完成 |
| P5.1-16 | PostgreSQL API 测试（201/200/401/404/409/413/415/422、并发一行一对象、失败补偿、公开哈希隐藏） | ✅ 已完成 |
| P5.1-17 | openpyxl==3.1.5 + xlrd==2.0.2 + xlwt==1.3.0 固定依赖 | ✅ 已完成 |
| P5.1-18 | Docker 后端全量 527 passed, 0 skipped | ✅ 已完成 |
| P5.1-19 | 前端 10 files / 106 passed；生产构建 126 modules | ✅ 已完成 |
| P5.1-20 | Alembic 008 head + check 无差异；冲突只读中止，007→008→007→008 可逆 | ✅ 已完成 |
| P5.1-21 | 码道修正一次性内存读取、事件循环阻塞、原始 bytes 解析器、哈希公开、迁移 DML、并发竞争和补偿缺口 | ✅ 已完成 |
| P5.1-22 | P5.1 解析/存储/API 定向 103；P4.3/MaaS/审阅广义定向 180；P4.1 指标定向 67，均 0 skipped | ✅ 已完成 |
| P5.1-23 | 测试库 17 表残留 0；开发库实验文件/结果保持 0；最新提交不变 | ✅ 已完成 |

### P5.2 — 确定性统计摘要 ✅ 已完成

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P5.2-01 | 迁移 009（analysis_tasks.experiment_file_id + CHECK + 部分唯一索引） | ✅ 已完成 |
| P5.2-02 | 统计计算服务（Welford mean/stddev + 精确 median + 数值安全） | ✅ 已完成 |
| P5.2-03 | 分析服务（任务创建/后台执行/原子写入 ExperimentResult） | ✅ 已完成 |
| P5.2-04 | 文件完整性复核（SHA-256 重算 + P5.1 magic/结构解析重验） | ✅ 已完成 |
| P5.2-05 | 新增配置 max_experiment_analysis_numeric_cells（默认 5,000,000） | ✅ 已完成 |
| P5.2-06 | POST /api/v1/experiment-files/{file_id}/analysis（201/200 幂等） | ✅ 已完成 |
| P5.2-07 | GET /api/v1/experiment-files/{file_id}/result（200/404） | ✅ 已完成 |
| P5.2-08 | 安全错误消息（固定安全分类，不泄漏内部信息） | ✅ 已完成 |
| P5.2-09 | 码道加固后统计/API/并发/事务定向 72 项 | ✅ 已完成 |
| P5.2-10 | Docker 后端全量 599 passed, 0 skipped | ✅ 已完成 |
| P5.2-11 | 前端 106 passed；生产构建 126 modules | ✅ 已完成 |
| P5.2-12 | 路由 27→29；表 17 不变；Alembic 009 head | ✅ 已完成 |
| P5.2-13 | 码道修正整文件缓存、静默数值降级、并发 409、PENDING 卡死、部分元数据比较和 commit 未知风险 | ✅ 已完成 |

### P5.3a — 论文指标交叉验证后端闭环 ✅ 已完成

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P5.3a-01 | 交叉验证服务（normalize_comparison_key: NFKC→casefold→alnum；checkpoint 映射 MEAN→mean/MAX→max；容差比较） | ✅ 已完成 |
| P5.3a-02 | Comparison service（持久化/幂等/事务原子性/异源 409） | ✅ 已完成 |
| P5.3a-03 | POST /api/v1/experiment-files/{file_id}/comparisons（201/200 幂等） | ✅ 已完成 |
| P5.3a-04 | 扩展 GET /api/v1/experiment-files/{file_id}/result 新增 metric_comparisons: list \| null | ✅ 已完成 |
| P5.3a-05 | Pydantic schema（ComparisonItem/PostComparisonsRequest/PostComparisonsResponse） | ✅ 已完成 |
| P5.3a-06 | 配置项 experiment_comparison_absolute_tolerance（默认 1e-6）+ experiment_comparison_relative_tolerance（默认 0.01） | ✅ 已完成 |
| P5.3a-07 | .env.example + docker-compose.yml 新增两个容差配置 | ✅ 已完成 |
| P5.3a-08 | 服务/Schema/配置单元测试 48 项（规范化、MEAN/MAX、不可验证口径、容差、有限数、严格跨字段关系） | ✅ 码道扩充并通过 |
| P5.3a-09 | PostgreSQL/API 集成测试 26 项（401/422/201/200/404/409、隔离、篡改、并发、事务与 commit unknown） | ✅ 码道扩充并通过 |
| P5.3a-10 | Docker P5.3a 定向 74；后端全量 673 passed, 0 skipped；前端 106 passed + build | ✅ 已完成 |
| P5.3a-11 | 路由 29→30；表 17 不变；Alembic 009 head | ✅ 已完成 |
| P5.3a-12 | 码道修正 diff 方向、零分母、重复/空指标、严格持久化校验、归属关系、行锁并发与事务恢复 | ✅ 已完成 |
| P5.3a-13 | 安全收口：比较链路不读正文/原始行/存储；旧上传补偿日志不再输出 storage key 或临时路径 | ✅ 已完成 |

### P5.3b — 实验数据前端 ✅ 已完成

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P5.3b-01 | 受保护路由、论文详情入口与严格 TypeScript API | ✅ 已完成 |
| P5.3b-02 | 非空 CSV/XLSX/XLS 本地预检、上传锁、上传后选中与可信列结构 | ✅ 码道收口 |
| P5.3b-03 | 文件分页、统计任务创建/轮询/重试与统计摘要 | ✅ 码道收口 |
| P5.3b-04 | 最新成功指标任务、已有比较恢复/来源锁定及 12 列结果表 | ✅ 码道收口 |
| P5.3b-05 | 路由/文件/任务三层竞态隔离与公开错误脱敏 | ✅ 码道收口 |
| P5.3b-06 | 定向 48；前端全量 12 files / 154；构建 129 modules；后端全量 673 | ✅ 已完成 |

## P6 阶段清单

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P6-01 | Markdown 报告生成、来源快照、状态机与安全下载 | ✅ P6.1 完成并经 码道收口 |
| P6-02 | PDF 报告生成 | ✅ P6.2 完成并经 码道中文可检索收口 |
| P6-03 | DOCX 报告生成 | ✅ P6.2 完成并经 码道包安全收口 |
| P6-04 | 报告创建/状态/历史/下载 API 与用户端闭环 | ✅ P6.1～P6.2 完成 |

## P7 阶段清单（产品方向已校正）

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P7-01 | 论文上传页面 | ✅ 已完成 |
| P7-02a | 论文详情、页面文本与 Evidence normalized 字符区间高亮 | ✅ 已完成 |
| P7-02b | LLM 审阅结果展示页面 | ✅ 已完成（P3.4 ReviewResultView） |
| P7-03 | 指标分析页面 | ✅ 已完成（P4.2 MetricAnalysisView） |
| P7-04 | 报告导出页面 | ✅ 已完成（P6.2 ReportExportView） |
| P7-05 | 注册、登录、密码找回、个人中心和受保护路由 | ✅ 已完成（P3.5） |
| P7-06 | P7.1 论文阅读工作台与证据化总结/解释/翻译 | ✅ 完成并经 码道收口（014 head；后端 866；前端 183） |
| P7-07 | P7.2 当前论文多轮问答、会话历史与 Evidence 引用 | ✅ 完成并经 码道独立收口（015；后端 909；前端 189） |
| P7-08 | P7.3 高亮/书签/笔记/知识卡/论文库与学习进度 | ✅ 完成并经 码道独立收口（016；后端 977；前端 197） |

## P8 阶段清单（固定轮次，不增加总数）

| 编号 | 交付物 | 状态 |
|------|--------|------|
| P8-01 | 完整管理员后端 + Vue 管理后台 + 用户角色/状态 + 不可变审计 | ⬜ 未开始，发布前必做 |
| P8-02 | 用户端/管理员端 E2E、任务恢复与全链路一致性 | ⬜ 未开始 |
| P8-03 | 性能、可靠性、限流和可观测性调优 | ⬜ 未开始 |
| P8-04 | 华为云部署（ECS/RDS/OBS/ModelArts）、备份恢复与综合安全审计 | ⬜ 未开始 |

P7.3 已新增 016、5 张个人学习表和 17 条 API，完成论文库、进度、高亮、书签、笔记、知识卡及前端学习记录闭环。最终结果为后端 977 passed、前端 16 files/197 passed、构建 136 modules、59 条 API、27 张 ORM 应用表和测试库残留 0。P8.1～P8.4 仍未实现。
