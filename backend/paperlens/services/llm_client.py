from abc import ABC, abstractmethod


class LLMClient(ABC):
    """LLM 调用统一接口"""

    @abstractmethod
    async def chat(self, messages: list[dict], **kwargs) -> dict:
        ...


class MockLLMClient(LLMClient):
    """默认 Mock 实现，无需云端密钥即可演示"""

    async def chat(self, messages: list[dict], **kwargs) -> dict:
        return {
            "role": "assistant",
            "content": '{"dimension": "OVERALL", "findings": []}',
        }