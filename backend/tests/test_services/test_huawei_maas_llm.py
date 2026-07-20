import json
import pytest
import httpx

from paperlens.services.llm_client import LLMClient, LLMError, MockLLMClient, get_llm_client
from paperlens.services.huawei_maas_llm import HuaweiMaaSLLMClient
from pydantic import SecretStr


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


def _ok_response(content: str, model: str = "glm-5.2", finish_reason: str = "stop"):
    return httpx.Response(
        200,
        json={
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": finish_reason,
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        },
    )


class TestMockLLMClient:
    def test_overall_returns_verdict(self):
        client = MockLLMClient()
        result = client.chat([], dimension="OVERALL", evidence_aliases=["E1"])
        data = json.loads(result["content"])
        assert data["dimension"] == "OVERALL"
        assert data["overall_verdict"] is not None

    def test_non_overall_null_verdict(self):
        client = MockLLMClient()
        result = client.chat([], dimension="SOUNDNESS", evidence_aliases=["E1"])
        data = json.loads(result["content"])
        assert data["overall_verdict"] is None

    def test_returns_assistant_content(self):
        client = MockLLMClient()
        result = client.chat([], dimension="OVERALL")
        assert result["role"] == "assistant"
        assert isinstance(result["content"], str)


class TestGetLLMClient:
    def test_mock_backend_returns_mock(self):
        from paperlens.core.config import settings
        original = settings.llm_backend
        settings.llm_backend = "mock"
        try:
            client = get_llm_client()
            assert isinstance(client, MockLLMClient)
        finally:
            settings.llm_backend = original

    def test_unknown_backend_raises(self):
        from paperlens.core.config import settings
        original = settings.llm_backend
        settings.llm_backend = "unknown"
        try:
            with pytest.raises(LLMError, match="Unknown LLM backend"):
                get_llm_client()
        finally:
            settings.llm_backend = original


class TestHuaweiMaaSBasic:
    def test_single_chat_returns_assistant_content(self):
        transport = _make_mock_transport([_ok_response("hello world")])
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="test-key",
            transport=transport,
        )
        result = client.chat([{"role": "user", "content": "hi"}])
        assert result == {"role": "assistant", "content": "hello world"}

    def test_internal_kwargs_not_in_payload(self):
        captured_request = None

        class _CapturingTransport(httpx.BaseTransport):
            def handle_request(self, request):
                nonlocal captured_request
                captured_request = request
                return _ok_response("ok")

        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test/v2",
            model="glm-5.2",
            api_key="test-key",
            transport=_CapturingTransport(),
        )
        client.chat(
            [{"role": "user", "content": "hi"}],
            dimension="SOUNDNESS",
            evidence_aliases=["E1"],
        )
        body = json.loads(captured_request.content)
        assert str(captured_request.url) == "https://mock.test/v2/chat/completions"
        assert body["model"] == "glm-5.2"
        assert "dimension" not in body
        assert "evidence_aliases" not in body
        assert "max_tokens" not in body
        assert "response_format" not in body
        assert body["stream"] is False
        assert body["max_completion_tokens"] == 2048

    def test_thinking_disabled_is_sent_only_when_requested(self):
        captured_requests = []

        class _CapturingTransport(httpx.BaseTransport):
            def handle_request(self, request):
                captured_requests.append(request)
                return _ok_response("ok")

        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test/v2",
            model="glm-5.2",
            api_key="test-key",
            transport=_CapturingTransport(),
        )
        client.chat([{"role": "user", "content": "hi"}])
        client.chat(
            [{"role": "user", "content": "hi"}],
            thinking_type="disabled",
        )
        first_body = json.loads(captured_requests[0].content)
        second_body = json.loads(captured_requests[1].content)
        assert "thinking" not in first_body
        assert second_body["thinking"] == {"type": "disabled"}

    @pytest.mark.parametrize("thinking_type", ["", "auto", True, 1])
    def test_invalid_thinking_type_rejected(self, thinking_type):
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test/v2",
            model="glm-5.2",
            api_key="test-key",
            transport=_make_mock_transport([_ok_response("ok")]),
        )
        with pytest.raises(LLMError, match="thinking_type"):
            client.chat(
                [{"role": "user", "content": "hi"}],
                thinking_type=thinking_type,
            )

    def test_messages_preserved_in_order(self):
        captured_request = None

        class _CapturingTransport(httpx.BaseTransport):
            def handle_request(self, request):
                nonlocal captured_request
                captured_request = request
                return _ok_response("ok")

        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="test-key",
            transport=_CapturingTransport(),
        )
        msgs = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "usr"},
        ]
        client.chat(msgs)
        body = json.loads(captured_request.content)
        assert body["messages"] == [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "usr"},
        ]

    def test_input_messages_not_modified(self):
        transport = _make_mock_transport([_ok_response("ok")])
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="test-key",
            transport=transport,
        )
        msgs = [{"role": "user", "content": "hi"}]
        original = msgs.copy()
        client.chat(msgs)
        assert msgs == original


class TestHuaweiMaaSAuth:
    def test_bearer_token_in_request(self):
        captured_request = None

        class _CapturingTransport(httpx.BaseTransport):
            def handle_request(self, request):
                nonlocal captured_request
                captured_request = request
                return _ok_response("ok")

        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="my-secret-key",
            transport=_CapturingTransport(),
        )
        client.chat([{"role": "user", "content": "hi"}])
        auth = captured_request.headers.get("authorization", "")
        assert auth == "Bearer my-secret-key"

    def test_secret_str_api_key_sent_correctly(self):
        captured_request = None

        class _CapturingTransport(httpx.BaseTransport):
            def handle_request(self, request):
                nonlocal captured_request
                captured_request = request
                return _ok_response("ok")

        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key=SecretStr("sentinel-key-123"),
            transport=_CapturingTransport(),
        )
        client.chat([{"role": "user", "content": "hi"}])
        auth = captured_request.headers.get("authorization", "")
        assert auth == "Bearer sentinel-key-123"
        assert "**********" not in auth

    def test_missing_api_key_raises(self):
        from paperlens.core.config import settings
        original = settings.llm_api_key
        settings.llm_api_key = None
        try:
            with pytest.raises(LLMError, match="llm_api_key is required"):
                HuaweiMaaSLLMClient()
        finally:
            settings.llm_api_key = original


class TestHuaweiMaaSConstructor:
    def test_http_url_rejected(self):
        with pytest.raises(LLMError, match="HTTPS"):
            HuaweiMaaSLLMClient(
                base_url="http://insecure.test",
                model="glm-5.2",
                api_key="key",
            )

    def test_relative_url_rejected(self):
        with pytest.raises(LLMError, match="HTTPS"):
            HuaweiMaaSLLMClient(
                base_url="/relative/path",
                model="glm-5.2",
                api_key="key",
            )

    def test_empty_model_rejected(self):
        with pytest.raises(LLMError, match="non-empty"):
            HuaweiMaaSLLMClient(
                base_url="https://mock.test",
                model="  ",
                api_key="key",
            )

    def test_empty_api_key_rejected(self):
        with pytest.raises(LLMError, match="non-empty"):
            HuaweiMaaSLLMClient(
                base_url="https://mock.test",
                model="glm-5.2",
                api_key="  ",
            )

    def test_zero_timeout_rejected(self):
        with pytest.raises(LLMError, match="positive"):
            HuaweiMaaSLLMClient(
                base_url="https://mock.test",
                model="glm-5.2",
                api_key="key",
                timeout_seconds=0,
            )

    def test_negative_timeout_rejected(self):
        with pytest.raises(LLMError, match="positive"):
            HuaweiMaaSLLMClient(
                base_url="https://mock.test",
                model="glm-5.2",
                api_key="key",
                timeout_seconds=-1,
            )

    def test_bool_timeout_rejected(self):
        with pytest.raises(LLMError, match="positive"):
            HuaweiMaaSLLMClient(
                base_url="https://mock.test",
                model="glm-5.2",
                api_key="key",
                timeout_seconds=True,
            )

    def test_zero_max_tokens_rejected(self):
        with pytest.raises(LLMError, match="positive integer"):
            HuaweiMaaSLLMClient(
                base_url="https://mock.test",
                model="glm-5.2",
                api_key="key",
                max_completion_tokens=0,
            )

    def test_bool_max_tokens_rejected(self):
        with pytest.raises(LLMError, match="positive integer"):
            HuaweiMaaSLLMClient(
                base_url="https://mock.test",
                model="glm-5.2",
                api_key="key",
                max_completion_tokens=True,
            )

    @pytest.mark.parametrize(
        "field,value",
        [
            ("base_url", 123),
            ("model", 123),
            ("api_key", 123),
        ],
    )
    def test_constructor_wrong_types_are_domain_errors(self, field, value):
        kwargs = {
            "base_url": "https://mock.test/v2",
            "model": "glm-5.2",
            "api_key": "key",
            field: value,
        }
        with pytest.raises(LLMError):
            HuaweiMaaSLLMClient(**kwargs)

    @pytest.mark.parametrize(
        "base_url",
        [
            "https://user:password@mock.test/v2",
            "https://mock.test/v2?target=other",
            "https://mock.test/v2#fragment",
        ],
    )
    def test_base_url_with_ambiguous_components_rejected(self, base_url):
        with pytest.raises(LLMError, match="base_url"):
            HuaweiMaaSLLMClient(
                base_url=base_url,
                model="glm-5.2",
                api_key="key",
            )

    @pytest.mark.parametrize("timeout", [float("nan"), float("inf"), 601])
    def test_non_finite_or_excessive_timeout_rejected(self, timeout):
        with pytest.raises(LLMError, match="timeout_seconds"):
            HuaweiMaaSLLMClient(
                base_url="https://mock.test/v2",
                model="glm-5.2",
                api_key="key",
                timeout_seconds=timeout,
            )

    def test_excessive_max_tokens_rejected(self):
        with pytest.raises(LLMError, match="max_completion_tokens"):
            HuaweiMaaSLLMClient(
                base_url="https://mock.test/v2",
                model="glm-5.2",
                api_key="key",
                max_completion_tokens=16385,
            )


class TestHuaweiMaaSMessageValidation:
    def test_empty_messages_rejected(self):
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="key",
        )
        with pytest.raises(LLMError, match="non-empty"):
            client.chat([])

    def test_invalid_role_rejected(self):
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="key",
        )
        with pytest.raises(LLMError, match="invalid role"):
            client.chat([{"role": "function", "content": "hi"}])

    def test_empty_content_rejected(self):
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="key",
        )
        with pytest.raises(LLMError, match="non-empty string"):
            client.chat([{"role": "user", "content": ""}])

    def test_non_string_content_rejected(self):
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="key",
        )
        with pytest.raises(LLMError, match="non-empty string"):
            client.chat([{"role": "user", "content": 123}])

    @pytest.mark.parametrize(
        "messages",
        [
            ({"role": "user", "content": "hi"},),
            123,
        ],
    )
    def test_messages_must_be_a_list(self, messages):
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test/v2",
            model="glm-5.2",
            api_key="key",
            transport=_make_mock_transport([_ok_response("ok")]),
        )
        with pytest.raises(LLMError, match="list"):
            client.chat(messages)


class TestHuaweiMaaSSuccessResponse:
    def test_extracts_content_from_choice_0(self):
        transport = _make_mock_transport([_ok_response("review result")])
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="key",
            transport=transport,
        )
        result = client.chat([{"role": "user", "content": "hi"}])
        assert result == {"role": "assistant", "content": "review result"}


class TestHuaweiMaaSErrorResponse:
    def test_non_2xx_status(self):
        transport = _make_mock_transport([httpx.Response(500, text="error")])
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="key",
            transport=transport,
        )
        with pytest.raises(LLMError, match="status 500"):
            client.chat([{"role": "user", "content": "hi"}])

    def test_4xx_status(self):
        transport = _make_mock_transport([httpx.Response(401, text="unauthorized")])
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="key",
            transport=transport,
        )
        with pytest.raises(LLMError, match="status 401"):
            client.chat([{"role": "user", "content": "hi"}])

    def test_non_json_response(self):
        transport = _make_mock_transport([httpx.Response(200, text="not json")])
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="key",
            transport=transport,
        )
        with pytest.raises(LLMError, match="non-JSON"):
            client.chat([{"role": "user", "content": "hi"}])

    def test_non_object_response(self):
        transport = _make_mock_transport([httpx.Response(200, json=[1, 2, 3])])
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="key",
            transport=transport,
        )
        with pytest.raises(LLMError, match="JSON object"):
            client.chat([{"role": "user", "content": "hi"}])

    def test_missing_choices(self):
        transport = _make_mock_transport([
            httpx.Response(200, json={"id": "x", "model": "m"})
        ])
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="key",
            transport=transport,
        )
        with pytest.raises(LLMError, match="choices"):
            client.chat([{"role": "user", "content": "hi"}])

    def test_empty_choices(self):
        transport = _make_mock_transport([
            httpx.Response(200, json={"choices": []})
        ])
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="key",
            transport=transport,
        )
        with pytest.raises(LLMError, match="choices"):
            client.chat([{"role": "user", "content": "hi"}])

    def test_choice_non_object(self):
        transport = _make_mock_transport([
            httpx.Response(200, json={"choices": ["bad"]})
        ])
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="key",
            transport=transport,
        )
        with pytest.raises(LLMError, match="object"):
            client.chat([{"role": "user", "content": "hi"}])

    def test_missing_index_0(self):
        transport = _make_mock_transport([
            httpx.Response(200, json={
                "choices": [{"index": 1, "message": {"role": "assistant", "content": "x"}, "finish_reason": "stop"}]
            })
        ])
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="key",
            transport=transport,
        )
        with pytest.raises(LLMError, match="index 0"):
            client.chat([{"role": "user", "content": "hi"}])

    def test_duplicate_index_0(self):
        transport = _make_mock_transport([
            httpx.Response(200, json={
                "choices": [
                    {"index": 0, "message": {"role": "assistant", "content": "a"}, "finish_reason": "stop"},
                    {"index": 0, "message": {"role": "assistant", "content": "b"}, "finish_reason": "stop"},
                ]
            })
        ])
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="key",
            transport=transport,
        )
        with pytest.raises(LLMError, match="duplicate index 0"):
            client.chat([{"role": "user", "content": "hi"}])

    def test_multiple_choices_rejected_as_ambiguous(self):
        transport = _make_mock_transport([
            httpx.Response(200, json={
                "choices": [
                    {"index": 0, "message": {"role": "assistant", "content": "a"}, "finish_reason": "stop"},
                    {"index": 1, "message": {"role": "assistant", "content": "b"}, "finish_reason": "stop"},
                ]
            })
        ])
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test/v2",
            model="glm-5.2",
            api_key="key",
            transport=transport,
        )
        with pytest.raises(LLMError, match="single choice"):
            client.chat([{"role": "user", "content": "hi"}])

    def test_duplicate_nonzero_index_rejected(self):
        transport = _make_mock_transport([
            httpx.Response(200, json={
                "choices": [
                    {"index": 0, "message": {"role": "assistant", "content": "a"}, "finish_reason": "stop"},
                    {"index": 1, "message": {"role": "assistant", "content": "b"}, "finish_reason": "stop"},
                    {"index": 1, "message": {"role": "assistant", "content": "c"}, "finish_reason": "stop"},
                ]
            })
        ])
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test/v2",
            model="glm-5.2",
            api_key="key",
            transport=transport,
        )
        with pytest.raises(LLMError, match="duplicate index"):
            client.chat([{"role": "user", "content": "hi"}])

    def test_bool_index_rejected(self):
        transport = _make_mock_transport([
            httpx.Response(200, json={
                "choices": [{"index": True, "message": {"role": "assistant", "content": "x"}, "finish_reason": "stop"}]
            })
        ])
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="key",
            transport=transport,
        )
        with pytest.raises(LLMError, match="valid index"):
            client.chat([{"role": "user", "content": "hi"}])

    def test_missing_message_object(self):
        transport = _make_mock_transport([
            httpx.Response(200, json={
                "choices": [{"index": 0, "finish_reason": "stop"}]
            })
        ])
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="key",
            transport=transport,
        )
        with pytest.raises(LLMError, match="message"):
            client.chat([{"role": "user", "content": "hi"}])

    def test_wrong_role(self):
        transport = _make_mock_transport([
            httpx.Response(200, json={
                "choices": [{"index": 0, "message": {"role": "user", "content": "x"}, "finish_reason": "stop"}]
            })
        ])
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="key",
            transport=transport,
        )
        with pytest.raises(LLMError, match="assistant"):
            client.chat([{"role": "user", "content": "hi"}])

    def test_empty_content(self):
        transport = _make_mock_transport([
            httpx.Response(200, json={
                "choices": [{"index": 0, "message": {"role": "assistant", "content": ""}, "finish_reason": "stop"}]
            })
        ])
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="key",
            transport=transport,
        )
        with pytest.raises(LLMError, match="non-empty"):
            client.chat([{"role": "user", "content": "hi"}])

    def test_non_string_content(self):
        transport = _make_mock_transport([
            httpx.Response(200, json={
                "choices": [{"index": 0, "message": {"role": "assistant", "content": 42}, "finish_reason": "stop"}]
            })
        ])
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="key",
            transport=transport,
        )
        with pytest.raises(LLMError, match="non-empty"):
            client.chat([{"role": "user", "content": "hi"}])


class TestHuaweiMaaSFinishReason:
    def test_stop_succeeds(self):
        transport = _make_mock_transport([_ok_response("ok", finish_reason="stop")])
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="key",
            transport=transport,
        )
        result = client.chat([{"role": "user", "content": "hi"}])
        assert result["content"] == "ok"

    def test_length_fails(self):
        transport = _make_mock_transport([_ok_response("trunc", finish_reason="length")])
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="key",
            transport=transport,
        )
        with pytest.raises(LLMError, match="truncated"):
            client.chat([{"role": "user", "content": "hi"}])

    def test_tool_calls_fails(self):
        transport = _make_mock_transport([_ok_response("tc", finish_reason="tool_calls")])
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="key",
            transport=transport,
        )
        with pytest.raises(LLMError, match="tool_calls"):
            client.chat([{"role": "user", "content": "hi"}])

    def test_missing_finish_reason_fails(self):
        transport = _make_mock_transport([
            httpx.Response(200, json={
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "x"}}]
            })
        ])
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="key",
            transport=transport,
        )
        with pytest.raises(LLMError, match="finish_reason"):
            client.chat([{"role": "user", "content": "hi"}])

    def test_unknown_finish_reason_fails(self):
        transport = _make_mock_transport([_ok_response("x", finish_reason="content_filter")])
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="key",
            transport=transport,
        )
        with pytest.raises(LLMError, match="unexpected finish_reason"):
            client.chat([{"role": "user", "content": "hi"}])

    def test_unknown_finish_reason_value_not_exposed(self):
        sentinel = "secret-upstream-finish-reason"
        transport = _make_mock_transport([_ok_response("partial", finish_reason=sentinel)])
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test/v2",
            model="glm-5.2",
            api_key="key",
            transport=transport,
        )
        with pytest.raises(LLMError) as exc_info:
            client.chat([{"role": "user", "content": "hi"}])
        assert sentinel not in str(exc_info.value)


class TestHuaweiMaaSNetworkErrors:
    def test_per_request_timeout_override(self):
        captured_timeout = None

        class _CapturingTransport(httpx.BaseTransport):
            def handle_request(self, request):
                nonlocal captured_timeout
                captured_timeout = request.extensions["timeout"]
                return _ok_response("ok")

        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="key",
            timeout_seconds=60,
            transport=_CapturingTransport(),
        )
        client.chat(
            [{"role": "user", "content": "hi"}],
            timeout_seconds=180,
        )
        assert captured_timeout["read"] == 180

    def test_timeout_error(self):
        class _TimeoutTransport(httpx.BaseTransport):
            def handle_request(self, request):
                raise httpx.TimeoutException("timed out")

        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="key",
            transport=_TimeoutTransport(),
        )
        with pytest.raises(LLMError, match="timed out"):
            client.chat([{"role": "user", "content": "hi"}])

    def test_connection_error(self):
        class _ConnectFailTransport(httpx.BaseTransport):
            def handle_request(self, request):
                raise httpx.ConnectError("refused")

        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="key",
            transport=_ConnectFailTransport(),
        )
        with pytest.raises(LLMError, match="connection failed"):
            client.chat([{"role": "user", "content": "hi"}])

    def test_no_api_key_leak_in_error(self):
        transport = _make_mock_transport([httpx.Response(500, text="error")])
        client = HuaweiMaaSLLMClient(
            base_url="https://mock.test",
            model="glm-5.2",
            api_key="super-secret-key-99999",
            transport=transport,
        )
        try:
            client.chat([{"role": "user", "content": "hi"}])
        except LLMError as e:
            assert "super-secret-key" not in str(e)
