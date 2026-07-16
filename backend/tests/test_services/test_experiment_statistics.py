from __future__ import annotations

import csv
import io
import math
import tempfile
from pathlib import Path

import pytest

from paperlens.core.enums import ExperimentFileType
from paperlens.services.experiment_file_parser import parse_experiment_file
from paperlens.services.experiment_statistics import (
    StatisticsError,
    _WelfordAccumulator,
    _coerce_numeric,
    compute_summary_stats,
)


def _write_csv(rows: list[list[str]], delimiter: str = ",") -> str:
    fd, path = tempfile.mkstemp(suffix=".csv")
    with open(fd, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerows(rows)
    return path


def _write_xlsx(rows: list[list]) -> str:
    import openpyxl

    fd, path = tempfile.mkstemp(suffix=".xlsx")
    with open(fd, "wb") as _:
        pass
    wb = openpyxl.Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    wb.save(path)
    wb.close()
    return path


def _write_xls(rows: list[list]) -> str:
    import xlwt

    fd, path = tempfile.mkstemp(suffix=".xls")
    with open(fd, "wb") as _:
        pass
    wb = xlwt.Workbook()
    ws = wb.add_sheet("Sheet1")
    for row_index, row in enumerate(rows):
        for col_index, value in enumerate(row):
            if isinstance(value, (int, float)):
                ws.write(row_index, col_index, value)
            else:
                ws.write(row_index, col_index, str(value))
    wb.save(path)
    return path


class TestWelfordAccumulator:
    def test_single_value(self):
        acc = _WelfordAccumulator()
        acc.observe(5.0)
        assert acc.mean == 5.0
        assert acc.stddev is None
        assert acc.median == 5.0
        assert acc.min_val == 5.0
        assert acc.max_val == 5.0

    def test_two_values_stddev(self):
        acc = _WelfordAccumulator()
        acc.observe(1.0)
        acc.observe(3.0)
        assert acc.mean == 2.0
        expected_stddev = math.sqrt(2.0)
        assert abs(acc.stddev - expected_stddev) < 1e-10
        assert acc.median == 2.0

    def test_odd_median(self):
        acc = _WelfordAccumulator()
        for v in [3.0, 1.0, 2.0]:
            acc.observe(v)
        assert acc.median == 2.0

    def test_even_median(self):
        acc = _WelfordAccumulator()
        for v in [1.0, 2.0, 3.0, 4.0]:
            acc.observe(v)
        assert acc.median == 2.5

    def test_negative_values(self):
        acc = _WelfordAccumulator()
        for v in [-5.0, -3.0, -1.0]:
            acc.observe(v)
        assert acc.mean == -3.0
        assert acc.min_val == -5.0
        assert acc.max_val == -1.0
        assert acc.median == -3.0

    def test_zero_value(self):
        acc = _WelfordAccumulator()
        acc.observe(0.0)
        assert acc.mean == 0.0
        assert acc.median == 0.0

    def test_reject_nan(self):
        acc = _WelfordAccumulator()
        with pytest.raises(StatisticsError, match="non-finite"):
            acc.observe(float("nan"))

    def test_reject_infinity(self):
        acc = _WelfordAccumulator()
        with pytest.raises(StatisticsError, match="non-finite"):
            acc.observe(float("inf"))

    def test_reject_js_unsafe_int(self):
        with pytest.raises(StatisticsError, match="JS safe range"):
            _coerce_numeric(2**53, "integer")

    def test_empty_accumulator(self):
        acc = _WelfordAccumulator()
        assert acc.stddev is None
        assert acc.median is None
        assert acc.min_val is None
        assert acc.max_val is None


class TestCoerceNumeric:
    def test_integer_string(self):
        assert _coerce_numeric("42", "integer") == 42.0

    def test_float_string(self):
        assert _coerce_numeric("3.14", "float") == 3.14

    def test_negative_string(self):
        assert _coerce_numeric("-7", "integer") == -7.0

    def test_empty_string(self):
        assert _coerce_numeric("", "integer") is None

    def test_nan_string(self):
        with pytest.raises(StatisticsError, match="non-finite"):
            _coerce_numeric("nan", "float")

    def test_infinity_string(self):
        with pytest.raises(StatisticsError, match="non-finite"):
            _coerce_numeric("inf", "float")

    def test_non_numeric_string(self):
        with pytest.raises(StatisticsError, match="invalid numeric"):
            _coerce_numeric("abc", "float")

    def test_float_to_integer_reject(self):
        with pytest.raises(StatisticsError, match="fractional"):
            _coerce_numeric("3.14", "integer")

    def test_bool_rejected(self):
        with pytest.raises(StatisticsError, match="boolean"):
            _coerce_numeric(True, "integer")
        with pytest.raises(StatisticsError, match="boolean"):
            _coerce_numeric(False, "float")

    def test_none_returns_none(self):
        assert _coerce_numeric(None, "integer") is None

    def test_js_unsafe_int_string(self):
        with pytest.raises(StatisticsError, match="JS safe range"):
            _coerce_numeric(str(2**53), "integer")

    def test_js_safe_int_string(self):
        assert _coerce_numeric(str(2**53 - 1), "integer") == float(2**53 - 1)

    def test_python_int_safe(self):
        assert _coerce_numeric(42, "integer") == 42.0

    def test_python_int_unsafe(self):
        with pytest.raises(StatisticsError, match="JS safe range"):
            _coerce_numeric(2**53, "integer")

    def test_python_float_finite(self):
        assert _coerce_numeric(3.14, "float") == 3.14

    def test_python_float_nan(self):
        with pytest.raises(StatisticsError, match="non-finite"):
            _coerce_numeric(float("nan"), "float")


class TestComputeSummaryStatsCSV:
    def test_basic_integer_float(self):
        path = _write_csv([
            ["accuracy", "loss"],
            ["0.9", "0.1"],
            ["0.88", "0.2"],
            ["0.92", "0.15"],
        ])
        try:
            parse_result = parse_experiment_file(path, ExperimentFileType.CSV)
            result = compute_summary_stats(
                path, ExperimentFileType.CSV,
                parse_result.row_count, parse_result.column_count,
                parse_result.columns_info,
            )
            assert result["version"] == 1
            assert result["row_count"] == 3
            assert result["column_count"] == 2
            assert len(result["columns"]) == 2

            acc_col = result["columns"][0]
            assert acc_col["name"] == "accuracy"
            assert acc_col["dtype"] == "float"
            assert acc_col["count"] == 3
            assert acc_col["null_count"] == 0
            assert acc_col["stats"] is not None
            assert abs(acc_col["stats"]["mean"] - 0.9) < 1e-10
            assert acc_col["stats"]["min"] == 0.88
            assert acc_col["stats"]["max"] == 0.92
            assert acc_col["stats"]["median"] == 0.9

            loss_col = result["columns"][1]
            assert loss_col["name"] == "loss"
            assert loss_col["stats"] is not None
        finally:
            Path(path).unlink()

    def test_with_nulls(self):
        path = _write_csv([
            ["value", "label"],
            ["1.5", "a"],
            ["", "b"],
            ["3.5", ""],
        ])
        try:
            parse_result = parse_experiment_file(path, ExperimentFileType.CSV)
            result = compute_summary_stats(
                path, ExperimentFileType.CSV,
                parse_result.row_count, parse_result.column_count,
                parse_result.columns_info,
            )
            value_col = result["columns"][0]
            assert value_col["name"] == "value"
            assert value_col["count"] == 2
            assert value_col["null_count"] == 1
            assert value_col["stats"] is not None
            assert abs(value_col["stats"]["mean"] - 2.5) < 1e-10
            assert value_col["stats"]["median"] == 2.5

            label_col = result["columns"][1]
            assert label_col["stats"] is None
        finally:
            Path(path).unlink()

    def test_string_only_column(self):
        path = _write_csv([
            ["model", "accuracy"],
            ["bert", "0.9"],
            ["gpt", "0.88"],
        ])
        try:
            parse_result = parse_experiment_file(path, ExperimentFileType.CSV)
            result = compute_summary_stats(
                path, ExperimentFileType.CSV,
                parse_result.row_count, parse_result.column_count,
                parse_result.columns_info,
            )
            model_col = result["columns"][0]
            assert model_col["dtype"] == "string"
            assert model_col["stats"] is None
            assert model_col["count"] == 2
        finally:
            Path(path).unlink()

    def test_empty_column(self):
        path = _write_csv([
            ["value", "empty_col"],
            ["1.0", ""],
            ["2.0", ""],
        ])
        try:
            parse_result = parse_experiment_file(path, ExperimentFileType.CSV)
            result = compute_summary_stats(
                path, ExperimentFileType.CSV,
                parse_result.row_count, parse_result.column_count,
                parse_result.columns_info,
            )
            empty_col = result["columns"][1]
            assert empty_col["dtype"] == "empty"
            assert empty_col["count"] == 0
            assert empty_col["null_count"] == 2
            assert empty_col["stats"] is None
        finally:
            Path(path).unlink()

    def test_deterministic(self):
        path = _write_csv([
            ["x"],
            ["1.0"],
            ["2.0"],
            ["3.0"],
        ])
        try:
            parse_result = parse_experiment_file(path, ExperimentFileType.CSV)
            r1 = compute_summary_stats(
                path, ExperimentFileType.CSV,
                parse_result.row_count, parse_result.column_count,
                parse_result.columns_info,
            )
            r2 = compute_summary_stats(
                path, ExperimentFileType.CSV,
                parse_result.row_count, parse_result.column_count,
                parse_result.columns_info,
            )
            assert r1 == r2
        finally:
            Path(path).unlink()

    def test_single_value_stddev_null(self):
        path = _write_csv([
            ["x"],
            ["5.0"],
        ])
        try:
            parse_result = parse_experiment_file(path, ExperimentFileType.CSV)
            result = compute_summary_stats(
                path, ExperimentFileType.CSV,
                parse_result.row_count, parse_result.column_count,
                parse_result.columns_info,
            )
            col = result["columns"][0]
            assert col["stats"]["stddev"] is None
        finally:
            Path(path).unlink()

    def test_negative_values(self):
        path = _write_csv([
            ["temp"],
            ["-3.5"],
            ["0.0"],
            ["2.5"],
        ])
        try:
            parse_result = parse_experiment_file(path, ExperimentFileType.CSV)
            result = compute_summary_stats(
                path, ExperimentFileType.CSV,
                parse_result.row_count, parse_result.column_count,
                parse_result.columns_info,
            )
            col = result["columns"][0]
            assert col["stats"]["min"] == -3.5
            assert col["stats"]["max"] == 2.5
            assert abs(col["stats"]["mean"] - (-1.0 / 3.0)) < 1e-10
        finally:
            Path(path).unlink()

    def test_integer_column(self):
        path = _write_csv([
            ["count"],
            ["10"],
            ["20"],
            ["30"],
        ])
        try:
            parse_result = parse_experiment_file(path, ExperimentFileType.CSV)
            result = compute_summary_stats(
                path, ExperimentFileType.CSV,
                parse_result.row_count, parse_result.column_count,
                parse_result.columns_info,
            )
            col = result["columns"][0]
            assert col["dtype"] == "integer"
            assert col["stats"]["mean"] == 20.0
            assert col["stats"]["median"] == 20.0
        finally:
            Path(path).unlink()

    def test_row_count_mismatch_raises(self):
        path = _write_csv([
            ["x"],
            ["1.0"],
        ])
        try:
            parse_result = parse_experiment_file(path, ExperimentFileType.CSV)
            with pytest.raises(StatisticsError, match="row count mismatch"):
                compute_summary_stats(
                    path, ExperimentFileType.CSV,
                    999, parse_result.column_count,
                    parse_result.columns_info,
                )
        finally:
            Path(path).unlink()

    def test_streaming_does_not_use_path_read_bytes(self, monkeypatch):
        path = _write_csv([["x"], ["1.0"], ["2.0"]])
        try:
            parse_result = parse_experiment_file(path, ExperimentFileType.CSV)

            def _forbidden_read_bytes(_self):
                raise AssertionError("statistics must stream rows")

            monkeypatch.setattr(Path, "read_bytes", _forbidden_read_bytes)
            result = compute_summary_stats(
                path,
                ExperimentFileType.CSV,
                parse_result.row_count,
                parse_result.column_count,
                parse_result.columns_info,
            )
            assert result["columns"][0]["count"] == 2
        finally:
            Path(path).unlink()

    def test_rejects_columns_info_null_count_mismatch(self):
        path = _write_csv([["x"], ["1.0"], [""]])
        try:
            parse_result = parse_experiment_file(path, ExperimentFileType.CSV)
            columns_info = dict(parse_result.columns_info)
            columns_info["columns"] = [dict(parse_result.columns_info["columns"][0])]
            columns_info["columns"][0]["null_count"] = 0
            columns_info["columns"][0]["nullable"] = False
            with pytest.raises(StatisticsError, match="null_count mismatch"):
                compute_summary_stats(
                    path,
                    ExperimentFileType.CSV,
                    parse_result.row_count,
                    parse_result.column_count,
                    columns_info,
                )
        finally:
            Path(path).unlink()


class TestComputeSummaryStatsXLSX:
    def test_basic_xlsx(self):
        path = _write_xlsx([
            ["score", "name"],
            [0.95, "model_a"],
            [0.87, "model_b"],
        ])
        try:
            parse_result = parse_experiment_file(path, ExperimentFileType.XLSX)
            result = compute_summary_stats(
                path, ExperimentFileType.XLSX,
                parse_result.row_count, parse_result.column_count,
                parse_result.columns_info,
            )
            score_col = result["columns"][0]
            assert score_col["dtype"] == "float"
            assert score_col["count"] == 2
            assert score_col["stats"] is not None
            assert abs(score_col["stats"]["mean"] - 0.91) < 1e-10
        finally:
            Path(path).unlink()

    def test_xlsx_with_nulls(self):
        path = _write_xlsx([
            ["value"],
            [1.0],
            [None],
            [3.0],
        ])
        try:
            parse_result = parse_experiment_file(path, ExperimentFileType.XLSX)
            result = compute_summary_stats(
                path, ExperimentFileType.XLSX,
                parse_result.row_count, parse_result.column_count,
                parse_result.columns_info,
            )
            col = result["columns"][0]
            assert col["count"] == 2
            assert col["null_count"] == 1
        finally:
            Path(path).unlink()


class TestComputeSummaryStatsXLS:
    def test_basic_xls(self):
        path = _write_xls([
            ["score", "name"],
            [0.95, "model_a"],
            [0.87, "model_b"],
        ])
        try:
            parse_result = parse_experiment_file(path, ExperimentFileType.XLS)
            result = compute_summary_stats(
                path, ExperimentFileType.XLS,
                parse_result.row_count, parse_result.column_count,
                parse_result.columns_info,
            )
            score_col = result["columns"][0]
            if score_col["dtype"] in ("integer", "float"):
                assert score_col["stats"] is not None
                assert abs(score_col["stats"]["mean"] - 0.91) < 1e-10
            else:
                assert score_col["stats"] is None
        finally:
            Path(path).unlink()


class TestNumericSafety:
    def test_numeric_metadata_rejects_nan_text(self):
        path = _write_csv([["value"], ["1.0"], ["nan"]])
        columns_info = {
            "version": 1,
            "encoding": "utf-8",
            "delimiter": ",",
            "sheet_name": None,
            "columns": [
                {
                    "name": "value",
                    "dtype": "float",
                    "nullable": False,
                    "null_count": 0,
                }
            ],
        }
        try:
            with pytest.raises(StatisticsError, match="non-finite"):
                compute_summary_stats(path, ExperimentFileType.CSV, 2, 1, columns_info)
        finally:
            Path(path).unlink()

    def test_rejects_js_unsafe_integer_file_value(self):
        path = _write_csv([["value"], [str(2**53)]])
        try:
            parse_result = parse_experiment_file(path, ExperimentFileType.CSV)
            with pytest.raises(StatisticsError, match="JS safe range"):
                compute_summary_stats(
                    path,
                    ExperimentFileType.CSV,
                    parse_result.row_count,
                    parse_result.column_count,
                    parse_result.columns_info,
                )
        finally:
            Path(path).unlink()

    def test_nan_text_in_csv(self):
        path = _write_csv([
            ["value"],
            ["1.0"],
            ["nan"],
            ["2.0"],
        ])
        try:
            parse_result = parse_experiment_file(path, ExperimentFileType.CSV)
            result = compute_summary_stats(
                path, ExperimentFileType.CSV,
                parse_result.row_count, parse_result.column_count,
                parse_result.columns_info,
            )
            col = result["columns"][0]
            assert col["dtype"] == "string"
            assert col["stats"] is None
        finally:
            Path(path).unlink()

    def test_infinity_text_in_csv(self):
        path = _write_csv([
            ["value"],
            ["1.0"],
            ["inf"],
            ["2.0"],
        ])
        try:
            parse_result = parse_experiment_file(path, ExperimentFileType.CSV)
            result = compute_summary_stats(
                path, ExperimentFileType.CSV,
                parse_result.row_count, parse_result.column_count,
                parse_result.columns_info,
            )
            col = result["columns"][0]
            assert col["dtype"] == "string"
            assert col["stats"] is None
        finally:
            Path(path).unlink()

    def test_boolean_not_numeric(self):
        path = _write_csv([
            ["flag"],
            ["true"],
            ["false"],
        ])
        try:
            parse_result = parse_experiment_file(path, ExperimentFileType.CSV)
            result = compute_summary_stats(
                path, ExperimentFileType.CSV,
                parse_result.row_count, parse_result.column_count,
                parse_result.columns_info,
            )
            col = result["columns"][0]
            assert col["dtype"] == "boolean"
            assert col["stats"] is None
        finally:
            Path(path).unlink()

    def test_mixed_numeric_string_column(self):
        path = _write_csv([
            ["mixed"],
            ["1.0"],
            ["abc"],
            ["2.0"],
        ])
        try:
            parse_result = parse_experiment_file(path, ExperimentFileType.CSV)
            result = compute_summary_stats(
                path, ExperimentFileType.CSV,
                parse_result.row_count, parse_result.column_count,
                parse_result.columns_info,
            )
            col = result["columns"][0]
            assert col["dtype"] == "string"
            assert col["stats"] is None
        finally:
            Path(path).unlink()


class TestColumnOrder:
    def test_columns_preserve_original_order(self):
        path = _write_csv([
            ["z_col", "a_col", "m_col"],
            ["1.0", "2.0", "3.0"],
        ])
        try:
            parse_result = parse_experiment_file(path, ExperimentFileType.CSV)
            result = compute_summary_stats(
                path, ExperimentFileType.CSV,
                parse_result.row_count, parse_result.column_count,
                parse_result.columns_info,
            )
            names = [c["name"] for c in result["columns"]]
            assert names == ["z_col", "a_col", "m_col"]
        finally:
            Path(path).unlink()
