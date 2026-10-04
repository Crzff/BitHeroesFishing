"""Trials (evento semanal; esta semana Nyxn's Trials, dificultad 499): gasta todos los tokens.

Perder es normal en Trials: la derrota se cierra y se sigue. La dificultad se
comprueba y nunca se cambia; con menos de 5 tokens se baja el coste hasta 1.
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
DIFFICULTY=('TRIALS_DIFF_499',(1090,755,1400,895))


class TrialsRunner(DungeonRunner):
    defeat_continues=True

    def __init__(self,io,capture,vision,channel,log,runs):
        self.io,self.cap,self.vision,self.channel,self.log=io,capture,vision,channel,log
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
        if self.vision.locate(self.capture(),*DIFFICULTY) is None:
            raise SafetyStop('La dificultad de Trials no es 499; no se cambia')

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


def run_trials(runs):
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
            TrialsRunner(io,capture,DungeonVision(),channel,log,runs).run()
    except (Exception,KeyboardInterrupt) as exc:
        if log:log.emit('SAFETY_STOP',message=str(exc) or 'F8',reason=str(exc) or 'F8',human=True)
        raise
    finally:
        if io:io.close()
        if log:log.close()
        for lock in reversed(locks):lock.close()


if __name__=='__main__':
    import sys
    run_trials(int(sys.argv[1]))
