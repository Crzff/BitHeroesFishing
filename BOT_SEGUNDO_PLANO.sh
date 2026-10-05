#!/bin/sh
# Todo en uno: cierra Steam, abre Bit Heroes en segundo plano (gamescope) y la app del bot.
set -u
cd -- "$(dirname -- "$0")"
if ! pgrep -f "gamescope --backend headless" >/dev/null; then
    if pgrep -x steam >/dev/null; then
        notify-send "Bit Heroes Bot" "Cerrando Steam para abrir el juego en segundo plano..." 2>/dev/null
        steam -shutdown
        for _ in $(seq 1 60); do pgrep -x steam >/dev/null || break; sleep 1; done
        sleep 3
    fi
    setsid ./JUEGO_SEGUNDO_PLANO.sh >/dev/null 2>&1 < /dev/null &
    notify-send "Bit Heroes Bot" "Abriendo el juego en segundo plano (1-2 minutos)..." 2>/dev/null
    sleep 90
fi
FARM_BACKEND=gamescope exec .venv/bin/python -B FARM_BOT_APP.py 2>>"${XDG_RUNTIME_DIR:-/tmp}/bitheroes-bot.log"
