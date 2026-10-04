"""Expedition (evento semanal; esta semana Idol Dimension): gasta todos los badges.

Perder es normal en Expedition: una derrota se cierra y se sigue. El evento cambia
cada semana; si la ventana o el mapa no coinciden con las plantillas, se detiene.
"""

import os
import time

import numpy as np

from .control_flow import SafetyStop
from .dungeon_runtime import DungeonRunner
from .farm_budget import FarmBudget
from .protocol import atomic_json

BADGE_COST=5
HOME_EXP=((1830,560),'HOME_EXPEDITION',(1720,440,1920,680))
PLAY=((1280,576),'EXP_PLAY',(1120,440,1445,710))
EXP_CLOSE=((1490,240),'EXP_CLOSE',(1400,150,1580,330))
PORTAL=((960,652),'PORTAL_COLISEUM',(830,545,1090,760))
IDOL_CLOSE=((1655,135),'IDOL_CLOSE',(1570,50,1740,220))
ENTER=((958,966),'PORTAL_ENTER',(830,880,1150,1060))
PORTAL_CLOSE=((1362,214),'PORTAL_CLOSE',(1280,130,1450,300))
ACCEPT=((1215,982),'ACCEPT',(1000,930,1420,1035))
BADGES={'EXPEDITION':(880,100,1060,150),'PORTAL':(870,74,1050,124)}


class ExpeditionRunner(DungeonRunner):
    defeat_continues=True

    def __init__(self,io,capture,vision,channel,log,runs):
        self.io,self.cap,self.vision,self.channel,self.log=io,capture,vision,channel,log
        self.runs=runs;self.deadline=time.monotonic()+60*60
        self.plan={'dungeon_id':'EXPEDITION','difficulty':'','runs':runs,'energy_limit':runs*BADGE_COST,'target':''}
        self.cost=BADGE_COST;self.balance=None
        self.budget=FarmBudget(max_runs=runs,max_energy=runs*BADGE_COST,max_seconds=60*60,max_gold=0,stop_on_defeat=False)

    def press(self,screen,action):
        xy,key,roi=action
        self.wait(lambda f:self.vision.screen(f)==screen and self.vision.locate(f,key,roi) is not None,10,f'{screen} · {key}')
        self.click(screen,xy,key,roi)

    def go_home(self):
        # TOWN tras la run vuelve al diálogo del portal.
        self.wait('PORTAL',20)

    def badges(self,screen):
        seen=None
        def known(frame):
            nonlocal seen
            current=None
            if self.vision.screen(frame)==screen:
                x,y,x1,y1=BADGES[screen];im=frame[y:y1,x:x1]
                # La barra cian tiene brillos casi blancos: solo blanco puro es dígito.
                current=self.vision.number(np.where(im.min(2,keepdims=True)>=240,im,0).astype(np.uint8))
            okay=current is not None and current==seen;seen=current
            return okay
        self.wait(known,30,'saldo de badges')
        return seen

    def to_portal(self):
        screen=self.vision.screen(self.wait(lambda f:self.vision.screen(f) in ('HOME','EXPEDITION','IDOL_MAP','PORTAL'),12))
        if screen=='HOME':self.press('HOME',HOME_EXP);screen=self.vision.screen(self.wait('EXPEDITION'))
        if screen=='EXPEDITION':
            balance=self.badges('EXPEDITION')
            if balance<1:return False
            # Con menos de 5 badges se baja el coste; PLAY con coste mayor ofrece comprar (nunca).
            self.cost=self.set_cost('EXPEDITION',min(BADGE_COST,balance),'COST_MENU_BADGES')
            self.press('EXPEDITION',PLAY);screen=self.vision.screen(self.wait('IDOL_MAP'))
        if screen=='IDOL_MAP':self.press('IDOL_MAP',PORTAL);self.wait('PORTAL')
        return True

    def enter(self,cycle,retried=False):
        if not self.to_portal():return None
        balance=self.badges('PORTAL')
        if balance<self.cost:
            # El coste se fija en la ventana; al volver a ella se bajará si quedan badges.
            if retried:raise SafetyStop('Coste y saldo de badges no cuadran tras fijarlo; no se entra')
            self.close_portal();return self.enter(cycle,True) if balance>=1 else None
        attempt=f'{self.channel.run_id}:{cycle}'
        if not self.budget.reserve_entry(attempt,resource='BADGES',balance=balance,cost=self.cost):
            raise SafetyStop('Expedición ya reservada; no repetir ENTER')
        atomic_json(self.channel.directory/f'exp-{cycle}.intent.json',{'attempt_id':attempt,'badges':balance,'effect_confirmed':False})
        self.press('PORTAL',ENTER);self.press('TEAM',ACCEPT)
        self.log.emit('EXP_STARTED',attempt_id=attempt,badges_before=balance)
        return attempt

    def close_portal(self):
        self.press('PORTAL',PORTAL_CLOSE);self.wait('IDOL_MAP');self.press('IDOL_MAP',IDOL_CLOSE);self.wait('EXPEDITION')

    def close(self):
        screen=self.vision.screen(self.wait(lambda f:self.vision.screen(f) in ('HOME','EXPEDITION','IDOL_MAP','PORTAL'),12))
        if screen=='PORTAL':self.press('PORTAL',PORTAL_CLOSE);screen=self.vision.screen(self.wait('IDOL_MAP'))
        if screen=='IDOL_MAP':self.press('IDOL_MAP',IDOL_CLOSE);screen=self.vision.screen(self.wait('EXPEDITION'))
        if screen=='EXPEDITION':self.press('EXPEDITION',EXP_CLOSE);self.wait('HOME')

    def run(self):
        for cycle in range(1,self.runs+1):
            attempt=self.enter(cycle)
            if attempt is None:break
            self.observe(attempt,cycle,auto_started=True)
        self.close()
        self.log.emit('EXP_STATUS',message='Badges gastados · detenido',budget=self.budget.payload())


def run_expedition(runs):
    from .game_window import ENV_WINDOW,focus_window
    from .dungeon_vision import DungeonVision
    from .linux import LinuxIO,LinuxCapture
    from .processes import Mutex
    from .protocol import Channel
    from .telemetry import Telemetry,run_environment
    if os.name=='nt':raise ValueError('Expedition aún no certificada en Windows')
    locks=[Mutex(role) for role in ('LAUNCHER','CONTROL','CATCH')];io=log=None
    try:
        env=run_environment();channel=Channel(env['FISHING_RUN_ID'])
        os.environ[ENV_WINDOW]=focus_window('Steam').serialize();os.environ.pop('FARM_LAUNCHER_PID',None)
        log=Telemetry('EXPEDITION',channel.run_id);io=LinuxIO();io.control_mode=True
        with LinuxCapture(io.game_guard) as capture:
            ExpeditionRunner(io,capture,DungeonVision(),channel,log,runs).run()
    except (Exception,KeyboardInterrupt) as exc:
        if log:log.emit('SAFETY_STOP',message=str(exc) or 'F8',reason=str(exc) or 'F8',human=True)
        raise
    finally:
        if io:io.close()
        if log:log.close()
        for lock in reversed(locks):lock.close()


if __name__=='__main__':
    import sys
    run_expedition(int(sys.argv[1]))
