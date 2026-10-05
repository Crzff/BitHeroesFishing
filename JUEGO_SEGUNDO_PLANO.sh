#!/bin/sh
# Abre Steam y Bit Heroes dentro de gamescope sin ventana: el bot juega en una
# pantalla virtual de 1920x1080 y tú puedes usar el ordenador con normalidad.
# Para ver el juego, cierra este Steam (steam -shutdown) y ábrelo como siempre.
set -eu
if pgrep -x steam >/dev/null; then
    echo "Steam ya está abierto: ciérralo antes (steam -shutdown)." >&2
    exit 1
fi
exec gamescope --backend headless -w 1920 -h 1080 -W 1920 -H 1080 -- steam -silent steam://rungameid/666860
