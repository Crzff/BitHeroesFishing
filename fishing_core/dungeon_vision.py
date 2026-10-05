"""Reconocimiento puro y conservador de la primera ruta de dungeons."""

from pathlib import Path

import cv2
import numpy as np

from .bait_inventory import BaitReader,quantity_boxes

ASSETS=Path(__file__).resolve().parent.parent/'assets/dungeon_templates.npz'


def familiar_glyph(frame):
    roi=frame[130:205,350:1570]
    mask=((roi.max(2)>=170)&(roi.max(2).astype(np.int16)-roi.min(2)>=50)).astype(np.uint8)*255
    ys,xs=np.nonzero(mask)
    return mask[ys.min():ys.max()+1,xs.min():xs.max()+1] if len(xs) else None


# Ventanas de otros modos: cada una exige título y botón propios (ROI con holgura).
MODE_SCREENS=(('DISCONNECTED',(('DISCONNECTED',(720,430,1200,640)),('RECONNECT',(770,665,1150,820)))),
              ('SEASON_REWARDS',(('SEASON_TITLE',(600,150,1320,310)),('SEASON_CLAIM',(740,885,1180,1040)))),
              ('ITEMS',(('ITEMS_TITLE',(600,150,1320,450)),('ITEMS_CLOSE',(1200,150,1500,450)))),
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


class DungeonVision:
    def __init__(self,path=ASSETS):
        with np.load(path,allow_pickle=False) as data:
            self.templates={key:data[key] for key in data.files}
        # ponytail: dos fondos observados; máscara alfa etiquetada si otro fondo falla.
        # El fondo de la ciudad cambia: comparar solo los píxeles comunes a todas las variantes observadas.
        self.home_masks={key:np.all([np.all(self.templates[key]==self.templates[v],axis=2) for v in self.templates
                                     if v.startswith(key+'_TOWN')],axis=0).astype(np.uint8)
                         for key in ('HOME_QUEST','HOME_SETTINGS','HOME_BOSS','HOME_PVP','HOME_RAID','HOME_EXPEDITION','HOME_TRIALS')
                         if any(v.startswith(key+'_TOWN') for v in self.templates)}
        self.digits=BaitReader(extra={k:v for k,v in self.templates.items() if k.startswith('DIGIT_')})

    def locate(self,frame,key,roi,threshold=.97):
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
        if score>=threshold and float(difference.mean())<=12:return x+px,y+py
        return self.locate(frame,'HEROIC_IDLE',roi,threshold) if key=='HEROIC' else None

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
        if (self.locate(frame,'DECLINE_CONFIRM',(700,455,1220,620)) and
                self.locate(frame,'DECLINE_YES',(670,695,955,805))):return 'DECLINE_CONFIRM'
        if (self.locate(frame,'WB_NOT_FULL',(680,410,1240,575)) and
                self.locate(frame,'DECLINE_YES',(670,695,955,805))):return 'WB_NOT_FULL'
        if (self.locate(frame,'CONFIRM_HEADER',(770,270,1150,370)) and self.locate(frame,'PERSUADE_GOLD',(800,500,1320,640))
                and self.locate(frame,'DECLINE_YES',(670,695,955,805))):return 'PERSUADE_CONFIRM'
        if (self.locate(frame,'CAPTURE_SUCCESS',(540,50,1380,170)) and
                self.locate(frame,'CAPTURE_CLOSE',(780,890,1140,1040))):return 'CAPTURE_SUCCESS'
        if self.locate(frame,'CONFIRM_HEADER',(770,270,1150,370)):return 'UNKNOWN'
        if (self.locate(frame,'PERSUADE',(360,640,720,780)) and
                self.locate(frame,'BRIBE',(1240,640,1535,780)) and
                self.locate(frame,'DECLINE',(550,890,965,1015))):return 'FAMILIAR_OFFER'
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
        image=frame[560:630,490:665].copy();mask=(image.min(2)>=170).astype(np.uint8)
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
        if best[0][1]<0.7 or best[0][1]-best[1][1]<0.15:return None
        rarity=rune_rarity(float(np.median(hsv[:,:,0][body])),float(np.median(hsv[:,:,1][body])))
        if rarity is None:return None
        kind=best[0][0];return kind,rarity,RUNE_VALUES[kind][RARITIES.index(rarity)]

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

    def familiar_name(self,frame):
        if self.screen(frame)!='FAMILIAR_OFFER':return None
        glyph=familiar_glyph(frame)
        # ponytail: nombres con referencia exacta; ampliar referencias u OCR validado para otros.
        names=[key[5:] for key,ref in self.templates.items() if key.startswith('NAME_') and np.array_equal(glyph,ref)]
        return names[0] if len(names)==1 else None

    def setting(self,frame,name):
        if self.screen(frame)!='SETTINGS':return None
        key={'gold':'GOLD','gems':'GEMS','duplicates':'DUPLICATES'}[name]
        pos=self.locate(frame,key,(550,340,1390,860))
        if pos is None:return None
        x,y=pos
        # Solo el padre a x≈478: las rarezas debajo tienen sangría y otro estado.
        for key,state in [('EMPTY',False),('EMPTY_HOVER',False),('CHECKED',True)]:
            if self.locate(frame,key,(x-83,y-15,x-11,y+58),.94):return state
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
