"""Runner Steam/niri: rutas locales calibradas, sin compras ni motores de pesca."""

import json
import os
import subprocess
import time

import cv2
import numpy as np

from .control_flow import SafetyStop
from .dungeon_catalog import dungeon,farm_plan,normalize
from .dungeon_vision import DungeonVision,familiar_glyph
from .farm_budget import FarmBudget
from .game_window import ENV_WINDOW,WindowGuard
from .processes import Mutex,child_options,close_children,python_executable
from .protocol import Channel,atomic_json
from .telemetry import ROOT,Telemetry,run_environment

ROUTE_COSTS={(d,level):cost for d in ('Z5D2','Z5D3') for level,cost in (('Normal',10),('Hard',20),('Heroic',30))}
LADDER=('Heroic','Hard','Normal')
DIFFICULTY_BUTTONS={'Normal':((550,495),(400,450,715,550)),'Hard':((958,495),(780,430,1140,570)),
                    'Heroic':((1365,495),(1200,450,1530,550))}
SESSION_SECONDS=3600
COST_ROI=(1210,392,1310,448)
COST_DROPDOWN=(1370,416)
ENERGY_WAIT=30  # ponytail: acotado sin medir el periodo real del reloj; ajustar con una muestra en vivo.
MAP_SCREENS=tuple(f'MAP_Z{zone}' for zone in range(1,21))
MENU_PARENTS={'SETTINGS':('HOME',),'TEAM':('DIFFICULTY_Z5D2','DIFFICULTY_Z5D3'),
              'DIFFICULTY_Z5D2':('MAP_Z5',),'DIFFICULTY_Z5D3':('MAP_Z5',),'ZONES':MAP_SCREENS,
              **{screen:('HOME',) for screen in MAP_SCREENS}}


def validate_supported(plan):
    checked=farm_plan(plan['dungeon_id'],plan['difficulty'],plan['runs'],plan['energy_limit'],plan.get('target',''))
    if (checked['dungeon_id'],checked['difficulty']) not in ROUTE_COSTS:
        raise ValueError('Ruta aún no calibrada: disponibles Z5D2 y Z5D3 · Normal/Hard/Heroic. No se cambia tu objetivo.')
    return checked


def start_dungeon(game,plan):
    plan=validate_supported(plan)
    if os.name=='nt':raise ValueError('Runner de dungeon todavía no certificado en Windows; Fishing se conserva')
    mutex=Mutex('LAUNCHER');process=channel=guard=None
    try:
        guard=WindowGuard(game);guard.check()
        env=run_environment();env[ENV_WINDOW]=game.serialize();env['FARM_LAUNCHER_PID']=str(os.getpid())
        channel=Channel(env['FISHING_RUN_ID']);atomic_json(channel.directory/'farm_plan.json',plan)
        process=subprocess.Popen([python_executable(),'-B','-u',str(ROOT/'FARM_DUNGEON_PROCESS.py')],
                                 cwd=str(ROOT),env=env,**child_options())
        return process,channel,mutex
    except (Exception,KeyboardInterrupt):
        try:close_children((process,),channel)
        finally:mutex.close()
        raise
    finally:
        if guard is not None:guard.api.close()


class DungeonRunner:
    def __init__(self,io,capture,vision,channel,log,plan):
        self.io,self.cap,self.vision,self.channel,self.log=io,capture,vision,channel,log
        self.plan=validate_supported(plan);self.cost=None;self.safety_checked=False
        self.deadline=time.monotonic()+SESSION_SECONDS;self.difficulty=self.plan['difficulty'];self.balance=None
        self.budget=FarmBudget(max_runs=plan['runs'],max_energy=plan['energy_limit'],max_seconds=SESSION_SECONDS,max_gold=0)

    def check(self):
        self.io.emergency();self.io.check_game();self.log.check()
        if self.channel.stop_path.exists():raise SafetyStop('Parada solicitada')
        parent=os.environ.get('FARM_LAUNCHER_PID')
        if parent and os.getppid()!=int(parent):raise SafetyStop('El panel terminó; no se continúa sin supervisor')
        if time.monotonic()>=self.deadline:raise SafetyStop(f'Límite de sesión: {SESSION_SECONDS//60} minutos')

    def capture(self):
        self.check();shot=self.cap.grab({'left':0,'top':0,'width':1920,'height':1080})
        return np.frombuffer(shot.bgra,np.uint8).reshape(1080,1920,4)[:,:,:3].copy()

    def wait(self,predicate,timeout=10,expected=None):
        deadline=time.monotonic()+timeout;stable=0;frame=None
        while time.monotonic()<deadline:
            frame=self.capture()
            okay=predicate(frame) if callable(predicate) else self.vision.screen(frame)==predicate
            stable=stable+1 if okay else 0
            if stable>=2:return frame
            time.sleep(.12)
        expected=expected or (predicate if isinstance(predicate,str) else 'lectura estable')
        screen=self.vision.screen(frame) if frame is not None else 'SIN_LECTURA'
        familiar=self.vision.familiar_name(frame) if screen=='FAMILIAR_OFFER' else None
        snapshot=None
        if frame is not None:
            clean=np.zeros_like(frame)
            boxes=[(645,90,1280,215),(1000,930,1420,1055)]
            if screen=='HOME':boxes += [(15,15,165,190),(1760,910,1920,1080)]
            elif screen.startswith('AUTO_') or screen=='BATTLE_VICTORY':boxes += [(1680,130,1920,680)]
            if screen=='FAMILIAR_OFFER':
                boxes += [(350,130,1570,205),(360,640,720,780),(1240,640,1535,780),(550,890,965,1015)]
            elif screen=='DECLINE_CONFIRM':boxes += [(700,455,1220,620),(670,695,955,805)]
            for x,y,x1,y1 in boxes:clean[y:y1,x:x1]=frame[y:y1,x:x1]
            path=self.channel.directory/f'wait-timeout-{time.perf_counter_ns()}.png'
            try:
                if cv2.imwrite(str(path),clean):snapshot=path.name
            except (cv2.error,OSError):pass  # La falta de evidencia nunca permite continuar.
        self.log.emit('DUNGEON_WAIT_TIMEOUT',expected=expected,screen=screen,familiar=familiar,
                      snapshot=snapshot,timeout_seconds=timeout)
        raise SafetyStop(f'Pantalla no confirmada: {expected}; observada {screen}'+(f' · {familiar}' if familiar else ''))

    def click(self,screen,xy,key=None,roi=None,expected_familiar=None,expected_zone=None):
        self.check();frame=self.capture()
        if (self.vision.screen(frame)!=screen or (key and self.vision.locate(frame,key,roi) is None) or
                (expected_familiar is not None and self.vision.familiar_name(frame)!=expected_familiar) or
                (expected_zone is not None and self.vision.zone_choice(frame,expected_zone)!=xy)):
            raise SafetyStop('La pantalla cambió antes del clic; no se reintenta')
        self.check();self.io.click(xy)
        self.log.emit('DUNGEON_INPUT',screen=screen,xy=xy)
        time.sleep(.25)  # Unity debe procesar la suelta antes de abandonar el botón.
        self.io._move((960,1070))  # Zona neutra: no confundir hover con cambio de estado.

    def cost_shown(self,frame):
        x,y,x1,y1=COST_ROI;return self.vision.number(frame[y:y1,x:x1])

    def set_cost(self,screen,cost,menu_key):
        """Fija el coste (filas 1-5 del desplegable de PvP/Expedition/Trials) y lo confirma leyéndolo."""
        if type(cost) is not int or not 1<=cost<=5:raise SafetyStop('Coste fuera de 1-5')
        shown=None
        def stable(f):
            nonlocal shown
            current=self.cost_shown(f) if self.vision.screen(f)==screen else None
            okay=current is not None and current==shown;shown=current
            return okay
        self.wait(stable,10,'coste actual')  # la ventana entra animada
        if shown!=cost:
            self.click(screen,COST_DROPDOWN)
            menu=lambda f:self.vision.locate(f,menu_key,(760,95,1160,240)) is not None
            self.wait(menu,10,'menú de coste');time.sleep(1.2)  # el menú entra deslizándose; antes se pierde
            xy=(930,316+128*(cost-1))
            for _ in range(2):  # un clic durante la animación se pierde: un reintento como máximo
                self.check();self.io.click(xy);self.log.emit('DUNGEON_INPUT',screen=menu_key,xy=list(xy))
                self.io._move((960,1070))  # bajo la fila 5 hay familiares con tooltip que tapan la ventana
                try:self.wait(lambda f:not menu(f),4,'menú de coste cerrado');break
                except SafetyStop:pass
            else:
                # Pulsar la fila ya marcada no cierra el menú: cerrarlo con su X y confirmar leyendo.
                self.check();self.io.click((1310,182));self.wait(lambda f:not menu(f),5,'menú de coste cerrado')
        self.wait(lambda f:self.vision.screen(f)==screen and self.cost_shown(f)==cost,10,f'coste {cost}')
        return cost

    def close_menu(self,screen):
        if screen not in MENU_PARENTS:raise SafetyStop('Escape no autorizado en esta pantalla')
        self.wait(screen);self.check()
        if self.vision.screen(self.capture())!=screen:raise SafetyStop('La ventana cambió antes de Escape')
        self.check();self.io.escape();self.log.emit('DUNGEON_KEY',screen=screen,key='ESCAPE')
        return self.wait(lambda frame:self.vision.screen(frame) in MENU_PARENTS[screen])

    def scroll_menu(self,screen,amount):
        from Xlib import X
        from Xlib.ext import xtest
        if screen not in ('SETTINGS','ZONES') or self.vision.screen(self.capture())!=screen:
            raise SafetyStop('Menú de scroll no confirmado')
        if type(amount) is not int or not 0<abs(amount)<=80:raise SafetyStop('Scroll fuera de límite')
        xy=(1250,600) if screen=='SETTINGS' else (1150,600)
        self.io._move(xy)
        for _ in range(abs(amount)):
            self.check()
            if self.io.game_guard.api.cursor()!=xy:raise SafetyStop('Cursor cambió durante scroll')
            button=5 if amount>0 else 4
            xtest.fake_input(self.io.game_guard.api.display,X.ButtonPress,button)
            xtest.fake_input(self.io.game_guard.api.display,X.ButtonRelease,button)
            self.io.game_guard.api.display.sync();time.sleep(.025)
        time.sleep(.12)
        self.io._move((960,1070))

    def verify_settings(self):
        self.safety_checked=False;self.wait('HOME')
        self.click('HOME',(1830,986),'HOME_SETTINGS',(1760,910,1920,1080));self.wait('SETTINGS')
        self.scroll_menu('SETTINGS',-80);seen={}
        for _ in range(35):
            frame=self.wait('SETTINGS')
            for name in ('gold','gems','duplicates'):
                value=self.vision.setting(frame,name)
                if value is not None:
                    second=self.capture()
                    if self.vision.setting(second,name)!=value:raise SafetyStop('Ajuste nativo inestable')
                    seen[name]=value
                    if name in ('gold','gems') and value:raise SafetyStop(f'Gasto nativo activado: {name}; no se entra')
            if len(seen)==3:break
            self.scroll_menu('SETTINGS',6)  # Calibrado: 8 salta una lectura; 6 conserva solape.
        if len(seen)!=3:raise SafetyStop('No se pudieron comprobar todos los ajustes anti-gasto')
        if self.plan['target'] and seen['duplicates']:
            raise SafetyStop('Desactiva Decline duplicate familiars antes de farmear copias; no se entra')
        atomic_json(self.channel.directory/'native_settings.json',{'checked':seen,'changed_by_bot':False})
        self.close_menu('SETTINGS');self.safety_checked=True
        self.log.emit('DUNGEON_STATUS',message='Ajustes comprobados · cero oro/gemas',settings=seen)

    def go_home(self):
        frame=self.wait(lambda frame:self.vision.screen(frame)=='HOME' or self.vision.screen(frame) in MENU_PARENTS,12)
        for _ in range(4):
            screen=self.vision.screen(frame)
            if screen=='HOME':return
            frame=self.close_menu(screen)
        raise SafetyStop('Demasiados niveles de menú; no se envía otro Escape')

    def select_zone(self,zone):
        if type(zone) is not int or not 1<=zone<=20:raise ValueError('Zona sin referencia; no se sustituye')
        frame=self.wait(lambda frame:self.vision.screen(frame) in MAP_SCREENS)
        screen=self.vision.screen(frame)
        if screen==f'MAP_Z{zone}':return
        self.click(screen,(440,153),'ZONES_BUTTON',(315,100,565,205));frame=self.wait('ZONES')
        if self.vision.zone_choice(frame,zone) is None:self.scroll_menu('ZONES',-40)
        for step in range(20):
            frame=self.wait('ZONES');xy=self.vision.zone_choice(frame,zone)
            if xy is not None:
                self.wait(lambda frame:self.vision.zone_choice(frame,zone)==xy)
                self.click('ZONES',xy,expected_zone=zone);self.wait(f'MAP_Z{zone}')
                self.log.emit('ZONE_SELECTED',zone=zone,message=f'Zona {zone} confirmada; sin entrada')
                return
            if step<19:self.scroll_menu('ZONES',1)
        raise SafetyStop('Zona no encontrada o bloqueada; no se elige otra')

    def select_route(self):
        identifier=self.plan['dungeon_id'];difficulty=self.difficulty;screen='DIFFICULTY_'+identifier
        self.click('HOME',(90,90),'HOME_QUEST',(15,15,165,190))
        self.select_zone(dungeon(identifier)['zone'])
        xy,roi=((990,810),(880,675,1110,955)) if identifier=='Z5D2' else ((1457,480),(1330,380,1575,610))
        self.click('MAP_Z5',xy,'NODE_'+identifier,roi)
        frame=self.wait(screen);self.cost=self.vision.cost(frame,difficulty)
        expected=ROUTE_COSTS[(identifier,difficulty)]
        if self.cost!=expected or self.vision.cost(self.capture(),difficulty)!=self.cost:
            raise SafetyStop(f'Coste/dificultad no confirmado: esta calibración exige {expected} de energía')
        xy,roi=DIFFICULTY_BUTTONS[difficulty];self.click(screen,xy,difficulty.upper(),roi);self.wait('TEAM')

    def affordable(self,balance):
        """Dificultad más alta, sin superar la elegida, que paga el saldo; None si ninguna."""
        options=LADDER[LADDER.index(self.plan['difficulty']):]
        return next((d for d in options if ROUTE_COSTS[(self.plan['dungeon_id'],d)]<=balance),None)

    def lower_difficulty(self,balance):
        """En TEAM sin saldo: Escape a la dificultad y elegir otra pagable; False si no queda ninguna."""
        level=self.affordable(balance)
        screen='DIFFICULTY_'+self.plan['dungeon_id']
        self.close_menu('TEAM')
        if level is None:return False
        frame=self.wait(screen);cost=self.vision.cost(frame,level)
        if cost!=ROUTE_COSTS[(self.plan['dungeon_id'],level)]:raise SafetyStop(f'Coste de {level} no confirmado')
        xy,roi=DIFFICULTY_BUTTONS[level];self.click(screen,xy,level.upper(),roi);self.wait('TEAM')
        self.difficulty,self.cost=level,cost
        self.log.emit('DUNGEON_STATUS',message=f'Energía {balance}: se baja a {level}')
        return True

    def read_team_energy(self):
        balance=None
        def known(frame):
            nonlocal balance
            current=self.vision.energy(frame)
            okay=self.vision.screen(frame)=='TEAM' and current is not None and current==balance
            balance=current
            return okay
        # La barra puede mostrar el reloj de recarga en vez del saldo; nunca se usa como saldo.
        frame=self.wait(known,ENERGY_WAIT,'saldo de energía en TEAM')
        if balance is None or self.vision.screen(frame)!='TEAM':raise SafetyStop('Energía desconocida')
        return balance

    def enter(self,cycle):
        """Entra con la dificultad pagable más alta; None si no queda energía para ninguna."""
        if not self.safety_checked or self.cost!=ROUTE_COSTS[(self.plan['dungeon_id'],self.difficulty)]:
            raise SafetyStop('Ruta o ajustes sin confirmar')
        balance=self.read_team_energy()
        while balance[0]<self.cost:
            if not self.lower_difficulty(balance[0]):
                self.balance=balance[0];return None
            balance=self.read_team_energy()
        attempt=f'{self.channel.run_id}:{cycle}'
        if not self.budget.reserve_entry(attempt,resource='ENERGY',balance=balance[0],cost=self.cost):
            raise SafetyStop('Entrada ya reservada; no repetir ACCEPT')
        atomic_json(self.channel.directory/f'entry-{cycle}.intent.json',
                    {'attempt_id':attempt,'plan':self.plan,'balance':balance,'cost':self.cost,
                     'budget':self.budget.payload(),'perf_ns':time.perf_counter_ns(),'effect_confirmed':False})
        self.click('TEAM',(1215,982),'ACCEPT',(1000,930,1420,1035))
        self.balance=balance[0]-self.cost  # cota inferior: la regeneración solo suma
        self.log.emit('DUNGEON_ENTERED',attempt_id=attempt,energy_before=balance[0],energy_reserved=self.cost,difficulty=self.difficulty)
        return attempt

    def decline_other(self,frame,attempt,offer):
        """Sin objetivo se rechaza toda oferta legible; con objetivo, solo otro nombre conocido."""
        name=self.vision.familiar_name(frame);target=self.plan['target'];glyph=familiar_glyph(frame)
        if glyph is None:return False
        if target and (not isinstance(name,str) or normalize(name)==normalize(target)):return False
        same=lambda f:(lambda g:g is not None and np.array_equal(g,glyph))(familiar_glyph(f))
        frame=self.wait('FAMILIAR_OFFER')
        if not same(frame):raise SafetyStop('Nombre de familiar inestable; no se rechaza')
        path=self.channel.directory/f'decline-{offer}.intent.json'
        if path.exists():raise SafetyStop('Rechazo ya registrado; no se repite una decisión incierta')
        intent={'attempt_id':attempt,'familiar':name,'target':target,'action':'DECLINE','effect_confirmed':False}
        atomic_json(path,intent)
        self.click('FAMILIAR_OFFER',(755,955),'DECLINE',(550,890,965,1015),expected_familiar=name if target else None)
        self.wait('DECLINE_CONFIRM')
        self.click('DECLINE_CONFIRM',(818,752),'DECLINE_YES',(670,695,955,805))
        def closed(frame):
            screen=self.vision.screen(frame)
            if screen in ('AUTO_ON','AUTO_OFF','AUTO_ON_BATTLE','BATTLE_VICTORY','VICTORY','LOADING'):return True
            if screen!='FAMILIAR_OFFER':return False
            # Con el diálogo de confirmación ya cerrado (YES verificado), una oferta legible es la
            # siguiente, aunque sea del mismo familiar: hay combates con dos iguales. Rechazar no gasta.
            return self.vision.familiar_name(frame) is not None if target else familiar_glyph(frame) is not None
        self.wait(closed)
        atomic_json(path,{**intent,'effect_confirmed':True})
        label=name or 'familiar sin referencia'
        self.log.emit('FAMILIAR_DECLINED',message=f'{label} rechazado · objetivo {target or "ninguno"}',familiar=name,target=target)
        return True

    def observe(self,attempt,cycle,*,auto_started=False,rerun=False):
        """Cierra la run; True si volvió a TEAM con RERUN para la siguiente."""
        previous=list(self.channel.directory.glob(f'decline-{cycle}-*.intent.json'))
        if any(json.loads(path.read_text()).get('effect_confirmed') is not True for path in previous):
            raise SafetyStop('Rechazo previo sin confirmar; no se continúa')
        unknown_since=None;story_sent=set();declined=len(previous);deadline=time.monotonic()+180;battle_autos=0;map_autos=0;map_off_since=None;battle_off_since=None
        while time.monotonic()<deadline:
            frame=self.capture();screen=self.vision.screen(frame)
            if screen=='FAMILIAR_OFFER':
                cv2.imwrite(str(self.channel.directory/'familiar-offer.png'),frame[110:900,350:1600])
                if declined>=20:raise SafetyStop('Demasiadas ofertas de familiar; no se continúa')
                if self.plan['target'] and self.vision.familiar_name(frame) is None:
                    # La oferta entra animada: esperar el nombre legible; uno desconocido sigue pausando.
                    try:frame=self.wait(lambda f:self.vision.familiar_name(f) is not None,3,'nombre de familiar')
                    except SafetyStop:pass
                if not self.decline_other(frame,attempt,f'{cycle}-{declined+1}'):
                    raise SafetyStop('Oferta de familiar objetivo o desconocido: pausa para decidir; no se gasta oro ni gemas')
                declined+=1;unknown_since=None;continue
            if screen=='WB_DEFEAT' and getattr(self,'defeat_continues',False):
                # Expedition/Trials: perder es normal. Cerrar con TOWN y seguir gastando.
                frame=self.wait('WB_DEFEAT');x,y=self.vision.locate(frame,'RESULT_TOWN',(700,915,1500,1080))
                h,w=self.vision.templates['RESULT_TOWN'].shape[:2]
                self.click('WB_DEFEAT',(x+w//2,y+h//2),'RESULT_TOWN',(700,915,1500,1080));self.go_home()
                self.budget.finish_run(attempt,'DEFEAT',closure_confirmed=True)
                self.log.emit('DUNGEON_COMPLETE',message=f'Run {cycle}: derrota (normal en este modo)',budget=self.budget.payload())
                return False
            if screen=='VICTORY':
                frame=self.wait('VICTORY')
                cv2.imwrite(str(self.channel.directory/f'result-{cycle}.png'),frame[110:930,1070:1600])
                atomic_json(self.channel.directory/f'result-{cycle}.json',
                            {'attempt_id':attempt,'outcome':'VICTORY','loot':None,'gold_gain':None,'xp_gain':None,
                             'closure_confirmed':False})
                # RERUN solo si el saldo estimado (cota inferior) paga otra run igual.
                again=(rerun and self.balance is not None and self.balance>=self.cost and
                       self.budget.energy_reserved+self.cost<=self.plan['energy_limit'])
                if not again:
                    # TOWN cambia de sitio: a la derecha con RERUN (Quest/Raid), centrado sin él (Expedition).
                    x,y=self.vision.locate(frame,'TOWN',(700,900,1500,1080));h,w=self.vision.templates['TOWN'].shape[:2]
                    self.click('VICTORY',(x+w//2,y+h//2),'TOWN',(700,900,1500,1080));self.go_home()
                self.budget.finish_run(attempt,'VICTORY',closure_confirmed=True)
                atomic_json(self.channel.directory/f'result-{cycle}.json',
                            {'attempt_id':attempt,'outcome':'VICTORY','loot':None,'gold_gain':None,'xp_gain':None,
                             'closure_confirmed':True,'budget':self.budget.payload()})
                self.log.emit('DUNGEON_COMPLETE',message=f'Dungeon {cycle} completada'+(' · RERUN' if again else ' y cerrada'),
                              budget=self.budget.payload())
                if not again:return None
                # RERUN entra directamente en la siguiente run (sin TEAM ni ACCEPT) y gasta en ese
                # momento: reservar e intención antes del clic, como ACCEPT.
                following=f'{self.channel.run_id}:{cycle+1}'
                if not self.budget.reserve_entry(following,resource='ENERGY',balance=self.balance,cost=self.cost):
                    raise SafetyStop('Entrada ya reservada; no repetir RERUN')
                atomic_json(self.channel.directory/f'entry-{cycle+1}.intent.json',
                            {'attempt_id':following,'plan':self.plan,'balance':self.balance,'cost':self.cost,'via':'RERUN',
                             'budget':self.budget.payload(),'perf_ns':time.perf_counter_ns(),'effect_confirmed':False})
                self.click('VICTORY',(834,996),'RERUN',(650,920,1020,1075))
                self.log.emit('DUNGEON_ENTERED',attempt_id=following,energy_before=self.balance,energy_reserved=self.cost,
                              difficulty=getattr(self,'difficulty',None),via='RERUN')
                self.balance-=self.cost
                return following
            if screen=='AUTO_OFF':
                # El mapa pasa un instante por OFF al entrar y salir de combates: un clic ahí lo
                # apaga. Solo se pulsa si sigue OFF 2 s; repetirlo más de 4 veces detiene.
                map_off_since=map_off_since or time.monotonic()
                if time.monotonic()-map_off_since>=(0 if not auto_started else 2):
                    if map_autos>=4:raise SafetyStop('Auto del mapa se apaga repetidamente; revisar posible derrota')
                    self.wait('AUTO_OFF');self.click('AUTO_OFF',(1880,530))
                    self.wait(lambda f:self.vision.screen(f)!='AUTO_OFF',5,'Auto del mapa activado')
                    auto_started=True;map_autos+=1;map_off_since=None
                time.sleep(.12);continue
            map_off_since=None
            if screen=='AUTO_OFF_BATTLE':
                # Un combate puede empezar sin Auto (p. ej. tras pausar el mapa). Al entrar está animado y
                # el clic se pierde: pulsar solo tras 2 s estables; si no prende, se reintenta (máx. 3).
                battle_off_since=battle_off_since or time.monotonic()
                if time.monotonic()-battle_off_since>=2:
                    if battle_autos>=3:raise SafetyStop('Auto de combate se apaga repetidamente; no se insiste')
                    self.click('AUTO_OFF_BATTLE',(1880,530));battle_autos+=1;battle_off_since=None
                    try:self.wait(lambda f:self.vision.screen(f)!='AUTO_OFF_BATTLE',5,'Auto de combate activado')
                    except SafetyStop:pass
                unknown_since=None;time.sleep(.12);continue
            battle_off_since=None
            if screen=='AUTO_ON':auto_started=True  # Auto de combate no acredita Auto del mapa.
            elif screen=='STORY_ZORUL':
                signature=hash(frame[420:813,780:1590].tobytes())
                if signature not in story_sent:
                    if len(story_sent)>=4:raise SafetyStop('Demasiados diálogos de historia')
                    self.wait('STORY_ZORUL');story_sent.add(signature)
                    self.click('STORY_ZORUL',(1665,646),'STORY_ARROW',(1620,575,1720,720))
            elif screen not in ('AUTO_ON','AUTO_OFF','AUTO_ON_BATTLE','BATTLE_VICTORY','LOADING'):
                unknown_since=unknown_since or time.monotonic()
                if time.monotonic()-unknown_since>8:
                    cv2.imwrite(str(self.channel.directory/'unknown.png'),frame[100:915,320:1600])
                    raise SafetyStop('Pantalla/oferta/derrota no reconocida: pausa sin Persuade ni gasto')
            if screen in ('AUTO_ON','AUTO_ON_BATTLE','BATTLE_VICTORY','STORY_ZORUL','LOADING'):unknown_since=None
            time.sleep(.12)
        raise SafetyStop('Dungeon sin cierre confirmado en 3 minutos; no se repite')

    def run(self):
        self.go_home();self.verify_settings()  # Ajustes nativos: una vez por sesión.
        following=None;runs=self.plan['runs']
        for cycle in range(1,runs+1):
            if following is None:
                if self.balance is not None:
                    level=self.affordable(self.balance)
                    if level is None:
                        self.log.emit('DUNGEON_STATUS',message=f'Energía agotada ({self.balance}) · detenido');return
                    self.difficulty=level
                if self.budget.energy_reserved+ROUTE_COSTS[(self.plan['dungeon_id'],self.difficulty)]>self.plan['energy_limit']:
                    self.log.emit('DUNGEON_STATUS',message='Límite de energía alcanzado');return
                self.select_route()
                attempt=self.enter(cycle)
                if attempt is None:
                    self.go_home();self.log.emit('DUNGEON_STATUS',message=f'Energía agotada ({self.balance}) · detenido');return
            else:attempt=following
            following=self.observe(attempt,cycle,rerun=cycle<runs)
        self.log.emit('DUNGEON_STATUS',message='Límite de runs alcanzado · detenido',budget=self.budget.payload())


def run_dungeon():
    from .linux import LinuxIO,LinuxCapture
    channel=Channel(os.environ['FISHING_RUN_ID']);io=log=None;locks=[]
    try:
        plan=validate_supported(json.loads((channel.directory/'farm_plan.json').read_text()))
        for role in ('CONTROL','CATCH'):locks.append(Mutex(role))
        log=Telemetry('DUNGEON',channel.run_id);io=LinuxIO();io.control_mode=True
        with LinuxCapture(io.game_guard) as capture:
            DungeonRunner(io,capture,DungeonVision(),channel,log,plan).run()
    except (Exception,KeyboardInterrupt) as exc:
        if log:log.emit('SAFETY_STOP',message=str(exc) or 'F8',reason=str(exc) or 'F8',human=True)
        channel.stop('DUNGEON',str(exc) or 'F8')
    finally:
        if io:io.close()
        if log:log.close()
        for lock in reversed(locks):lock.close()
