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

    def slot_rune(self,slot):
        """Runa del hueco; las runas del tablero entran animadas: dos lecturas iguales o 3 s."""
        x,y=SLOTS[slot];self.board();previous=object();end=time.monotonic()+3
        while True:
            frame=self.capture();rune=self.vision.rune(frame[y-90:y+90,x-90:x+90])
            if rune==previous or time.monotonic()>end:return rune
            previous=rune;time.sleep(.4)

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

    def wheel(self,steps):
        if hasattr(self.io,'wheel'):self.io.wheel(steps,LIST_WHEEL)
        else:
            from Xlib import X
            from Xlib.ext import xtest
            self.io._move(LIST_WHEEL);display=self.io.game_guard.api.display
            for _ in range(abs(steps)):
                self.check();button=5 if steps>0 else 4
                xtest.fake_input(display,X.ButtonPress,button);xtest.fake_input(display,X.ButtonRelease,button);display.sync();time.sleep(.05)
        self.io._move((960,1070));time.sleep(.6)

    def scan(self,kind):
        """Mejor runa del tipo en la lista: (valor, rareza) recorriendo con scroll; None si no hay."""
        self.wheel(-30);best=None;previous=None
        for _ in range(12):
            visible=self.visible()
            for xy,k,rarity,value in visible:
                if k==kind and (best is None or value>best[0]):best=(value,rarity)
            signature=[(k,r) for _,k,r,_ in visible]
            if signature==previous:break
            previous=signature;self.wheel(2)
        return best

    def find_and_click(self,kind,rarity):
        """Vuelve arriba y baja hasta ver esa runa; la pulsa. False si no aparece."""
        self.wheel(-30);previous=None
        for _ in range(12):
            visible=self.visible()
            match=[xy for xy,k,r,_ in visible if k==kind and r==rarity]
            if match:
                xy=tuple(int(n) for n in match[0])
                self.check();self.io.click(xy);time.sleep(.25);self.io._move((960,1070))  # Unity procesa la suelta por frames
                self.log.emit('DUNGEON_INPUT',screen='MINOR_RUNE',xy=list(xy));return True
            signature=[(k,r) for _,k,r,_ in visible]
            if signature==previous:return False
            previous=signature;self.wheel(2)
        return False

    def close_list(self):
        self.check();self.io.click(LIST_CLOSE)
        self.wait(self.on('RUNE_SWITCH',SWITCH[2]),10,'opciones de runa')
        self.check();self.io.click(OPTIONS_CLOSE);self.board()

    def click_on(self,frame,action):
        xy,key,roi=action
        if self.vision.locate(frame,key,roi) is None:raise SafetyStop(f'{key} no visible; no se pulsa')
        self.check();self.io.click(xy);self.log.emit('DUNGEON_INPUT',screen=key,xy=list(xy))

    def apply(self,profile):
        kind=PROFILES[profile]
        for _ in range(4):  # cada vuelta mejora como mucho un hueco
            current=[self.slot_rune(slot) for slot in (0,1)]
            values=[r[2] if r and r[0]==kind else 0 for r in current]
            slot=values.index(min(values))
            self.open_list(slot);best=self.scan(kind)
            if best is None or best[0]<=values[slot]:
                self.close_list()
                other=1-slot  # el otro hueco ya es igual o mejor: probar si aún mejora
                if values[other]>=values[slot]:return True
                continue
            if not self.find_and_click(kind,best[1]):raise SafetyStop('La runa elegida desapareció de la lista')
            self.wait(self.on('RUNES_TITLE',(760,90,1160,245)),6,'tablero tras elegir runa')
            end=time.monotonic()+4;x,y=SLOTS[slot]
            while (self.vision.rune(self.capture()[y-90:y+90,x-90:x+90]) or (None,None,None))[::2]!=(kind,best[0]):
                if time.monotonic()>end:raise SafetyStop('La runa no quedó equipada; no se insiste')
                time.sleep(.4)
            self.log.emit('RUNE_EQUIPPED',slot=slot,rune=f'{kind} {best[1]}',message=f'Hueco {slot+1}: {kind} {best[1]} ({best[0]}%)')
        return True

    def run(self,profile):
        self.ensure_home()
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
