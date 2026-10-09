"""Reconocimiento puro y conservador de la primera ruta de dungeons."""

from pathlib import Path

import cv2
import numpy as np

from .bait_inventory import BaitReader,quantity_boxes

ASSETS=Path(__file__).resolve().parent.parent/'assets/dungeon_templates.npz'
SETTINGS={'gold':('GOLD',False),'gems':('GEMS',False),'duplicates':('DUPLICATES',False),
          'notifications':('SETTING_NOTIFICATIONS',False),'animations':('SETTING_ANIMATIONS',False),
          'tips':('SETTING_TIPS',False),'merchants':('SETTING_MERCHANTS',True),
          'treasures':('SETTING_TREASURES',True),'music':('SETTING_MUSIC',True),'sound':('SETTING_SOUND',True)}
NEW_TEMPLATES=tuple(key for key,_ in SETTINGS.values() if key.startswith('SETTING_'))+(
    'AUDIO_ZERO','IDLE_TITLE','IDLE_YES','EVENT_TITLE','EVENT_ENDS','EVENT_CLOSE')


def familiar_glyph(frame):
    roi=frame[130:205,350:1570]
    mask=((roi.max(2)>=170)&(roi.max(2).astype(np.int16)-roi.min(2)>=50)).astype(np.uint8)*255
    ys,xs=np.nonzero(mask)
    return mask[ys.min():ys.max()+1,xs.min():xs.max()+1] if len(xs) else None


def text_letters(mask):
    """Letras de una máscara de texto (columnas vacías entre ellas), normalizadas a 27 px; sin apóstrofos."""
    cols=np.nonzero(mask.any(0))[0];runs=[]
    for c in cols:
        if runs and c==runs[-1][1]+1:runs[-1][1]=c
        else:runs.append([c,c])
    out=[]
    for a,b in runs:
        part=mask[:,a:b+1];ys=np.nonzero(part.any(1))[0]
        if ys.max()-ys.min()+1<0.6*mask.shape[0]:continue
        g=part[ys.min():ys.max()+1].astype(np.uint8)*255
        out.append(cv2.resize(g,(max(1,round(g.shape[1]*27/g.shape[0])),27),interpolation=cv2.INTER_AREA)>127)
    return out


def edit_distance(a,b):
    row=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        prev,row[0]=row[0],i
        for j,y in enumerate(b,1):prev,row[j]=row[j],min(row[j]+1,row[j-1]+1,prev+(x!=y))
    return row[-1]


# Ventanas de otros modos: cada una exige título y botón propios (ROI con holgura).
MODE_SCREENS=(('DISCONNECTED',(('DISCONNECTED',(720,430,1200,640)),('RECONNECT',(770,665,1150,820)))),
              ('SEASON_REWARDS',(('SEASON_TITLE',(600,150,1320,310)),('SEASON_CLAIM',(740,885,1180,1040)))),
              ('ITEMS',(('ITEMS_TITLE',(600,150,1320,450)),('ITEMS_CLOSE',(1200,150,1500,450)))),
              ('TRIALS_REWARDS',(('STARTUP_TRIALS_TITLE',(800,95,1200,210)),('ITEMS_CLOSE',(1600,100,1740,240)))),
              ('FISHING_REWARDS',(('STARTUP_FISHING_TITLE',(760,230,1160,350)),('ITEMS_CLOSE',(1280,240,1420,370)))),
              ('NEWS',(('NEWS_TITLE',(740,90,1180,255)),('NEWS_CLOSE',(935,885,1310,1045)))),
              ('PVP',(('PVP_TITLE',(600,140,1320,295)),('PVP_PLAY',(1120,440,1445,695)))),
              ('PVP_SELECT',(('PVP_SELECT',(520,95,1400,250)),)),
              ('RAID',(('RAID_TITLE',(760,155,1160,300)),('RAID_SUMMON',(1095,650,1435,920)))),
              ('RAID_DIFFICULTY',(('RAID_NORMAL',(360,395,750,575)),('RAID_HARD',(770,395,1150,575)),
                                  ('RAID_HEROIC',(1180,395,1560,575)))),
              ('EXPEDITION',(('EXP_TITLE',(680,150,1220,310)),('EXP_PLAY',(1120,440,1445,710)))),
              ('IDOL_MAP',(('IDOL_TITLE',(560,50,1420,215)),)),
              ('PORTAL',(('PORTAL_TITLE',(710,130,1285,285)),('PORTAL_ENTER',(830,880,1150,1060)))),
              ('TRIALS',(('TRIALS_TITLE',(620,150,1300,310)),('TRIALS_PLAY',(1120,450,1450,710)))))


# Runas menores (wiki 2026-10-05): bono por rareza común, rara, épica, legendaria y mítica.
RUNE_VALUES={'QUINDI':(5,10,15,20,25),'VRYN':(7.5,15,22.5,30,37.5),'DAR':(5,10,15,20,25),'ZYRK':(5,10,15,20,25)}
RARITIES=('COMMON','RARE','EPIC','LEGENDARY','MYTHIC')


def rune_rarity(hue,saturation):
    """Tono del rombo -> rareza: gris común, azul rara, magenta épica, amarillo legendaria, rojo mítica."""
    # ponytail: las comunes (grises) no pasan el umbral de saturación de runes_in; se ignoran (5 %), sin captura de referencia.
    if saturation<70:return 'COMMON'
    if 90<=hue<=130:return 'RARE'
    if 135<=hue<=166:return 'EPIC'
    if 12<=hue<=40:return 'LEGENDARY'
    if hue>=167 or hue<=11:return 'MYTHIC'
    return None


# LOOT RECAP/FOUND de las pantallas de resultado: rejilla de 3x2 casillas visibles (con scroll).
LOOT_CELLS=tuple((x,y) for y in (627,781) for x in (1093,1247,1401))
LOOT_SIZE=129


def loot_rarity(bgr):
    """Color del borde de la casilla -> rareza (nombres de crzf); None si la casilla está vacía."""
    b,g,r=(int(c) for c in bgr);hi,lo=max(b,g,r),min(b,g,r)
    if hi<120:return None
    if lo>=200:return 'COMMON'  # borde blanco: oro, XP y consumibles sin rareza
    hue=cv2.cvtColor(np.uint8([[bgr]]),cv2.COLOR_BGR2HSV)[0,0,0]
    # Rojos del juego: épico salmón (240,128,112) y mítico rojo rosado (240,80,112); los separa el verde.
    if (hue<=8 or hue>=166) and r>=200:return 'EPIC' if g>=105 else 'MYTHIC'
    if 45<=hue<=80:return 'COMMON'
    if 82<=hue<=100:return 'SET'
    if 101<=hue<=128:return 'RARE'
    if 129<=hue<=165 or 9<=hue<=19:return 'EPIC'
    if 20<=hue<=40:return 'LEGENDARY'
    return 'MYTHIC'


class DungeonVision:
    def __init__(self,path=ASSETS):
        with np.load(path,allow_pickle=False) as data:
            self.templates={key:data[key] for key in data.files}
        for key in ('MERCHANT_TITLE','MERCHANT_DECLINE')+NEW_TEMPLATES:
            template=cv2.imread(str(ASSETS.parent/f'{key.lower()}.png'))
            if template is not None:self.templates[key]=template
        # ponytail: fondos/variantes observados; máscara alfa etiquetada si otro fondo falla.
        # El fondo de la ciudad cambia: comparar solo los píxeles comunes a todas las variantes observadas.
        self.home_masks={key:np.all([np.all(self.templates[key]==self.templates[v],axis=2) for v in self.templates
                                     if v.startswith(key+'_TOWN')],axis=0).astype(np.uint8)
                         for key in ('HOME_QUEST','HOME_SETTINGS','HOME_BOSS','HOME_PVP','HOME_RAID','HOME_EXPEDITION','HOME_TRIALS')
                         if any(v.startswith(key+'_TOWN') for v in self.templates)}
        self.digits=BaitReader(extra={k:v for k,v in self.templates.items() if k.startswith('DIGIT_')})

    def locate(self,frame,key,roi,threshold=.97,max_diff=12):
        x,y,x1,y1=roi;image=frame[y:y1,x:x1];ref=self.templates[key]
        if image.shape[0]<ref.shape[0] or image.shape[1]<ref.shape[1]:return None
        mask=self.home_masks.get(key)
        result=cv2.matchTemplate(image,ref,cv2.TM_CCOEFF_NORMED,mask=mask)
        result[~np.isfinite(result)]=-1  # Una ROI uniforme no acredita coincidencia.
        _,score,_,pos=cv2.minMaxLoc(result);px,py=pos
        matched=image[py:py+ref.shape[0],px:px+ref.shape[1]]
        # Correlación sola acepta ventanas oscurecidas por un diálogo/pago.
        difference=np.abs(matched.astype(np.int16)-ref)
        if mask is not None:difference=difference[mask!=0]
        if score>=threshold and float(difference.mean())<=max_diff:return x+px,y+py
        return self.locate(frame,'HEROIC_IDLE',roi,threshold) if key=='HEROIC' else None

    def locate_all(self,frame,key,roi,threshold=.97):
        """Todas las apariciones completas de key en roi, de arriba abajo (sin solapes)."""
        x,y,x1,y1=roi;image=frame[y:y1,x:x1];ref=self.templates[key];h,w=ref.shape[:2]
        if image.shape[0]<h or image.shape[1]<w:return []
        result=cv2.matchTemplate(image,ref,cv2.TM_CCOEFF_NORMED);result[~np.isfinite(result)]=-1
        found=[]
        for py,px in sorted(zip(*np.nonzero(result>=threshold)),key=lambda p:-result[p]):
            if any(abs(px-fx)<w//2 and abs(py-fy)<h//2 for fx,fy in found):continue
            if float(np.abs(image[py:py+h,px:px+w].astype(np.int16)-ref).mean())<=12:found.append((px,py))
        return sorted(((x+px,y+py) for px,py in found),key=lambda p:p[1])

    def map_zone(self,frame):
        if frame.shape!=(1080,1920,3) or not self.locate(frame,'ZONES_BUTTON',(315,100,565,205)):return None
        zones=[zone for zone in range(1,21) if self.locate(frame,f'MAP_Z{zone}',(645,90,1280,185))]
        return zones[0] if len(zones)==1 else None

    def zone_choice(self,frame,zone):
        if type(zone) is not int or not 1<=zone<=20 or self.screen(frame)!='ZONES':return None
        # El fondo de la fila cambia al seleccionar/hover; comparar solo texto blanco.
        text=cv2.cvtColor((frame.min(2)>=170).astype(np.uint8)*255,cv2.COLOR_GRAY2BGR)
        key=f'ZONE_CHOICE_{zone}';pos=self.locate(text,key,(670,280,1200,900))
        if pos is None:return None
        h,w=self.templates[key].shape[:2];x,y=pos
        return x+w//2,y+h//2

    def screen(self,frame):
        if frame.shape!=(1080,1920,3):return 'UNKNOWN'
        if (self.locate(frame,'IDLE_TITLE',(700,450,1200,610)) and
                self.locate(frame,'IDLE_YES',(770,680,1140,830))):return 'IDLE_PROMPT'
        if (self.locate(frame,'EVENT_TITLE',(700,90,1220,210)) and
                self.locate(frame,'EVENT_ENDS',(570,220,1380,300))):return 'EVENT_WINDOW'
        if (all(key in self.templates for key in ('MERCHANT_TITLE','MERCHANT_DECLINE')) and
                self.locate(frame,'MERCHANT_TITLE',(720,220,1160,335)) and
                self.locate(frame,'MERCHANT_DECLINE',(990,765,1250,865))):return 'MERCHANT'
        if (self.locate(frame,'DECLINE_CONFIRM',(700,455,1220,620)) and
                self.locate(frame,'DECLINE_YES',(670,695,955,805))):return 'DECLINE_CONFIRM'
        if (self.locate(frame,'WB_NOT_FULL',(680,410,1240,575)) and
                self.locate(frame,'DECLINE_YES',(670,695,955,805))):return 'WB_NOT_FULL'
        if (self.locate(frame,'CONFIRM_HEADER',(770,270,1150,370)) and self.locate(frame,'PERSUADE_GOLD',(800,500,1320,640))
                and self.locate(frame,'DECLINE_YES',(670,695,955,805))):return 'PERSUADE_CONFIRM'
        # El dibujo del familiar puede tapar el título (alas de Callumoth): CLOSE exacto y título tolerante.
        if (self.locate(frame,'CAPTURE_CLOSE',(780,890,1140,1040)) and
                self.locate(frame,'CAPTURE_SUCCESS',(540,50,1380,170),.8,max_diff=40)):return 'CAPTURE_SUCCESS'
        if (self.locate(frame,'RESUME_DUNGEON',(640,400,1280,500)) and
                self.locate(frame,'DECLINE_YES',(670,695,955,805))):return 'RESUME_DUNGEON'  # "UH OH! ¿continuar?"
        if self.locate(frame,'CONFIRM_HEADER',(770,270,1150,370)):return 'UNKNOWN'
        # El dibujo del familiar puede tapar parte de PERSUADE (la caña de Columbus): BRIBE y DECLINE
        # exactos y PERSUADE con algo de tolerancia.
        if (self.locate(frame,'BRIBE',(1240,640,1535,780)) and self.locate(frame,'DECLINE',(550,890,965,1015)) and
                self.locate(frame,'PERSUADE',(360,640,720,780),.8,max_diff=40)):return 'FAMILIAR_OFFER'
        if self.locate(frame,'LOADING',(790,470,1130,550)):return 'LOADING'
        if self.locate(frame,'ZONES_MENU',(820,120,1100,215)):return 'ZONES'
        boss=self.boss_screen(frame)
        if boss:return boss
        for screen,checks in MODE_SCREENS:
            if all(key in self.templates and self.locate(frame,key,roi) for key,roi in checks):return screen
        regions=[('VICTORY',(780,110,1150,210)),('SETTINGS',(760,100,1160,215)),
                 ('TEAM',(830,90,1100,200))]
        for key,roi in regions:
            if self.locate(frame,key,roi):return key
        # Ventanas de entrada a una dungeon: misma disposición en todas; el título dice cuál es.
        if self.locate(frame,'NORMAL',(400,450,715,550)) and self.locate(frame,'HARD',(780,430,1140,570)):return 'DIFFICULTY'
        if self.locate(frame,'SPECIAL_HEADER',(700,170,1220,290)) and self.locate(frame,'SPECIAL_ENTER',(940,870,1320,1020)):
            return 'DUNGEON_SPECIAL'
        zone=self.map_zone(frame)
        if zone is not None:return f'MAP_Z{zone}'
        if (self.locate(frame,'BATTLE_VICTORY',(810,70,1120,155)) and
                self.locate(frame,'BATTLE_CONTINUE',(1000,950,1310,1055))):return 'BATTLE_VICTORY'
        if self.locate(frame,'STORY_ZORUL',(1200,415,1480,520)) and self.locate(frame,'STORY_ARROW',(1620,575,1720,720)):
            return 'STORY_ZORUL'
        # Cualquier otro diálogo de historia (Agnar, Nyxn...): misma flecha amarilla a la derecha.
        # La flecha es igual en todos; el fondo detrás cambia (mapa, combate de raid): algo de tolerancia.
        if self.locate(frame,'STORY_ARROW',(1600,560,1740,740),.88,max_diff=40) or self.dialog_box(frame):return 'STORY'
        map_hud=self.locate(frame,'DUNGEON_MAP_HUD',(1680,130,1860,175))
        if self.locate(frame,'AUTO_OFF',(1835,410,1920,610)):
            return 'AUTO_OFF' if map_hud else 'AUTO_OFF_BATTLE'
        if (self.locate(frame,'AUTO_ON',(1835,410,1920,610)) or
                self.locate(frame,'AUTO_ON_BATTLE',(1835,410,1920,675))):
            return 'AUTO_ON' if map_hud else 'AUTO_ON_BATTLE'
        if (self.locate(frame,'HOME_QUEST',(15,15,165,190)) and
                self.locate(frame,'HOME_SETTINGS',(1760,910,1920,1080))):return 'HOME'
        return 'UNKNOWN'

    def boss_screen(self,frame):
        """Ventanas del World Boss; cada una exige título y botón propios."""
        if self.locate(frame,'RESULT_TOWN',(700,915,1500,1080)):
            if self.locate(frame,'WB_DEFEAT',(760,75,1160,230)):return 'WB_DEFEAT'
            if 'WB_VICTORY' in self.templates and self.locate(frame,'WB_VICTORY',(760,75,1160,230)):return 'WB_VICTORY'
        if self.locate(frame,'WB_START',(695,905,1140,1065)):  # START solo existe en la sala (cualquier jefe)
            return 'WB_LOBBY'
        if self.locate(frame,'WB_SUMMON_TITLE',(790,185,1190,325)) and self.locate(frame,'WB_SUMMON_BUTTON',(975,760,1290,925)):
            return 'WB_SUMMON'
        if self.locate(frame,'WB_LIST',(680,120,1240,275)):
            if self.locate(frame,'WB_SUMMON_LIST',(995,890,1365,1045)):return 'WB_LIST'
            if self.locate(frame,'WB_CAROUSEL_SUMMON',(1100,660,1425,910)):return 'WB_CAROUSEL'
        return None

    def offer_cost(self,frame):
        """Oro de Persuade en la oferta ("4,000"); None si no se lee."""
        if self.screen(frame)!='FAMILIAR_OFFER':return None
        image=frame[560:630,490:665].copy()
        image[(image.min(2)>=170)&(image.min(2)<235)]=0  # cifras blanco puro; la caña de Columbus es crema
        mask=(image.min(2)>=170).astype(np.uint8)
        for x,y,w,h,_ in quantity_boxes(mask):
            if h<20:image[y:y+h,x:x+w]=0  # coma de miles
        return self.number(image)

    def bright_number(self,image):
        """Número de color (azul/amarillo/blanco): brillo en cualquier canal, sin comas."""
        white=np.zeros_like(image);white[image.max(2)>=170]=255
        mask=(white[:,:,0]>0).astype(np.uint8);boxes=quantity_boxes(mask)
        if not boxes:return None
        tall=max(b[3] for b in boxes)
        for x,y,w,h,_ in boxes:
            if h<0.7*tall:white[y:y+h,x:x+w]=0
        return self.number(white)

    def menu_lines(self,frame):
        """Líneas de texto altas del menú de Trials: [(y en pantalla, recorte)]. La etiqueta TIER es más baja."""
        x0,y0,x1,y1=730,255,1190,930;menu=frame[y0:y1,x0:x1]
        lines=(menu.max(2)>=170).any(1);out=[];y=0
        while y<len(lines):
            if lines[y]:
                top=y
                while y<len(lines) and lines[y]:y+=1
                if y-top>=26:out.append((y0+(top+y)//2,menu[max(0,top-4):y+4]))
            y+=1
        return out

    def trials_ranges(self,frame):
        """Primer menú de dificultad de Trials: [(y, mínimo, máximo)]."""
        return [(y,)+span for y,line in self.menu_lines(frame) if (span:=self.range_text(line))]

    def trials_levels(self,frame):
        """Segundo menú (niveles de un rango): [(y, nivel)]; vacío si es el menú de rangos."""
        lines=self.menu_lines(frame)
        if any(self.range_text(line) for _,line in lines):return []
        return [(y,n) for y,line in lines if (n:=self.bright_number(line)) is not None]

    def range_text(self,line):
        """'1,080 - 1,239' -> (1080, 1239): separa por el guion."""
        white=np.zeros_like(line);white[line.max(2)>=170]=255
        boxes=quantity_boxes((white[:,:,0]>0).astype(np.uint8))
        if not boxes:return None
        tall=max(b[3] for b in boxes)
        dashes=[b for b in boxes if b[3]<0.4*tall and b[2]>1.5*b[3]]
        if len(dashes)!=1:return None
        dx,_,dw,_,_=dashes[0];values=[]
        for left,right in ((0,dx),(dx+dw,white.shape[1])):
            part=np.zeros_like(white);part[:,left:right]=white[:,left:right];values.append(self.bright_number(part))
        return tuple(values) if None not in values else None

    def rune(self,crop):
        """(tipo, rareza, valor) de una runa menor recortada, o None si no se reconoce con margen."""
        hsv=cv2.cvtColor(crop,cv2.COLOR_BGR2HSV)
        fill=((hsv[:,:,1]>60)&(hsv[:,:,2]>110)).astype(np.uint8)
        count,labels,stats,_=cv2.connectedComponentsWithStats(cv2.morphologyEx(fill,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8)))
        # El rombo es el componente más pequeño que contiene el centro (el marco de rareza de la lista lo rodea).
        H,W=crop.shape[:2];inside=[j for j in range(1,count) if stats[j,4]>=600 and
                                   stats[j,0]<=W//2<stats[j,0]+stats[j,2] and stats[j,1]<=H//2<stats[j,1]+stats[j,3]]
        if not inside:return None
        i=min(inside,key=lambda j:stats[j,2]*stats[j,3]);x,y,w,h,area=stats[i]
        if area<600 or not 0.7<w/max(h,1)<1.4:return None
        cx,cy=x+w//2,y+h//2;r=int(0.27*max(w,h))
        body=labels==i;sym=((~body)&(hsv[:,:,2]<120))[max(0,cy-r):cy+r,max(0,cx-r):cx+r].astype(np.uint8)
        if sym.size==0:return None
        sym=cv2.resize(sym,(40,40),interpolation=cv2.INTER_AREA)>0
        scores={k[9:]:(sym&(ref>0)).sum()/max(1,(sym|(ref>0)).sum()) for k,ref in self.templates.items() if k.startswith('RUNE_SYM_')}
        best=sorted(scores.items(),key=lambda kv:-kv[1])
        rarity=rune_rarity(float(np.median(hsv[:,:,0][body])),float(np.median(hsv[:,:,1][body])))
        if rarity is None:return None
        # El símbolo solo es una pista (falla con las míticas rojas): sin margen, tipo desconocido
        # y el runner lo confirma con el tooltip.
        if best[0][1]<0.7 or best[0][1]-best[1][1]<0.15:return None,rarity,None
        kind=best[0][0];return kind,rarity,RUNE_VALUES[kind][RARITIES.index(rarity)]

    @staticmethod
    def tooltip_border(frame):
        """Borde del tooltip: amarillo pálido (255,255,125) o blanco azulado (238,241,249), según la runa."""
        b,g,r=frame[:,:,0],frame[:,:,1],frame[:,:,2]
        return (((b>=100)&(b<=150))|(b>=230))&(g>=230)&(r>=230)

    def tooltip_visible(self,frame):
        """Hay un tooltip de runa abierto (línea horizontal larga de su borde)."""
        border=self.tooltip_border(frame)
        title=(np.abs(frame.astype(np.int16)-np.array((36,26,20),np.int16)).sum(2)<=18)  # fondo del título
        for y in np.nonzero(border[:1000].sum(1)>=250)[0]:
            if y+8>=frame.shape[0]:continue
            row=np.concatenate([[0],border[y].astype(np.int8),[0]]);edges=np.nonzero(np.diff(row))[0]
            for x0,x1 in zip(edges[::2],edges[1::2]):  # tramos continuos del borde
                if x1-x0>=250 and title[y+8,x0+10:x1-10].mean()>.8:return True
        return False

    def tooltip_kind(self,before,after):
        """Tipo de runa leído en el título del tooltip ("QUINDI RUNE") que aparece al pasar el ratón."""
        # El tooltip aparece con un borde amarillo pálido (255,255,125): su línea superior lo sitúa.
        changed=np.abs(after.astype(np.int16)-before.astype(np.int16)).sum(2)>60
        yellow=self.tooltip_border(after)&changed
        rows=np.nonzero(yellow.sum(1)>=250)[0]
        if not len(rows):return None
        y=int(rows[0]);xs=np.nonzero(yellow[y])[0];x,w=int(xs.min()),int(xs.max()-xs.min())
        band=after[y+8:y+62,x+30:x+w-30]
        hsv=cv2.cvtColor(band,cv2.COLOR_BGR2HSV);mask=((hsv[:,:,1]>120)&(hsv[:,:,2]>150))|(band.min(2)>=200)
        ys=np.nonzero(mask.any(1))[0]
        if not len(ys):return None
        text=self.read_text(mask[ys.min():ys.max()+1])
        scored=sorted((edit_distance(text,name+'RUNE'),name) for name in RUNE_VALUES)
        return scored[0][1] if scored[0][0]<=2 and scored[1][0]>scored[0][0] else None

    def runes_in(self,frame,roi):
        """Runas de la lista (MINOR RUNE): [((x,y) centro, tipo, rareza, valor)] dentro de roi."""
        x0,y0,x1,y1=roi;area=frame[y0:y1,x0:x1];hsv=cv2.cvtColor(area,cv2.COLOR_BGR2HSV)
        fill=((hsv[:,:,1]>60)&(hsv[:,:,2]>110)).astype(np.uint8)
        count,_,stats,_=cv2.connectedComponentsWithStats(cv2.morphologyEx(fill,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8)))
        found=[]
        for x,y,w,h,a in stats[1:]:
            if a<600 or not 0.7<w/max(h,1)<1.4 or w>140 or a/(w*h)<0.28:continue
            cx,cy=x0+x+w//2,y0+y+h//2;pad=int(0.35*max(w,h))
            info=self.rune(frame[max(0,cy-h//2-pad):cy+h//2+pad,max(0,cx-w//2-pad):cx+w//2+pad])
            if info:found.append(((cx,cy),)+info)
        return sorted(found,key=lambda r:(r[0][1],r[0][0]))

    def read_text(self,mask):
        """Texto en mayúsculas con el alfabeto del juego (GLYPH_*), letra a letra por solapamiento."""
        out=''
        for g in text_letters(mask>0):
            def score(ref):
                r=cv2.resize(ref.astype(np.uint8),(g.shape[1],27),interpolation=cv2.INTER_NEAREST)>0
                return (r&g).sum()/max(1,(r|g).sum())-abs(ref.shape[1]-g.shape[1])*.02
            out+=max((k for k in self.templates if k.startswith('GLYPH_')),key=lambda k:score(self.templates[k]))[6]  # GLYPH_M2: variante
        return out

    def loot_amount(self,frame,x,y):
        """Cantidad escrita arriba de la casilla ("6", "10.1K"); None si no hay o no se lee."""
        band=frame[y+12:y+48,x+10:x+122];m=(band.min(2)>=235).astype(np.uint8)
        n,lab,st,_=cv2.connectedComponentsWithStats(m);tall=[];dots=[]
        for i in range(1,n):
            gx,gy,gw,gh,a=st[i]
            if 18<=gh<=32:tall.append((gx,i))
            elif gh<=9 and a>=4 and gy+gh>=24:dots.append(gx)
        if not tall:return None
        text=''
        for gx,i in sorted(tall):
            gx,gy,gw,gh,_=st[i];g=(lab[gy:gy+gh,gx:gx+gw]==i).astype(np.uint8)*255
            g=cv2.resize(g,(max(1,round(gw*27/gh)),27),interpolation=cv2.INTER_AREA)>127
            def score(ref):
                r=cv2.resize(ref.astype(np.uint8),(g.shape[1],27),interpolation=cv2.INTER_NEAREST)>0
                return (r&g).sum()/max(1,(r|g).sum())
            key=max((k for k in self.templates if k.startswith('LOOT_DIGIT_')),key=lambda k:score(self.templates[k]))
            # ponytail: sin muestras de 4, 8 ni M; un glifo dudoso deja la cantidad sin leer.
            if score(self.templates[key])<.7:return None
            text+=key[11:]
            inner=[d for d in dots if gx+gw<=d<=gx+gw+12]
            if inner and '.' not in text and i!=sorted(tall)[-1][1]:text+='.'
        unit={'K':1000,'M':1_000_000}.get(text[-1:],1);text=text.rstrip('KM')
        try:return round(float(text)*unit) if text and text.count('.')<=1 and 'K' not in text else None
        except ValueError:return None

    def tooltip_boxes(self,frame):
        """Recuadros de descripción: (x0, y0, x1, y1) desde su línea superior de borde (alto fijo útil)."""
        border=self.tooltip_border(frame);out=[]
        for y in np.nonzero(border.sum(1)>=200)[0]:
            row=np.concatenate([[0],border[y].astype(np.int8),[0]]);e=np.nonzero(np.diff(row))[0]
            for x0,x1 in zip(e[::2],e[1::2]):
                if x1-x0<200 or y+140>=frame.shape[0]:continue
                if any(abs(x0-a)<6 and abs(x1-b)<6 and 0<=y-c<40 for a,c,b,_ in out):continue
                out.append((int(x0),int(y),int(x1),int(min(frame.shape[0],y+260))))
        return out

    def loot_tooltip(self,before,after):
        """Tipo que el juego escribe en la descripción de una casilla del botín ("RARE MATERIAL",
        "COMMON CONSUMABLE", "RARE RING"...): MATERIAL, CONSUMABLE, CURRENCY o ITEM; None si no se lee."""
        new=[b for b in self.tooltip_boxes(after)
             if (np.abs(after[b[1]:b[1]+3,b[0]:b[2]].astype(np.int16)-before[b[1]:b[1]+3,b[0]:b[2]].astype(np.int16)).sum(2)>60).mean()>.5]
        if not new:return None
        x0,y0,x1,y1=max(new,key=lambda b:b[0])  # con comparación salen dos: el de la derecha es el del botín
        region=after[y0+6:y1,x0+int(.44*(x1-x0)):x1-8];hsv=cv2.cvtColor(region,cv2.COLOR_BGR2HSV)
        mask=(region.min(2)>=215)|((hsv[:,:,1]>70)&(hsv[:,:,2]>170))  # texto blanco o del color de la rareza
        lines=[];rows=mask.any(1);start=None
        for y in range(len(rows)+1):
            on=y<len(rows) and rows[y]
            if on and start is None:start=y
            if not on and start is not None:
                if 12<=y-start<=40:
                    seg=mask[start:y];xs=np.nonzero(seg.any(0))[0];lines.append(self.read_text(seg[:,xs.min():xs.max()+1]))
                start=None
        near=lambda text,word:edit_distance(text,word)<=2
        rarities=('COMMON','RARE','EPIC','LEGENDARY','MYTHIC','SET','GENERIC')
        for i,line in enumerate(lines):
            for word,kind in (('MATERIAL','MATERIAL'),('CONSUMABLE','CONSUMABLE'),('CURRENCY','CURRENCY')):
                if near(line,word):return kind
            if any(near(line,r) for r in rarities) and i+1<len(lines) and len(lines[i+1])>=3:
                if not any(near(lines[i+1],w) for w in ('MATERIAL','CONSUMABLE','CURRENCY')):return 'ITEM'
        return None

    def raid_title(self,frame,names):
        """Nombre de la raid del carrusel (texto de color sobre la descripción), emparejado con names."""
        region=frame[735:805,500:1150];hsv=cv2.cvtColor(region,cv2.COLOR_BGR2HSV)
        mask=(hsv[:,:,1]>110)&(hsv[:,:,2]>150);rows=mask.sum(1)
        if rows.max()<60:return None
        ys=np.nonzero(rows>=.4*rows.max())[0];band=mask[ys.min():ys.max()+1]
        n,lab,st,_=cv2.connectedComponentsWithStats(band.astype(np.uint8),connectivity=8);letters=np.zeros_like(band)
        for j in range(1,n):
            if st[j,3]>=.5*band.shape[0]:letters|=lab==j  # letras: casi toda la altura de la línea
        xs=np.nonzero(letters.any(0))[0]
        if not len(xs):return None
        text=self.read_text(letters[:,xs.min():xs.max()+1])
        def clean(name):
            s=''.join(c for c in name.upper() if c.isalpha());return s[3:] if s.startswith('THE') else s
        text=text[3:] if text.startswith('THE') else text
        scored=sorted((edit_distance(clean(name),text[:len(clean(name))]),name) for name in names)
        return scored[0][1] if scored[0][0]<=2 and (len(scored)==1 or scored[1][0]>scored[0][0]+1) else None

    @staticmethod
    def dialog_box(frame):
        """Recuadro de diálogo de historia aunque un personaje tape la flecha: borde inferior gris
        (144,151,158) de 900+ px y el interior oscuro encima."""
        band=frame[700:880].astype(np.int16);bottom=np.abs(band-np.array((158,151,144),np.int16)).sum(2)<=24
        for i in range(bottom.shape[0]):
            row=np.concatenate([[0],bottom[i].astype(np.int8),[0]]);edges=np.nonzero(np.diff(row))[0]
            for x0,x1 in zip(edges[::2],edges[1::2]):
                if x1-x0>=900:
                    y=700+i;inner=frame[max(0,y-260):y-25,x0+40:x1-40]
                    if (inner.max(2)<45).mean()>.5:return True
        return False

    def loot_cells(self,frame):
        """Casillas visibles: [{'kind','rarity','amount','icon'}]; kind GOLD/XP/MATERIAL/ITEM."""
        cells=[]
        for x,y in LOOT_CELLS:
            ring=np.concatenate([frame[y+2:y+6,x+20:x+110].reshape(-1,3),frame[y+20:y+110,x+2:x+6].reshape(-1,3)])
            rarity=loot_rarity(np.median(ring,0).astype(np.uint8))
            if rarity is None:continue
            box=(x,y,x+LOOT_SIZE,y+LOOT_SIZE);amount=self.loot_amount(frame,x,y)
            # El equipo lleva la flecha de comparación (roja/verde) arriba a la izquierda; materiales no.
            c=frame[y+8:y+50,x+8:x+44].astype(int);r,g,b=c[:,:,2],c[:,:,1],c[:,:,0]
            arrow=((r>95)&(r>3*g)&(r>3*b)).sum()>=80 or ((g>120)&(g>2*r)&(g>2*b)).sum()>=80
            kind=('XP' if self.locate(frame,'LOOT_XP',box,.9) else 'GOLD' if self.locate(frame,'LOOT_GOLD',box,.9)
                  else 'ITEM' if arrow else 'MATERIAL')
            if amount is None:amount=0 if kind in ('XP','GOLD') else 1  # oro/XP ilegible: no se inventa
            cells.append({'kind':kind,'rarity':rarity,'amount':amount,'xy':(x+LOOT_SIZE//2,y+LOOT_SIZE//2),
                          'icon':frame[y+10:y+LOOT_SIZE-10,x+10:x+LOOT_SIZE-10].copy()})
        return cells

    def familiar_name(self,frame,candidates=()):
        """Nombre de la oferta: referencia exacta o, si no, lectura emparejada con los familiares de la ruta."""
        if self.screen(frame)!='FAMILIAR_OFFER':return None
        glyph=familiar_glyph(frame)
        if glyph is None:return None
        names=[key[5:] for key,ref in self.templates.items() if key.startswith('NAME_') and np.array_equal(glyph,ref)]
        if len(names)==1:return names[0]
        text=self.read_text(glyph)
        scored=sorted((edit_distance(text,''.join(c for c in name.upper() if c.isalpha())),name) for name in candidates)
        # Un solo candidato a distancia <=1 y sin empate: así un nombre ilegible nunca se confunde con otro.
        if scored and scored[0][0]<=1 and (len(scored)==1 or scored[1][0]>scored[0][0]):return scored[0][1]
        return None

    def setting(self,frame,name):
        """Estado del padre; para audio, True acredita volumen cero, None es lectura desconocida."""
        if self.screen(frame)!='SETTINGS':return None
        key=SETTINGS[name][0]
        pos=self.locate(frame,key,(475,340,1390,860))
        if pos is None:return None
        x,y=pos
        if name in ('music','sound'):
            roi=(830,max(340,y-70),1300,min(860,y+100))
            center=y+(28 if name=='music' else 30)
            bar=frame[center-15:center+15,850:1250]
            b,g,r=bar.astype(np.int16).transpose(2,0,1)
            green=(g>150)&(g>b+60)&(g>r+60)
            blue=(b>130)&(g>100)&(r<100)
            if green.sum()<=10 and self.locate(frame,'AUDIO_ZERO',roi):return True
            return False if green.sum()>10 and blue.sum()>300 else None
        # Solo el padre a x≈478: las rarezas debajo tienen sangría y otro estado.
        for key,state in [('EMPTY',False),('EMPTY_HOVER',False),('CHECKED',True)]:
            if self.locate(frame,key,(x-83,y-15,x-11,y+58),.94):return state
        return None

    def setting_box(self,frame,name):
        """Casilla padre o extremo izquierdo de audio en SETTINGS; None si no se acredita."""
        if self.screen(frame)!='SETTINGS':return None
        pos=self.locate(frame,SETTINGS[name][0],(475,340,1390,860))
        if pos is None:return None
        x,y=pos
        if name in ('music','sound'):
            # El mismo tirador/barra se desplaza con su etiqueta, también con WINDOWED en Steam.
            if self.setting(frame,name) is None:return None
            bar=self.locate(frame,'AUDIO_ZERO',(830,max(340,y-70),1300,min(860,y+100)))
            return (868,bar[1]+43) if bar else (868,y+(28 if name=='music' else 30))
        for key in ('CHECKED','EMPTY','EMPTY_HOVER'):
            box=self.locate(frame,key,(x-83,y-15,x-11,y+58),.94)
            if box:h,w=self.templates[key].shape[:2];return box[0]+w//2,box[1]+h//2
        return None

    def number(self,image):
        mask=(image.min(2)>=170).astype(np.uint8)
        boxes=quantity_boxes(mask)
        if not boxes or any(h<15 or w>h*1.2 or area<20 or x==0 or y==0 or x+w>=mask.shape[1] or y+h>=mask.shape[0]
                            for x,y,w,h,area in boxes):return None
        values=[]
        for x,y,w,h,_ in boxes:
            glyph=cv2.resize(mask[y:y+h,x:x+w],(max(1,round(w*27/h)),27),interpolation=cv2.INTER_NEAREST)
            value,_,source=self.digits.quantity(cv2.cvtColor(np.pad(glyph,5)*255,cv2.COLOR_GRAY2BGR))
            if source!='DIGITS' or value is None or value>9:return None
            values.append(str(value))
        text=''.join(values)
        return int(text) if len(text)<=5 and (len(text)==1 or text[0]!='0') else None

    def energy_clock(self,frame):
        """True si la barra de energía muestra el reloj de recarga (p. ej. 1:41): dos puntos y dígitos."""
        if self.screen(frame)=='TEAM':frame=np.minimum(frame[:80].astype(np.uint16)*2,255).astype(np.uint8)
        pos=self.locate(frame,'ENERGY_ICON',(880,10,1050,78))
        if pos is None:return False
        x,y=pos;mask=(frame[y+1:y+46,x+64:x+229].min(2)>=170).astype(np.uint8)
        boxes=quantity_boxes(mask)
        if not boxes:return False
        tall=max(b[3] for b in boxes)
        # ':' es una caja estrecha con filas vacías en medio (un '1' es continuo); no hay barra '/'.
        colons=[b for b in boxes if b[2]<=8 and b[3]>=0.7*tall and mask[b[1]:b[1]+b[3],b[0]:b[0]+b[2]].any(1).mean()<0.75]
        slashes=[b for b in boxes if b[2]>=1.0*b[3]]
        return len(colons)==1 and not slashes and 3<=len(boxes)<=5

    def energy(self,frame):
        if self.screen(frame)=='TEAM':
            # TEAM oscurece la barra superior al 50 %; calibrado con fixture
            # propia. No reducir filtros de pantallas ni aceptar overlays ajenos.
            frame=np.minimum(frame[:80].astype(np.uint16)*2,255).astype(np.uint8)
        pos=self.locate(frame,'ENERGY_ICON',(880,10,1050,78))
        if pos is None:return None
        x,y=pos;image=frame[y+1:y+46,x+64:x+229]
        mask=(image.min(2)>=170).astype(np.uint8);boxes=quantity_boxes(mask)
        slashes=[ref for key,ref in self.templates.items() if key=='SLASH' or key.startswith('SLASH_')]
        separators=[]
        for bx,by,w,h,_ in boxes:
            for slash in slashes:
                glyph=cv2.resize(mask[by:by+h,bx:bx+w],(slash.shape[1],slash.shape[0]),interpolation=cv2.INTER_NEAREST)
                dice=2*float((glyph*slash).sum())/max(1,glyph.sum()+slash.sum())
                if dice>.95:
                    separators.append((bx,w));break
        if len(separators)!=1:return None  # Reloj/valor ilegible nunca es saldo.
        sx,sw=separators[0]
        balance=self.number(image[:,:sx]);capacity=self.number(image[:,sx+sw:])
        # Saldo > capacidad delata una capacidad truncada; por encima del máximo se pausa.
        return (balance,capacity) if balance is not None and capacity is not None and 0<capacity and balance<=capacity else None

    def dungeon_title(self,frame,identifier):
        key='TITLE_'+identifier
        return key in self.templates and self.locate(frame,key,(440,140,1480,420)) is not None

    def cost(self,frame,difficulty):
        screen=self.screen(frame)
        if difficulty=='Special':
            return 20 if screen=='DUNGEON_SPECIAL' and self.locate(frame,'SPECIAL_COST_20',(700,900,900,1000)) else None
        if screen!='DIFFICULTY':return None
        x={'Normal':625,'Hard':1025,'Heroic':1430}[difficulty]
        return self.number(frame[335:415,x:x+90])
