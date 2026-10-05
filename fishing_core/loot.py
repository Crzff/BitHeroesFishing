"""Totales de lo farmeado por la app (runs/loot_totals.json): oro, XP, objetos y materiales
por rareza, familiares capturados y recursos gastados. Los modos suman con add()."""

import json

from .protocol import atomic_json
from .telemetry import ROOT

PATH=ROOT/'runs/loot_totals.json'
RARITIES=('COMMON','RARE','EPIC','LEGENDARY','MYTHIC','SET')
RARITY_NAMES={'COMMON':'COMUN','RARE':'RARO','EPIC':'EPICO','LEGENDARY':'LEGENDARIO','MYTHIC':'MITICO','SET':'DE CONJUNTO'}


def empty():
    return {'gold':0,'xp':0,'items':{},'materials':{},'familiars':{},'spent':{}}


def load(path=None):
    try:data=json.loads((path or PATH).read_text())
    except (OSError,ValueError):return empty()
    out=empty()
    for key,value in data.items():
        if key in ('gold','xp') and type(value) is int:out[key]=value
        elif key in ('items','materials','familiars','spent') and isinstance(value,dict):
            out[key]={str(k):v for k,v in value.items() if type(v) is int and v>=0}
    return out


def add(path=None,**counts):
    """Suma contadores: gold=, xp=, items={rareza:n}, materials={rareza:n}, familiars={nombre:n}, spent={recurso:n}."""
    data=load(path)
    for key,value in counts.items():
        if key in ('gold','xp'):data[key]+=int(value)
        else:
            for name,n in value.items():data[key][name]=data[key].get(name,0)+int(n)
    (path or PATH).parent.mkdir(parents=True,exist_ok=True);atomic_json(path or PATH,data)
    return data


def reset(path=None):
    (path or PATH).parent.mkdir(parents=True,exist_ok=True);atomic_json(path or PATH,empty())
