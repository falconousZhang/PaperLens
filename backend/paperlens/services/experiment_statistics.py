from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from paperlens.core.enums import ExperimentFileType
from paperlens.services.experiment_file_parser import ParseError, iter_experiment_rows

_JS_SAFE_INT_MAX = 2**53 - 1
_JS_SAFE_INT_MIN = -(2**53 - 1)
_SUMMARY_STATS_VERSION = 1
_NUMERIC_DTYPES = {"integer", "float"}
_COLUMN_DTYPES = _NUMERIC_DTYPES | {"boolean", "datetime", "string", "empty"}


class StatisticsError(Exception):
    def __init__(self, message: str, kind: str = "computation"):
        super().__init__(message)
        self.kind = kind


@dataclass
class _WelfordAccumulator:
    n: int = 0
    mean: float = 0.0
    m2: float = 0.0
    minimum: float | None = None
    maximum: float | None = None
    _values: list[float] = field(default_factory=list)

    def observe(self, value: float) -> None:
        if not math.isfinite(value):
            raise StatisticsError("non-finite numeric value", "numeric_safety")
        self.n += 1
        delta = value - self.mean
        self.mean += delta / self.n
        delta2 = value - self.mean
        self.m2 += delta * delta2
        if not math.isfinite(self.mean) or not math.isfinite(self.m2):
            raise StatisticsError("numeric accumulation overflow", "numeric_safety")
        self.minimum = value if self.minimum is None else min(self.minimum, value)
        self.maximum = value if self.maximum is None else max(self.maximum, value)
        self._values.append(value)

    @property
    def stddev(self) -> float | None:
        if self.n < 2:
            return None
        variance = self.m2 / (self.n - 1)
        if variance < 0 or not math.isfinite(variance):
            raise StatisticsError("invalid variance", "numeric_safety")
        result = math.sqrt(variance)
        if not math.isfinite(result):
            raise StatisticsError("stddev overflow", "numeric_safety")
        return result

    def take_median(self) -> float | None:
        if self.n == 0:
            return None
        self._values.sort()
        mid = self.n // 2
        if self.n % 2 == 1:
            result = self._values[mid]
        else:
            result = self._values[mid - 1] / 2.0 + self._values[mid] / 2.0
        self._values.clear()
        if not math.isfinite(result):
            raise StatisticsError("median overflow", "numeric_safety")
        return result

    @property
    def median(self) -> float | None:
        if self.n == 0:
            return None
        ordered = sorted(self._values)
        mid = self.n // 2
        if self.n % 2 == 1:
            return ordered[mid]
        result = ordered[mid - 1] / 2.0 + ordered[mid] / 2.0
        if not math.isfinite(result):
            raise StatisticsError("median overflow", "numeric_safety")
        return result

    @property
    def min_val(self) -> float | None:
        return self.minimum

    @property
    def max_val(self) -> float | None:
        return self.maximum


def _is_numeric_dtype(dtype: str) -> bool:
    return dtype in _NUMERIC_DTYPES


def _reject_unsafe_integral(value: float) -> None:
    if value.is_integer() and (value > _JS_SAFE_INT_MAX or value < _JS_SAFE_INT_MIN):
        raise StatisticsError("integer exceeds JS safe range", "numeric_safety")


def _coerce_numeric(value: Any, dtype: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise StatisticsError("boolean in numeric column", "numeric_safety")
    if isinstance(value, int):
        if value > _JS_SAFE_INT_MAX or value < _JS_SAFE_INT_MIN:
            raise StatisticsError("integer exceeds JS safe range", "numeric_safety")
        return float(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise StatisticsError("non-finite numeric value", "numeric_safety")
        if dtype == "integer" and not value.is_integer():
            raise StatisticsError("fractional value in integer column", "numeric_safety")
        _reject_unsafe_integral(value)
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            parsed = float(stripped)
        except ValueError as exc:
            raise StatisticsError("invalid numeric value", "numeric_safety") from exc
        if not math.isfinite(parsed):
            raise StatisticsError("non-finite numeric value", "numeric_safety")
        if dtype == "integer" and not parsed.is_integer():
            raise StatisticsError("fractional value in integer column", "numeric_safety")
        _reject_unsafe_integral(parsed)
        return parsed
    raise StatisticsError("unsupported numeric value", "numeric_safety")


def _validated_columns(columns_info: dict, column_count: int, row_count: int) -> list[dict]:
    if not isinstance(columns_info, dict):
        raise StatisticsError("columns_info is invalid", "integrity")
    if set(columns_info) != {"version", "encoding", "delimiter", "sheet_name", "columns"}:
        raise StatisticsError("columns_info shape mismatch", "integrity")
    if columns_info.get("version") != 1:
        raise StatisticsError("columns_info version mismatch", "integrity")
    columns = columns_info.get("columns")
    if not isinstance(columns, list) or len(columns) != column_count:
        raise StatisticsError("columns_info mismatch", "integrity")
    validated = []
    for column in columns:
        if not isinstance(column, dict) or set(column) != {"name", "dtype", "nullable", "null_count"}:
            raise StatisticsError("column metadata shape mismatch", "integrity")
        if not isinstance(column.get("name"), str) or not column["name"]:
            raise StatisticsError("column name metadata mismatch", "integrity")
        if column.get("dtype") not in _COLUMN_DTYPES:
            raise StatisticsError("column dtype metadata mismatch", "integrity")
        if not isinstance(column.get("nullable"), bool):
            raise StatisticsError("column nullable metadata mismatch", "integrity")
        null_count = column.get("null_count")
        if not isinstance(null_count, int) or isinstance(null_count, bool) or not 0 <= null_count <= row_count:
            raise StatisticsError("column null_count metadata mismatch", "integrity")
        if column["nullable"] != (null_count > 0):
            raise StatisticsError("column nullable metadata mismatch", "integrity")
        validated.append(column)
    return validated


def compute_summary_stats(
    source_path: str | Path,
    file_type: ExperimentFileType,
    row_count: int,
    column_count: int,
    columns_info: dict,
) -> dict:
    if not isinstance(row_count, int) or isinstance(row_count, bool) or row_count < 1:
        raise StatisticsError("row_count is invalid", "integrity")
    if not isinstance(column_count, int) or isinstance(column_count, bool) or column_count < 1:
        raise StatisticsError("column_count is invalid", "integrity")
    columns = _validated_columns(columns_info, column_count, row_count)
    accumulators = [
        _WelfordAccumulator() if _is_numeric_dtype(column["dtype"]) else None
        for column in columns
    ]
    null_counts = [0] * column_count
    rows_seen = 0

    try:
        rows = iter_experiment_rows(source_path, file_type, columns_info)
        for row in rows:
            rows_seen += 1
            if rows_seen > row_count or len(row) != column_count:
                raise StatisticsError("row structure mismatch", "integrity")
            for index, raw_value in enumerate(row):
                if raw_value is None:
                    null_counts[index] += 1
                    continue
                dtype = columns[index]["dtype"]
                if dtype == "empty":
                    raise StatisticsError("empty column contains a value", "integrity")
                if _is_numeric_dtype(dtype):
                    numeric = _coerce_numeric(raw_value, dtype)
                    if numeric is None:
                        null_counts[index] += 1
                    else:
                        accumulators[index].observe(numeric)
    except ParseError as exc:
        raise StatisticsError("row streaming failed", "integrity") from exc

    if rows_seen != row_count:
        raise StatisticsError("row count mismatch", "integrity")

    result_columns: list[dict[str, Any]] = []
    for index, column in enumerate(columns):
        actual_null = null_counts[index]
        if actual_null != column["null_count"]:
            raise StatisticsError("column null_count mismatch", "integrity")
        count = row_count - actual_null
        dtype = column["dtype"]
        accumulator = accumulators[index]
        stats = None
        if _is_numeric_dtype(dtype):
            if accumulator is None or accumulator.n != count or count == 0:
                raise StatisticsError("numeric column count mismatch", "integrity")
            median = accumulator.take_median()
            if accumulator.minimum is None or accumulator.maximum is None or median is None:
                raise StatisticsError("numeric statistics are incomplete", "integrity")
            stats = {
                "mean": accumulator.mean,
                "stddev": accumulator.stddev,
                "min": accumulator.minimum,
                "max": accumulator.maximum,
                "median": median,
            }
        result_columns.append(
            {
                "name": column["name"],
                "dtype": dtype,
                "count": count,
                "null_count": actual_null,
                "stats": stats,
            }
        )

    return {
        "version": _SUMMARY_STATS_VERSION,
        "row_count": row_count,
        "column_count": column_count,
        "columns": result_columns,
    }
