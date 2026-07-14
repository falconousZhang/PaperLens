# 华为云 MaaS LLM 运行配置详细设计

## 1. 状态与边界

P3.3 已实现 HuaweiMaaSLLMClient；P4.3 补齐安全运行开关、配置预检和最小烟测入口。默认开发、测试和 Docker 启动仍使用 MockLLMClient。华为云真实账号的最小连通性与非流式返回已验收；模型质量、长文本审阅效果和生产费用仍不属于本阶段结论。

## 2. 配置流

```text
本机 .env / 部署 Secret
  → Docker Compose 六项 LLM 变量
  → Settings（API Key 为 SecretStr）
  → validate_llm_config
  → HuaweiMaaSLLMClient
```

Embedding provider 在 Compose 固定为 mock。base URL 必须是绝对 HTTPS，不含 credentials、query、fragment 或 `/chat/completions` 后缀；model 和 Key 去除首尾空白后必须有效，Key 不得是说明性占位文本。

## 3. CLI

`maas-config-check` 不创建数据库会话、不创建 HTTP 请求，只验证 client 可构造性并输出非敏感摘要。

`maas-smoke --confirm-billable` 在确认 flag 和 backend 校验通过后才构造 client；固定发送一次 `Hi`，completion 上限取配置值与 32 的较小值。GLM-5.2 默认开启深度思考，真实首轮烟测在 32 token 限制下失败，因此 smoke 专用请求显式发送 `thinking.type=disabled`；正常论文审阅配置不在本次修正中改变。成功只输出字符数，失败只输出预定义安全类别，不回显底层异常、响应或 Key。

## 4. 测试

Docker 将实际 Compose 文件只读挂载到 `/app/docker-compose.yml`，测试直接验证六项变量、mock 默认、Embedding 强制 mock 和无宽泛 env_file。conftest 在导入 Settings 前强制 LLM/Embedding mock、`.invalid` endpoint，并移除从运行容器继承的 API Key，因此即使生产 backend 已切到 MaaS，pytest 也不会访问真实服务。所有 MaaS HTTP 覆盖使用 fake client/MockTransport。

最终验收：配置/CLI/Huawei LLM 定向 110 passed、0 skipped；真实审阅围栏修复定向 138 passed、0 skipped；Docker 后端全量 435 passed、0 skipped；前端全量 106 passed，生产构建成功。真实配置检查、DNS/TCP/TLS 均通过；首轮 32 token 请求安全失败，smoke 专用关闭思考模式后第二轮成功并返回 35 字符，未进行第三次请求。
