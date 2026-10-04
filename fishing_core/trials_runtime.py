"""Trials (evento semanal; esta semana Nyxn's Trials): gasta todos los tokens.

Perder es normal en Trials: la derrota se cierra y se sigue. La dificultad elegida
(máximo de un rango del menú, p. ej. 499 = T9 azul, objetos de set) se fija con el
desplegable y se confirma leyendo el campo; el coste baja de 5 hasta 1.
"""

import os
import time

import numpy as np

from .control_flow import SafetyStop
from .dungeon_runtime import DungeonRunner
from .farm_budget import FarmBudget
from .protocol import atomic_json

TOKEN_COST=5
HOME_TRIALS=((1830,710),'HOME_TRIALS',(1720,590,1920,830))
PLAY=((1280,580),'TRIALS_PLAY',(1120,450,1450,710))
CLOSE=((1490,236),'TRIALS_CLOSE',(1404,150,1584,330))
ACCEPT=((1215,982),'ACCEPT',(1000,930,1420,1035))
TOKENS_ROI=(880,88,1060,138)
DIFF_FIELD=(1130,800,1360,850)
DIFF_DROPDOWN=(1416,826)


class TrialsRunner(DungeonRunner):
    defeat_continues=True

    def __init__(self,io,capture,vision,channel,log,runs,difficulty=499):
        if type(difficulty) is not int or not 1<=difficulty<=9999:raise ValueError('Dificultad de Trials inválida')
        self.io,self.cap,self.vision,self.channel,self.log=io,capture,vision,channel,log
        self.trials_difficulty=difficulty
        self.runs=runs;self.deadline=time.monotonic()+60*60
        self.plan={'dungeon_id':'TRIALS','difficulty':'499','runs':runs,'energy_limit':runs*TOKEN_COST,'target':''}
        self.cost=TOKEN_COST;self.balance=None
        self.budget=FarmBudget(max_runs=runs,max_energy=runs*TOKEN_COST,max_seconds=60*60,max_gold=0,stop_on_defeat=False)

    def press(self,screen,action):
        xy,key,roi=action
        self.wait(lambda f:self.vision.screen(f)==screen and self.vision.locate(f,key,roi) is not None,10,f'{screen} · {key}')
        self.click(screen,xy,key,roi)

    def go_home(self):
        self.wait('TRIALS',20)  # TOWN vuelve a la ventana de Trials.

    def tokens(self):
        seen=None
        def known(frame):
            nonlocal seen
            current=None
            if self.vision.screen(frame)=='TRIALS':
                x,y,x1,y1=TOKENS_ROI;im=frame[y:y1,x:x1]
                current=self.vision.number(np.where(im.min(2,keepdims=True)>=240,im,0).astype(np.uint8))
            okay=current is not None and current==seen;seen=current
            return okay
        self.wait(known,30,'saldo de tokens')
        return seen

    def open(self):
        screen=self.vision.screen(self.wait(lambda f:self.vision.screen(f) in ('HOME','TRIALS'),12))
        if screen=='HOME':self.press('HOME',HOME_TRIALS);self.wait('TRIALS')
        self.set_difficulty()

    def difficulty_shown(self,frame):
        x,y,x1,y1=DIFF_FIELD;return self.vision.bright_number(frame[y:y1,x:x1])

    def wheel(self,steps):
        """Rueda del ratón sobre el menú (abajo si steps>0), comprobando foco antes de cada paso."""
        from Xlib import X
        from Xlib.ext import xtest
        self.io._move((930,600));display=self.io.game_guard.api.display
        for _ in range(abs(steps)):
            self.check();button=5 if steps>0 else 4
            xtest.fake_input(display,X.ButtonPress,button);xtest.fake_input(display,X.ButtonRelease,button)
            display.sync();time.sleep(.05)
        time.sleep(.6)

    def scroll_to(self,find,label):
        """Sube al inicio de la lista y baja hasta que find(frame) da una fila; None si no está."""
        time.sleep(1.2);self.wheel(-40);previous=None
        for _ in range(60):
            frame=self.capture();y=find(frame)
            if y is not None:return y
            rows=self.vision.menu_lines(frame);signature=[yy for yy,_ in rows],[line.tobytes() for _,line in rows]
            if signature==previous:return None  # final de la lista
            previous=signature;self.wheel(3)
        return None

    def choose(self,y,label):
        xy=(930,y);self.check();self.io.click(xy);time.sleep(.25);self.io._move((960,1070))
        self.log.emit('DUNGEON_INPUT',screen=label,xy=list(xy))

    def set_difficulty(self):
        """Dos menús: rango que contiene la dificultad y nivel exacto; se confirma leyendo el campo."""
        stable=lambda f:self.vision.screen(f)=='TRIALS' and self.difficulty_shown(f) is not None
        self.wait(stable,10,'dificultad de Trials');time.sleep(.5)
        target=self.trials_difficulty
        if self.difficulty_shown(self.capture())==target:return
        menu=lambda f:self.vision.locate(f,'WB_DIFF_MENU',(760,95,1160,240)) is not None
        self.click('TRIALS',DIFF_DROPDOWN);self.wait(menu,10,'menú de dificultad')
        y=self.scroll_to(lambda f:next((y for y,low,high in self.vision.trials_ranges(f) if low<=target<=high),None),'rango')
        if y is None:raise SafetyStop(f'La dificultad {target} no está en el menú; no se cambia')
        self.choose(y,'TRIALS_RANGE')
        self.wait(lambda f:menu(f) and bool(self.vision.trials_levels(f)),10,'niveles del rango')
        y=self.scroll_to(lambda f:next((y for y,n in self.vision.trials_levels(f) if n==target),None),'nivel')
        if y is None:raise SafetyStop(f'El nivel {target} no aparece en su rango; no se cambia')
        self.choose(y,'TRIALS_LEVEL')
        self.wait(lambda f:self.vision.screen(f)=='TRIALS' and self.difficulty_shown(f)==target,10,f'dificultad {target}')

    def enter(self,cycle):
        self.open();balance=self.tokens()
        if balance<1:return None
        # PLAY con coste mayor que el saldo ofrece comprar tokens: nunca.
        self.cost=self.set_cost('TRIALS',min(TOKEN_COST,balance),'COST_MENU_TOKENS')
        attempt=f'{self.channel.run_id}:{cycle}'
        if not self.budget.reserve_entry(attempt,resource='TOKENS',balance=balance,cost=self.cost):
            raise SafetyStop('Trial ya reservado; no repetir PLAY')
        atomic_json(self.channel.directory/f'trials-{cycle}.intent.json',{'attempt_id':attempt,'tokens':balance,'effect_confirmed':False})
        self.press('TRIALS',PLAY);self.press('TEAM',ACCEPT)
        self.log.emit('TRIALS_STARTED',attempt_id=attempt,tokens_before=balance,cost=self.cost)
        return attempt

    def run(self):
        for cycle in range(1,self.runs+1):
            attempt=self.enter(cycle)
            if attempt is None:break
            self.observe(attempt,cycle,auto_started=False)
        self.open();self.press('TRIALS',CLOSE);self.wait('HOME')
        self.log.emit('TRIALS_STATUS',message='Tokens gastados · detenido',budget=self.budget.payload())


def run_trials(runs,difficulty=499):
    from .game_window import ENV_WINDOW,focus_window
    from .dungeon_vision import DungeonVision
    from .linux import LinuxIO,LinuxCapture
    from .processes import Mutex
    from .protocol import Channel
    from .telemetry import Telemetry,run_environment
    if os.name=='nt':raise ValueError('Trials aún no certificado en Windows')
    locks=[Mutex(role) for role in ('LAUNCHER','CONTROL','CATCH')];io=log=None
    try:
        env=run_environment();channel=Channel(env['FISHING_RUN_ID'])
        os.environ[ENV_WINDOW]=focus_window('Steam').serialize();os.environ.pop('FARM_LAUNCHER_PID',None)
        log=Telemetry('TRIALS',channel.run_id);io=LinuxIO();io.control_mode=True
        with LinuxCapture(io.game_guard) as capture:
            TrialsRunner(io,capture,DungeonVision(),channel,log,runs,difficulty).run()
    except (Exception,KeyboardInterrupt) as exc:
        if log:log.emit('SAFETY_STOP',message=str(exc) or 'F8',reason=str(exc) or 'F8',human=True)
        raise
    finally:
        if io:io.close()
        if log:log.close()
        for lock in reversed(locks):lock.close()


if __name__=='__main__':
    import sys
    run_trials(int(sys.argv[1]),*[int(a) for a in sys.argv[2:3]])  # runs [dificultad]
