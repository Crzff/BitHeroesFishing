"""Runner Steam/niri: rutas locales calibradas, sin compras ni motores de pesca."""

import json
import os
import subprocess
import time

import cv2
import numpy as np

from .control_flow import SafetyStop
from .dungeon_catalog import FAMILIARS,dungeon,farm_plan,normalize
from .dungeon_vision import DungeonVision,familiar_glyph
from . import loot
from .farm_budget import FarmBudget
from .game_window import ENV_WINDOW,WindowGuard
from .processes import Mutex,child_options,close_children,python_executable
from .protocol import Channel,atomic_json
from .telemetry import ROOT,Telemetry,run_environment

# Coste universal (wiki Zones): Normal 10, Hard 20, Heroic 30; especial (D4) 20.
COSTS={'Normal':10,'Hard':20,'Heroic':30,'Special':20}
# Nodo de cada dungeon en el mapa de su zona (igual en todas las cuentas); calibrado en vivo.
NODES={k:tuple(v) for k,v in json.loads((ROOT/'assets/dungeon_nodes.json').read_text())['nodes'].items()}
LADDER=('Heroic','Hard','Normal')
ENTRY_SCREENS=('DIFFICULTY','DUNGEON_SPECIAL')
DIFFICULTY_BUTTONS={'Normal':((550,495),(400,450,715,550)),'Hard':((958,495),(780,430,1140,570)),
                    'Heroic':((1365,495),(1200,450,1530,550))}
SESSION_SECONDS=3600
# Ventanas de modo -> su X (coordenada, plantilla, ROI). Sin plantilla: basta la pantalla reconocida.
# Tras una desconexión: RECONNECT, recompensa diaria gratuita (CLAIM) e ITEMS. Nunca compra.
WINDOW_CLOSERS={'DISCONNECTED':((960,742),'RECONNECT',(770,665,1150,820)),
                'SEASON_REWARDS':((960,962),'SEASON_CLAIM',(740,885,1180,1040)),
                'ITEMS':(None,'ITEMS_CLOSE',(1200,150,1500,450)),
                # Resultado de una run que quedó abierta: TOWN no gasta nada (cambia de sitio: se localiza).
                'VICTORY':(None,'TOWN',(700,900,1500,1080)),'WB_VICTORY':(None,'RESULT_TOWN',(700,915,1500,1080)),
                'WB_DEFEAT':(None,'RESULT_TOWN',(700,915,1500,1080)),
                'NEWS':((1118,964),'NEWS_CLOSE',(935,885,1310,1045)),'TRIALS':((1490,236),'TRIALS_CLOSE',(1404,150,1584,330)),'PVP':((1494,226),'PVP_CLOSE',(1410,140,1580,310)),
                'EXPEDITION':((1490,240),'EXP_CLOSE',(1400,150,1580,330)),'IDOL_MAP':((1655,135),'IDOL_CLOSE',(1570,50,1740,220)),
                'PORTAL':((1362,214),'PORTAL_CLOSE',(1280,130,1450,300)),'RAID':((1468,236),'RAID_CLOSE',(1380,150,1560,320)),
                'WB_LIST':((1536,214),'WB_CLOSE',(1500,180,1575,250)),'WB_CAROUSEL':((1470,240),None,None),
                'WB_SUMMON':((1266,260),None,None)}
COST_ROI=(1210,392,1310,448)
COST_DROPDOWN=(1370,416)
ENERGY_WAIT=30  # ponytail: acotado sin medir el periodo real del reloj; ajustar con una muestra en vivo.
MAP_SCREENS=tuple(f'MAP_Z{zone}' for zone in range(1,21))
# Pantallas de una run en marcha que pueden quedar al reiniciar el bot.
LEFTOVER_SCREENS=('AUTO_ON','AUTO_ON_BATTLE','AUTO_OFF','AUTO_OFF_BATTLE','BATTLE_VICTORY','LOADING','FAMILIAR_OFFER','DECLINE_CONFIRM','STORY',
                  'RESUME_DUNGEON','CAPTURE_SUCCESS')


class OfferChanged(Exception):
    """La oferta cambió mientras se decidía (entró la siguiente): se vuelve a evaluar sin pulsar nada."""
MENU_PARENTS={'SETTINGS':('HOME',),'TEAM':ENTRY_SCREENS,
              'DIFFICULTY':MAP_SCREENS,'DUNGEON_SPECIAL':MAP_SCREENS,'ZONES':MAP_SCREENS,
              **{screen:('HOME',) for screen in MAP_SCREENS}}


def validate_supported(plan):
    targets=[str(name).strip() for name in plan.get('targets') or ([plan['target']] if plan.get('target') else []) if str(name).strip()]
    for name in targets:farm_plan(plan['dungeon_id'],plan['difficulty'],1,1,name)  # cada objetivo debe salir en esa ruta
    checked=farm_plan(plan['dungeon_id'],plan['difficulty'],plan['runs'],plan['energy_limit'],targets[0] if targets else '')
    checked['targets']=targets
    gold=plan.get('max_gold',0)
    if type(gold) is not int or not 0<=gold<=10_000_000:raise ValueError('Cuota de oro inválida (0-10.000.000)')
    checked['max_gold']=gold
    if checked['dungeon_id'] not in NODES:
        raise ValueError('Dungeon aún sin calibrar en el mapa; no se cambia tu objetivo.')
    return checked


def start_dungeon(game,plan):
    plan=validate_supported(plan)
    if os.name=='nt':raise ValueError('Runner de dungeon todavía no certificado en Windows; Fishing se conserva')
    mutex=Mutex('LAUNCHER');process=channel=guard=None
    try:
        env=run_environment();env['FARM_LAUNCHER_PID']=str(os.getpid())
        if game is not None:guard=WindowGuard(game);guard.check();env[ENV_WINDOW]=game.serialize()
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
    @property
    def targets(self):
        """Familiares objetivo: lista nueva o el campo único anterior."""
        plan=getattr(self,'plan',None) or {}
        return list(plan.get('targets') or ([plan['target']] if plan.get('target') else []))

    def __init__(self,io,capture,vision,channel,log,plan):
        self.io,self.cap,self.vision,self.channel,self.log=io,capture,vision,channel,log
        self.plan=validate_supported(plan);self.cost=None;self.safety_checked=False
        self.deadline=time.monotonic()+SESSION_SECONDS;self.difficulty=self.plan['difficulty'];self.balance=None
        # Oro solo para Persuade de objetivos, con cuota por sesión; nunca gemas (Bribe).
        self.budget=FarmBudget(max_runs=plan['runs'],max_energy=plan['energy_limit'],max_seconds=SESSION_SECONDS,
                               max_gold=int(self.plan.get('max_gold',0)))

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
        deadline=time.monotonic()+timeout;stable=0;frame=None;stories=0
        while time.monotonic()<deadline:
            frame=self.capture()
            okay=predicate(frame) if callable(predicate) else self.vision.screen(frame)==predicate
            stable=stable+1 if okay else 0
            if stable>=2:return frame
            if (not okay and predicate not in ('STORY','STORY_ZORUL') and stories<30 and
                    self.vision.screen(frame) in ('STORY','STORY_ZORUL')):
                # Diálogo de historia (primer jefe, mazmorra...): se pasa con su flecha; no gasta nada.
                self.check();self.io.click((1665,646));time.sleep(.25);self.io._move((960,1070))
                self.log.emit('DUNGEON_INPUT',screen='STORY',xy=[1665,646]);stories+=1
                deadline+=2;time.sleep(.8);continue
            time.sleep(.12)
        expected=expected or (predicate if isinstance(predicate,str) else 'lectura estable')
        screen=self.vision.screen(frame) if frame is not None else 'SIN_LECTURA'
        familiar=self.offer_name(frame) if screen=='FAMILIAR_OFFER' else None
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

    def record_loot(self):
        """Suma el LOOT RECAP visible y el que queda bajo el scroll (las casillas repetidas no cuentan dos veces)."""
        if not loot.ENABLED:return
        seen={};previous=None
        for _ in range(8):
            cells=self.vision.loot_cells(self.capture())
            for cell in cells:seen.setdefault((cell['icon'][::8,::8].tobytes(),cell['amount']),cell)
            signature=[(c['kind'],c['rarity'],c['amount']) for c in cells]
            if len(cells)<6 or signature==previous:break
            previous=signature;self.wheel(1,(1320,770));time.sleep(.6)
        loot.record(list(seen.values()))
        self.log.emit('LOOT_RECORDED',cells=len(seen))

    def offer_name(self,frame):
        identifier=getattr(self,'plan',{}).get('dungeon_id')
        return self.vision.familiar_name(frame,[name for name,ids in FAMILIARS.items() if identifier in ids])

    def click(self,screen,xy,key=None,roi=None,expected_familiar=None,expected_zone=None):
        self.check();frame=self.capture()
        if (self.vision.screen(frame)!=screen or (key and self.vision.locate(frame,key,roi) is None) or
                (expected_familiar is not None and self.offer_name(frame)!=expected_familiar) or
                (expected_zone is not None and self.vision.zone_choice(frame,expected_zone)!=xy)):
            raise SafetyStop('La pantalla cambió antes del clic; no se reintenta')
        self.check();self.io.click(xy)
        self.log.emit('DUNGEON_INPUT',screen=screen,xy=xy)
        time.sleep(.25)  # Unity debe procesar la suelta antes de abandonar el botón.
        self.io._move((960,1070))  # Zona neutra: no confundir hover con cambio de estado.

    def ensure_home(self,keep=()):
        """Cierra con su X verificada las ventanas de modo abiertas hasta llegar a Home (o a una de keep).
        Si el juego quedó a mitad de una run (bot reiniciado), la deja terminar: Auto encendido, ofertas
        rechazadas (no gasta) y el resultado se cierra con TOWN."""
        running=LEFTOVER_SCREENS
        for _ in range(240):  # una run reanudada puede durar varios minutos (cada vuelta ~2 s)
            frame=self.wait(lambda f:self.vision.screen(f)=='HOME' or self.vision.screen(f) in keep or
                            self.vision.screen(f) in WINDOW_CLOSERS or self.vision.screen(f) in MENU_PARENTS or
                            self.vision.screen(f) in running,60,'Home o ventana conocida')
            screen=self.vision.screen(frame)
            if screen=='HOME' or screen in keep:return screen
            if screen in running:
                self.finish_leftover_run(screen);continue
            if screen in MENU_PARENTS:self.close_menu(screen);continue
            xy,key,roi=WINDOW_CLOSERS[screen];time.sleep(.4)
            if xy is None:  # botón que cambia de sitio: se localiza
                x,y=self.vision.locate(self.capture(),key,roi);h,w=self.vision.templates[key].shape[:2];xy=(x+w//2,y+h//2)
            self.click(screen,xy,key,roi)
            if screen=='DISCONNECTED':
                self.log.emit('RECONNECT',message='Desconectado: RECONNECT')
                self.wait(lambda f:self.vision.screen(f)!='DISCONNECTED',90,'reconexión')
            time.sleep(1)
        raise SafetyStop('No se pudo volver a Home cerrando ventanas')

    def finish_leftover_run(self,screen):
        """Un paso de una run que quedó a medias al reiniciar el bot; nunca gasta."""
        if screen=='FAMILIAR_OFFER':
            # Sin sesión no hay cuota de oro: rechazar es gratis (BRIBE nunca).
            self.click('FAMILIAR_OFFER',(755,955),'DECLINE',(550,890,965,1015))
            self.log.emit('FAMILIAR_DECLINED',message='Oferta de una run anterior rechazada al reanudar')
        elif screen=='DECLINE_CONFIRM':self.click('DECLINE_CONFIRM',(818,752),'DECLINE_YES',(670,695,955,805))
        elif screen=='STORY':self.click('STORY',(1665,646),'STORY_ARROW',(1620,575,1720,720))
        elif screen=='CAPTURE_SUCCESS':self.click('CAPTURE_SUCCESS',(958,962),'CAPTURE_CLOSE',(780,890,1140,1040))
        elif screen=='RESUME_DUNGEON':
            # Desconexión a mitad de dungeon: la energía ya se gastó; continuarla da el botín.
            self.click('RESUME_DUNGEON',(812,750),'DECLINE_YES',(670,695,955,805))
            self.log.emit('DUNGEON_STATUS',message='Dungeon interrumpida por desconexión: se continúa')
        elif screen in ('AUTO_OFF','AUTO_OFF_BATTLE'):
            time.sleep(2)
            if self.vision.screen(self.capture())==screen:self.click(screen,(1880,530))
        else:time.sleep(2)  # la run sigue sola con Auto
        time.sleep(.5)

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
                time.sleep(.25)  # Unity procesa la suelta por frames: no abandonar la fila al instante
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
        if screen not in ('SETTINGS','ZONES') or self.vision.screen(self.capture())!=screen:
            raise SafetyStop('Menú de scroll no confirmado')
        if type(amount) is not int or not 0<abs(amount)<=80:raise SafetyStop('Scroll fuera de límite')
        self.wheel(amount,(1250,600) if screen=='SETTINGS' else (1150,600))

    def wheel(self,amount,xy):
        """Rueda sobre xy (positivo = bajar); el llamante confirma antes la pantalla."""
        from Xlib import X
        from Xlib.ext import xtest
        if hasattr(self.io,'wheel'):  # gamescope: rueda en su servidor X, sin cursor del usuario
            self.io.wheel(amount,xy);time.sleep(.12);self.io._move((960,1070));return
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
        self.scroll_menu('SETTINGS',-80);seen={};changed=[]
        for _ in range(35):
            frame=self.wait('SETTINGS')
            for name in ('gold','gems','duplicates'):
                value=self.vision.setting(frame,name)
                if value is not None:
                    second=self.capture()
                    if self.vision.setting(second,name)!=value:raise SafetyStop('Ajuste nativo inestable')
                    # crzf: auto persuadir con oro/gemas nunca; con objetivos tampoco rechazar duplicados.
                    if value and (name in ('gold','gems') or self.targets):
                        xy=self.vision.setting_box(second,name)
                        if xy is None:raise SafetyStop(f'Gasto nativo activado: {name}; no se entra')
                        self.click('SETTINGS',xy)
                        frame=self.wait(lambda f:self.vision.setting(f,name) is False,5,f'{name} desactivado')
                        value=False;changed.append(name)
                        self.log.emit('DUNGEON_STATUS',message=f'Ajuste {name} desactivado por el bot')
                    seen[name]=value
            if len(seen)==3:break
            self.scroll_menu('SETTINGS',6)  # Calibrado: 8 salta una lectura; 6 conserva solape.
        if len(seen)!=3:raise SafetyStop('No se pudieron comprobar todos los ajustes anti-gasto')
        atomic_json(self.channel.directory/'native_settings.json',{'checked':seen,'changed_by_bot':changed})
        self.close_menu('SETTINGS');self.safety_checked=True
        self.log.emit('DUNGEON_STATUS',message='Ajustes comprobados · cero oro/gemas',settings=seen)

    def go_home(self):
        # Ventanas de modo o una run que quedó a medias (bot reiniciado): ensure_home las resuelve.
        if self.vision.screen(self.capture()) in tuple(WINDOW_CLOSERS)+LEFTOVER_SCREENS:self.ensure_home()
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

    def entry_screen(self):
        return 'DUNGEON_SPECIAL' if self.plan['difficulty']=='Special' else 'DIFFICULTY'

    def press_level(self,level):
        screen=self.entry_screen()
        if level=='Special':self.click(screen,(1130,945),'SPECIAL_ENTER',(940,870,1320,1020))
        else:xy,roi=DIFFICULTY_BUTTONS[level];self.click(screen,xy,level.upper(),roi)
        self.wait('TEAM')

    def select_route(self):
        identifier=self.plan['dungeon_id'];difficulty=self.difficulty;screen=self.entry_screen()
        self.click('HOME',(90,90),'HOME_QUEST',(15,15,165,190))
        zone=dungeon(identifier)['zone'];self.select_zone(zone)
        time.sleep(1)  # el mapa entra animado: un clic temprano cae en otro sitio
        self.click(f'MAP_Z{zone}',NODES[identifier])
        frame=self.wait(lambda f:self.vision.screen(f)==screen and self.vision.dungeon_title(f,identifier),10,f'ventana de {identifier}')
        self.cost=self.vision.cost(frame,difficulty)
        if self.cost!=COSTS[difficulty] or self.vision.cost(self.capture(),difficulty)!=self.cost:
            raise SafetyStop(f'Coste/dificultad no confirmado: se esperaba {COSTS[difficulty]} de energía')
        self.press_level(difficulty)

    def affordable(self,balance):
        """Dificultad más alta, sin superar la elegida, que paga el saldo; None si ninguna."""
        options=('Special',) if self.plan['difficulty']=='Special' else LADDER[LADDER.index(self.plan['difficulty']):]
        return next((d for d in options if COSTS[d]<=balance),None)

    def lower_difficulty(self,balance):
        """En TEAM sin saldo: Escape a la dificultad y elegir otra pagable; False si no queda ninguna."""
        level=self.affordable(balance)
        screen=self.entry_screen()
        self.close_menu('TEAM')
        if level is None:return False
        frame=self.wait(screen);cost=self.vision.cost(frame,level)
        if cost!=COSTS[level]:raise SafetyStop(f'Coste de {level} no confirmado')
        self.press_level(level)
        self.difficulty,self.cost=level,cost
        self.log.emit('DUNGEON_STATUS',message=f'Energía {balance}: se baja a {level}')
        return True

    def clock_only(self):
        """La barra de energía muestra un reloj (dígitos con ':') y no un saldo legible."""
        frame=self.capture()
        if self.vision.energy(frame) is not None:return False
        return self.vision.energy_clock(frame)

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
        if not self.safety_checked or self.cost!=COSTS[self.difficulty]:
            raise SafetyStop('Ruta o ajustes sin confirmar')
        try:
            balance=self.read_team_energy()
        except SafetyStop:
            # Con menos energía de la que cuesta cualquier run, la barra solo muestra el reloj de
            # recarga. Si el reloj es lo único legible, se termina sin entrar (nunca gasta).
            # El reloj cambia cada segundo: una lectura en pleno cambio no basta; se mira unos segundos.
            end=time.monotonic()+6
            while time.monotonic()<end:
                if self.vision.screen(self.capture())=='TEAM' and self.clock_only():
                    self.close_menu('TEAM');self.balance=0;return None
                time.sleep(.3)
            raise
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
        name=self.offer_name(frame);targets={normalize(n) for n in self.targets}
        target=', '.join(self.targets);glyph=familiar_glyph(frame)
        if glyph is None:return False
        if targets and (not isinstance(name,str) or normalize(name) in targets):return False
        same=lambda f:(lambda g:g is not None and np.array_equal(g,glyph))(familiar_glyph(f))
        frame=self.wait('FAMILIAR_OFFER')
        if not same(frame):raise OfferChanged()
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
            return self.offer_name(frame) is not None if target else familiar_glyph(frame) is not None
        try:self.wait(closed,15,'oferta cerrada')
        except SafetyStop:
            # YES ya se pulsó: si el juego sigue la run (combate/mapa), la oferta quedó cerrada.
            if self.vision.screen(self.capture()) not in ('AUTO_ON','AUTO_OFF','AUTO_ON_BATTLE','AUTO_OFF_BATTLE','BATTLE_VICTORY','VICTORY','LOADING'):raise
        atomic_json(path,{**intent,'effect_confirmed':True})
        label=name or 'familiar sin referencia'
        self.log.emit('FAMILIAR_DECLINED',message=f'{label} rechazado · objetivo {target or "ninguno"}',familiar=name,target=target)
        return True

    def persuade(self,frame,attempt,offer,name):
        """Persuade con oro a un objetivo: coste leído, cuota de sesión, diálogo de oro confirmado.

        Nunca BRIBE (gemas). Sin cuota o coste ilegible no se gasta: la oferta se rechaza.
        """
        frame=self.wait('FAMILIAR_OFFER');cost=self.vision.offer_cost(frame);glyph=familiar_glyph(frame)
        # Identidad antes de pulsar: sigue la oferta, con el mismo coste y, si es del catálogo, el mismo
        # nombre. La imagen del nombre no sirve: el dibujo del familiar puede taparla y moverse (Callumoth).
        same=lambda f:(self.vision.screen(f)=='FAMILIAR_OFFER' and self.vision.offer_cost(f)==cost and
                       (not name or self.offer_name(f) in (name,None)))
        if cost is None:raise SafetyStop('Coste de Persuade ilegible; no se gasta oro')
        if not same(self.capture()):raise OfferChanged()  # nada reservado ni pulsado: se vuelve a leer
        if not name:name=self.vision.read_text(glyph).title() if glyph is not None else 'Familiar'
        action=f'persuade-{offer}'
        try:
            # El saldo de oro se muestra abreviado (7,6M): la protección es la cuota de sesión.
            self.budget.reserve_gold(action,currency='GOLD',purpose='PERSUADE',target=name,balance=cost,cost=cost)
        except ValueError as exc:
            self.log.emit('FAMILIAR_KEPT_GOLD',message=f'{name}: sin cuota de oro ({exc}); se rechaza',familiar=name)
            if not self.decline_any(frame,attempt,offer,name):raise SafetyStop('No se pudo rechazar el objetivo sin cuota')
            return
        path=self.channel.directory/f'persuade-{offer}.intent.json'
        intent={'attempt_id':attempt,'familiar':name,'cost':cost,'currency':'GOLD','effect_confirmed':False}
        atomic_json(path,intent)
        self.click('FAMILIAR_OFFER',(528,704))  # FAMILIAR_OFFER ya exige PERSUADE (tolerante), BRIBE y DECLINE
        self.wait('PERSUADE_CONFIRM',10)
        self.click('PERSUADE_CONFIRM',(814,750),'DECLINE_YES',(670,695,955,805))
        left=[False]  # la oferta pagada tiene que haberse cerrado antes de aceptar otra: nunca se paga dos veces
        def outcome(f):
            screen=self.vision.screen(f)
            if screen not in ('FAMILIAR_OFFER','PERSUADE_CONFIRM'):left[0]=True
            if screen=='FAMILIAR_OFFER':  # no se unió y el juego ofrece el siguiente
                other=self.offer_name(f)
                return (other!=name) if (name and other) else (left[0] and familiar_glyph(f) is not None)
            return screen in ('CAPTURE_SUCCESS','AUTO_ON_BATTLE','AUTO_OFF_BATTLE','LOADING','BATTLE_VICTORY','VICTORY','AUTO_ON','AUTO_OFF')
        frame=self.wait(outcome,20,'resultado de Persuade')
        captured=self.vision.screen(frame)=='CAPTURE_SUCCESS'
        if captured:self.click('CAPTURE_SUCCESS',(958,962),'CAPTURE_CLOSE',(780,890,1140,1040));loot.familiar(name)
        self.budget.finish_gold(action,effect_confirmed=True)
        atomic_json(path,{**intent,'effect_confirmed':True,'captured':captured})
        self.log.emit('FAMILIAR_PERSUADED',message=f'{name}: {"capturado" if captured else "no se unió"} · {cost} oro',
                      familiar=name,captured=captured,gold=cost)

    def decline_any(self,frame,attempt,offer,name):
        """Rechazar un objetivo cuando no se puede pagar (misma secuencia verificada que decline_other)."""
        saved=self.plan.get('targets'),self.plan.get('target')
        self.plan['targets']=[];self.plan['target']=''
        try:return self.decline_other(frame,attempt,offer)
        finally:self.plan['targets'],self.plan['target']=saved

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
                if self.targets and self.offer_name(frame) is None:
                    # La oferta entra animada: esperar el nombre legible; uno desconocido sigue pausando.
                    try:frame=self.wait(lambda f:self.offer_name(f) is not None,3,'nombre de familiar')
                    except SafetyStop:pass
                offer=f'{cycle}-{declined+1}';name=self.offer_name(frame)
                known=isinstance(name,str) and normalize(name) in {normalize(n) for n in self.targets}
                try:
                    if getattr(self,'persuade_all',False):self.persuade(frame,attempt,offer,name)  # Raid: cualquiera
                    elif not self.decline_other(frame,attempt,offer):
                        if not known:raise LookupError
                        self.persuade(frame,attempt,offer,name)
                except LookupError:
                    raise SafetyStop('Oferta de familiar desconocido: pausa para decidir; no se gasta oro ni gemas') from None
                except OfferChanged:
                    unknown_since=None;time.sleep(.3);continue  # nada pulsado: se lee la oferta nueva
                except SafetyStop:
                    # La oferta puede cerrarse sola antes de pulsar nada: sin intención escrita no hubo gasto.
                    sent=[p for p in (f'decline-{offer}',f'persuade-{offer}') if (self.channel.directory/f'{p}.intent.json').exists()]
                    if sent or self.vision.screen(self.capture())=='FAMILIAR_OFFER':raise
                    self.log.emit('FAMILIAR_OFFER_GONE',message='La oferta se cerró sola antes de decidir; se sigue');unknown_since=None;continue
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
                frame=self.wait('VICTORY');self.record_loot()
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
                if not self.budget.reserve_entry(following,resource=getattr(self,'entry_resource','ENERGY'),
                                                 balance=self.balance,cost=self.cost):
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
            elif screen in ('STORY_ZORUL','STORY'):
                signature=hash(frame[420:813,780:1590].tobytes())
                if signature not in story_sent:
                    if len(story_sent)>=30:raise SafetyStop('Demasiados diálogos de historia')
                    self.wait(screen);story_sent.add(signature)
                    self.click(screen,(1665,646),'STORY_ARROW',(1620,575,1720,720))
            elif screen not in ('AUTO_ON','AUTO_OFF','AUTO_ON_BATTLE','BATTLE_VICTORY','LOADING'):
                unknown_since=unknown_since or time.monotonic()
                if time.monotonic()-unknown_since>8:
                    cv2.imwrite(str(self.channel.directory/'unknown.png'),frame[100:915,320:1600])
                    raise SafetyStop('Pantalla/oferta/derrota no reconocida: pausa sin Persuade ni gasto')
            if screen in ('AUTO_ON','AUTO_ON_BATTLE','BATTLE_VICTORY','STORY_ZORUL','STORY','LOADING'):unknown_since=None
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
                if self.budget.energy_reserved+COSTS[self.difficulty]>self.plan['energy_limit']:
                    self.log.emit('DUNGEON_STATUS',message='Límite de energía alcanzado');return
                self.select_route()
                attempt=self.enter(cycle)
                if attempt is None:
                    self.go_home();self.log.emit('DUNGEON_STATUS',message=f'Energía agotada ({self.balance}) · detenido');return
            else:attempt=following
            following=self.observe(attempt,cycle,rerun=cycle<runs)
        self.log.emit('DUNGEON_STATUS',message='Límite de runs alcanzado · detenido',budget=self.budget.payload())


def run_dungeon():
    from .gamescope import backend
    LinuxIO,LinuxCapture=backend()
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
