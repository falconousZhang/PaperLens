import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from paperlens.core.enums import ReviewDimension
from paperlens.services.embedding_client import MockEmbeddingClient, EmbeddingError, cosine_similarity
from paperlens.services.evidence_retriever import (
    build_dimension_query,
    EvidenceCandidate,
    rank_evidence_by_dimension,
    retrieve_evidence_by_dimension,
)


class TestBuildDimensionQuery:
    def test_english_query_contains_dimension_terms(self):
        q = build_dimension_query("Test Paper", ReviewDimension.SOUNDNESS, "en")
        assert "SOUNDNESS" in q
        assert "methodology" in q
        assert "Test Paper" in q

    def test_chinese_query_contains_dimension_terms(self):
        q = build_dimension_query("测试论文", ReviewDimension.NOVELTY, "zh")
        assert "NOVELTY" in q
        assert "创新性" in q

    def test_unknown_language_defaults_to_english(self):
        q = build_dimension_query("Paper", ReviewDimension.CLARITY, "fr")
        assert "clarity" in q

    def test_overall_dimension(self):
        q = build_dimension_query("Paper", ReviewDimension.OVERALL, "en")
        assert "OVERALL" in q
        assert "assessment" in q


class TestRetrieveEvidenceByDimension:
    def _make_mock_db(self, evidence_list: list[dict]):
        rows = []
        for ev in evidence_list:
            rows.append((
                ev.get("id", str(uuid.uuid4())),
                ev.get("quoted_text", ""),
                ev.get("page_number", 1),
                ev.get("created_at", None),
                ev.get("raw_id", ev.get("id", str(uuid.uuid4()))),
            ))

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = rows

        mock_db = MagicMock()
        mock_db.query.return_value = mock_query
        return mock_db

    def test_returns_empty_for_no_evidence(self):
        mock_db = self._make_mock_db([])
        client = MockEmbeddingClient()
        result = retrieve_evidence_by_dimension(
            "paper-1", [ReviewDimension.OVERALL], "en", "Title", mock_db, client
        )
        assert result == {ReviewDimension.OVERALL: []}

    def test_returns_top_k_results(self):
        evidence = [
            {"id": f"ev-{i}", "quoted_text": f"Evidence text {i}", "page_number": i}
            for i in range(5)
        ]
        mock_db = self._make_mock_db(evidence)
        client = MockEmbeddingClient()
        result = retrieve_evidence_by_dimension(
            "paper-1", [ReviewDimension.OVERALL], "en", "Title", mock_db, client, top_k=3
        )
        assert len(result[ReviewDimension.OVERALL]) == 3

    def test_returns_id_and_text_tuples(self):
        evidence = [
            {"id": "ev-1", "quoted_text": "Some text", "page_number": 1},
        ]
        mock_db = self._make_mock_db(evidence)
        client = MockEmbeddingClient()
        result = retrieve_evidence_by_dimension(
            "paper-1", [ReviewDimension.OVERALL], "en", "Title", mock_db, client
        )
        items = result[ReviewDimension.OVERALL]
        assert len(items) == 1
        assert items[0][0] == "ev-1"
        assert items[0][1] == "Some text"

    def test_multiple_dimensions_independent(self):
        evidence = [
            {"id": "ev-0", "quoted_text": "methodology soundness reliability 0", "page_number": 1},
            {"id": "ev-10", "quoted_text": "novelty innovation originality 0", "page_number": 2},
        ]
        mock_db = self._make_mock_db(evidence)
        client = MockEmbeddingClient()
        result = retrieve_evidence_by_dimension(
            "paper-1",
            [ReviewDimension.SOUNDNESS, ReviewDimension.NOVELTY],
            "en",
            "Title",
            mock_db,
            client,
            top_k=2,
        )
        assert ReviewDimension.SOUNDNESS in result
        assert ReviewDimension.NOVELTY in result

    def test_evidence_embedded_once(self):
        evidence = [
            {"id": "ev-1", "quoted_text": "text1", "page_number": 1},
            {"id": "ev-2", "quoted_text": "text2", "page_number": 2},
        ]
        mock_db = self._make_mock_db(evidence)

        call_log = []

        class _TrackingClient(MockEmbeddingClient):
            def embed(self, texts):
                call_log.append(len(texts))
                return super().embed(texts)

        client = _TrackingClient()
        retrieve_evidence_by_dimension(
            "paper-1",
            [ReviewDimension.SOUNDNESS, ReviewDimension.NOVELTY, ReviewDimension.OVERALL],
            "en",
            "Title",
            mock_db,
            client,
        )
        assert len(call_log) == 2
        assert call_log[0] == 2
        assert call_log[1] == 3

    def test_semantic_ranking_prefers_relevant(self):
        evidence = [
            {"id": "ev-method", "quoted_text": "methodology approach technique algorithm", "page_number": 1},
            {"id": "ev-novel", "quoted_text": "novel innovative original contribution", "page_number": 2},
            {"id": "ev-clear", "quoted_text": "clear writing presentation readable", "page_number": 3},
        ]
        mock_db = self._make_mock_db(evidence)
        client = MockEmbeddingClient()
        result = retrieve_evidence_by_dimension(
            "paper-1",
            [ReviewDimension.SOUNDNESS],
            "en",
            "Test Paper",
            mock_db,
            client,
            top_k=3,
        )
        items = result[ReviewDimension.SOUNDNESS]
        assert items[0][0] == "ev-method"

    def test_top_k_defaults_to_settings(self):
        evidence = [
            {"id": f"ev-{i}", "quoted_text": f"text {i}", "page_number": i}
            for i in range(20)
        ]
        mock_db = self._make_mock_db(evidence)
        client = MockEmbeddingClient()
        result = retrieve_evidence_by_dimension(
            "paper-1", [ReviewDimension.OVERALL], "en", "Title", mock_db, client
        )
        assert len(result[ReviewDimension.OVERALL]) <= 8

    def test_tiebreaker_by_page_number(self):
        identical_texts = [
            {"id": "ev-3", "quoted_text": "same text", "page_number": 3},
            {"id": "ev-1", "quoted_text": "same text", "page_number": 1},
            {"id": "ev-2", "quoted_text": "same text", "page_number": 2},
        ]
        mock_db = self._make_mock_db(identical_texts)
        client = MockEmbeddingClient()
        result = retrieve_evidence_by_dimension(
            "paper-1", [ReviewDimension.OVERALL], "en", "Title", mock_db, client, top_k=3
        )
        items = result[ReviewDimension.OVERALL]
        assert items[0][0] == "ev-1"
        assert items[1][0] == "ev-2"
        assert items[2][0] == "ev-3"

    @pytest.mark.parametrize("top_k", [0, -1, True])
    def test_invalid_top_k_rejected(self, top_k):
        candidate = EvidenceCandidate(
            id="ev-1",
            text="methodology",
            page_number=1,
            created_at=datetime.now(timezone.utc),
        )
        with pytest.raises(EmbeddingError, match="positive integer"):
            rank_evidence_by_dimension(
                [candidate],
                [ReviewDimension.SOUNDNESS],
                "en",
                "Title",
                MockEmbeddingClient(),
                top_k,
            )

    def test_empty_dimensions_rejected(self):
        candidate = EvidenceCandidate(
            id="ev-1",
            text="methodology",
            page_number=1,
            created_at=datetime.now(timezone.utc),
        )
        with pytest.raises(EmbeddingError, match="dimensions must be non-empty"):
            rank_evidence_by_dimension(
                [candidate], [], "en", "Title", MockEmbeddingClient()
            )

    def test_chinese_semantic_ranking_prefers_relevant(self):
        evidence = [
            {"id": "ev-method", "quoted_text": "本文详细说明方法论与实验设置，结果具有可靠性", "page_number": 1},
            {"id": "ev-writing", "quoted_text": "文章重点讨论写作表达和段落组织", "page_number": 2},
        ]
        result = retrieve_evidence_by_dimension(
            "paper-1",
            [ReviewDimension.SOUNDNESS],
            "zh",
            "测试论文",
            self._make_mock_db(evidence),
            MockEmbeddingClient(),
            top_k=2,
        )
        assert result[ReviewDimension.SOUNDNESS][0][0] == "ev-method"
