"""Backend gamescope: el juego corre en una pantalla virtual y el usuario puede usar otras ventanas.

- Imagen: el nodo PipeWire "gamescope" (1920x1080) mediante un gst-launch persistente que
  escribe fotogramas BGR crudos; siempre se devuelve el más reciente, nunca uno viejo.
- Input: XTest sobre el servidor X propio de gamescope (no mueve el cursor del usuario).
- Guarda: la ventana "Bit Heroes" debe seguir en ese servidor; F8 sigue mirándose en el
  escritorio del usuario (niri) mediante LinuxAPI.emergency.

Uso: lanzar el juego con `gamescope --backend headless -w 1920 -h 1080 -W 1920 -H 1080 --
steam ...` y exportar FARM_BACKEND=gamescope.
"""

from __future__ import annotations

import os
import select
import signal
import subprocess
import sys
import threading
import time

import numpy as np

from .control_flow import SafetyStop
from .accounts import account_id, gamescope_target, shm_path

W,H=1920,1080
FRAME=W*H*3
GAME_TITLE='Bit Heroes'


def pipewire_serial(name='gamescope'):
    """object.serial del nodo de vídeo de gamescope en PipeWire."""
    target=gamescope_target()
    out=subprocess.run(['pw-cli','ls','Node'],capture_output=True,text=True,timeout=10).stdout
    block={};matches=[]
    for line in out.splitlines()+['id end']:
        line=line.strip()
        if line.startswith('id '):
            if block.get('node.name')==f'"{name}"' and block.get('media.class')=='"Video/Source"':
                serial=block.get('object.serial','').strip('"')
                if serial.isdecimal() and (target is None or serial==target[1]):matches.append(serial)
            block={}
        elif ' = ' in line:
            k,v=line.split(' = ',1);block[k]=v
    if len(matches)==1:return matches[0]
    if matches:raise RuntimeError('Hay varios nodos de vídeo de gamescope; especifica la sesión, no se elige el primero')
    raise RuntimeError('No hay nodo de vídeo de gamescope para esta sesión en PipeWire')


def find_display(title=GAME_TITLE):
    """Servidor X de gamescope que contiene la ventana del juego."""
    from Xlib import display
    target=gamescope_target()
    if target is not None:
        try:d=display.Display(target[0])
        except Exception as exc:raise RuntimeError('gamescope no responde en la pantalla de esta cuenta') from exc
        try:
            if window_of(d,title) is not None:return d
        except Exception:
            d.close();raise
        d.close()
        raise RuntimeError('No se encontró la ventana de Bit Heroes en la pantalla de esta cuenta')
    matches=[]
    for entry in sorted(os.listdir('/tmp/.X11-unix')):
        name=':'+entry.lstrip('X')
        try:
            d=display.Display(name)
        except Exception:
            continue
        try:
            if window_of(d,title) is not None:matches.append(d)
            else:d.close()
        except Exception:
            d.close()
            for candidate in matches:candidate.close()
            raise
    if len(matches)==1:return matches[0]
    if matches:
        for candidate in matches:candidate.close()
        raise RuntimeError('Hay varias pantallas con Bit Heroes; especifica la sesión, no se elige la primera')
    raise RuntimeError('No se encontró la ventana de Bit Heroes en ningún servidor X de gamescope')


def window_of(d,title=GAME_TITLE):
    account=account_id();brave=account in ('personal','perfil-1')
    if brave:
        from .accounts import brave_target
        from .telemetry import ROOT
        pid=brave_target()[0];cls=(f'brave-browser ({ROOT}/runs/accounts/{account}/brave-data)','Brave-browser')
    matches=[]
    def walk(w):
        for c in w.query_tree().children:
            try:
                geo=c.get_geometry()
                if brave:
                    prop=c.get_full_property(d.intern_atom('_NET_WM_PID'),0)
                    own=c.get_wm_class()==cls and prop is not None and list(prop.value)==[pid]
                else:own=c.get_wm_name()==title
                if own and (geo.width,geo.height)==(W,H):matches.append(c)
                walk(c)
            except Exception:
                pass
    walk(d.screen().root)
    if len(matches)>1:raise RuntimeError('Hay varias ventanas Bit Heroes en gamescope; identidad ambigua')
    return matches[0] if matches else None


class PipeWireFrames:
    """Lee el flujo crudo en un hilo y conserva solo el último fotograma completo."""
    def __init__(self,serial):
        self.proc=subprocess.Popen(['gst-launch-1.0','-q','-e','pipewiresrc',f'target-object={serial}','always-copy=true','!',
                                    'videoconvert','!','video/x-raw,format=BGR,width=1920,height=1080','!','fdsink','fd=1'],
                                   stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,bufsize=0)
        self.lock=threading.Lock();self.latest=None;self.stamp=0.0;self.error=None
        self.thread=threading.Thread(target=self.pump,daemon=True);self.thread.start()

    def pump(self):
        buf=bytearray()
        try:
            while True:
                chunk=self.proc.stdout.read(FRAME-len(buf))
                if not chunk:break
                buf+=chunk
                if len(buf)==FRAME:
                    with self.lock:self.latest=bytes(buf);self.stamp=time.monotonic()
                    buf=bytearray()
        except Exception as exc:
            self.error=exc

    def frame(self,newer_than,timeout=0.4):
        """Fotograma más reciente. gamescope solo emite al cambiar la imagen: si en `timeout` no llega
        uno nuevo, el último sigue siendo el actual (pantalla quieta), siempre que el flujo siga vivo."""
        end=time.monotonic()+timeout
        while True:
            if self.proc.poll() is not None or self.error is not None:raise RuntimeError('El flujo de gamescope se cerró')
            with self.lock:
                if self.latest is not None and (self.stamp>newer_than or time.monotonic()>=end):
                    return np.frombuffer(self.latest,np.uint8).reshape(H,W,3)
            if time.monotonic()>=end+2.0:raise RuntimeError('gamescope no entregó ningún fotograma')
            time.sleep(.01)

    def close(self):
        if self.proc.poll() is None:
            self.proc.send_signal(signal.SIGINT)  # gst-launch gestiona Ctrl-C + -e; SIGTERM no drena el flujo.
            try:self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.terminate()
                try:self.proc.wait(timeout=2)
                except subprocess.TimeoutExpired:self.proc.kill();self.proc.wait(timeout=2)
        else:self.proc.wait()
        self.thread.join(timeout=2);self.proc.stdout.close()
        if self.thread.is_alive():raise RuntimeError('El hilo lector de gamescope no terminó')


SHM=shm_path()  # [seq u64][stamp f64][BGR 1920x1080], independiente por cuenta
LEGACY_SHM='/dev/shm/bitheroes-gamescope-frame'
HEADER=16


def legacy_steam_frames(proc=None):
    """Verificar el flujo antiguo contra proceso propio, memoria privada y serial explícito."""
    from pathlib import Path
    from .telemetry import ROOT
    if account_id()!='steam':return False
    serial=gamescope_target()[1];proc=Path('/proc') if proc is None else Path(proc);fd=None
    try:
        frame=Path(LEGACY_SHM);meta=frame.stat()
        if frame.is_symlink() or meta.st_uid!=os.getuid() or meta.st_mode&0o077 or meta.st_size!=HEADER+FRAME:return False
        fd=os.open(LEGACY_SHM+'.pid',os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
        if os.fstat(fd).st_uid!=os.getuid():return False
        value=os.read(fd,33).strip()
        if len(value)>10 or not value.isdigit() or int(value)<=0:return False
        pid=str(int(value));server=proc/pid
        if server.stat().st_uid!=os.getuid() or (server/'cwd').resolve()!=ROOT or \
                (server/'exe').resolve()!=Path(sys.executable).resolve():return False
        raw=(server/'cmdline').read_bytes()
        if len(raw)>65536 or not raw.endswith(b'\0'):return False
        args=[os.fsdecode(a) for a in raw[:-1].split(b'\0')][1:]
        while args and args[0] in ('-B','-u'):args.pop(0)
        if args!=['-m','fishing_core.gamescope','serve']:return False
        if not any(link.resolve()==frame.resolve() for link in (server/'fd').iterdir()):return False
        matches=0
        for child in (server/'task'/pid/'children').read_text().split():
            if not child.isdecimal():return False
            p=proc/child
            if p.stat().st_uid!=os.getuid():return False
            if (p/'exe').resolve().name!='gst-launch-1.0':continue
            raw=(p/'cmdline').read_bytes()
            if len(raw)>65536 or not raw.endswith(b'\0'):return False
            args=[os.fsdecode(a) for a in raw[:-1].split(b'\0')]
            if args.count('pipewiresrc')!=1 or [a for a in args if a.startswith('target-object=')]!=[f'target-object={serial}']:return False
            matches+=1
        return matches==1
    except (OSError,ValueError):return False
    finally:
        if fd is not None:os.close(fd)


def steam_frame_source():
    """Compartir solo el flujo antiguo verificado; restos o dos fuentes detienen sin duplicar."""
    if account_id()!='steam':return None
    if legacy_steam_frames():
        if server_alive():raise RuntimeError('Fuente Steam ambigua: hay dos capturas; no se elige una')
        return LEGACY_SHM
    if any(os.path.lexists(path) for path in (LEGACY_SHM,LEGACY_SHM+'.pid')):
        raise RuntimeError('Flujo Steam antiguo no confirmado; no se abre otra captura')
    return None


class FrameServer:
    """Un único flujo PipeWire por sesión: abrir y cerrar flujos de gamescope coincidió con sus
    caídas (SIGSEGV en el driver Vulkan). Publica el último fotograma en memoria compartida."""
    def __init__(self):
        import mmap
        from .processes import Mutex
        self.mutex=Mutex('FRAME_SERVER');self.fd=self.map=self.frames=None
        try:
            if account_id()=='steam' and any(os.path.lexists(path) for path in (LEGACY_SHM,LEGACY_SHM+'.pid')):
                raise RuntimeError('Flujo Steam antiguo no confirmado; no se abre otra captura')
            serial=pipewire_serial()
            self.fd=os.open(SHM,os.O_CREAT|os.O_RDWR|os.O_CLOEXEC|os.O_NOFOLLOW,0o600)
            if os.fstat(self.fd).st_uid!=os.getuid():raise RuntimeError('La memoria de imagen no pertenece al usuario')
            os.ftruncate(self.fd,HEADER+FRAME)
            self.map=mmap.mmap(self.fd,HEADER+FRAME);self.map[:HEADER]=bytes(HEADER)
            self.frames=PipeWireFrames(serial);self.seq=0
        except Exception:
            self.close();raise

    def serve(self,stop):
        import struct
        last=0.0
        while not stop.is_set():
            if self.frames.proc.poll() is not None:raise RuntimeError('El flujo de gamescope se cerró')
            with self.frames.lock:latest,stamp=self.frames.latest,self.frames.stamp
            if latest is not None and stamp>last:
                last=stamp;self.seq+=1
                self.map[HEADER:]=latest;self.map[:HEADER]=struct.pack('<Qd',self.seq,time.time())
            time.sleep(.005)

    def close(self):
        try:
            if self.frames is not None:self.frames.close()
        finally:
            try:
                if self.map is not None:self.map.close()
                if self.fd is not None:os.close(self.fd)
            finally:self.mutex.close()


class SharedFrames:
    """Lado lector de FrameServer: misma interfaz que PipeWireFrames.frame()."""
    def __init__(self,path=None):
        import mmap
        self.path=SHM if path is None else path
        if self.path not in (SHM,LEGACY_SHM):raise RuntimeError('Fuente de imagen no permitida')
        self.fd=os.open(self.path,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
        try:
            if os.fstat(self.fd).st_uid!=os.getuid():raise RuntimeError('La imagen no pertenece al usuario')
            if os.fstat(self.fd).st_size!=HEADER+FRAME:raise RuntimeError('Cambió el tamaño de la memoria de imagen')
            self.map=mmap.mmap(self.fd,HEADER+FRAME,prot=mmap.PROT_READ)
        except BaseException:os.close(self.fd);raise

    def frame(self,newer_than,timeout=0.4):
        import struct
        end=time.monotonic()+timeout;start_seq=None
        while True:
            alive=legacy_steam_frames() if self.path!=SHM else server_alive()
            if not alive:raise RuntimeError('El flujo de gamescope se cerró')
            current=os.stat(self.path,follow_symlinks=False);opened=os.fstat(self.fd)
            if (current.st_dev,current.st_ino)!=(opened.st_dev,opened.st_ino) or opened.st_size!=HEADER+FRAME:
                raise RuntimeError('Cambió la memoria de imagen')
            seq,written=struct.unpack('<Qd',self.map[:HEADER])
            if start_seq is None:start_seq=seq
            if seq==0:
                if time.monotonic()>=end+2.0:raise RuntimeError('gamescope no entregó ningún fotograma')
            elif seq!=start_seq or time.monotonic()>=end:
                data=bytes(self.map[HEADER:]);check=struct.unpack('<Qd',self.map[:HEADER])[0]
                if check==seq:return np.frombuffer(data,np.uint8).reshape(H,W,3)  # copia sin escritura a medias
                continue
            time.sleep(.01)

    def close(self):
        self.map.close();os.close(self.fd)


def server_alive():
    pid_file=SHM+'.pid'
    try:
        pid=int(open(pid_file).read());os.kill(pid,0);return True
    except (OSError,ValueError):
        return False


class GamescopeGuard:
    """Equivalente a WindowGuard: el juego sigue en su servidor X de gamescope. F8 en el escritorio."""
    def __init__(self,read_only=False):
        require_calibrated_client(read_only=read_only);self.read_only=read_only
        from .linux import LinuxAPI
        self.display=self.desktop=self.web=None;self.target=gamescope_target()
        try:
            self.display=find_display();self.window=window_of(self.display)
            self.desktop=LinuxAPI()  # solo para F8 (estado del teclado del usuario)
            if account_id() in ('personal','perfil-1'):
                from .brave import BraveGuard
                self.web=BraveGuard(self.display,self.window)
        except BaseException:
            self.close();raise

    def focused(self):
        prop=self.display.screen().root.get_full_property(self.display.intern_atom('GAMESCOPE_FOCUSED_WINDOW'),0)
        return prop.value[0] if prop and len(prop.value) else None

    def restore_focus(self):
        """Otra ventana tiene el foco: las de Steam (avisos) se cierran como con su X; las auxiliares del
        propio juego (Proton) o las que ya se cerraron suelen devolverlo solas. Espera hasta 5 s."""
        if getattr(self,'read_only',False):return False
        from Xlib import X
        from Xlib.protocol import event
        end=time.monotonic()+5
        while time.monotonic()<end:
            focused=self.focused()
            if focused in (None,self.window.id):return True
            try:
                other=self.display.create_resource_object('window',focused)
                cls=other.get_wm_class() or ('','')
            except Exception:  # BadWindow: se cerró mientras se miraba
                time.sleep(.5);continue
            if cls[1]=='steam':
                message=event.ClientMessage(window=other,client_type=self.display.intern_atom('WM_PROTOCOLS'),
                                            data=(32,[self.display.intern_atom('WM_DELETE_WINDOW'),X.CurrentTime,0,0,0]))
                other.send_event(message);self.display.sync();time.sleep(1.5);continue
            time.sleep(.5)
        return self.focused() in (None,self.window.id)

    def check(self):
        try:
            if hasattr(self,'target') and gamescope_target()!=self.target:
                raise RuntimeError('Cambió el endpoint de gamescope; no se envía input')
            current=window_of(self.display)
            if current is None:raise RuntimeError('La ventana de Bit Heroes desapareció de gamescope')
            if current.id!=self.window.id:raise RuntimeError('La ventana de Bit Heroes cambio su identidad; no se envía input')
            if getattr(self,'web',None) is not None:
                if self.focused()!=self.window.id:raise RuntimeError('Brave perdió el foco en gamescope; no se envía input')
                self.web.check(current)
            elif self.focused() not in (None,self.window.id) and (getattr(self,'read_only',False) or not self.restore_focus()):
                raise RuntimeError('Otra ventana tapa el juego en gamescope; no se envía input')
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f'gamescope no responde: {exc}') from exc

    def close(self):
        try:
            if getattr(self,'web',None) is not None:self.web.close();self.web=None
        finally:
            try:
                if self.display is not None:self.display.close();self.display=None
            finally:
                if self.desktop is not None:self.desktop.close();self.desktop=None


class GamescopeIO:
    """Misma interfaz que LinuxIO (click, _move, escape, emergency, check_game) sobre gamescope."""
    platform='linux'

    def __init__(self,read_only=False):
        self.game_guard=None;self.control_mode=False;self.read_only=read_only
        try:
            self.game_guard=GamescopeGuard(read_only=True) if read_only else GamescopeGuard();self.check_game()
        except BaseException:
            self.close();raise

    def emergency(self):
        self.game_guard.desktop.emergency()

    def check_game(self):
        try:self.game_guard.check()
        except RuntimeError as exc:raise SafetyStop(str(exc)) from exc

    def rebaseline_web(self):
        web=getattr(self.game_guard,'web',None)
        if web is None:return
        from .brave import BraveGuard
        replacement=None
        try:
            self.emergency();web.close()
            replacement=BraveGuard(self.game_guard.display,self.game_guard.window)
            if replacement.settings!=web.settings or replacement.identity!=web.identity:
                raise RuntimeError('Cambió la identidad o los endpoints propios de Brave')
            replacement.check()
            self.game_guard.web=replacement
        except BaseException as exc:
            if replacement is not None:replacement.close()
            if isinstance(exc,RuntimeError):raise SafetyStop(str(exc)) from exc
            raise

    def _move(self,xy,settle=True):
        if getattr(self,'read_only',False):raise SafetyStop('Modo observación: todo input está bloqueado')
        from Xlib import X
        from Xlib.ext import xtest
        if len(xy)!=2 or any(type(n) is not int for n in xy) or not (0<=xy[0]<W and 0<=xy[1]<H):
            raise SafetyStop('Coordenadas fuera de la pantalla de gamescope')
        self.emergency();self.check_game()
        d=self.game_guard.display;xtest.fake_input(d,X.MotionNotify,x=xy[0],y=xy[1]);d.sync()
        if settle and self.control_mode:time.sleep(.08)
        self.emergency();self.check_game()

    def click(self,xy):
        from Xlib import X
        from Xlib.ext import xtest
        self._move(xy);d=self.game_guard.display
        self.check_point(xy)
        try:
            xtest.fake_input(d,X.ButtonPress,1);d.sync()
            if self.control_mode:time.sleep(.06)
        finally:
            xtest.fake_input(d,X.ButtonRelease,1);d.sync()

    def cast_click(self,xy):
        self.click(xy)

    def check_point(self,xy):
        web=getattr(self.game_guard,'web',None)
        if web is not None:
            try:web.point(xy)
            except RuntimeError as exc:raise SafetyStop(str(exc)) from exc
            self.emergency();self.check_game()

    def escape(self):
        if getattr(self,'read_only',False):raise SafetyStop('Modo observación: todo input está bloqueado')
        self.emergency();self.check_game()
        web=getattr(self.game_guard,'web',None)
        if web is not None:
            try:
                web.key('escapeDown');self.emergency();self.check_game()
            except BaseException:
                try:web.key('escapeUp')
                except (RuntimeError,KeyboardInterrupt):
                    try:web.close()
                    except (RuntimeError,OSError,KeyboardInterrupt):pass  # Se conserva la parada original, incluso si el cierre falló.
                raise  # Detener/Ctrl+C nunca se transforma en un reintento por el error de soltar.
            web.key('escapeUp');self.emergency();self.check_game();return
        from Xlib import X
        from Xlib.ext import xtest
        d=self.game_guard.display;key=d.keysym_to_keycode(0xff1b)
        if not key:raise SafetyStop('Escape no disponible en gamescope')
        try:
            xtest.fake_input(d,X.KeyPress,key);d.sync();time.sleep(.06)
            self.emergency();self.check_game()
        finally:
            xtest.fake_input(d,X.KeyRelease,key);d.sync()

    def wheel(self,steps,xy=(930,600)):
        from Xlib import X
        from Xlib.ext import xtest
        self._move(xy);d=self.game_guard.display
        for _ in range(abs(steps)):
            self.emergency();self.check_game();button=5 if steps>0 else 4
            self.check_point(xy)
            xtest.fake_input(d,X.ButtonPress,button);xtest.fake_input(d,X.ButtonRelease,button);d.sync();time.sleep(.05)

    def close(self):
        if self.game_guard is not None:self.game_guard.close();self.game_guard=None


class GamescopeCapture:
    """Misma interfaz que LinuxCapture: grab(monitor) devuelve un ScreenShot BGRA del recorte pedido."""
    def __init__(self,guard):
        # Con el servidor de fotogramas en marcha no se abre otro flujo PipeWire (ver FrameServer).
        source=steam_frame_source();alive=server_alive()
        if account_id() is not None and not alive and source is None:
            raise RuntimeError('No hay servidor de imagen propio de esta cuenta; no se abre otro flujo')
        self.guard=guard;self.frames=SharedFrames(source) if source is not None else SharedFrames() if alive else PipeWireFrames(pipewire_serial())

    def __enter__(self):
        return self

    def __exit__(self,*args):
        self.close();return False

    def close(self):
        self.frames.close()

    def grab(self,monitor):
        from mss.screenshot import ScreenShot
        try:
            self.guard.check()
            x,y,w,h=(monitor[k] for k in ('left','top','width','height'))
            if any(type(n) is not int for n in (x,y,w,h)) or x<0 or y<0 or w<=0 or h<=0 or x+w>W or y+h>H:
                raise RuntimeError('Región de captura fuera del juego')
            try:
                frame=self.frames.frame(time.monotonic())
            except RuntimeError:
                if isinstance(self.frames,SharedFrames):raise  # el servidor lleva su propio flujo
                # El flujo se corta si otra ventana tapó el juego: reabrirlo una vez, ya con el juego delante.
                self.frames.close();self.guard.check();self.frames=PipeWireFrames(pipewire_serial())
                frame=self.frames.frame(time.monotonic(),timeout=2.0)
            if not isinstance(frame,np.ndarray) or frame.shape!=(H,W,3) or frame.dtype!=np.uint8:
                raise RuntimeError('Fotograma BGR de gamescope con tamaño o formato incorrectos')
            self.guard.check()  # No entregar una imagen si la ventana/contenido cambió durante la copia.
            frame=frame[y:y+h,x:x+w]
            bgra=np.dstack([frame,np.full(frame.shape[:2],255,np.uint8)])
            return ScreenShot(bytearray(bgra.tobytes()),monitor)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            raise SafetyStop('No se puede capturar gamescope: '+str(exc)) from exc


GONE=('No se encontró la ventana de Bit Heroes','gamescope no responde','flujo de gamescope se cerró',
      'gamescope no entregó','No hay nodo de vídeo de gamescope','desapareció de gamescope')


def is_gone(message):
    """La parada se debe a que gamescope/el juego dejó de existir (p. ej. el fallo del driver Vulkan)."""
    return any(text in message for text in GONE)


def relaunch_game(timeout=300):
    """Cierra lo que quede de Steam y relanza el juego con JUEGO_SEGUNDO_PLANO.sh; espera a que exista."""
    if account_id() is not None:
        raise RuntimeError('El relanzamiento global de Steam está deshabilitado en multicuenta')
    root=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if subprocess.run(['pgrep','-x','steam'],capture_output=True).returncode==0:
        subprocess.run(['steam','-shutdown'],capture_output=True,timeout=30)
        for _ in range(60):
            if subprocess.run(['pgrep','-x','steam'],capture_output=True).returncode!=0:break
            time.sleep(1)
    subprocess.Popen([os.path.join(root,'JUEGO_SEGUNDO_PLANO.sh')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                     stdin=subprocess.DEVNULL,start_new_session=True)
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        time.sleep(5)
        try:
            find_display().close();pipewire_serial();time.sleep(20)  # dejar que el juego cargue
            return True
        except Exception:
            continue
    return False


def require_calibrated_client(env=None,read_only=False):
    gamescope_target(env)
    if type(read_only) is not bool or (read_only and account_id(env) is None):
        raise ValueError('Observación requiere una cuenta gamescope explícita')
    if read_only:
        from .accounts import brave_target
        brave_target(env)
    if not read_only and account_id(env) not in (None,'steam'):
        # crzf autorizó el farmeo online de las tres cuentas (2026-10-08). Las guardas de Brave
        # (PID/perfil/puerto, foco, geometría y punto sobre el canvas) siguen comprobándose en cada input.
        from .accounts import brave_target
        source=os.environ if env is None else env
        if source.get('FARM_SINGLE_DUNGEON')!='1' and source.get('FARM_MULTI_FARM')!='1':
            raise ValueError('Input en Brave solo desde el supervisor multicuenta (prueba o farmeo)')
        pid,port,_=brave_target(env)
        from .brave import browser_identity
        browser_identity(pid,port,account_id(env))  # proceso, perfil exclusivo y puerto CDP propios, vivos


def backend(read_only=False):
    """(IO, Capture) según FARM_BACKEND: 'gamescope' o el escritorio niri por defecto."""
    require_calibrated_client(read_only=read_only)
    if read_only:
        from functools import partial
        return partial(GamescopeIO,read_only=True),GamescopeCapture
    if os.environ.get('FARM_BACKEND')=='gamescope':return GamescopeIO,GamescopeCapture
    from .linux import LinuxIO,LinuxCapture
    return LinuxIO,LinuxCapture


def serve_forever():
    """Proceso servidor: python -m fishing_core.gamescope serve (lo lanza farm_all en segundo plano)."""
    import signal
    stop=threading.Event();signal.signal(signal.SIGTERM,lambda *a:stop.set());signal.signal(signal.SIGINT,lambda *a:stop.set())
    server=FrameServer()
    try:
        fd=os.open(SHM+'.pid',os.O_CREAT|os.O_WRONLY|os.O_TRUNC|os.O_CLOEXEC|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'w') as pid_file:pid_file.write(str(os.getpid()))
        server.serve(stop)
    finally:
        try:
            for path in (SHM,SHM+'.pid'):
                try:os.remove(path)
                except OSError:pass
        finally:server.close()  # soltar el lock solo después de retirar los archivos propios


if __name__=='__main__':
    import sys
    if sys.argv[1:]==['serve']:serve_forever()
