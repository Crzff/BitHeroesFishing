"""World Boss elegido por el jugador (jefe, tier y dificultad), sala privada en solitario: gasta solo xeals."""

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
DIFFICULTIES=('Normal','Hard','Heroic')
# Jefes del carrusel (2026-10-04) y los tiers que ofrece su menú.
BOSSES={'NETHERWORLD':('Netherworld',(13,12,11,10,9)),'MELVIN_FACTORY':('Melvin Factory',(11,10)),
        'EXTERMINATION':('3XT3RMIN4TION',(11,10)),'BRIMSTONE_SYNDICATE':('Brimstone Syndicate',(12,11)),
        'TITANS_ATTACK':('Titans Attack!',(13,12,11)),'IGNITED_ABYSS':('The Ignited Abyss',(13,)),
        'PROJECT_GOODALL':('Project: Goodall',(7,)),'GALLUS_APOTHEOSIS':('Gallus Apotheosis',(7,)),
        'ORLAG_CLAN':('Orlag Clan',(12,11,10,9,8))}
TIER_FIELD=(945,415,1080,470)
TIER_DROPDOWN=(1126,444)
DIFF_DROPDOWN=(1126,610)
DIFF_FIELD=(775,585,1080,640)
PRIVATE=((838,725),(800,690,875,760))
MENU_CLOSE=(1310,182)


def menu_row(i):
    return (930,316+128*i)


def lobby_config(difficulty):
    checks=[('WB_LOBBY_PRIVATE_ON',(1130,950,1200,1010)),('WB_SLOT2_EMPTY',(830,465,1065,530))]
    if difficulty!='Hard':checks.append((f'WB_LOBBY_{difficulty.upper()}',(715,230,1100,285)))  # sin plantilla de Hard
    return tuple(checks)
XEALS_LOBBY=(370,130,520,175)
XEALS_LIST=(860,70,1060,120)
BATTLE_LIMIT=300  # T9 Normal real terminó en segundos; holgura acotada.


class BossRunner(DungeonRunner):
    def __init__(self,io,capture,vision,channel,log,runs,difficulty='Normal',boss='NETHERWORLD',tier=9):
        if difficulty not in DIFFICULTIES:raise ValueError('Dificultad de World Boss no soportada')
        if boss not in BOSSES or tier not in BOSSES[boss][1]:raise ValueError('Jefe o tier no disponible')
        self.io,self.cap,self.vision,self.channel,self.log=io,capture,vision,channel,log
        self.difficulty,self.boss,self.tier=difficulty,boss,tier
        self.runs=runs;self.deadline=time.monotonic()+60*60
        self.budget=FarmBudget(max_runs=runs,max_energy=runs*XEAL_COST,max_seconds=60*60,max_gold=0,stop_on_defeat=False)

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

    def find_boss(self):
        """El carrusel no siempre abre en el último jefe: pasar páginas hasta leer el elegido."""
        named=lambda f:self.vision.locate(f,f'WB_NAME_{self.boss}',(480,700,1160,830)) is not None
        for _ in range(len(BOSSES)+1):  # una vuelta; nunca se invoca otro
            self.wait('WB_CAROUSEL');time.sleep(.5)
            if named(self.capture()):return
            self.click('WB_CAROUSEL',CAROUSEL_PREV);time.sleep(1)
        raise SafetyStop(f'{BOSSES[self.boss][0]} no aparece en el carrusel; no se cambia de jefe')

    def tier_shown(self,frame):
        x,y,x1,y1=TIER_FIELD;return self.vision.number(frame[y:y1,x:x1])

    def pick(self,dropdown,menu_key,row,confirm,label):
        """Abre un desplegable del Summon, pulsa una fila y confirma el cambio leyendo el campo."""
        self.click('WB_SUMMON',dropdown)
        menu=lambda f:self.vision.locate(f,menu_key,(760,95,1160,240)) is not None
        frame=self.wait(menu,10,f'menú de {label}');time.sleep(1.2)  # el menú entra deslizándose
        xy=menu_row(row(self.capture()) if callable(row) else row)
        self.check();self.io.click(xy);time.sleep(.25);self.io._move((960,1070))
        self.log.emit('DUNGEON_INPUT',screen=menu_key,xy=list(xy))
        self.wait(lambda f:self.vision.screen(f)=='WB_SUMMON' and confirm(f),10,f'{label} elegido')

    def configure_summon(self):
        """Fija tier, dificultad y sala privada elegidos; cada cambio se confirma leyendo el diálogo."""
        frame=self.wait(lambda f:self.vision.screen(f)=='WB_SUMMON' and self.tier_shown(f) is not None,10,'Summon')
        time.sleep(.5);frame=self.capture()
        if self.tier_shown(frame)!=self.tier:
            def row(f):
                for i in range(6):
                    y=316+128*i
                    if self.vision.number(f[y-30:y+30,970:1100])==self.tier:return i
                raise SafetyStop(f'Tier {self.tier} no está en el menú; no se cambia')
            self.pick(TIER_DROPDOWN,'WB_TIER_MENU',row,lambda f:self.tier_shown(f)==self.tier,f'tier {self.tier}')
        key=f'WB_{self.difficulty.upper()}'
        if self.vision.locate(self.capture(),key,DIFF_FIELD) is None:
            self.pick(DIFF_DROPDOWN,'WB_DIFF_MENU',DIFFICULTIES.index(self.difficulty),
                      lambda f:self.vision.locate(f,key,DIFF_FIELD) is not None,self.difficulty)
        if self.vision.locate(self.capture(),'WB_PRIVATE_ON',PRIVATE[1]) is None:
            self.click('WB_SUMMON',PRIVATE[0])
            self.wait(lambda f:self.vision.locate(f,'WB_PRIVATE_ON',PRIVATE[1]) is not None,5,'sala privada')
        self.wait(lambda f:self.vision.screen(f)=='WB_SUMMON' and self.tier_shown(f)==self.tier and
                  self.vision.locate(f,key,DIFF_FIELD) is not None and
                  self.vision.locate(f,'WB_PRIVATE_ON',PRIVATE[1]) is not None,10,
                  f'Summon Tier {self.tier} · {self.difficulty} · Private')

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
        self.find_boss()
        self.press('WB_CAROUSEL',CAROUSEL_SUMMON)
        self.configure_summon()
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
        regroup=again  # crzf: una derrota no detiene, se sigue gastando
        if regroup:self.result_button(frame,'RESULT_REGROUP',REGROUP_ROI);self.wait('WB_LOBBY',15)
        else:self.result_button(frame,'RESULT_TOWN',TOWN_ROI);self.close_list()
        self.budget.finish_run(attempt,outcome,closure_confirmed=True)
        atomic_json(self.channel.directory/f'boss-{cycle}.intent.json',{'attempt_id':attempt,'outcome':outcome,'effect_confirmed':True})
        self.log.emit('BOSS_COMPLETE',message=f'Netherworld {cycle}: {outcome}',budget=self.budget.payload())
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


def run_boss(runs,difficulty='Normal',boss='NETHERWORLD',tier=9):
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
            BossRunner(io,capture,DungeonVision(),channel,log,runs,difficulty,boss,tier).run()
    except (Exception,KeyboardInterrupt) as exc:
        if log:log.emit('SAFETY_STOP',message=str(exc) or 'F8',reason=str(exc) or 'F8',human=True)
        raise
    finally:
        if io:io.close()
        if log:log.close()
        for lock in reversed(locks):lock.close()


if __name__=='__main__':
    import sys
    # runs [dificultad] [jefe] [tier]
    args=sys.argv[1:];run_boss(int(args[0]),*(args[1:3]),*([int(args[3])] if len(args)>3 else []))
