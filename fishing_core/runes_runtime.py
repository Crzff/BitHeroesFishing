"""Runas de farmeo en los dos huecos laterales del tablero (runas menores).

Perfil -> tipo: CAPTURE Quindi, ITEM_FIND Vryn, GOLD Dar, XP Zyrk. Funciona con las runas
que tenga cada jugador: el tipo se reconoce por el símbolo y la rareza por el color
(común 5 ... mítica 25; Vryn 7,5 ... 37,5). Cada hueco se compara con lo mejor de la
lista de SWITCH (solo runas no equipadas, con scroll) y solo se cambia si mejora; el
resultado se comprueba en el tablero. BROWSE abre MELT y nunca se usa.
"""

import os
import time

from .control_flow import SafetyStop
from .dungeon_runtime import DungeonRunner
from .dungeon_vision import RARITIES,RUNE_VALUES

PROFILES={'CAPTURE':'QUINDI','ITEM_FIND':'VRYN','GOLD':'DAR','XP':'ZYRK'}
PROFILE=((90,1010),'HOME_QUEST',(15,15,165,190))
RUNES=((446,1014),'PROFILE_RUNES',(290,935,620,1080))
SLOTS=((700,596),(1216,596))
SWITCH=((958,570),'RUNE_SWITCH',(735,485,1190,655))
LIST_ROI=(620,380,1260,760)
LIST_WHEEL=(958,560)
LIST_CLOSE=(1344,304)
OPTIONS_CLOSE=(1276,244)  # cerrar la lista vuelve a OPTIONS, no al tablero
BOARD_CLOSE=(1522,182)
PROFILE_CLOSE=(1652,112)


class RunesRunner(DungeonRunner):
    def __init__(self,io,capture,vision,channel,log):
        self.io,self.cap,self.vision,self.channel,self.log=io,capture,vision,channel,log
        self.deadline=time.monotonic()+10*60

    def on(self,key,roi):
        return lambda f:self.vision.locate(f,key,roi) is not None

    def board(self):
        return self.wait(self.on('RUNES_TITLE',(760,90,1160,245)),10,'tablero de runas')

    def hover_kind(self,xy):
        """Tipo leído en el tooltip al pasar el ratón (el símbolo falla con las míticas rojas)."""
        end=time.monotonic()+3  # sin tooltip anterior en la imagen de referencia
        while self.vision.tooltip_visible(self.capture()) and time.monotonic()<end:time.sleep(.2)
        before=self.capture();self.check();self.io._move(tuple(int(n) for n in xy));time.sleep(1.2)
        after=self.capture();self.io._move((960,1070))
        # El tooltip se desvanece despacio y puede tapar el otro hueco: esperar a que desaparezca.
        end=time.monotonic()+3
        while self.vision.tooltip_visible(self.capture()) and time.monotonic()<end:time.sleep(.2)
        time.sleep(.3)
        return self.vision.tooltip_kind(before,after)

    def resolve(self,xy,symbol_kind,rarity):
        """(tipo, valor) confirmados; el símbolo solo sirve si el tooltip no se lee."""
        kind=self.hover_kind(xy) or symbol_kind
        return (kind,RUNE_VALUES[kind][RARITIES.index(rarity)]) if kind else (None,0)

    def slot_runes(self):
        """[(tipo, rareza, valor) o None] de los dos huecos. Ambos se leen de una sola captura sin tooltip
        (el tooltip de un hueco tapa el otro) y luego se confirma el tipo pasando el ratón."""
        self.board();time.sleep(1);history=[];end=time.monotonic()+6
        while True:  # el tablero entra animado (y desliza despacio): tres lecturas iguales o 6 s
            frame=self.capture()
            runes=[self.vision.rune(frame[y-90:y+90,x-90:x+90]) for x,y in SLOTS]
            history=(history+[runes])[-3:]
            if (len(history)==3 and history[0]==history[1]==history[2]) or time.monotonic()>end:break
            time.sleep(.4)
        out=[]
        for xy,rune in zip(SLOTS,runes):
            kind,value=self.resolve(xy,rune[0],rune[1]) if rune else (None,0)
            out.append((kind,rune[1],value) if kind else None)
        return out

    def visible(self):
        """Runas de la lista; vacía solo si sigue vacía 3 s (la lista entra animada)."""
        end=time.monotonic()+3
        while True:
            runes=self.vision.runes_in(self.capture(),LIST_ROI)
            if runes or time.monotonic()>end:return runes
            time.sleep(.4)

    def open_list(self,slot):
        self.board();self.check();self.io.click(SLOTS[slot]);time.sleep(.25);self.io._move((960,1070))
        frame=self.wait(self.on('RUNE_SWITCH',SWITCH[2]),10,'opciones de runa')
        self.click_on(frame,SWITCH)
        frame=self.wait(lambda f:self.vision.locate(f,'MINOR_RUNE',(720,210,1200,365)) is not None,10,'lista de runas menores')
        time.sleep(1.5)  # la lista sigue deslizándose aunque ya se vea el título
        return self.capture()

    def scroll(self,steps):
        self.wheel(steps,LIST_WHEEL);time.sleep(.5)

    def scan(self,kind):
        """Mejor runa del tipo en la lista: (valor, rareza, pasos de scroll, xy) o None."""
        self.scroll(-30);best=None;previous=None
        for step in range(12):
            visible=self.visible()
            for xy,k,rarity,_ in visible:
                real,value=self.resolve(xy,k,rarity)
                if real==kind and (best is None or value>best[0]):best=(value,rarity,step,tuple(int(n) for n in xy))
            signature=[(k,r) for _,k,r,_ in visible]
            if signature==previous:break
            previous=signature;self.scroll(2)
        return best

    def click_best(self,kind,best):
        """Vuelve a la posición de la mejor runa, confirma tipo y rareza y la pulsa."""
        value,rarity,step,xy=best;self.scroll(-30)
        for _ in range(step):self.scroll(2)
        for _ in range(2):  # un tooltip que tarda en salir no debe detener el bot: se confirma otra vez
            time.sleep(.5)
            here=[r for p,_,r,_ in self.visible() if abs(p[0]-xy[0])<20 and abs(p[1]-xy[1])<20]
            if here==[rarity] and self.hover_kind(xy)==kind:break
        else:return False
        self.check();self.io.click(xy);time.sleep(.25);self.io._move((960,1070))  # Unity procesa la suelta por frames
        self.log.emit('DUNGEON_INPUT',screen='MINOR_RUNE',xy=list(xy));return True

    def close_list(self):
        self.check();self.io.click(LIST_CLOSE)
        self.wait(self.on('RUNE_SWITCH',SWITCH[2]),10,'opciones de runa')
        self.check();self.io.click(OPTIONS_CLOSE);self.board()

    def click_on(self,frame,action):
        xy,key,roi=action
        if self.vision.locate(frame,key,roi) is None:raise SafetyStop(f'{key} no visible; no se pulsa')
        self.check();self.io.click(xy);self.log.emit('DUNGEON_INPUT',screen=key,xy=list(xy))

    def apply(self,profile):
        kind=PROFILES[profile];tried=set()
        for _ in range(2):  # cada hueco se revisa una vez, empezando por el peor
            current=self.slot_runes()
            values=[r[2] if r and r[0]==kind else 0 for r in current]
            slot=min((s for s in (0,1) if s not in tried),key=lambda s:values[s]);tried.add(slot)
            self.open_list(slot);best=self.scan(kind)
            if best is None or best[0]<=values[slot]:
                self.close_list();continue
            if not self.click_best(kind,best):raise SafetyStop('La runa elegida desapareció de la lista')
            self.wait(self.on('RUNES_TITLE',(760,90,1160,245)),6,'tablero tras elegir runa')
            time.sleep(1)  # el hueco cambia animado
            placed=self.slot_runes()[slot]
            if not placed or (placed[0],placed[2])!=(kind,best[0]):raise SafetyStop('La runa no quedó equipada; no se insiste')
            self.log.emit('RUNE_EQUIPPED',slot=slot,rune=f'{kind} {best[1]}',message=f'Hueco {slot+1}: {kind} {best[1]} ({best[0]}%)')
        return True

    def leave_runes(self):
        """Si el juego quedó en la lista de runas, sus opciones, el tablero o el perfil, vuelve a Home."""
        steps=((lambda f:self.vision.locate(f,'MINOR_RUNE',(720,210,1200,365)),LIST_CLOSE),
               (lambda f:self.vision.locate(f,'RUNE_SWITCH',SWITCH[2]),OPTIONS_CLOSE),
               (lambda f:self.vision.locate(f,'RUNES_TITLE',(760,90,1160,245)),BOARD_CLOSE),
               (lambda f:self.vision.locate(f,*RUNES[1:]),PROFILE_CLOSE))
        for _ in range(6):
            frame=self.capture();hit=next((xy for seen,xy in steps if seen(frame) is not None),None)
            if hit is None:return
            self.check();self.io.click(hit);time.sleep(.25);self.io._move((960,1070));time.sleep(1.5)

    def run(self,profile):
        self.leave_runes();self.ensure_home()
        self.click('HOME',*PROFILE[:2],PROFILE[2])
        self.click_on(self.wait(self.on(*RUNES[1:]),10,'perfil'),RUNES)
        self.apply(profile)
        self.check();self.io.click(BOARD_CLOSE);self.wait(self.on(*RUNES[1:]),10,'perfil')
        self.check();self.io.click(PROFILE_CLOSE);self.wait('HOME')
        self.log.emit('RUNES_STATUS',message=f'Runas de farmeo: {profile}')


def run_runes(profile):
    from .game_window import ENV_WINDOW,focus_window
    from .dungeon_vision import DungeonVision
    from .gamescope import backend
    LinuxIO,LinuxCapture=backend()
    from .processes import Mutex
    from .protocol import Channel
    from .telemetry import Telemetry,run_environment
    if profile not in PROFILES:raise ValueError('Perfil de runas desconocido')
    locks=[Mutex(role) for role in ('LAUNCHER','CONTROL','CATCH')];io=log=None
    try:
        env=run_environment();channel=Channel(env['FISHING_RUN_ID'])
        if os.environ.get('FARM_BACKEND')!='gamescope':os.environ[ENV_WINDOW]=focus_window('Steam').serialize()
        os.environ.pop('FARM_LAUNCHER_PID',None)
        log=Telemetry('RUNES',channel.run_id);io=LinuxIO();io.control_mode=True
        with LinuxCapture(io.game_guard) as capture:
            RunesRunner(io,capture,DungeonVision(),channel,log).run(profile)
    except (Exception,KeyboardInterrupt) as exc:
        if log:log.emit('SAFETY_STOP',message=str(exc) or 'F8',reason=str(exc) or 'F8',human=True)
        raise
    finally:
        if io:io.close()
        if log:log.close()
        for lock in reversed(locks):lock.close()


if __name__=='__main__':
    import sys
    run_runes(sys.argv[1])
