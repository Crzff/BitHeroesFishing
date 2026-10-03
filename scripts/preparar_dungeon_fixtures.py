"""Importa recortes etiquetados de la exploración local; sin capturas ni input."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT=Path(__file__).resolve().parent.parent
SOURCES={'home':'farm-home','map':'farm-map3','difficulty':'farm-difficulty','team':'farm-roster',
         'energy':'farm-header-frame-3','timer':'farm-header-frame-0','settings_gold':'dungeon-settings-gold',
         'settings_gems':'dungeon-settings-auto2','settings_duplicates':'dungeon-settings-duplicate',
         'settings_top':'dungeon-settings','auto_off':'farm-entered','auto_on':'farm-auto-on',
         'battle':'farm-observe-19','story':'farm-progress','result':'farm-result-current',
         'offer':'farm-loading-current','loading':'farm-loading-label'}
# Coordenadas comprobadas en Steam 1920×1080; no derivadas de la wiki.
REGIONS={
    'HOME_QUEST':('home',(22,24,155,174)), 'HOME_SETTINGS':('home',(1780,932,1896,1075)),
    'MAP_Z5':('map',(775,110,1130,165)), 'NODE_Z5D2':('map',(900,695,1090,935)),
    'DIFFICULTY_Z5D2':('difficulty',(577,177,1340,242)), 'NORMAL':('difficulty',(411,459,700,536)),
    'TEAM':('team',(858,107,1065,171)), 'ACCEPT':('team',(1040,943,1395,1015)),
    'SETTINGS':('settings_gold',(790,122,1127,185)),
    'GOLD':('settings_gold',(557,662,1278,707)), 'GEMS':('settings_gems',(557,776,1178,822)),
    'DUPLICATES':('settings_duplicates',(557,607,1347,653)),
    'EMPTY':('settings_gold',(478,653,542,717)), 'CHECKED':('settings_duplicates',(478,597,542,661)),
    'ENERGY_ICON':('energy',(974,19,1020,62)),
    'AUTO_OFF':('auto_off',(1848,428,1914,588)), 'AUTO_ON':('auto_on',(1848,428,1914,588)),
    'DUNGEON_MAP_HUD':('auto_off',(1715,142,1820,160)),
    'STORY_ZORUL':('story',(1265,446,1430,489)), 'STORY_ARROW':('story',(1640,605,1696,694)),
    'VICTORY':('result',(821,126,1118,180)), 'TOWN':('result',(1018,963,1296,1033)),
    'PERSUADE':('offer',(388,672,670,733)), 'BRIBE':('offer',(1296,675,1468,733)),
    'DECLINE':('offer',(581,921,939,982)),
    'LOADING':('loading',(805,480,1110,538)),
}


def append_zones(source,parser,targets):
    sources={f'zones_map_{z}':('zones-current' if z==1 else f'zones-map-z{z}') for z in range(1,21)}
    sources.update({f'zones_list_{page}':f'zones-list-{page}' for page in ('top','middle-b','middle-a','bottom')})
    sources['zones_reopened']='zones-list-after-z6'
    frames={};hashes={}
    for key,name in sources.items():
        path=source/(name+'.png');frame=cv2.imread(str(path))
        if frame is None or frame.shape!=(1080,1920,3):raise ValueError(f'Fuente incompleta: {path}')
        frames[key]=frame;hashes[key]=hashlib.sha256(path.read_bytes()).hexdigest()
    regions={'ZONES_MENU':('zones_list_top',(840,135,1080,199)),
             'ZONES_BUTTON':('zones_map_5',(323,112,550,194))}
    regions.update({f'MAP_Z{z}':(f'zones_map_{z}',(645,100,1280,171)) for z in range(1,21) if z!=5})
    templates={key:frames[name][y:y1,x:x1].copy() for key,(name,(x,y,x1,y1)) in regions.items()}
    choices={}
    for page,start,y0 in [('top',1,316),('middle-b',6,348),('middle-a',11,316),('bottom',16,348)]:
        for z in range(start,start+5):
            y=y0+(z-start)*128;box=(670,y-25,1200,y+25);choices[str(z)]=[f'zones_list_{page}',box]
            x,y,x1,y1=box;mask=(frames[f'zones_list_{page}'][y:y1,x:x1].min(2)>=170).astype(np.uint8)*255
            ys,xs=np.nonzero(mask)
            if not len(xs):raise ValueError(f'Nombre ausente: zona {z}')
            templates[f'ZONE_CHOICE_{z}']=cv2.cvtColor(mask[ys.min():ys.max()+1,xs.min():xs.max()+1],cv2.COLOR_GRAY2BGR)
    with np.load(targets[0],allow_pickle=False) as data:old_templates={k:data[k] for k in data.files}
    with np.load(targets[1],allow_pickle=False) as data:old_frames={k:data[k] for k in data.files}
    if templates.keys()&old_templates.keys() or frames.keys()&old_frames.keys():parser.error('Zones ya existe; no se sobrescribe')
    metadata=json.loads(targets[2].read_text())
    for key,frame in frames.items():
        clean=np.zeros_like(frame)
        boxes=[(640,130,1280,934)] if key.startswith('zones_list_') or key=='zones_reopened' else [(300,90,1610,205)]
        for x,y,x1,y1 in boxes:clean[y:y1,x:x1]=frame[y:y1,x:x1]
        frames[key]=clean
    np.savez_compressed(targets[0],**old_templates,**templates);np.savez_compressed(targets[1],**old_frames,**frames)
    metadata['source_sha256'].update(hashes);metadata['regions'].update(regions)
    metadata['zone_choice_sources']=choices
    metadata.setdefault('notes',[]).append('Zones: 20 nombres/títulos observados en Steam/niri 2026-10-03; abrir mapa no acredita dungeon desbloqueada. Choices compara texto blanco con los mismos umbrales .97/12, sin OCR.')
    targets[2].write_text(json.dumps(metadata,indent=2)+'\n')
    print('Zones: referencias y fixtures sanitizadas añadidas; datos anteriores conservados')


def append_energy(source,parser,targets):
    sources={'energy_team_large':'team-neutral-1','energy_team_timer':'team-bar-1'}
    frames={};hashes={}
    for key,name in sources.items():
        path=source/(name+'.png');frame=cv2.imread(str(path))
        if frame is None or frame.shape!=(1080,1920,3):raise ValueError(f'Fuente incompleta: {path}')
        clean=np.zeros_like(frame)
        for x,y,x1,y1 in [(880,10,1260,78),(830,90,1100,200),(1000,930,1420,1035)]:
            clean[y:y1,x:x1]=frame[y:y1,x:x1]
        frames[key]=clean;hashes[key]=hashlib.sha256(path.read_bytes()).hexdigest()
    # TEAM oscurece el HUD al 50 %; referencia del slash grande observado, no del reloj.
    slash=frames['energy_team_large'][30:52,1106:1129]
    templates={'SLASH_LARGE':(np.minimum(slash.astype(np.uint16)*2,255).min(2)>=170).astype(np.uint8)}
    with np.load(targets[0],allow_pickle=False) as data:old_templates={k:data[k] for k in data.files}
    with np.load(targets[1],allow_pickle=False) as data:old_frames={k:data[k] for k in data.files}
    if templates.keys()&old_templates.keys() or frames.keys()&old_frames.keys():parser.error('Energía ya existe; no se sobrescribe')
    metadata=json.loads(targets[2].read_text())
    metadata['source_sha256'].update(hashes)
    metadata['regions']['SLASH_LARGE']=['energy_team_large',[1106,30,1129,52]]
    metadata.setdefault('notes',[]).append('Energía TEAM 2026-10-03: saldo 317/368, slash 23×22; normalizar sombreado al 50 % y binarizar blanco >=170. Reloj 2:09 no es saldo. Referencia previa 21×20 y filtros intactos.')
    np.savez_compressed(targets[0],**old_templates,**templates);np.savez_compressed(targets[1],**old_frames,**frames)
    targets[2].write_text(json.dumps(metadata,indent=2)+'\n')
    print('Energía: slash grande y fixtures sanitizadas añadidos; datos anteriores conservados')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--append-tealk',action='store_true',help='Añade solo referencias Z5D3; conserva Z5D2')
    mode.add_argument('--append-zones',action='store_true',help='Añade nombres/títulos Zones; conserva referencias anteriores')
    mode.add_argument('--append-energy',action='store_true',help='Añade slash grande de energía; conserva referencias anteriores')
    args=parser.parse_args();frames={};hashes={};previous_frames={};previous_templates={};metadata={}
    targets=[ROOT/'assets/dungeon_templates.npz',ROOT/'tests/fixtures/dungeons.npz',ROOT/'assets/dungeon_templates.json']
    if args.append_zones:
        append_zones(args.source,parser,targets);raise SystemExit(0)
    if args.append_energy:
        append_energy(args.source,parser,targets);raise SystemExit(0)
    if args.append_tealk:
        SOURCES={'tealk_home':'tealk-ready-home','tealk_map':'tealk-map','tealk_difficulty':'tealk-difficulty','tealk_team':'tealk-team',
                 'tealk_gold':'tealk-settings-gold-off','tealk_gems':'tealk-settings-autospend',
                 'tealk_duplicates_on':'tealk-settings-duplicates','tealk_duplicates_off':'tealk-settings-duplicates-off',
                 'offer_mummih':'tealk-live-familiar_offer','offer_brute':'tealk-current',
                 'decline_confirm':'tealk-after-decline','tealk_battle_victory':'tealk-decline-confirmed',
                 'offer_sitra':'tealk-hover-resume-after','tealk_difficulty_idle':'tealk-stopped-2325'}
        REGIONS={'HOME_QUEST_TOWN':('tealk_home',(22,24,155,174)),
                 'HOME_SETTINGS_TOWN':('tealk_home',(1780,932,1896,1075)),
                 'NODE_Z5D3':('tealk_map',(1360,397,1558,601)),
                 'DIFFICULTY_Z5D3':('tealk_difficulty',(620,177,1295,242)),
                 'HEROIC':('tealk_difficulty',(1220,459,1510,536)),
                 'HEROIC_IDLE':('tealk_difficulty_idle',(1220,459,1510,536)),
                 'EMPTY_HOVER':('tealk_duplicates_off',(478,506,542,570)),
                 'CONFIRM_HEADER':('decline_confirm',(800,285,1115,350)),
                 'DECLINE_CONFIRM':('decline_confirm',(715,465,1205,608)),
                 'DECLINE_YES':('decline_confirm',(688,710,943,787)),
                 'AUTO_ON_BATTLE':('offer_brute',(1848,435,1910,595)),
                 'BATTLE_VICTORY':('tealk_battle_victory',(831,83,1100,137)),
                 'BATTLE_CONTINUE':('tealk_battle_victory',(1020,966,1293,1036))}
        with np.load(targets[0],allow_pickle=False) as data:previous_templates={key:data[key] for key in data.files}
        with np.load(targets[1],allow_pickle=False) as data:previous_frames={key:data[key] for key in data.files}
        metadata=json.loads(targets[2].read_text())
        if set(REGIONS)&previous_templates.keys() or set(SOURCES)&previous_frames.keys():
            parser.error('Tealk ya existe: respalda y revisa antes de sustituir referencias')
    elif any(path.exists() for path in targets):parser.error('Destino existente: respalda y revisa antes de regenerar')
    for key,name in SOURCES.items():
        path=args.source/(name+'.png');image=cv2.imread(str(path))
        if image is None or image.shape!=(1080,1920,3):raise ValueError(f'Fuente incompleta: {path}')
        hashes[key]=hashlib.sha256(path.read_bytes()).hexdigest();frames[key]=image
    templates={key:frames[name][y:y1,x:x1].copy() for key,(name,(x,y,x1,y1)) in REGIONS.items()}
    if args.append_tealk:
        sys.path.insert(0,str(ROOT))
        from fishing_core.dungeon_vision import familiar_glyph
        metadata['familiar_name_sources']={'Mummih':'offer_mummih','Brute':'offer_brute','Sitra':'offer_sitra'}
        for name,source in metadata['familiar_name_sources'].items():templates['NAME_'+name]=familiar_glyph(frames[source])
    # El slash de ENERGY no es un digito ni una lectura de saldo por sí mismo.
    if not args.append_tealk:
        crop=frames['energy'][20:65,1038:1203];templates['SLASH']=(crop[11:31,75:96].min(2)>=170).astype(np.uint8)
    np.savez_compressed(targets[0],**previous_templates,**templates)
    for key,frame in frames.items():
        if args.append_tealk:
            if key=='offer_sitra':
                clean=np.zeros_like(frame)
                for x,y,x1,y1 in [(350,130,1570,205),(360,640,720,780),(1240,640,1535,780),(550,890,965,1015)]:
                    clean[y:y1,x:x1]=frame[y:y1,x:x1]
                frames[key]=clean;continue
            if key in ('offer_mummih','offer_brute','decline_confirm','tealk_battle_victory'):
                frame[925:1080,1600:1760]=0;continue
            clean=np.zeros_like(frame);clean[:80]=frame[:80]
            boxes=([(15,15,165,190),(1760,910,1920,1080)] if key=='tealk_home' else
                   [(230,90,1715,1025)] if key=='tealk_map' else
                   [(300,130,1655,1045)] if key in ('tealk_difficulty','tealk_difficulty_idle') else
                   [(830,90,1100,200),(510,920,1420,1040)] if key=='tealk_team' else
                   [(760,100,1160,215),(465,340,1400,860)])
            for x,y,x1,y1 in boxes:clean[y:y1,x:x1]=frame[y:y1,x:x1]
            frames[key]=clean;continue
        frame[925:1080,1600:1760]=0  # Botón/chat ajeno al reconocimiento.
        if key=='team':frame[320:670,530:820]=0  # Nombres de jugadores.
    targets[1].parent.mkdir(parents=True,exist_ok=True);np.savez_compressed(targets[1],**previous_frames,**frames)
    metadata.setdefault('schema',1);metadata.setdefault('source','Steam/niri local 2026-10-02')
    metadata.setdefault('source_sha256',{}).update(hashes);metadata.setdefault('regions',{}).update(REGIONS)
    targets[2].write_text(json.dumps(metadata,indent=2)+'\n')
    print('Recortes y fixtures sanitizados guardados; sin modificar las fuentes')
