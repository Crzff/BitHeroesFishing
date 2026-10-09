"""Proceso exclusivo de dungeon; importar no inicia el juego."""

from fishing_core.dungeon_runtime import run_dungeon
import sys

if __name__=='__main__':
    if sys.argv[1:] not in ([],['--stop-check']):raise SystemExit('Argumentos no válidos')
    run_dungeon(read_only=sys.argv[1:]==['--stop-check'])
