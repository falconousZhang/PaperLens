# 码道下一阶段提示词：P3.2 华为云优先的 Embedding 抽象与语义 Evidence 检索

> 复制下面代码框中的全部内容，粘贴到华为云码道“智能体 / 规范开发”模式。

~~~text
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
~~~
