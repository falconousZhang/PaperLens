# Markdown 审稿报告导出 Sprint

## 范围

P6.1 交付 Markdown 审稿报告后端闭环：来源选择 → Markdown 生成 → ExportReport 原子状态机 → 状态查询 → 鉴权下载。PDF/DOCX 转换、报告 Vue 页面、报告列表 UI、文件删除不在本 Sprint。

## 交付状态

| 工作项 | 状态 |
|--------|------|
| 010 基础迁移 + 011 source_hash/严格约束/来源感知索引 | ✅ 码道收口 |
| ExportReport 模型完整化（language/include_metrics/include_experiment_analysis/source_snapshot） | ✅ |
| Markdown 生成服务（zh/en 双语模板、维度排序、指标表、实验统计+交叉验证） | ✅ |
| HTML/Markdown 安全转义、表格单元格转义、禁止字段过滤 | ✅ |
| 确定性输出（创建 PENDING 前固定 bytes/content_hash/source_hash） | ✅ 码道收口 |
| POST /api/v1/papers/{paper_id}/exports（201/200 duplicate） | ✅ |
| GET /api/v1/exports/{export_id} | ✅ |
| GET /api/v1/exports/{export_id}/download（attachment + nosniff） | ✅ |
| 状态机条件 UPDATE 单认领、回读校验与失败补偿 | ✅ 码道收口 |
| 幂等创建（同源同内容一行；新来源新建；FAILED 重试） | ✅ 码道收口 |
| 来源选择：最新成功 REVIEW/METRIC/EXPERIMENT 任务 | ✅ |
| 401/404/409 鉴权与业务校验 | ✅ |
| config.py max_report_size_bytes | ✅ |
| 历史 PDF/DOCX 骨架行兼容，不篡改既有认证测试语义 | ✅ 码道收口 |
| db_helpers verify_alembic_revision 更新为 011 | ✅ |

## 验收

| 项目 | 结果 |
|------|------|
| P6.1 生成单元测试 | 72 passed |
| P6.1 API/来源/并发/补偿 | 25 passed |
| P6.1 迁移测试 | 1 passed |
| Docker 后端全量 | 771 passed，0 skipped/failed |
| 前端回归 | 12 files / 154 passed |
| 前端构建 | 129 modules |
| Alembic | 011 head；历史 PDF 009→011 保留；非空 downgrade 无损中止 |
| API / ORM | 33 条 `/api/v1` method+path；18 张业务表 |
| 数据隔离 | paperlens_test 全空；开发库无变化 |

## 关键文件

### 新建

- `backend/alembic/versions/010_export_report_p61.py`
- `backend/alembic/versions/011_export_report_p61_integrity.py`
- `backend/paperlens/schemas/export.py`
- `backend/paperlens/services/export_service.py`
- `backend/paperlens/api/exports.py`
- `backend/tests/test_services/test_export_markdown.py`
- `backend/tests/test_api/test_exports.py`
- `backend/tests/test_migrations/test_export_report_p61_migration.py`

### 修改

- `backend/paperlens/models/models.py` — ExportReport 新列/约束/索引
- `backend/paperlens/core/config.py` — max_report_size_bytes
- `backend/paperlens/main.py` — 注册 exports_router
- `backend/tests/db_helpers.py` — verify_alembic_revision 默认值 011
- `backend/tests/test_api/test_auth.py` — 保持历史 PDF 骨架兼容测试

## 码道独立审查收口

码道初版按“用户+论文+选项”永久复用 READY 报告，来源更新后仍返回旧内容；后台还会重新选择最新任务，使 source_snapshot 与实际文件不一致。生成时间取当前时钟破坏逐字节确定性，Evidence 输出的是 id 而不是页码/短引用，Markdown 结构未完整转义，来源图、真实并发、存储补偿和迁移历史行测试均缺失。

码道直接修正而未增加码道返工轮次：创建时完成全来源图复核和确定性渲染；用 source_hash+content_hash 收口同源并发；后台原子认领并只保存创建时 bytes；补齐 Evidence、安全转义、严格公开 Schema、下载回读与失败对象清理；新增 011 兼容已应用 010 和历史 PDF/DOCX 行。
