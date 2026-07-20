import json
import math
from typing import Any

import httpx
from pydantic import SecretStr

from paperlens.core.config import settings
from paperlens.services.llm_client import LLMClient, LLMError

_VALID_ROLES = {"system", "user", "assistant"}
_MAX_TIMEOUT_SECONDS = 600
_MAX_COMPLETION_TOKENS = 16384
_API_KEY_PLACEHOLDERS = {
    "<api-key>",
    "<your-api-key>",
    "api-key",
    "api_key",
    "changeme",
    "replace-me",
    "replace_me",
    "your-api-key",
    "your_api_key",
    "由用户环境安全注入",
}


class HuaweiMaaSLLMClient(LLMClient):
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | SecretStr | None = None,
        timeout_seconds: float | None = None,
        max_completion_tokens: int | None = None,
        transport: httpx.BaseTransport | None = None,
    ):
        resolved_base_url = settings.llm_base_url if base_url is None else base_url
        if not isinstance(resolved_base_url, str):
            raise LLMError("llm_base_url must be a string")
        resolved_base_url = resolved_base_url.strip().rstrip("/")
        if not resolved_base_url:
            raise LLMError("llm_base_url must be an absolute HTTPS URL")

        try:
            parsed_url = httpx.URL(resolved_base_url)
        except (httpx.InvalidURL, TypeError, ValueError):
            raise LLMError("llm_base_url must be a valid absolute HTTPS URL") from None
        if parsed_url.scheme != "https" or not parsed_url.host:
            raise LLMError("llm_base_url must be an absolute HTTPS URL")
        if parsed_url.userinfo or parsed_url.query or parsed_url.fragment:
            raise LLMError(
                "llm_base_url must not include credentials, query parameters, or a fragment"
            )
        if parsed_url.path.rstrip("/").endswith("/chat/completions"):
            raise LLMError("llm_base_url must not include /chat/completions")
        self._base_url = str(parsed_url).rstrip("/")

        resolved_model = settings.llm_model if model is None else model
        if not isinstance(resolved_model, str):
            raise LLMError("llm_model must be a string")
        self._model = resolved_model.strip()
        if not self._model:
            raise LLMError("llm_model must be non-empty")

        self._api_key = self._coerce_api_key(api_key) if api_key is not None else self._resolve_api_key()
        self._timeout = settings.llm_timeout_seconds if timeout_seconds is None else timeout_seconds
        self._max_completion_tokens = settings.llm_max_completion_tokens if max_completion_tokens is None else max_completion_tokens
        self._validate_timeout_seconds(self._timeout)
        self._validate_max_completion_tokens(self._max_completion_tokens)
        if transport is not None and not isinstance(transport, httpx.BaseTransport):
            raise LLMError("transport must implement httpx.BaseTransport")
        self._transport = transport

    @staticmethod
    def _validate_timeout_seconds(value: float) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 1
            or value > _MAX_TIMEOUT_SECONDS
        ):
            raise LLMError(
                f"timeout_seconds must be a positive finite number no greater than {_MAX_TIMEOUT_SECONDS}"
            )

    @staticmethod
    def _validate_max_completion_tokens(value: int) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 1
            or value > _MAX_COMPLETION_TOKENS
        ):
            raise LLMError(
                "max_completion_tokens must be a positive integer "
                f"no greater than {_MAX_COMPLETION_TOKENS}"
            )

    @staticmethod
    def _resolve_api_key() -> str:
        key = settings.llm_api_key
        if not key:
            raise LLMError("llm_api_key is required when backend is huawei_maas")
        return HuaweiMaaSLLMClient._coerce_api_key(key)

    @staticmethod
    def _coerce_api_key(key: str | SecretStr) -> str:
        if isinstance(key, SecretStr):
            value = key.get_secret_value()
        elif isinstance(key, str):
            value = key
        else:
            raise LLMError("llm_api_key must be a string")
        value = value.strip()
        if not value:
            raise LLMError("llm_api_key must be non-empty")
        if value.lower() in _API_KEY_PLACEHOLDERS:
            raise LLMError("llm_api_key must not be a placeholder")
        return value

    def chat(self, messages: list[dict], **kwargs) -> dict:
        self._validate_messages(messages)

        request_timeout = kwargs.get("timeout_seconds", self._timeout)
        self._validate_timeout_seconds(request_timeout)

        thinking_type = kwargs.get("thinking_type")
        if thinking_type is not None and (
            not isinstance(thinking_type, str)
            or thinking_type not in {"enabled", "disabled"}
        ):
            raise LLMError("thinking_type must be enabled or disabled")

        request_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
        ]

        request_body: dict[str, Any] = {
            "model": self._model,
            "messages": request_messages,
            "stream": False,
            "max_completion_tokens": self._max_completion_tokens,
        }
        if thinking_type is not None:
            request_body["thinking"] = {"type": thinking_type}

        client_kwargs: dict[str, Any] = {
            "base_url": self._base_url,
            "timeout": self._timeout,
        }
        if self._transport is not None:
            client_kwargs["transport"] = self._transport

        try:
            with httpx.Client(**client_kwargs) as client:
                response = client.post(
                    "/chat/completions",
                    json=request_body,
                    timeout=request_timeout,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                )
        except httpx.TimeoutException:
            raise LLMError("LLM request timed out") from None
        except httpx.ConnectError:
            raise LLMError("LLM service connection failed") from None
        except httpx.HTTPError as exc:
            raise LLMError(f"LLM request failed: {type(exc).__name__}") from None

        if response.status_code < 200 or response.status_code >= 300:
            raise LLMError(f"LLM service returned status {response.status_code}")

        try:
            body = response.json()
        except (json.JSONDecodeError, ValueError):
            raise LLMError("LLM service returned non-JSON response") from None

        if not isinstance(body, dict):
            raise LLMError("LLM response must be a JSON object")

        return self._parse_response(body)

    @staticmethod
    def _validate_messages(messages: list[dict]) -> None:
        if not isinstance(messages, list):
            raise LLMError("messages must be a list")
        if not messages:
            raise LLMError("messages must be a non-empty list")
        for i, m in enumerate(messages):
            if not isinstance(m, dict):
                raise LLMError(f"messages[{i}] must be an object")
            role = m.get("role")
            if not isinstance(role, str) or role not in _VALID_ROLES:
                raise LLMError(f"messages[{i}] has invalid role")
            content = m.get("content")
            if not isinstance(content, str) or not content.strip():
                raise LLMError(f"messages[{i}] content must be a non-empty string")

    @staticmethod
    def _parse_response(body: dict) -> dict:
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMError("LLM response missing choices array")

        target = None
        seen_indices: set[int] = set()
        for item in choices:
            if not isinstance(item, dict):
                raise LLMError("LLM response choice must be an object")
            idx = item.get("index")
            if isinstance(idx, bool) or not isinstance(idx, int) or idx < 0:
                raise LLMError("LLM response choice missing valid index")
            if idx in seen_indices:
                raise LLMError(f"LLM response duplicate index {idx}")
            seen_indices.add(idx)
            if idx == 0:
                target = item

        if target is None:
            raise LLMError("LLM response missing index 0")
        if len(choices) != 1:
            raise LLMError("LLM response must contain a single choice")

        message = target.get("message")
        if not isinstance(message, dict):
            raise LLMError("LLM response choice missing message object")

        role = message.get("role")
        if role != "assistant":
            raise LLMError("LLM response message role must be assistant")

        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise LLMError("LLM response message content must be a non-empty string")

        finish_reason = target.get("finish_reason")
        if finish_reason != "stop":
            if finish_reason == "length":
                raise LLMError("LLM response truncated (finish_reason=length)")
            if finish_reason == "tool_calls":
                raise LLMError("LLM response has tool_calls (not supported)")
            if finish_reason is None:
                raise LLMError("LLM response missing finish_reason")
            raise LLMError("LLM response has unexpected finish_reason")

        return {"role": "assistant", "content": content}
