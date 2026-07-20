# PaperLens 安全设计文档

## 1. 文件类型检查

### 策略
- **PDF 上传**：校验文件扩展名 + Magic Number（文件头 `%PDF-`）
- **CSV/Excel 上传**：校验扩展名 `.csv` / `.xlsx` / `.xls` + Magic Number
  - CSV：无固定 Magic Number，校验内容可解析性
  - XLSX：Magic Number `PK`（ZIP 格式）
  - XLS：Magic Number `0xD0CF11E0A1B11AE1`（OLE2 格式）

### 实现
```python
ALLOWED_MIME_TYPES = {
    "pdf": ["application/pdf"],
    "csv": ["text/csv", "application/csv"],
    "xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
    "xls": ["application/vnd.ms-excel"],
}

MAGIC_NUMBERS = {
    "pdf": b"%PDF-",
    "xlsx": b"PK",
    "xls": b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",
}
```

1. 读取文件前 8 字节，校验 Magic Number
2. 校验 Content-Type 头
3. 校验文件扩展名
4. 三项全部通过才允许上传

### 拒绝策略
- 不匹配的文件直接拒绝，返回 415 Unsupported Media Type
- 不尝试修复或转换文件格式

## 2. 大小限制

| 文件类型 | 最大大小 | 说明 |
|---------|---------|------|
| PDF | 50 MB | 学术论文通常不超过此限制 |
| CSV/Excel | 20 MB | 实验数据文件 |
| 请求体 | 60 MB | Nginx/Traefik 层面限制 |

### 多层限制
1. **反向代理层**（Nginx）：`client_max_body_size 60m`
2. **应用层**（FastAPI）：Content-Length 只能作快速拒绝，不能作为可信大小
3. **业务层**：P5.1 对 UploadFile 按固定块累计实际字节，超过 20MB 立即 413

### 超限处理
- 返回 413 Payload Too Large
- 记录日志，不存储文件

## 3. 路径穿越防护

### 风险场景
- 用户上传文件名包含 `../` 或绝对路径
- OBS key 构造时拼接用户输入导致路径穿越

### 防护措施

1. **文件名清洗**：
   - 移除所有路径分隔符（`/`, `\`）
   - 移除 `..` 序列
   - 仅保留文件名部分
   ```python
   import os
   safe_name = os.path.basename(user_filename)
   ```

2. **存储路径构造**：
   - 使用 paper UUID 作为存储路径，不使用用户提供的文件名
   - 存储路径格式：`papers/{paper_uuid}/source.pdf`
   - 实验文件格式：`experiment-files/{uuid}/source.csv|source.xlsx|source.xls`
   - 不允许用户直接指定存储路径

### P5.1 CSV/Excel 容器安全

- CSV 仅完整解码 UTF-8/BOM/GB18030，分隔符必须在逗号/分号/Tab 中唯一确定；拒绝 NUL、坏语法和行宽不一致。
- XLSX 在 openpyxl 前限制 ZIP entry 数、单项/总压缩比和总解压量，拒绝正反斜杠穿越、绝对/盘符路径、重复/加密 entry、宏、外链、嵌入对象、多个非空 sheet 和公式。
- XLS 同时验证扩展名、OLE magic 和 xlrd 解析成功；解析器不执行宏、DDE、外链或网络。
- 解析/校验失败不进入持久存储；storage、flush、commit 失败 rollback 并补偿对象。错误响应和日志不包含文件内容、用户文件名、本机临时路径、SQL 参数或 secret。

### P5.2 统计安全边界

- 统计任务仅使用认证上下文 user_id，联查 task、ExperimentFile、Paper 与 User；ADMIN 不默认访问他人资源。
- 计算前重新验证 SHA-256、magic/容器和完整 columns_info，计算后再次复核 SHA-256，防止替换文件结果入库。
- CSV/XLSX/XLS 按路径逐行读取，不保存原始行或字符串样本；只为数值列保留受 5,000,000 cells 上限约束的紧凑数组。
- 非有限数、计算溢出与超 JavaScript 安全范围整数安全失败；任务错误只使用固定分类，不包含值、行、文件名、路径、storage key、SQL 或底层异常。
- ExperimentResult 与 SUCCEEDED 同事务提交；失败回滚，commit 未知重新查询，补偿逻辑不删除可能已提交的结果。

3. **文件读取**：
   - 读取存储文件时仅使用数据库中记录的 storage_key
   - 不接受用户输入的文件路径参数

4. **路径校验**：
   ```python
   def validate_path(base_dir: str, target_path: str) -> bool:
       resolved = os.path.realpath(target_path)
       return resolved.startswith(os.path.realpath(base_dir))
   ```

## 4. SSRF 防护

### 风险场景
- 用户通过参数注入内网地址
- LLM 输出中包含恶意 URL
- Webhook 回调到内网地址

### 防护措施

1. **出站请求白名单**：
   - 仅允许访问 ModelArts 推理端点（配置白名单域名/IP）
   - 仅允许访问 OBS 端点
   - 禁止访问内网地址（10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8）

2. **URL 校验**：
   ```python
   import ipaddress
   import socket

   BLOCKED_NETWORKS = [
       ipaddress.ip_network("10.0.0.0/8"),
       ipaddress.ip_network("172.16.0.0/12"),
       ipaddress.ip_network("192.168.0.0/16"),
       ipaddress.ip_network("127.0.0.0/8"),
       ipaddress.ip_network("169.254.0.0/16"),
   ]

   def is_safe_url(url: str) -> bool:
       parsed = urlparse(url)
       if parsed.scheme not in ("https",):
           return False
       try:
           ip = socket.gethostbyname(parsed.hostname)
           addr = ipaddress.ip_address(ip)
           return not any(addr in net for net in BLOCKED_NETWORKS)
       except (socket.gaierror, ValueError):
           return False
   ```

3. **禁止功能**：
   - 不提供任意 URL 抓取功能
   - 不提供用户自定义 Webhook
   - 不从用户输入构造出站请求 URL

## 5. Prompt Injection 防护

### 风险场景
- 论文内容中包含恶意 Prompt（如 "Ignore previous instructions..."）
- 用户通过标题/文件名注入 Prompt
- LLM 输出被二次注入

### 防护措施

1. **输入与指令分离**：
   - 使用结构化 Prompt 模板，用户输入和论文内容放在明确的分隔符内
   ```
   [SYSTEM]
   You are a paper review assistant. Follow the instructions below strictly.

   [INSTRUCTIONS]
   1. Review the paper based on the {dimension} dimension.
   2. Each conclusion MUST reference an Evidence ID from the provided evidence.
   3. Do NOT generate conclusions without evidence.

   [PAPER CONTENT]
   <<<CONTENT_START>>>
   {paper_content}
   <<<CONTENT_END>>>

   [EVIDENCE LIST]
   {evidence_list}
   ```

2. **输出校验**：
   - 解析 LLM 输出为结构化 JSON
   - 校验每条结论是否关联了有效的 Evidence ID
   - 未关联 Evidence 的结论丢弃，不返回给用户
   - 校验 Evidence ID 是否存在于数据库中

3. **输出转义**：
   - LLM 输出在展示前进行 HTML 转义
   - 不将 LLM 输出作为代码执行

4. **速率限制**：
   - 单用户单论文的审阅请求频率限制
   - 防止通过大量请求探测 Prompt 模板

5. **日志脱敏**：
   - 日志中不记录完整 Prompt 模板
   - 不记录 API Key

### 5.1 P3.3 Huawei MaaS LLM 出站边界

- `PAPERLENS_LLM_BASE_URL` 是部署配置而不是用户输入；客户端只接受无凭据、query 和 fragment 的绝对 HTTPS URL，并固定请求相对路径 `/chat/completions`。
- `PAPERLENS_LLM_API_KEY` 使用 SecretStr，从环境或云端密钥服务注入；请求异常、任务错误和测试日志不得包含 Key、Authorization Header 或完整上游响应体。
- 输入 messages 只允许 system/user/assistant 和非空字符串 content；PaperLens 内部的 dimension、evidence_aliases 等参数不得发送给上游。
- 响应只接受单一 `choices[index=0]`、`role=assistant`、非空 content 和 `finish_reason=stop`；多 choice、截断、工具调用、非法 JSON 或歧义结构全部安全失败。
- 本轮不自动重试，避免超时边界重复计费；自动测试只使用 MockTransport，不访问真实华为云，也不代表用户账号、区域、模型质量或费用已经验收。

## 6. 密钥管理

### 密钥清单

| 密钥 | 用途 | 存储位置 |
|------|------|---------|
| OBS AK/SK | 对象存储访问 | 华为云 DEW / 环境变量 |
| RDS 连接串 | 数据库连接 | 华为云 DEW / 环境变量 |
| ModelArts API Key | LLM 推理调用 | 华为云 DEW / 环境变量 |
| JWT Secret | Token 签名 | 华为云 DEW / 环境变量 |
| Redis 密码 | 任务队列 | 华为云 DEW / 环境变量 |

### 管理原则

1. **不硬编码**：所有密钥通过环境变量注入，代码中不出现明文密钥
2. **不提交到 Git**：`.env` 文件加入 `.gitignore`
3. **最小权限**：OBS AK/SK 仅授予必要桶的读写权限
4. **定期轮换**：生产环境密钥每 90 天轮换
5. **审计日志**：密钥访问记录审计日志

### 本地开发
- 使用 `.env.local` 文件（已加入 `.gitignore`）
- 提供 `.env.example` 模板（不含实际密钥值）

### 云端部署
- 优先使用华为云 DEW（数据加密服务）管理密钥
- ECS 通过 IAM 角色获取临时凭证访问 OBS
- 不使用永久 AK/SK

## 7. 用户数据清理策略

### 自动清理

| 数据类型 | 保留期限 | 清理方式 |
|---------|---------|---------|
| 论文原文（本地存储） | 用户删除时立即清理 | 同步删除文件 |
| 解析中间结果 | 用户删除时立即清理 | 同步清理 |
| 结构化数据（RDS） | 用户删除时级联删除 | 数据库 CASCADE |
| 规划中的向量索引（FAISS，尚未实现） | 用户删除时重建索引 | 异步重建（规划） |
| 导出报告 | 7 天后自动清理 | 定时任务扫描 |
| 失败任务记录 | 30 天后自动清理 | 定时任务扫描 |

### 用户主动删除（规划，删除 API 尚未实现）
- `DELETE /papers/{paper_id}`：删除论文及所有关联数据
- 删除操作不可恢复（不提供回收站功能，MVP 阶段简化）
- 删除前确认提示

### 数据隔离
- 所有查询强制带 `user_id` 过滤条件
- API 层从 JWT Token 提取 user_id，不接受用户传入
- 不提供跨用户数据访问接口

### 存储生命周期
- 本地存储：删除论文时同步删除对应目录 `papers/{paper_uuid}/`
- 云端部署使用已实现的 OBSStorage，并在启用版本控制后配置经确认的生命周期规则
- 导出报告目录：7 天后自动过期删除
- 临时文件目录：1 天后自动过期删除

### 日志脱敏
- 日志中不记录论文原文内容
- 日志中不记录用户文件名（使用 paper_id 替代）
- 日志中不记录 LLM 完整响应（仅记录 token 使用量）
- SQLAlchemy engine 固定关闭 `echo` 并启用 `hide_parameters`；`PAPERLENS_DEBUG=true` 不能重新开启包含论文、认证或任务数据的 SQL 参数日志

## 8. 错误信息安全

### 风险场景
- 内部异常堆栈信息泄露文件路径、SQL 语句、内部 IP 等
- 用户通过错误响应探测系统内部结构

### 防护措施

1. **_safe_error_message() 映射**：
   - 所有用户可见的错误消息通过 `_safe_error_message()` 统一处理
   - 已知异常类型映射为固定用户友好消息（如 "论文解析失败，请稍后重试或重新上传"）
   - 未知异常统一返回 "操作失败，请稍后重试"
   - 原始异常详情仅记录到服务端日志，不返回给用户

2. **验证**：
   - `test_error_message_is_safe`：断言 error_message 不包含 `/`、`Traceback`、`SELECT` 等内部信息模式
   - `test_error_message_safe_with_injected_exception`：注入包含 `/tmp/`、`Traceback`、`SELECT *` 的异常，验证返回消息中不含这些模式

## 9. 用户认证、RBAC 与管理员系统

P3.5 已完成产品账号认证和 USER/ADMIN RBAC 基础；完整管理员业务 API、审计日志和管理控制台仍在 P7。所有论文、Evidence、任务和审阅业务路由都从统一 Bearer 依赖取得真实用户，不再使用 `demo_user_id` 作为运行时后门。

### 用户认证

- 邮箱大小写无关唯一；密码为 15～128 个可打印 Unicode code point，使用 pwdlib Argon2id，不 trim、不截断、不强制字符组合。当前只使用内置弱口令集合，尚未接入完整泄露口令语料库。
- JWT access 默认 15 分钟，固定 HS256，强制校验全部 claims、issuer、audience、typ、签名和 sid；secret 无仓库默认值且至少 32 字节。
- refresh 是至少 256 bit 的不透明随机值，只存在于 `paperlens_refresh` HttpOnly/SameSite=Lax cookie；数据库只存 SHA-256。每次刷新单次轮换并记录 replaced_by，旧 token 重放会撤销整个 family。
- access 鉴权同时查询 AuthSession 与 User，因此 logout、logout-all、密码修改/重置、账号禁用和有效锁定会立即拒绝旧 access。
- 登录不存在、密码错误、禁用和锁定账号均走 Argon2 dummy 检查并返回相同 401；账号失败计数通过数据库行锁串行化。当前尚无分布式 IP 限流，需由部署层补齐。
- reset token 单次、15 分钟有效且只存摘要；默认 NullPasswordResetNotifier 不联网、不记录或响应明文 token。生产通知适配器尚未实现，后续优先可替换的华为云能力。
- 所有业务资源的 user_id 只来自服务端认证上下文，不接受客户端自报。

### RBAC 与管理员安全

- 基础角色为 USER、ADMIN；前端菜单/路由守卫只用于体验，所有权限必须由后端逐接口校验。
- P8.1 已用 `python -m paperlens.cli admin-bootstrap --user-id <UUID4> --reason <text>` 替代早期 promote-admin；仅零 ACTIVE ADMIN 时可提升现有 ACTIVE USER，并同事务撤销 session、写入不可变审计。无默认管理员、无命令行密码、无 email 模糊匹配。
- 管理员业务 API/页面、用户启停/角色管理、最后管理员保护和管理员操作审计尚未实现，统一留到 P7；ADMIN 当前也不会绕过普通资源所有权。
- 华为云 IAM 负责云资源访问身份，不代替 PaperLens 产品用户与管理员账号。

## 10. P4.1 指标完整性与隔离

- MetricRecord 的 `user_id/paper_id/task_id` 在任务写入和公开查询时交叉校验；ADMIN 不默认绕过所有权。
- 每条公开记录必须且只能绑定 `table_id + row_index` 或 `evidence_id`，并验证来源属于同一论文；来源外键使用 RESTRICT，避免记录失去证据。
- 指标值写入前使用 `math.isfinite`，数据库同时拒绝 NaN/Infinity；百分比指标统一为 0～1。
- Checkpoint 无证据或冲突时保存 UNKNOWN；不根据数值最大猜测 BEST/MAX。
- 同一用户/论文的活动指标任务由部分唯一索引防止竞态重复；任务失败时记录整批回滚，只返回固定安全错误。
- 指标提取完全离线，不调用 LLM 或华为云；日志只记录 task_id 和异常类型，不记录论文原文、候选值或数据库参数。

## 11. P4.3 MaaS Secret 与计费边界

- API Key 只从本机 `.env` 或部署平台 secret 注入，Pydantic 使用 SecretStr；仓库、前端、文档和 CLI 参数均不保存真实值。
- 空白值、常见占位文本、非 HTTPS URL、URL credentials/query/fragment 和完整 `/chat/completions` endpoint 在联网前拒绝。
- config-check 不联网，只输出 scheme/host/path、model、超时、token 上限和 Key 是否已配置。
- smoke 必须显式提供 `--confirm-billable`，每次命令只发一次固定短提示，最多请求 32 completion token；GLM smoke 专用发送 `thinking.type=disabled`，正常审阅保持模型默认；成功不打印模型原文，失败仅打印固定类别。
- 自动测试只用 `.invalid` 域名、fake client 或 MockTransport。2026-07-14 的真实云端烟测仅在用户明确授权后执行，第二次且最后一次请求成功；未读取、输出或记录本地 Key。
- pytest 的 conftest 在导入 Settings 前覆盖两类 provider 为 mock，并从测试进程环境移除继承的 LLM/Embedding API Key，避免运行容器切换到真实 MaaS 后回归测试产生费用。

## 12. P5.3a 交叉验证安全边界

- USER 与 ADMIN 都必须满足资源所有权；他人实验文件或指标任务统一 404，管理员不获得读取普通用户论文数据的旁路。
- Result、EXPERIMENT_ANALYSIS task、ExperimentFile、Paper、User 以及 MetricRecord/source 在写入前交叉验证；关系异常固定 409。
- 不读取 storage、实验原始行、MetricRecord.raw_text、PaperTable.raw_text/structured_data 或 Evidence.quoted_text；公开响应不包含哈希、对象 key 或正文。
- 所有数值拒绝布尔、NaN、Infinity 和计算溢出；零论文值不构造 Infinity，相对差返回 null。
- 行锁和原子 JSONB 写入防止并发覆盖；同源幂等，异源固定冲突，失败不删除可能已经提交的结果。
- 交叉验证完全离线，不构造 LLM/Embedding client，不产生华为云请求或费用。

## 13. P5.3b 浏览器安全与竞态边界

- 实验路由需要认证；前端权限只改善体验，所有资源归属仍由后端逐接口校验。
- 文件选择只做扩展名、非空和 20MB 快速拒绝；服务端继续执行完整格式、容器、哈希和结构校验。
- FormData 不手写 Content-Type，避免错误 boundary；不把文件内容、API Key、token 或 Authorization 写入 Web Storage、DOM HTML 或日志。
- 详情、结果、分析任务和比较响应必须匹配当前 paper/file/task；路由或文件切换后在途响应被代数令牌丢弃。
- 只允许固定分析错误列表进入页面，未知网络/服务端错误统一为安全文案，不展示内部路径、SQL、Traceback 或服务端 message。
- 所有后端文本使用 Vue 转义插值，不使用 v-html；已有比较结果只读恢复并锁定来源，防止用户误覆盖审计链。

## 14. P6.1 Markdown 导出安全边界

- POST、状态和下载均要求资源所有权；USER/ADMIN 访问他人报告统一 404。公开 Schema 不包含 source_snapshot、source_hash、content_hash 或 storage_key。
- 所有来源图逐层复核 paper/user/task/file/source 关系；异常固定 `EXPORT_SOURCE_INVALID` 409，不跨论文拼接数据。
- 数据库文本规范换行并转义 HTML、Markdown 结构、表格分隔符和可执行 URL scheme；Evidence 只输出页码与最多 240 字短引用，不输出整页正文、raw_text 或原始实验行。
- 同来源并发由 source_hash/content_hash 部分唯一索引收口；后台条件 UPDATE 单次认领。storage 部分写入、校验或提交失败时清理未归属对象，FAILED 只保存固定安全文案。
- 下载通过 StorageBackend 回读并复核 size/SHA-256，响应为 attachment、nosniff、private/no-store；不接受路径或 Range 参数。

## 15. P6.2 多格式导出安全边界

- PDF 使用内置字体和纯 Python invariant 生成，不执行 shell、不下载字体、不事后替换二进制对象；禁止 JavaScript、OpenAction、Launch、附件或外部资源。
- DOCX 从全新文档生成并确定性重打包；输出验证拒绝 vbaProject、OLE、embeddings 和任何 `TargetMode="External"` relationship，同时清除 rsid。
- 导出历史只返回固定公开字段；FAILED 无论数据库历史详情为何均映射为固定安全文案。USER/ADMIN 访问他人论文或报告统一 404。
- 前端不使用 v-html、Web Storage 或 token URL；翻页、轮询和路由请求均由代数令牌隔离，下载对象 URL 在成功、失败和竞态路径都回收。

## 16. P7.1 阅读学习安全边界（COMPLETED）

- 客户端只能提交同论文 section/page/evidence 标识，不能上传任意“原文”或覆盖服务端 source；user_id 只取认证上下文。
- 论文标题、正文、Evidence 和后续用户问题都属于不可信输入，必须与系统指令分隔；内容中的“忽略之前规则”等文本不得改变模型契约。
- 模型输出只接受严格单 JSON 对象；answer/key_points/terms/evidence_refs 均有长度和数量上限，全部 alias 必须完整绑定同论文 Evidence。
- 不存在有效 Citation 时整次失败，不能把未验证或部分验证答案公开。公开响应不含 prompt、request/source hash、原始模型响应或底层异常。
- 外部 LLM 调用时不持有数据库事务；成功结果、Citation 和终态单事务提交，失败回滚并只保存固定安全错误。
- Vue 只用文本插值，不渲染模型 Markdown/HTML；Citation 定位使用服务端 Evidence 和规范字符区间，失败时安全降级。

实现验收确认：来源和 Evidence 指纹在创建前及模型返回后双重复核；外部推理期间 Session 已关闭；日志只记录 explanation/paper/stage/异常类型；前端对 paper/page/history/explanation/poll 分别使用代数令牌并在卸载时清理 timer。自动测试只使用 Mock，未调用真实 MaaS。

## P7.2 问答安全边界

- 会话创建只接受空对象，问题创建只接受去空白问题、zh/en 和 UUID4；user/paper/正文/Evidence/prompt/model 均不能由客户端覆盖。
- 检索只使用当前论文非空 Evidence；批量向量在排序前验证数量、维度、数值类型、NaN/Inf 和零范数，错误整轮失败。
- 历史 question/answer、当前问题、标题和 Evidence 都是不可信文本，经过标签分隔和转义，不能提升为 system 指令。
- context_hash 覆盖身份、顺序、语言、问题、历史和候选 Evidence；模型返回后重新加载并复算，来源变化不公开答案。
- grounded/Citation 同事务，失败清空 hash 和结果并只保存固定错误；日志不记录问题、回答、Evidence、prompt、hash、email 或 token。
- Vue 纯文本显示，grounded=false 无伪引用；会话/轮次分页、轮询、切换与卸载有独立代数和 timer 清理，不使用 Web Storage。

## 18. P7.3 个人学习安全边界

- 全部资源使用认证上下文中的 user_id，Paper、Page、高亮、笔记和知识卡来源必须形成同一 owner/paper 全图；普通 ADMIN 不绕过普通业务所有权。
- 客户端不能提交 quoted_text、source_hash、last_reviewed_at 或 owner 字段；高亮引文和 hash 只由服务端页面文本与偏移派生。
- Schema 拒绝 extra、空 PATCH、非法 null、控制字符和超限文本；公开错误固定，不记录笔记、卡片、引文、正文或 secret。
- 论文库计数在单查询内完成；读取不创建 library entry。写事务失败统一 rollback，并发重复只形成一行一对象。
- Vue 不使用 v-html/Web Storage；更新失败不做乐观覆盖，路由、列表、动作、页码和进度请求分别用代数令牌隔离。高亮只允许 PAGE 正文选区，并复核 Unicode/跨文本节点的完整切片。

## 19. P8.1 管理员系统安全边界（COMPLETED）

- 管理权限始终由数据库用户状态、当前 AuthSession 和 `require_admin` 服务端复核；前端路由守卫不构成授权依据。
- 首次引导和用户权限写入共用 PostgreSQL 事务级 advisory lock，取得锁后重新读取操作者；并发互相降级最多一项成功，另一项固定 409，最终至少一个 ACTIVE ADMIN。
- 旧 promote-admin 无审计入口已移除；角色/状态变化撤销目标旧 session，禁用同时失效未使用且未过期的 reset token。
- 审计 before/after 仅允许 role/status，数据库 CHECK 保证 action 与精确状态形状一致，trigger 拒绝 UPDATE/DELETE；日志不记录 email、reason、令牌、正文、SQL 或异常详情。
- 跨用户内容仅通过显式 `/admin` 元数据 API 只读访问；响应不含 storage_key、hash、source_snapshot、正文、模型输入输出或原始错误。

## 20. P8.2 后台任务恢复安全边界（已完成）

- PostgreSQL `pg_try_advisory_xact_lock` 确保同一时刻仅一个扫描事务执行恢复；锁繁忙立即跳过，提交后释放，任何外部处理不持锁。
- 扫描只使用有限行锁和既有状态字段。完整持久化输入才允许重放；审阅参数、解析代次或导出 bytes 不足时固定 FAILED，不猜测输入、不删除用户学习数据。
- 恢复写入的 error_message 使用各模块既有固定公开文案，不包含内部路径、SQL、Traceback 或服务端异常详情。
- 认证失败（401）由现有中间件统一处理并引导登录，恢复逻辑不涉及认证流程。
- 日志只记录 stage、实体 id/type、task type、action、计数和异常类型，不记录论文内容、用户数据、任务参数、路径、hash 或敏感字段。
- TaskDetail 的 `experiment_file_id` 仅为 UUID 关联，不暴露 storage_key、文件哈希、模型内容或原始错误。

## 21. P8.3 限流与可观测性安全边界（已完成）

- 只接受规范小写 UUID4 request id；非法、非规范或超长值不会进入响应和日志。
- 请求日志只记录 request_id、method、路由模板、status、duration_ms、rate_scope；未知路由固定为 `<unmatched>`，不记录 URL、查询、正文、IP、身份或 secret。
- 限流 store 使用单调时钟、有限容量和过期/最旧淘汰，不持久化 IP。429 不返回 key、IP、计数或内部额度。
- 默认不信任转发头。只有 TCP peer 命中 `PAPERLENS_TRUSTED_PROXY_CIDRS` 才严格解析代理链；任一非法地址使其回退到直接 peer。
- live 不检查外部依赖；ready 只读检查数据库并把异常映射为固定 503，不返回 DSN、驱动或异常正文。
- 应用内限流不是分布式安全边界；P8.4 已在部署基线中要求 ELB/WAF 补充入口总限流、TLS、安全组和访问控制。

## 22. P8.4 华为云生产安全边界（已完成）

- OBS 默认使用 ECS Agency 临时凭证，ENV AK/SK 仅作 Secret 文件兜底；对象固定私有并使用 SSE-OBS/KMS，所有 SDK 失败按白名单脱敏。
- 生产启动拒绝本地存储、非华为/非 HTTPS 端点、弱 JWT、mock/缺 Key 模型、RDS 非 `verify-full + sslrootcert`、空或全网可信代理和公开 API 文档。
- 数据库 DSN、JWT、MaaS/Embedding Key 及可选 OBS 凭据由 `*_FILE` 加载，migrate 与 serve 共用入口，不写入 Compose 明文环境。
- ECS 只向 ELB 发布私网 8080；backend 8000 只在固定容器私网暴露。Nginx 与后端均非 root、read-only、cap_drop ALL、no-new-privileges 并设置资源上限。
- RDS/OBS 恢复到新资源后只读核验再人工切换；RPO/RTO 只采用真实演练结果，不承诺未验证时长。
