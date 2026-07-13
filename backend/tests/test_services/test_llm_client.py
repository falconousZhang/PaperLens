from paperlens.services.llm_client import MockLLMClient


def test_mock_llm_client_returns_valid_structure():
    client = MockLLMClient()
    result = client.chat(messages=[{"role": "user", "content": "test"}])
    assert "content" in result