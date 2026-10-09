"""F8 nativo de niri -> SIGINT a workers propios; sin leer teclas ni cerrar juegos."""
import os
from pathlib import Path
import signal
import sys
import time

ROOT=Path(__file__).resolve().parent.parent
WORKERS={'FARM_DUNGEON_PROCESS.py','CATCH_FAST_PROCESS_V6_FINAL.py','FISHING_CONTROL_PROCESS.py','INICIAR_TODO.py'}
PYTHONS={sys.executable,str(Path(sys.executable).resolve()),str(ROOT/'.venv/bin/python')}


def is_worker(argv,cwd,uid):
    if uid!=os.getuid() or cwd!=ROOT or not argv or argv[0] not in PYTHONS:return False
    args=list(argv[1:])
    while args and args[0] in ('-B','-u'):args.pop(0)
    if not args:return False
    if args[0]=='-m':
        return args[1:2] in (['fishing_core.farm_all'],['fishing_core.farm_multi']) or args[1:]==['fishing_core.global_stop','--probe']
    path=Path(args[0])
    if not path.is_absolute():path=cwd/path
    if path.parent==ROOT and path.name in WORKERS:return True
    return path==ROOT/'fishing_core/global_stop.py' and args[1:]==['--probe']


def stop_workers(proc=Path('/proc')):
    """pidfd liga la señal al proceso comprobado, no a un PID reciclado."""
    stopped=0
    for entry in proc.iterdir():
        if not entry.name.isdecimal():continue
        fd=None
        try:
            fd=os.pidfd_open(int(entry.name))
            uid=entry.stat().st_uid
            if uid!=os.getuid():continue
            cwd=(entry/'cwd').resolve(strict=True)
            if cwd!=ROOT:continue  # No leer argumentos de otras aplicaciones.
            with (entry/'cmdline').open('rb') as stream:raw=stream.read(65537)
            if len(raw)>65536 or not raw.endswith(b'\0'):continue
            argv=[os.fsdecode(arg) for arg in raw[:-1].split(b'\0')]
            if is_worker(argv,cwd,uid):signal.pidfd_send_signal(fd,signal.SIGINT);stopped+=1
        except (OSError,ValueError):continue  # Salió durante la comprobación; no ampliar la selección.
        finally:
            if fd is not None:os.close(fd)
    return stopped


if __name__=='__main__':
    if sys.platform!='linux':raise SystemExit('Parada global disponible solo en Linux/niri')
    if sys.argv[1:]==['--probe']:
        try:
            print('PROBE_READY',flush=True)
            time.sleep(900)
            raise SystemExit('F8 no detectado en 15 minutos')
        except KeyboardInterrupt:print('PROBE_STOPPED',flush=True)
    elif sys.argv[1:]:raise SystemExit('Argumentos no válidos')
    else:print(f'Parada solicitada a {stop_workers()} workers del bot',flush=True)
