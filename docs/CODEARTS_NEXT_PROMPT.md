# 码道下一阶段提示词：P2.6 ProjectDocs 实现态校准

> 复制下面代码框中的全部内容，粘贴到华为云码道“智能体 / 规范开发”模式。

~~~text
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
~~~
