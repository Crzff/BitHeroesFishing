"""Consumo y compra acotados de los cuatro Minor; sin integración en farm_all."""

import os
import json
import time
from pathlib import Path

import cv2
import numpy as np

from .control_flow import SafetyStop
from .dungeon_runtime import DungeonRunner
from .dungeon_vision import text_letters
from .protocol import atomic_json

BOOSTS={'item_find':'Minor Item Find Scroll','xp':'Minor Experience Tome',
        'gold':'Minor Gold Potion','speed':'Minor Speed Kicks'}
LIST_ROI=(1090,330,1540,930)
PROFILE_CLOSE=(1652,112)
KEYS=('active','slot','flag','filter','consumables','consumables_selected','profile_close','activated','done','yes',
      *BOOSTS,*(f'confirm_{kind}' for kind in BOOSTS),
      'shop','shop_tab','shop_list','shop_close','one','coin','diamond','no',
      'purchase_header','purchase_item_find','purchase_name_xp','purchase_name_gold','purchase_name_speed','purchase_gold','price_10000','price_5000',
      'coin_xp','coin_speed','price_10000_right','price_5000_right','price_5000_dialog',
      *(f'shop_{kind}' for kind in BOOSTS))
SHOP_ROI=(320,330,1540,905)
PRICES={'item_find':10000,'xp':10000,'gold':5000,'speed':5000}


class BoostsRunner(DungeonRunner):
    def __init__(self,io,capture,vision,channel,log):
        self.io,self.cap,self.vision,self.channel,self.log=io,capture,vision,channel,log
        for key in KEYS:
            name='BOOST_'+key.upper()
            if name not in self.vision.templates:
                template=cv2.imread(str(Path(__file__).resolve().parent.parent/f'assets/boost_{key}.png'))
                if template is None:raise SafetyStop(f'Plantilla {name} no disponible')
                self.vision.templates[name]=template
        # El cofre y el cartel FREE de la tienda se animan: comparar solo píxeles comunes a las variantes reales.
        shop=self.vision.templates['BOOST_SHOP'];towns=[cv2.imread(str(Path(__file__).resolve().parent.parent/f'assets/boost_shop_town{i}.png')) for i in (1,2)]
        if all(t is not None and t.shape==shop.shape for t in towns):
            self.vision.home_masks['BOOST_SHOP']=np.all([np.all(shop==t,axis=2) for t in towns],axis=0).astype(np.uint8)
        # Casilla de boost: solo el anillo del marco (el icono cambia y la barra pasa de verde a amarillo con el tiempo).
        ring=np.ones(self.vision.templates['BOOST_SLOT'].shape[:2],np.uint8);ring[13:-13,13:-13]=0
        self.vision.home_masks['BOOST_SLOT']=ring
        # Oro reparte el nombre en dos líneas; excluir FOR y el precio de la segunda.
        name_mask=np.ones(self.vision.templates['BOOST_PURCHASE_NAME_GOLD'].shape[:2],np.uint8)
        name_mask[40:,185:]=0
        self.vision.home_masks['BOOST_PURCHASE_NAME_GOLD']=name_mask
        self.deadline=time.monotonic()+10*60

    def boosts_active(self,frame):
        return self.locate(frame,'slot',(425,955,1100,1080)) is not None

    def locate(self,frame,key,roi):
        # FILTER cambia algo de tono entre cuentas (KORTZZ: correlación 0,979, diferencia 12,8).
        return self.vision.locate(frame,'BOOST_'+key.upper(),roi,max_diff=20 if key=='filter' else 12)

    def on(self,key,roi):
        return lambda f:self.locate(f,key,roi) is not None

    def wait(self,predicate,timeout=10,expected=None):
        """Estados desconocidos esperan y paran; no atraviesan diálogos ajenos."""
        end=time.monotonic()+timeout;stable=0
        while time.monotonic()<end:
            frame=self.capture()
            okay=predicate(frame) if callable(predicate) else self.vision.screen(frame)==predicate
            stable=stable+1 if okay else 0
            if stable>=2:return frame
            time.sleep(.12)
        raise SafetyStop(f'Pantalla no confirmada: {expected or predicate}')

    def press(self,xy,key,roi,also=None):
        # Recaptura justo antes del input: una plantilla anterior no autoriza el clic.
        frame=self.capture()
        if self.locate(frame,key,roi) is None:raise SafetyStop(f'{key} no visible; no se pulsa')
        if also and self.locate(frame,*also) is None:raise SafetyStop(f'{also[0]} no visible; no se pulsa')
        self.check();self.io.click(tuple(int(n) for n in xy));time.sleep(.25)
        self.check();self.io._move((960,1070))
        self.log.emit('DUNGEON_INPUT',screen='BOOST_'+key.upper(),xy=list(xy))

    def bottom(self):
        previous=None;stable=0
        for _ in range(20):
            frame=self.wait(self.on('filter',(1070,180,1605,295)),10,'inventario')
            current=frame[330:930,1090:1585].copy()
            stable=stable+1 if previous is not None and np.array_equal(current,previous) else 0
            if stable>=2:return frame
            previous=current
            self.check();self.wheel(8,(1450,700));self.check();self.io._move((960,1070));time.sleep(.5)
        raise SafetyStop('El inventario no llegó a un final estable')

    def consume(self,kind):
        frame=self.bottom();pos=self.locate(frame,kind,LIST_ROI)
        if pos is None:
            self.log.emit('BOOST_MISSING',boost=BOOSTS[kind],message=f'Falta {BOOSTS[kind]}')
            return False
        # La referencia incluye dibujo y borde verde, pero excluye el contador variable.
        ref=self.vision.templates['BOOST_'+kind.upper()];x,y=pos
        xy=(x+ref.shape[1]//2,y+ref.shape[0]//2)
        roi=(x,y,x+ref.shape[1],y+ref.shape[0])
        self.press(xy,kind,roi)
        confirm='confirm_'+kind;area=(690,455,1230,625)
        try:self.wait(self.on(confirm,area),5,f'confirmación de {BOOSTS[kind]}')
        except SafetyStop:
            if self.locate(self.capture(),'no',(990,695,1230,800)) is not None:
                self.press((1102,748),'no',(990,695,1230,800))
            raise
        # El nombre y YES deben coexistir en la captura inmediatamente anterior al gasto.
        self.press((814,748),confirm,area,('yes',(690,695,945,800)))
        self.wait(self.on('activated',(500,20,1410,120)),10,'boost activado')
        self.press((960,994),'done',(770,945,1150,1050),('activated',(500,20,1410,120)))
        self.wait(self.on('filter',(1070,180,1605,295)),10,'inventario tras boost')
        self.log.emit('BOOST_CONSUMED',boost=BOOSTS[kind])
        return True

    def price(self,image,expected,green=False):
        # Mismo alfabeto pixelado: normalizar blanco de la lista y verde del diálogo.
        def letters(img):
            mask=((img.min(2)>=170)|((img[:,:,1]>=170)&(img[:,:,0]<160)&(img[:,:,2]<160))).astype(np.uint8)
            ys=np.nonzero(mask.any(1))[0]
            return text_letters(mask[ys.min():ys.max()+1]) if len(ys) else []
        if green:
            image=image.copy()
            image[~((image[:,:,1]>=170)&(image[:,:,0]<160)&(image[:,:,2]<160))]=0
        actual=letters(image)
        for suffix in ('','_RIGHT',*(('_DIALOG',) if expected==5000 else ())):
            reference=letters(self.vision.templates[f'BOOST_PRICE_{expected}{suffix}'])
            if len(actual)==len(reference) and bool(actual) and all(
                    a.shape==b.shape and np.mean(a==b)>=.97 for a,b in zip(actual,reference)):return True
        return False

    def shop_ready(self,frame):
        return (self.locate(frame,'shop_list',(1000,180,1250,255)) is not None and
                self.locate(frame,'one',(870,950,980,1030)) is not None and
                self.locate(frame,'purchase_header',(780,265,1140,370)) is None)

    def shop_article(self,frame,kind):
        if not self.shop_ready(frame):raise SafetyStop('Lista de tienda o 1x desconocidos')
        pos=self.locate(frame,'shop_'+kind,SHOP_ROI)
        if pos is None:return None
        x,y=pos;left=560 if x<940 else 1185
        # Los nombres ocupan dos líneas; el precio está 120 px debajo en la misma tarjeta.
        box=(left,y+120,left+335,y+205);l,t,r,b=box
        if b>905:return None  # precio aún bajo el borde: seguir bajando con la rueda
        coin='coin_'+kind if kind in ('xp','speed') else 'coin'
        if (self.locate(frame,coin,box) is None or self.locate(frame,'diamond',box) is not None or
                not self.price(frame[t+10:b-10,l+155:r-10],PRICES[kind])):
            raise SafetyStop('Precio o moneda del Minor no confirmados')
        return ((l+r)//2,(t+b)//2)

    def purchase_valid(self,frame,kind):
        area=(630,450,1290,630)
        if self.locate(frame,'purchase_gold',area) is None:return False
        names=[k for k in BOOSTS if self.locate(frame,'purchase_item_find' if k=='item_find' else 'purchase_name_'+k,area) is not None]
        if names!=[kind]:return False
        pos=self.locate(frame,'purchase_gold',area)
        x,y=pos
        if kind=='gold':return self.price(frame[y-44:y,1020:1230],PRICES[kind],green=True)
        return self.price(frame[y:y+47,690:x-15],PRICES[kind],green=True)

    def reject_purchase(self):
        self.press((1102,748),'no',(990,695,1230,800),('purchase_header',(780,265,1140,370)))
        raise SafetyStop('Confirmación de compra no coincide')

    def quota_path(self):
        from .accounts import account_id,steam_account
        from .telemetry import ROOT
        account=account_id() or steam_account()
        if account is None:raise SafetyStop('Cuenta de compras no identificada')
        return ROOT/'runs/accounts'/account/'boost_purchases.json'

    def quota(self):
        path=self.quota_path();now=time.time()
        try:
            data=json.loads(path.read_text()) if path.exists() else {'purchases':[]}
            entries=data['purchases']
            if not isinstance(entries,list):raise ValueError('cuota inválida')
            for entry in entries:
                if (entry['boost'] not in BOOSTS or type(entry['time']) not in (int,float) or
                        not np.isfinite(entry['time']) or entry['time']>now or
                        type(entry['cost']) is not int or entry['cost']!=PRICES[entry['boost']] or
                        type(entry['confirmed']) is not bool):raise ValueError('reserva inválida')
        except (OSError,ValueError,KeyError,TypeError) as exc:
            raise SafetyStop('Cuota de boosts ilegible o inválida') from exc
        return path,[entry for entry in entries if now-entry['time']<24*60*60]

    def quota_available(self,entries,kinds):
        okay=len(entries)+len(kinds)<=4 and sum(e['cost'] for e in entries)+sum(PRICES[k] for k in kinds)<=30000
        if not okay:self.log.emit('BOOST_QUOTA',message='Cuota de compras Minor agotada')
        return okay

    def buy_missing(self,missing):
        if not missing:return
        from . import farm_config
        if farm_config.load().get('boosts_buy') is not True:return
        if missing!=getattr(self,'missing',None):raise SafetyStop('Compra sin faltantes de run()')
        kinds=[kind for kind in BOOSTS if BOOSTS[kind] in missing]
        if len(kinds)!=len(missing):raise SafetyStop('Faltantes inválidos')
        _,entries=self.quota()
        if not self.quota_available(entries,kinds):return
        for kind in kinds:
            if (self.channel.directory/f'boost-{kind}.intent.json').exists():
                raise SafetyStop('Ya existe intención de compra; no se repite')
        # missing solo existe si run() empezó sin ningún boost activo; los Minor que sí estaban ya se consumieron.
        self.ensure_home()
        self.press((1748,100),'shop',(1700,60,1880,180))
        # La tienda recuerda la última pestaña: puede abrirse ya en BOOSTS (en vivo, FMANI).
        tab=self.on('shop_tab',(1000,180,1250,255));listed=self.on('shop_list',(1000,180,1250,255))
        frame=self.wait(lambda f:tab(f) or listed(f),10,'tienda')
        if not listed(frame):self.press((1116,218),'shop_tab',(1000,180,1250,255))
        self.wait(self.shop_ready,10,'lista BOOSTS 1x')
        for kind in kinds:
            self.check();self.wheel(-30,(930,600));time.sleep(.5)
            for _ in range(16):
                frame=self.capture();xy=self.shop_article(frame,kind)
                if xy is not None:break
                self.check();self.wheel(2,(930,600));time.sleep(.5)
            else:raise SafetyStop('Minor no localizado en tienda')
            # Revalidar artículo, moneda, cantidad y precio inmediatamente antes del clic.
            if self.shop_article(self.capture(),kind)!=xy:raise SafetyStop('Artículo cambió')
            self.check();self.io.click(xy);time.sleep(.25);self.io._move((960,1070))
            self.wait(self.on('purchase_header',(780,265,1140,370)),5,'confirmación de compra')
            frame=self.capture()
            if not self.purchase_valid(frame,kind):self.reject_purchase()
            path=self.channel.directory/f'boost-{kind}.intent.json'
            if path.exists():self.reject_purchase()
            quota_path,entries=self.quota()
            if not self.quota_available(entries,[kind]):self.reject_purchase()
            reservation={'boost':kind,'cost':PRICES[kind],'time':time.time(),'confirmed':False}
            entries.append(reservation)
            atomic_json(quota_path,{'purchases':entries})
            intent={'boost':BOOSTS[kind],'quantity':1,'cost':PRICES[kind],
                    'currency':'GOLD','effect_confirmed':False}
            atomic_json(path,intent)
            frame=self.capture()
            if (not self.purchase_valid(frame,kind) or
                    self.locate(frame,'purchase_header',(780,265,1140,370)) is None or
                    self.locate(frame,'yes',(690,695,945,800)) is None):self.reject_purchase()
            self.check();self.io.click((814,748));time.sleep(.25);self.io._move((960,1070))
            self.log.emit('DUNGEON_INPUT',screen='BOOST_PURCHASE_YES',xy=[814,748])
            # Solo la desaparición del diálogo y la lista permiten continuar; sin clics de recuperación.
            self.wait(self.shop_ready,10,'lista tras YES')
            reservation['confirmed']=True
            atomic_json(quota_path,{'purchases':entries})
            atomic_json(path,{**intent,'effect_confirmed':True})
            self.log.emit('BOOST_BOUGHT',boost=BOOSTS[kind],quantity=1,gold=PRICES[kind])
        self.press((1660,146),'shop_close',(1600,80,1730,210),('shop_list',(1000,180,1250,255)))
        self.wait('HOME')
        self.press((90,1010),'slot',(320,955,430,1080),('slot',(320,955,430,1080)))
        self.wait(self.on('filter',(1070,180,1605,295)),10,'perfil')
        self.press((1338,238),'filter',(1070,180,1605,295))
        consumables=lambda f:next((k for k in ('consumables','consumables_selected') if self.locate(f,k,(980,535,1405,625)) is not None),None)
        key=consumables(self.wait(consumables,10,'filtro'))  # el juego recuerda el filtro: puede verse ya seleccionado
        self.press((1186,578),key,(980,535,1405,625))
        for kind in kinds:
            if not self.consume(kind):raise SafetyStop('Minor comprado ausente del inventario')
        self.press(PROFILE_CLOSE,'profile_close',(1590,55,1710,170))
        self.wait('HOME');self.missing=[]

    def leave_profile(self):
        """Al reanudar: cerrar el filtro y el perfil que hayan quedado abiertos (ensure_home no los conoce)."""
        for _ in range(3):
            frame=self.capture()
            if self.locate(frame,'shop_close',(1600,80,1730,210)) is not None and \
                    any(self.locate(frame,k,(1000,180,1250,255)) is not None for k in ('shop_tab','shop_list')):
                self.press((1660,146),'shop_close',(1600,80,1730,210));time.sleep(1);continue  # tienda abierta al reanudar
            if any(self.locate(frame,k,(980,535,1405,625)) is not None for k in ('consumables','consumables_selected')):
                self.check();self.io.click((1500,290));time.sleep(1);continue
            if self.locate(frame,'filter',(1070,180,1605,295)) is not None and self.locate(frame,'profile_close',(1590,55,1710,170)) is not None:
                self.press(PROFILE_CLOSE,'profile_close',(1590,55,1710,170));time.sleep(1);continue
            return

    def run(self):
        self.missing=[]
        self.leave_profile();self.ensure_home()
        frame=self.wait(lambda f:self.vision.screen(f)=='HOME' and self.on('slot',(320,955,430,1080))(f),10,'Home con botón de letra')  # la letra (F, S, T...) cambia a diario
        if self.boosts_active(frame):
            self.log.emit('BOOSTS_STATUS',message='ya activos')
            return []
        self.press((90,1010),'slot',(320,955,430,1080),('slot',(320,955,430,1080)))
        self.wait(self.on('filter',(1070,180,1605,295)),10,'perfil')
        self.press((1338,238),'filter',(1070,180,1605,295))
        consumables=lambda f:next((k for k in ('consumables','consumables_selected') if self.locate(f,k,(980,535,1405,625)) is not None),None)
        key=consumables(self.wait(consumables,10,'filtro'))  # el juego recuerda el filtro: puede verse ya seleccionado
        self.press((1186,578),key,(980,535,1405,625))
        missing=[BOOSTS[kind] for kind in BOOSTS if not self.consume(kind)]
        self.press(PROFILE_CLOSE,'profile_close',(1590,55,1710,170))
        self.wait('HOME')
        self.log.emit('BOOSTS_STATUS',missing=missing,message='Boosts revisados')
        self.missing=missing.copy()
        return missing


def run_boosts():
    from .game_window import ENV_WINDOW,focus_window
    from .dungeon_vision import DungeonVision
    from .gamescope import backend
    from .processes import Mutex
    from .protocol import Channel
    from .telemetry import Telemetry,run_environment
    LinuxIO,LinuxCapture=backend()
    locks=[Mutex(role) for role in ('LAUNCHER','CONTROL','CATCH')];io=log=None
    try:
        env=run_environment();channel=Channel(env['FISHING_RUN_ID'])
        if os.environ.get('FARM_BACKEND') not in ('gamescope','cdp'):os.environ[ENV_WINDOW]=focus_window('Steam').serialize()
        os.environ.pop('FARM_LAUNCHER_PID',None)
        log=Telemetry('BOOSTS',channel.run_id);io=LinuxIO();io.control_mode=True
        with LinuxCapture(io.game_guard) as capture:
            runner=BoostsRunner(io,capture,DungeonVision(),channel,log)
            missing=runner.run()
            runner.buy_missing(missing)
            return runner.missing
    except (Exception,KeyboardInterrupt) as exc:
        if log:log.emit('SAFETY_STOP',message=str(exc) or 'F8',reason=str(exc) or 'F8',human=True)
        raise
    finally:
        if io:io.close()
        if log:log.close()
        for lock in reversed(locks):lock.close()
