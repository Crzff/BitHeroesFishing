"""Guarda del Brave exclusivo del bot. Importar no conecta ni lee perfiles."""
import json
import os
from pathlib import Path
import re
import select
import shlex
import shutil
import subprocess
import time

from .telemetry import ROOT
from .accounts import account_id,brave_target,gamescope_target

_PREPARE_STAGES={'connection':'conexión CDP','blank':'ventana vacía','play':'Play',
    'fullscreen':'Fullscreen','canvas':'canvas','snapshot':'geometría web final'}


def _flag(argv,name):
    values=[]
    for i,arg in enumerate(argv):
        if arg.startswith(name+'='):values.append(arg[len(name)+1:])
        elif arg==name:values.append(argv[i+1] if i+1<len(argv) else None)
    return values[0] if len(values)==1 else None


def browser_identity(pid,port,account,proc=Path('/proc')):
    """Solo metadatos del proceso aprobado; no cookies, storage ni archivos del perfil."""
    try:
        if type(pid) is not int or not 0<pid<2**31 or type(port) is not int or not 0<port<65536 or \
                account not in ('personal','perfil-1'):raise ValueError
        p=proc/str(pid)
        if p.stat().st_uid!=os.getuid():raise ValueError
        exe=(p/'exe').resolve(strict=True)
        if exe.name not in ('brave','brave-browser'):raise ValueError
        stamp=(p/'stat').read_text().rsplit(') ',1)[1].split()[19]
        if not stamp.isdecimal() or int(stamp)<=0:raise ValueError
        with (p/'cmdline').open('rb') as stream:raw=stream.read(65537)
        if len(raw)>65536 or not raw.endswith(b'\0'):raise ValueError
        argv=[os.fsdecode(a) for a in raw[:-1].split(b'\0')]
        if len(argv)==1:argv=shlex.split(argv[0])  # Brave expone su título de proceso aplanado en Linux.
        if _flag(argv,'--user-data-dir')!=str(ROOT/'runs/accounts'/account/'brave-data') or \
                _flag(argv,'--remote-debugging-port') not in ('0',str(port)):raise ValueError
        sockets=set()
        for fd in (p/'fd').iterdir():
            try:match=re.fullmatch(r'socket:\[([0-9]+)\]',os.readlink(fd))
            except OSError:continue  # Un descriptor que acaba de cerrarse no prueba el puerto.
            if match:sockets.add(match[1])
        with (p/'net/tcp').open() as stream:tcp=stream.read(262145)
        if len(tcp)>262144:raise ValueError
        for line in tcp.splitlines()[1:]:
            fields=line.split()
            if len(fields)>9 and fields[1]==f'0100007F:{port:04X}' and fields[3]=='0A' and fields[9] in sockets:
                return str(exe),stamp
        raise ValueError
    except (OSError,ValueError,IndexError):
        raise RuntimeError('No se confirma el proceso, perfil o puerto CDP propio de Brave') from None


def _close_adapter(process):
    if process is None:return
    try:
        process.stdin.close()  # EOF cancela la preparación o limpia Escape, nunca Browser.close.
        try:process.wait(timeout=4)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:process.wait(timeout=1)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=1)
    finally:process.stdout.close()


def prepare_brave(pid,port):
    """Preparación explícita de un Brave propio ya abierto, sin lanzar clientes ni motores.

    El llamador debe confirmar exclusividad de la cuenta y arrancar sin ventana.
    Prepara Play/Fullscreen y geometría web; devuelve el target nuevo sin habilitar farmeo.
    La ventana X, la captura, Home y el personaje todavía requieren validación posterior.
    """
    process=pidfd=None
    failure='No se confirmó la preparación del Brave propio; no se habilita farmeo'
    try:
        account=account_id();node=shutil.which('node')
        if account not in ('personal','perfil-1') or node is None or type(pid) is not int or not 0<pid<2**31 or \
                type(port) is not int or not 0<port<65536:raise ValueError
        pidfd=os.pidfd_open(pid);identity=browser_identity(pid,port,account)
        if select.select([pidfd],[],[],0)[0]:raise ValueError
        process=subprocess.Popen([node,str(Path(__file__).with_name('brave_cdp.mjs')),str(port),'--prepare'],
            cwd=str(ROOT),env={'PATH':os.defpath,'LANG':'C.UTF-8'},stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,bufsize=0,start_new_session=True)
        end=time.monotonic()+90;buffer=b''
        while b'\n' not in buffer:
            remaining=end-time.monotonic()
            if remaining<=0:raise ValueError
            ready=select.select([pidfd,process.stdout],[],[],remaining)[0]
            if pidfd in ready or not ready:raise ValueError
            chunk=os.read(process.stdout.fileno(),1025)
            if not chunk or len(buffer)+len(chunk)>1024:raise ValueError
            buffer+=chunk
        line,tail=buffer.split(b'\n',1);reply=json.loads(line)
        if not tail and isinstance(reply,dict) and set(reply)=={'id','ok','stage'} and \
                type(reply['id']) is int and reply['id']==0 and reply['ok'] is False:
            if isinstance(reply['stage'],str) and reply['stage'] in _PREPARE_STAGES:
                failure+=f" (etapa: {_PREPARE_STAGES[reply['stage']]})"
            raise ValueError
        if tail or not isinstance(reply,dict) or set(reply)!={'id','ok','target'} or type(reply['id']) is not int or \
                reply['id']!=0 or reply['ok'] is not True or not isinstance(reply['target'],str) or \
                not re.fullmatch(r'[0-9a-fA-F]{32}',reply['target']) or account_id()!=account or \
                select.select([pidfd],[],[],0)[0] or browser_identity(pid,port,account)!=identity:raise ValueError
        process.stdin.close();process.wait(timeout=4)
        if process.returncode!=0:raise ValueError
        return reply['target']
    except (OSError,ValueError,TypeError,RuntimeError,subprocess.SubprocessError):
        raise RuntimeError(failure) from None
    finally:
        try:_close_adapter(process)
        finally:
            if pidfd is not None:os.close(pidfd)


def require_closed_profile(profile,proc=Path('/proc')):
    """Solo metadatos de procesos: nunca leer archivos del perfil ni cerrar un cliente existente."""
    for p in proc.iterdir():
        if not p.name.isdecimal():continue
        try:
            if p.stat().st_uid!=os.getuid():continue
            try:exe=(p/'exe').readlink().name.removesuffix(' (deleted)')
            except PermissionError:  # p. ej. systemd --user: exe ilegible; comm siempre se lee
                if not any(n in (p/'comm').read_text() for n in ('brave','chrom')):continue
                raise
            if exe not in ('brave','brave-browser'):continue
            with (p/'cmdline').open('rb') as stream:raw=stream.read(65537)
            if len(raw)>65536 or not raw.endswith(b'\0'):raise ValueError
            argv=[os.fsdecode(a) for a in raw[:-1].split(b'\0')]
            if len(argv)==1:argv=shlex.split(argv[0])
            if str(profile) in '\0'.join(argv):
                raise RuntimeError('El perfil Brave ya está abierto; no se inicia otro cliente')
        except (FileNotFoundError,ProcessLookupError):continue  # El proceso desapareció durante la consulta.
        except (OSError,ValueError):
            raise RuntimeError('No se confirma cerrado el perfil Brave; no se inicia otro cliente') from None


def gamescope_launch_serial(pid):
    """Descubrir únicamente el vídeo del gamescope que acaba de crear este lanzador."""
    out=subprocess.run(['pw-dump'],capture_output=True,text=True,timeout=10)
    if out.returncode or len(out.stdout)>4_194_304:raise RuntimeError('No se confirma PipeWire del cliente nuevo')
    try:
        records=json.loads(out.stdout)
        clients={r['id']:r.get('info',{}).get('props',{}) for r in records if r.get('type')=='PipeWire:Interface:Client'}
        serials=[]
        for record in records:
            p=record.get('info',{}).get('props',{})
            if p.get('node.name')=='gamescope' and p.get('media.class')=='Video/Source' and \
                    str(clients.get(p.get('client.id'),{}).get('application.process.id'))==str(pid):
                serial=str(p.get('object.serial',''))
                if not re.fullmatch(r'[1-9][0-9]{0,19}',serial) or int(serial)>2**64-1:raise ValueError
                serials.append(serial)
        if len(serials)!=1:raise ValueError
        return serials[0]
    except (ValueError,TypeError,KeyError,AttributeError):
        raise RuntimeError('Vídeo del gamescope nuevo ausente o ambiguo; no usar otra sesión') from None


def launch_brave(executable=None):
    """Opt-in desde perfil cerrado: gamescope nuevo y preparación web, sin farmeo ni preferencias."""
    import socket,sys,tempfile
    from .accounts import prepare_profiles
    from .processes import Mutex
    account=account_id()
    if account not in ('personal','perfil-1') or os.environ.get('FARM_BACKEND')!='gamescope':
        raise ValueError('Lanzamiento requiere una cuenta Brave explícita y gamescope')
    binary=Path(executable or shutil.which('brave') or '').resolve(strict=True)
    if binary.name not in ('brave','brave-browser') or not binary.is_file():raise ValueError('Ejecutable Brave no confirmado')
    lock=Mutex('BRAVE_CLIENT');process=None;bootstrap=None
    try:
        profile=prepare_profiles(ROOT)[account];require_closed_profile(profile)
        with socket.socket() as reserve:reserve.bind(('127.0.0.1',0));port=reserve.getsockname()[1]
        bootstrap=tempfile.TemporaryDirectory(prefix='brave-launch-',dir=ROOT/'runs');endpoint=Path(bootstrap.name)/'endpoint.json'
        # gamescopereaper cierra descriptores adicionales: publicar solo PID/display en una carpeta privada.
        child="import json,os,sys;p=sys.argv[1];fd=os.open(p+'.partial',os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600);os.write(fd,(json.dumps({'pid':os.getpid(),'display':os.environ['DISPLAY']})+'\\n').encode());os.close(fd);os.rename(p+'.partial',p);os.execv(sys.argv[2],sys.argv[2:])"
        flags=[f'--user-data-dir={profile}',f'--remote-debugging-port={port}','--remote-debugging-address=127.0.0.1',
               '--ozone-platform=x11','--force-device-scale-factor=1','--window-size=1920,1080','--window-position=0,0',
               '--kiosk','--no-startup-window','--no-first-run','--no-default-browser-check']
        process=subprocess.Popen(['gamescope','--backend','headless','-w','1920','-h','1080','-W','1920','-H','1080',
                                  '--',sys.executable,'-B','-c',child,str(endpoint),str(binary),*flags],
                                 cwd=str(ROOT),stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL,start_new_session=True)
        end=time.monotonic()+30
        while not endpoint.exists():
            if process.poll() is not None or time.monotonic()>=end:raise RuntimeError('gamescope nuevo no confirmó su pantalla')
            time.sleep(.1)
        fd=os.open(endpoint,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
        with os.fdopen(fd,'rb') as stream:
            meta=os.fstat(stream.fileno())
            if meta.st_uid!=os.getuid() or meta.st_mode&0o077:raise RuntimeError('Endpoint nuevo no privado')
            raw=stream.read(1025)
        if len(raw)>1024 or not raw.endswith(b'\n'):raise RuntimeError('Pantalla nueva no confirmada')
        reply=json.loads(raw)
        if type(reply) is not dict or set(reply)!={'pid','display'} or type(reply['pid']) is not int or \
                not 0<reply['pid']<2**31 or type(reply['display']) is not str or \
                not re.fullmatch(r':[0-9]{1,5}(?:\.0)?',reply['display']):raise RuntimeError('Endpoint nuevo inválido')
        pid=reply['pid'];end=time.monotonic()+30
        while True:
            if process.poll() is not None:raise RuntimeError('gamescope terminó antes de preparar Brave')
            try:browser_identity(pid,port,account);serial=gamescope_launch_serial(process.pid);break
            except RuntimeError:
                if time.monotonic()>=end:raise
                time.sleep(.1)  # Esperar arranque, sin reenviar navegación ni input.
        target=prepare_brave(pid,port)
        if process.poll() is not None:raise RuntimeError('gamescope terminó durante la preparación')
        return process,{'FARM_GAMESCOPE_DISPLAY':reply['display'],'FARM_GAMESCOPE_SERIAL':serial,
                        'FARM_BRAVE_PID':str(pid),'FARM_BRAVE_CDP_PORT':str(port),'FARM_BRAVE_TARGET_ID':target}
    except BaseException:
        if process is not None and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=2)
        raise
    finally:
        try:
            if bootstrap is not None:bootstrap.cleanup()
        finally:lock.close()


class Bridge:
    """Un WebSocket nativo persistente por guarda; solo check y Escape, sin datos web en stdout."""
    def __init__(self,port,target):
        self.process=None;self.closed=False;self.broken=False;self.buffer=b'';self.sequence=0
        if type(port) is not int or not 0<port<65536 or not isinstance(target,str) or not re.fullmatch(r'[0-9a-fA-F]{32}',target):
            raise RuntimeError('El adaptador de la guarda requiere puerto válido y target hexadecimal fijo')
        node=shutil.which('node')
        if node is None:raise RuntimeError('Brave requiere Node con WebSocket nativo; no se habilita input')
        try:
            # No heredar credenciales, proxies ni NODE_OPTIONS/preloads al adaptador CDP.
            self.process=subprocess.Popen([node,str(Path(__file__).with_name('brave_cdp.mjs')),str(port),target],
                cwd=str(ROOT),env={'PATH':os.defpath,'LANG':'C.UTF-8'},stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,bufsize=0,start_new_session=True)
            self._receive(0,15)  # en vivo, con tres cuentas arrancando a la vez, 5 s no bastó
        except (OSError,ValueError,TypeError):
            self.close()
            raise RuntimeError('No se puede abrir el CDP local propio de Brave') from None
        except BaseException:
            self.close();raise

    def _receive(self,expected,timeout=30):  # snapshot: varias llamadas de hasta 8 s mientras Unity carga
        end=time.monotonic()+timeout
        while b'\n' not in self.buffer:
            remaining=end-time.monotonic()
            if remaining<=0 or not select.select([self.process.stdout],[],[],remaining)[0]:raise ValueError
            chunk=os.read(self.process.stdout.fileno(),1025)
            if not chunk or len(self.buffer)+len(chunk)>1024:raise ValueError
            self.buffer+=chunk
        line,self.buffer=self.buffer.split(b'\n',1);reply=json.loads(line)
        if not isinstance(reply,dict) or set(reply)!={'id','ok'} or type(reply['id']) is not int or \
                reply['id']!=expected or reply['ok'] is not True:raise ValueError

    def call(self,op,xy=None):
        if self.closed or self.broken or op not in ('check','escapeDown','escapeUp','point'):
            raise RuntimeError('CDP propio no disponible; no se envía input')
        try:
            self.sequence+=1;request={'id':self.sequence,'op':op}
            if op=='point':request['xy']=xy
            data=json.dumps(request).encode()+b'\n'
            if self.process.stdin.write(data)!=len(data):raise ValueError
            self._receive(self.sequence)
        except KeyboardInterrupt:
            self.broken=True;raise  # EOF hará que el adaptador suelte Escape antes de desconectarse.
        except (OSError,ValueError,TypeError):
            self.broken=True
            raise RuntimeError('CDP no confirma la identidad, foco o geometría de Brave; no se envía input') from None

    def close(self):
        if self.closed:return
        self.closed=True
        _close_adapter(self.process)


class BraveGuard:
    def __init__(self,display,window):
        self.pidfd=None;self.bridge=None;self.display=display;self.window=window
        self.settings=(account_id(),gamescope_target(),brave_target())
        if self.settings[0] not in ('personal','perfil-1') or self.settings[1] is None:
            raise RuntimeError('Brave requiere una cuenta y pantalla explícitas')
        self.pid,self.port,self.target=self.settings[2]
        try:
            self.pidfd=os.pidfd_open(self.pid)
            self.identity=browser_identity(self.pid,self.port,self.settings[0])
            self.check_window(window)
            if select.select([self.pidfd],[],[],0)[0]:raise RuntimeError('El proceso Brave original terminó antes de abrir CDP')
            self.bridge=Bridge(self.port,self.target)
        except BaseException:
            self.close();raise

    def check_window(self,window):
        try:
            geo=window.get_geometry();prop=window.get_full_property(self.display.intern_atom('_NET_WM_PID'),0)
            focus=self.display.screen().root.get_full_property(self.display.intern_atom('GAMESCOPE_FOCUSED_WINDOW'),0)
            if window.id!=self.window.id or \
                    window.get_wm_class()!=(f'brave-browser ({ROOT}/runs/accounts/{self.settings[0]}/brave-data)','Brave-browser') or \
                    (geo.x,geo.y,geo.width,geo.height)!=(0,0,1920,1080) or window.get_attributes().map_state!=2 or \
                    prop is None or list(prop.value)!=[self.pid] or focus is None or list(focus.value)!=[window.id] or \
                    getattr(self.display.get_input_focus().focus,'id',None)!=window.id:raise ValueError
        except Exception:
            raise RuntimeError('Brave perdió el foco o cambió su ventana, proceso o geometría') from None

    def check(self,window=None):
        if self.pidfd is None or select.select([self.pidfd],[],[],0)[0] or \
                (account_id(),gamescope_target(),brave_target())!=self.settings or \
                browser_identity(self.pid,self.port,self.settings[0])!=self.identity:
            raise RuntimeError('Cambió la identidad o los endpoints propios de Brave')
        self.check_window(self.window if window is None else window)
        self.bridge.call('check')

    def key(self,op):
        if op not in ('escapeDown','escapeUp'):raise RuntimeError('Tecla CDP no autorizada')
        if op=='escapeDown':self.check()
        if self.bridge is None:raise RuntimeError('CDP propio cerrado; no se envía input')
        self.bridge.call(op)

    def point(self,xy):
        self.check();self.bridge.call('point',xy)

    def close(self):
        try:
            if self.bridge is not None:self.bridge.close();self.bridge=None
        finally:
            if self.pidfd is not None:os.close(self.pidfd);self.pidfd=None
