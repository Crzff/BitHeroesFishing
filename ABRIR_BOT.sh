#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
exec .venv/bin/python -B FARM_BOT_APP.py "$@"
