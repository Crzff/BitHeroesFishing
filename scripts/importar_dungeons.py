"""Genera el catálogo desde una copia Markdown de la wiki; nunca toca el juego."""

import argparse
import hashlib
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from fishing_core.protocol import atomic_json

# Nombres y orden de https://bit-heroes.fandom.com/wiki/Zones (2026-10-02).
# Z7-9 tienen dos dungeons normales, no tres. La última de cada zona es especial.
ZONES=[
    ("Bit Valley","Grimz Crossing|Dryad's Heart|Lord Cerulean's Tomb|Grim Valley"),
    ("Wintermarsh","Yeti's Tundra|Blubber's Gutter|Gemm's Cell|Deathmarsh"),
    ("Lakehaven","Nosdoodoo Wasteland|Jeb's Chamber|Quirrel's Fortress|Corpse Haven"),
    ("Ashvale","Rexie's Plateau|Warty's Corridor|Kov'alg Pit|Bonevale"),
    ("Aramore","Torlim's Vault|Zorul's Gauntlet|Tealk's Palace|Necromore"),
    ("Morgoroth","Rugum's Sewer|Oozmire|Moghur's Catacomb|Demiroth"),
    ("Cambora","Scorpius's Plateau|Vedaire Thicket|Grimbora"),
    ("Galaran","Googamenz's Vault|The Trilogy Chamber|Oblitaran"),
    ("Eshlyn","Eshlyn Void|Eshlyn Abyss|Grimlyn"),
    ("Uamor","Calverang's Dominion|Broken Abyss|Elemental Colony|Hero's Ruin"),
    ("Melvin's Genesis","Eldingverold|Terra Nova Mines|The Obelisk of Mistral|Thiduna Conflux"),
    ("Zord Attacks!","Bay City|Underground Refuge|Fotovoltaic Center|Capital City"),
    ("Ancient Odyssey","Viranaco|Uhyuta|Kushatan|Tumalenque"),
    ("Southpeak","Asuteng's Marshland|Thikad Mul's Wind Hills|Melica's Glacier|Iron Fate"),
    ("Fenrir's Omen","Haefest's Tumuli|Baga Baya's Fungal Lawn|Calaveragh's Coffin|Seior's Circle"),
    ("Steamfunk City","Gorobot Pipeline|Trombolini's Bandstand|Pomp Drillo's Tunnel|The Secret Leaf Clover Lodge"),
    ("Olympian Secret Party","Thanates's Sanctuary|Thebes's Peaks of Fire & Love|High Cloud Shrine|Uzum's VIP"),
    ("Sruxon Attack!","R.A.N or Die!|Edibleghs Frenzy Kitchen-Lab|Washed by the Melvin|Auriga's Exploration"),
    ("Galactic Trials","Tomorian Graveyard|Espanior's Coliseum|Fisherfish Shrine|Martyr's Garden"),
    ("Big Claw","Cluck Pit|Avian Post|Roosterville|Wing Terminal"),
]


def build(text):
    dungeons=[]
    for zone,(name,names) in enumerate(ZONES,1):
        values=names.split('|')
        for index,title in enumerate(values,1):
            dungeons.append({'id':f'Z{zone}D{index}','zone':zone,'zone_name':name,
                             'name':title,'special':index==len(values),
                             'source':'https://bit-heroes.fandom.com/wiki/Zones'})
    ids={row['id'] for row in dungeons};familiars={}
    chunks=re.split(r'\| \*\*([^*]+)\*\* \| !\[UIPower\]',text)
    for index in range(1,len(chunks)-1,2):
        name=re.sub(r'\\([.!])',r'\1',chunks[index].strip())
        routes=set(re.findall(r'\bZ\d+D\d+\b',chunks[index+1]))
        if not routes:continue  # Familiares exclusivos de raids no son dungeons.
        if '%' in name or name in familiars or not routes<=ids:
            raise ValueError(f'Entrada de familiar ambigua: {name}')
        familiars[name]=sorted(routes,key=lambda x:tuple(map(int,re.findall(r'\d+',x))))
    if familiars.get('Bob',[])[:1]!=['Z1D2'] or len(familiars)<200:
        raise ValueError('Fuente incompleta o formato cambiado; no generar catálogo')
    return {'schema':1,'consulted':'2026-10-02','coverage':'Wiki Zones 1–20; no garantiza contenido posterior',
            'sources':['https://bit-heroes.fandom.com/wiki/Zones','https://bit-heroes.fandom.com/wiki/Familiar'],
            'familiar_source_sha256':hashlib.sha256(text.encode()).hexdigest(),
            'dungeons':dungeons,'familiars':familiars}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('--output',type=Path,default=ROOT/'assets/dungeons.json')
    args=parser.parse_args()
    if args.output.exists():parser.error('El destino existe; respáldalo y elige un archivo nuevo')
    data=build(args.source.read_text())
    atomic_json(args.output,data)
    print(f"Catálogo generado: {len(data['dungeons'])} dungeons / {len(data['familiars'])} familiares")
