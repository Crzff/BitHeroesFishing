#!/usr/bin/env bash
# Puente Claude -> Codex con escritura limitada al proyecto (workspace-write, sin red).
# Uso: scripts/claude_codex_write.sh <id-tarea> < tarea.txt
# Límites: una tarea a la vez (lock), 15 min por llamada, salida completa en runs/codex/<id>.log.
set -euo pipefail

project="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
task="${1:?falta el id de la tarea}"
[[ "$task" =~ ^[A-Za-z0-9._-]{1,64}$ ]] || { echo "id de tarea inválido" >&2; exit 2; }
mkdir -p -- "$project/runs/codex"
log="$project/runs/codex/$task.log"
last="$project/runs/codex/$task.last.md"

# Un solo Codex escribiendo a la vez.
exec 9>"$project/runs/codex/.lock"
flock -n 9 || { echo "Ya hay otra tarea de Codex en marcha" >&2; exit 3; }

prompt="$(cat)"
rules='Reglas fijas (proyecto BitHeroesFishing): trabaja solo dentro de este repositorio; respeta AGENTS.md
salvo que aquí se te permite editar código y pruebas. No ejecutes el bot, el juego, Brave, Steam ni
gamescope, y no envíes input; solo pruebas offline con .venv/bin/python -B -m unittest. No borres ni
reviertas archivos ajenos a la tarea, no hagas commits, no instales paquetes ni uses red. Cambios mínimos,
estilo del código existente. Al terminar responde en español: archivos tocados, qué cambiaste, comandos
de prueba y su resultado exacto, y problemas pendientes.'

status=0
printf '%s\n\nTAREA %s:\n%s\n' "$rules" "$task" "$prompt" | \
  timeout 900 env -u DISPLAY -u WAYLAND_DISPLAY -u CODEX_API_KEY -u OPENAI_API_KEY \
    /home/crzf/.local/bin/codex exec --sandbox workspace-write --ephemeral \
    --cd "$project" -o "$last" - >"$log" 2>&1 || status=$?
cat -- "$last" 2>/dev/null || tail -n 30 -- "$log"
exit "$status"
