import json
import pytest
import httpx
from pydantic import SecretStr

from paperlens.services.embedding_client import EmbeddingError
from paperlens.services.huawei_maas_embedding import HuaweiMaaSEmbeddingClient


def _make_mock_transport(responses: list[httpx.Response]):
    call_count = 0

    class _MockTransport(httpx.BaseTransport):
        nonlocal call_count

        def handle_request(self, request):
            nonlocal call_count
            if call_count >= len(responses):
                return httpx.Response(500, json={"error": "unexpected call"})
            resp = responses[call_count]
            call_count += 1
            return resp

    return _MockTransport()


def _ok_response(embeddings: list[list[float]], model: str = "bge-m3"):
    data = []
    for i, emb in enumerate(embeddings):
        data.append({"index": i, "embedding": emb, "object": "embedding"})
    return httpx.Response(
        200,
        json={"object": "list", "model": model, "data": data, "usage": {"prompt_tokens": 0, "total_tokens": 0}},
    )


class TestHuaweiMaaSBasic:
    def test_single_text_returns_vector(self):
        transport = _make_mock_transport([_ok_response([[0.1, 0.2, 0.3]])])
        client = HuaweiMaaSEmbeddingClient(
            base_url="https://mock.test",
            model="bge-m3",
            api_key="test-key",
            transport=transport,
        )
        result = client.embed(["hello"])
        assert len(result) == 1
        assert result[0] == [0.1, 0.2, 0.3]

    def test_multiple_texts_returns_ordered_vectors(self):
        transport = _make_mock_transport([
            _ok_response([[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]])
        ])
        client = HuaweiMaaSEmbeddingClient(
            base_url="https://mock.test",
            model="bge-m3",
            api_key="test-key",
            transport=transport,
        )
        result = client.embed(["a", "b", "c"])
        assert len(result) == 3
        assert result[0] == [1.0, 0.0]
        assert result[1] == [0.0, 1.0]
        assert result[2] == [0.5, 0.5]

    def test_empty_input_rejected(self):
        client = HuaweiMaaSEmbeddingClient(
            base_url="https://mock.test",
            model="bge-m3",
            api_key="test-key",
        )
        with pytest.raises(EmbeddingError, match="non-empty"):
            client.embed([])

    def test_empty_text_rejected(self):
        client = HuaweiMaaSEmbeddingClient(
            base_url="https://mock.test",
            model="bge-m3",
            api_key="test-key",
        )
        with pytest.raises(EmbeddingError, match="non-empty"):
            client.embed([""])

    def test_whitespace_only_text_rejected(self):
        client = HuaweiMaaSEmbeddingClient(
            base_url="https://mock.test",
            model="bge-m3",
            api_key="test-key",
        )
        with pytest.raises(EmbeddingError, match="non-empty"):
            client.embed(["   "])


class TestHuaweiMaaSAuth:
    def test_bearer_token_in_request(self):
        captured_request = None

        class _CapturingTransport(httpx.BaseTransport):
            def handle_request(self, request):
                nonlocal captured_request
                captured_request = request
                return _ok_response([[0.1, 0.2]])

        client = HuaweiMaaSEmbeddingClient(
            base_url="https://mock.test",
            model="bge-m3",
            api_key="my-secret-key",
            transport=_CapturingTransport(),
        )
        client.embed(["test"])
        assert captured_request is not None
        auth_header = captured_request.headers.get("authorization", "")
        assert auth_header == "Bearer my-secret-key"

    def test_secret_str_from_settings_is_unwrapped(self):
        from paperlens.core.config import settings

        original = settings.embedding_api_key
        captured_request = None

        class _CapturingTransport(httpx.BaseTransport):
            def handle_request(self, request):
                nonlocal captured_request
                captured_request = request
                return _ok_response([[1.0]])

        settings.embedding_api_key = SecretStr("settings-sentinel-key")
        try:
            client = HuaweiMaaSEmbeddingClient(
                base_url="https://mock.test",
                transport=_CapturingTransport(),
            )
            client.embed(["test"])
        finally:
            settings.embedding_api_key = original

        assert captured_request is not None
        assert captured_request.headers["authorization"] == "Bearer settings-sentinel-key"

    def test_missing_api_key_raises(self):
        from paperlens.core.config import settings
        original = settings.embedding_api_key
        settings.embedding_api_key = None
        try:
            with pytest.raises(EmbeddingError, match="embedding_api_key is required"):
                HuaweiMaaSEmbeddingClient()
        finally:
            settings.embedding_api_key = original


class TestHuaweiMaaSBatching:
    def test_batch_split_and_reassembly(self):
        batch1 = _ok_response([[1.0, 0.0], [0.0, 1.0]])
        batch2 = _ok_response([[0.5, 0.5]])
        transport = _make_mock_transport([batch1, batch2])
        client = HuaweiMaaSEmbeddingClient(
            base_url="https://mock.test",
            model="bge-m3",
            api_key="test-key",
            batch_size=2,
            transport=transport,
        )
        result = client.embed(["a", "b", "c"])
        assert len(result) == 3
        assert result[0] == [1.0, 0.0]
        assert result[1] == [0.0, 1.0]
        assert result[2] == [0.5, 0.5]

    def test_out_of_order_index_reassembled(self):
        transport = _make_mock_transport([
            httpx.Response(200, json={
                "object": "list",
                "data": [
                    {"index": 1, "embedding": [0.0, 1.0], "object": "embedding"},
                    {"index": 0, "embedding": [1.0, 0.0], "object": "embedding"},
                ],
            }),
        ])
        client = HuaweiMaaSEmbeddingClient(
            base_url="https://mock.test",
            model="bge-m3",
            api_key="test-key",
            transport=transport,
        )
        result = client.embed(["a", "b"])
        assert result[0] == [1.0, 0.0]
        assert result[1] == [0.0, 1.0]

    def test_later_batch_failure_discards_partial_results_and_redacts_body(self):
        transport = _make_mock_transport([
            _ok_response([[1.0, 0.0], [0.0, 1.0]]),
            httpx.Response(503, text="secret-upstream-response"),
        ])
        client = HuaweiMaaSEmbeddingClient(
            base_url="https://mock.test",
            model="bge-m3",
            api_key="test-key",
            batch_size=2,
            transport=transport,
        )

        with pytest.raises(EmbeddingError, match="status 503") as exc_info:
            client.embed(["a", "b", "c"])

        assert "secret-upstream-response" not in str(exc_info.value)


class TestHuaweiMaaSErrorHandling:
    @pytest.mark.parametrize(
        ("kwargs", "message"),
        [
            ({"base_url": "http://mock.test"}, "HTTPS"),
            ({"model": "   "}, "non-empty"),
            ({"timeout_seconds": 0}, "positive"),
            ({"batch_size": 0}, "positive integer"),
            ({"batch_size": True}, "positive integer"),
        ],
    )
    def test_invalid_constructor_values_rejected(self, kwargs, message):
        with pytest.raises(EmbeddingError, match=message):
            HuaweiMaaSEmbeddingClient(api_key="test-key", **kwargs)

    def test_http_error_status(self):
        transport = _make_mock_transport([httpx.Response(500, text="Internal Server Error")])
        client = HuaweiMaaSEmbeddingClient(
            base_url="https://mock.test",
            model="bge-m3",
            api_key="test-key",
            transport=transport,
        )
        with pytest.raises(EmbeddingError, match="status 500"):
            client.embed(["test"])

    def test_non_json_response(self):
        transport = _make_mock_transport([httpx.Response(200, text="not json")])
        client = HuaweiMaaSEmbeddingClient(
            base_url="https://mock.test",
            model="bge-m3",
            api_key="test-key",
            transport=transport,
        )
        with pytest.raises(EmbeddingError, match="non-JSON"):
            client.embed(["test"])

    def test_missing_data_array(self):
        transport = _make_mock_transport([
            httpx.Response(200, json={"object": "list"})
        ])
        client = HuaweiMaaSEmbeddingClient(
            base_url="https://mock.test",
            model="bge-m3",
            api_key="test-key",
            transport=transport,
        )
        with pytest.raises(EmbeddingError, match="missing data array"):
            client.embed(["test"])

    def test_non_object_response_rejected(self):
        transport = _make_mock_transport([httpx.Response(200, json=[])])
        client = HuaweiMaaSEmbeddingClient(
            base_url="https://mock.test",
            api_key="test-key",
            transport=transport,
        )
        with pytest.raises(EmbeddingError, match="JSON object"):
            client.embed(["test"])

    def test_non_object_data_item_rejected(self):
        transport = _make_mock_transport([httpx.Response(200, json={"data": [1]})])
        client = HuaweiMaaSEmbeddingClient(
            base_url="https://mock.test",
            api_key="test-key",
            transport=transport,
        )
        with pytest.raises(EmbeddingError, match="item must be an object"):
            client.embed(["test"])

    def test_boolean_index_rejected(self):
        transport = _make_mock_transport([
            httpx.Response(200, json={"data": [{"index": True, "embedding": [1.0]}]})
        ])
        client = HuaweiMaaSEmbeddingClient(
            base_url="https://mock.test",
            api_key="test-key",
            transport=transport,
        )
        with pytest.raises(EmbeddingError, match="valid index"):
            client.embed(["test"])

    def test_count_mismatch(self):
        transport = _make_mock_transport([
            _ok_response([[0.1, 0.2], [0.3, 0.4]])
        ])
        client = HuaweiMaaSEmbeddingClient(
            base_url="https://mock.test",
            model="bge-m3",
            api_key="test-key",
            transport=transport,
        )
        with pytest.raises(EmbeddingError, match="count mismatch"):
            client.embed(["a"])

    def test_missing_index(self):
        transport = _make_mock_transport([
            httpx.Response(200, json={
                "data": [{"embedding": [0.1, 0.2], "object": "embedding"}],
            }),
        ])
        client = HuaweiMaaSEmbeddingClient(
            base_url="https://mock.test",
            model="bge-m3",
            api_key="test-key",
            transport=transport,
        )
        with pytest.raises(EmbeddingError, match="missing valid index"):
            client.embed(["a"])

    def test_duplicate_index(self):
        transport = _make_mock_transport([
            httpx.Response(200, json={
                "data": [
                    {"index": 0, "embedding": [0.1, 0.2], "object": "embedding"},
                    {"index": 0, "embedding": [0.3, 0.4], "object": "embedding"},
                ],
            }),
        ])
        client = HuaweiMaaSEmbeddingClient(
            base_url="https://mock.test",
            model="bge-m3",
            api_key="test-key",
            transport=transport,
        )
        with pytest.raises(EmbeddingError, match="duplicate index"):
            client.embed(["a", "b"])

    def test_index_out_of_range(self):
        transport = _make_mock_transport([
            httpx.Response(200, json={
                "data": [
                    {"index": 5, "embedding": [0.1, 0.2], "object": "embedding"},
                ],
            }),
        ])
        client = HuaweiMaaSEmbeddingClient(
            base_url="https://mock.test",
            model="bge-m3",
            api_key="test-key",
            transport=transport,
        )
        with pytest.raises(EmbeddingError, match="index out of range"):
            client.embed(["a"])

    def test_missing_embedding_field(self):
        transport = _make_mock_transport([
            httpx.Response(200, json={
                "data": [{"index": 0, "object": "embedding"}],
            }),
        ])
        client = HuaweiMaaSEmbeddingClient(
            base_url="https://mock.test",
            model="bge-m3",
            api_key="test-key",
            transport=transport,
        )
        with pytest.raises(EmbeddingError, match="missing embedding"):
            client.embed(["a"])

    def test_boolean_in_embedding_rejected(self):
        transport = _make_mock_transport([
            httpx.Response(200, json={
                "data": [{"index": 0, "embedding": [True, 0.2], "object": "embedding"}],
            }),
        ])
        client = HuaweiMaaSEmbeddingClient(
            base_url="https://mock.test",
            model="bge-m3",
            api_key="test-key",
            transport=transport,
        )
        with pytest.raises(EmbeddingError, match="invalid vector value"):
            client.embed(["a"])

    def test_nan_in_embedding_rejected(self):
        raw_body = '{"data":[{"index":0,"embedding":[NaN,0.2],"object":"embedding"}]}'
        transport = _make_mock_transport([httpx.Response(200, text=raw_body, headers={"content-type": "application/json"})])
        client = HuaweiMaaSEmbeddingClient(
            base_url="https://mock.test",
            model="bge-m3",
            api_key="test-key",
            transport=transport,
        )
        with pytest.raises(EmbeddingError):
            client.embed(["a"])

    def test_inf_in_embedding_rejected(self):
        raw_body = '{"data":[{"index":0,"embedding":[Infinity,0.2],"object":"embedding"}]}'
        transport = _make_mock_transport([httpx.Response(200, text=raw_body, headers={"content-type": "application/json"})])
        client = HuaweiMaaSEmbeddingClient(
            base_url="https://mock.test",
            model="bge-m3",
            api_key="test-key",
            transport=transport,
        )
        with pytest.raises(EmbeddingError):
            client.embed(["a"])

    def test_empty_vector_rejected(self):
        transport = _make_mock_transport([
            httpx.Response(200, json={
                "data": [{"index": 0, "embedding": [], "object": "embedding"}],
            }),
        ])
        client = HuaweiMaaSEmbeddingClient(
            base_url="https://mock.test",
            model="bge-m3",
            api_key="test-key",
            transport=transport,
        )
        with pytest.raises(EmbeddingError, match="empty vector"):
            client.embed(["a"])

    def test_dimension_mismatch_across_items(self):
        transport = _make_mock_transport([
            httpx.Response(200, json={
                "data": [
                    {"index": 0, "embedding": [0.1, 0.2], "object": "embedding"},
                    {"index": 1, "embedding": [0.3, 0.4, 0.5], "object": "embedding"},
                ],
            }),
        ])
        client = HuaweiMaaSEmbeddingClient(
            base_url="https://mock.test",
            model="bge-m3",
            api_key="test-key",
            transport=transport,
        )
        with pytest.raises(EmbeddingError, match="dimension mismatch"):
            client.embed(["a", "b"])

    def test_missing_index_in_response(self):
        transport = _make_mock_transport([
            httpx.Response(200, json={
                "data": [
                    {"index": 0, "embedding": [0.1, 0.2], "object": "embedding"},
                    {"embedding": [0.3, 0.4], "object": "embedding"},
                ],
            }),
        ])
        client = HuaweiMaaSEmbeddingClient(
            base_url="https://mock.test",
            model="bge-m3",
            api_key="test-key",
            transport=transport,
        )
        with pytest.raises(EmbeddingError, match="missing valid index"):
            client.embed(["a", "b"])

    def test_connection_error(self):
        class _ConnectFailTransport(httpx.BaseTransport):
            def handle_request(self, request):
                raise httpx.ConnectError("connection refused")

        client = HuaweiMaaSEmbeddingClient(
            base_url="https://mock.test",
            model="bge-m3",
            api_key="test-key",
            transport=_ConnectFailTransport(),
        )
        with pytest.raises(EmbeddingError, match="connection failed"):
            client.embed(["test"])

    def test_timeout_error(self):
        class _TimeoutTransport(httpx.BaseTransport):
            def handle_request(self, request):
                raise httpx.TimeoutException("timed out")

        client = HuaweiMaaSEmbeddingClient(
            base_url="https://mock.test",
            model="bge-m3",
            api_key="test-key",
            transport=_TimeoutTransport(),
        )
        with pytest.raises(EmbeddingError, match="timed out"):
            client.embed(["test"])

    def test_no_api_key_leak_in_error(self):
        transport = _make_mock_transport([httpx.Response(500, text="error")])
        client = HuaweiMaaSEmbeddingClient(
            base_url="https://mock.test",
            model="bge-m3",
            api_key="super-secret-key-12345",
            transport=transport,
        )
        try:
            client.embed(["test"])
        except EmbeddingError as e:
            assert "super-secret-key" not in str(e)
