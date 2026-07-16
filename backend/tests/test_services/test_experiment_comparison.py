import datetime
import math
import uuid

import pytest
from pydantic import ValidationError

from paperlens.core.config import Settings
from paperlens.core.enums import CheckpointType
from paperlens.core.errors import AppError
from paperlens.schemas.experiment_file import ComparisonItem
from paperlens.services.experiment_comparison_service import (
    _build_comparisons,
    _compute_comparison,
    _resolve_experiment_value,
    normalize_comparison_key,
)


class _Metric:
    def __init__(
        self,
        name="accuracy",
        value=0.9,
        checkpoint=CheckpointType.MEAN,
        created_at=None,
        record_id=None,
        task_id=None,
    ):
        self.id = record_id or str(uuid.uuid4())
        self.task_id = task_id or str(uuid.uuid4())
        self.metric_name = name
        self.metric_value = value
        self.checkpoint_type = checkpoint
        self.created_at = created_at or datetime.datetime.now(datetime.timezone.utc)


def _summary(*columns):
    return {"columns": list(columns)}


def _column(name="accuracy", dtype="float", mean=0.9, maximum=0.95):
    return {
        "name": name,
        "dtype": dtype,
        "stats": None if dtype not in {"integer", "float"} else {"mean": mean, "max": maximum},
    }


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("F1_score", "f1score"),
        ("f1 score", "f1score"),
        ("Ｆ１", "f1"),
        ("Straße", "strasse"),
        ("AUC-ROC", "aucroc"),
        ("BLEU-4", "bleu4"),
        ("___", None),
        (None, None),
        (42, None),
    ],
)
def test_normalize_comparison_key(raw, expected):
    assert normalize_comparison_key(raw) == expected


def test_normalization_does_not_add_semantic_aliases():
    assert normalize_comparison_key("acc") != normalize_comparison_key("accuracy")
    assert normalize_comparison_key("ppl") != normalize_comparison_key("perplexity")


@pytest.mark.parametrize(
    ("checkpoint", "expected_statistic", "expected_value"),
    [
        (CheckpointType.MEAN, "MEAN", 0.9),
        (CheckpointType.MAX, "MAX", 0.95),
    ],
)
def test_resolve_supported_checkpoint(checkpoint, expected_statistic, expected_value):
    name, statistic, value, reason = _resolve_experiment_value(
        _summary(_column()),
        "accuracy",
        checkpoint,
    )
    assert (name, statistic, value, reason) == ("accuracy", expected_statistic, expected_value, None)


@pytest.mark.parametrize(
    "checkpoint",
    [CheckpointType.BEST, CheckpointType.FINAL, CheckpointType.LAST, CheckpointType.UNKNOWN],
)
def test_unsupported_checkpoint_is_unverifiable(checkpoint):
    assert _resolve_experiment_value(_summary(_column()), "accuracy", checkpoint) == (
        None,
        None,
        None,
        "UNSUPPORTED_CHECKPOINT",
    )


def test_resolve_no_numeric_column():
    result = _resolve_experiment_value(_summary(_column(name="loss")), "accuracy", CheckpointType.MEAN)
    assert result[-1] == "NO_EXPERIMENT_COLUMN"


def test_resolve_ignores_non_numeric_column():
    result = _resolve_experiment_value(
        _summary(_column(dtype="string")),
        "accuracy",
        CheckpointType.MEAN,
    )
    assert result[-1] == "NO_EXPERIMENT_COLUMN"


def test_resolve_ambiguous_numeric_columns():
    result = _resolve_experiment_value(
        _summary(_column("F1_score"), _column("f1 score")),
        "f1score",
        CheckpointType.MEAN,
    )
    assert result[-1] == "AMBIGUOUS_EXPERIMENT_COLUMN"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), True])
def test_resolve_rejects_invalid_numeric_values(value):
    with pytest.raises(AppError) as exc_info:
        _resolve_experiment_value(
            _summary(_column(mean=value)),
            "accuracy",
            CheckpointType.MEAN,
        )
    assert exc_info.value.code == "COMPARISON_INPUT_INVALID"


def test_compute_match_and_diff_direction():
    result = _compute_comparison(_Metric(value=0.9), _summary(_column(mean=0.895)), 1e-6, 0.01)
    assert result["status"] == "MATCH"
    assert result["statistic"] == "MEAN"
    assert result["diff"] == pytest.approx(-0.005)
    assert result["absolute_diff"] == pytest.approx(0.005)
    assert result["relative_diff"] == pytest.approx(0.005 / 0.9)
    assert result["allowed_diff"] == pytest.approx(0.009)


def test_compute_mismatch_and_negative_values():
    result = _compute_comparison(
        _Metric(name="loss", value=-2.0),
        _summary(_column(name="loss", mean=-2.5)),
        1e-6,
        0.01,
    )
    assert result["status"] == "MISMATCH"
    assert result["diff"] == pytest.approx(-0.5)
    assert result["relative_diff"] == pytest.approx(0.25)


def test_compute_zero_paper_value_uses_null_relative_diff():
    result = _compute_comparison(
        _Metric(name="loss", value=0.0),
        _summary(_column(name="loss", mean=0.0)),
        1e-6,
        0.01,
    )
    assert result["status"] == "MATCH"
    assert result["relative_diff"] is None


def test_compute_exact_tolerance_boundary_matches():
    result = _compute_comparison(_Metric(value=100.0), _summary(_column(mean=101.0)), 1e-6, 0.01)
    assert result["absolute_diff"] == result["allowed_diff"] == 1.0
    assert result["status"] == "MATCH"


def test_compute_absolute_tolerance_can_dominate():
    result = _compute_comparison(_Metric(value=0.01), _summary(_column(mean=0.0105)), 0.001, 0.01)
    assert result["allowed_diff"] == 0.001
    assert result["status"] == "MATCH"


def test_compute_empty_name_is_unverifiable():
    result = _compute_comparison(_Metric(name="___"), _summary(_column()), 1e-6, 0.01)
    assert result["status"] == "UNVERIFIABLE"
    assert result["reason"] == "EMPTY_NORMALIZED_NAME"


def test_compute_duplicate_paper_metric_is_unverifiable():
    result = _compute_comparison(
        _Metric(),
        _summary(_column()),
        1e-6,
        0.01,
        ambiguous_paper_metric=True,
    )
    assert result["status"] == "UNVERIFIABLE"
    assert result["reason"] == "AMBIGUOUS_PAPER_METRIC"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True, 10**1000])
def test_compute_rejects_invalid_or_overflowing_paper_value(value):
    with pytest.raises(AppError) as exc_info:
        _compute_comparison(_Metric(value=value), _summary(_column()), 1e-6, 0.01)
    assert exc_info.value.code == "COMPARISON_INPUT_INVALID"


def test_compute_rejects_arithmetic_overflow():
    with pytest.raises(AppError) as exc_info:
        _compute_comparison(
            _Metric(value=-1e308),
            _summary(_column(mean=1e308)),
            1e-6,
            0.01,
        )
    assert exc_info.value.code == "COMPARISON_INPUT_INVALID"


def test_build_comparisons_marks_duplicate_names_and_sorts_stably(monkeypatch):
    task_id = str(uuid.uuid4())
    base = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    records = [
        _Metric("zeta", 0.9, created_at=base, task_id=task_id),
        _Metric("F1_score", 0.9, created_at=base + datetime.timedelta(seconds=2), task_id=task_id),
        _Metric("f1 score", 0.9, created_at=base + datetime.timedelta(seconds=1), task_id=task_id),
        _Metric("alpha", 0.9, created_at=base, task_id=task_id),
    ]
    result = _build_comparisons(
        records,
        _summary(_column("alpha"), _column("f1 score"), _column("zeta")),
    )
    assert [item["metric_name"] for item in result] == ["alpha", "f1 score", "F1_score", "zeta"]
    assert [item["reason"] for item in result[1:3]] == [
        "AMBIGUOUS_PAPER_METRIC",
        "AMBIGUOUS_PAPER_METRIC",
    ]


def _valid_item():
    paper_value = 0.9
    experiment_value = 0.895
    diff = experiment_value - paper_value
    return {
        "metric_record_id": str(uuid.uuid4()),
        "metric_task_id": str(uuid.uuid4()),
        "metric_name": "accuracy",
        "checkpoint_type": "MEAN",
        "column_name": "accuracy",
        "statistic": "MEAN",
        "paper_value": paper_value,
        "experiment_value": experiment_value,
        "diff": diff,
        "absolute_diff": abs(diff),
        "relative_diff": abs(diff) / paper_value,
        "allowed_diff": paper_value * 0.01,
        "status": "MATCH",
        "reason": None,
    }


def test_comparison_schema_accepts_strict_valid_item():
    assert ComparisonItem.model_validate(_valid_item()).status == "MATCH"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda item: item.update(extra="forbidden"),
        lambda item: item.update(paper_value=float("nan")),
        lambda item: item.update(paper_value=True),
        lambda item: item.update(diff=0.5),
        lambda item: item.update(status="UNVERIFIABLE", reason=None),
        lambda item: item.update(statistic="MAX"),
    ],
)
def test_comparison_schema_rejects_invalid_shapes(mutation):
    item = _valid_item()
    mutation(item)
    with pytest.raises(ValidationError):
        ComparisonItem.model_validate(item)


def test_comparison_schema_accepts_honest_unverifiable_item():
    item = _valid_item()
    item.update(
        column_name=None,
        statistic=None,
        experiment_value=None,
        diff=None,
        absolute_diff=None,
        relative_diff=None,
        allowed_diff=None,
        status="UNVERIFIABLE",
        reason="NO_EXPERIMENT_COLUMN",
    )
    assert ComparisonItem.model_validate(item).status == "UNVERIFIABLE"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("experiment_comparison_absolute_tolerance", -1),
        ("experiment_comparison_absolute_tolerance", 1e12 + 1),
        ("experiment_comparison_relative_tolerance", -0.01),
        ("experiment_comparison_relative_tolerance", 1.01),
    ],
)
def test_comparison_tolerance_configuration_bounds(field, value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, jwt_secret="x" * 32, **{field: value})
