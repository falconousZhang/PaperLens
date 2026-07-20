# 码道下一阶段提示词：P8.4 华为云部署、备份恢复与综合安全验收

## 任务目标

本轮固定为 P8.4，也是既定开发计划的最后一个码道轮次。必须在一个轮次内完成：在 P2～P8.3 已实现并收口的论文阅读学习、审阅/指标/实验/导出、登录注册、管理员系统、任务恢复、限流和可观测性基础上，实现可切换的华为云 OBS 存储适配，补齐面向华为云 ECS + RDS for PostgreSQL + OBS + ModelArts MaaS + ELB/WAF 的生产部署资产、备份恢复手册和综合安全清单，使项目达到“代码与部署资料完整、等待用户在真实云环境最终验收”的状态。

本轮不得新增码道轮次，不实际购买、创建、修改或删除任何华为云资源，不调用真实 OBS/MaaS/RDS，不把“部署资产已完成”写成“真实云上已经部署”。不返工现有产品页面和 P2～P8.3 已验收业务能力。

## 一、最高优先级：码道禁止运行任何测试或环境命令

1. 码道只编写代码、最多 3 个轻量后端测试资产、部署配置和文档，不得运行 pytest、Vitest、E2E、覆盖率、Python 编译、类型检查、npm test/build、Alembic、Docker、HTTP、浏览器或性能命令。
2. 禁止执行 `docker compose config`、`docker inspect`、`env`、`set`、云 CLI/SDK 调用、OBS/RDS/MaaS 连通性检查、依赖安装或任何外网请求；禁止以单文件或“只做语法检查”为例外。
3. 最终报告必须明确写明“按项目规则未运行测试、构建、迁移、Docker、HTTP、浏览器或真实华为云验收，等待集中验收”，只列待验收项，不得引用历史通过数冒充 P8.4 结果。

## 二、开始前边界与真实基线

1. 完整阅读根目录 `AGENTS.md`、systemDesign 01～08、SDD、P8.3 Sprint/修复报告、部署相关文档和真实代码；严格按 `dev-process-framework → page-mockup → fullstack-testing → function-detail → sdd-workflow` 先更新设计，再编码，最后同步 Sprint。P8.4 不新增页面，页面设计只记录生产入口和错误展示无变化。
2. 当前数据库仍为 Alembic 017，P8.4 不需要新业务表或迁移。P8.3 独立集中验收结果仅为历史基线：P8.3 专项 3 passed、两个受影响查询 2 passed、新后端镜像构建成功、隔离 live/ready/404 HTTP 通过；不得写成 P8.4 结果。
3. 现有未提交改动都属于用户/码道。禁止 git add/commit/reset/checkout/restore/clean/rebase，禁止修改 `.git/`、`.arts/`、`.codeartsdoer/`、`.skills/`、`AGENTS.md`、`docs/CODEARTS_NEXT_PROMPT.md` 和 `docs/CODEARTS_PROMPT_ARCHIVE.md`，禁止批量格式化或清理无关文件。
4. 禁止读取、搜索、打印、复制或推断 `.env`、API Key、AK/SK、security token、JWT secret、Authorization、cookie、密码、DSN、证书私钥或完整环境。禁止修改开发库数据、用户文件、审计日志和 Docker volume。
5. 所有示例只能使用显眼占位符，不得把任何曾在对话、环境或文件中出现的真实凭据写入代码、Compose、日志、文档或测试。测试资产只允许注入 fake client 和临时目录，不能依赖真实 SDK 网络行为。

## 三、设计、SDD 与 Sprint 先行

1. 编码前同步 `ProjectDocs/systemDesign/01～08`，增加 P8.4 的生产拓扑、配置矩阵、OBS 对象生命周期、凭据边界、部署/回滚、RDS/OBS 备份恢复、ELB/WAF/安全组和最终验收矩阵。
2. 更新 `ProjectDocs/specs_SDD/PaperLens/spec.md`、`tasks.md`、`design/design.md`；新增 `ProjectDocs/specs_SDD/PaperLens/design/19-华为云部署备份恢复与安全.md` 和 `ProjectDocs/sprint/华为云部署备份恢复与综合安全.md`。开始时置进行中，结束时只能置“实现完成、待真实云环境最终验收”。
3. 本轮不新增产品路由、页面、数据库表、Alembic 018、Redis/Celery、Kubernetes、Terraform 自动建云资源、Prometheus/Grafana、FAISS/pgvector、邮件/MFA、计费调用或数据迁移任务。
4. 所有设计以当前单 ECS 或小规模多实例为目标。应用内限流继续是单进程保护；跨实例总限流、TLS、DDoS/WAF 规则由华为云入口层承担，不在应用中伪造分布式能力。

## 四、实现真实但可离线测试的 OBSStorage

1. 使用华为云官方 Python OBS SDK `esdk-obs-python`，按项目固定依赖方式加入 `backend/requirements.txt`；SDK 必须延迟导入，仅选择 `storage_backend=obs` 时初始化，保证 local/test 模式不因 SDK 客户端或云环境缺失而启动失败。
2. 在 Settings 增加严格配置并更新 `.env.example`：`PAPERLENS_STORAGE_BACKEND=local|obs`、HTTPS endpoint、bucket、可选安全 prefix、凭据模式 `ECS|ENV`、可选临时 security token、SSE 模式 `OBS|KMS` 及 KMS key id、下载临时目录和连接/读取超时。Secret 字段使用 `SecretStr`；布尔值不能冒充整数；选择 OBS 时缺项、HTTP endpoint、非法 bucket/prefix、KMS 无 key id 必须在启动前用固定安全错误失败。
3. 生产默认推荐 ECS agency 的临时凭据链；ENV 模式只用于由 DEW/部署系统注入的 AK/SK/token，不允许硬编码或日志输出。使用 SDK 官方 `security_provider_policy`/临时凭据能力，不自行请求元数据地址，不实现自制签名。
4. 统一严格对象 key 规范化：拒绝空 key、绝对路径、反斜杠、`.`/`..` 段、控制字符、重复分隔和超长值；只能在配置 prefix 下访问由现有 `build_key` 生成的对象。错误和日志不得包含 endpoint、bucket、对象 key、文件名、本地路径、SDK 原始异常或凭据。
5. `save` 只能上传已有普通文件，使用私有对象和配置的 SSE；检查 SDK HTTP 状态，仅 2xx 视为成功。失败时不得留下被误认为成功的数据库状态；补偿删除只能删除本次确定创建且尚未转移所有权的对象。禁止 public-read、桶创建/删除、列桶/全桶扫描和预签名 URL。
6. 将只适用于本地路径的读取契约演进为安全的上下文管理式本地物化接口：LocalStorage 直接 yield 已校验路径；OBSStorage 下载到唯一临时文件，验证 SDK 状态，在 `finally` 中关闭并删除。修改实验分析、报告生成完整性检查和报告下载等所有调用者使用该接口，异常、客户端取消和解析失败也不能遗留临时文件。可保留 LocalStorage `read_path` 兼容层，但生产调用不得依赖 OBS 永久缓存路径。
7. OBS 客户端/Storage 实例应为应用级、并发安全且有显式 `close()` 生命周期，由 FastAPI lifespan 关闭；local 模式为安全 no-op。工厂不得每个请求无限创建连接，也不得在模块导入时访问网络。
8. 保持数据库 `storage_key` 语义和现有对象命名，不自动把本地已有文件迁移到 OBS，不改写开发环境默认 local Compose。缺失对象、403/404、非 2xx、下载中断和 close 竞态统一映射为现有安全业务错误，不向客户端透传 SDK 文本。

## 五、生产配置与华为云部署资产

1. 增加 `PAPERLENS_ENV=local|test|production` 和集中生产校验。production 必须拒绝 debug、非 Secure 认证 cookie、local storage、HTTP OBS/MaaS endpoint、弱/占位 JWT、缺失数据库/OBS/MaaS 必需配置；生产环境关闭 `/api/docs`、`/api/redoc` 和 OpenAPI JSON，local/test 保持兼容。
2. 新增 `deploy/huawei/`，至少包含 `README.md`、`.env.production.example`、`docker-compose.prod.yml`、生产 Nginx 配置、部署/回滚说明、备份恢复手册和安全验收清单。示例只能引用外部镜像名和 secret 文件路径，不包含真实域名、IP、账号、项目 ID、桶名或凭据。
3. 生产 Compose 不包含 PostgreSQL 服务，不暴露后端 8000，只让前端/Nginx 接受来自 ELB 安全组的端口；RDS 通过私网 SSL DSN 连接。增加一次性 migration 服务，再启动 backend，避免多副本同时迁移。不得自动 downgrade 或在失败后继续启动。
4. 为生产增加独立 Dockerfile/entrypoint 或等价配置：应用进程使用非 root 用户；镜像内不包含 `.env`、测试、用户数据和构建缓存；合理使用 read-only filesystem、`tmpfs /tmp`、`no-new-privileges`、cap drop、资源/进程上限、restart policy 和 live/ready healthcheck。不要破坏现有本地开发 Compose。
5. 生产 Nginx 只代理同源 `/api/`，保留 request id，正确覆盖而不是盲目信任客户端转发头，限制请求体并配置必要的 CSP、frame、content-type、referrer 等安全响应头；不得启用目录浏览、`v-html` 或客户端 token 存储。TLS 在 ELB/WAF 终止时必须记录可信代理 CIDR 由实际私网网段显式配置，默认仍不信任任意 X-Forwarded-For。
6. Secret 通过 DEW/CSMS 或部署系统落到宿主机受限文件并以 Compose secrets/只读文件注入；entrypoint 只读取明确的 `*_FILE`，不得 `set -x` 或打印内容。至少覆盖 RDS DSN、JWT secret、MaaS/Embedding key；OBS 优先 ECS agency，ENV fallback 才使用 secret。
7. 文档给出用户手工配置顺序：VPC/私有子网与安全组 → RDS PostgreSQL/SSL → 私有 OBS 桶 → ECS agency/IAM 最小权限 → DEW secrets → 镜像仓库/ECS → ELB HTTPS/WAF/入口限流 → DNS → health/readiness → 小额 MaaS/OBS 验证。这里只写步骤和占位符，不实现会创建或收费的 IaC。

## 六、备份、恢复、回滚与综合安全

1. `deploy/huawei/backup-restore.md` 明确 RDS 自动备份、保留期、PITR、发布前手工备份、RPO/RTO 假设和月度恢复演练。恢复默认先恢复到新 RDS 实例并只读核对 schema/关键计数，再由人工切换；禁止脚本自动覆盖生产实例或自动执行破坏性 downgrade。
2. OBS 使用私有桶、SSE-OBS 或 SSE-KMS、版本控制和生命周期规则；文档说明恢复指定对象版本、非当前版本保留、未完成分段上传清理。应用删除不等同于备份删除，不提供全桶清理脚本。
3. 发布回滚以镜像版本回滚为主；数据库 migration 失败立即停止。若 schema 已前进，只允许兼容旧镜像时回滚应用，否则从发布前备份恢复到新实例并人工切换。任何恢复步骤都必须先确认目标 Region、VPC、实例和备份时间点。
4. 安全清单至少覆盖：RDS/后端无公网入口、最小安全组、IAM agency 桶级最小权限、MaaS/OBS 仅 HTTPS、DEW 密钥轮换、Secure/HttpOnly/SameSite cookie、生产文档关闭、CORS 同源、WAF/ELB 总限流、日志白名单、审计不可变、备份加密和恢复演练。
5. 明确真实云最终验收尚需用户提供/配置的外部条件，但不要索取或记录具体 secret。给出只读/低风险的手工验收清单和预期结果，不提供会删除 volume、对象、数据库或用户数据的命令。

## 七、只编写、不运行的最小测试资产

1. 本轮新增后端测试函数最多 3 个，集中在一个文件，不新增前端/E2E/云端测试：
   - OBS fake client 合并验证 save → context materialize → delete、非 2xx 安全失败、key/prefix 拒绝和临时文件必清理；
   - production Settings 合并验证安全配置可通过、debug/local/HTTP/缺失 KMS key/占位 secret 会失败且错误文本不含 secret；
   - storage 工厂与 lifespan 合并验证 local/obs 选择、单例/close，并验证 production OpenAPI 文档关闭。
2. fake client 只模拟最少 SDK 返回对象，不安装 SDK、不联网、不读取环境；每个测试最多一个对象和一个小文件，不做 bucket/Region/状态参数排列组合。
3. 不新增覆盖率、前端测试、浏览器 E2E、Docker E2E、RDS/OBS/MaaS 集成测试或大规模部署矩阵。集中验收阶段默认只运行这 3 个测试、一个生产配置静态渲染、一个镜像构建和一条隔离 HTTP 冒烟；码道本轮不得运行。

## 八、文档状态与最终交付

1. 完成后同步 systemDesign 01～08、SDD spec/tasks/design、P8.4 Sprint、README、`.env.example`、`docs/IMPLEMENTATION_STATUS.md`、`docs/PROGRESS.md`、architecture/api-contract/data-model/security-design。把 P8.1～P8.3 保持已验收，P8.4 标记“实现完成、待真实华为云最终验收”。
2. 文档必须区分三种状态：代码/部署资产已实现、离线集中验收尚未执行、真实华为云资源尚未创建/验证。不得声称已经上线、已配置 WAF/备份或已完成灾备演练。
3. 最终报告逐项列出：OBSStorage 契约与安全边界、生产配置校验、生产镜像/Compose/Nginx、secret 注入、RDS/OBS 备份恢复、回滚、安全清单、最多 3 个测试资产、修改文件和等待集中验收项。
4. 不得生成新的后续开发提示词或 P8.5；P8.4 之后只剩码道交付后的独立验收、必要修正和用户真实云环境部署，不增加开发轮次。

本轮完成定义是“P8.4 代码、部署资产、最多 3 个轻量测试资产和文档实现完毕，等待独立集中验收与用户真实华为云验收”。不要运行任何测试、构建、迁移、Docker、HTTP、浏览器、外网或云服务命令。
