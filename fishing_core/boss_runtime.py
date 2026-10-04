"""World Boss Netherworld T9 Normal, sala privada en solitario: gasta solo xeals."""

import os
import time

from .control_flow import SafetyStop
from .dungeon_runtime import DungeonRunner
from .farm_budget import FarmBudget
from .protocol import atomic_json

XEAL_COST=1
# Pantalla: (coordenada, plantilla que debe verse antes del clic, ROI)
HOME_BOSS=((90,430),'HOME_BOSS',(15,355,165,505))
LIST_SUMMON=((1180,966),'WB_SUMMON_LIST',(1035,930,1325,1005))
LIST_CLOSE=((1536,214),'WB_CLOSE',(1500,180,1575,250))
CAROUSEL_SUMMON=((1260,786),'WB_CAROUSEL_SUMMON',(1140,700,1385,870))
SUMMON=((1130,842),'WB_SUMMON_BUTTON',(1015,800,1250,885))
CAROUSEL_PREV=(440,624)
START=((920,984),'WB_START',(735,945,1100,1025))
NOT_FULL_YES=((816,750),'DECLINE_YES',(670,695,955,805))
AUTO=(1880,530)
TOWN_ROI=(700,915,1500,1080)
REGROUP_ROI=(650,915,1250,1080)
# La configuración se comprueba; el bot nunca la cambia. Heroic T9 en solitario
# perdió en segundos en una prueba; Normal gana en ~8 s. El usuario elige.
DIFFICULTIES=('Normal','Heroic')


def summon_config(difficulty):
    return (('WB_TIER_9',(775,415,1080,470)),(f'WB_{difficulty.upper()}',(775,585,1080,640)),
            ('WB_PRIVATE_ON',(800,690,875,760)))


def lobby_config(difficulty):
    return ((f'WB_LOBBY_{difficulty.upper()}',(715,230,1100,285)),('WB_LOBBY_PRIVATE_ON',(1130,950,1200,1010)),
            ('WB_SLOT2_EMPTY',(830,465,1065,530)))
XEALS_LOBBY=(370,130,520,175)
XEALS_LIST=(860,70,1060,120)
BATTLE_LIMIT=300  # T9 Normal real terminó en segundos; holgura acotada.


class BossRunner(DungeonRunner):
    def __init__(self,io,capture,vision,channel,log,runs,difficulty='Normal'):
        if difficulty not in DIFFICULTIES:raise ValueError('Dificultad de World Boss no soportada')
        self.io,self.cap,self.vision,self.channel,self.log=io,capture,vision,channel,log
        self.difficulty=difficulty
        self.runs=runs;self.deadline=time.monotonic()+60*60
        self.budget=FarmBudget(max_runs=runs,max_energy=runs*XEAL_COST,max_seconds=60*60,max_gold=0)

    def configured(self,screen,checks,message):
        """Espera lectura estable de toda la configuración: los diálogos entran animados."""
        return self.wait(lambda f:self.vision.screen(f)==screen and
                         all(self.vision.locate(f,key,roi) is not None for key,roi in checks),10,message)

    def press(self,screen,action):
        # Las ventanas entran y salen animadas: esperar también el botón concreto.
        xy,key,roi=action
        self.wait(lambda f:self.vision.screen(f)==screen and self.vision.locate(f,key,roi) is not None,10,f'{screen} · {key}')
        self.click(screen,xy,key,roi)

    def to_list(self):
        screen=self.vision.screen(self.wait(lambda f:self.vision.screen(f) in ('HOME','WB_LIST'),12))
        if screen=='HOME':self.press('HOME',HOME_BOSS);self.wait('WB_LIST')

    def close_list(self):
        self.wait('WB_LIST');self.press('WB_LIST',LIST_CLOSE);self.wait('HOME')

    def xeals(self,frame,roi):
        x,y,x1,y1=roi;return self.vision.number(frame[y:y1,x:x1])

    def find_netherworld(self):
        """El carrusel no siempre abre en el último jefe: pasar páginas hasta leer Netherworld."""
        named=lambda f:self.vision.locate(f,'WB_NETHERWORLD',(480,680,1000,850)) is not None
        for _ in range(11):  # 11 jefes; nunca se invoca otro
            frame=self.wait('WB_CAROUSEL');time.sleep(.5)
            if named(self.capture()):return
            self.click('WB_CAROUSEL',CAROUSEL_PREV);time.sleep(1)
        raise SafetyStop('Netherworld no aparece en el carrusel; no se cambia de jefe')

    def enter(self,cycle,in_lobby=False):
        """Devuelve el intento, o None si no quedan xeals (sin invocar sala)."""
        if not in_lobby:
            if not self.summon():return None
        return self.start(cycle)

    def summon(self):
        self.to_list();seen=None
        def known(frame):
            nonlocal seen
            current=self.xeals(frame,XEALS_LIST) if self.vision.screen(frame)=='WB_LIST' else None
            okay=current is not None and current==seen;seen=current
            return okay
        self.wait(known,30,'saldo de xeals en la lista')
        if seen<XEAL_COST:
            self.close_list();self.log.emit('BOSS_STATUS',message=f'Sin xeals ({seen}); nada que gastar');return False
        self.press('WB_LIST',LIST_SUMMON)
        self.find_netherworld()
        self.press('WB_CAROUSEL',CAROUSEL_SUMMON)
        self.configured('WB_SUMMON',summon_config(self.difficulty),f'Summon Tier 9 · {self.difficulty} · Private')
        self.press('WB_SUMMON',SUMMON)
        return True

    def start(self,cycle):
        balance=None
        def lobby(frame):
            nonlocal balance
            if self.vision.screen(frame)!='WB_LOBBY':return False
            current=self.xeals(frame,XEALS_LOBBY)
            okay=current is not None and current==balance;balance=current
            return okay
        self.wait(lobby,30,'sala con saldo de xeals')
        self.configured('WB_LOBBY',lobby_config(self.difficulty),f'sala privada, {self.difficulty} y en solitario')
        attempt=f'{self.channel.run_id}:{cycle}'
        if not self.budget.reserve_entry(attempt,resource='XEALS',balance=balance,cost=XEAL_COST):
            raise SafetyStop('Entrada ya reservada; no repetir START')
        atomic_json(self.channel.directory/f'boss-{cycle}.intent.json',
                    {'attempt_id':attempt,'xeals':balance,'cost':XEAL_COST,'effect_confirmed':False})
        self.press('WB_LOBBY',START)
        self.wait('WB_NOT_FULL');self.press('WB_NOT_FULL',NOT_FULL_YES)
        self.log.emit('BOSS_STARTED',attempt_id=attempt,xeals_before=balance)
        self.balance=balance
        return attempt

    def result_button(self,frame,key,roi):
        x,y=self.vision.locate(frame,key,roi);h,w=self.vision.templates[key].shape[:2]
        self.click(self.vision.screen(frame),(x+w//2,y+h//2),key,roi)

    def battle(self,attempt,cycle,again=False):
        """Devuelve True si volvió a la sala con REGROUP para otra run."""
        results=('WB_VICTORY','WB_DEFEAT')
        frame=self.wait(lambda f:self.vision.screen(f) in ('AUTO_OFF_BATTLE','AUTO_ON_BATTLE')+results,30,'combate del jefe')
        if self.vision.screen(frame)=='AUTO_OFF_BATTLE':self.click('AUTO_OFF_BATTLE',AUTO)
        frame=self.wait(lambda f:self.vision.screen(f) in results,BATTLE_LIMIT,'resultado del jefe')
        screen=self.vision.screen(frame);outcome='VICTORY' if screen=='WB_VICTORY' else 'DEFEAT'
        # Botones localizados: cambian de sitio entre victoria (3) y derrota (2).
        regroup=again and outcome=='VICTORY'
        if regroup:self.result_button(frame,'RESULT_REGROUP',REGROUP_ROI);self.wait('WB_LOBBY',15)
        else:self.result_button(frame,'RESULT_TOWN',TOWN_ROI);self.close_list()
        self.budget.finish_run(attempt,outcome,closure_confirmed=True)
        atomic_json(self.channel.directory/f'boss-{cycle}.intent.json',{'attempt_id':attempt,'outcome':outcome,'effect_confirmed':True})
        self.log.emit('BOSS_COMPLETE',message=f'Netherworld {cycle}: {outcome}',budget=self.budget.payload())
        if outcome=='DEFEAT':raise SafetyStop('Derrota en el jefe: no se repite')
        return regroup

    def run(self):
        in_lobby=False
        for cycle in range(1,self.runs+1):
            attempt=self.enter(cycle,in_lobby)
            if attempt is None:return
            # REGROUP solo si queda saldo para otra run; si no, TOWN y cerrar.
            again=cycle<self.runs and self.balance-XEAL_COST>=XEAL_COST
            in_lobby=self.battle(attempt,cycle,again)
        self.log.emit('BOSS_STATUS',message='Límite de runs alcanzado · detenido',budget=self.budget.payload())


def run_boss(runs,difficulty='Normal'):
    """Sesión de World Boss con F8, foco y exclusividad; sin panel todavía."""
    from .game_window import ENV_WINDOW,focus_window
    from .dungeon_vision import DungeonVision
    from .linux import LinuxIO,LinuxCapture
    from .processes import Mutex
    from .protocol import Channel
    from .telemetry import Telemetry,run_environment
    if os.name=='nt':raise ValueError('World Boss aún no certificado en Windows')
    locks=[Mutex(role) for role in ('LAUNCHER','CONTROL','CATCH')];io=log=None
    try:
        env=run_environment();channel=Channel(env['FISHING_RUN_ID'])
        os.environ[ENV_WINDOW]=focus_window('Steam').serialize();os.environ.pop('FARM_LAUNCHER_PID',None)
        log=Telemetry('BOSS',channel.run_id);io=LinuxIO();io.control_mode=True
        with LinuxCapture(io.game_guard) as capture:
            BossRunner(io,capture,DungeonVision(),channel,log,runs,difficulty).run()
    except (Exception,KeyboardInterrupt) as exc:
        if log:log.emit('SAFETY_STOP',message=str(exc) or 'F8',reason=str(exc) or 'F8',human=True)
        raise
    finally:
        if io:io.close()
        if log:log.close()
        for lock in reversed(locks):lock.close()


if __name__=='__main__':
    import sys
    run_boss(int(sys.argv[1]),*sys.argv[2:3])
