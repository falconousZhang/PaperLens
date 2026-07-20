import hashlib
import math
import datetime
from types import SimpleNamespace

import pytest

from paperlens.services.export_service import (
    _esc,
    _esc_cell,
    _fmt_num,
    _ZH_LABELS,
    _EN_LABELS,
    _REASON_LABELS,
    _CHECKPOINT_LABELS,
    _VERDICT_LABELS,
    compute_content_hash,
    compute_source_hash,
    generate_markdown,
)


def test_learning_report_without_review_contains_learning_materials():
    paper = _make_paper()
    explanation = SimpleNamespace(
        id="learning-1",
        mode="EXPLAIN",
        page_number=3,
        selection_text="federated learning",
        answer="这是联邦学习的通俗解释。",
        key_points=["数据不离开本地"],
        terms=[{"term": "FL", "definition": "联邦学习"}],
        _export_page_number=3,
    )
    highlight = SimpleNamespace(
        id="highlight-1",
        page_number=2,
        quoted_text="important finding",
    )
    note = SimpleNamespace(
        id="note-1",
        page_number=None,
        content="这里需要结合实验结果复习。",
        _export_page_number=2,
        _export_highlight=highlight,
    )

    text = generate_markdown(
        paper,
        None,
        [],
        "zh",
        False,
        False,
        learning_explanations=[explanation],
        highlights=[highlight],
        notes=[note],
    ).decode("utf-8")

    assert "# 论文学习报告" in text
    assert "**批判性阅读**: 尚未生成（不影响本报告）" in text
    assert "### 第 3 页 · 选中文字解释" in text
    assert "federated learning" in text
    assert "这是联邦学习的通俗解释。" in text
    assert "## 高亮摘录" in text
    assert "important finding" in text
    assert "## 学习笔记" in text
    assert "这里需要结合实验结果复习。" in text
    assert "## 审阅详情" not in text


def _make_paper(**overrides):
    defaults = dict(
        id="paper-1",
        title="Test Paper Title",
        filename="test_paper.pdf",
        storage_key="papers/paper-1/source.pdf",
        file_size=1000,
        file_hash="a" * 64,
        page_count=10,
        status="PARSED",
        user_id="user-1",
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_review_task(**overrides):
    defaults = dict(
        id="task-review-1",
        paper_id="paper-1",
        task_type="REVIEW",
        status="SUCCEEDED",
        user_id="user-1",
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_review_result(dimension="SOUNDNESS", rating=4, summary="Good work", overall_verdict=None, findings=None, **overrides):
    defaults = dict(
        id=f"rr-{dimension}",
        task_id="task-review-1",
        paper_id="paper-1",
        dimension=dimension,
        rating=rating,
        summary=summary,
        overall_verdict=overall_verdict,
        findings=findings or [],
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_finding(finding_type="STRENGTH", content="Strong method", sequence=0, evidences=None, **overrides):
    defaults = dict(
        id=f"f-{finding_type}-{sequence}",
        review_id="rr-SOUNDNESS",
        finding_type=finding_type,
        content=content,
        confidence=0.9,
        verification_status="PENDING",
        sequence=sequence,
        evidences=evidences or [],
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_evidence(eid="ev-1", page_number=1, quoted_text="Quote text"):
    return SimpleNamespace(id=eid, page_number=page_number, quoted_text=quoted_text)


def _make_metric_task(**overrides):
    defaults = dict(
        id="task-metric-1",
        paper_id="paper-1",
        task_type="METRIC_EXTRACTION",
        status="SUCCEEDED",
        user_id="user-1",
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_metric_record(model_name="BERT", dataset_name="SQuAD", metric_name="Accuracy", metric_value=92.5, checkpoint_type="BEST", **overrides):
    defaults = dict(
        id=f"mr-{model_name}-{metric_name}",
        paper_id="paper-1",
        task_id="task-metric-1",
        user_id="user-1",
        model_name=model_name,
        dataset_name=dataset_name,
        metric_name=metric_name,
        metric_value=metric_value,
        checkpoint_type=checkpoint_type,
        checkpoint_source=None,
        evidence_id=None,
        raw_text=None,
        table_id=None,
        row_index=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_experiment_file(filename="exp.csv", row_count=100, column_count=5, **overrides):
    defaults = dict(
        id="ef-1",
        paper_id="paper-1",
        user_id="user-1",
        filename=filename,
        file_type="CSV",
        storage_key="experiment-files/ef-1/data.csv",
        file_size=5000,
        file_hash="b" * 64,
        row_count=row_count,
        column_count=column_count,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_experiment_result(summary_stats=None, metric_comparisons=None, **overrides):
    defaults = dict(
        id="er-1",
        file_id="ef-1",
        task_id="task-exp-1",
        summary_stats=summary_stats or {},
        column_analysis=None,
        metric_comparisons=metric_comparisons,
        file=_make_experiment_file(),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestEscaping:
    def test_esc_none(self):
        assert _esc(None) == ""

    def test_esc_html_chars(self):
        assert _esc("<script>alert('xss')</script>") == "&lt;script&gt;alert('xss')&lt;/script&gt;"

    def test_esc_amp(self):
        assert _esc("a & b") == "a &amp; b"

    def test_esc_crlf_normalized(self):
        assert _esc("a\r\nb\rc\n") == "a\nb\nc\n"

    def test_esc_cell_pipe(self):
        assert _esc_cell("a | b") == "a \\| b"

    def test_esc_cell_newlines(self):
        assert _esc_cell("a\nb\r\nc\rd") == "a b c d"

    def test_esc_cell_pipe_and_newline(self):
        assert _esc_cell("a|b\nc") == "a\\|b c"

    def test_esc_cell_none(self):
        assert _esc_cell(None) == ""

    def test_esc_cell_html(self):
        assert _esc_cell("<b>bold</b>") == "&lt;b&gt;bold&lt;/b&gt;"


class TestFmtNum:
    def test_none(self):
        assert _fmt_num(None) == ""

    def test_int(self):
        assert _fmt_num(42) == "42"

    def test_float(self):
        assert _fmt_num(3.14) == "3.14"

    def test_inf(self):
        assert _fmt_num(float("inf")) == ""

    def test_neg_inf(self):
        assert _fmt_num(float("-inf")) == ""

    def test_nan(self):
        assert _fmt_num(float("nan")) == ""

    def test_zero(self):
        assert _fmt_num(0) == "0"

    def test_negative(self):
        assert _fmt_num(-1.5) == "-1.5"


class TestZhTemplate:
    def test_basic_zh(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result(dimension="SOUNDNESS", rating=4, summary="Good")
        content = generate_markdown(paper, task, [rr], "zh", False, False)
        text = content.decode("utf-8")
        assert "# 论文学习报告" in text
        assert "## 论文信息" in text
        assert "## 学习概览" in text
        assert "## 审阅详情（批判性阅读）" in text
        assert "**论文标题**: Test Paper Title" in text
        assert "**文件名**: test_paper.pdf" in text
        assert "**页数**: 10" in text
        assert "### SOUNDNESS" in text
        assert "**评分**: 4/5" in text
        assert "**摘要**: Good" in text

    def test_zh_verdict(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result(dimension="OVERALL", rating=5, overall_verdict="ACCEPT")
        content = generate_markdown(paper, task, [rr], "zh", False, False)
        text = content.decode("utf-8")
        assert "**结论**: 接受" in text

    def test_zh_findings(self):
        paper = _make_paper()
        task = _make_review_task()
        f1 = _make_finding(finding_type="STRENGTH", content="Strong method", sequence=0)
        f2 = _make_finding(finding_type="WEAKNESS", content="Weak eval", sequence=1)
        f3 = _make_finding(finding_type="SUGGESTION", content="Add baseline", sequence=2)
        rr = _make_review_result(dimension="SOUNDNESS", findings=[f1, f2, f3])
        content = generate_markdown(paper, task, [rr], "zh", False, False)
        text = content.decode("utf-8")
        assert "**优势**:" in text
        assert "- Strong method" in text
        assert "**不足**:" in text
        assert "- Weak eval" in text
        assert "**建议**:" in text
        assert "- Add baseline" in text


class TestEnTemplate:
    def test_basic_en(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result(dimension="SOUNDNESS", rating=3, summary="Some issues")
        content = generate_markdown(paper, task, [rr], "en", False, False)
        text = content.decode("utf-8")
        assert "# Paper Learning Report" in text
        assert "## Paper Information" in text
        assert "## Learning Overview" in text
        assert "## Review Details (Critical Reading)" in text
        assert "**Title**: Test Paper Title" in text
        assert "**Filename**: test_paper.pdf" in text
        assert "**Pages**: 10" in text
        assert "**Rating**: 3/5" in text
        assert "**Summary**: Some issues" in text

    def test_en_verdict(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result(dimension="OVERALL", rating=2, overall_verdict="WEAK_REJECT")
        content = generate_markdown(paper, task, [rr], "en", False, False)
        text = content.decode("utf-8")
        assert "**Verdict**: Weak Reject" in text


class TestDimensionOrder:
    def test_dimensions_sorted(self):
        paper = _make_paper()
        task = _make_review_task()
        rr1 = _make_review_result(dimension="OVERALL", rating=4, id="rr-overall")
        rr2 = _make_review_result(dimension="SOUNDNESS", rating=3, id="rr-sound")
        rr3 = _make_review_result(dimension="NOVELTY", rating=5, id="rr-novel")
        content = generate_markdown(paper, task, [rr1, rr2, rr3], "zh", False, False)
        text = content.decode("utf-8")
        pos_sound = text.index("### SOUNDNESS")
        pos_novel = text.index("### NOVELTY")
        pos_overall = text.index("### OVERALL")
        assert pos_sound < pos_novel < pos_overall


class TestMetricsSection:
    def test_zh_metrics_table(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result()
        metric_task = _make_metric_task()
        m1 = _make_metric_record(model_name="BERT", metric_name="Accuracy", metric_value=92.5, checkpoint_type="BEST")
        m2 = _make_metric_record(model_name="RoBERTa", metric_name="F1", metric_value=88.3, checkpoint_type="FINAL")
        content = generate_markdown(paper, task, [rr], "zh", True, False, metric_task=metric_task, metrics=[m1, m2])
        text = content.decode("utf-8")
        assert "## 指标数据" in text
        assert "| 模型 | 数据集 | 指标名 | 指标值 | 检查点 |" in text
        assert "| BERT | SQuAD | Accuracy | 92.5 | 最佳 |" in text
        assert "| RoBERTa | SQuAD | F1 | 88.3 | 最终 |" in text

    def test_en_metrics_table(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result()
        metric_task = _make_metric_task()
        m1 = _make_metric_record(checkpoint_type="BEST")
        content = generate_markdown(paper, task, [rr], "en", True, False, metric_task=metric_task, metrics=[m1])
        text = content.decode("utf-8")
        assert "## Metrics Data" in text
        assert "| Model | Dataset | Metric | Value | Checkpoint |" in text
        assert "| Best |" in text

    def test_no_metrics_placeholder(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result()
        content = generate_markdown(paper, task, [rr], "zh", True, False, metric_task=None, metrics=None)
        text = content.decode("utf-8")
        assert "暂无指标数据" in text

    def test_metrics_not_included(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result()
        content = generate_markdown(paper, task, [rr], "zh", False, False)
        text = content.decode("utf-8")
        assert "指标数据" not in text


class TestExperimentSection:
    def test_zh_experiment_with_stats(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result()
        summary_stats = {
            "columns": [
                {
                    "name": "accuracy",
                    "dtype": "float64",
                    "count": 100,
                    "null_count": 0,
                    "stats": {"mean": 0.85, "stddev": 0.05, "min": 0.7, "max": 0.99, "median": 0.87},
                },
            ]
        }
        er = _make_experiment_result(summary_stats=summary_stats)
        content = generate_markdown(paper, task, [rr], "zh", False, True, experiment_results=[er])
        text = content.decode("utf-8")
        assert "## 实验分析数据" in text
        assert "### exp.csv" in text
        assert "**行数**: 100" in text
        assert "**列数**: 5" in text
        assert "**统计摘要**:" in text
        assert "| 列名 | 类型 | 有效值 | 空值 | 均值 | 标准差 | 最小值 | 最大值 | 中位数 |" in text
        assert "| accuracy | float64 | 100 | 0 | 0.85 | 0.05 | 0.7 | 0.99 | 0.87 |" in text

    def test_en_experiment_with_comparisons(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result()
        comparisons = [
            {
                "metric_name": "Accuracy",
                "checkpoint_type": "BEST",
                "paper_value": 92.5,
                "experiment_value": 91.8,
                "diff": 0.7,
                "status": "MATCH",
                "reason": None,
            },
        ]
        er = _make_experiment_result(summary_stats={}, metric_comparisons=comparisons)
        content = generate_markdown(paper, task, [rr], "en", False, True, experiment_results=[er])
        text = content.decode("utf-8")
        assert "## Experiment Analysis Data" in text
        assert "**Cross Validation**:" in text
        assert "| Metric | Checkpoint | Paper Value | Experiment Value | Diff | Status | Reason |" in text
        assert "| Accuracy | Best | 92.5 | 91.8 | 0.7 | MATCH |  |" in text

    def test_no_experiment_placeholder(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result()
        content = generate_markdown(paper, task, [rr], "zh", False, True, experiment_results=None)
        text = content.decode("utf-8")
        assert "暂无实验分析数据" in text

    def test_experiment_not_included(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result()
        content = generate_markdown(paper, task, [rr], "zh", False, False)
        text = content.decode("utf-8")
        assert "实验分析" not in text


class TestComparisonReasons:
    @pytest.mark.parametrize("reason_key", list(_REASON_LABELS.keys()))
    def test_all_reason_labels_zh(self, reason_key):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result()
        comparisons = [
            {
                "metric_name": "M1",
                "checkpoint_type": "BEST",
                "paper_value": 1.0,
                "experiment_value": 1.0,
                "diff": 0.0,
                "status": "MISMATCH",
                "reason": reason_key,
            },
        ]
        er = _make_experiment_result(summary_stats={}, metric_comparisons=comparisons)
        content = generate_markdown(paper, task, [rr], "zh", False, True, experiment_results=[er])
        text = content.decode("utf-8")
        assert _REASON_LABELS[reason_key]["zh"] in text

    @pytest.mark.parametrize("reason_key", list(_REASON_LABELS.keys()))
    def test_all_reason_labels_en(self, reason_key):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result()
        comparisons = [
            {
                "metric_name": "M1",
                "checkpoint_type": "BEST",
                "paper_value": 1.0,
                "experiment_value": 1.0,
                "diff": 0.0,
                "status": "MISMATCH",
                "reason": reason_key,
            },
        ]
        er = _make_experiment_result(summary_stats={}, metric_comparisons=comparisons)
        content = generate_markdown(paper, task, [rr], "en", False, True, experiment_results=[er])
        text = content.decode("utf-8")
        assert _REASON_LABELS[reason_key]["en"] in text


class TestEmptyOptionalSections:
    def test_no_page_count(self):
        paper = _make_paper(page_count=None)
        task = _make_review_task()
        rr = _make_review_result()
        content = generate_markdown(paper, task, [rr], "zh", False, False)
        text = content.decode("utf-8")
        assert "页数" not in text

    def test_no_rating(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result(rating=None)
        content = generate_markdown(paper, task, [rr], "zh", False, False)
        text = content.decode("utf-8")
        assert "评分" not in text

    def test_no_summary(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result(summary=None)
        content = generate_markdown(paper, task, [rr], "zh", False, False)
        text = content.decode("utf-8")
        assert "摘要" not in text

    def test_no_verdict_non_overall(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result(dimension="SOUNDNESS", overall_verdict=None)
        content = generate_markdown(paper, task, [rr], "zh", False, False)
        text = content.decode("utf-8")
        assert "结论" not in text

    def test_no_findings(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result(findings=[])
        content = generate_markdown(paper, task, [rr], "zh", False, False)
        text = content.decode("utf-8")
        assert "优势" not in text
        assert "不足" not in text
        assert "建议" not in text

    def test_experiment_no_file(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result()
        er = _make_experiment_result(file=None, summary_stats={})
        content = generate_markdown(paper, task, [rr], "zh", False, True, experiment_results=[er])
        text = content.decode("utf-8")
        assert "### exp.csv" not in text

    def test_experiment_empty_stats(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result()
        er = _make_experiment_result(summary_stats={})
        content = generate_markdown(paper, task, [rr], "zh", False, True, experiment_results=[er])
        text = content.decode("utf-8")
        assert "统计摘要" not in text

    def test_experiment_no_comparisons(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result()
        er = _make_experiment_result(summary_stats={}, metric_comparisons=None)
        content = generate_markdown(paper, task, [rr], "zh", False, True, experiment_results=[er])
        text = content.decode("utf-8")
        assert "交叉验证" not in text


class TestDeterminism:
    def test_same_input_same_output(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result()
        c1 = generate_markdown(paper, task, [rr], "zh", False, False)
        c2 = generate_markdown(paper, task, [rr], "zh", False, False)
        assert c1 == c2

    def test_deterministic_hash(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result()
        content = generate_markdown(paper, task, [rr], "zh", False, False)
        h = compute_content_hash(content)
        assert h == hashlib.sha256(content).hexdigest()

    def test_utf8_no_bom(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result()
        content = generate_markdown(paper, task, [rr], "zh", False, False)
        assert not content.startswith(b"\xef\xbb\xbf")

    def test_lf_only(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result()
        content = generate_markdown(paper, task, [rr], "zh", False, False)
        text = content.decode("utf-8")
        assert "\r\n" not in text
        assert "\r" not in text

    def test_trailing_newline(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result()
        content = generate_markdown(paper, task, [rr], "zh", False, False)
        assert content.endswith(b"\n")
        assert not content.endswith(b"\n\n")

    def test_generation_time_comes_from_source(self):
        paper = _make_paper()
        task = _make_review_task(
            completed_at=datetime.datetime(2025, 2, 3, 4, 5, 6, tzinfo=datetime.timezone.utc)
        )
        rr = _make_review_result()
        text = generate_markdown(paper, task, [rr], "en", False, False).decode("utf-8")
        assert "Generated At: 2025-02-03 04:05:06 UTC" in text

    def test_source_hash_is_canonical(self):
        first = {"review_task_id": "a", "experiment_results": [{"result_id": "b"}]}
        second = {"experiment_results": [{"result_id": "b"}], "review_task_id": "a"}
        assert compute_source_hash(first) == compute_source_hash(second)


class TestForbiddenFields:
    FORBIDDEN = [
        "storage_key", "content_hash", "raw_text",
        "/app/", "/tmp/", "SQL", "Traceback",
        "api_key", "token", "Bearer ",
    ]

    def test_no_storage_key_in_report(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result()
        content = generate_markdown(paper, task, [rr], "zh", True, True)
        text = content.decode("utf-8")
        for forbidden in self.FORBIDDEN:
            assert forbidden not in text, f"Forbidden string '{forbidden}' found in report"

    def test_no_raw_text_in_metrics(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result()
        metric_task = _make_metric_task()
        m = _make_metric_record(raw_text="secret raw text data")
        content = generate_markdown(paper, task, [rr], "zh", True, False, metric_task=metric_task, metrics=[m])
        text = content.decode("utf-8")
        assert "secret raw text data" not in text
        assert "raw_text" not in text


class TestSpecialValues:
    def test_zero_metric_value(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result()
        metric_task = _make_metric_task()
        m = _make_metric_record(metric_value=0.0)
        content = generate_markdown(paper, task, [rr], "zh", True, False, metric_task=metric_task, metrics=[m])
        text = content.decode("utf-8")
        assert "| 0.0 |" in text

    def test_negative_metric_value(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result()
        metric_task = _make_metric_task()
        m = _make_metric_record(metric_value=-0.5)
        content = generate_markdown(paper, task, [rr], "zh", True, False, metric_task=metric_task, metrics=[m])
        text = content.decode("utf-8")
        assert "| -0.5 |" in text

    def test_decimal_metric_value(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result()
        metric_task = _make_metric_task()
        m = _make_metric_record(metric_value=0.123456789)
        content = generate_markdown(paper, task, [rr], "zh", True, False, metric_task=metric_task, metrics=[m])
        text = content.decode("utf-8")
        assert "0.123456789" in text

    def test_null_model_and_dataset(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result()
        metric_task = _make_metric_task()
        m = _make_metric_record(model_name=None, dataset_name=None)
        content = generate_markdown(paper, task, [rr], "zh", True, False, metric_task=metric_task, metrics=[m])
        text = content.decode("utf-8")
        lines = text.split("\n")
        data_lines = [l for l in lines if l.startswith("|") and "---" not in l and "模型" not in l]
        assert len(data_lines) >= 1
        cells = [c.strip() for c in data_lines[-1].strip("|").split("|")]
        assert cells[0] == ""
        assert cells[1] == ""


class TestUnicode:
    def test_unicode_paper_title(self):
        paper = _make_paper(title="深度学习在自然语言处理中的应用")
        task = _make_review_task()
        rr = _make_review_result(summary="这是一篇关于深度学习的论文")
        content = generate_markdown(paper, task, [rr], "zh", False, False)
        text = content.decode("utf-8")
        assert "深度学习在自然语言处理中的应用" in text
        assert "这是一篇关于深度学习的论文" in text

    def test_unicode_model_name(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result()
        metric_task = _make_metric_task()
        m = _make_metric_record(model_name="模型α")
        content = generate_markdown(paper, task, [rr], "zh", True, False, metric_task=metric_task, metrics=[m])
        text = content.decode("utf-8")
        assert "模型α" in text


class TestMarkdownEscaping:
    def test_html_in_summary_escaped(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result(summary='<img src=x onerror=alert(1)>')
        content = generate_markdown(paper, task, [rr], "zh", False, False)
        text = content.decode("utf-8")
        assert "<img" not in text
        assert "&lt;img" in text

    def test_pipe_in_cell_escaped(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result()
        metric_task = _make_metric_task()
        m = _make_metric_record(model_name="a|b")
        content = generate_markdown(paper, task, [rr], "zh", True, False, metric_task=metric_task, metrics=[m])
        text = content.decode("utf-8")
        assert "a\\|b" in text

    def test_newline_in_cell_escaped(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result()
        metric_task = _make_metric_task()
        m = _make_metric_record(model_name="a\nb")
        content = generate_markdown(paper, task, [rr], "zh", True, False, metric_task=metric_task, metrics=[m])
        text = content.decode("utf-8")
        assert "a b" in text

    def test_script_tag_escaped(self):
        paper = _make_paper()
        task = _make_review_task()
        rr = _make_review_result(summary='<script>alert("xss")</script>')
        content = generate_markdown(paper, task, [rr], "en", False, False)
        text = content.decode("utf-8")
        assert "<script>" not in text
        assert "&lt;script&gt;" in text

    def test_markdown_structure_and_link_escaped(self):
        paper = _make_paper(title="# injected\n- item")
        task = _make_review_task()
        rr = _make_review_result(summary="[click](javascript:alert(1))")
        text = generate_markdown(paper, task, [rr], "en", False, False).decode("utf-8")
        assert "\\# injected" in text
        assert "\\- item" in text
        assert "\\[click\\](javascript\\:alert(1))" in text

    def test_evidence_page_and_short_quote(self):
        paper = _make_paper()
        task = _make_review_task()
        evidence = _make_evidence(page_number=7, quoted_text="quoted evidence")
        finding = _make_finding(evidences=[evidence])
        rr = _make_review_result(findings=[finding])
        text = generate_markdown(paper, task, [rr], "en", False, False).decode("utf-8")
        assert "**Evidence Page 7**: quoted evidence" in text


class TestComputeContentHash:
    def test_sha256(self):
        data = b"hello world"
        h = compute_content_hash(data)
        assert h == hashlib.sha256(data).hexdigest()
        assert len(h) == 64

    def test_empty(self):
        data = b""
        h = compute_content_hash(data)
        assert h == hashlib.sha256(data).hexdigest()
