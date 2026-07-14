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
- 云端部署时配置 OBS 桶生命周期规则（OBSStorage 未实现，后续版本）
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
- 当前只提供数据库角色校验依赖和 `python -m paperlens.cli promote-admin --email <email> [--claim-legacy-data]`；无默认管理员、无命令行密码、无自动提升。
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
