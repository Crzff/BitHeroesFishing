"""GvG semanal: insignias, rivales de PvP y confirmación de gremio acotada."""

import os
import time
from pathlib import Path

import cv2
import numpy as np

from .control_flow import SafetyStop
from .pvp_runtime import PvpRunner,ACCEPT,AUTO,BATTLE_LIMIT,TOWN_ROI
from .protocol import atomic_json

HOME=((1828,540),'GVG_HOME',(1740,465,1910,635))
PLAY=((1280,580),'GVG_PLAY',(1120,480,1445,700))
CLOSE=((1490,240),'GVG_CLOSE',(1410,140,1580,310))
TEXT_ROI=(630,400,1290,675)
YES=((814,748),'GVG_YES',(690,695,945,800))
NO=((1102,748),'GVG_NO',(990,695,1230,800))


class GvgVision:
    """Extensión local; conserva el lector y las plantillas compartidas."""
    def __init__(self,vision):
        self.base=vision
        for key in ('home','home_town','title','play','close','confirm','flee','yes','no'):
            template=cv2.imread(str(Path(__file__).resolve().parent.parent/f'assets/gvg_{key}.png'))
            if template is None:raise SafetyStop(f'Plantilla GVG_{key.upper()} no disponible')
            vision.templates['GVG_'+key.upper()]=template
        vision.home_masks['GVG_HOME']=np.all(vision.templates['GVG_HOME']==vision.templates['GVG_HOME_TOWN'],axis=2).astype(np.uint8)

    def __getattr__(self,name):return getattr(self.base,name)

    def screen(self,frame):
        if frame.shape!=(1080,1920,3):return 'UNKNOWN'
        if self.locate(frame,'GVG_FLEE',TEXT_ROI) is not None:return 'GVG_FLEE'
        if (self.locate(frame,'CONFIRM_HEADER',(770,270,1150,370)) is not None and
                self.locate(frame,'GVG_CONFIRM',TEXT_ROI,threshold=.999,max_diff=1) is not None and
                self.locate(frame,'GVG_YES',YES[2]) is not None):return 'GVG_CONFIRM'
        if (self.locate(frame,'GVG_TITLE',(620,170,1300,280)) is not None and
                self.locate(frame,'GVG_PLAY',PLAY[2]) is not None):return 'GVG'
        return self.base.screen(frame)


class GvgRunner(PvpRunner):
    def __init__(self,io,capture,vision,channel,log,fights,opponent=4):
        super().__init__(io,capture,GvgVision(vision),channel,log,fights,opponent)

    def wait(self,predicate,timeout=10,expected=None):
        # No atravesar historias ni diálogos desconocidos durante este evento.
        end=time.monotonic()+timeout;stable=0
        while time.monotonic()<end:
            frame=self.capture();screen=self.vision.screen(frame)
            if screen=='GVG_FLEE':
                self.click('GVG_FLEE',*NO)
                raise SafetyStop('Huida GvG rechazada; revisar estado')
            if screen=='UNKNOWN' and self.vision.locate(frame,'CONFIRM_HEADER',(770,270,1150,370)) is not None:
                raise SafetyStop('Confirmación GvG desconocida; no se pulsa YES')
            okay=predicate(frame) if callable(predicate) else screen==predicate
            stable=stable+1 if okay else 0
            if stable>=2:return frame
            time.sleep(.12)
        raise SafetyStop(f'Pantalla no confirmada: {expected or predicate}')

    def open(self):
        if self.vision.screen(self.capture())=='GVG':return
        screen=self.ensure_home(keep=('GVG',))
        if screen=='HOME':self.press('HOME',HOME);self.wait('GVG')

    def badges(self):
        seen=None
        def known(frame):
            nonlocal seen
            current=self.vision.number(frame[108:145,900:1020]) if self.vision.screen(frame)=='GVG' else None
            okay=current is not None and current==seen;seen=current
            return okay
        self.wait(known,30,'saldo de insignias')
        return seen

    def choose_opponent(self):
        frame=self.wait(lambda f:self.vision.screen(f) in ('GVG_CONFIRM','PVP_SELECT'),10,'confirmación o rivales GvG')
        if self.vision.screen(frame)=='GVG_CONFIRM':
            # click recaptura: el texto completo y YES siguen siendo obligatorios.
            self.press('GVG_CONFIRM',YES)
        super().choose_opponent()

    def fight(self,cycle):
        self.open();balance=self.badges()
        if balance<1:return None
        cost=self.set_cost('GVG',min(5,balance),'COST_MENU_BADGES')
        attempt=f'{self.channel.run_id}:{cycle}'
        if not self.budget.reserve_entry(attempt,resource='BADGES',balance=balance,cost=cost):
            raise SafetyStop('Combate ya reservado; no repetir PLAY')
        path=self.channel.directory/f'gvg-{cycle}.intent.json'
        atomic_json(path,{'attempt_id':attempt,'badges':balance,'effect_confirmed':False})
        self.press('GVG',PLAY);self.choose_opponent();self.press('TEAM',ACCEPT)
        self.log.emit('GVG_STARTED',attempt_id=attempt,badges_before=balance)
        results=('WB_VICTORY','WB_DEFEAT');battle=('AUTO_OFF_BATTLE','AUTO_ON_BATTLE')+results
        frame=self.wait(lambda f:self.vision.screen(f) in battle+('WB_NOT_FULL',),30,'combate GvG')
        if self.vision.screen(frame)=='WB_NOT_FULL':
            self.click('WB_NOT_FULL',(816,750),'DECLINE_YES',(670,695,955,805))
            frame=self.wait(lambda f:self.vision.screen(f) in battle,30,'combate GvG')
        if self.vision.screen(frame)=='AUTO_OFF_BATTLE':self.click('AUTO_OFF_BATTLE',AUTO)
        frame=self.wait(lambda f:self.vision.screen(f) in results,BATTLE_LIMIT,'resultado GvG')
        screen=self.vision.screen(frame);outcome='VICTORY' if screen=='WB_VICTORY' else 'DEFEAT'
        if outcome=='VICTORY':self.record_loot()
        pos=self.vision.locate(frame,'RESULT_TOWN',TOWN_ROI)
        if pos is None:raise SafetyStop('TOWN GvG no confirmado')
        x,y=pos;h,w=self.vision.templates['RESULT_TOWN'].shape[:2]
        self.click(screen,(x+w//2,y+h//2),'RESULT_TOWN',TOWN_ROI);self.wait('GVG',15)
        self.budget.finish_run(attempt,outcome,closure_confirmed=True)
        atomic_json(path,{'attempt_id':attempt,'outcome':outcome,'effect_confirmed':True})
        self.log.emit('GVG_COMPLETE',message=f'GvG {cycle}: {outcome}',budget=self.budget.payload())
        return outcome

    def run(self):
        for cycle in range(1,self.fights+1):
            if self.fight(cycle) is None:break
        self.press('GVG',CLOSE);self.wait('HOME')
        self.log.emit('GVG_STATUS',message='Insignias gastadas · detenido',budget=self.budget.payload())


def run_gvg(fights):
    from .game_window import ENV_WINDOW,focus_window
    from .dungeon_vision import DungeonVision
    from .gamescope import backend
    from .processes import Mutex
    from .protocol import Channel
    from .telemetry import Telemetry,run_environment
    LinuxIO,LinuxCapture=backend()
    if os.name=='nt':raise ValueError('GvG aún no certificado en Windows')
    locks=[Mutex(role) for role in ('LAUNCHER','CONTROL','CATCH')];io=log=None
    try:
        env=run_environment();channel=Channel(env['FISHING_RUN_ID'])
        if os.environ.get('FARM_BACKEND')!='gamescope':os.environ[ENV_WINDOW]=focus_window('Steam').serialize()
        os.environ.pop('FARM_LAUNCHER_PID',None)
        log=Telemetry('GVG',channel.run_id);io=LinuxIO();io.control_mode=True
        with LinuxCapture(io.game_guard) as capture:
            GvgRunner(io,capture,DungeonVision(),channel,log,fights).run()
    except (Exception,KeyboardInterrupt) as exc:
        if log:log.emit('SAFETY_STOP',message=str(exc) or 'F8',reason=str(exc) or 'F8',human=True)
        raise
    finally:
        if io:io.close()
        if log:log.close()
        for lock in reversed(locks):lock.close()
