import json
from abc import ABC, abstractmethod

from paperlens.core.config import settings


class LLMError(Exception):
    pass


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


def validate_llm_config() -> dict:
    backend = settings.llm_backend
    result = {
        "backend": backend,
        "api_key_configured": False,
    }
    if backend == "mock":
        return result
    if backend == "huawei_maas":
        from paperlens.services.huawei_maas_llm import HuaweiMaaSLLMClient

        HuaweiMaaSLLMClient()
        result["base_url"] = settings.llm_base_url
        result["model"] = settings.llm_model
        result["timeout_seconds"] = settings.llm_timeout_seconds
        result["max_completion_tokens"] = settings.llm_max_completion_tokens
        result["api_key_configured"] = settings.llm_api_key is not None
        return result
    raise LLMError(f"Unknown LLM backend: {backend}")


def get_llm_client() -> LLMClient:
    backend = settings.llm_backend
    if backend == "mock":
        return MockLLMClient()
    if backend == "huawei_maas":
        from paperlens.services.huawei_maas_llm import HuaweiMaaSLLMClient

        return HuaweiMaaSLLMClient()
    raise LLMError(f"Unknown LLM backend: {backend}")
