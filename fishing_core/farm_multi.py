"""Supervisor de una prueba limitada. No descubre, prepara ni abre clientes."""
import json
import os
import signal
import subprocess
import sys
import time
import threading

from .accounts import account_names,account_id,brave_target,gamescope_target,steam_account
from .gamescope import require_calibrated_client
from .processes import Mutex,close_children
from .telemetry import ROOT
from .protocol import atomic_json
from .retention import prune_runs


class Heartbeat:
    def __init__(self):
        self.last=time.monotonic();self.stage=0;self.deadline=None

    def progress(self):
        if not self.stage:self.last=time.monotonic()

    def check(self,worker,now=None):
        now=time.monotonic() if now is None else now
        if self.stage>=3:return True
        if now < (self.deadline if self.stage else self.last+45*60):return bool(self.stage)
        try:
            if os.name=='nt' and self.stage:
                worker.terminate() if self.stage==1 else worker.kill()
            else:worker.send_signal((signal.SIGINT,signal.SIGTERM,getattr(signal,'SIGKILL',signal.SIGTERM))[self.stage])
        except OSError:pass
        self.stage+=1;self.deadline=now+30
        return True

MULTI_STATUS=ROOT/'runs/accounts/multi_status.json'

DISPLAY_KEYS={'FARM_GAMESCOPE_DISPLAY','FARM_GAMESCOPE_SERIAL'}
BRAVE_KEYS={'FARM_BRAVE_PID','FARM_BRAVE_CDP_PORT','FARM_BRAVE_TARGET_ID','FARM_BRAVE_CDP_ENDPOINT'}


def trial_environments(sessions,farm=False):
    """Datos explícitos por cuenta; no mutar os.environ ni heredar otra identidad."""
    if type(sessions) is not dict or not sessions or not set(sessions)<=set(account_names()) or (not farm and set(sessions)!=set(account_names())):
        raise ValueError('El farmeo requiere al menos una cuenta conocida' if farm else 'La prueba requiere todas las cuentas del registro')
    base={k:v for k,v in os.environ.items() if k not in DISPLAY_KEYS|BRAVE_KEYS|
          {'FARM_ACCOUNT','FARM_LAUNCHER_PID','FARM_SUPERVISOR_PID','FISHING_GAME_WINDOW','FISHING_RUN_ID'}}
    envs={};seen={key:set() for key in DISPLAY_KEYS|BRAVE_KEYS}
    for account in sessions:
        record=sessions[account];keys=DISPLAY_KEYS if account==steam_account() else DISPLAY_KEYS|BRAVE_KEYS
        cdp=farm and account!=steam_account() and type(record) is dict and record.get('FARM_BACKEND')=='cdp'
        if cdp:keys=BRAVE_KEYS|{'FARM_BACKEND'}
        if type(record) is dict:keys=keys-({'FARM_BRAVE_CDP_PORT'} if 'FARM_BRAVE_CDP_ENDPOINT' in record else {'FARM_BRAVE_CDP_ENDPOINT'})
        if type(record) is not dict or set(record)!=keys or any(type(v) is not str for v in record.values()):
            raise ValueError('Endpoints incompletos o campos no permitidos en la prueba')
        env={**base,**record,'FARM_ACCOUNT':account,'FARM_BACKEND':'cdp' if cdp else 'gamescope','FARM_SUPERVISOR_PID':str(os.getpid())}
        identity={};web=brave_target(env)
        if not cdp:
            display,serial=gamescope_target(env)
            identity={'FARM_GAMESCOPE_DISPLAY':str(int(display[1:].split('.')[0])),'FARM_GAMESCOPE_SERIAL':serial}
        if web:identity.update(zip(('FARM_BRAVE_PID','FARM_BRAVE_CDP_ENDPOINT' if isinstance(web[1],str) else 'FARM_BRAVE_CDP_PORT','FARM_BRAVE_TARGET_ID'),(web[0],web[1],web[2].upper())))
        for key,value in identity.items():
            if value in seen[key]:raise ValueError('Dos cuentas comparten un endpoint; no se inicia la prueba')
            seen[key].add(value)
        envs[account]=env
    return envs


def validate_trial(sessions,read_only=False):
    envs=trial_environments(sessions)
    if account_id() is not None:raise ValueError('El supervisor no debe fijarse a una sola cuenta')
    for env in envs.values():
        if read_only:require_calibrated_client(env,read_only=True);continue
        env['FARM_SINGLE_DUNGEON']='1'  # el worker solo admite 1 run Normal, 10 energía, cero oro
        require_calibrated_client(env)  # Brave vivo con su perfil y puerto, antes de ningún worker
    return envs


def start_trial(sessions,read_only=False):
    """Entrada del panel: opt-in y preflight, sin escribir preferencias ni endpoints."""
    validate_trial(sessions,read_only)
    args=[sys.executable,'-B','-u','-m','fishing_core.farm_multi']+(['--stop-check'] if read_only else [])
    process=subprocess.Popen(args,cwd=str(ROOT),
                             stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    try:
        process.stdin.write(json.dumps(sessions));process.stdin.close()
    except BaseException:
        try:process.send_signal(signal.SIGINT)
        except OSError:pass
        try:close_children([process])
        finally:process.stdin.close();process.stdout.close()
        raise
    return process


def run_trial(sessions,read_only=False):
    prune_runs(ROOT)
    envs=validate_trial(sessions,read_only)
    lock=Mutex('MULTI_SUPERVISOR');workers=[];pending={};results={}
    try:
        for account,env in envs.items():
            worker=subprocess.Popen([sys.executable,'-B','-u','-m','fishing_core.farm_all','--stop-check' if read_only else '--single-dungeon'],
                                    cwd=str(ROOT),env=env,stdin=subprocess.DEVNULL,start_new_session=True)
            workers.append(worker);pending[account]=worker
        while pending:
            for account,worker in list(pending.items()):
                code=worker.poll()
                if code is None:continue
                results[account]=code;del pending[account]
                print(f'{account_names()[account]}: '+('OK (prueba limitada)' if code==0 else f'PARADO (código {code})'),flush=True)
                if code:raise RuntimeError(f'Falló la prueba de {account_names()[account]}; se detienen las demás cuentas')
            if pending:time.sleep(.05)
        return results
    finally:
        try:
            for worker in workers:
                if worker.poll() is None:
                    try:worker.send_signal(signal.SIGINT)
                    except OSError:pass  # Puede haber salido; aun así limpiar todos los hijos propios.
            close_children(workers)
        finally:lock.close()


def validate_farm(sessions):
    """Farmeo completo: cada cuenta con su configuración; Brave vivo y propio antes de arrancar ninguna."""
    envs=trial_environments(sessions,farm=True)
    if account_id() is not None:raise ValueError('El supervisor no debe fijarse a una sola cuenta')
    for env in envs.values():
        env['FARM_MULTI_FARM']='1'
        require_calibrated_client(env)
    return envs


def start_farm(sessions):
    """Entrada del panel: lanza el supervisor de farmeo y le pasa los endpoints por stdin."""
    validate_farm(sessions)
    process=subprocess.Popen([sys.executable,'-B','-u','-m','fishing_core.farm_multi','--farm'],cwd=str(ROOT),
                             stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    try:process.stdin.write(json.dumps(sessions));process.stdin.close()
    except BaseException:
        try:process.send_signal(signal.SIGINT)
        except OSError:pass
        close_children([process]);raise
    return process


def run_farm(sessions):
    """Las cuentas recibidas a la vez: una parada de una cuenta no detiene a las demás.
    STOP (SIGINT al supervisor) detiene todos los motores propios."""
    prune_runs(ROOT)
    envs=validate_farm(sessions)
    lock=Mutex('MULTI_SUPERVISOR');workers={};results={}
    status={'supervisor_pid':os.getpid(),'started':time.time(),'accounts':{
        a:{'name':account_names()[a],'step':'Iniciando','state':'EN MARCHA','detail':'','updated':time.time()} for a in envs}}
    status_lock=threading.Lock()
    def update(account=None,**values):
        with status_lock:
            if account and 'state' not in values and status['accounts'][account]['state']!='EN MARCHA':return
            if account:status['accounts'][account].update(values,updated=time.time())
            try:
                MULTI_STATUS.parent.mkdir(parents=True,exist_ok=True);atomic_json(MULTI_STATUS,status)
            except Exception:pass  # La telemetría nunca debe detener los workers.
    try:
        update()
        for account,env in envs.items():
            workers[account]=subprocess.Popen([sys.executable,'-B','-u','-m','fishing_core.farm_all'],cwd=str(ROOT),env=env,
                                              stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                              text=True,start_new_session=True)
        heartbeats={a:Heartbeat() for a in workers}
        def relay(account,worker):  # "== Modo" y "Modo: resultado" de cada cuenta, con su nombre delante
            for line in worker.stdout:
                heartbeats[account].progress()
                line=line.rstrip()
                if line.startswith('== '):update(account,step=line[3:].split(' (')[0],detail=line[3:])
                elif ': ' in line:
                    detail=line.split(': ',1)[1]
                    try:detail=json.loads(detail).get('reason',detail)  # paradas del motor: JSON con 'reason'
                    except (ValueError,AttributeError):pass
                    update(account,detail=str(detail))
                if line:print(f'[{account_names()[account]}] {line}',flush=True)
        threads=[threading.Thread(target=relay,args=item,daemon=True) for item in workers.items()]
        for thread in threads:thread.start()
        pending=dict(workers)
        while pending:
            for account,worker in list(pending.items()):
                code=worker.poll()
                if code is None:
                    if heartbeats[account].check(worker):update(account,state='PARADO',detail='sin progreso')
                    continue
                results[account]=code;del pending[account]
                threads[list(workers).index(account)].join(timeout=2)
                update(account,state='PARADO' if heartbeats[account].stage else ('TERMINADO' if code==0 else 'PARADO'),
                       detail=status['accounts'][account]['detail'] or ('TERMINADO' if code==0 else f'Código {code}'))
                print(f'{account_names()[account]}: '+('PARADO (sin progreso)' if heartbeats[account].stage else
                      ('TERMINADO' if code==0 else f'PARADO (código {code})')),flush=True)
            if pending:time.sleep(.1)
        for thread in threads:thread.join(timeout=2)
        return results
    finally:
        for account in envs:
            if status['accounts'][account]['state']=='EN MARCHA':update(account,state='PARADO',detail='STOP')
        try:
            for worker in workers.values():
                if worker.poll() is None:
                    try:worker.send_signal(signal.SIGINT)
                    except OSError:pass
            close_children(list(workers.values()))
        finally:lock.close()


def read_sessions():
    text=sys.stdin.read(8193)
    if len(text)>8192:raise ValueError('Payload de endpoints demasiado grande')
    try:sessions=json.loads(text)
    except (ValueError,RecursionError):raise ValueError('JSON de endpoints inválido') from None
    if type(sessions) is not dict:raise ValueError('JSON de endpoints inválido')
    return sessions


def main(argv):
    if argv not in ([],['--stop-check'],['--farm']):raise ValueError('Argumentos del supervisor inválidos')
    if argv==['--farm']:run_farm(read_sessions())
    elif argv:run_trial(read_sessions(),read_only=True)
    else:run_trial(read_sessions())


if __name__=='__main__':
    try:main(sys.argv[1:])
    except KeyboardInterrupt:raise SystemExit(130)
    except (ValueError,RuntimeError,OSError):raise SystemExit('PARADO: no se pudo completar la prueba multicuenta')
