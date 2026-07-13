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
2. **应用层**（FastAPI）：中间件检查 Content-Length
3. **业务层**：根据文件类型校验具体大小

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
   - 不允许用户直接指定存储路径

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
| 向量索引（FAISS） | 用户删除时重建索引 | 异步重建 |
| 导出报告 | 7 天后自动清理 | 定时任务扫描 |
| 失败任务记录 | 30 天后自动清理 | 定时任务扫描 |

### 用户主动删除
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