#!/bin/sh
# Cierra el juego en segundo plano y abre Bit Heroes normal en Steam.
set -u
pkill -f "fishing_core.gamescope serve" 2>/dev/null
if pgrep -x steam >/dev/null; then
    steam -shutdown
    for _ in $(seq 1 60); do pgrep -x steam >/dev/null || break; sleep 1; done
fi
pkill -f "gamescope --backend headless" 2>/dev/null
sleep 3
setsid steam steam://rungameid/666860 >/dev/null 2>&1 < /dev/null &
