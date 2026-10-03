"""Catálogo local puro: elegir una ruta no confirma que la cuenta pueda entrar."""

import json
from pathlib import Path
import unicodedata

DATA=json.loads((Path(__file__).resolve().parent.parent/'assets/dungeons.json').read_text())
if DATA.get('schema')!=1:raise ValueError('Versión de catálogo no compatible')
CATALOG=DATA['dungeons']
FAMILIARS=DATA['familiars']
BY_ID={item['id']:item for item in CATALOG}
if len(BY_ID)!=len(CATALOG) or any(not set(ids)<=BY_ID.keys() for ids in FAMILIARS.values()):
    raise ValueError('Catálogo de dungeons inconsistente')


def normalize(text):
    return unicodedata.normalize('NFKC',text).strip().casefold().replace('’',"'").replace('‘',"'")


def dungeon(identifier):
    try:return BY_ID[identifier]
    except KeyError as exc:raise ValueError('Dungeon desconocida; no se sustituye la ruta') from exc


def routes_for(name):
    key=normalize(name)
    for familiar,ids in FAMILIARS.items():
        if normalize(familiar)==key:return [dungeon(identifier) for identifier in ids]
    return []


def farm_plan(identifier,difficulty,runs,energy_limit,target=''):
    item=dungeon(identifier)
    if difficulty not in (('Special',) if item['special'] else ('Normal','Hard','Heroic')):
        raise ValueError('Dificultad no compatible con la dungeon')
    if type(runs) is not int or not 1<=runs<=100 or type(energy_limit) is not int or not 1<=energy_limit<=10000:
        raise ValueError('Usa 1–100 runs y un límite positivo de energía')
    target=target.strip()
    if target and item not in routes_for(target):
        raise ValueError('El familiar no pertenece a esta ruta o necesita fusión')
    return {'dungeon_id':identifier,'difficulty':difficulty,'runs':runs,'energy_limit':energy_limit,'target':target}
