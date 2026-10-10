"""Lanza el farmeo multicuenta en segundo plano con las sesiones de runs/accounts/sessions.json.

Uso: .venv/bin/python -B scripts/farmear.py [cuenta ...]   (sin argumentos: las cuentas marcadas FARMEAR)
La app (FARM_BOT_APP.py) detecta el supervisor y muestra el estado; STOP lo detiene.
"""

import json
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent


def main(argv):
    sessions=json.loads((ROOT/'runs/accounts/sessions.json').read_text())
    if argv:accounts=argv
    else:
        try:enabled=json.loads((ROOT/'runs/accounts/enabled.json').read_text())
        except (OSError,ValueError):enabled={}
        accounts=[a for a in sessions if enabled.get(a,True)]
    chosen={a:sessions[a] for a in accounts}
    log=ROOT/f'runs/multi-live/farm-{time.strftime("%Y%m%d-%H%M")}.log';log.parent.mkdir(exist_ok=True)
    with open(log,'a') as out:
        process=subprocess.Popen([sys.executable,'-B','-u','-m','fishing_core.farm_multi','--farm'],cwd=ROOT,
                                 stdin=subprocess.PIPE,stdout=out,stderr=subprocess.STDOUT,text=True,start_new_session=True,
                                 preexec_fn=lambda:signal.signal(signal.SIGINT,signal.SIG_DFL))  # STOP (SIGINT) debe llegar
        process.stdin.write(json.dumps(chosen));process.stdin.close()
    print(process.pid,log,', '.join(chosen))


if __name__=='__main__':main(sys.argv[1:])
