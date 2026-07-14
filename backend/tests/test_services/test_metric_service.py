import datetime

import pytest

from paperlens.core.enums import CheckpointType
from paperlens.services.metric_service import (
    EvidenceSource,
    TableSource,
    _dedup_candidates,
    _extract_from_evidence,
    _extract_from_table,
    _is_percent_metric,
    determine_checkpoint_type,
    extract_model_dataset_from_context,
    normalize_metric_name,
    parse_metric_value,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("acc", "accuracy"),
        ("Accuracy", "accuracy"),
        ("F1-score", "F1"),
        ("F1Score", "F1"),
        ("AUROC", "AUC"),
        ("AP", "mAP"),
        ("mIoU", "mIoU"),
        ("自定义指标", "自定义指标"),
    ],
)
def test_normalize_metric_aliases_and_unicode(raw, expected):
    assert normalize_metric_name(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["", "  ", "2024", "epoch", "learning_rate", "batch size", "样本数量", "Model", "Dataset"],
)
def test_normalize_metric_rejects_non_metrics(raw):
    assert normalize_metric_name(raw) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0", 0.0),
        ("42", 42.0),
        (".5", 0.5),
        ("1.5e-3", 0.0015),
        ("-1.5e-3", -0.0015),
        ("-0.5", -0.5),
        ("95%", 0.95),
        ("95.2 %", 0.952),
    ],
)
def test_parse_metric_value_supported_forms(raw, expected):
    assert parse_metric_value(raw) == pytest.approx(expected)


@pytest.mark.parametrize(
    "raw",
    ["NaN", "Infinity", "-inf", "0.8-0.9", "0.8~0.9", "0.85±0.02", "-5%", ""],
)
def test_parse_metric_value_rejects_ambiguous_or_non_finite(raw):
    assert parse_metric_value(raw) is None


@pytest.mark.parametrize(
    ("context", "caption", "row_header", "expected", "source"),
    [
        ("final results", None, None, CheckpointType.FINAL, "context"),
        (None, "Best performance", None, CheckpointType.BEST, "caption"),
        (None, None, "max accuracy", CheckpointType.MAX, "row_header"),
        ("some results", "Table 1", "row 1", CheckpointType.UNKNOWN, None),
        ("best results", "final model", None, CheckpointType.UNKNOWN, "conflict"),
        ("finalization study", None, None, CheckpointType.UNKNOWN, None),
    ],
)
def test_checkpoint_determination(context, caption, row_header, expected, source):
    assert determine_checkpoint_type(context, caption, row_header) == (expected, source)


def test_checkpoint_same_type_from_multiple_sources_is_not_conflict():
    assert determine_checkpoint_type("best checkpoint", "best results", None) == (
        CheckpointType.BEST,
        "caption",
    )


def test_context_extraction_requires_explicit_header_semantics():
    assert extract_model_dataset_from_context("Model", "BERT-base", "ignored") == (
        "BERT-base",
        None,
    )
    assert extract_model_dataset_from_context("Dataset", "SQuAD 2.0", "ignored") == (
        None,
        "SQuAD 2.0",
    )
    assert extract_model_dataset_from_context("Accuracy", "BERT-base", "Best on SQuAD") == (
        None,
        None,
    )


def _table(caption=None, rows=None):
    return TableSource(
        id="00000000-0000-0000-0000-000000000010",
        paper_id="00000000-0000-0000-0000-000000000001",
        page_number=1,
        table_index=1,
        caption=caption,
        structured_data={
            "headers": ["Model", "Dataset", "Accuracy", "Loss", "Year"],
            "rows": rows or [["BERT-base", "SQuAD 2.0", "92.5%", "-0.15", "2024"]],
        },
        raw_text=None,
    )


def test_table_extraction_has_explicit_context_source_and_unknown_checkpoint():
    records = _extract_from_table(_table(), "00000000-0000-0000-0000-000000000001")
    assert [(record["metric_name"], record["metric_value"]) for record in records] == [
        ("accuracy", pytest.approx(0.925)),
        ("loss", pytest.approx(-0.15)),
    ]
    assert all(record["model_name"] == "BERT-base" for record in records)
    assert all(record["dataset_name"] == "SQuAD 2.0" for record in records)
    assert all(record["checkpoint_type"] == CheckpointType.UNKNOWN for record in records)
    assert all(record["table_id"] is not None and record["row_index"] == 0 for record in records)
    assert all(record["evidence_id"] is None for record in records)


def test_table_checkpoint_uses_caption_not_numeric_maximum():
    records = _extract_from_table(
        _table(caption="Best checkpoint results"),
        "00000000-0000-0000-0000-000000000001",
    )
    assert all(record["checkpoint_type"] == CheckpointType.BEST for record in records)
    assert all(record["checkpoint_source"] == "caption" for record in records)


def test_percent_metric_without_percent_must_already_be_zero_to_one():
    table = _table(rows=[["A", "D", "92.5", "0.1", "2024"], ["B", "D", "0.93", "0.2", "2025"]])
    records = _extract_from_table(table, "00000000-0000-0000-0000-000000000001")
    accuracy = [record for record in records if record["metric_name"] == "accuracy"]
    assert len(accuracy) == 1
    assert accuracy[0]["model_name"] == "B"
    assert accuracy[0]["metric_value"] == pytest.approx(0.93)


def test_evidence_extraction_only_uses_known_metric_tokens():
    evidence = EvidenceSource(
        id="00000000-0000-0000-0000-000000000020",
        paper_id="00000000-0000-0000-0000-000000000001",
        page_number=2,
        quoted_text="At the final checkpoint, accuracy = 95.3% and loss: -1.2; epoch: 20.",
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )
    records = _extract_from_evidence(evidence, evidence.paper_id)
    assert [(record["metric_name"], record["metric_value"]) for record in records] == [
        ("accuracy", pytest.approx(0.953)),
        ("loss", pytest.approx(-1.2)),
    ]
    assert all(record["checkpoint_type"] == CheckpointType.FINAL for record in records)
    assert all(record["evidence_id"] == evidence.id for record in records)
    assert all(record["table_id"] is None and record["row_index"] is None for record in records)


def _candidate(metric_name, value, table_id=None, evidence_id=None, row_index=None):
    return {
        "metric_name": metric_name,
        "metric_value": value,
        "model_name": None,
        "dataset_name": None,
        "checkpoint_type": CheckpointType.UNKNOWN,
        "table_id": table_id,
        "evidence_id": evidence_id,
        "row_index": row_index,
    }


def test_dedup_prefers_table_source_and_sorts_stably():
    candidates = [
        _candidate("F1", 0.8, evidence_id="e2"),
        _candidate("accuracy", 0.95, evidence_id="e1"),
        _candidate("accuracy", 0.95, table_id="t1", row_index=0),
    ]
    result = _dedup_candidates(candidates)
    assert [record["metric_name"] for record in result] == ["accuracy", "F1"]
    assert result[0]["table_id"] == "t1"


@pytest.mark.parametrize(
    ("metric_name", "expected"),
    [("accuracy", True), ("precision", True), ("F1", True), ("AUC", True), ("loss", False), ("RMSE", False)],
)
def test_percent_metric_classification(metric_name, expected):
    assert _is_percent_metric(metric_name) is expected
