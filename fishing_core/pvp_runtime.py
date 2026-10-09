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
# Rivales de menos a más puntos; su número cambia con el coste en tickets. Se baja al final de
# la lista y se cuenta desde abajo: rival 4 = el que más puntos da, 1 = el cuarto desde abajo.
FIGHT_ROWS=(1,2,3,4)
LIST_ROI=(1236,330,1544,900)
LIST_WHEEL=(960,600)
ACCEPT=((1215,982),'ACCEPT',(1000,930,1420,1035))
TICKETS_ROI=(1350,22,1530,62)
TOWN_ROI=(700,915,1500,1080)
AUTO=(1880,530)
BATTLE_LIMIT=180


class PvpRunner(DungeonRunner):
    def __init__(self,io,capture,vision,channel,log,fights,opponent=4):
        if opponent not in FIGHT_ROWS:raise ValueError('Rival de PvP: 1 a 4')
        self.io,self.cap,self.vision,self.channel,self.log=io,capture,vision,channel,log
        self.opponent=opponent
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

    def choose_opponent(self):
        self.wait('PVP_SELECT');time.sleep(1)  # la lista entra animada
        self.wheel(40,LIST_WHEEL)
        rows=[None]
        def settled(frame):
            current=self.vision.locate_all(frame,'PVP_FIGHT',LIST_ROI) if self.vision.screen(frame)=='PVP_SELECT' else []
            okay=bool(current) and current==rows[0];rows[0]=current
            return okay
        self.wait(settled,10,'lista de rivales quieta')
        x,y=map(int,rows[0][max(0,len(rows[0])-(5-self.opponent))]);h,w=self.vision.templates['PVP_FIGHT'].shape[:2]
        self.click('PVP_SELECT',(x+w//2,y+h//2),'PVP_FIGHT',(x-10,y-10,x+w+10,y+h+10))

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
        self.press('PVP',PLAY);self.choose_opponent();self.press('TEAM',ACCEPT)
        self.log.emit('PVP_STARTED',attempt_id=attempt,tickets_before=balance)
        results=('WB_VICTORY','WB_DEFEAT')
        battle=('AUTO_OFF_BATTLE','AUTO_ON_BATTLE')+results
        frame=self.wait(lambda f:self.vision.screen(f) in battle+('WB_NOT_FULL',),30,'combate PvP')
        if self.vision.screen(frame)=='WB_NOT_FULL':  # KORTZZ (T4) no llena el equipo: pelear igual, como en World Boss
            self.click('WB_NOT_FULL',(816,750),'DECLINE_YES',(670,695,955,805))
            frame=self.wait(lambda f:self.vision.screen(f) in battle,30,'combate PvP')
        if self.vision.screen(frame)=='AUTO_OFF_BATTLE':self.click('AUTO_OFF_BATTLE',AUTO)
        frame=self.wait(lambda f:self.vision.screen(f) in results,BATTLE_LIMIT,'resultado PvP')
        screen=self.vision.screen(frame);outcome='VICTORY' if screen=='WB_VICTORY' else 'DEFEAT'
        if outcome=='VICTORY':self.record_loot()
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


def run_pvp(fights,opponent=4):
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
        if os.environ.get('FARM_BACKEND') not in ('gamescope','cdp'):os.environ[ENV_WINDOW]=focus_window('Steam').serialize()
        os.environ.pop('FARM_LAUNCHER_PID',None)
        log=Telemetry('PVP',channel.run_id);io=LinuxIO();io.control_mode=True
        with LinuxCapture(io.game_guard) as capture:
            PvpRunner(io,capture,DungeonVision(),channel,log,fights,opponent).run()
    except (Exception,KeyboardInterrupt) as exc:
        if log:log.emit('SAFETY_STOP',message=str(exc) or 'F8',reason=str(exc) or 'F8',human=True)
        raise
    finally:
        if io:io.close()
        if log:log.close()
        for lock in reversed(locks):lock.close()


if __name__=='__main__':
    import sys
    run_pvp(int(sys.argv[1]),*[int(a) for a in sys.argv[2:3]])  # combates [rival 1-4]
