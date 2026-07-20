#!/bin/sh
set -eu

load_secret() {
    target_name="$1"
    file_name="$2"
    eval "secret_path=\${$file_name:-}"
    if [ -z "$secret_path" ] || [ ! -r "$secret_path" ]; then
        echo "required secret file is unavailable: $file_name" >&2
        exit 1
    fi
    secret_value=$(cat "$secret_path")
    if [ -z "$secret_value" ]; then
        echo "required secret file is empty: $file_name" >&2
        exit 1
    fi
    export "$target_name=$secret_value"
    unset "$file_name"
}

if [ "${PAPERLENS_ENV:-}" = "production" ]; then
    load_secret PAPERLENS_DATABASE_URL PAPERLENS_DATABASE_URL_FILE
    load_secret PAPERLENS_JWT_SECRET PAPERLENS_JWT_SECRET_FILE
    load_secret PAPERLENS_LLM_API_KEY PAPERLENS_LLM_API_KEY_FILE
    load_secret PAPERLENS_EMBEDDING_API_KEY PAPERLENS_EMBEDDING_API_KEY_FILE

    if [ "${PAPERLENS_OBS_CREDENTIAL_MODE:-ECS}" = "ENV" ]; then
        load_secret PAPERLENS_OBS_ACCESS_KEY_ID PAPERLENS_OBS_ACCESS_KEY_ID_FILE
        load_secret PAPERLENS_OBS_SECRET_ACCESS_KEY PAPERLENS_OBS_SECRET_ACCESS_KEY_FILE
        if [ -n "${PAPERLENS_OBS_SECURITY_TOKEN_FILE:-}" ]; then
            load_secret PAPERLENS_OBS_SECURITY_TOKEN PAPERLENS_OBS_SECURITY_TOKEN_FILE
        fi
    fi
fi

case "${1:-serve}" in
    migrate)
        exec alembic upgrade head
        ;;
    serve)
        exec uvicorn paperlens.main:app --host 0.0.0.0 --port 8000
        ;;
    *)
        echo "unsupported entrypoint command" >&2
        exit 2
        ;;
esac
