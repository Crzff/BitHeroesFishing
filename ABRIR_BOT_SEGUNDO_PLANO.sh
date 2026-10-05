#!/bin/sh
# App del Farm Bot usando el juego de JUEGO_SEGUNDO_PLANO.sh (no necesita el foco).
set -eu
cd -- "$(dirname -- "$0")"
FARM_BACKEND=gamescope exec .venv/bin/python -B FARM_BOT_APP.py "$@"
