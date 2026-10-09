"""Consumo acotado de los cuatro boosts Minor, sin compras ni integración en farm_all."""

import os
import time
from pathlib import Path

import cv2
import numpy as np

from .control_flow import SafetyStop
from .dungeon_runtime import DungeonRunner

BOOSTS={'item_find':'Minor Item Find Scroll','xp':'Minor Experience Tome',
        'gold':'Minor Gold Potion','speed':'Minor Speed Kicks'}
LIST_ROI=(1090,330,1540,930)
PROFILE_CLOSE=(1652,112)
KEYS=('active','flag','filter','consumables','profile_close','activated','done','yes',
      *BOOSTS,*(f'confirm_{kind}' for kind in BOOSTS))


class BoostsRunner(DungeonRunner):
    def __init__(self,io,capture,vision,channel,log):
        self.io,self.cap,self.vision,self.channel,self.log=io,capture,vision,channel,log
        for key in KEYS:
            name='BOOST_'+key.upper()
            if name not in self.vision.templates:
                template=cv2.imread(str(Path(__file__).resolve().parent.parent/f'assets/boost_{key}.png'))
                if template is None:raise SafetyStop(f'Plantilla {name} no disponible')
                self.vision.templates[name]=template
        self.deadline=time.monotonic()+10*60

    def locate(self,frame,key,roi):
        return self.vision.locate(frame,'BOOST_'+key.upper(),roi)

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
        self.wait(self.on(confirm,area),5,f'confirmación de {BOOSTS[kind]}')
        # El nombre y YES deben coexistir en la captura inmediatamente anterior al gasto.
        self.press((814,748),confirm,area,('yes',(690,695,945,800)))
        self.wait(self.on('activated',(500,20,1410,120)),10,'boost activado')
        self.press((960,994),'done',(770,945,1150,1050),('activated',(500,20,1410,120)))
        self.wait(self.on('filter',(1070,180,1605,295)),10,'inventario tras boost')
        self.log.emit('BOOST_CONSUMED',boost=BOOSTS[kind])
        return True

    def run(self):
        self.ensure_home()
        frame=self.wait(self.on('flag',(320,960,425,1060)),10,'Home con botón F')
        if self.locate(frame,'active',(425,1038,1100,1075)) is not None:
            self.log.emit('BOOSTS_STATUS',message='ya activos')
            return []
        self.press((90,1010),'flag',(320,960,425,1060))
        self.wait(self.on('filter',(1070,180,1605,295)),10,'perfil')
        self.press((1338,238),'filter',(1070,180,1605,295))
        self.wait(self.on('consumables',(980,535,1405,625)),10,'filtro')
        self.press((1186,578),'consumables',(980,535,1405,625))
        missing=[BOOSTS[kind] for kind in BOOSTS if not self.consume(kind)]
        self.press(PROFILE_CLOSE,'profile_close',(1590,55,1710,170))
        self.wait('HOME')
        self.log.emit('BOOSTS_STATUS',missing=missing,message='Boosts revisados')
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
        if os.environ.get('FARM_BACKEND')!='gamescope':os.environ[ENV_WINDOW]=focus_window('Steam').serialize()
        os.environ.pop('FARM_LAUNCHER_PID',None)
        log=Telemetry('BOOSTS',channel.run_id);io=LinuxIO();io.control_mode=True
        with LinuxCapture(io.game_guard) as capture:
            return BoostsRunner(io,capture,DungeonVision(),channel,log).run()
    except (Exception,KeyboardInterrupt) as exc:
        if log:log.emit('SAFETY_STOP',message=str(exc) or 'F8',reason=str(exc) or 'F8',human=True)
        raise
    finally:
        if io:io.close()
        if log:log.close()
        for lock in reversed(locks):lock.close()
