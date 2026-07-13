from paperlens.services.llm_client import MockLLMClient
import pytest


@pytest.mark.asyncio
async def test_mock_llm_client_returns_valid_structure():
    client = MockLLMClient()
    result = await client.chat(messages=[{"role": "user", "content": "test"}])
    assert "content" in result
    assert "dimension" in result["content"]