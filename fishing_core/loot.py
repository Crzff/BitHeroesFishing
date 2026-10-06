"""Totales de lo farmeado por la app (runs/loot_totals.json): oro, XP, objetos y materiales
por rareza, familiares capturados y recursos gastados. Los modos suman con add()."""

import json
import os

from .protocol import atomic_json
from .telemetry import ROOT

PATH=ROOT/'runs/loot_totals.json'
ALBUM=ROOT/'runs/loot_album'
KINDS=ROOT/'runs/loot_kinds.json'  # tipo leído en la descripción de cada icono (se consulta una vez)
ENABLED=os.environ.get('FARM_LOOT')=='1'  # solo farm_all lo activa: pruebas y runners sueltos no tocan los totales
ORDER=('MYTHIC','SET','LEGENDARY','EPIC','RARE','COMMON')
RARITIES=('COMMON','RARE','EPIC','LEGENDARY','MYTHIC','SET')
RARITY_NAMES={'COMMON':'COMUN','RARE':'RARO','EPIC':'EPICO','LEGENDARY':'LEGENDARIO','MYTHIC':'MITICO','SET':'DE CONJUNTO'}


def empty():
    return {'gold':0,'xp':0,'items':{},'materials':{},'consumables':{},'familiars':{},'spent':{},'album':{}}


def load(path=None):
    try:data=json.loads((path or PATH).read_text())
    except (OSError,ValueError):return empty()
    out=empty()
    for key,value in data.items():
        if key in ('gold','xp') and type(value) is int:out[key]=value
        elif key in ('items','materials','consumables','familiars','spent') and isinstance(value,dict):
            out[key]={str(k):v for k,v in value.items() if type(v) is int and v>=0}
        elif key=='album' and isinstance(value,dict):
            out[key]={str(k):v for k,v in value.items() if isinstance(v,dict) and v.get('rarity') in RARITIES and
                      v.get('kind') in ('ITEM','MATERIAL','CONSUMABLE') and type(v.get('count')) is int}
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


def icon_key(icon,rarity):
    """Identidad de un icono del botín (sin la franja de la cantidad)."""
    import hashlib
    import cv2
    small=cv2.resize(icon[40:],(16,10),interpolation=cv2.INTER_AREA)//32
    return hashlib.md5(small.tobytes()+rarity.encode()).hexdigest()[:12]


def known_kind(key,path=None):
    try:return json.loads((path or KINDS).read_text()).get(key)
    except (OSError,ValueError,AttributeError):return None


def remember_kind(key,kind,path=None):
    try:data=json.loads((path or KINDS).read_text())
    except (OSError,ValueError):data={}
    data[key]=kind;(path or KINDS).parent.mkdir(parents=True,exist_ok=True);atomic_json(path or KINDS,data)


def record(cells,path=None,album=None):
    """Suma las casillas de un LOOT RECAP y guarda cada icono nuevo en el álbum (runs/loot_album)."""
    if not ENABLED or not cells:return None
    import hashlib
    import cv2
    album=album or ALBUM;album.mkdir(parents=True,exist_ok=True)
    counts={'gold':0,'xp':0,'items':{},'materials':{},'consumables':{},'album':{}}
    for cell in cells:
        kind,rarity,amount=cell['kind'],cell['rarity'],cell['amount']
        if kind in ('GOLD','XP'):counts[kind.lower()]+=amount;continue
        key=icon_key(cell['icon'],rarity)
        if not (album/f'{key}.png').exists():cv2.imwrite(str(album/f'{key}.png'),cell['icon'])
        group={'ITEM':'items','CONSUMABLE':'consumables'}.get(kind,'materials');counts[group][rarity]=counts[group].get(rarity,0)+amount
        entry=counts['album'].setdefault(key,{'kind':kind,'rarity':rarity,'count':0});entry['count']+=amount
    return add(path,**counts)
