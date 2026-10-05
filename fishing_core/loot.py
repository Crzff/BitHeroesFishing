"""Totales de lo farmeado por la app (runs/loot_totals.json): oro, XP, objetos y materiales
por rareza, familiares capturados y recursos gastados. Los modos suman con add()."""

import json
import os

from .protocol import atomic_json
from .telemetry import ROOT

PATH=ROOT/'runs/loot_totals.json'
ALBUM=ROOT/'runs/loot_album'
ENABLED=os.environ.get('FARM_LOOT')=='1'  # solo farm_all lo activa: pruebas y runners sueltos no tocan los totales
ORDER=('MYTHIC','SET','LEGENDARY','EPIC','RARE','COMMON')
RARITIES=('COMMON','RARE','EPIC','LEGENDARY','MYTHIC','SET')
RARITY_NAMES={'COMMON':'COMUN','RARE':'RARO','EPIC':'EPICO','LEGENDARY':'LEGENDARIO','MYTHIC':'MITICO','SET':'DE CONJUNTO'}


def empty():
    return {'gold':0,'xp':0,'items':{},'materials':{},'familiars':{},'spent':{},'album':{}}


def load(path=None):
    try:data=json.loads((path or PATH).read_text())
    except (OSError,ValueError):return empty()
    out=empty()
    for key,value in data.items():
        if key in ('gold','xp') and type(value) is int:out[key]=value
        elif key in ('items','materials','familiars','spent') and isinstance(value,dict):
            out[key]={str(k):v for k,v in value.items() if type(v) is int and v>=0}
        elif key=='album' and isinstance(value,dict):
            out[key]={str(k):v for k,v in value.items() if isinstance(v,dict) and v.get('rarity') in RARITIES and
                      v.get('kind') in ('ITEM','MATERIAL') and type(v.get('count')) is int}
    return out


def add(path=None,**counts):
    """Suma contadores: gold=, xp=, items={rareza:n}, materials={rareza:n}, familiars={nombre:n}, spent={recurso:n}."""
    data=load(path)
    for key,value in counts.items():
        if key in ('gold','xp'):data[key]+=int(value)
        elif key=='album':
            for name,entry in value.items():
                old=data['album'].get(name,{**entry,'count':0});data['album'][name]={**entry,'count':old['count']+entry['count']}
        else:
            for name,n in value.items():data[key][name]=data[key].get(name,0)+int(n)
    (path or PATH).parent.mkdir(parents=True,exist_ok=True);atomic_json(path or PATH,data)
    return data


def reset(path=None):
    (path or PATH).parent.mkdir(parents=True,exist_ok=True);atomic_json(path or PATH,empty())


def spend(resource,amount):
    if ENABLED:add(spent={resource.lower():amount})


def familiar(name):
    if ENABLED:add(familiars={name:1})


def record(cells,path=None,album=None):
    """Suma las casillas de un LOOT RECAP y guarda cada icono nuevo en el álbum (runs/loot_album)."""
    if not ENABLED or not cells:return None
    import hashlib
    import cv2
    album=album or ALBUM;album.mkdir(parents=True,exist_ok=True)
    counts={'gold':0,'xp':0,'items':{},'materials':{},'album':{}}
    for cell in cells:
        kind,rarity,amount=cell['kind'],cell['rarity'],cell['amount']
        if kind in ('GOLD','XP'):counts[kind.lower()]+=amount;continue
        small=cv2.resize(cell['icon'][40:],(16,10),interpolation=cv2.INTER_AREA)//32  # sin la franja de la cantidad
        key=hashlib.md5(small.tobytes()+rarity.encode()).hexdigest()[:12]
        if not (album/f'{key}.png').exists():cv2.imwrite(str(album/f'{key}.png'),cell['icon'])
        group='items' if kind=='ITEM' else 'materials';counts[group][rarity]=counts[group].get(rarity,0)+amount
        entry=counts['album'].setdefault(key,{'kind':kind,'rarity':rarity,'count':0});entry['count']+=amount
    return add(path,**counts)
