"""Runas de farmeo en los dos huecos laterales del tablero (runas menores).

Quest -> captura (Quindi); el resto -> Item Find (Vayn), según el jugador.
La lista de SWITCH solo muestra las runas NO equipadas: si una deseada aparece,
se pulsa; cuando ya no aparece ninguna, están equipadas. Si el jugador no tiene
la runa, nada se mueve. BROWSE abre MELT y nunca se usa.

Estado 2026-10-04: los clics se perdían por apartar el ratón al instante (Unity
procesa la suelta por frames); corregido, 3/3 cambios CAPTURE<->ITEM_FIND en vivo.
"""

import os
import time

from .control_flow import SafetyStop
from .dungeon_runtime import DungeonRunner

PROFILES={'CAPTURE':('RUNE_QUINDI_LEG','RUNE_QUINDI_EPIC'),
          'ITEM_FIND':('RUNE_VAYN_MYTHIC','RUNE_VAYN_LEG')}
PROFILE=((90,1010),'HOME_QUEST',(15,15,165,190))
RUNES=((446,1014),'PROFILE_RUNES',(290,935,620,1080))
SLOTS=((700,596),(1216,596))
SWITCH=((958,570),'RUNE_SWITCH',(735,485,1190,655))
LIST_CELLS=tuple((702+154*i,476) for i in range(3))
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

    def listed(self,frame,wanted):
        """Runas deseadas visibles en la lista (no equipadas): [(clave, celda)]."""
        return [(key,xy) for key in wanted for xy in LIST_CELLS
                if self.vision.locate(frame,key,(xy[0]-70,xy[1]-70,xy[0]+70,xy[1]+70)) is not None]

    def open_list(self,slot):
        self.board();self.check();self.io.click(SLOTS[slot])
        frame=self.wait(self.on('RUNE_SWITCH',SWITCH[2]),10,'opciones de runa')
        self.click_on(frame,SWITCH)
        # La lista entra animada: esperar el título y al menos un icono conocido estable.
        icons=[k for k in self.vision.templates if k.startswith('RUNE_') and k not in ('RUNE_OPTIONS','RUNE_SWITCH')]
        return self.wait(lambda f:self.vision.locate(f,'MINOR_RUNE',(720,210,1200,365)) is not None and
                         bool(self.listed(f,icons)),10,'lista de runas menores')

    def click_on(self,frame,action):
        xy,key,roi=action
        if self.vision.locate(frame,key,roi) is None:raise SafetyStop(f'{key} no visible; no se pulsa')
        self.check();self.io.click(xy);self.log.emit('DUNGEON_INPUT',screen=key,xy=list(xy))

    def apply(self,profile):
        wanted=PROFILES[profile]
        for attempt in range(3):
            changed=False
            for slot in (0,1):
                self.open_list(slot);time.sleep(1.5)  # la lista sigue asentándose aunque ya se vean los iconos
                found=self.listed(self.capture(),wanted)
                if found:
                    key,xy=found[0]
                    for _ in range(2):  # un clic durante la animación se pierde: un reintento como máximo
                        # Unity procesa la suelta por frames: no abandonar el botón al instante.
                        self.check();self.io.click(xy);time.sleep(.25);self.io._move((960,1070))  # el tooltip tapa el tablero
                        try:self.wait(self.on('RUNES_TITLE',(760,90,1160,245)),4,'tablero tras elegir runa');break
                        except SafetyStop:
                            if self.vision.locate(self.capture(),key,(xy[0]-70,xy[1]-70,xy[0]+70,xy[1]+70)) is None:raise
                    else:raise SafetyStop('La runa no se equipó; no se insiste')
                    changed=True;self.log.emit('RUNE_EQUIPPED',slot=slot,rune=key,message=f'Hueco {slot+1}: {key}')
                else:
                    self.check();self.io.click(LIST_CLOSE)
                    self.wait(self.on('RUNE_SWITCH',SWITCH[2]),10,'opciones de runa')
                    self.check();self.io.click(OPTIONS_CLOSE)
                self.board()
            if not changed:return True
        raise SafetyStop('Las runas no se estabilizan; revisar a mano')

    def run(self,profile):
        frame=self.wait(lambda f:self.vision.screen(f)=='HOME',12,'Home')
        self.click('HOME',*PROFILE[:2],PROFILE[2])
        self.click_on(self.wait(self.on(*RUNES[1:]),10,'perfil'),RUNES)
        self.apply(profile)
        self.check();self.io.click(BOARD_CLOSE);self.wait(self.on(*RUNES[1:]),10,'perfil')
        self.check();self.io.click(PROFILE_CLOSE);self.wait('HOME')
        self.log.emit('RUNES_STATUS',message=f'Runas de farmeo: {profile}')


def run_runes(profile):
    from .game_window import ENV_WINDOW,focus_window
    from .dungeon_vision import DungeonVision
    from .linux import LinuxIO,LinuxCapture
    from .processes import Mutex
    from .protocol import Channel
    from .telemetry import Telemetry,run_environment
    if profile not in PROFILES:raise ValueError('Perfil de runas desconocido')
    locks=[Mutex(role) for role in ('LAUNCHER','CONTROL','CATCH')];io=log=None
    try:
        env=run_environment();channel=Channel(env['FISHING_RUN_ID'])
        os.environ[ENV_WINDOW]=focus_window('Steam').serialize();os.environ.pop('FARM_LAUNCHER_PID',None)
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
