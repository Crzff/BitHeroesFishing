"""Qué hace el bot: modos activos, dungeon y familiares objetivo. Preferencia local, no se publica."""

import copy
import json

from .protocol import atomic_json
from .telemetry import ROOT

PATH=ROOT/'farm_config.json'
MODES=('quest','pvp','boss','raid','expedition','trials')  # orden de ejecución de crzf
DEFAULT={'modes':{mode:True for mode in MODES},
         'quest':{'dungeon':'Z5D3','difficulty':'Heroic','targets':['Tealk']},
         'boss':{'difficulty':'Heroic'},
         'runes':True}


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
    return config


def save(config,path=None):
    atomic_json(path or PATH,config)
