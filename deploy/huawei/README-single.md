# PaperLens 华为云 ECS 轻量单机部署

该方案面向小规模实习项目，将前端、后端和 PostgreSQL 部署在同一台 ECS 上。公网只开放 80 端口，后端和数据库仅通过 Docker 内网访问。现有 RDS、OBS、ELB、SWR 正式部署方案保持不变。

## 1. 准备源码

将部署包上传并解压到 `/opt/paperlens`，进入项目根目录：

```bash
cd /opt/paperlens
```

## 2. 生成环境文件

先轮换已经在聊天或其他不安全位置出现过的华为云 MaaS API Key。然后执行：

```bash
umask 077
POSTGRES_PASSWORD=$(openssl rand -hex 24)
PAPERLENS_JWT_SECRET=$(openssl rand -hex 32)
read -rsp "Huawei MaaS API Key: " PAPERLENS_LLM_API_KEY
echo
printf 'POSTGRES_PASSWORD=%s\nPAPERLENS_JWT_SECRET=%s\nPAPERLENS_LLM_API_KEY=%s\n' "$POSTGRES_PASSWORD" "$PAPERLENS_JWT_SECRET" "$PAPERLENS_LLM_API_KEY" > deploy/huawei/.env.single
unset POSTGRES_PASSWORD PAPERLENS_JWT_SECRET PAPERLENS_LLM_API_KEY
chmod 600 deploy/huawei/.env.single
```

API Key 输入时不会显示在终端，也不会写入 shell 历史。

## 3. 校验并启动

```bash
docker compose --env-file deploy/huawei/.env.single -f deploy/huawei/docker-compose.single.yml config --quiet
docker compose --env-file deploy/huawei/.env.single -f deploy/huawei/docker-compose.single.yml up -d --build
docker compose --env-file deploy/huawei/.env.single -f deploy/huawei/docker-compose.single.yml ps
```

首次构建需要下载 Python、Node、Nginx 和 PostgreSQL 镜像及依赖，耗时取决于网络速度。

## 4. 验证

```bash
curl -fsS http://127.0.0.1/healthz
curl -fsS http://127.0.0.1/api/v1/health/ready
docker compose --env-file deploy/huawei/.env.single -f deploy/huawei/docker-compose.single.yml logs --tail=100 backend
```

两条健康检查成功后，通过 `http://ECS弹性公网IP` 访问。

## 5. 日常管理

```bash
docker compose --env-file deploy/huawei/.env.single -f deploy/huawei/docker-compose.single.yml ps
docker compose --env-file deploy/huawei/.env.single -f deploy/huawei/docker-compose.single.yml logs -f --tail=100 backend
docker compose --env-file deploy/huawei/.env.single -f deploy/huawei/docker-compose.single.yml restart backend frontend
docker compose --env-file deploy/huawei/.env.single -f deploy/huawei/docker-compose.single.yml stop
docker compose --env-file deploy/huawei/.env.single -f deploy/huawei/docker-compose.single.yml start
```

不要执行 `docker compose down -v`，否则会删除论文文件和数据库卷。该方案使用 HTTP，适合低成本演示；后续绑定域名时再增加 HTTPS。
