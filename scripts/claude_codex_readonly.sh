#!/usr/bin/env bash
set -euo pipefail

project="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
progress="$(mktemp)"
trap 'rm -f -- "$progress"' EXIT

# ponytail: solo resumen al acertar, últimas 12 líneas al fallar; CLI directo para diagnóstico completo.
if env -u DISPLAY -u WAYLAND_DISPLAY -u XDG_RUNTIME_DIR \
    -u CODEX_API_KEY -u OPENAI_API_KEY \
    /home/crzf/.local/bin/codex exec --sandbox read-only --ephemeral \
    --cd "$project" - 2>"$progress"; then
    exit 0
else
    status=$?
    tail -n 12 -- "$progress" >&2
    exit "$status"
fi
