# PaperLens 数据模型设计

## ER 关系概览

```
Paper 1──N PaperPage
Paper 1──N PaperSection
Paper 1──N PaperChunk
Paper 1──N Evidence
Paper 1──N AnalysisTask
Paper 1──N ExperimentFile
AnalysisTask 1──1 ReviewResult
AnalysisTask 1──N MetricRecord
ExperimentFile 1──1 ExperimentResult
Paper 1──N ExportReport
ReviewResult N──N Evidence (通过 review_evidence 关联表)
```

## 1. Paper

论文主表，记录上传的论文元信息。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| title | VARCHAR(500) | NOT NULL | 论文标题（从 PDF 提取或用户填写） |
| filename | VARCHAR(255) | NOT NULL | 原始文件名 |
| obs_key | VARCHAR(1024) | NOT NULL | OBS 存储路径 |
| file_size | BIGINT | NOT NULL | 文件大小（字节） |
| file_hash | VARCHAR(64) | NOT NULL | SHA-256 文件哈希（去重） |
| page_count | INTEGER | | 页数 |
| status | VARCHAR(20) | NOT NULL | UPLOADING / PARSED / FAILED |
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
| width | FLOAT | | 页面宽度（pt） |
| height | FLOAT | | 页面高度（pt） |
| obs_key | VARCHAR(1024) | | 页面图片 OBS 路径（可选） |

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

## 5. Evidence

原文证据，审阅结论的依据。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| paper_id | UUID | FK → Paper.id | 所属论文 |
| chunk_id | UUID | FK → PaperChunk.id | 来源文本块 |
| section_id | UUID | FK → PaperSection.id | 来源章节 |
| content | TEXT | NOT NULL | 证据原文内容 |
| page_number | INTEGER | | 所在页码 |
| location_desc | VARCHAR(500) | | 位置描述（如 "Table 3, Row 2"） |
| evidence_type | VARCHAR(30) | NOT NULL | TEXT / TABLE / FIGURE_CAPTION / EQUATION |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |

索引：
- `idx_evidence_paper_id` ON (paper_id)
- `idx_evidence_chunk_id` ON (chunk_id)

## 6. AnalysisTask

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

## 7. ReviewResult

审阅结果，每条审阅意见绑定 Evidence。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| task_id | UUID | FK → AnalysisTask.id, UNIQUE | 关联任务 |
| paper_id | UUID | FK → Paper.id | 关联论文 |
| dimension | VARCHAR(50) | NOT NULL | 审阅维度：SOUNDNESS / NOVELTY / CLARITY / COMPLETENESS / REPRODUCIBILITY / SIGNIFICANCE / OTHER |
| rating | INTEGER | | 评分 1-5 |
| summary | TEXT | | 总体评价 |
| strengths | JSONB | | 优点列表，每项含 content + evidence_ids |
| weaknesses | JSONB | | 缺点列表，每项含 content + evidence_ids |
| suggestions | JSONB | | 改进建议列表，每项含 content + evidence_ids |
| overall_verdict | VARCHAR(20) | | ACCEPT / WEAK_ACCEPT / BORDERLINE / WEAK_REJECT / REJECT |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |

JSONB 结构示例（strengths/weaknesses/suggestions）：
```json
[
  {
    "content": "The proposed method achieves significant improvement on Dataset A.",
    "evidence_ids": ["uuid-1", "uuid-2"]
  }
]
```

索引：
- `idx_review_paper_id` ON (paper_id)
- `idx_review_task_id` ON (task_id) UNIQUE

### review_evidence 关联表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| review_id | UUID | FK → ReviewResult.id | 审阅结果 |
| evidence_id | UUID | FK → Evidence.id | 证据 |

索引：
- `idx_review_evidence` ON (review_id, evidence_id) UNIQUE

## 8. MetricRecord

实验指标记录，从论文表格和正文中提取。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| paper_id | UUID | FK → Paper.id | 所属论文 |
| task_id | UUID | FK → AnalysisTask.id | 关联任务 |
| model_name | VARCHAR(200) | | 模型名称 |
| dataset_name | VARCHAR(200) | | 数据集名称 |
| metric_name | VARCHAR(100) | NOT NULL | 指标名称（accuracy, F1, BLEU 等） |
| metric_value | FLOAT | NOT NULL | 指标值 |
| checkpoint_type | VARCHAR(20) | | 统计口径：FINAL / MAX / MEAN / BEST / LAST / UNKNOWN |
| checkpoint_source | VARCHAR(50) | | 口径来源：EXPLICIT_TEXT / IMPLICIT_CONTEXT / TABLE_HEADER / UNKNOWN |
| evidence_id | UUID | FK → Evidence.id | 关联证据 |
| raw_text | TEXT | | 原始文本片段 |
| table_id | VARCHAR(100) | | 来源表格标识 |
| row_index | INTEGER | | 表格行号 |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |

索引：
- `idx_metric_paper_id` ON (paper_id)
- `idx_metric_task_id` ON (task_id)
- `idx_metric_checkpoint_type` ON (checkpoint_type)

## 9. ExperimentFile

实验数据文件（CSV/Excel）。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| paper_id | UUID | FK → Paper.id | 关联论文 |
| filename | VARCHAR(255) | NOT NULL | 原始文件名 |
| obs_key | VARCHAR(1024) | NOT NULL | OBS 存储路径 |
| file_size | BIGINT | NOT NULL | 文件大小 |
| file_hash | VARCHAR(64) | NOT NULL | SHA-256 哈希 |
| file_type | VARCHAR(10) | NOT NULL | CSV / XLSX / XLS |
| row_count | INTEGER | | 数据行数 |
| column_count | INTEGER | | 数据列数 |
| columns_info | JSONB | | 列名与类型信息 |
| user_id | VARCHAR(128) | NOT NULL | 所属用户 |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |

索引：
- `idx_exp_file_paper_id` ON (paper_id)
- `idx_exp_file_user_id` ON (user_id)

## 10. ExperimentResult

实验数据分析结果，由确定性代码计算。

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
  "columns": {
    "accuracy": {
      "count": 10,
      "mean": 0.852,
      "std": 0.023,
      "min": 0.810,
      "max": 0.891,
      "median": 0.855
    }
  }
}
```

JSONB 结构示例（metric_comparisons）：
```json
[
  {
    "metric_name": "accuracy",
    "dataset": "SQuAD",
    "paper_value": 0.891,
    "experiment_value": 0.855,
    "diff": -0.036,
    "checkpoint_type": "MAX",
    "status": "MISMATCH"
  }
]
```

索引：
- `idx_exp_result_file_id` ON (file_id) UNIQUE

## 11. ExportReport

导出报告记录。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| paper_id | UUID | FK → Paper.id | 关联论文 |
| report_type | VARCHAR(20) | NOT NULL | MARKDOWN / PDF / DOCX |
| obs_key | VARCHAR(1024) | | 导出文件 OBS 路径 |
| content_hash | VARCHAR(64) | | 内容哈希 |
| file_size | BIGINT | | 文件大小 |
| user_id | VARCHAR(128) | NOT NULL | 所属用户 |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |

索引：
- `idx_export_paper_id` ON (paper_id)
- `idx_export_user_id` ON (user_id)