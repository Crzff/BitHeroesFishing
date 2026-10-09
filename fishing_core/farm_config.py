"""Qué hace el bot: modos activos, dungeon y familiares objetivo. Preferencia local, no se publica."""

import copy
import json

from .protocol import atomic_json
from .telemetry import ROOT
from .accounts import account_id, state_root

PATH=state_root(ROOT)/'farm_config.json'
MODES=('quest','pvp','boss','raid','expedition','trials')  # orden de ejecución de crzf
DEFAULT={'modes':{mode:True for mode in MODES},
         'quest':{'dungeon':'Z5D3','difficulty':'Heroic','targets':['Tealk'],'max_gold':50_000},
         'boss':{'boss':'NETHERWORLD','tier':9,'difficulty':'Heroic'},
         'raid':{'raid':'STORM','difficulty':'Heroic','max_gold':250_000},
         'trials':{'difficulty':499},
         'pvp':{'opponent':4},
         'runes':True,
         'boosts':True,  # sin ningún boost activo: consumir los 4 Minor (crzf)
         'background':False}  # True: juego en gamescope (JUEGO_SEGUNDO_PLANO.sh), sin foco


def load(path=None):
    path=path or PATH;config=copy.deepcopy(DEFAULT)
    if account_id() is not None:
        config['quest']['max_gold']=0;config['raid']['max_gold']=0
    try:
        saved=json.loads(path.read_text())
    except (OSError,ValueError):
        return config
    if isinstance(saved,dict):
        for key,value in saved.items():
            if isinstance(config.get(key),dict) and isinstance(value,dict):config[key].update(value)
            elif key in config:config[key]=value
    return config


def save(config,path=None):
    atomic_json(path or PATH,config)
