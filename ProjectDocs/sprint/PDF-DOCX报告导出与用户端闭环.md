# P6.2 PDF/DOCX 报告导出与用户端闭环

## Sprint 信息

| 项目 | 内容 |
|------|------|
| 阶段 | P6.2 |
| 状态 | ✅ 完成 |
| 开始日期 | 2026-07-15 |
| 完成日期 | 2026-07-15 |

## 交付范围

1. 012 迁移：调整 `ck_export_p61_source` 约束使 source_snapshot 非空的 MARKDOWN/PDF/DOCX 均合法
2. PDF 生成：reportlab 确定性生成，固定元信息/文档 ID，PyMuPDF 验证
3. DOCX 生成：python-docx 确定性生成，固定 core properties，ZIP 重打包
4. 三格式幂等：report_type 扩展为 MARKDOWN|PDF|DOCX，各自独立 ExportReport
5. 列表 API：GET /api/v1/papers/{paper_id}/exports 分页
6. 下载 API：三格式 MIME + 安全文件名
7. P08 前端页面：ReportExportView.vue 格式/语言/指标配置 + 历史分页 + 轮询 + blob 下载 + FAILED 重试
8. 测试：转换单元 34 项、P6.2 API 25 项、前端 19 项

## 新建文件

| 文件 | 说明 |
|------|------|
| `backend/alembic/versions/012_export_report_pdf_docx.py` | 012 迁移 |
| `backend/paperlens/services/report_converter.py` | PDF/DOCX 确定性生成器 |
| `backend/tests/test_services/test_report_converter.py` | 转换器单元测试 34 项 |
| `backend/tests/test_api/test_exports_p62.py` | P6.2 API/PostgreSQL 测试 25 项 |
| `frontend/src/views/ReportExportView.vue` | P08 报告导出页面 |
| `frontend/src/tests/ReportExportView.test.ts` | 前端导出测试 19 项 |

## 修改文件

| 文件 | 变更 |
|------|------|
| `backend/paperlens/models/models.py` | ck_export_p61_source 扩展为三格式 |
| `backend/paperlens/services/export_service.py` | create_export 支持 PDF/DOCX 转换；run_export_task 支持不同存储键后缀 |
| `backend/paperlens/schemas/export.py` | CreateExportRequest 支持 MARKDOWN|PDF|DOCX；新增 ExportListItem/ExportListResponse |
| `backend/paperlens/api/exports.py` | 新增列表 API；下载支持三格式 MIME 和安全文件名 |
| `backend/requirements.txt` | 新增 reportlab==4.4.1 + python-docx==1.1.2 |
| `backend/tests/db_helpers.py` | verify_alembic_revision 默认值 012 |
| `frontend/src/api/index.ts` | 新增 6 个 TypeScript 类型和 3 个 API 函数 |
| `frontend/src/router/index.ts` | 添加 /papers/:id/export 路由 |
| `frontend/src/views/PaperDetailView.vue` | 添加"导出报告" tab |
| `frontend/src/tests/PaperDetailView.test.ts` | 更新 tab 验证和路由配置 |

## 测试结果

| 测试套件 | 数量 | 结果 |
|----------|------|------|
| test_report_converter.py | 34 | ✅ passed |
| test_exports.py (P6.1 回归) | 25 | ✅ passed |
| test_exports_p62.py | 25 | ✅ passed |
| test_health.py | 23 | ✅ passed |
| Docker 后端全量 | 830 | ✅ passed，0 skipped |
| 前端全量 | 173 | ✅ passed |
| 前端构建 | 132 modules | ✅ built |

## 基线变化

| 指标 | P6.1 基线 | P6.2 终态 |
|------|-----------|-----------|
| Alembic head | 011 | 012 |
| /api/v1 路由数 | 33 | 34 |
| 业务表数 | 18 | 18 |
| 前端测试 | 154 | 173 |
| 前端测试文件 | 12 | 13 |

## 关键约束遵守

- PDF/DOCX 使用 P6.1 确定性 Markdown 输出作为来源，不重新查询数据库
- 转换纯 Python 离线无 shell
- 输出逐字节确定性（PDF 使用 ReportLab invariant 固定 metadata/trailer ID，DOCX 固定 ZIP timestamp/排序/权限/压缩参数）
- PDF 有可选择/提取的中英文文本、稳定分页、页码
- DOCX 保留标题层级、段落、列表和表格，无宏/OLE/外部关系
- 后台任务只保存创建时 bytes，不在后台再次转换
- 012 迁移 downgrade 遇到任何 PDF/DOCX 行无损中止

## 码道独立审查与收口

码道初版的 PDF 在 Helvetica 下把中文提取为连续 `I`，并在生成后用不同长度字符串直接替换 PDF metadata，依赖解析器容错修复对象偏移；中文测试只断言“提取结果非空”。DOCX 外部关系测试只搜索 entry 文件名，未解析 relationship；rsid 未实际清除。前端固定只请求第一页，没有分页控件或请求代数，历史/下载错误被静默吞掉，下载测试也没有验证对象 URL 创建和回收。

码道直接完成以下修正，不增加码道轮次：

- PDF 改用 ReportLab invariant 模式和内置 STSong-Light CID 字体，固定 creator/producer/title/subject/日期/trailer ID，禁止生成后修改二进制对象；PyMuPDF 逐字验证中文。
- DOCX 固定 ZIP entry 时间、权限和顺序，清除 rsid，解析 `.rels` 拒绝 External，并拒绝 vbaProject、OLE 和 embeddings。
- 012 downgrade 检查全部 PDF/DOCX 行；迁移测试按 PostgreSQL 事务性 DDL 正确断言整体保持 012。
- 历史页增加 20 条分页、请求代数、路由/翻页/卸载竞态隔离、加载重试；下载增加单项锁、安全错误和 finally 回收 blob URL。
- FAILED API 始终映射固定公开文案，避免历史内部错误触发 Schema 失败或泄漏。

最终定向验证：转换器 34、P6.2 API 25、迁移 1、ReportExportView 19 全部通过；Docker 后端全量 830，前端全量 173，生产构建 132 modules。完整静态/数据库验收记录在 `docs/PROGRESS.md`。
