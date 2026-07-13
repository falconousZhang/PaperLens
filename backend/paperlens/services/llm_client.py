import json
from abc import ABC, abstractmethod

from paperlens.core.config import settings

class LLMClient(ABC):
    @abstractmethod
    def chat(self, messages: list[dict], **kwargs) -> dict:
        ...


class MockLLMClient(LLMClient):
    def chat(self, messages: list[dict], **kwargs) -> dict:
        dimension = kwargs.get("dimension", "OVERALL")
        evidence_aliases = kwargs.get("evidence_aliases", [])

        findings = []
        if evidence_aliases:
            findings.append(
                {
                    "finding_type": "STRENGTH",
                    "content": f"Mock strength finding for {dimension}",
                    "confidence": 0.9,
                    "evidence_refs": [evidence_aliases[0]],
                }
            )
        if len(evidence_aliases) > 1:
            findings.append(
                {
                    "finding_type": "WEAKNESS",
                    "content": f"Mock weakness finding for {dimension}",
                    "confidence": 0.7,
                    "evidence_refs": [evidence_aliases[1]],
                }
            )

        overall_verdict = "WEAK_ACCEPT" if dimension == "OVERALL" else None

        content = json.dumps(
            {
                "dimension": dimension,
                "rating": 4,
                "summary": f"Mock review summary for {dimension}",
                "overall_verdict": overall_verdict,
                "findings": findings,
            }
        )

        return {"role": "assistant", "content": content}


_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        backend = settings.llm_backend
        if backend == "mock":
            _llm_client = MockLLMClient()
        else:
            raise ValueError(f"Unknown LLM backend: {backend}")
    return _llm_client


def set_llm_client(client: LLMClient):
    global _llm_client
    _llm_client = client


def reset_llm_client():
    global _llm_client
    _llm_client = None
