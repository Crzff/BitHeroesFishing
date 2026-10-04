"""Gasta los recursos de los modos activos en el orden de crzf: Quest -> PvP -> World Boss -> Raid -> Expedition -> Trials.

Lee farm_config.json (lo escribe la app). Cada modo termina en Home al quedarse sin
su recurso; una derrota no detiene nada. Cualquier otra parada de seguridad (pantalla
desconocida, F8, pérdida de foco) deja el juego sin confirmar y detiene la cadena.
Cada paso imprime "== <modo>" y al final "<modo>: <resultado>" (la app los muestra).
"""

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
    process,channel,mutex=start_dungeon(focus_window('Steam'),plan)
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
    rest=[('PvP','pvp',lambda:run_pvp(60)),('World Boss','boss',lambda:run_boss(60,config['boss']['difficulty'],config['boss']['boss'],int(config['boss']['tier']))),
          ('Raid','raid',lambda:run_raid(60,config['raid']['raid'],config['raid']['difficulty'])),('Expedition','expedition',lambda:run_expedition(60)),
          ('Trials','trials',lambda:run_trials(60))]
    if runes and any(on[mode] for _,mode,_ in rest):plan.append(('Runas Item Find',lambda:run_runes('ITEM_FIND')))
    plan+=[(name,step) for name,mode,step in rest if on[mode]]
    return plan


def main(argv):
    config=farm_config.load()
    if '--runes' in argv:config['runes']=True
    if '--no-quest' in argv:config['modes']['quest']=False
    results=[]
    for name,step in steps(config):
        print(f'== {name}',flush=True)
        try:
            step();results.append((name,'OK'))
        except KeyboardInterrupt:
            results.append((name,'F8'));break
        except (SafetyStop,RuntimeError,ValueError) as exc:
            results.append((name,str(exc)))
            if not str(exc).startswith('Derrota'):break  # estado del juego no confirmado: no seguir
    for name,result in results:print(f'{name}: {result}',flush=True)


if __name__=='__main__':
    main(sys.argv[1:])
