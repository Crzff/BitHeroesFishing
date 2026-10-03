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


class DungeonVision:
    def __init__(self,path=ASSETS):
        with np.load(path,allow_pickle=False) as data:
            self.templates={key:data[key] for key in data.files}
        # ponytail: dos fondos observados; máscara alfa etiquetada si otro fondo falla.
        self.home_masks={key:np.all(self.templates[key]==self.templates[key+'_TOWN'],axis=2).astype(np.uint8)
                         for key in ('HOME_QUEST','HOME_SETTINGS')}
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
        if self.locate(frame,'CONFIRM_HEADER',(770,270,1150,370)):return 'UNKNOWN'
        if (self.locate(frame,'PERSUADE',(360,640,720,780)) and
                self.locate(frame,'BRIBE',(1240,640,1535,780)) and
                self.locate(frame,'DECLINE',(550,890,965,1015))):return 'FAMILIAR_OFFER'
        if self.locate(frame,'LOADING',(790,470,1130,550)):return 'LOADING'
        if self.locate(frame,'ZONES_MENU',(820,120,1100,215)):return 'ZONES'
        regions=[('VICTORY',(780,110,1150,210)),('SETTINGS',(760,100,1160,215)),
                 ('TEAM',(830,90,1100,200)),('DIFFICULTY_Z5D2',(540,160,1380,265)),
                 ('DIFFICULTY_Z5D3',(540,160,1380,265))]
        for key,roi in regions:
            if self.locate(frame,key,roi):return key
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
        return (balance,capacity) if balance is not None and capacity is not None and capacity>0 else None

    def cost(self,frame,difficulty):
        if self.screen(frame) not in ('DIFFICULTY_Z5D2','DIFFICULTY_Z5D3'):return None
        x={'Normal':625,'Hard':1025,'Heroic':1430}[difficulty]
        return self.number(frame[335:415,x:x+90])
