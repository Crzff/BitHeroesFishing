"""PvP Arena: gasta tickets eligiendo rival; perder es normal y no detiene."""

import os
import time

from .control_flow import SafetyStop
from .dungeon_runtime import DungeonRunner
from .farm_budget import FarmBudget
from .protocol import atomic_json

TICKET_COST=5  # máximo; con menos tickets se baja hasta 1
HOME_PVP=((90,280),'HOME_PVP',(15,205,165,355))
PLAY=((1280,568),'PVP_PLAY',(1120,440,1445,695))
CLOSE=((1494,226),'PVP_CLOSE',(1410,140,1580,310))
# Rival de la 4.ª fila: el que más puntos da. Ganó en 4 s el 2026-10-04.
FIGHT=((1390,768),'PVP_FIGHT',(1236,698,1544,840))
ACCEPT=((1215,982),'ACCEPT',(1000,930,1420,1035))
TICKETS_ROI=(1350,22,1530,62)
TOWN_ROI=(700,915,1500,1080)
AUTO=(1880,530)
BATTLE_LIMIT=180


class PvpRunner(DungeonRunner):
    def __init__(self,io,capture,vision,channel,log,fights):
        self.io,self.cap,self.vision,self.channel,self.log=io,capture,vision,channel,log
        self.fights=fights;self.deadline=time.monotonic()+60*60
        self.budget=FarmBudget(max_runs=fights,max_energy=fights*TICKET_COST,max_seconds=60*60,
                               max_gold=0,stop_on_defeat=False)

    def press(self,screen,action):
        xy,key,roi=action
        self.wait(lambda f:self.vision.screen(f)==screen and self.vision.locate(f,key,roi) is not None,10,f'{screen} · {key}')
        self.click(screen,xy,key,roi)

    def tickets(self):
        """Saldo estable de la barra superior; alterna con el reloj de recarga."""
        seen=None
        def known(frame):
            nonlocal seen
            x,y,x1,y1=TICKETS_ROI
            current=self.vision.number(frame[y:y1,x:x1]) if self.vision.screen(frame)=='PVP' else None
            okay=current is not None and current==seen;seen=current
            return okay
        self.wait(known,30,'saldo de tickets')
        return seen

    def open(self):
        screen=self.ensure_home(keep=('PVP',))
        if screen=='HOME':self.press('HOME',HOME_PVP);self.wait('PVP')

    def fight(self,cycle):
        """Un combate; None si no quedan tickets para el coste."""
        self.open();balance=self.tickets()
        if balance<1:return None
        cost=self.set_cost('PVP',min(TICKET_COST,balance),'COST_MENU_TICKETS')
        attempt=f'{self.channel.run_id}:{cycle}'
        if not self.budget.reserve_entry(attempt,resource='TICKETS',balance=balance,cost=cost):
            raise SafetyStop('Combate ya reservado; no repetir PLAY')
        atomic_json(self.channel.directory/f'pvp-{cycle}.intent.json',{'attempt_id':attempt,'tickets':balance,'effect_confirmed':False})
        self.press('PVP',PLAY);self.press('PVP_SELECT',FIGHT);self.press('TEAM',ACCEPT)
        self.log.emit('PVP_STARTED',attempt_id=attempt,tickets_before=balance)
        results=('WB_VICTORY','WB_DEFEAT')
        frame=self.wait(lambda f:self.vision.screen(f) in ('AUTO_OFF_BATTLE','AUTO_ON_BATTLE')+results,30,'combate PvP')
        if self.vision.screen(frame)=='AUTO_OFF_BATTLE':self.click('AUTO_OFF_BATTLE',AUTO)
        frame=self.wait(lambda f:self.vision.screen(f) in results,BATTLE_LIMIT,'resultado PvP')
        screen=self.vision.screen(frame);outcome='VICTORY' if screen=='WB_VICTORY' else 'DEFEAT'
        x,y=self.vision.locate(frame,'RESULT_TOWN',TOWN_ROI);h,w=self.vision.templates['RESULT_TOWN'].shape[:2]
        self.click(screen,(x+w//2,y+h//2),'RESULT_TOWN',TOWN_ROI);self.wait('PVP',15)
        self.budget.finish_run(attempt,outcome,closure_confirmed=True)
        atomic_json(self.channel.directory/f'pvp-{cycle}.intent.json',{'attempt_id':attempt,'outcome':outcome,'effect_confirmed':True})
        self.log.emit('PVP_COMPLETE',message=f'PvP {cycle}: {outcome}',budget=self.budget.payload())
        return outcome

    def run(self):
        for cycle in range(1,self.fights+1):
            if self.fight(cycle) is None:break
        self.press('PVP',CLOSE);self.wait('HOME')
        self.log.emit('PVP_STATUS',message='Tickets gastados · detenido',budget=self.budget.payload())


def run_pvp(fights):
    from .game_window import ENV_WINDOW,focus_window
    from .dungeon_vision import DungeonVision
    from .gamescope import backend
    LinuxIO,LinuxCapture=backend()
    from .processes import Mutex
    from .protocol import Channel
    from .telemetry import Telemetry,run_environment
    if os.name=='nt':raise ValueError('PvP aún no certificado en Windows')
    locks=[Mutex(role) for role in ('LAUNCHER','CONTROL','CATCH')];io=log=None
    try:
        env=run_environment();channel=Channel(env['FISHING_RUN_ID'])
        if os.environ.get('FARM_BACKEND')!='gamescope':os.environ[ENV_WINDOW]=focus_window('Steam').serialize()
        os.environ.pop('FARM_LAUNCHER_PID',None)
        log=Telemetry('PVP',channel.run_id);io=LinuxIO();io.control_mode=True
        with LinuxCapture(io.game_guard) as capture:
            PvpRunner(io,capture,DungeonVision(),channel,log,fights).run()
    except (Exception,KeyboardInterrupt) as exc:
        if log:log.emit('SAFETY_STOP',message=str(exc) or 'F8',reason=str(exc) or 'F8',human=True)
        raise
    finally:
        if io:io.close()
        if log:log.close()
        for lock in reversed(locks):lock.close()


if __name__=='__main__':
    import sys
    run_pvp(int(sys.argv[1]))
