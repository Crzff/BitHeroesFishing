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
from .accounts import account_id, runs_root


def quest_plan(config,single=False):
    from .dungeon_catalog import farm_plan
    from .dungeon_runtime import validate_supported
    q=config['quest']
    return validate_supported({**farm_plan(q['dungeon'],'Normal' if single else q['difficulty'],1 if single else 60,10 if single else 1000),
                               'targets':[] if single else q.get('targets') or [],'max_gold':0 if single else int(q.get('max_gold',0))})


def check_supervisor():
    supervisor=os.environ.get('FARM_SUPERVISOR_PID')
    if supervisor and str(os.getppid())!=supervisor:
        raise SafetyStop('El supervisor terminó; no se continúa la dungeon')
    return supervisor


def quest(config,single=False,read_only=False):
    from .dungeon_runtime import start_dungeon
    from .game_window import focus_window
    from .processes import close_children
    plan=quest_plan(config,single)
    supervisor=check_supervisor()
    game=None if os.environ.get('FARM_BACKEND') in ('gamescope','cdp') else focus_window('Steam')
    process,channel,mutex=start_dungeon(game,plan,read_only=True) if read_only else start_dungeon(game,plan)
    try:
        while True:
            check_supervisor()
            try:
                code=process.wait(timeout=.2 if supervisor else None);break
            except subprocess.TimeoutExpired:continue
    except BaseException:
        close_children((process,),channel)
        raise
    finally:
        mutex.close()
    if channel.stop_path.exists():  # solo existe si la sesión se detuvo
        raise SafetyStop(channel.stop_path.read_text())
    if code:raise SafetyStop(f'El motor de dungeon terminó con código {code}')
    return code


WEEKLY_EXPEDITION='GVG'


def steps(config):
    from .boss_runtime import run_boss
    from .expedition_runtime import run_expedition
    from .gvg_runtime import run_gvg
    from .pvp_runtime import run_pvp
    from .raid_runtime import run_raid
    from .runes_runtime import run_runes
    from .trials_runtime import run_trials
    on=config['modes'];runes=config['runes'];plan=[]
    if config.get('boosts'):
        from .boosts_runtime import run_boosts
        plan.append(('Boosts',run_boosts))
    if on['quest']:
        if runes:plan.append(('Runas captura',lambda:run_runes('CAPTURE')))
        plan.append(('Quest',lambda:quest(config)))
    rest=[('PvP','pvp',lambda:run_pvp(60,int(config['pvp']['opponent']))),('World Boss','boss',lambda:run_boss(60,config['boss']['difficulty'],config['boss']['boss'],int(config['boss']['tier']))),
          ('Raid','raid',lambda:run_raid(60,config['raid']['raid'],config['raid']['difficulty'],int(config['raid'].get('max_gold',250_000)))),
          ('GvG' if WEEKLY_EXPEDITION=='GVG' else 'Expedition','expedition',lambda:run_gvg(60) if WEEKLY_EXPEDITION=='GVG' else run_expedition(60)),
          ('Trials','trials',lambda:run_trials(60,int(config['trials']['difficulty'])))]
    if runes and any(on[mode] for _,mode,_ in rest):plan.append(('Runas Item Find',lambda:run_runes('ITEM_FIND')))
    plan+=[(name,step) for name,mode,step in rest if on[mode]]
    return plan


def main(argv):
    from .gamescope import is_gone,relaunch_game,require_calibrated_client
    from .processes import Mutex
    read_only='--stop-check' in argv
    if read_only and argv!=['--stop-check']:raise ValueError('Observación no acepta modos de farmeo')
    require_calibrated_client(read_only=True) if read_only else require_calibrated_client()
    single='--single-dungeon' in argv or read_only
    if os.environ.get('FARM_SINGLE_DUNGEON')=='1' and argv!=['--single-dungeon']:
        raise ValueError('Un worker de prueba limitada solo puede ejecutar --single-dungeon')
    if single and (argv not in (['--single-dungeon'],['--stop-check']) or account_id() is None):
        raise ValueError('Prueba de una dungeon requiere una cuenta explícita y ningún otro modo')
    lock=Mutex('FARM_ALL')
    try:
        background=os.environ.get('FARM_BACKEND') in ('gamescope','cdp')
        os.environ['FARM_LOOT']='1';loot.ENABLED=True  # contador de la app (también en los subprocesos)
        config=farm_config.load()
        if single:
            quest_plan(config,single=True)  # Rechazar rutas incompatibles antes de abrir la captura.
            check_supervisor()
            if read_only:
                if os.environ.get('FARM_BACKEND')!='cdp':start_frame_server(read_only=True)
                quest(config,single=True,read_only=True)
            else:
                if os.environ.get('FARM_BACKEND')!='cdp':start_frame_server()
                quest(config,single=True)
            report([('Quest','OK (prueba limitada)')]);return
        if '--runes' in argv:config['runes']=True
        if '--no-quest' in argv:config['modes']['quest']=False
        # El servidor de imagen queda vivo al terminar: cerrar el flujo PipeWire coincidió con caídas de gamescope.
        results=[];server={'proc':start_frame_server() if os.environ.get('FARM_BACKEND')=='gamescope' else None}
        run_steps(config,results,background,is_gone,relaunch_game,server)
        report(results)
        if any(not result.startswith('OK') for _,result in results):raise SystemExit(1)
    finally:lock.close()


def start_frame_server(read_only=False):
    """Un solo flujo de imagen para toda la sesión (abrir/cerrar flujos coincidió con caídas de gamescope)."""
    import subprocess
    from .gamescope import server_alive,steam_frame_source
    if steam_frame_source() is not None:return None
    if server_alive():return None  # ya hay uno: se reutiliza
    proc=subprocess.Popen([sys.executable,'-B','-m','fishing_core.gamescope','serve'],stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL,stdin=subprocess.DEVNULL,start_new_session=True)
    import time
    for _ in range(50):
        if server_alive():return proc
        if proc.poll() is not None:raise RuntimeError('El servidor de imagen no pudo iniciar')
        time.sleep(.1)
    proc.terminate()
    try:proc.wait(timeout=1)
    except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=1)
    raise RuntimeError('El servidor de imagen no confirmó el arranque')


def stop_frame_server(server):
    """Solo cuando el juego ya no existe (antes de relanzarlo)."""
    from .gamescope import SHM
    try:
        os.kill(int(open(SHM+'.pid').read()),15)
    except (OSError,ValueError):
        pass
    server['proc']=None


PROGRESS=runs_root(ROOT)/'farm_progress.json'
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
        print(f'== {name}',flush=True);retried=False;pauses=0;sessions=0
        while True:
            try:
                step();results.append((name,'OK'));done.add(name);save_progress(done);break
            except KeyboardInterrupt:
                results.append((name,'F8'));return
            except (SafetyStop,RuntimeError,ValueError) as exc:
                message=str(exc)
                if 'Límite de sesión' in message and sessions<20:
                    # Cada proceso de modo dura como mucho 1 h; con muchos recursos se abre otra sesión.
                    sessions+=1;print(f'== {name} (sesión {sessions+1})',flush=True);continue
                if account_id() in ('personal','perfil-1') and ('Cambió la identidad' in message or 'terminó' in message or retried):
                    # Identidad/proceso cambiados: nunca otra guarda. Los endpoints están fijados por el supervisor,
                    # así que el único reintento genérico solo vuelve a aceptar el mismo Brave (fallos CDP momentáneos).
                    results.append((name,message));return
                if 'DISCONNECTED' in message and not retried:
                    retried=True;print(f'== {name} (reconexión)',flush=True);continue
                # Segundo plano: gamescope puede caerse (fallo del driver Vulkan). Relanzar el juego y repetir el modo.
                if background and account_id() is None and is_gone(message) and relaunches<3:
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
