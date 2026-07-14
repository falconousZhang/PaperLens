# Sprint：华为云 MaaS LLM 运行接入

## 范围

P4.3 将已实现的 HuaweiMaaSLLMClient 接入 Docker 运行配置，提供离线配置检查与显式计费烟测入口，并在用户明确授权后完成最小真实调用。本 Sprint 不切换 Embedding，不修改 UI、API 或数据模型。

## 完成项

| 项目 | 状态 |
|------|------|
| Compose 六项 LLM 变量逐项透传、默认 mock | ✅ |
| Embedding 强制 mock | ✅ |
| SecretStr 与配置失败前置 | ✅ |
| 离线 `maas-config-check` | ✅ |
| `maas-smoke --confirm-billable`、单次调用、32 token 上限 | ✅ |
| 配置/CLI/Huawei LLM 定向测试 | ✅ 110 passed / 0 skipped |
| Docker/前端/迁移/数据库全量验收 | ✅ 435/0 skipped；106；126 modules；007 head；残留 0 |
| 用户真实 MaaS 小额烟测 | ✅ 第二轮授权请求成功，返回 35 字符 |

## 真实联调补充

首轮真实请求前的配置检查、DNS、TCP 443 和 TLS 1.3 均通过，但 32 token smoke 返回安全失败。依据 GLM-5.2 默认开启深度思考的接口契约，本轮仅修正 smoke 为 `thinking.type=disabled` 并增加安全失败分类。110 项定向与 425 项全量测试通过后，第二次且本轮最后一次授权请求成功，返回 35 字符；没有发起第三次请求。正常论文审阅路径仍保留模型默认行为。

## 独立审查

码道初版存在 huawei 配置检查 AttributeError、Docker 三项测试跳过、占位 Key 可通过、CLI 烟测覆盖不真实、失败回显底层异常、pytest 继承真实 MaaS 配置及 ProjectDocs/SDD/Sprint 漏同步。Codex 已按授权直接修正并完成全量验收与最小真实连通性验证。
