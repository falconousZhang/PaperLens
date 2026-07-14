from __future__ import annotations

import argparse
import sys
from urllib.parse import urlparse

from paperlens.core.config import settings
from paperlens.core.database import SessionLocal
from paperlens.core.enums import UserRole
from paperlens.models.models import User


def promote_admin(email: str, claim_legacy_data: bool = False) -> None:
    db = SessionLocal()
    try:
        email_normalized = email.strip().lower()
        user = db.query(User).filter(User.email_normalized == email_normalized).first()

        if user is None:
            print(f"User with email '{email}' not found.", file=sys.stderr)
            sys.exit(1)

        already_admin = user.role == UserRole.ADMIN
        user.role = UserRole.ADMIN

        if claim_legacy_data:
            from paperlens.models.models import Paper, AnalysisTask, ExperimentFile, ExportReport
            demo_id = settings.demo_user_id
            for model_cls in (Paper, AnalysisTask, ExperimentFile, ExportReport):
                db.query(model_cls).filter(model_cls.user_id == demo_id).update(
                    {"user_id": user.id}
                )

        db.commit()
        if already_admin and claim_legacy_data:
            print(f"User '{email}' is already an admin; requested legacy claim completed.")
        elif already_admin:
            print(f"User '{email}' is already an admin.")
        else:
            print(f"User '{email}' has been promoted to admin.")
    finally:
        db.close()


def maas_config_check() -> None:
    from paperlens.services.llm_client import validate_llm_config, LLMError

    try:
        info = validate_llm_config()
    except LLMError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)

    backend = info["backend"]
    print(f"backend: {backend}")
    print(f"api_key_configured: {'true' if info['api_key_configured'] else 'false'}")
    print(f"embedding_provider: {settings.embedding_provider}")

    if backend == "huawei_maas":
        parsed = urlparse(settings.llm_base_url)
        print(f"base_url_scheme: {parsed.scheme}")
        print(f"base_url_host: {parsed.hostname}")
        print(f"base_url_path: {parsed.path}")
        print(f"model: {settings.llm_model}")
        print(f"timeout_seconds: {settings.llm_timeout_seconds}")
        print(f"max_completion_tokens: {settings.llm_max_completion_tokens}")

    print("OK: configuration is valid")


def _get_smoke_client():
    from paperlens.services.huawei_maas_llm import HuaweiMaaSLLMClient

    return HuaweiMaaSLLMClient(
        max_completion_tokens=min(settings.llm_max_completion_tokens, 32)
    )


def _classify_smoke_failure(exc: Exception) -> str:
    message = str(exc)
    status_prefix = "LLM service returned status "
    if message.startswith(status_prefix):
        try:
            status = int(message.removeprefix(status_prefix))
        except ValueError:
            return "request"
        if status == 401:
            return "authentication"
        if status == 403:
            return "permission"
        if status == 402:
            return "quota_or_billing"
        if status == 429:
            return "rate_or_quota"
        if status >= 500:
            return "service"
        return "request"
    if "timed out" in message:
        return "timeout"
    if "connection failed" in message:
        return "connection"
    if "truncated" in message or "finish_reason=length" in message:
        return "truncated"
    if "response" in message:
        return "response"
    return "unknown"


def maas_smoke(confirm_billable: bool = False, client_factory=None) -> None:
    if not confirm_billable:
        print("FAIL: --confirm-billable is required to proceed with a billable API call", file=sys.stderr)
        sys.exit(1)

    if settings.llm_backend != "huawei_maas":
        print("FAIL: LLM backend is not huawei_maas; smoke test requires huawei_maas", file=sys.stderr)
        sys.exit(1)

    from paperlens.services.llm_client import LLMError

    try:
        factory = _get_smoke_client if client_factory is None else client_factory
        client = factory()
        result = client.chat(
            messages=[{"role": "user", "content": "Hi"}],
            thinking_type="disabled",
        )
        content = result.get("content", "")
        if not content or not content.strip():
            print("FAIL: LLM returned empty content", file=sys.stderr)
            sys.exit(1)
        char_count = len(content.strip())
        print(f"OK: smoke test passed ({char_count} characters)")
    except LLMError as exc:
        reason = _classify_smoke_failure(exc)
        print(
            f"FAIL: MaaS smoke test failed (reason={reason})",
            file=sys.stderr,
        )
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="PaperLens CLI")
    subparsers = parser.add_subparsers(dest="command")

    promote_parser = subparsers.add_parser("promote-admin", help="Promote a user to admin")
    promote_parser.add_argument("--email", required=True, help="Email of the user to promote")
    promote_parser.add_argument(
        "--claim-legacy-data",
        action="store_true",
        help="Transfer demo-user data to this admin",
    )

    subparsers.add_parser("maas-config-check", help="Validate MaaS LLM configuration without network access")

    smoke_parser = subparsers.add_parser("maas-smoke", help="Send a minimal chat request to MaaS LLM (billable)")
    smoke_parser.add_argument(
        "--confirm-billable",
        action="store_true",
        help="Explicitly confirm that this will incur charges",
    )

    args = parser.parse_args()

    if args.command == "promote-admin":
        promote_admin(args.email, args.claim_legacy_data)
    elif args.command == "maas-config-check":
        maas_config_check()
    elif args.command == "maas-smoke":
        maas_smoke(args.confirm_billable)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
