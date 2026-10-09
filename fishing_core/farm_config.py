"""Qué hace el bot: modos activos, dungeon y familiares objetivo. Preferencia local, no se publica."""

import copy
import json

from .protocol import atomic_json
from .telemetry import ROOT
from .accounts import state_root

PATH=state_root(ROOT)/'farm_config.json'
MODES=('quest','pvp','boss','raid','expedition','trials')  # orden de ejecución de crzf
DEFAULT={'modes':{mode:True for mode in MODES},
         'quest':{'dungeon':'Z5D3','difficulty':'Heroic','targets':[]},
         'boss':{'boss':'NETHERWORLD','tier':9,'difficulty':'Heroic'},
         'raid':{'raid':'STORM','difficulty':'Heroic'},
         'trials':{'difficulty':499},
         'pvp':{'opponent':4},
         'runes':True,
         'diagnostic_screenshots':True,  # diagnóstico local de crzf, sin barra superior
         'boosts':True,  # sin ningún boost activo: consumir los 4 Minor (crzf)
         'boosts_buy':True,  # comprar con oro los Minor ausentes (crzf)
         'background':False}  # True: juego en gamescope (JUEGO_SEGUNDO_PLANO.sh), sin foco


def load(path=None):
    path=path or PATH;config=copy.deepcopy(DEFAULT)
    try:
        saved=json.loads(path.read_text())
    except (OSError,ValueError):
        return config
    if isinstance(saved,dict):
        for key,value in saved.items():
            if isinstance(config.get(key),dict) and isinstance(value,dict):config[key].update(value)
            elif key in config:config[key]=value
    for mode in ('quest','raid'):
        if isinstance(config.get(mode),dict):config[mode].pop('max_gold',None)
    return config


def save(config,path=None):
    atomic_json(path or PATH,config)
