"""Raid elegida por el jugador (crzf: Storm, su T13) en la dificultad elegida: gasta todos los shards.

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
PREV=(440,624)
DIFFICULTY_BUTTONS={'Normal':((554,482),'RAID_NORMAL',(360,395,750,575)),'Hard':((958,482),'RAID_HARD',(770,395,1150,575)),
                    'Heroic':((1370,482),'RAID_HEROIC',(1180,395,1560,575))}
# Todas las raids del juego (wiki 2026-10-06), de la 1 a la 18; la raid N se desbloquea en el tier N+3.
RAIDS={'ASTAROTHS_AWAKENING':"Astaroth's Awakening",'HYPER_DIMENSION':'Hyper Dimension','WOODBEARDS_BOOTY':"Woodbeard's Booty",
       'A_HAILE_OF_A_MISTAKE':'A Haile of a Mistake','ZOLS_LABYRINTH':"Zol's Labyrinth",'MALLOWDALE':'Mallowdale',
       'GORBONS_ROCKIN_RUCKUS':"Gorbon's Rockin' Ruckus",'CHARRED_EXPANSE':'Charred Expanse','MINIONS_OF_TARANIS':'Minions of Taranis',
       'STORM':'Storm','TIKAL_DIKI':'Tikal-Diki','METAL_MOUNTAIN':'Metal Mountain','WOLFS_DECEPTION':"The Wolf's Deception",
       'BRAWLY_GRAS_PALACE':'Brawly Gras Palace','UZUMS_OLYMPIAN_RAVE':"Uzum's Olympian Rave",'UNDER_THE_TITANS_EYE':"Under The Titan's Eye",
       'ROASTGARD':'Roastgard','HENS_HIDEAWAY':"Hen's Hideaway"}
RAID_TIER={key:i+4 for i,key in enumerate(RAIDS)}  # Astaroth T4 ... Storm T13, Tikal-Diki T14 ... Hen's Hideaway T21
ACCEPT=((1215,982),'ACCEPT',(1000,930,1420,1035))
SHARDS_ROI=(880,100,1050,145)


class RaidRunner(DungeonRunner):
    defeat_continues=True
    OBSERVE_SECONDS=600  # en vivo una raid de Steam superó los 3 min de una dungeon

    persuade_all=True  # crzf: en Raid todos los familiares son buenos; se persuade cualquiera con oro
    entry_resource='SHARDS'  # RERUN reserva shards, no energía

    def __init__(self,io,capture,vision,channel,log,runs,raid='STORM',difficulty='Heroic',max_gold=0):
        if raid not in RAIDS or difficulty not in DIFFICULTY_BUTTONS:raise ValueError('Raid o dificultad no disponible')
        self.io,self.cap,self.vision,self.channel,self.log=io,capture,vision,channel,log
        self.raid,self.raid_difficulty=raid,difficulty
        self.runs=runs;self.deadline=time.monotonic()+60*60
        self.plan={'dungeon_id':'RAID_STORM','difficulty':'Heroic','runs':runs,'energy_limit':runs,'target':''}
        self.cost=SHARD_COST;self.balance=None
        if type(max_gold) is not int or not 0<=max_gold<=10_000_000:raise ValueError('Cuota de oro inválida (0-10.000.000)')
        self.budget=FarmBudget(max_runs=runs,max_energy=runs*SHARD_COST,max_seconds=60*60,max_gold=max_gold,stop_on_defeat=False)

    def finish_leftover_run(self,screen):
        """Raid a medias al reanudar: la oferta también se persuade (con la cuota de oro), no se rechaza."""
        if screen!='FAMILIAR_OFFER':return super().finish_leftover_run(screen)
        self.leftovers=getattr(self,'leftovers',0)+1;frame=self.capture()
        self.persuade(frame,f'{self.channel.run_id}:resume',f'resume-{self.leftovers}',self.offer_name(frame))

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
        screen=self.ensure_home(keep=('RAID',))
        if screen=='HOME':self.press('HOME',HOME_RAID);self.wait('RAID')
        key=f'RAID_NAME_{self.raid}'
        if key in self.vision.templates:named=lambda f:self.vision.locate(f,key,(500,700,1170,830)) is not None
        else:named=lambda f:self.vision.raid_title(f,list(RAIDS.values()))==RAIDS[self.raid]  # sin imagen: se lee el nombre
        for _ in range(len(RAIDS)+1):  # una vuelta; nunca se invoca otra
            self.wait('RAID');time.sleep(.5)
            if named(self.capture()):return
            self.click('RAID',PREV);time.sleep(1)
        raise SafetyStop(f'{RAIDS[self.raid]} no aparece entre las raids; no se cambia de raid')

    def enter(self,cycle):
        self.open();balance=self.shards()
        if balance<SHARD_COST:return None
        attempt=f'{self.channel.run_id}:{cycle}'
        if not self.budget.reserve_entry(attempt,resource='SHARDS',balance=balance,cost=SHARD_COST):
            raise SafetyStop('Raid ya reservada; no repetir SUMMON')
        atomic_json(self.channel.directory/f'raid-{cycle}.intent.json',{'attempt_id':attempt,'shards':balance,'effect_confirmed':False})
        self.press('RAID',SUMMON);self.press('RAID_DIFFICULTY',DIFFICULTY_BUTTONS[self.raid_difficulty]);self.press('TEAM',ACCEPT)
        self.balance=balance-SHARD_COST  # cota inferior para decidir RERUN (la regeneración solo suma)
        self.log.emit('RAID_STARTED',attempt_id=attempt,shards_before=balance)
        return attempt

    def run(self):
        following=None
        for cycle in range(1,self.runs+1):
            attempt=following or self.enter(cycle)  # tras RERUN la raid ya está en marcha
            if attempt is None:break
            # observe(): Auto, ofertas (se persuade cualquiera), victoria -> RERUN si quedan shards, si no TOWN.
            following=self.observe(attempt,cycle,auto_started=True,rerun=cycle<self.runs)
            atomic_json(self.channel.directory/f'raid-{cycle}.intent.json',{'attempt_id':attempt,'outcome':'VICTORY','effect_confirmed':True})
        self.open();self.press('RAID',CLOSE);self.wait('HOME')
        self.log.emit('RAID_STATUS',message='Shards gastados · detenido',budget=self.budget.payload())


def run_raid(runs,raid='STORM',difficulty='Heroic',max_gold=0):
    from .game_window import ENV_WINDOW,focus_window
    from .dungeon_vision import DungeonVision
    from .gamescope import backend
    LinuxIO,LinuxCapture=backend()
    from .processes import Mutex
    from .protocol import Channel
    from .telemetry import Telemetry,run_environment
    if os.name=='nt':raise ValueError('Raid aún no certificada en Windows')
    locks=[Mutex(role) for role in ('LAUNCHER','CONTROL','CATCH')];io=log=None
    try:
        env=run_environment();channel=Channel(env['FISHING_RUN_ID'])
        if os.environ.get('FARM_BACKEND') not in ('gamescope','cdp'):os.environ[ENV_WINDOW]=focus_window('Steam').serialize()
        os.environ.pop('FARM_LAUNCHER_PID',None)
        log=Telemetry('RAID',channel.run_id);io=LinuxIO();io.control_mode=True
        with LinuxCapture(io.game_guard) as capture:
            RaidRunner(io,capture,DungeonVision(),channel,log,runs,raid,difficulty,max_gold).run()
    except (Exception,KeyboardInterrupt) as exc:
        if log:log.emit('SAFETY_STOP',message=str(exc) or 'F8',reason=str(exc) or 'F8',human=True)
        raise
    finally:
        if io:io.close()
        if log:log.close()
        for lock in reversed(locks):lock.close()


if __name__=='__main__':
    import sys
    run_raid(int(sys.argv[1]),*sys.argv[2:4])  # runs [raid] [dificultad]
