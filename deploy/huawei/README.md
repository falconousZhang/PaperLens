# PaperLens 华为云生产部署指南

实施方：码道（CodeArts）  
适用版本：P8.4

本目录提供 ECS 单机容器部署基线。外部流量路径为 `ELB/WAF -> ECS:8080 -> Nginx -> backend:8000`；后端端口不发布到宿主机。

## 1. 前置资源

- ECS、RDS PostgreSQL、OBS 私有桶位于同一 Region/VPC；RDS 不开放公网入口。
- ECS 绑定 IAM Agency，默认通过临时凭证访问 OBS，权限仅包含指定桶前缀所需的读、写、删操作。
- OBS 开启 SSE-OBS 或 SSE-KMS、版本控制和适合项目的数据生命周期规则。
- ELB 配置 HTTPS 证书与健康检查 `/healthz`，WAF 按需要启用。
- ECS 安全组仅允许 ELB 安全组访问 8080；RDS 安全组仅允许 ECS 私网访问 5432。
- DEW/CSMS 保存 JWT、MaaS Key 等敏感值；SWR 保存不可变版本镜像。

## 2. 构建并推送镜像

在仓库根目录执行，镜像标签使用发布版本或提交哈希，避免生产使用可漂移的 `latest`：

```bash
docker build -f backend/Dockerfile.prod -t <backend-image>:<version> ./backend
docker build -f frontend/Dockerfile.prod -t <frontend-image>:<version> .
docker push <backend-image>:<version>
docker push <frontend-image>:<version>
```

## 3. 准备配置与 Secret

将 `deploy/huawei` 复制到 ECS 的 `/opt/paperlens/deploy/huawei`，再复制配置模板：

```bash
cd /opt/paperlens
cp deploy/huawei/.env.production.example deploy/huawei/.env.production
chmod 600 deploy/huawei/.env.production
mkdir -p /opt/paperlens/secrets
chmod 700 /opt/paperlens/secrets
```

编辑 `.env.production`，至少替换镜像、OBS 桶和 ELB CIDR 占位符。`PAPERLENS_FRONTEND_BIND_ADDRESS` 应填写 ECS 私网 IP，不要填写公网 IP。

通过 DEW/CSMS 或受控发布系统把敏感值直接注入下列文件，不要把真实值写进命令历史、环境文件或 Git：

| 文件 | 内容 |
|---|---|
| `database_url` | `postgresql+psycopg2://<user>:<encoded-password>@<rds-private-host>:5432/paperlens?sslmode=verify-full&sslrootcert=/run/secrets/rds_ca` |
| `rds_ca.pem` | 华为云 RDS 对应 Region 的 CA 证书 |
| `jwt_secret` | 至少 48 字节的高熵随机值 |
| `llm_api_key` | 华为云 MaaS API Key |
| `embedding_api_key` | 华为云 Embedding API Key；相同时也应单独注入 |

文件写入完成后执行 `chmod 400 /opt/paperlens/secrets/*`。数据库密码中的特殊字符必须做 URL 编码。

默认 OBS 认证模式是 `ECS`，不保存长期 AK/SK。确需 ENV 兜底时，将模式改为 `ENV`，额外注入 `obs_access_key_id`、`obs_secret_access_key`，并在后续命令同时加入 `-f deploy/huawei/docker-compose.obs-env.yml`。

## 4. 发布

先静态校验配置，再拉取镜像、执行迁移并启动服务：

```bash
cd /opt/paperlens
docker compose --env-file deploy/huawei/.env.production -f deploy/huawei/docker-compose.prod.yml config --quiet
docker compose --env-file deploy/huawei/.env.production -f deploy/huawei/docker-compose.prod.yml pull
docker compose --env-file deploy/huawei/.env.production -f deploy/huawei/docker-compose.prod.yml up migrate
docker compose --env-file deploy/huawei/.env.production -f deploy/huawei/docker-compose.prod.yml up -d backend frontend
```

迁移失败时不得继续启动。启动后检查：

```bash
docker compose --env-file deploy/huawei/.env.production -f deploy/huawei/docker-compose.prod.yml ps
curl --fail http://<ecs-private-ip>:8080/healthz
curl --fail https://<production-domain>/api/v1/health/live
curl --fail https://<production-domain>/api/v1/health/ready
```

`ready` 必须返回 200；`/api/docs`、`/api/redoc`、`/api/openapi.json` 在生产必须返回 404。随后使用专用小额账号各执行一次登录、PDF 上传/解析、真实 MaaS 审阅、问答或学习操作和导出，确认 OBS 对象为私有且已加密。

## 5. 安全验收

- 互联网只能访问 ELB/WAF 的 443，ECS 8000 和 RDS 5432 不对外开放。
- `.env.production` 不包含数据库口令、JWT 或 API Key；容器配置检查输出不出现 Secret。
- `PAPERLENS_TRUSTED_PROXY_CIDRS` 只包含固定 Docker 网段和真实 ELB 私网网段，不使用 `0.0.0.0/0`。
- RDS 使用 `sslmode=verify-full` 和受信 CA；OBS/MaaS 仅使用 HTTPS。
- 容器使用非 root、只读根文件系统、最小能力集和资源上限。
- 轮换 Secret 后重建相关容器，不在日志中输出 Secret、请求正文或完整查询串。

## 6. 回滚与恢复

应用回滚使用上一不可变镜像版本。若数据库迁移产生不兼容变更，不直接对生产库执行破坏性 downgrade，应按 [backup-restore.md](backup-restore.md) 从发布前备份恢复到新实例，经只读核验后人工切换。所有恢复操作先核对 Region、VPC、实例和目标时间点。
