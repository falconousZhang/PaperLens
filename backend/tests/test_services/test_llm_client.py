import json
import pytest

from paperlens.services.llm_client import MockLLMClient, LLMError, get_llm_client


class TestMockLLMClient:
    def test_overall_dimension_returns_verdict(self):
        client = MockLLMClient()
        result = client.chat([], dimension="OVERALL", evidence_aliases=["E1"])
        content = json.loads(result["content"])
        assert content["dimension"] == "OVERALL"
        assert content["overall_verdict"] is not None

    def test_non_overall_dimension_null_verdict(self):
        client = MockLLMClient()
        result = client.chat([], dimension="SOUNDNESS", evidence_aliases=["E1"])
        content = json.loads(result["content"])
        assert content["dimension"] == "SOUNDNESS"
        assert content["overall_verdict"] is None

    def test_with_evidence_aliases_returns_findings(self):
        client = MockLLMClient()
        result = client.chat([], dimension="OVERALL", evidence_aliases=["E1", "E2"])
        content = json.loads(result["content"])
        assert len(content["findings"]) >= 1
        assert content["findings"][0]["evidence_refs"] == ["E1"]

    def test_returns_valid_structure(self):
        client = MockLLMClient()
        result = client.chat(messages=[{"role": "user", "content": "test"}])
        assert "content" in result
        assert result["role"] == "assistant"


class TestGetLLMClient:
    def test_mock_backend_returns_mock_client(self):
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

    def test_no_mutable_global_state(self):
        from paperlens.services import llm_client
        assert not hasattr(llm_client, "_llm_client") or llm_client._llm_client is None
        c1 = get_llm_client()
        c2 = get_llm_client()
        assert isinstance(c1, MockLLMClient)
        assert isinstance(c2, MockLLMClient)
