# 码道下一阶段提示词：P5.2 实验数据确定性统计摘要后端闭环

继续维护 D:\shixi\PaperLens 项目。

本轮定义为 P5.2：在已验收的 P5.1 CSV/XLSX/XLS 安全上传与可信结构解析基础上，实现实验文件的确定性统计任务、ExperimentResult 原子写入和结果查询 API。只完成“已上传实验文件 → 后台统计任务 → 可查询严格统计摘要”的后端闭环；不做论文 MetricRecord 交叉验证、不做 P07 实验前端、不做删除/下载/行预览或报告导出。指标交叉验证单独留到 P5.3，避免在没有明确匹配语义时猜测 BEST/FINAL/LAST。

P5.1 最终真实基线：解析/存储/API 定向 103 passed、0 skipped；P4.3 MaaS/LLM/审阅广义定向 180 passed、0 skipped；P4.1 指标定向 67 passed、0 skipped；Docker 后端全量 527 passed、0 skipped；前端 10 files / 106 passed；生产构建 126 modules；Alembic 为 008 head 且 check 无差异；27 条 `/api/v1` method+path 路由、17 张 ORM 表；测试库 17 表残留 0；开发库为 2 users / 3 papers / 3 tasks / 14 review_results / 0 metrics / 0 experiment_files / 0 experiment_results；三容器运行且 PostgreSQL healthy；health/login 200、无 token experiment-file 401；77 个本地 Markdown 链接、0 断链；最新提交仍为 `4659a0b8e634ec539c3d96994cf55e745c8d8b39`。008 已实际验证不兼容记录原值保留并无损中止，以及 007→008→007→008 可逆。真实华为云 `glm-5.2` 最小烟测已成功，但长文本质量和生产费用仍未验收；本轮禁止真实云端调用。

开始前完整阅读并以当前代码为准：AGENTS.md、README.md、.gitignore、docker-compose.yml、backend/paperlens/core/config.py、core/enums.py、models/models.py、schemas/task.py、schemas/experiment_file.py、api/tasks.py、api/experiment_files.py、services/experiment_file_parser.py、services/experiment_file_service.py、utils/storage.py、tests/conftest.py、tests/db_helpers.py、alembic 001～008、ProjectDocs/systemDesign/01～08、specs_SDD/PaperLens/spec.md、tasks.md、design/04/05/08/09、Sprint、docs/api-contract.md、data-model.md、architecture.md、security-design.md、PROGRESS.md、IMPLEMENTATION_STATUS.md 和 P5.1 bugfix report。

## 一、工作流、基线和禁止事项

1. 严格按 AGENTS.md：dev-process-framework 先更新 systemDesign 01～06；本轮无 UI，page-mockup 只确认 P07 继续 PLANNED；fullstack-testing 先更新 08；function-detail 更新 SDD 后再编码；sdd-workflow 新建 `ProjectDocs/sprint/实验数据统计摘要.md`。skill 不可用时明确记录并按同序手工完成。
2. 开始前记录 git status、HEAD、Docker 状态、008 current/check、路由/表数、测试库残留、开发库七表只读计数和两个 Codex 提示词 SHA-256。
3. 禁止 git add/commit/reset/checkout/restore/clean/rebase；禁止修改 `.git/`、`.arts/`、`.codeartsdoer/`、`.skills/`、AGENTS.md 和两个 Codex 提示词文件；不得还原现有未提交改动。
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
6. 执行 Python 编译、git diff --check、高熵 secret 候选、生产 Web Storage/v-html、敏感日志、Markdown 路径/锚点检查；禁改目录和 HEAD 不变。两个 Codex 提示词在码道执行期间 hash 必须不变。
7. 不读取 `.env`，不运行真实 MaaS，不修改开发库。受权限限制未执行的项目必须如实标明。

最终逐项报告工作流、迁移、任务关联、统计定义、数值/内存边界、文件完整性复核、API、用户隔离、幂等并发、事务失败、离线保证、定向/全量测试、前端、迁移/路由/表、HTTP、数据库残留、secret/Markdown 和明确未实现项。

不要 git commit，不要修改 Codex 提示词，不要读取或使用 API Key，不要真实调用华为云，不要修改开发库，不要删除 volume，不要提前实现交叉验证、实验前端或 P5.3～P8。
