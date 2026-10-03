#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
runtime="${XDG_RUNTIME_DIR:-/tmp/opencode/bitheroes-$(id -u)}"
mkdir -p -m 700 "$runtime"
exec 9>"$runtime/bitheroes-LAUNCHER.lock"
flock -n 9 || { echo "Deten el bot antes de instalar; no se reemplaza una instalacion activa." >&2; exit 1; }
command -v uv >/dev/null || { echo "Falta uv para instalar Python localmente." >&2; exit 1; }
command -v cc >/dev/null || { echo "Falta un compilador C (cc)." >&2; exit 1; }
if [ ! -x .venv/bin/python ]; then
    uv python install 3.13
    uv venv --python 3.13 .venv
fi
.venv/bin/python -B -c 'import sys, tkinter; assert sys.version_info[:2] == (3,13), "Se requiere Python 3.13 con Tk; no se reemplaza un entorno existente"'
uv pip install --python .venv/bin/python -r requirements-linux.txt
cc -shared -fPIC -O2 -Wall -Wextra -Werror fishing_core/linux_pointer.c fishing_core/linux_capture.c \
    -o .venv/lib/bitheroes-pointer.so.tmp -lwayland-client
mv .venv/lib/bitheroes-pointer.so.tmp .venv/lib/bitheroes-pointer.so
uv pip check --python .venv/bin/python
echo "Instalacion Linux lista. Abre ABRIR_BOT.sh; abrir el panel no inicia pesca."
