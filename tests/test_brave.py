"""Guardas CDP offline: no navegan, capturan ni envían input a ningún cliente real."""
import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock,patch
from types import SimpleNamespace

from fishing_core.telemetry import ROOT


class BraveBridgeProtocolTests(unittest.TestCase):
    def bridge(self):
        import io
        from fishing_core.brave import Bridge
        bridge=Bridge.__new__(Bridge)
        bridge.closed=bridge.broken=False;bridge.sequence=0
        bridge.process=SimpleNamespace(stdin=io.BytesIO())
        bridge._receive=Mock()
        return bridge

    def test_mouse_and_frame_json_lines(self):
        import json
        bridge=self.bridge()
        bridge.call('move',xy=(1,2));bridge.call('click',xy=(3,4))
        bridge.call('wheel',xy=(5,6),steps=-2);bridge.call('frame',path='test.png')
        lines=bridge.process.stdin.getvalue().splitlines()
        self.assertEqual([json.loads(line) for line in lines],[
            {'id':1,'op':'move','xy':[1,2]},{'id':2,'op':'click','xy':[3,4]},
            {'id':3,'op':'wheel','xy':[5,6],'steps':-2},{'id':4,'op':'frame','path':'test.png'}])
        self.assertTrue(all(len(line)<1024 for line in lines))

    def test_refused_reply_blocks_later_requests(self):
        bridge=self.bridge();bridge._receive.side_effect=ValueError('refuse')
        with self.assertRaises(RuntimeError):bridge.call('click',xy=(1,2))
        before=bridge.process.stdin.getvalue()
        with self.assertRaises(RuntimeError):bridge.call('move',xy=(3,4))
        self.assertEqual(bridge.process.stdin.getvalue(),before)

    def test_windows_pipe_receive_keeps_bounded_protocol(self):
        import queue
        bridge=self.bridge();bridge.buffer=b'';bridge.replies=queue.Queue()
        for byte in b'{"id":1,"ok":true}\n':bridge.replies.put(bytes([byte]))
        from fishing_core.brave import Bridge
        with patch('fishing_core.brave.os.name','nt'):
            Bridge._receive(bridge,1)
            for byte in b'x'*1025:bridge.replies.put(bytes([byte]))
            with self.assertRaises(ValueError):Bridge._receive(bridge,2)


@unittest.skipIf(os.name=='nt','Identidad de proceso Linux')
class BraveIdentityTests(unittest.TestCase):
    def test_endpoint_identity_keeps_browser_start_parent_and_pipe(self):
        from fishing_core import brave
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=self.fixture(root)
            (p/'stat').write_text('1234 (brave) '+' '.join(['S','99']+['0']*17+['9001']))
            args=['brave',f'--user-data-dir={ROOT}/runs/accounts/personal/brave-data','--remote-debugging-pipe']
            (p/'cmdline').write_bytes(b'\0'.join(os.fsencode(a) for a in args)+b'\0')
            with patch.object(brave,'validate_cdp_endpoint'):
                self.assertEqual(brave.browser_identity(1234,'/endpoint','personal',root),(str(root/'brave'),'9001',99))
                with self.assertRaises(RuntimeError):brave.browser_identity(1234,'/endpoint','perfil-1',root)
                (p/'cmdline').write_bytes(b'\0'.join(os.fsencode(a) for a in args+['--remote-debugging-port=9222'])+b'\0')
                with self.assertRaises(RuntimeError):brave.browser_identity(1234,'/endpoint','personal',root)

    def test_registered_browser_keeps_profile_and_port_guards(self):
        from fishing_core import accounts
        from fishing_core.brave import browser_identity
        with tempfile.TemporaryDirectory() as tmp,patch.object(accounts,'ROOT',Path(tmp)):
            accounts.add_account('Amigo','browser')
            root=Path(tmp)/'proc';self.fixture(root,account='amigo')
            self.assertEqual(browser_identity(1234,45678,'amigo',root),(str(root/'brave'),'9001'))
            with self.assertRaises(RuntimeError):browser_identity(1234,45679,'amigo',root)
            accounts.remove_account('amigo')
            with self.assertRaises(RuntimeError):browser_identity(1234,45678,'amigo',root)

    def fixture(self,path,account='personal',port=45678):
        p=path/'1234';(p/'fd').mkdir(parents=True);(p/'net').mkdir()
        exe=path/'brave';exe.touch();(p/'exe').symlink_to(exe)
        (p/'stat').write_text('1234 (brave) '+' '.join(['S']+['0']*18+['9001']))
        args=['brave',f'--user-data-dir={ROOT}/runs/accounts/{account}/brave-data','--remote-debugging-port=0']
        (p/'cmdline').write_bytes(b'\0'.join(os.fsencode(a) for a in args)+b'\0')
        (p/'fd/7').symlink_to('socket:[777]')
        (p/'net/tcp').write_text(f'header\n 0: 0100007F:{port:04X} 00000000:0000 0A 0:0 0:0 0 1000 0 777\n')
        return p

    def test_browser_pid_is_bound_to_its_own_profile_loopback_socket_and_start_time(self):
        from fishing_core.brave import browser_identity
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            identity=browser_identity(1234,45678,'personal',root)
            self.assertEqual(identity,(str(root/'brave'),'9001'))
            with self.assertRaises(RuntimeError):browser_identity(1234,45678,'perfil-1',root)
            with self.assertRaises(RuntimeError):browser_identity(1234,45679,'personal',root)

    def test_supported_chromium_identity_and_open_profile_keep_guards(self):
        from fishing_core.brave import browser_identity,require_closed_profile
        for name in ('google-chrome','chrome','chromium','microsoft-edge'):
            with self.subTest(browser=name),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);p=self.fixture(root);exe=root/name;exe.touch()
                (p/'exe').unlink();(p/'exe').symlink_to(exe)
                self.assertEqual(browser_identity(1234,45678,'personal',root),(str(exe),'9001'))
                with self.assertRaises(RuntimeError):browser_identity(1234,45679,'personal',root)
                with self.assertRaisesRegex(RuntimeError,'abierto'):
                    require_closed_profile(ROOT/'runs/accounts/personal/brave-data',root)

    def test_foreign_owner_exposed_port_and_duplicated_profile_flags_are_rejected_without_secret_output(self):
        from fishing_core.brave import browser_identity
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=self.fixture(root)
            with patch('fishing_core.brave.os.getuid',return_value=os.getuid()+1),self.assertRaises(RuntimeError):
                browser_identity(1234,45678,'personal',root)
            tcp=p/'net/tcp';original=tcp.read_text();tcp.write_text(original.replace('0100007F','00000000'))
            with self.assertRaises(RuntimeError):browser_identity(1234,45678,'personal',root)
            tcp.write_text(original)
            with (p/'cmdline').open('ab') as f:f.write(b'--user-data-dir=PRIVATE_TEST_MARKER\0')
            with self.assertRaises(RuntimeError) as failure:browser_identity(1234,45678,'personal',root)
            self.assertNotIn('PRIVATE_TEST_MARKER',str(failure.exception))

    def test_incomplete_duplicate_profile_flag_is_still_ambiguous(self):
        from fishing_core.brave import browser_identity
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
            root=Path(tmp);p=self.fixture(root)
            with (p/'cmdline').open('ab') as f:f.write(b'--user-data-dir\0')
            with self.assertRaises(RuntimeError):browser_identity(1234,45678,'personal',root)

    def test_brave_flat_process_title_keeps_exact_profile_and_rejects_malformed_or_duplicate_flags(self):
        from fishing_core.brave import browser_identity
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
            root=Path(tmp);p=self.fixture(root);args=[os.fsdecode(v) for v in (p/'cmdline').read_bytes().split(b'\0') if v]
            (p/'cmdline').write_bytes(os.fsencode(shlex.join(args))+b'\0')
            self.assertEqual(browser_identity(1234,45678,'personal',root),(str(root/'brave'),'9001'))
            for bad in (shlex.join(args)+' --user-data-dir=PRIVATE_TEST_MARKER',shlex.join(args)+' "'):
                (p/'cmdline').write_bytes(os.fsencode(bad)+b'\0')
                with self.assertRaises(RuntimeError) as failure:browser_identity(1234,45678,'personal',root)
                self.assertNotIn('PRIVATE_TEST_MARKER',str(failure.exception))

    def test_closed_profile_refuses_unreadable_or_incomplete_brave_metadata(self):
        from fishing_core.brave import require_closed_profile
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
            root=Path(tmp);p=self.fixture(root);profile=ROOT/'runs/accounts/personal/brave-data'
            for raw in (b'brave\0--other-profile=PRIVATE_TEST_MARKER',b'x'*65537,
                        b'brave "PRIVATE_TEST_MARKER\0'):
                with self.subTest(size=len(raw)):
                    (p/'cmdline').write_bytes(raw)
                    with self.assertRaises(RuntimeError) as failure:require_closed_profile(profile,root)
                    self.assertNotIn('PRIVATE_TEST_MARKER',str(failure.exception))
            with patch.object(Path,'open',side_effect=PermissionError('PRIVATE_TEST_MARKER')):
                with self.assertRaises(RuntimeError) as failure:require_closed_profile(profile,root)
            self.assertNotIn('PRIVATE_TEST_MARKER',str(failure.exception))

    def test_closed_profile_handles_flat_escaping_and_process_disappearance_without_reading_profiles(self):
        from fishing_core.brave import require_closed_profile
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
            root=Path(tmp);p=self.fixture(root);profile=ROOT/'runs/accounts/personal/brave-data'
            escaped=str(profile).replace('/runs/','/r\\uns/')
            (p/'cmdline').write_bytes(os.fsencode(f'brave --user-data-dir={escaped}')+b'\0')
            with self.assertRaisesRegex(RuntimeError,'abierto'):require_closed_profile(profile,root)
            (p/'cmdline').write_bytes(b'brave\0--user-data-dir=/another-profile\0')
            require_closed_profile(profile,root)
            with patch.object(Path,'open',side_effect=FileNotFoundError):require_closed_profile(profile,root)

    def test_deleted_brave_executable_still_blocks_its_live_profile(self):
        from fishing_core.brave import require_closed_profile
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
            root=Path(tmp);p=self.fixture(root)
            (p/'exe').unlink();(p/'exe').symlink_to(root/'brave (deleted)')
            with self.assertRaisesRegex(RuntimeError,'abierto'):
                require_closed_profile(ROOT/'runs/accounts/personal/brave-data',root)


@unittest.skipIf(os.name=='nt','Guarda de ventana Linux')
class BraveGuardTests(unittest.TestCase):
    def env(self):
        return {'FARM_ACCOUNT':'personal','FARM_BACKEND':'gamescope','FARM_GAMESCOPE_DISPLAY':':12',
            'FARM_GAMESCOPE_SERIAL':'4500','FARM_BRAVE_PID':'1234','FARM_BRAVE_CDP_PORT':'45678','FARM_BRAVE_TARGET_ID':'A'*32}

    def window(self):
        d=Mock();w=Mock();w.id=7;w.get_wm_name.return_value='Bit Heroes'
        w.get_wm_class.return_value=(f'brave-browser ({ROOT}/runs/accounts/personal/brave-data)','Brave-browser')
        w.get_geometry.return_value=SimpleNamespace(x=0,y=0,width=1920,height=1080)
        w.get_attributes.return_value=SimpleNamespace(map_state=2)
        w.get_full_property.return_value=SimpleNamespace(value=[1234])
        d.screen().root.get_full_property.return_value=SimpleNamespace(value=[7])
        d.get_input_focus.return_value=SimpleNamespace(focus=SimpleNamespace(id=7))
        return d,w

    def test_guard_checks_pid_class_geometry_focus_and_fixed_account_before_cdp(self):
        from fishing_core.brave import BraveGuard
        with patch.dict(os.environ,self.env(),clear=True),patch('fishing_core.brave.os.pidfd_open',return_value=101), \
                patch('fishing_core.brave.os.close'),patch('fishing_core.brave.select.select',return_value=([],[],[])), \
                patch('fishing_core.brave.browser_identity',return_value=('brave','stamp')),patch('fishing_core.brave.Bridge') as bridge:
            d,w=self.window();w.get_wm_name.side_effect=AssertionError('No leer títulos web para identificar Brave')
            g=BraveGuard(d,w);self.addCleanup(g.close)
            g.check(w);bridge.return_value.call.assert_called_once_with('check')
            for mutate,restore in ((lambda:setattr(w.get_geometry.return_value,'x',1),lambda:setattr(w.get_geometry.return_value,'x',0)),
                (lambda:setattr(w.get_full_property.return_value,'value',[999]),lambda:setattr(w.get_full_property.return_value,'value',[1234])),
                (lambda:setattr(d.get_input_focus.return_value.focus,'id',8),lambda:setattr(d.get_input_focus.return_value.focus,'id',7)),
                (lambda:setattr(w.get_wm_class,'return_value',(f'brave-browser ({ROOT}/runs/accounts/perfil-1/brave-data)','Brave-browser')),
                 lambda:setattr(w.get_wm_class,'return_value',(f'brave-browser ({ROOT}/runs/accounts/personal/brave-data)','Brave-browser'))),
                (lambda:os.environ.update(FARM_BRAVE_TARGET_ID='B'*32),lambda:os.environ.update(FARM_BRAVE_TARGET_ID='A'*32))):
                bridge.return_value.call.reset_mock();mutate()
                with self.assertRaises(RuntimeError):g.check(w)
                bridge.return_value.call.assert_not_called();restore()
            g.close();g.close()

    def test_reused_pid_or_invalid_window_cannot_connect_to_cdp_and_fds_are_closed(self):
        from fishing_core.brave import BraveGuard
        with patch.dict(os.environ,self.env(),clear=True),patch('fishing_core.brave.os.pidfd_open',return_value=101), \
                patch('fishing_core.brave.os.close') as closed,patch('fishing_core.brave.select.select',return_value=([],[],[])), \
                patch('fishing_core.brave.browser_identity',return_value=('brave','first')) as identity,patch('fishing_core.brave.Bridge') as bridge:
            d,w=self.window();w.get_wm_class.return_value=('steam','steam')
            with self.assertRaises(RuntimeError):BraveGuard(d,w)
            bridge.assert_not_called();closed.assert_called_once_with(101)
            w.get_wm_class.return_value=(f'brave-browser ({ROOT}/runs/accounts/personal/brave-data)','Brave-browser');closed.reset_mock()
            g=BraveGuard(d,w);identity.return_value=('brave','reused')
            with self.assertRaises(RuntimeError):g.check(w)
            bridge.return_value.call.assert_not_called();g.close();closed.assert_called_once_with(101)

    def test_a_pid_reused_during_initial_validation_never_opens_cdp(self):
        from fishing_core.brave import BraveGuard
        with patch.dict(os.environ,self.env(),clear=True),patch('fishing_core.brave.os.pidfd_open',return_value=101), \
                patch('fishing_core.brave.os.close') as closed,patch('fishing_core.brave.select.select',return_value=([101],[],[])), \
                patch('fishing_core.brave.browser_identity',return_value=('brave','stamp')),patch('fishing_core.brave.Bridge') as bridge:
            with self.assertRaises(RuntimeError):BraveGuard(*self.window())
            bridge.assert_not_called();closed.assert_called_once_with(101)

class BraveProtocolTests(unittest.TestCase):
    @unittest.skipIf(os.name=='nt','Lanzador multicuenta Linux')
    def test_uncertain_profile_blocks_both_launchers_before_spawning_and_releases_their_lock(self):
        from fishing_core import brave,accounts
        from fishing_core.processes import Mutex
        require_closed=brave.require_closed_profile
        for account in ('personal','perfil-1'):
            with self.subTest(account=account),tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
                root=Path(tmp);proc=root/'proc';p=proc/'123';p.mkdir(parents=True)
                binary=root/'brave';binary.touch();(p/'exe').symlink_to(binary)
                (p/'cmdline').write_bytes(b'brave\0PRIVATE_TEST_MARKER')
                profile=ROOT/'runs/accounts'/account/'brave-data'
                with patch.dict(os.environ,{'FARM_ACCOUNT':account,'FARM_BACKEND':'gamescope','XDG_RUNTIME_DIR':tmp},clear=True), \
                        patch.object(accounts,'prepare_profiles',return_value={account:profile}), \
                        patch.object(brave,'require_closed_profile',side_effect=lambda path:require_closed(path,proc)), \
                        patch.object(brave.subprocess,'Popen') as spawn:
                    with self.assertRaises(RuntimeError) as failure:brave.launch_brave(binary)
                    self.assertNotIn('PRIVATE_TEST_MARKER',str(failure.exception));spawn.assert_not_called()
                    lock=Mutex('BRAVE_CLIENT');lock.close()

    def test_launch_handshake_survives_a_reaper_that_closes_extra_inherited_descriptors(self):
        from fishing_core import brave,accounts
        spawn_real=subprocess.Popen
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
            root=Path(tmp);binary=root/'brave';binary.write_text('#!/bin/sh\nexit 0\n');binary.chmod(0o700)
            process=Mock(pid=123);process.poll.return_value=None
            def spawn(command,**kwargs):
                # Ejecutar solo el bootstrap con un Brave ficticio: sin gamescope, red, captura ni input.
                child=spawn_real(command[command.index('--')+1:],env={**os.environ,'DISPLAY':':12'},
                                 stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,close_fds=True)
                self.assertEqual(child.wait(timeout=5),0)
                return process
            with patch.dict(os.environ,{'FARM_ACCOUNT':'personal','FARM_BACKEND':'gamescope','XDG_RUNTIME_DIR':tmp},clear=True), \
                    patch.object(accounts,'prepare_profiles',return_value={'personal':root/'profile'}), \
                    patch.object(brave,'require_closed_profile'),patch.object(brave.subprocess,'Popen',side_effect=spawn), \
                    patch.object(brave,'browser_identity',return_value=(str(binary),'stamp')), \
                    patch.object(brave,'gamescope_launch_serial',return_value='4501'), \
                    patch.object(brave,'prepare_brave',return_value='A'*32):
                owned,record=brave.launch_brave(binary)
                self.assertIs(owned,process);self.assertEqual(record['FARM_GAMESCOPE_DISPLAY'],':12')

    def test_closed_launcher_returns_only_owned_endpoints_and_cleans_its_process_on_preparation_failure(self):
        from fishing_core import brave,accounts
        from fishing_core.processes import Mutex
        import json
        for failure in (False,True):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
                root=Path(tmp);binary=root/'brave';binary.touch();process=Mock(pid=123);process.poll.return_value=None
                def spawn(command,**kwargs):
                    endpoint=Path(command[command.index('-c')+2]);endpoint.write_text('{"pid":1234,"display":":12"}\n');endpoint.chmod(0o600)
                    self.assertIn('--no-startup-window',command);self.assertIn('--ozone-platform=x11',command)
                    return process
                env={'FARM_ACCOUNT':'personal','FARM_BACKEND':'gamescope','XDG_RUNTIME_DIR':tmp}
                with patch.dict(os.environ,env,clear=True),patch.object(accounts,'prepare_profiles',return_value={'personal':root/'profile'}), \
                        patch.object(brave,'require_closed_profile'),patch.object(brave.subprocess,'Popen',side_effect=spawn), \
                        patch.object(brave,'browser_identity',return_value=(str(binary),'stamp')), \
                        patch.object(brave,'gamescope_launch_serial',return_value='4501'), \
                        patch.object(brave,'prepare_brave',side_effect=RuntimeError('preparación') if failure else None,return_value='A'*32) as prepare:
                    if failure:
                        with self.assertRaisesRegex(RuntimeError,'preparación'):brave.launch_brave(binary)
                        process.terminate.assert_called_once();process.wait.assert_called_once()
                    else:
                        owned,record=brave.launch_brave(binary);self.assertIs(owned,process)
                        self.assertEqual(record,{'FARM_GAMESCOPE_DISPLAY':':12','FARM_GAMESCOPE_SERIAL':'4501',
                                                'FARM_BRAVE_PID':'1234','FARM_BRAVE_CDP_PORT':record['FARM_BRAVE_CDP_PORT'],
                                                'FARM_BRAVE_TARGET_ID':'A'*32})
                        prepare.assert_called_once_with(1234,int(record['FARM_BRAVE_CDP_PORT']))
                        process.terminate.assert_not_called()
                    lock=Mutex('BRAVE_CLIENT');lock.close()  # No queda el lanzamiento bloqueado tras éxito o fallo.
                    self.assertNotIn('FARM_BRAVE_PID',os.environ)

    def test_closed_profile_launcher_requires_an_explicit_brave_account_and_refuses_a_live_profile(self):
        from fishing_core import brave
        for env in ({},{'FARM_ACCOUNT':'steam'},{'FARM_ACCOUNT':'personal','FARM_BACKEND':'desktop'}):
            with patch.dict(os.environ,env,clear=True),patch.object(brave.subprocess,'Popen') as spawn:
                with self.assertRaises((ValueError,RuntimeError)):brave.launch_brave()
                spawn.assert_not_called()
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
            root=Path(tmp);p=root/'123';p.mkdir();exe=root/'brave';exe.touch();(p/'exe').symlink_to(exe)
            profile=ROOT/'runs/accounts/personal/brave-data'
            for command in (f'brave\0--user-data-dir={profile}\0',f'brave --user-data-dir={profile}\0'):
                (p/'cmdline').write_bytes(os.fsencode(command))
                with self.assertRaisesRegex(RuntimeError,'abierto'):brave.require_closed_profile(profile,root)

    def test_launcher_binds_video_to_its_own_gamescope_process_not_the_first_node(self):
        from fishing_core import brave
        import json
        records=[{'id':1,'type':'PipeWire:Interface:Client','info':{'props':{'application.process.id':123}}},
                 {'id':2,'type':'PipeWire:Interface:Client','info':{'props':{'application.process.id':999}}},
                 {'id':3,'type':'PipeWire:Interface:Node','info':{'props':{'client.id':2,'node.name':'gamescope','media.class':'Video/Source','object.serial':4500}}},
                 {'id':4,'type':'PipeWire:Interface:Node','info':{'props':{'client.id':1,'node.name':'gamescope','media.class':'Video/Source','object.serial':4501}}}]
        with patch.object(brave.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps(records))):
            self.assertEqual(brave.gamescope_launch_serial(123),'4501')
            with self.assertRaises(RuntimeError):brave.gamescope_launch_serial(888)
        records.append(records[-1])
        with patch.object(brave.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps(records))):
            with self.assertRaises(RuntimeError):brave.gamescope_launch_serial(123)

    def test_runtime_bridge_never_accepts_the_preparation_switch_or_malformed_endpoints(self):
        from fishing_core.brave import Bridge
        with patch('fishing_core.brave.subprocess.Popen') as start:
            for port,target in ((45678,'--prepare'),(True,'A'*32),(0,'A'*32),(45678,['A'*32])):
                with self.assertRaises(RuntimeError):Bridge(port,target)
            start.assert_not_called()

    @unittest.skipIf(shutil.which('node') is None,'Node no instalado; Brave seguirá bloqueado')
    def test_native_node_protocol_and_geometry_checks(self):
        path=Path(__file__).with_name('brave_cdp.test.mjs')
        result=subprocess.run(['node','--test',str(path)],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)


@unittest.skipIf(os.name=='nt' or shutil.which('node') is None,'Bridge CDP Linux/Node no disponible')
class BraveBridgeTests(unittest.TestCase):
    def server(self):
        """Servidor CDP ficticio en loopback: ningún navegador o juego."""
        import base64
        import hashlib
        import json
        import struct
        import threading
        from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
        target='A'*32
        class Handler(BaseHTTPRequestHandler):
            protocol_version='HTTP/1.1'
            def log_message(self,*args):pass
            def do_GET(self):
                if self.path=='/json/version':
                    url=getattr(self.server,'websocket_url',f'ws://127.0.0.1:{self.server.server_port}/devtools/browser/'+target)
                    body=json.dumps({'webSocketDebuggerUrl':url}).encode()
                    self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body);return
                key=self.headers.get('Sec-WebSocket-Key','')
                accept=base64.b64encode(hashlib.sha1((key+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
                self.send_response(101);self.send_header('Upgrade','websocket');self.send_header('Connection','Upgrade')
                self.send_header('Sec-WebSocket-Accept',accept);self.end_headers();self.wfile.flush()
                while True:
                    header=self.rfile.read(2)
                    if len(header)!=2:break
                    opcode=header[0]&15;length=header[1]&127
                    if length==126:length=struct.unpack('!H',self.rfile.read(2))[0]
                    elif length==127:length=struct.unpack('!Q',self.rfile.read(8))[0]
                    if length>16384:break
                    mask=self.rfile.read(4) if header[1]&128 else b''
                    payload=self.rfile.read(length)
                    if len(payload)!=length:break
                    if mask:payload=bytes(b^mask[i%4] for i,b in enumerate(payload))
                    if opcode==8:
                        self.wfile.write(bytes([136,len(payload)])+payload);self.wfile.flush();self.close_connection=True;break
                    request=json.loads(payload);method=request['method'];self.server.commands.append(request)
                    if method=='Input.dispatchKeyEvent' and request['params']['type']=='rawKeyDown':
                        self.server.key_down.set();self.server.allow_key_down_reply.wait(3)
                    replies={'Target.attachToTarget':{'sessionId':'own'},'Target.setAutoAttach':{},
                        'Target.getTargets':{'targetInfos':[{'targetId':target,'type':'page',
                            'url':'https://www.kongregate.com/en/games/Juppiomenz/bit-heroes?test=PRIVATE_TEST_MARKER',
                            'title':'PRIVATE_TEST_MARKER'}]},
                        'Browser.getWindowForTarget':{'windowId':4,'bounds':{'left':0,'top':0,'width':1920,'height':1080}},
                        'Page.getFrameTree':{'frameTree':{'frame':{'id':'frame','loaderId':'loader'}}},
                        'Page.createIsolatedWorld':{'executionContextId':7},
                        'Runtime.evaluate':{'result':{'value':self.server.point_hit if request.get('params',{}).get('expression','').startswith('document.elementFromPoint') else self.server.geometry}},
                        'Input.dispatchKeyEvent':{}}
                    response={'id':request['id'],'result':self.server.reply(request) if getattr(self.server,'reply',None) else replies[method]}
                    body=json.dumps(response).encode();prefix=bytes([129,len(body)]) if len(body)<126 else bytes([129,126])+struct.pack('!H',len(body))
                    self.wfile.write(prefix+body);self.wfile.flush()
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True;server.commands=[]
        server.point_hit=True;server.key_down=threading.Event();server.allow_key_down_reply=threading.Event();server.allow_key_down_reply.set()
        server.geometry={'size':[1920,1080],'dpr':1,'visual':[0,0,1920,1080,1],'scroll':[0,0],
            'focused':True,'visible':True,'brave':True,'activeTag':'CANVAS',
            'canvases':[{'size':[1920,1080],'rect':[0,0,1920,1080],'visible':True}]}
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        return server,target

    def test_native_websocket_pipe_and_eof_release_escape_without_closing_the_browser(self):
        from fishing_core.brave import Bridge
        server,target=self.server();bridge=Bridge(server.server_port,target);self.addCleanup(bridge.close)
        bridge.call('check');bridge.call('escapeDown');bridge.close()
        keys=[r for r in server.commands if r['method']=='Input.dispatchKeyEvent']
        self.assertEqual([r['params']['type'] for r in keys],['rawKeyDown','keyUp'])
        self.assertTrue(all(r['sessionId']=='own' and 'nativeVirtualKeyCode' not in r['params'] for r in keys))
        self.assertFalse(any(r['method']=='Browser.close' for r in server.commands))
        self.assertEqual(bridge.process.returncode,0);self.assertTrue(bridge.process.stdout.closed)

    def test_bad_geometry_never_produces_input_or_discloses_cdp_fields(self):
        from fishing_core.brave import Bridge
        server,target=self.server();server.geometry['size']=[1920,1024]
        bridge=Bridge(server.server_port,target);self.addCleanup(bridge.close)
        with self.assertRaises(RuntimeError) as failure:bridge.call('check')
        self.assertNotIn('PRIVATE_TEST_MARKER',str(failure.exception));bridge.close()
        self.assertFalse(any(r['method']=='Input.dispatchKeyEvent' for r in server.commands))

    def test_point_command_crosses_the_real_pipe_and_websocket_and_rejects_an_overlay(self):
        from fishing_core.brave import Bridge
        server,target=self.server();bridge=Bridge(server.server_port,target);self.addCleanup(bridge.close)
        bridge.call('check');bridge.call('point',(10,20));server.point_hit=False
        with self.assertRaises(RuntimeError):bridge.call('point',(10,20))
        bridge.close();self.assertEqual(bridge.process.returncode,0)
        self.assertFalse(any(r['method']=='Input.dispatchKeyEvent' for r in server.commands))

    def test_disappearing_parent_during_escape_reply_still_releases_the_original_key(self):
        from fishing_core.brave import Bridge
        server,target=self.server();bridge=Bridge(server.server_port,target);self.addCleanup(bridge.close)
        bridge.call('check');server.allow_key_down_reply.clear()
        bridge.process.stdin.write(b'{"id":2,"op":"escapeDown"}\n')
        try:
            self.assertTrue(server.key_down.wait(3),'El transporte ficticio no recibió Escape')
            bridge.process.stdin.close();bridge.process.stdout.close()
        finally:server.allow_key_down_reply.set()
        bridge.process.wait(timeout=5)
        self.assertEqual(bridge.process.returncode,0)
        self.assertEqual([r['params']['type'] for r in server.commands if r['method']=='Input.dispatchKeyEvent'],['rawKeyDown','keyUp'])

    def test_a_cdp_advertised_url_cannot_redirect_to_another_socket_or_leak_its_query(self):
        from fishing_core.brave import Bridge
        server,target=self.server();url=f'ws://127.0.0.1:{server.server_port}/devtools/browser/{target}'
        for bad in (url.replace('127.0.0.1','127.0.0.2'),url+'?private=PRIVATE_TEST_MARKER',
                    url.replace('/browser/','/page/'),url.replace('ws:','https:')):
            with self.subTest(kind=bad.split('/')[0]):
                server.websocket_url=bad
                with self.assertRaises(RuntimeError) as failure:Bridge(server.server_port,target)
                self.assertNotIn('PRIVATE_TEST_MARKER',str(failure.exception))
        self.assertEqual(server.commands,[])

@unittest.skipIf(os.name=='nt' or shutil.which('node') is None,'Preparación CDP Linux/Node no disponible')
class BraveStartupTests(unittest.TestCase):
    def server(self,bad_geometry=False):
        server,old=BraveBridgeTests.server(self);fresh='B'*32
        pages=[{'type':'page','targetId':old,'url':'https://www.kongregate.com/en/games/Juppiomenz/bit-heroes'}]
        server.geometry.update(canvases=[],size=[1920,1024] if bad_geometry else [1920,1080])
        def reply(request):
            method=request['method'];params=request.get('params',{})
            if method=='Target.getTargets':return {'targetInfos':list(pages)}
            if method=='Target.createTarget':
                pages.append({'type':'page','targetId':fresh,'url':'about:blank'});return {'targetId':fresh}
            if method=='Target.closeTarget':
                self.assertEqual(params['targetId'],old);pages[:]=[t for t in pages if t['targetId']!=old];return {'success':True}
            if method=='Target.attachToTarget':return {'sessionId':'own'}
            if method in ('Target.setAutoAttach','Target.activateTarget','Browser.setWindowBounds'):return {}
            if method=='Browser.getWindowForTarget':return {'windowId':4,'bounds':{'left':0,'top':0,'width':1920,'height':1080}}
            if method=='Page.getFrameTree':return {'frameTree':{'frame':{'id':'blank','loaderId':'loader','url':pages[0]['url']}}}
            if method=='Page.createIsolatedWorld':return {'executionContextId':7}
            if method=='Runtime.evaluate':
                expression=params['expression']
                if '#gtm-play-now-button' in expression:return {'result':{'value':'clicked'}}
                if '#fullscreen_button' in expression:return {'result':{'value':[60,35]}}
                if expression.startswith("location.href===") or expression.startswith("(()=>{const c=document.querySelector('canvas')"):
                    return {'result':{'value':True}}
                return {'result':{'value':server.geometry}}
            if method=='Page.navigate':
                self.assertEqual(len(pages),1);self.assertEqual(pages[0]['url'],'about:blank')
                pages[0]['url']=params['url'];server.geometry.update(activeTag='CANVAS',canvases=[{'size':[1920,1080],'rect':[0,0,1920,1080],'visible':True}])
                return {'frameId':'blank'}
            if method=='Input.synthesizeTapGesture':
                self.assertEqual(params,{'x':60,'y':35,'gestureSourceType':'mouse','tapCount':1})
                self.assertEqual(request.get('sessionId'),'own');return {}
            raise AssertionError('Comando de preparación inesperado')
        server.reply=reply;return server,fresh

    def test_explicit_preparation_crosses_native_transport_only_after_verifying_the_owned_process(self):
        from fishing_core.brave import prepare_brave
        server,target=self.server();fd,write=os.pipe();self.addCleanup(os.close,write)
        with patch.dict(os.environ,{'FARM_ACCOUNT':'perfil-1'},clear=True), \
                patch('fishing_core.brave.os.pidfd_open',return_value=fd), \
                patch('fishing_core.brave.browser_identity',return_value=('brave','stamp')) as identity:
            self.assertEqual(prepare_brave(1234,server.server_port),target)
            self.assertTrue(all(call.args==(1234,server.server_port,'perfil-1') for call in identity.call_args_list))
            self.assertGreaterEqual(identity.call_count,2)
        with self.assertRaises(OSError):os.fstat(fd)
        self.assertEqual(sum(r['method']=='Page.navigate' for r in server.commands),1)
        self.assertFalse(any(r['method']=='Browser.close' for r in server.commands))
        self.assertEqual([r['method'] for r in server.commands if r['method'].startswith('Input.')],['Input.synthesizeTapGesture'])

    def test_preparation_failure_closes_only_its_adapter_without_navigating_or_exposing_data(self):
        from fishing_core.brave import prepare_brave
        server,_=self.server(bad_geometry=True);fd,write=os.pipe();self.addCleanup(os.close,write)
        with patch.dict(os.environ,{'FARM_ACCOUNT':'personal'},clear=True), \
                patch('fishing_core.brave.os.pidfd_open',return_value=fd), \
                patch('fishing_core.brave.browser_identity',return_value=('brave','stamp')):
            with self.assertRaises(RuntimeError) as failure:prepare_brave(1234,server.server_port)
        self.assertNotIn('PRIVATE_TEST_MARKER',str(failure.exception))
        self.assertFalse(any(r['method']=='Page.navigate' or r['method']=='Browser.close' for r in server.commands))
        with self.assertRaises(OSError):os.fstat(fd)

    def test_steam_invalid_profile_and_dead_pid_never_start_an_adapter(self):
        from fishing_core.brave import prepare_brave
        with patch('fishing_core.brave.subprocess.Popen') as start:
            for account in ('steam',None):
                with patch.dict(os.environ,{} if account is None else {'FARM_ACCOUNT':account},clear=True),self.assertRaises(RuntimeError):
                    prepare_brave(1234,45678)
            for dead in (False,True):
                fd,write=os.pipe()
                if dead:os.close(write)
                try:
                    with patch.dict(os.environ,{'FARM_ACCOUNT':'personal'},clear=True), \
                            patch('fishing_core.brave.os.pidfd_open',return_value=fd), \
                            patch('fishing_core.brave.browser_identity',side_effect=None if dead else RuntimeError('PRIVATE_TEST_MARKER')):
                        with self.assertRaises(RuntimeError) as failure:prepare_brave(1234,45678)
                        self.assertNotIn('PRIVATE_TEST_MARKER',str(failure.exception))
                finally:
                    if not dead:os.close(write)
            start.assert_not_called()

    def test_an_identity_changed_during_preparation_cannot_be_returned_as_ready(self):
        from fishing_core.brave import prepare_brave
        server,_=self.server();fd,write=os.pipe();self.addCleanup(os.close,write)
        with patch.dict(os.environ,{'FARM_ACCOUNT':'personal'},clear=True), \
                patch('fishing_core.brave.os.pidfd_open',return_value=fd), \
                patch('fishing_core.brave.browser_identity',side_effect=[('brave','first'),('brave','reused')]):
            with self.assertRaises(RuntimeError):prepare_brave(1234,server.server_port)
        with self.assertRaises(OSError):os.fstat(fd)

    def test_parent_eof_before_preparation_cancels_before_creating_or_loading_a_page(self):
        import json
        server,_=self.server()
        result=subprocess.run(['node',str(ROOT/'fishing_core/brave_cdp.mjs'),str(server.server_port),'--prepare'],
            input='',capture_output=True,text=True,timeout=8,env={'PATH':os.defpath,'LANG':'C.UTF-8'})
        self.assertEqual(result.returncode,0);self.assertEqual(json.loads(result.stdout),{'id':0,'ok':False,'stage':'connection'})
        self.assertEqual(server.commands,[]);self.assertEqual(result.stderr,'')

    def test_failed_play_reports_a_fixed_stage_over_the_native_transport_without_web_data(self):
        import json
        from fishing_core.brave import prepare_brave
        server,_=self.server();reply=server.reply
        def fail_play(request):
            if request['method']=='Runtime.evaluate' and '#gtm-play-now-button' in request['params']['expression']:
                return {'exceptionDetails':{'text':'PRIVATE_TEST_MARKER'}}
            return reply(request)
        server.reply=fail_play
        with subprocess.Popen(['node',str(ROOT/'fishing_core/brave_cdp.mjs'),str(server.server_port),'--prepare'],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                env={'PATH':os.defpath,'LANG':'C.UTF-8'}) as proc:
            result=proc.stdout.readline();proc.stdin.close();proc.wait(timeout=8)
            self.assertEqual(json.loads(result),{'id':0,'ok':False,'stage':'play'})
            self.assertEqual(proc.stdout.read(),'');self.assertEqual(proc.stderr.read(),'')
        server,_=self.server();reply=server.reply;server.reply=fail_play
        # El segundo transporte usa el mismo fallo ficticio; no conecta a ningún navegador.
        fd,write=os.pipe();self.addCleanup(os.close,write)
        with patch.dict(os.environ,{'FARM_ACCOUNT':'personal'},clear=True), \
                patch('fishing_core.brave.os.pidfd_open',return_value=fd), \
                patch('fishing_core.brave.browser_identity',return_value=('brave','stamp')):
            with self.assertRaisesRegex(RuntimeError,'etapa: Play') as failure:prepare_brave(1234,server.server_port)
        self.assertNotIn('PRIVATE_TEST_MARKER',str(failure.exception))
        self.assertFalse(any(r['method']=='Browser.close' or r['method'].startswith('Input.') for r in server.commands))

    def test_untrusted_or_malformed_stage_replies_are_not_echoed_or_accepted_as_ready(self):
        import json
        from fishing_core.brave import prepare_brave
        for fields,tail in (({'stage':'PRIVATE_TEST_MARKER'},''),({'stage':['PRIVATE_TEST_MARKER']},''),
                ({'stage':'play','id':False},''),({'stage':'play','details':'PRIVATE_TEST_MARKER'},''),
                ({'stage':'play'},'PRIVATE_TEST_MARKER')):
            reply={'id':0,'ok':False,**fields};proc=Mock();proc.returncode=0
            fd,write=os.pipe()
            try:
                with patch.dict(os.environ,{'FARM_ACCOUNT':'personal'},clear=True), \
                        patch('fishing_core.brave.os.pidfd_open',return_value=fd), \
                        patch('fishing_core.brave.browser_identity',return_value=('brave','stamp')), \
                        patch('fishing_core.brave.subprocess.Popen',return_value=proc), \
                        patch('fishing_core.brave.select.select',side_effect=lambda readers,*args:
                            ([proc.stdout] if proc.stdout in readers else [],[],[])), \
                        patch('fishing_core.brave.os.read',return_value=(json.dumps(reply)+'\n'+tail).encode()):
                    with self.assertRaises(RuntimeError) as failure:prepare_brave(1234,45678)
                self.assertNotIn('PRIVATE_TEST_MARKER',str(failure.exception))
                self.assertNotIn('etapa:',str(failure.exception))
                proc.stdin.close.assert_called();proc.stdout.close.assert_called()
            finally:os.close(write)

if __name__=='__main__':unittest.main()
