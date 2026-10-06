"""Gasta los recursos de los modos activos en el orden de crzf: Quest -> PvP -> World Boss -> Raid -> Expedition -> Trials.

Lee farm_config.json (lo escribe la app). Cada modo termina en Home al quedarse sin
su recurso; una derrota no detiene nada. Si el usuario usa el ordenador (modo escritorio)
el modo queda en pausa hasta que el juego recupera el foco; otra parada de seguridad se
reintenta una vez. Un START tras una parada reanuda desde el modo pendiente.
Cada paso imprime "== <modo>" y al final "<modo>: <resultado>" (la app los muestra).
"""

import json
import os
import subprocess
import sys
import time

from . import farm_config, loot
from .telemetry import ROOT
from .control_flow import SafetyStop


def quest(config):
    from .dungeon_catalog import farm_plan
    from .dungeon_runtime import start_dungeon,validate_supported
    from .game_window import focus_window
    q=config['quest']
    plan=validate_supported({**farm_plan(q['dungeon'],q['difficulty'],60,1000),'targets':q.get('targets') or [],
                             'max_gold':int(q.get('max_gold',0))})
    game=None if os.environ.get('FARM_BACKEND')=='gamescope' else focus_window('Steam')
    process,channel,mutex=start_dungeon(game,plan)
    try:
        code=process.wait()
    finally:
        mutex.close()
    if channel.stop_path.exists():  # solo existe si la sesión se detuvo
        raise SafetyStop(channel.stop_path.read_text())
    return code


def steps(config):
    from .boss_runtime import run_boss
    from .expedition_runtime import run_expedition
    from .pvp_runtime import run_pvp
    from .raid_runtime import run_raid
    from .runes_runtime import run_runes
    from .trials_runtime import run_trials
    on=config['modes'];runes=config['runes'];plan=[]
    if on['quest']:
        if runes:plan.append(('Runas captura',lambda:run_runes('CAPTURE')))
        plan.append(('Quest',lambda:quest(config)))
    rest=[('PvP','pvp',lambda:run_pvp(60,int(config['pvp']['opponent']))),('World Boss','boss',lambda:run_boss(60,config['boss']['difficulty'],config['boss']['boss'],int(config['boss']['tier']))),
          ('Raid','raid',lambda:run_raid(60,config['raid']['raid'],config['raid']['difficulty'],int(config['raid'].get('max_gold',250_000)))),('Expedition','expedition',lambda:run_expedition(60)),
          ('Trials','trials',lambda:run_trials(60,int(config['trials']['difficulty'])))]
    if runes and any(on[mode] for _,mode,_ in rest):plan.append(('Runas Item Find',lambda:run_runes('ITEM_FIND')))
    plan+=[(name,step) for name,mode,step in rest if on[mode]]
    return plan


def main(argv):
    from .gamescope import is_gone,relaunch_game
    background=os.environ.get('FARM_BACKEND')=='gamescope'
    os.environ['FARM_LOOT']='1';loot.ENABLED=True  # contador de la app (también en los subprocesos)
    config=farm_config.load()
    if '--runes' in argv:config['runes']=True
    if '--no-quest' in argv:config['modes']['quest']=False
    # El servidor de imagen queda vivo al terminar: cerrar el flujo PipeWire coincidió con caídas de gamescope.
    results=[];server={'proc':start_frame_server() if background else None}
    run_steps(config,results,background,is_gone,relaunch_game,server)
    report(results)


def start_frame_server():
    """Un solo flujo de imagen para toda la sesión (abrir/cerrar flujos coincidió con caídas de gamescope)."""
    import subprocess
    from .gamescope import server_alive
    if server_alive():return None  # ya hay uno: se reutiliza
    proc=subprocess.Popen([sys.executable,'-B','-m','fishing_core.gamescope','serve'],stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL,stdin=subprocess.DEVNULL,start_new_session=True)
    import time
    for _ in range(50):
        if server_alive():break
        time.sleep(.1)
    return proc


def stop_frame_server(server):
    """Solo cuando el juego ya no existe (antes de relanzarlo)."""
    from .gamescope import SHM
    try:
        os.kill(int(open(SHM+'.pid').read()),15)
    except (OSError,ValueError):
        pass
    server['proc']=None


PROGRESS=ROOT/'runs/farm_progress.json'
# Paradas porque el usuario usó el ordenador (modo escritorio): pausa y se reanuda, no se pierde el ciclo.
PAUSES=('perdio el foco','no confirma el cursor','Otra ventana tapa','cambio su identidad')
RESUME_SECONDS=3*3600


def wait_for_game_focus(limit=4*3600):
    """Modo escritorio: espera a que el juego vuelva a tener el foco (el usuario regresó)."""
    import json as _json
    end=time.monotonic()+limit
    while time.monotonic()<end:
        try:
            out=subprocess.run(['niri','msg','--json','focused-window'],capture_output=True,text=True,timeout=5).stdout
            if (_json.loads(out) or {}).get('app_id')=='steam_app_666860':time.sleep(2);return True
        except (OSError,ValueError,subprocess.SubprocessError):pass
        time.sleep(3)
    return False


def load_progress():
    """Modos ya hechos en el ciclo anterior si se detuvo hace poco; si no, ciclo nuevo."""
    try:data=json.loads(PROGRESS.read_text())
    except (OSError,ValueError):return set()
    return set(data.get('done',[])) if time.time()-data.get('stamp',0)<RESUME_SECONDS else set()


def save_progress(done):
    PROGRESS.parent.mkdir(parents=True,exist_ok=True)
    PROGRESS.write_text(json.dumps({'done':sorted(done),'stamp':time.time()}))


def run_steps(config,results,background,is_gone,relaunch_game,server):
    relaunches=0;done=load_progress()
    if done:print(f'== Reanudando: ya hechos {", ".join(sorted(done))}',flush=True)
    for name,step in steps(config):
        if name in done:results.append((name,'OK (ya hecho)'));continue
        print(f'== {name}',flush=True);retried=False;pauses=0
        while True:
            try:
                step();results.append((name,'OK'));done.add(name);save_progress(done);break
            except KeyboardInterrupt:
                results.append((name,'F8'));return
            except (SafetyStop,RuntimeError,ValueError) as exc:
                message=str(exc)
                if 'DISCONNECTED' in message and not retried:
                    retried=True;print(f'== {name} (reconexión)',flush=True);continue
                # Segundo plano: gamescope puede caerse (fallo del driver Vulkan). Relanzar el juego y repetir el modo.
                if background and is_gone(message) and relaunches<3:
                    relaunches+=1;print(f'== {name} (relanzando el juego {relaunches}/3)',flush=True)
                    stop_frame_server(server)
                    if relaunch_game():
                        server['proc']=start_frame_server()
                        continue
                if not background and any(p in message for p in PAUSES) and pauses<50:
                    pauses+=1;print(f'== {name} (en pausa: vuelve a la ventana del juego para seguir)',flush=True)
                    if wait_for_game_focus():
                        print(f'== {name}',flush=True);continue
                if not retried and not message.startswith('Derrota') and (background or not any(p in message for p in PAUSES)):
                    # Un estado no confirmado: un reintento (la run a medias se termina al volver a Home).
                    retried=True;print(f'== {name} (reintento)',flush=True);continue
                results.append((name,message))
                if message.startswith('Derrota'):break
                return  # estado del juego no confirmado: no seguir
            except Exception as exc:  # un fallo inesperado se informa en vez de tumbar el lanzador en silencio
                import traceback;traceback.print_exc();results.append((name,f'{type(exc).__name__}: {exc}'));return
    try:PROGRESS.unlink()  # ciclo completo: el próximo START empieza de nuevo
    except OSError:pass


def report(results):
    for name,result in results:print(f'{name}: {result}',flush=True)


if __name__=='__main__':
    main(sys.argv[1:])
