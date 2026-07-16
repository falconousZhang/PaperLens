# PaperLens 数据模型设计

## ER 关系概览

```
Paper 1──N PaperPage
Paper 1──N PaperSection
Paper 1──N PaperChunk
Paper 1──N PaperTable
Paper 1──N Evidence
Paper 1──N AnalysisTask
Paper 1──N ExperimentFile
Paper 1──N ExportReport
AnalysisTask 1──N ReviewResult
AnalysisTask 1──N MetricRecord
ReviewResult 1──N ReviewFinding
ReviewFinding N──N Evidence (通过 finding_evidence 关联表)
ExperimentFile 1──1 ExperimentResult
```

## 1. Paper

论文主表，记录上传的论文元信息。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| title | VARCHAR(500) | NOT NULL | 论文标题（从 PDF 提取或用户填写） |
| filename | VARCHAR(255) | NOT NULL | 原始文件名 |
| storage_key | VARCHAR(1024) | NOT NULL | 存储路径，格式：papers/{paper_uuid}/source.pdf |
| file_size | BIGINT | NOT NULL | 文件大小（字节） |
| file_hash | VARCHAR(64) | NOT NULL | SHA-256 文件哈希（去重） |
| page_count | INTEGER | | 页数 |
| status | VARCHAR(20) | NOT NULL | UPLOADING / PROCESSING / PARSED / FAILED |
| user_id | VARCHAR(128) | NOT NULL | 所属用户 |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL | 更新时间 |

索引：
- `idx_paper_user_id` ON (user_id)
- `idx_paper_file_hash` ON (file_hash)
- `idx_paper_status` ON (status)

## 2. PaperPage

论文页面信息，存储每页的文本和布局信息。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| paper_id | UUID | FK → Paper.id | 所属论文 |
| page_number | INTEGER | NOT NULL | 页码（从 1 开始） |
| text_content | TEXT | | 页面纯文本内容 |
| normalized_text_content | TEXT | | 页面归一化文本（空白字符合并） |
| width | FLOAT | | 页面宽度（pt） |
| height | FLOAT | | 页面高度（pt） |
| storage_key | VARCHAR(1024) | | 页面图片存储路径（可选，预留） |

索引：
- `idx_paper_page_paper_id` ON (paper_id, page_number) UNIQUE

## 3. PaperSection

论文章节结构，由 PDF 解析或 LLM 辅助识别。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| paper_id | UUID | FK → Paper.id | 所属论文 |
| section_type | VARCHAR(50) | NOT NULL | 章节类型：ABSTRACT / INTRODUCTION / METHOD / EXPERIMENT / RESULT / DISCUSSION / CONCLUSION / REFERENCES / APPENDIX / OTHER |
| title | VARCHAR(500) | | 章节标题 |
| level | INTEGER | NOT NULL DEFAULT 1 | 标题层级（1=一级标题） |
| sequence | INTEGER | NOT NULL | 排序序号 |
| start_page | INTEGER | | 起始页码 |
| end_page | INTEGER | | 结束页码 |
| text_content | TEXT | | 章节正文内容 |

索引：
- `idx_paper_section_paper_id` ON (paper_id, sequence)

## 4. PaperChunk

文本分块，用于向量索引和证据检索。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| paper_id | UUID | FK → Paper.id | 所属论文 |
| section_id | UUID | FK → PaperSection.id | 所属章节 |
| chunk_index | INTEGER | NOT NULL | 块序号 |
| content | TEXT | NOT NULL | 块文本内容 |
| char_count | INTEGER | NOT NULL | 字符数 |
| page_numbers | INTEGER[] | | 涉及的页码列表 |
| embedding_id | VARCHAR(128) | | 向量索引中的 ID |

索引：
- `idx_paper_chunk_paper_id` ON (paper_id, chunk_index) UNIQUE

## 5. PaperTable

论文表格实体，记录从 PDF 中提取的表格。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| paper_id | UUID | FK → Paper.id | 所属论文 |
| page_number | INTEGER | NOT NULL | 所在页码 |
| table_index | INTEGER | NOT NULL | 页内表格序号（从 1 开始） |
| caption | VARCHAR(500) | | 表格标题 |
| bbox_x0 | FLOAT | | 表格边界框左上角 X |
| bbox_y0 | FLOAT | | 表格边界框左上角 Y |
| bbox_x1 | FLOAT | | 表格边界框右下角 X |
| bbox_y1 | FLOAT | | 表格边界框右下角 Y |
| structured_data | JSONB | | 结构化表格数据（行列形式） |
| raw_text | TEXT | | 表格原始文本（兜底） |

索引：
- `idx_paper_table_paper_id` ON (paper_id, page_number, table_index) UNIQUE

## 6. Evidence

原文证据，审阅结论的依据。Evidence 为页内定位（page-local），基于 PyMuPDF block 提取，使用真实 bbox 坐标。不涉及跨页 span。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| paper_id | UUID | FK → Paper.id | 所属论文 |
| chunk_id | UUID | FK → PaperChunk.id | 来源文本块 |
| section_id | UUID | FK → PaperSection.id | 来源章节 |
| quoted_text | TEXT | NOT NULL | 证据原文引用文本 |
| page_number | INTEGER | NOT NULL | 所在页码 |
| bbox_x0 | FLOAT | | 证据区域左上角 X（pt） |
| bbox_y0 | FLOAT | | 证据区域左上角 Y（pt） |
| bbox_x1 | FLOAT | | 证据区域右下角 X（pt） |
| bbox_y1 | FLOAT | | 证据区域右下角 Y（pt） |
| char_start | INTEGER | | 在页面文本中的起始字符偏移 |
| char_end | INTEGER | | 在页面文本中的结束字符偏移 |
| evidence_type | VARCHAR(30) | NOT NULL | TEXT / TABLE / FIGURE_CAPTION / EQUATION |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |

索引：
- `idx_evidence_paper_id` ON (paper_id)
- `idx_evidence_chunk_id` ON (chunk_id)
- `idx_evidence_page` ON (paper_id, page_number)

## 7. AnalysisTask

分析任务，记录后台处理任务的状态。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| paper_id | UUID | FK → Paper.id | 关联论文 |
| task_type | VARCHAR(50) | NOT NULL | REVIEW / METRIC_EXTRACTION / EXPERIMENT_ANALYSIS |
| status | VARCHAR(20) | NOT NULL | PENDING / RUNNING / SUCCEEDED / FAILED / CANCELLED |
| progress | INTEGER | NOT NULL DEFAULT 0 | 进度百分比 0-100 |
| error_message | TEXT | | 失败原因 |
| started_at | TIMESTAMP | | 开始时间 |
| completed_at | TIMESTAMP | | 完成时间 |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |
| user_id | VARCHAR(128) | NOT NULL | 发起用户 |

索引：
- `idx_task_paper_id` ON (paper_id)
- `idx_task_status` ON (status)
- `idx_task_user_id` ON (user_id)

## 8. ReviewResult

审阅结果，按维度组织。一个 AnalysisTask 可产生多个 ReviewResult（每个维度一个）。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| task_id | UUID | FK → AnalysisTask.id | 关联任务 |
| paper_id | UUID | FK → Paper.id | 关联论文 |
| dimension | VARCHAR(50) | NOT NULL | 审阅维度：SOUNDNESS / NOVELTY / CLARITY / COMPLETENESS / REPRODUCIBILITY / SIGNIFICANCE / OVERALL / OTHER |
| rating | INTEGER | | 评分 1-5 |
| summary | TEXT | | 该维度的总体评价 |
| overall_verdict | VARCHAR(20) | | ACCEPT / WEAK_ACCEPT / BORDERLINE / WEAK_REJECT / REJECT（仅 OVERALL 维度使用） |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |

索引：
- `idx_review_task_id` ON (task_id)
- `idx_review_paper_id` ON (paper_id)
- `idx_review_dimension` ON (task_id, dimension) UNIQUE

## 9. ReviewFinding

审阅发现，每条发现绑定 Evidence。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| review_id | UUID | FK → ReviewResult.id | 所属审阅结果 |
| finding_type | VARCHAR(20) | NOT NULL | STRENGTH / WEAKNESS / SUGGESTION |
| content | TEXT | NOT NULL | 发现内容 |
| confidence | FLOAT | | 置信度 0.0-1.0 |
| verification_status | VARCHAR(20) | NOT NULL DEFAULT PENDING | VERIFIED / UNVERIFIED / PENDING |
| sequence | INTEGER | NOT NULL | 排序序号 |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |

索引：
- `idx_finding_review_id` ON (review_id, sequence)
- `idx_finding_type` ON (review_id, finding_type)

### finding_evidence 关联表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| finding_id | UUID | FK → ReviewFinding.id | 审阅发现 |
| evidence_id | UUID | FK → Evidence.id | 证据 |

索引：
- `idx_finding_evidence` ON (finding_id, evidence_id) UNIQUE

## 10. MetricRecord

实验指标记录，从论文表格和正文中提取。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| paper_id | UUID | FK → Paper.id | 所属论文 |
| task_id | UUID | FK → AnalysisTask.id | 关联任务 |
| user_id | VARCHAR(128) | FK → User.id, NOT NULL | 真实资源所有者 |
| model_name | VARCHAR(200) | | 模型名称 |
| dataset_name | VARCHAR(200) | | 数据集名称 |
| metric_name | VARCHAR(100) | NOT NULL | 指标名称（accuracy, F1, BLEU 等） |
| metric_value | FLOAT | NOT NULL | 指标值 |
| checkpoint_type | VARCHAR(20) | NOT NULL | FINAL / MAX / MEAN / BEST / LAST / UNKNOWN |
| checkpoint_source | VARCHAR(50) | | caption / row_header / context / conflict / null |
| evidence_id | UUID | FK → Evidence.id | 关联证据 |
| raw_text | TEXT | | 原始文本片段 |
| table_id | UUID | FK → PaperTable.id | 来源表格 |
| row_index | INTEGER | | 表格行号 |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |

索引：
- `idx_metric_paper_id` ON (paper_id)
- `idx_metric_task_id` ON (task_id)
- `idx_metric_checkpoint_type` ON (checkpoint_type)
- `idx_metric_user_id` ON (user_id)
- `idx_metric_name` ON (metric_name)

完整性：metric_value 必须有限；表格来源要求 `table_id + row_index`，Evidence 来源要求 `evidence_id`，二者严格二选一；来源外键为 RESTRICT。007 另为同一用户/论文的 PENDING/RUNNING METRIC_EXTRACTION 任务建立部分唯一索引。

## 11. ExperimentFile

实验数据文件（CSV/XLSX/XLS）；P5.1 服务/API 已实现，完整哈希和 storage_key 仅内部使用。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| paper_id | UUID | FK → Paper.id | 关联论文 |
| filename | VARCHAR(255) | NOT NULL | 原始文件名 |
| storage_key | VARCHAR(1024) | NOT NULL | 存储路径 |
| file_size | BIGINT | NOT NULL | 文件大小 |
| file_hash | VARCHAR(64) | NOT NULL | SHA-256 哈希 |
| file_type | VARCHAR(10) | NOT NULL | CSV / XLSX / XLS |
| row_count | INTEGER | NOT NULL，1～100000 | 数据行数，不含表头 |
| column_count | INTEGER | NOT NULL，1～256 | 数据列数 |
| columns_info | JSONB | NOT NULL | version=1 严格结构元数据 |
| user_id | VARCHAR(128) | NOT NULL | 所属用户 |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |

索引：
- `idx_exp_file_paper_id` ON (paper_id)
- `idx_exp_file_user_id` ON (user_id)

008 约束：file_type 仅 CSV/XLSX/XLS、file_size > 0、file_hash 为 64 位小写十六进制、行列范围，以及 `UNIQUE(user_id, paper_id, file_hash)`。upgrade 发现已有冲突会无损中止，不修补或删除记录。

## 12. ExperimentResult

P5.2 原子写入确定性 version=1 `summary_stats`；P5.3a 在同一结果行原子写入单一指标任务来源的严格 `metric_comparisons` 数组，`column_analysis` 仍保持 null。P5.3a 不新增迁移。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| file_id | UUID | FK → ExperimentFile.id, UNIQUE | 关联文件 |
| task_id | UUID | FK → AnalysisTask.id | 关联任务 |
| summary_stats | JSONB | NOT NULL | 统计摘要 |
| column_analysis | JSONB | | 列级分析结果 |
| metric_comparisons | JSONB | | 与论文指标的对比结果 |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |

JSONB 结构示例（summary_stats）：
```json
{
  "version": 1,
  "row_count": 10,
  "column_count": 1,
  "columns": [
    {
      "name": "accuracy",
      "dtype": "float",
      "count": 10,
      "null_count": 0,
      "stats": {
      "mean": 0.852,
      "stddev": 0.023,
      "min": 0.810,
      "max": 0.891,
      "median": 0.855
      }
    }
  ]
}
```

JSONB 结构示例（metric_comparisons）：
```json
[
  {
    "metric_record_id": "uuid",
    "metric_task_id": "uuid",
    "metric_name": "accuracy",
    "checkpoint_type": "MAX",
    "column_name": "accuracy",
    "statistic": "MAX",
    "paper_value": 0.891,
    "experiment_value": 0.855,
    "diff": -0.036,
    "absolute_diff": 0.036,
    "relative_diff": 0.0404,
    "allowed_diff": 0.00891,
    "status": "MISMATCH",
    "reason": null
  }
]
```

索引：
- `idx_exp_result_file_id` ON (file_id) UNIQUE

## 13. ExportReport

导出报告记录。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| paper_id | UUID | FK → Paper.id | 关联论文 |
| report_type | VARCHAR(20) | NOT NULL | MARKDOWN / PDF / DOCX |
| language | VARCHAR(2) | NOT NULL DEFAULT zh | 模板语言 zh / en |
| include_metrics | BOOLEAN | NOT NULL DEFAULT true | 是否包含论文指标 |
| include_experiment_analysis | BOOLEAN | NOT NULL DEFAULT true | 是否包含实验分析 |
| source_snapshot | JSONB | | 只含 review/metric/experiment 来源 id；历史骨架行为空 |
| source_hash | VARCHAR(64) | | source_snapshot 规范 JSON 的 SHA-256；历史骨架行为空 |
| status | VARCHAR(20) | NOT NULL DEFAULT PENDING | PENDING / GENERATING / READY / FAILED |
| storage_key | VARCHAR(1024) | | 导出文件存储路径 |
| content_hash | VARCHAR(64) | | 内容哈希 |
| file_size | BIGINT | | 文件大小 |
| error_message | TEXT | | 失败原因 |
| user_id | VARCHAR(128) | NOT NULL | 所属用户 |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |
| completed_at | TIMESTAMP | | 完成时间 |

索引：
- `idx_export_paper_id` ON (paper_id)
- `idx_export_user_id` ON (user_id)
- `idx_export_status` ON (status)
- `uq_active_export_source`：user/paper/type/language/include 选项/source_hash/content_hash 的部分唯一索引，仅覆盖 PENDING/GENERATING/READY 的来源行

010 新增 language、两个 include 选项和 source_snapshot。011 新增 source_hash，并约束非 FAILED 来源行在创建 PENDING 前已有 content_hash；READY 必须有 storage_key/file_size/completed_at，FAILED 必须有固定安全 error_message/completed_at，非 READY 不得声明存储对象。012 将来源行扩展为 MARKDOWN/PDF/DOCX，不新增表列；历史 source_snapshot=null 骨架行保持兼容，PDF/DOCX downgrade 无损中止。

## 数据库约束

002_constraints 迁移新增 CheckConstraints：

| 表 | 约束名 | 约束表达式 | 说明 |
|------|--------|-----------|------|
| Paper | ck_paper_status | status IN ('UPLOADING','PROCESSING','PARSED','FAILED') | 状态枚举约束 |
| AnalysisTask | ck_task_status | status IN ('PENDING','RUNNING','SUCCEEDED','FAILED','CANCELLED') | 任务状态枚举约束 |
| AnalysisTask | ck_task_progress | progress >= 0 AND progress <= 100 | 进度范围约束 |
| ReviewResult | ck_review_rating | rating >= 1 AND rating <= 5 | 评分范围约束 |
| ReviewFinding | ck_finding_confidence | confidence >= 0.0 AND confidence <= 1.0 | 置信度范围约束 |
| ReviewFinding | ck_finding_verification | verification_status IN ('VERIFIED','UNVERIFIED','PENDING') | 验证状态枚举约束 |
| Evidence | ck_evidence_type | evidence_type IN ('TEXT','TABLE','FIGURE_CAPTION','EQUATION') | 证据类型枚举约束 |
| ReviewFinding | ck_finding_type | finding_type IN ('STRENGTH','WEAKNESS','SUGGESTION') | 发现类型枚举约束 |
| ExportReport | ck_export_status | status IN ('PENDING','GENERATING','READY','FAILED') | 导出状态枚举约束 |

## P7.1 学习模型（COMPLETED）

013 新增 `learning_explanations` 与 `learning_citations`，不修改或复用 ReviewResult 的评分语义。Explanation 保存服务端确认的 SECTION/PAGE/EVIDENCE scope、SUMMARY/EXPLAIN/TRANSLATE mode、zh/en、非空 request_hash、状态和严格结构化结果；Citation 保存有序 Evidence 外键。

成功结果至少一个 Citation，所有 Evidence 必须属于同一 paper；活动同 request_hash 由部分唯一索引收口。模型 prompt、正文快照、原始响应、token、密钥和底层异常都不入库。因码道已把初版 013 应用到开发库并留下 1 条记录，014 以纯 DDL 无损收紧 request_hash、终态 JSON 和固定错误约束；没有删除或回填业务行。当前为 19 张 ORM 应用表、20 张物理表。

## P7.2 问答模型（COMPLETED）

015 新增 `paper_qa_conversations`、`paper_qa_turns`、`paper_qa_citations`。Turn 保存 conversation/user/paper 全图、sequence、UUID 幂等键、问题、语言、状态、context_hash 和严格终态；数据库强制问题非空且最多 2000 字、活动 conversation 部分唯一、成功 hash/answer/grounded 完整、失败固定错误且无 hash/结果。Citation 用 turn+evidence 复合主键和有序 sequence。

跨表 grounded/Citation 数量与五实体所有权由成功事务复核。prompt、完整上下文、向量、原始响应、token 和 secret 不入库。空表支持 014→015→014→015，非空降级在任何 DDL 前中止。当前为 22 张 ORM 应用表、23 张含 alembic_version 的物理表。

## P7.3 个人学习模型（COMPLETED）

016 新增 `paper_library_entries`、`paper_highlights`、`paper_bookmarks`、`paper_notes` 和 `paper_knowledge_cards`。阅读状态为 TO_READ/READING/COMPLETED/ARCHIVED；高亮颜色为 YELLOW/GREEN/BLUE/PINK；笔记锚点为 PAPER/PAGE/HIGHLIGHT；知识卡掌握状态为 NEW/LEARNING/MASTERED。

五表均以 user_id/paper_id 归属收口，页码、非空文本、长度、source hash、锚点互斥和卡片来源互斥由数据库 CHECK/FK/UQ 约束。高亮/书签重复创建幂等返回既有对象；被 Note/Card 引用的来源使用 RESTRICT 和应用层 409。五表为空可往返 015/016，任一非空时 downgrade 在任何 DDL 前拒绝。当前为 27 张 ORM 应用表、28 张含 alembic_version 的物理表。
