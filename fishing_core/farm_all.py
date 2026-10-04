"""Gasta todos los recursos en el orden de crzf: Quest -> PvP -> World Boss -> Raid -> Expedition -> Trials.

Cada modo termina en Home al quedarse sin su recurso. Cualquier parada de seguridad
(pantalla desconocida, derrota en Raid/WB, F8, pérdida de foco) deja el juego en un
estado no confirmado y detiene toda la cadena. Las runas (experimental) solo con --runes.
"""

import sys

from .control_flow import SafetyStop

QUEST_PLAN=('Z5D3','Heroic',60,1000,'Tealk')  # Tealk: Heroic -> Hard -> Normal con RERUN


def quest():
    from .dungeon_catalog import farm_plan
    from .dungeon_runtime import start_dungeon,validate_supported
    from .game_window import focus_window
    plan=validate_supported(farm_plan(*QUEST_PLAN))
    process,channel,mutex=start_dungeon(focus_window('Steam'),plan)
    try:
        code=process.wait()
    finally:
        mutex.close()
    if channel.stop_path.exists():  # solo existe si la sesión se detuvo
        raise SafetyStop(channel.stop_path.read_text())
    return code


def steps(runes):
    from .boss_runtime import run_boss
    from .expedition_runtime import run_expedition
    from .pvp_runtime import run_pvp
    from .raid_runtime import run_raid
    from .runes_runtime import run_runes
    from .trials_runtime import run_trials
    plan=[]
    if runes:plan.append(('Runas captura',lambda:run_runes('CAPTURE')))
    if '--no-quest' not in sys.argv:plan.append(('Quest',quest))
    if runes:plan.append(('Runas Item Find',lambda:run_runes('ITEM_FIND')))
    plan+=[('PvP',lambda:run_pvp(60)),('World Boss',lambda:run_boss(60,'Heroic')),('Raid',lambda:run_raid(60)),
           ('Expedition',lambda:run_expedition(60)),('Trials',lambda:run_trials(60))]
    return plan


def main(argv):
    results=[]
    for name,step in steps('--runes' in argv):
        print(f'== {name}',flush=True)
        try:
            step();results.append((name,'OK'))
        except KeyboardInterrupt:
            results.append((name,'F8'));break
        except (SafetyStop,RuntimeError,ValueError) as exc:
            results.append((name,str(exc)))
            # Una derrota en Raid/WB se cierra con TOWN y vuelve a Home: termina solo ese modo.
            if not str(exc).startswith('Derrota'):break  # estado del juego no confirmado: no seguir
    for name,result in results:print(f'{name}: {result}',flush=True)


if __name__=='__main__':
    main(sys.argv[1:])
