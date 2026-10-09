"""Clientes Chromium propios por cuenta, sin gamescope ni motores de farmeo.

Pensado para Windows: ventana 1920x1080 fuera de pantalla. En Linux con Wayland (niri) la posición se ignora y la
ventana se ajustaría al escritorio; ahí se sigue alojando el navegador en gamescope (brave.launch_brave) y se
controla igual por CDP (FARM_BACKEND=cdp).
"""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import queue
import threading
import uuid
import subprocess
import tempfile
import time

from .accounts import brave_target,prepare_profiles,browser_accounts
from .brave import CHROMIUM_NAMES,browser_identity,prepare_brave,require_closed_profile
from .telemetry import ROOT


def detect_browser(executable=None):
    if executable is not None:
        binary=Path(executable).resolve(strict=True)
        if binary.name.lower() not in CHROMIUM_NAMES or not binary.is_file():
            raise ValueError('Ejecutable Chromium no admitido')
        return str(binary)
    if os.name=='nt':
        relatives=('BraveSoftware/Brave-Browser/Application/brave.exe',
                   'Google/Chrome/Application/chrome.exe','Chromium/Application/chrome.exe',
                   'Microsoft/Edge/Application/msedge.exe')
        for name in ('PROGRAMFILES','PROGRAMFILES(X86)','LOCALAPPDATA'):
            base=os.environ.get(name)
            if not base:continue
            for relative in relatives:
                path=Path(base)/relative
                if path.is_file():return str(path.resolve())
    else:
        for name in CHROMIUM_NAMES:
            if name.endswith('.exe'):continue
            path=shutil.which(name)
            if path:return path
    raise ValueError('No se encuentra Brave, Chrome, Chromium o Edge')


@contextmanager
def _exclusive(path):
    # Lock transitorio: si queda tras un fallo, detenerse y pedir revisión manual.
    fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    try:yield
    finally:
        os.close(fd);path.unlink()


def launch_browser(account,executable=None,visible=False):
    if account not in browser_accounts():raise ValueError('Se requiere una cuenta de navegador')
    binary=detect_browser(executable);profile=prepare_profiles(ROOT)[account]
    process=None
    with _exclusive(profile.parent/'browser-launch.lock'):
        require_closed_profile(profile)
        node=shutil.which('node')
        if node is None:raise RuntimeError('CDP requiere Node')
        requested=ROOT/'runs'/('cdp-'+uuid.uuid4().hex)/'cdp.sock'
        flags=[f'--user-data-dir={profile}','--window-size=1920,1080',
               '--force-device-scale-factor=1','--disable-background-timer-throttling',
               '--disable-backgrounding-occluded-windows','--disable-renderer-backgrounding',
               '--no-first-run','--no-default-browser-check']
        if not visible:flags.append('--window-position=-2400,0')
        else:flags.append('--window-position=0,0')
        # prepare_brave crea la página de juego; no restaurar una ventana anterior.
        if not visible:flags.append('--no-startup-window')
        previous={key:os.environ.get(key) for key in ('FARM_ACCOUNT','FARM_BACKEND')}
        try:
            os.environ.update(FARM_ACCOUNT=account,FARM_BACKEND='cdp')
            process=subprocess.Popen([node,str(Path(__file__).with_name('cdp_broker.mjs')),str(requested),binary,*flags],
                cwd=str(ROOT),env={'PATH':os.defpath,'LANG':'C.UTF-8'},stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,start_new_session=True)
            replies=queue.Queue()
            def read_reply():
                try:replies.put(process.stdout.readline(1025))
                except OSError:replies.put(b'')
            threading.Thread(target=read_reply,daemon=True).start()
            try:raw=replies.get(timeout=30)
            except queue.Empty:raise RuntimeError('El intermediario CDP no respondió') from None
            try:
                reply=json.loads(raw)
                if len(raw)>1024 or not raw.endswith(b'\n') or type(reply) is not dict or set(reply)!={'ok','pid','endpoint'} or reply['ok'] is not True or \
                        type(reply['pid']) is not int or not 0<reply['pid']<2**31 or type(reply['endpoint']) is not str:raise ValueError
                pid=reply['pid'];endpoint=reply['endpoint']
                if os.name!='nt' and endpoint!=str(requested):raise ValueError
            except (ValueError,TypeError):raise RuntimeError('Respuesta del intermediario CDP inválida') from None
            end=time.monotonic()+30
            while True:
                if process.poll() is not None:raise RuntimeError('El navegador terminó antes de preparar CDP')
                try:
                    identity=browser_identity(pid,endpoint,account)
                    break
                except RuntimeError:
                    if time.monotonic()>=end:raise
                    time.sleep(.1)
            if identity[2]!=process.pid:raise RuntimeError('El navegador no es hijo del intermediario propio')
            target=prepare_brave(pid,endpoint)
            if process.poll() is not None:raise RuntimeError('El navegador terminó durante la preparación')
            if browser_identity(pid,endpoint,account)!=identity:raise RuntimeError('Cambió el navegador durante la preparación')
            process.stdout.close()
            return process,{'FARM_BRAVE_PID':str(pid),'FARM_BRAVE_CDP_ENDPOINT':endpoint,
                           'FARM_BRAVE_TARGET_ID':target,'FARM_BACKEND':'cdp'}
        except BaseException:
            if process is not None and process.poll() is None:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=2)
            if process is not None and process.stdout is not None:process.stdout.close()
            raise
        finally:
            for key,value in previous.items():
                if value is None:os.environ.pop(key,None)
                else:os.environ[key]=value


def write_session(account,session):
    transport='FARM_BRAVE_CDP_ENDPOINT' if 'FARM_BRAVE_CDP_ENDPOINT' in session else 'FARM_BRAVE_CDP_PORT'
    if account not in browser_accounts() or set(session)!={'FARM_BRAVE_PID',transport,
            'FARM_BRAVE_TARGET_ID','FARM_BACKEND'} or session['FARM_BACKEND']!='cdp':
        raise ValueError('Sesión CDP inválida')
    brave_target({**session,'FARM_ACCOUNT':account})
    prepare_profiles(ROOT)
    path=ROOT/'runs/accounts/sessions.json';temporary=None
    with _exclusive(path.with_suffix('.lock')):
        if path.is_symlink():raise ValueError('No se escriben sesiones a través de enlaces')
        records=json.loads(path.read_text()) if path.exists() else {}
        if not isinstance(records,dict):raise ValueError('Registro de sesiones inválido')
        records[account]=dict(session)
        try:
            fd,temporary=tempfile.mkstemp(prefix='.sessions-',dir=path.parent)
            with os.fdopen(fd,'w',encoding='utf-8') as stream:
                os.chmod(temporary,0o600)
                json.dump(records,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
            os.replace(temporary,path);temporary=None
        finally:
            if temporary is not None:Path(temporary).unlink()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('account',choices=browser_accounts())
    parser.add_argument('--visible',action='store_true')
    parser.add_argument('--browser')
    args=parser.parse_args(argv)
    process,session=launch_browser(args.account,args.browser,args.visible)
    write_session(args.account,session)
    return 0


if __name__=='__main__':raise SystemExit(main())
