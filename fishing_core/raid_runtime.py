"""Raid del tier del jugador (crzf: T13 = Storm) en Heroic: gasta todos los shards.

Una derrota no detiene: se cierra con TOWN y se sigue gastando (pedido por crzf).
"""

import os
import time

from .control_flow import SafetyStop
from .dungeon_runtime import DungeonRunner
from .farm_budget import FarmBudget
from .protocol import atomic_json

SHARD_COST=1
HOME_RAID=((90,580),'HOME_RAID',(15,505,165,640))
SUMMON=((1260,786),'RAID_SUMMON',(1095,650,1435,920))
CLOSE=((1468,236),'RAID_CLOSE',(1380,150,1560,320))
HEROIC=((1370,482),'RAID_HEROIC',(1180,395,1560,575))
ACCEPT=((1215,982),'ACCEPT',(1000,930,1420,1035))
SHARDS_ROI=(880,100,1050,145)


class RaidRunner(DungeonRunner):
    defeat_continues=True

    def __init__(self,io,capture,vision,channel,log,runs):
        self.io,self.cap,self.vision,self.channel,self.log=io,capture,vision,channel,log
        self.runs=runs;self.deadline=time.monotonic()+60*60
        self.plan={'dungeon_id':'RAID_STORM','difficulty':'Heroic','runs':runs,'energy_limit':runs,'target':''}
        self.cost=SHARD_COST;self.balance=None
        self.budget=FarmBudget(max_runs=runs,max_energy=runs*SHARD_COST,max_seconds=60*60,max_gold=0,stop_on_defeat=False)

    def press(self,screen,action):
        xy,key,roi=action
        self.wait(lambda f:self.vision.screen(f)==screen and self.vision.locate(f,key,roi) is not None,10,f'{screen} · {key}')
        self.click(screen,xy,key,roi)

    def go_home(self):
        # TOWN tras la raid vuelve a la ventana de Raid, no a Home.
        self.wait('RAID',20)

    def shards(self):
        seen=None
        def known(frame):
            nonlocal seen
            x,y,x1,y1=SHARDS_ROI
            current=self.vision.number(frame[y:y1,x:x1]) if self.vision.screen(frame)=='RAID' else None
            okay=current is not None and current==seen;seen=current
            return okay
        self.wait(known,30,'saldo de shards')
        return seen

    def open(self):
        screen=self.vision.screen(self.wait(lambda f:self.vision.screen(f) in ('HOME','RAID'),12))
        if screen=='HOME':self.press('HOME',HOME_RAID);self.wait('RAID')
        if self.vision.locate(self.capture(),'RAID_STORM',(500,695,780,830)) is None:
            raise SafetyStop('La raid mostrada no es Storm (T13); no se cambia de raid')

    def enter(self,cycle):
        self.open();balance=self.shards()
        if balance<SHARD_COST:return None
        attempt=f'{self.channel.run_id}:{cycle}'
        if not self.budget.reserve_entry(attempt,resource='SHARDS',balance=balance,cost=SHARD_COST):
            raise SafetyStop('Raid ya reservada; no repetir SUMMON')
        atomic_json(self.channel.directory/f'raid-{cycle}.intent.json',{'attempt_id':attempt,'shards':balance,'effect_confirmed':False})
        self.press('RAID',SUMMON);self.press('RAID_DIFFICULTY',HEROIC);self.press('TEAM',ACCEPT)
        self.log.emit('RAID_STARTED',attempt_id=attempt,shards_before=balance)
        return attempt

    def run(self):
        for cycle in range(1,self.runs+1):
            attempt=self.enter(cycle)
            if attempt is None:break
            # observe(): Auto del mapa/combate, ofertas (sin objetivo se rechazan), victoria -> TOWN.
            self.observe(attempt,cycle,auto_started=True)
            atomic_json(self.channel.directory/f'raid-{cycle}.intent.json',{'attempt_id':attempt,'outcome':'VICTORY','effect_confirmed':True})
        self.open();self.press('RAID',CLOSE);self.wait('HOME')
        self.log.emit('RAID_STATUS',message='Shards gastados · detenido',budget=self.budget.payload())


def run_raid(runs):
    from .game_window import ENV_WINDOW,focus_window
    from .dungeon_vision import DungeonVision
    from .linux import LinuxIO,LinuxCapture
    from .processes import Mutex
    from .protocol import Channel
    from .telemetry import Telemetry,run_environment
    if os.name=='nt':raise ValueError('Raid aún no certificada en Windows')
    locks=[Mutex(role) for role in ('LAUNCHER','CONTROL','CATCH')];io=log=None
    try:
        env=run_environment();channel=Channel(env['FISHING_RUN_ID'])
        os.environ[ENV_WINDOW]=focus_window('Steam').serialize();os.environ.pop('FARM_LAUNCHER_PID',None)
        log=Telemetry('RAID',channel.run_id);io=LinuxIO();io.control_mode=True
        with LinuxCapture(io.game_guard) as capture:
            RaidRunner(io,capture,DungeonVision(),channel,log,runs).run()
    except (Exception,KeyboardInterrupt) as exc:
        if log:log.emit('SAFETY_STOP',message=str(exc) or 'F8',reason=str(exc) or 'F8',human=True)
        raise
    finally:
        if io:io.close()
        if log:log.close()
        for lock in reversed(locks):lock.close()


if __name__=='__main__':
    import sys
    run_raid(int(sys.argv[1]))
