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
