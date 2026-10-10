"""Abre los clientes en segundo plano (gamescope headless) y escribe runs/accounts/sessions.json.

Uso tras reiniciar el PC: .venv/bin/python -B scripts/abrir_clientes.py
- Cuentas de navegador del registro: Brave en su propio gamescope (perfil runs/accounts/<id>/brave-data).
- Steam: si no está abierto, JUEGO_SEGUNDO_PLANO.sh; espera la ventana del juego y su nodo PipeWire.
No farmea ni pulsa nada en el juego. El sessions.json anterior se guarda como .bak.
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from fishing_core.accounts import browser_accounts,steam_account  # noqa: E402


def gamescope_serials():
    out=subprocess.run(['pw-cli','ls','Node'],capture_output=True,text=True,timeout=10).stdout
    serials=[];block={}
    for line in out.splitlines()+['id end']:
        line=line.strip()
        if line.startswith('id '):
            if block.get('node.name')=='"gamescope"' and block.get('media.class')=='"Video/Source"':
                serials.append(block.get('object.serial','').strip('"'))
            block={}
        elif ' = ' in line:
            key,value=line.split(' = ',1);block[key]=value
    return serials


def open_browser(account):
    env={**os.environ,'FARM_ACCOUNT':account,'FARM_BACKEND':'gamescope'}
    code=("import json,os,sys;from fishing_core.brave import launch_brave;p,e=launch_brave();"
          "print(json.dumps(e))")
    out=subprocess.run([sys.executable,'-B','-c',code],cwd=ROOT,env=env,capture_output=True,text=True,timeout=240)
    if out.returncode:raise RuntimeError(f'{account}: '+(out.stderr.strip().splitlines() or ['sin detalle'])[-1])
    return json.loads(out.stdout.strip().splitlines()[-1])


def open_steam(known_displays,known_serials,timeout=300):
    from Xlib import display
    from fishing_core.gamescope import window_of
    if subprocess.run(['pgrep','-x','steam'],capture_output=True).returncode!=0:
        subprocess.Popen([str(ROOT/'JUEGO_SEGUNDO_PLANO.sh')],cwd=ROOT,stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        for n in range(10):
            name=f':{n}'
            if name in known_displays:continue
            try:d=display.Display(name)
            except Exception:continue
            try:found=window_of(d) is not None
            except Exception:found=False
            finally:d.close()
            if not found:continue
            new=[s for s in gamescope_serials() if s not in known_serials]
            if len(new)==1:
                time.sleep(60)  # la ventana aparece con el juego aún cargando (en vivo: farmeo parado en la carga)
                return {'FARM_GAMESCOPE_DISPLAY':name,'FARM_GAMESCOPE_SERIAL':new[0]}
        time.sleep(5)
    raise RuntimeError('Steam: no apareció la ventana del juego en gamescope (¿Steam abierto fuera de gamescope?)')


def main():
    sessions={}
    for account in browser_accounts():
        sessions[account]=open_browser(account);print(account,'listo',sessions[account]['FARM_GAMESCOPE_DISPLAY'],flush=True)
    steam=steam_account()
    if steam:
        known={s['FARM_GAMESCOPE_DISPLAY'] for s in sessions.values()}
        serials={s['FARM_GAMESCOPE_SERIAL'] for s in sessions.values()}
        sessions[steam]=open_steam(known,serials);print(steam,'listo',sessions[steam]['FARM_GAMESCOPE_DISPLAY'],flush=True)
    path=ROOT/'runs/accounts/sessions.json'
    if path.exists():shutil.copy2(path,path.with_suffix('.json.bak'))
    from fishing_core.protocol import atomic_json
    atomic_json(path,sessions)
    print('sessions.json escrito:',', '.join(sessions))


if __name__=='__main__':main()
