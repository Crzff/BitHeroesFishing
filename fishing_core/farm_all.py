"""Gasta los recursos de los modos activos en el orden de crzf: Quest -> PvP -> World Boss -> Raid -> Expedition -> Trials.

Lee farm_config.json (lo escribe la app). Cada modo termina en Home al quedarse sin
su recurso; una derrota no detiene nada. Cualquier otra parada de seguridad (pantalla
desconocida, F8, pérdida de foco) deja el juego sin confirmar y detiene la cadena.
Cada paso imprime "== <modo>" y al final "<modo>: <resultado>" (la app los muestra).
"""

import os
import sys

from . import farm_config
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
          ('Raid','raid',lambda:run_raid(60,config['raid']['raid'],config['raid']['difficulty'])),('Expedition','expedition',lambda:run_expedition(60)),
          ('Trials','trials',lambda:run_trials(60,int(config['trials']['difficulty'])))]
    if runes and any(on[mode] for _,mode,_ in rest):plan.append(('Runas Item Find',lambda:run_runes('ITEM_FIND')))
    plan+=[(name,step) for name,mode,step in rest if on[mode]]
    return plan


def main(argv):
    from .gamescope import is_gone,relaunch_game
    background=os.environ.get('FARM_BACKEND')=='gamescope'
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


def run_steps(config,results,background,is_gone,relaunch_game,server):
    relaunches=0
    for name,step in steps(config):
        print(f'== {name}',flush=True)
        for attempt in (1,2,3,4):
            try:
                step();results.append((name,'OK'));break
            except KeyboardInterrupt:
                results.append((name,'F8'));return
            except (SafetyStop,RuntimeError,ValueError) as exc:
                # Desconexión del servidor: el siguiente intento empieza con ensure_home(), que pulsa
                # RECONNECT y cierra las ventanas del arranque. Solo un reintento por modo.
                if attempt==1 and 'DISCONNECTED' in str(exc):print(f'== {name} (reconexión)',flush=True);continue
                # Segundo plano: gamescope puede caerse (fallo del driver Vulkan). Relanzar el juego y repetir el modo.
                if background and is_gone(str(exc)) and relaunches<3:
                    relaunches+=1;print(f'== {name} (relanzando el juego {relaunches}/3)',flush=True)
                    stop_frame_server(server)
                    if relaunch_game():
                        server['proc']=start_frame_server()
                        continue
                results.append((name,str(exc)))
                if str(exc).startswith('Derrota'):break
                return  # estado del juego no confirmado: no seguir


def report(results):
    for name,result in results:print(f'{name}: {result}',flush=True)


if __name__=='__main__':
    main(sys.argv[1:])
