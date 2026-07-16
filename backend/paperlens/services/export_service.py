from __future__ import annotations

import hashlib
import html
import json
import math
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, defer, selectinload

from paperlens.core.config import settings
from paperlens.core.database import SessionLocal
from paperlens.core.enums import (
    ExportStatus,
    FindingType,
    OverallVerdict,
    ReviewDimension,
    TaskStatus,
    TaskType,
)
from paperlens.core.errors import AppError
from paperlens.models.models import (
    AnalysisTask,
    Evidence,
    ExperimentFile,
    ExperimentResult,
    ExportReport,
    MetricRecord,
    Paper,
    PaperTable,
    ReviewFinding,
    ReviewResult,
)
from paperlens.schemas.experiment_file import ComparisonItem, SummaryStatsResponse
from paperlens.utils.storage import get_storage


_FAILED_MESSAGE = "报告生成失败，请稍后重试"
_SOURCE_INVALID_MESSAGE = "报告来源数据异常"
_EVIDENCE_QUOTE_LIMIT = 240

_REVIEW_DIMENSION_ORDER = [
    "SOUNDNESS",
    "NOVELTY",
    "CLARITY",
    "COMPLETENESS",
    "REPRODUCIBILITY",
    "SIGNIFICANCE",
    "OVERALL",
]

_ZH_LABELS = {
    "title": "论文审阅报告",
    "paper_info": "论文信息",
    "paper_title": "论文标题",
    "filename": "文件名",
    "pages": "页数",
    "review_section": "审阅详情",
    "dimension": "维度",
    "rating": "评分",
    "verdict": "结论",
    "summary": "摘要",
    "strengths": "优势",
    "weaknesses": "不足",
    "suggestions": "建议",
    "evidence_page": "证据页",
    "evidence_quote": "证据引用",
    "metrics_section": "指标数据",
    "no_metrics": "暂无指标数据",
    "model": "模型",
    "dataset": "数据集",
    "metric_name": "指标名",
    "metric_value": "指标值",
    "checkpoint": "检查点",
    "experiment_section": "实验分析数据",
    "no_experiment": "暂无实验分析数据",
    "file": "文件",
    "rows": "行数",
    "columns": "列数",
    "statistics": "统计摘要",
    "column_name": "列名",
    "dtype": "类型",
    "count": "有效值",
    "null_count": "空值",
    "mean": "均值",
    "stddev": "标准差",
    "min": "最小值",
    "max": "最大值",
    "median": "中位数",
    "comparison_section": "交叉验证",
    "status": "状态",
    "match": "匹配",
    "mismatch": "不匹配",
    "unverifiable": "不可验证",
    "reason": "原因",
    "paper_value": "论文值",
    "experiment_value": "实验值",
    "diff": "差值",
    "generated_at": "生成时间",
}

_EN_LABELS = {
    "title": "Paper Review Report",
    "paper_info": "Paper Information",
    "paper_title": "Title",
    "filename": "Filename",
    "pages": "Pages",
    "review_section": "Review Details",
    "dimension": "Dimension",
    "rating": "Rating",
    "verdict": "Verdict",
    "summary": "Summary",
    "strengths": "Strengths",
    "weaknesses": "Weaknesses",
    "suggestions": "Suggestions",
    "evidence_page": "Evidence Page",
    "evidence_quote": "Evidence Quote",
    "metrics_section": "Metrics Data",
    "no_metrics": "No metrics data available",
    "model": "Model",
    "dataset": "Dataset",
    "metric_name": "Metric",
    "metric_value": "Value",
    "checkpoint": "Checkpoint",
    "experiment_section": "Experiment Analysis Data",
    "no_experiment": "No experiment analysis data available",
    "file": "File",
    "rows": "Rows",
    "columns": "Columns",
    "statistics": "Statistics Summary",
    "column_name": "Column",
    "dtype": "Type",
    "count": "Count",
    "null_count": "Nulls",
    "mean": "Mean",
    "stddev": "Std Dev",
    "min": "Min",
    "max": "Max",
    "median": "Median",
    "comparison_section": "Cross Validation",
    "status": "Status",
    "match": "MATCH",
    "mismatch": "MISMATCH",
    "unverifiable": "UNVERIFIABLE",
    "reason": "Reason",
    "paper_value": "Paper Value",
    "experiment_value": "Experiment Value",
    "diff": "Diff",
    "generated_at": "Generated At",
}

_REASON_LABELS = {
    "AMBIGUOUS_PAPER_METRIC": {"zh": "论文指标歧义", "en": "Ambiguous paper metric"},
    "NO_EXPERIMENT_COLUMN": {"zh": "无对应实验列", "en": "No matching experiment column"},
    "AMBIGUOUS_EXPERIMENT_COLUMN": {"zh": "实验列歧义", "en": "Ambiguous experiment column"},
    "UNSUPPORTED_CHECKPOINT": {"zh": "不支持的检查点", "en": "Unsupported checkpoint"},
    "EMPTY_NORMALIZED_NAME": {"zh": "标准化名称为空", "en": "Empty normalized name"},
}

_VERDICT_LABELS = {
    "ACCEPT": {"zh": "接受", "en": "Accept"},
    "WEAK_ACCEPT": {"zh": "弱接受", "en": "Weak Accept"},
    "BORDERLINE": {"zh": "边界", "en": "Borderline"},
    "WEAK_REJECT": {"zh": "弱拒绝", "en": "Weak Reject"},
    "REJECT": {"zh": "拒绝", "en": "Reject"},
}

_CHECKPOINT_LABELS = {
    "BEST": {"zh": "最佳", "en": "Best"},
    "FINAL": {"zh": "最终", "en": "Final"},
    "MAX": {"zh": "最大", "en": "Max"},
    "MEAN": {"zh": "均值", "en": "Mean"},
    "LAST": {"zh": "最近", "en": "Last"},
    "UNKNOWN": {"zh": "未知", "en": "Unknown"},
}


def _esc(text: str | None) -> str:
    if text is None:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = html.escape(text, quote=False)
    escaped_lines: list[str] = []
    for line in text.split("\n"):
        line = line.replace("\\", "\\\\")
        if line.startswith(("- ", "+ ")):
            line = "\\" + line
        else:
            prefix = line.split(" ", 1)[0]
            if prefix[:-1].isdigit() and prefix.endswith("."):
                line = prefix[:-1] + "\\." + line[len(prefix):]
        for char in ("`", "*", "[", "]", "#", "!", ">", "|"):
            line = line.replace(char, "\\" + char)
        line = re.sub(r"(?i)\b(javascript|data):", r"\1\\:", line)
        escaped_lines.append(line)
    return "\n".join(escaped_lines)


def _esc_cell(text: str | None) -> str:
    if text is None:
        return ""
    text = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    text = html.escape(text, quote=False)
    text = text.replace("\\", "\\\\")
    for char in ("|", "`", "*", "_", "[", "]", "(", ")", "#", "!", ">"):
        text = text.replace(char, "\\" + char)
    text = re.sub(r"(?i)\b(javascript|data):", r"\1\\:", text)
    return text


def _fmt_num(value: object) -> str:
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return ""
    if not math.isfinite(float(value)):
        return ""
    return str(value)


def _short_quote(text: str) -> str:
    normalized = " ".join(text.replace("\r\n", "\n").replace("\r", "\n").split())
    if len(normalized) <= _EVIDENCE_QUOTE_LIMIT:
        return normalized
    return normalized[: _EVIDENCE_QUOTE_LIMIT - 1].rstrip() + "…"


def _source_invalid() -> AppError:
    return AppError("EXPORT_SOURCE_INVALID", _SOURCE_INVALID_MESSAGE, 409)


def _select_review_task(paper_id: str, user_id: str, db: Session) -> AnalysisTask | None:
    return (
        db.query(AnalysisTask)
        .filter(
            AnalysisTask.paper_id == paper_id,
            AnalysisTask.user_id == user_id,
            AnalysisTask.task_type == TaskType.REVIEW,
            AnalysisTask.status == TaskStatus.SUCCEEDED,
        )
        .order_by(
            AnalysisTask.completed_at.desc().nulls_last(),
            AnalysisTask.created_at.desc(),
            AnalysisTask.id.desc(),
        )
        .first()
    )


def _select_metric_task(paper_id: str, user_id: str, db: Session) -> AnalysisTask | None:
    return (
        db.query(AnalysisTask)
        .filter(
            AnalysisTask.paper_id == paper_id,
            AnalysisTask.user_id == user_id,
            AnalysisTask.task_type == TaskType.METRIC_EXTRACTION,
            AnalysisTask.status == TaskStatus.SUCCEEDED,
        )
        .order_by(
            AnalysisTask.completed_at.desc().nulls_last(),
            AnalysisTask.created_at.desc(),
            AnalysisTask.id.desc(),
        )
        .first()
    )


def _load_review_results(
    task_id: str,
    paper_id: str,
    db: Session,
) -> list[ReviewResult]:
    results = (
        db.query(ReviewResult)
        .filter(ReviewResult.task_id == task_id)
        .all()
    )
    valid_dimensions = {item.value for item in ReviewDimension}
    valid_verdicts = {item.value for item in OverallVerdict}
    for result in results:
        if (
            result.paper_id != paper_id
            or result.dimension not in valid_dimensions
            or (result.rating is not None and not 1 <= result.rating <= 5)
            or (result.overall_verdict is not None and result.overall_verdict not in valid_verdicts)
        ):
            raise _source_invalid()
    review_ids = [result.id for result in results]
    findings = []
    if review_ids:
        findings = (
            db.query(ReviewFinding)
            .filter(ReviewFinding.review_id.in_(review_ids))
            .options(selectinload(ReviewFinding.evidences))
            .order_by(ReviewFinding.review_id, ReviewFinding.sequence, ReviewFinding.id)
            .all()
        )
    grouped: dict[str, list[ReviewFinding]] = {review_id: [] for review_id in review_ids}
    valid_finding_types = {item.value for item in FindingType}
    for finding in findings:
        if finding.review_id not in grouped or finding.finding_type not in valid_finding_types:
            raise _source_invalid()
        for evidence in finding.evidences:
            if evidence.paper_id != paper_id or evidence.page_number < 1 or not evidence.quoted_text:
                raise _source_invalid()
        grouped[finding.review_id].append(finding)
    for result in results:
        result._export_findings = grouped[result.id]
    dim_order = {d: i for i, d in enumerate(_REVIEW_DIMENSION_ORDER)}
    return sorted(results, key=lambda r: (dim_order.get(r.dimension, 99), r.id))


def _load_metrics(task_id: str, paper_id: str, user_id: str, db: Session) -> list[MetricRecord]:
    records = (
        db.query(MetricRecord)
        .filter(MetricRecord.task_id == task_id)
        .order_by(MetricRecord.id)
        .options(defer(MetricRecord.raw_text))
        .all()
    )
    _validate_metric_records(records, task_id, paper_id, user_id, db)
    return records


def _validate_metric_records(
    records: list[MetricRecord],
    task_id: str,
    paper_id: str,
    user_id: str,
    db: Session,
) -> None:
    table_ids = {record.table_id for record in records if record.table_id is not None}
    evidence_ids = {record.evidence_id for record in records if record.evidence_id is not None}
    table_rows = {
        row.id: row.paper_id
        for row in db.query(PaperTable.id, PaperTable.paper_id)
        .filter(PaperTable.id.in_(table_ids))
        .all()
    } if table_ids else {}
    evidence_rows = {
        row.id: row.paper_id
        for row in db.query(Evidence.id, Evidence.paper_id)
        .filter(Evidence.id.in_(evidence_ids))
        .all()
    } if evidence_ids else {}
    for record in records:
        table_source = record.table_id is not None
        evidence_source = record.evidence_id is not None
        if (
            record.task_id != task_id
            or record.paper_id != paper_id
            or record.user_id != user_id
            or table_source == evidence_source
            or (table_source and (record.row_index is None or record.row_index < 0))
            or (evidence_source and record.row_index is not None)
        ):
            raise _source_invalid()
        if table_source and table_rows.get(record.table_id) != paper_id:
            raise _source_invalid()
        if evidence_source and evidence_rows.get(record.evidence_id) != paper_id:
            raise _source_invalid()


def _load_experiment_results(paper_id: str, user_id: str, db: Session) -> list[ExperimentResult]:
    tasks = (
        db.query(AnalysisTask)
        .filter(
            AnalysisTask.paper_id == paper_id,
            AnalysisTask.user_id == user_id,
            AnalysisTask.task_type == TaskType.EXPERIMENT_ANALYSIS,
            AnalysisTask.status == TaskStatus.SUCCEEDED,
        )
        .all()
    )
    for task in tasks:
        exp_file = db.get(ExperimentFile, task.experiment_file_id)
        task_results = (
            db.query(ExperimentResult)
            .filter(ExperimentResult.task_id == task.id)
            .all()
        )
        if (
            exp_file is None
            or exp_file.paper_id != paper_id
            or exp_file.user_id != user_id
            or len(task_results) != 1
        ):
            raise _source_invalid()
        result = task_results[0]
        if result.file_id != exp_file.id:
            raise _source_invalid()
    results = (
        db.query(ExperimentResult)
        .join(ExperimentFile, ExperimentFile.id == ExperimentResult.file_id)
        .filter(
            ExperimentFile.paper_id == paper_id,
            ExperimentFile.user_id == user_id,
        )
        .order_by(ExperimentFile.created_at.desc(), ExperimentFile.id.desc())
        .all()
    )
    for result in results:
        exp_file = result.file
        task = db.get(AnalysisTask, result.task_id)
        if (
            exp_file is None
            or exp_file.id != result.file_id
            or exp_file.paper_id != paper_id
            or exp_file.user_id != user_id
            or task is None
            or task.id != result.task_id
            or task.paper_id != paper_id
            or task.user_id != user_id
            or task.task_type != TaskType.EXPERIMENT_ANALYSIS
            or task.status != TaskStatus.SUCCEEDED
            or task.experiment_file_id != exp_file.id
        ):
            raise _source_invalid()
        try:
            summary = SummaryStatsResponse.model_validate(result.summary_stats)
            comparisons = None
            if result.metric_comparisons is not None:
                if not isinstance(result.metric_comparisons, list) or not result.metric_comparisons:
                    raise ValueError
                comparisons = [ComparisonItem.model_validate(item) for item in result.metric_comparisons]
        except (ValidationError, ValueError, TypeError) as exc:
            raise _source_invalid() from exc
        if comparisons:
            metric_task_ids = {str(item.metric_task_id) for item in comparisons}
            metric_record_ids = {str(item.metric_record_id) for item in comparisons}
            if len(metric_task_ids) != 1:
                raise _source_invalid()
            metric_task_id = metric_task_ids.pop()
            metric_task = db.get(AnalysisTask, metric_task_id)
            if (
                metric_task is None
                or metric_task.paper_id != paper_id
                or metric_task.user_id != user_id
                or metric_task.task_type != TaskType.METRIC_EXTRACTION
                or metric_task.status != TaskStatus.SUCCEEDED
            ):
                raise _source_invalid()
            metric_records = (
                db.query(MetricRecord)
                .filter(MetricRecord.id.in_(metric_record_ids))
                .options(defer(MetricRecord.raw_text))
                .all()
            )
            if {record.id for record in metric_records} != metric_record_ids:
                raise _source_invalid()
            _validate_metric_records(metric_records, metric_task_id, paper_id, user_id, db)
        result._export_summary = summary.model_dump(mode="json")
        result._export_comparisons = (
            [item.model_dump(mode="json") for item in comparisons]
            if comparisons is not None
            else None
        )
    return results


def _build_source_snapshot(
    review_task_id: str,
    metric_task_id: str | None,
    experiment_results: list[ExperimentResult],
) -> dict:
    snapshot: dict = {"review_task_id": review_task_id}
    if metric_task_id is not None:
        snapshot["metric_task_id"] = metric_task_id
    if experiment_results:
        snapshot["experiment_results"] = [
            {
                "result_id": str(result.id),
                "file_id": str(result.file_id),
                "task_id": str(result.task_id),
            }
            for result in experiment_results
        ]
    return snapshot


def generate_markdown(
    paper: Paper,
    review_task: AnalysisTask,
    review_results: list[ReviewResult],
    language: str,
    include_metrics: bool,
    include_experiment_analysis: bool,
    metric_task: AnalysisTask | None = None,
    metrics: list[MetricRecord] | None = None,
    experiment_results: list[ExperimentResult] | None = None,
) -> bytes:
    labels = _ZH_LABELS if language == "zh" else _EN_LABELS
    dim_order = {d: i for i, d in enumerate(_REVIEW_DIMENSION_ORDER)}
    review_results = sorted(review_results, key=lambda r: (dim_order.get(r.dimension, 99), getattr(r, 'id', '')))
    lines: list[str] = []

    lines.append(f"# {_esc(labels['title'])}")
    lines.append("")
    lines.append(f"## {_esc(labels['paper_info'])}")
    lines.append("")
    lines.append(f"- **{_esc(labels['paper_title'])}**: {_esc(paper.title)}")
    lines.append(f"- **{_esc(labels['filename'])}**: {_esc(paper.filename)}")
    if paper.page_count is not None:
        lines.append(f"- **{_esc(labels['pages'])}**: {paper.page_count}")
    lines.append("")

    lines.append(f"## {_esc(labels['review_section'])}")
    lines.append("")

    for rr in review_results:
        lines.append(f"### {_esc(rr.dimension)}")
        lines.append("")
        if rr.rating is not None:
            lines.append(f"**{_esc(labels['rating'])}**: {rr.rating}/5")
        if rr.overall_verdict:
            verdict_label = _VERDICT_LABELS.get(rr.overall_verdict, {}).get(language, rr.overall_verdict)
            lines.append(f"**{_esc(labels['verdict'])}**: {_esc(verdict_label)}")
        lines.append("")
        if rr.summary:
            lines.append(f"**{_esc(labels['summary'])}**: {_esc(rr.summary)}")
            lines.append("")

        findings = getattr(rr, "_export_findings", None)
        if findings is None:
            findings = rr.findings if hasattr(rr, "findings") and rr.findings else []
        findings = sorted(findings, key=lambda item: (item.sequence, str(item.id)))
        by_type: dict[str, list[ReviewFinding]] = {}
        for f in findings:
            by_type.setdefault(f.finding_type, []).append(f)

        for ft_key, ft_label_key in [("STRENGTH", "strengths"), ("WEAKNESS", "weaknesses"), ("SUGGESTION", "suggestions")]:
            group = by_type.get(ft_key, [])
            if not group:
                continue
            lines.append(f"**{_esc(labels[ft_label_key])}**:")
            lines.append("")
            for f in group:
                lines.append(f"- {_esc(f.content)}")
                evidences = sorted(f.evidences, key=lambda item: str(item.id)) if f.evidences else []
                for evidence in evidences:
                    quote = _short_quote(evidence.quoted_text)
                    lines.append(
                        f"  - **{_esc(labels['evidence_page'])} {evidence.page_number}**: "
                        f"{_esc(quote)}"
                    )
            lines.append("")

    if include_metrics:
        lines.append(f"## {_esc(labels['metrics_section'])}")
        lines.append("")
        if metric_task and metrics:
            lines.append("| " + " | ".join([
                _esc_cell(labels["model"]),
                _esc_cell(labels["dataset"]),
                _esc_cell(labels["metric_name"]),
                _esc_cell(labels["metric_value"]),
                _esc_cell(labels["checkpoint"]),
            ]) + " |")
            lines.append("| " + " | ".join(["---"] * 5) + " |")
            for m in metrics:
                cp_label = _CHECKPOINT_LABELS.get(m.checkpoint_type, {}).get(language, m.checkpoint_type)
                lines.append("| " + " | ".join([
                    _esc_cell(m.model_name),
                    _esc_cell(m.dataset_name),
                    _esc_cell(m.metric_name),
                    _fmt_num(m.metric_value),
                    _esc_cell(cp_label),
                ]) + " |")
            lines.append("")
        else:
            lines.append(_esc(labels["no_metrics"]))
            lines.append("")

    if include_experiment_analysis:
        lines.append(f"## {_esc(labels['experiment_section'])}")
        lines.append("")
        if experiment_results:
            for er in experiment_results:
                exp_file = er.file if hasattr(er, 'file') and er.file else None
                if exp_file:
                    lines.append(f"### {_esc(exp_file.filename)}")
                    lines.append("")
                    lines.append(f"- **{_esc(labels['rows'])}**: {exp_file.row_count}")
                    lines.append(f"- **{_esc(labels['columns'])}**: {exp_file.column_count}")
                    lines.append("")

                exported_summary = getattr(er, "_export_summary", er.summary_stats)
                ss = exported_summary if isinstance(exported_summary, dict) else {}
                if ss and "columns" in ss:
                    lines.append(f"**{_esc(labels['statistics'])}**:")
                    lines.append("")
                    cols = ss.get("columns", [])
                    lines.append("| " + " | ".join([
                        _esc_cell(labels["column_name"]),
                        _esc_cell(labels["dtype"]),
                        _esc_cell(labels["count"]),
                        _esc_cell(labels["null_count"]),
                        _esc_cell(labels["mean"]),
                        _esc_cell(labels["stddev"]),
                        _esc_cell(labels["min"]),
                        _esc_cell(labels["max"]),
                        _esc_cell(labels["median"]),
                    ]) + " |")
                    lines.append("| " + " | ".join(["---"] * 9) + " |")
                    for col in cols:
                        stats = col.get("stats")
                        lines.append("| " + " | ".join([
                            _esc_cell(col.get("name", "")),
                            _esc_cell(col.get("dtype", "")),
                            _fmt_num(col.get("count")),
                            _fmt_num(col.get("null_count")),
                            _fmt_num(stats.get("mean") if stats else None),
                            _fmt_num(stats.get("stddev") if stats else None),
                            _fmt_num(stats.get("min") if stats else None),
                            _fmt_num(stats.get("max") if stats else None),
                            _fmt_num(stats.get("median") if stats else None),
                        ]) + " |")
                    lines.append("")

                exported_comparisons = getattr(er, "_export_comparisons", er.metric_comparisons)
                comparisons = exported_comparisons if isinstance(exported_comparisons, list) else None
                if comparisons:
                    lines.append(f"**{_esc(labels['comparison_section'])}**:")
                    lines.append("")
                    lines.append("| " + " | ".join([
                        _esc_cell(labels["metric_name"]),
                        _esc_cell(labels["checkpoint"]),
                        _esc_cell(labels["paper_value"]),
                        _esc_cell(labels["experiment_value"]),
                        _esc_cell(labels["diff"]),
                        _esc_cell(labels["status"]),
                        _esc_cell(labels["reason"]),
                    ]) + " |")
                    lines.append("| " + " | ".join(["---"] * 7) + " |")
                    for c in comparisons:
                        status_label = labels.get(c.get("status", "").lower(), c.get("status", ""))
                        reason_raw = c.get("reason")
                        reason_label = _REASON_LABELS.get(reason_raw, {}).get(language, reason_raw or "")
                        cp_label = _CHECKPOINT_LABELS.get(c.get("checkpoint_type", ""), {}).get(language, c.get("checkpoint_type", ""))
                        lines.append("| " + " | ".join([
                            _esc_cell(c.get("metric_name", "")),
                            _esc_cell(cp_label),
                            _fmt_num(c.get("paper_value")),
                            _fmt_num(c.get("experiment_value")),
                            _fmt_num(c.get("diff")),
                            _esc_cell(status_label),
                            _esc_cell(reason_label),
                        ]) + " |")
                    lines.append("")
        else:
            lines.append(_esc(labels["no_experiment"]))
            lines.append("")

    source_time = getattr(review_task, "completed_at", None)
    if not isinstance(source_time, datetime):
        source_time = getattr(review_task, "created_at", None)
    if not isinstance(source_time, datetime):
        source_time = datetime(1970, 1, 1, tzinfo=timezone.utc)
    elif source_time.tzinfo is None:
        source_time = source_time.replace(tzinfo=timezone.utc)
    source_time_text = source_time.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines.append("---")
    lines.append(f"*{_esc(labels['generated_at'])}: {source_time_text}*")
    lines.append("")

    content = "\n".join(lines)
    encoded = content.encode("utf-8")
    return encoded


def compute_content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def compute_source_hash(source_snapshot: dict) -> str:
    encoded = json.dumps(
        source_snapshot,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return compute_content_hash(encoded)


def _find_active_export(
    db: Session,
    paper_id: str,
    user_id: str,
    report_type: str,
    language: str,
    include_metrics: bool,
    include_experiment_analysis: bool,
    source_hash: str,
    content_hash: str,
) -> ExportReport | None:
    return (
        db.query(ExportReport)
        .filter(
            ExportReport.user_id == user_id,
            ExportReport.paper_id == paper_id,
            ExportReport.report_type == report_type,
            ExportReport.language == language,
            ExportReport.include_metrics == include_metrics,
            ExportReport.include_experiment_analysis == include_experiment_analysis,
            ExportReport.source_hash == source_hash,
            ExportReport.content_hash == content_hash,
            ExportReport.status.in_(
                [ExportStatus.PENDING, ExportStatus.GENERATING, ExportStatus.READY]
            ),
        )
        .order_by(ExportReport.created_at, ExportReport.id)
        .first()
    )


def _recover_created_export(
    report_id: str,
    paper_id: str,
    user_id: str,
    report_type: str,
    language: str,
    include_metrics: bool,
    include_experiment_analysis: bool,
    source_hash: str,
    content_hash: str,
) -> tuple[ExportReport | None, bool]:
    recovery_db = SessionLocal()
    try:
        own_report = recovery_db.get(ExportReport, report_id)
        if own_report is not None:
            recovery_db.expunge(own_report)
            return own_report, False
        existing = _find_active_export(
            recovery_db,
            paper_id,
            user_id,
            report_type,
            language,
            include_metrics,
            include_experiment_analysis,
            source_hash,
            content_hash,
        )
        if existing is not None:
            recovery_db.expunge(existing)
        return existing, True
    finally:
        recovery_db.close()


def create_export(
    paper_id: str,
    user_id: str,
    report_type: str,
    language: str,
    include_metrics: bool,
    include_experiment_analysis: bool,
    db: Session,
) -> tuple[ExportReport, bool, bytes | None]:
    paper = db.get(Paper, paper_id)
    if paper is None or paper.user_id != user_id:
        raise AppError("NOT_FOUND", "论文不存在", 404)
    if paper.status != "PARSED":
        raise AppError("VALIDATION_ERROR", "论文尚未解析完成", 409)

    review_task = _select_review_task(paper_id, user_id, db)
    if review_task is None:
        raise AppError("REVIEW_NOT_READY", "审阅结果尚未就绪", 409)

    review_results = _load_review_results(review_task.id, paper_id, db)
    if not review_results:
        raise AppError("REVIEW_NOT_READY", "审阅结果尚未就绪", 409)

    metric_task = None
    metrics = None
    if include_metrics:
        metric_task = _select_metric_task(paper_id, user_id, db)
        if metric_task:
            metrics = _load_metrics(metric_task.id, paper_id, user_id, db)

    experiment_results: list[ExperimentResult] | None = None
    if include_experiment_analysis:
        experiment_results = _load_experiment_results(paper_id, user_id, db)

    source_snapshot = _build_source_snapshot(
        review_task_id=review_task.id,
        metric_task_id=metric_task.id if metric_task else None,
        experiment_results=experiment_results or [],
    )
    content = generate_markdown(
        paper=paper,
        review_task=review_task,
        review_results=review_results,
        language=language,
        include_metrics=include_metrics,
        include_experiment_analysis=include_experiment_analysis,
        metric_task=metric_task,
        metrics=metrics,
        experiment_results=experiment_results,
    )
    if report_type == "PDF":
        from paperlens.services.report_converter import markdown_to_pdf
        content = markdown_to_pdf(content)
    elif report_type == "DOCX":
        from paperlens.services.report_converter import markdown_to_docx
        content = markdown_to_docx(content)
    if len(content) > settings.max_report_size_bytes:
        raise AppError("EXPORT_TOO_LARGE", "报告超过大小上限", 413)
    content_hash = compute_content_hash(content)
    source_hash = compute_source_hash(source_snapshot)

    existing = _find_active_export(
        db,
        paper_id,
        user_id,
        report_type,
        language,
        include_metrics,
        include_experiment_analysis,
        source_hash,
        content_hash,
    )
    if existing is not None:
        return existing, True, None

    report = ExportReport(
        id=str(uuid.uuid4()),
        paper_id=paper_id,
        report_type=report_type,
        language=language,
        include_metrics=include_metrics,
        include_experiment_analysis=include_experiment_analysis,
        source_snapshot=source_snapshot,
        source_hash=source_hash,
        content_hash=content_hash,
        status=ExportStatus.PENDING,
        user_id=user_id,
    )
    db.add(report)
    try:
        db.flush()
        db.commit()
        db.refresh(report)
        return report, False, content
    except IntegrityError:
        db.rollback()
        recovered, duplicate = _recover_created_export(
            report.id,
            paper_id,
            user_id,
            report_type,
            language,
            include_metrics,
            include_experiment_analysis,
            source_hash,
            content_hash,
        )
        if recovered is None:
            raise
        return recovered, duplicate, None if duplicate else content
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        recovered, duplicate = _recover_created_export(
            report.id,
            paper_id,
            user_id,
            report_type,
            language,
            include_metrics,
            include_experiment_analysis,
            source_hash,
            content_hash,
        )
        if recovered is None:
            raise
        return recovered, duplicate, None if duplicate else content


def _report_is_ready(
    report_id: str,
    storage_key: str,
    content_hash: str,
    file_size: int,
) -> bool:
    db = SessionLocal()
    try:
        report = db.get(ExportReport, report_id)
        return bool(
            report is not None
            and report.status == ExportStatus.READY
            and report.storage_key == storage_key
            and report.content_hash == content_hash
            and report.file_size == file_size
        )
    finally:
        db.close()


def _delete_unowned_object(storage, storage_key: str) -> None:
    for _ in range(2):
        try:
            storage.delete(storage_key)
            return
        except Exception:
            continue


def _mark_export_failed(report_id: str) -> None:
    for _ in range(2):
        db = SessionLocal()
        try:
            result = db.execute(
                update(ExportReport)
                .where(
                    ExportReport.id == report_id,
                    ExportReport.status.in_([ExportStatus.PENDING, ExportStatus.GENERATING]),
                )
                .values(
                    status=ExportStatus.FAILED,
                    storage_key=None,
                    file_size=None,
                    error_message=_FAILED_MESSAGE,
                    completed_at=datetime.now(timezone.utc),
                )
            )
            if result.rowcount == 0:
                db.rollback()
                return
            db.commit()
            return
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            db.close()


def _claim_export(report_id: str, content_hash: str) -> bool:
    db = SessionLocal()
    try:
        result = db.execute(
            update(ExportReport)
            .where(
                ExportReport.id == report_id,
                ExportReport.status == ExportStatus.PENDING,
                ExportReport.content_hash == content_hash,
            )
            .values(status=ExportStatus.GENERATING)
        )
        if result.rowcount != 1:
            db.rollback()
            return False
        try:
            db.commit()
            return True
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
            recovery_db = SessionLocal()
            try:
                report = recovery_db.get(ExportReport, report_id)
                if report is not None and report.status == ExportStatus.READY:
                    return False
                if report is not None and report.status == ExportStatus.GENERATING:
                    return True
            finally:
                recovery_db.close()
            _mark_export_failed(report_id)
            return False
    finally:
        db.close()


def run_export_task(report_id: str, content: bytes) -> None:
    content_hash = compute_content_hash(content)
    if len(content) > settings.max_report_size_bytes or not _claim_export(report_id, content_hash):
        if len(content) > settings.max_report_size_bytes:
            _mark_export_failed(report_id)
        return

    storage_key = f"export-reports/{report_id}/report.md"
    storage = None
    object_may_exist = False
    try:
        db = SessionLocal()
        try:
            report = db.get(ExportReport, report_id)
            if (
                report is None
                or report.status != ExportStatus.GENERATING
                or report.content_hash != content_hash
                or report.source_snapshot is None
                or report.source_hash != compute_source_hash(report.source_snapshot)
            ):
                raise ValueError
            ext = {"MARKDOWN": ".md", "PDF": ".pdf", "DOCX": ".docx"}.get(report.report_type, ".md")
            storage_key = f"export-reports/{report_id}/report{ext}"
        finally:
            db.close()

        storage = get_storage()
        ext = {"MARKDOWN": ".md", "PDF": ".pdf", "DOCX": ".docx"}.get(
            report.report_type if report else "MARKDOWN", ".md"
        )
        with tempfile.NamedTemporaryFile(
            dir=tempfile.gettempdir(),
            prefix=f"paperlens_export_{report_id}_",
            suffix=ext,
            delete=False,
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            object_may_exist = True
            storage.save(storage_key, tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        local_path = storage.read_path(storage_key)
        with open(local_path, "rb") as stored_file:
            stored_content = stored_file.read()
        if stored_content != content:
            raise ValueError

        db = SessionLocal()
        try:
            result = db.execute(
                update(ExportReport)
                .where(
                    ExportReport.id == report_id,
                    ExportReport.status == ExportStatus.GENERATING,
                    ExportReport.content_hash == content_hash,
                )
                .values(
                    status=ExportStatus.READY,
                    storage_key=storage_key,
                    file_size=len(content),
                    error_message=None,
                    completed_at=datetime.now(timezone.utc),
                )
            )
            if result.rowcount != 1:
                db.rollback()
                if _report_is_ready(report_id, storage_key, content_hash, len(content)):
                    return
                raise ValueError
            try:
                db.commit()
            except Exception:
                try:
                    db.rollback()
                except Exception:
                    pass
                if _report_is_ready(report_id, storage_key, content_hash, len(content)):
                    return
                raise
        finally:
            db.close()
    except Exception:
        if storage is not None and object_may_exist:
            if not _report_is_ready(report_id, storage_key, content_hash, len(content)):
                _delete_unowned_object(storage, storage_key)
        _mark_export_failed(report_id)
