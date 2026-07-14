from __future__ import annotations

import copy
import datetime
import logging
import math
import re
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from paperlens.core.database import SessionLocal
from paperlens.core.enums import CheckpointType, PaperStatus, TaskStatus, TaskType
from paperlens.models.models import AnalysisTask, Evidence, MetricRecord, Paper, PaperTable

logger = logging.getLogger(__name__)

METRIC_ALIASES: dict[str, str] = {
    "accuracy": "accuracy",
    "acc": "accuracy",
    "precision": "precision",
    "recall": "recall",
    "f1": "F1",
    "f1-score": "F1",
    "f1 score": "F1",
    "f1score": "F1",
    "auc": "AUC",
    "auroc": "AUC",
    "map": "mAP",
    "ap": "mAP",
    "bleu": "BLEU",
    "rouge": "ROUGE",
    "iou": "IoU",
    "miou": "mIoU",
    "rmse": "RMSE",
    "mae": "MAE",
    "loss": "loss",
}

CHECKPOINT_KEYWORDS: dict[CheckpointType, tuple[str, ...]] = {
    CheckpointType.FINAL: ("final", "最终"),
    CheckpointType.MAX: ("max", "maximum", "最大", "最高"),
    CheckpointType.MEAN: ("mean", "average", "avg", "平均", "均值"),
    CheckpointType.BEST: ("best", "最优", "最佳", "最好"),
    CheckpointType.LAST: ("last", "latest", "最后", "最新", "最近"),
}

_PERCENT_METRICS = {
    "accuracy",
    "precision",
    "recall",
    "f1",
    "auc",
    "map",
    "bleu",
    "rouge",
    "iou",
    "miou",
}
_MODEL_HEADERS = {"model", "model name", "method", "method name", "architecture", "system"}
_DATASET_HEADERS = {"dataset", "dataset name", "data", "corpus", "benchmark"}
_NON_METRIC_PATTERNS = re.compile(
    r"^(?:year|年份|epoch|batch|step|iteration|sample|样本(?:数量|数)?|layer|层数|param|参数|size|大小|count|数量|seed|lr|learning[ _.-]?rate|dropout|weight[ _.-]?decay|gamma|beta|alpha|lambda|threshold|num(?:ber)?[ _.-]|n[ _.-]|dimension|维度|hidden|model|method|architecture|system|dataset|data|corpus|benchmark)(?:$|[ _./:(-])",
    re.IGNORECASE,
)
_NUMBER_PATTERN = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
_EVIDENCE_METRIC_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])(?P<name>accuracy|acc|precision|recall|f1(?:[-_ ]?score)?|auc|auroc|map|ap|bleu|rouge|miou|iou|rmse|mae|loss)(?![A-Za-z0-9_])"
    r"\s*(?:=|:|\bis\b|\bof\b)\s*"
    r"(?P<value>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\s*%?)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TableSource:
    id: str
    paper_id: str
    page_number: int
    table_index: int
    caption: str | None
    structured_data: dict[str, Any] | None
    raw_text: str | None


@dataclass(frozen=True)
class EvidenceSource:
    id: str
    paper_id: str
    page_number: int
    quoted_text: str
    created_at: datetime.datetime


def normalize_metric_name(raw_name: str) -> str | None:
    if not isinstance(raw_name, str):
        return None
    stripped = raw_name.strip()
    if not stripped or len(stripped) > 100 or any(ord(ch) < 32 for ch in stripped):
        return None
    if _NON_METRIC_PATTERNS.match(stripped) or not any(ch.isalpha() for ch in stripped):
        return None
    return METRIC_ALIASES.get(stripped.casefold(), stripped)


def parse_metric_value(raw: str) -> float | None:
    if not isinstance(raw, str):
        return None
    value_text = raw.strip()
    if not value_text:
        return None
    is_percent = value_text.endswith("%")
    number_text = value_text[:-1].strip() if is_percent else value_text
    if not _NUMBER_PATTERN.fullmatch(number_text):
        return None
    try:
        value = float(number_text)
    except ValueError:
        return None
    if not math.isfinite(value) or (is_percent and value < 0):
        return None
    return value / 100.0 if is_percent else value


def _keyword_present(text: str, keyword: str) -> bool:
    if keyword.isascii():
        return re.search(
            rf"(?<![A-Za-z0-9_]){re.escape(keyword)}(?![A-Za-z0-9_])",
            text,
            re.IGNORECASE,
        ) is not None
    return keyword in text


def determine_checkpoint_type(
    context: str | None,
    caption: str | None,
    row_header: str | None,
) -> tuple[CheckpointType, str | None]:
    matches: list[tuple[CheckpointType, str]] = []
    for text, source_name in (
        (caption, "caption"),
        (row_header, "row_header"),
        (context, "context"),
    ):
        if not text:
            continue
        for checkpoint_type, keywords in CHECKPOINT_KEYWORDS.items():
            if any(_keyword_present(text, keyword) for keyword in keywords):
                matches.append((checkpoint_type, source_name))
    if not matches:
        return CheckpointType.UNKNOWN, None
    if len({checkpoint_type for checkpoint_type, _ in matches}) > 1:
        return CheckpointType.UNKNOWN, "conflict"
    return matches[0]


def _normalize_header(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[\s_.-]+", " ", value.strip().casefold())


def _context_header_kind(value: Any) -> str | None:
    normalized = _normalize_header(value)
    if normalized in _MODEL_HEADERS:
        return "model"
    if normalized in _DATASET_HEADERS:
        return "dataset"
    return None


def _clean_context_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped or len(stripped) > 200 or any(ord(ch) < 32 for ch in stripped):
        return None
    if parse_metric_value(stripped) is not None or normalize_metric_name(stripped) in METRIC_ALIASES.values():
        return None
    return stripped


def extract_model_dataset_from_context(
    header: str | None,
    row_label: str | None,
    caption: str | None,
) -> tuple[str | None, str | None]:
    del caption
    value = _clean_context_value(row_label)
    if value is None:
        return None, None
    kind = _context_header_kind(header)
    if kind == "model":
        return value, None
    if kind == "dataset":
        return None, value
    return None, None


def _extract_model_dataset_from_row(headers: list[Any], row: list[Any]) -> tuple[str | None, str | None]:
    model_name = None
    dataset_name = None
    for index, header in enumerate(headers):
        if index >= len(row):
            break
        value = _clean_context_value(row[index])
        if value is None:
            continue
        kind = _context_header_kind(header)
        if kind == "model" and model_name is None:
            model_name = value
        elif kind == "dataset" and dataset_name is None:
            dataset_name = value
    return model_name, dataset_name


def _is_percent_metric(canonical_name: str) -> bool:
    return canonical_name.casefold() in _PERCENT_METRICS


def _extract_from_table(table: TableSource | PaperTable, paper_id: str) -> list[dict[str, Any]]:
    data = table.structured_data
    if not isinstance(data, dict):
        return []
    headers = data.get("headers")
    rows = data.get("rows")
    if not isinstance(headers, list) or not isinstance(rows, list) or not headers or not rows:
        return []

    candidates: list[dict[str, Any]] = []
    for row_index, row in enumerate(rows):
        if not isinstance(row, list):
            continue
        model_name, dataset_name = _extract_model_dataset_from_row(headers, row)
        row_header = row[0] if row and isinstance(row[0], str) else None
        for column_index, cell in enumerate(row):
            if column_index >= len(headers) or _context_header_kind(headers[column_index]) is not None:
                continue
            metric_name = normalize_metric_name(headers[column_index])
            if metric_name is None or cell is None:
                continue
            raw_value = str(cell).strip()
            metric_value = parse_metric_value(raw_value)
            if metric_value is None:
                continue
            if _is_percent_metric(metric_name) and not 0.0 <= metric_value <= 1.0:
                continue
            checkpoint_type, checkpoint_source = determine_checkpoint_type(
                context=None,
                caption=table.caption,
                row_header=row_header,
            )
            candidates.append(
                {
                    "paper_id": paper_id,
                    "model_name": model_name,
                    "dataset_name": dataset_name,
                    "metric_name": metric_name,
                    "metric_value": metric_value,
                    "checkpoint_type": checkpoint_type,
                    "checkpoint_source": checkpoint_source,
                    "table_id": table.id,
                    "row_index": row_index,
                    "evidence_id": None,
                    "raw_text": f"{str(headers[column_index]).strip()}: {raw_value}",
                }
            )
    return candidates


def _extract_from_evidence(evidence: EvidenceSource | Evidence, paper_id: str) -> list[dict[str, Any]]:
    text = evidence.quoted_text
    if not isinstance(text, str) or not text:
        return []
    candidates: list[dict[str, Any]] = []
    for match in _EVIDENCE_METRIC_PATTERN.finditer(text):
        metric_name = normalize_metric_name(match.group("name"))
        metric_value = parse_metric_value(match.group("value"))
        if metric_name is None or metric_value is None:
            continue
        if _is_percent_metric(metric_name) and not 0.0 <= metric_value <= 1.0:
            continue
        checkpoint_type, checkpoint_source = determine_checkpoint_type(text, None, None)
        candidates.append(
            {
                "paper_id": paper_id,
                "model_name": None,
                "dataset_name": None,
                "metric_name": metric_name,
                "metric_value": metric_value,
                "checkpoint_type": checkpoint_type,
                "checkpoint_source": checkpoint_source,
                "table_id": None,
                "row_index": None,
                "evidence_id": evidence.id,
                "raw_text": match.group(0),
            }
        )
    return candidates


def _dedup_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: dict[tuple[Any, ...], dict[str, Any]] = {}
    for candidate in candidates:
        checkpoint = candidate.get("checkpoint_type")
        checkpoint_value = checkpoint.value if isinstance(checkpoint, CheckpointType) else checkpoint
        key = (
            candidate["metric_name"],
            candidate["metric_value"],
            candidate.get("model_name"),
            candidate.get("dataset_name"),
            checkpoint_value,
        )
        current = selected.get(key)
        if current is None or (
            candidate.get("table_id") is not None and current.get("table_id") is None
        ):
            selected[key] = candidate
    return sorted(
        selected.values(),
        key=lambda item: (
            item["metric_name"].casefold(),
            item.get("model_name") or "",
            item.get("dataset_name") or "",
            item["metric_value"],
            item.get("table_id") or "",
            item.get("row_index") if item.get("row_index") is not None else -1,
            item.get("evidence_id") or "",
        ),
    )


def load_metric_sources(db: Session, paper_id: str) -> tuple[list[TableSource], list[EvidenceSource]]:
    tables = (
        db.query(PaperTable)
        .filter(PaperTable.paper_id == paper_id)
        .order_by(PaperTable.page_number.asc(), PaperTable.table_index.asc(), PaperTable.id.asc())
        .all()
    )
    evidences = (
        db.query(Evidence)
        .filter(Evidence.paper_id == paper_id)
        .order_by(Evidence.page_number.asc(), Evidence.created_at.asc(), Evidence.id.asc())
        .all()
    )
    table_sources = [
        TableSource(
            id=table.id,
            paper_id=table.paper_id,
            page_number=table.page_number,
            table_index=table.table_index,
            caption=table.caption,
            structured_data=copy.deepcopy(table.structured_data),
            raw_text=table.raw_text,
        )
        for table in tables
    ]
    evidence_sources = [
        EvidenceSource(
            id=evidence.id,
            paper_id=evidence.paper_id,
            page_number=evidence.page_number,
            quoted_text=evidence.quoted_text,
            created_at=evidence.created_at,
        )
        for evidence in evidences
    ]
    return table_sources, evidence_sources


def extract_metrics_from_sources(
    paper_id: str,
    tables: list[TableSource],
    evidences: list[EvidenceSource],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for table in tables:
        candidates.extend(_extract_from_table(table, paper_id))
    for evidence in evidences:
        candidates.extend(_extract_from_evidence(evidence, paper_id))
    return _dedup_candidates(candidates)


def extract_metrics_from_paper(paper_id: str, db: Session) -> list[dict[str, Any]]:
    tables, evidences = load_metric_sources(db, paper_id)
    return extract_metrics_from_sources(paper_id, tables, evidences)


def _validate_candidates(
    db: Session,
    paper_id: str,
    candidates: list[dict[str, Any]],
) -> None:
    table_ids = {candidate.get("table_id") for candidate in candidates if candidate.get("table_id")}
    evidence_ids = {candidate.get("evidence_id") for candidate in candidates if candidate.get("evidence_id")}
    tables = {
        table.id: table
        for table in db.query(PaperTable).filter(PaperTable.id.in_(table_ids)).all()
    } if table_ids else {}
    evidences = {
        evidence.id: evidence
        for evidence in db.query(Evidence).filter(Evidence.id.in_(evidence_ids)).all()
    } if evidence_ids else {}

    for candidate in candidates:
        if candidate.get("paper_id") != paper_id:
            raise ValueError("Metric candidate paper mismatch")
        metric_name = candidate.get("metric_name")
        if not isinstance(metric_name, str) or normalize_metric_name(metric_name) != metric_name:
            raise ValueError("Invalid metric name")
        metric_value = candidate.get("metric_value")
        if isinstance(metric_value, bool) or not isinstance(metric_value, (int, float)) or not math.isfinite(metric_value):
            raise ValueError("Invalid metric value")
        if _is_percent_metric(metric_name) and not 0.0 <= metric_value <= 1.0:
            raise ValueError("Invalid percent metric value")
        try:
            CheckpointType(candidate.get("checkpoint_type"))
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid checkpoint type") from exc
        raw_text = candidate.get("raw_text")
        if not isinstance(raw_text, str) or not raw_text.strip() or len(raw_text) > 500:
            raise ValueError("Invalid metric source text")
        for field in ("model_name", "dataset_name"):
            value = candidate.get(field)
            if value is not None and _clean_context_value(value) != value:
                raise ValueError(f"Invalid {field}")

        table_id = candidate.get("table_id")
        evidence_id = candidate.get("evidence_id")
        row_index = candidate.get("row_index")
        if (table_id is None) == (evidence_id is None):
            raise ValueError("Metric candidate must have exactly one source")
        if table_id is not None:
            table = tables.get(table_id)
            if table is None or table.paper_id != paper_id:
                raise ValueError("Invalid metric table source")
            rows = table.structured_data.get("rows") if isinstance(table.structured_data, dict) else None
            if isinstance(row_index, bool) or not isinstance(row_index, int) or row_index < 0:
                raise ValueError("Invalid metric row index")
            if not isinstance(rows, list) or row_index >= len(rows):
                raise ValueError("Metric row index out of range")
        elif row_index is not None:
            raise ValueError("Evidence metric cannot have row index")
        else:
            evidence = evidences.get(evidence_id)
            if evidence is None or evidence.paper_id != paper_id:
                raise ValueError("Invalid metric evidence source")


def _safe_metric_error(_exc: Exception) -> str:
    return "指标提取失败，请稍后重试"


def run_metric_extraction_task(task_id: str) -> None:
    db = SessionLocal()
    claimed = False
    try:
        task = (
            db.query(AnalysisTask)
            .filter(AnalysisTask.id == task_id)
            .with_for_update()
            .one_or_none()
        )
        if task is None:
            logger.error("Metric extraction task %s was not found", task_id)
            return
        if task.status != TaskStatus.PENDING:
            db.rollback()
            return
        claimed = True
        if task.task_type != TaskType.METRIC_EXTRACTION:
            raise ValueError("Unsupported metric task type")
        paper = db.get(Paper, task.paper_id)
        if paper is None or paper.status != PaperStatus.PARSED:
            raise ValueError("Paper is not ready for metric extraction")
        if paper.user_id != task.user_id:
            raise ValueError("Metric task owner mismatch")

        paper_id = task.paper_id
        user_id = task.user_id
        task.status = TaskStatus.RUNNING
        task.progress = 10
        task.error_message = None
        task.started_at = datetime.datetime.now(datetime.timezone.utc)
        db.commit()

        tables, evidences = load_metric_sources(db, paper_id)
        db.rollback()
        if db.in_transaction():
            raise RuntimeError("Metric source transaction was not closed")
        candidates = extract_metrics_from_sources(paper_id, tables, evidences)
        if not candidates:
            raise ValueError("No metric candidates found")
        if db.in_transaction():
            raise RuntimeError("Metric extraction opened a database transaction")

        task = (
            db.query(AnalysisTask)
            .filter(AnalysisTask.id == task_id)
            .with_for_update()
            .one_or_none()
        )
        if task is None or task.status != TaskStatus.RUNNING:
            raise ValueError("Metric task state changed before persistence")
        paper = db.get(Paper, paper_id)
        if paper is None or paper.user_id != user_id or task.user_id != user_id or task.paper_id != paper_id:
            raise ValueError("Metric task ownership changed before persistence")
        if db.query(MetricRecord.id).filter(MetricRecord.task_id == task_id).first() is not None:
            raise ValueError("Metric task already has records")

        _validate_candidates(db, paper_id, candidates)
        for candidate in candidates:
            db.add(
                MetricRecord(
                    id=str(uuid.uuid4()),
                    paper_id=paper_id,
                    task_id=task_id,
                    user_id=user_id,
                    model_name=candidate.get("model_name"),
                    dataset_name=candidate.get("dataset_name"),
                    metric_name=candidate["metric_name"],
                    metric_value=candidate["metric_value"],
                    checkpoint_type=candidate["checkpoint_type"],
                    checkpoint_source=candidate.get("checkpoint_source"),
                    evidence_id=candidate.get("evidence_id"),
                    table_id=candidate.get("table_id"),
                    row_index=candidate.get("row_index"),
                    raw_text=candidate["raw_text"],
                )
            )
        db.flush()
        task.status = TaskStatus.SUCCEEDED
        task.progress = 100
        task.completed_at = datetime.datetime.now(datetime.timezone.utc)
        task.error_message = None
        db.commit()
    except Exception as exc:
        logger.error("Metric extraction task %s failed (%s)", task_id, type(exc).__name__)
        db.rollback()
        if claimed:
            task = (
                db.query(AnalysisTask)
                .filter(AnalysisTask.id == task_id)
                .with_for_update()
                .one_or_none()
            )
            if task is not None and task.status == TaskStatus.RUNNING:
                db.query(MetricRecord).filter(MetricRecord.task_id == task_id).delete(synchronize_session=False)
                task.status = TaskStatus.FAILED
                task.progress = 100
                task.error_message = _safe_metric_error(exc)
                task.completed_at = datetime.datetime.now(datetime.timezone.utc)
                db.commit()
            else:
                db.rollback()
    finally:
        db.close()
