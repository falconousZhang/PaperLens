from __future__ import annotations

import secrets
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    env_path = root / ".env"
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    values = {}
    for line in lines:
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()

    changed = False
    if not values.get("PAPERLENS_JWT_SECRET"):
        lines.append(f"PAPERLENS_JWT_SECRET={secrets.token_urlsafe(48)}")
        changed = True
    if "PAPERLENS_AUTH_COOKIE_SECURE" not in values:
        lines.append("PAPERLENS_AUTH_COOKIE_SECURE=false")
        changed = True

    if changed:
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("Local .env authentication settings created without displaying secret values.")
    else:
        print("Local .env authentication settings already exist.")


if __name__ == "__main__":
    main()
