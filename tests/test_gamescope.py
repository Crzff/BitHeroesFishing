"""Backend gamescope sin juego: búsqueda del nodo PipeWire, recorte de fotogramas y guardas."""

import time
import os
import shutil
import signal
import subprocess
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from fishing_core import gamescope
from fishing_core.control_flow import SafetyStop

PW="""	id 98, type PipeWire:Interface:Node/3
 		object.serial = "4441"
 		node.name = "gamescope"
 		media.class = "Video/Source"
	id 99, type PipeWire:Interface:Node/3
 		object.serial = "4500"
 		node.name = "otro"
 		media.class = "Audio/Sink"
"""


class GamescopeTests(unittest.TestCase):
    def test_direct_frame_server_refuses_legacy_steam_files_before_opening_any_stream(self):
        for existing in ('frame','pid','symlink'):
            with self.subTest(existing=existing),tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
                source=Path(tmp)/'legacy-frame'
                if existing=='frame':source.write_bytes(b'keep')
                elif existing=='pid':Path(str(source)+'.pid').write_text('123')
                else:source.symlink_to(source.with_name('missing'))
                with patch.dict(os.environ,{**self.account_env(),'XDG_RUNTIME_DIR':tmp},clear=True), \
                        patch.object(gamescope,'LEGACY_SHM',str(source)),patch.object(gamescope,'SHM',str(Path(tmp)/'new-frame')), \
                        patch.object(gamescope,'pipewire_serial',return_value='4500') as serial, \
                        patch.object(gamescope,'PipeWireFrames') as stream:
                    server=None
                    try:
                        with self.assertRaisesRegex(RuntimeError,'antiguo'):server=gamescope.FrameServer()
                    finally:
                        if server is not None:server.close()
                    serial.assert_not_called();stream.assert_not_called()
                    self.assertFalse((Path(tmp)/'new-frame').exists())
                if existing=='frame':self.assertEqual(source.read_bytes(),b'keep')
                elif existing=='pid':self.assertEqual(Path(str(source)+'.pid').read_text(),'123')
                else:self.assertTrue(source.is_symlink())

    def test_legacy_steam_frames_require_owned_project_server_matching_child_and_memory(self):
        import sys
        from fishing_core.telemetry import ROOT
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
            root=Path(tmp);frame=root/'legacy-frame'
            with frame.open('wb') as stream:stream.truncate(gamescope.HEADER+gamescope.FRAME)
            frame.chmod(0o600);Path(str(frame)+'.pid').write_text('123');Path(str(frame)+'.pid').chmod(0o600)
            proc=root/'proc';server=proc/'123';child=proc/'124';server.mkdir(parents=True);child.mkdir()
            (server/'cwd').symlink_to(ROOT);(server/'exe').symlink_to(Path(sys.executable).resolve())
            (server/'cmdline').write_bytes(b'python\0-B\0-m\0fishing_core.gamescope\0serve\0')
            (server/'fd').mkdir();(server/'fd/3').symlink_to(frame)
            (server/'task/123').mkdir(parents=True);(server/'task/123/children').write_text('124')
            gst=root/'gst-launch-1.0';gst.touch();(child/'exe').symlink_to(gst)
            good=b'gst-launch-1.0\0pipewiresrc\0target-object=4500\0'
            (child/'cmdline').write_bytes(good)
            with patch.dict(os.environ,self.account_env(),clear=True),patch.object(gamescope,'LEGACY_SHM',str(frame)):
                self.assertTrue(gamescope.legacy_steam_frames(proc))
                for bad in (good.replace(b'4500',b'4501'),good+b'target-object=4500\0'):
                    (child/'cmdline').write_bytes(bad);self.assertFalse(gamescope.legacy_steam_frames(proc))
                (child/'cmdline').write_bytes(good);frame.chmod(0o644)
                self.assertFalse(gamescope.legacy_steam_frames(proc));frame.chmod(0o600)
                (server/'cmdline').write_bytes(b'python\0-c\0unrelated\0')
                self.assertFalse(gamescope.legacy_steam_frames(proc))

    def test_farming_and_observation_share_only_the_verified_legacy_steam_source(self):
        for read_only in (False,True):
            with self.subTest(read_only=read_only),tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp, \
                    patch.dict(os.environ,self.account_env(),clear=True),patch.object(gamescope,'LEGACY_SHM',str(Path(tmp)/'legacy')), \
                    patch.object(gamescope,'server_alive',return_value=False), \
                    patch.object(gamescope,'legacy_steam_frames',return_value=True), \
                    patch.object(gamescope,'SharedFrames') as frames,patch.object(gamescope,'PipeWireFrames') as stream:
                cap=gamescope.GamescopeCapture(SimpleNamespace(read_only=read_only))
                frames.assert_called_once_with(gamescope.LEGACY_SHM);stream.assert_not_called();cap.close()

    def test_two_steam_sources_or_uncertain_legacy_remains_block_capture_without_opening_streams(self):
        for verified in (False,True):
            with self.subTest(verified=verified),tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
                source=Path(tmp)/'legacy';source.touch()
                with patch.dict(os.environ,self.account_env(),clear=True),patch.object(gamescope,'LEGACY_SHM',str(source)), \
                        patch.object(gamescope,'server_alive',return_value=True), \
                        patch.object(gamescope,'legacy_steam_frames',return_value=verified), \
                        patch.object(gamescope,'SharedFrames') as frames,patch.object(gamescope,'PipeWireFrames') as stream:
                    with self.assertRaises(RuntimeError):gamescope.GamescopeCapture(SimpleNamespace(read_only=False))
                    frames.assert_not_called();stream.assert_not_called();self.assertTrue(source.exists())

    def test_finds_the_gamescope_video_node_and_rejects_its_absence(self):
        with patch('fishing_core.gamescope.subprocess.run',return_value=SimpleNamespace(stdout=PW)):
            self.assertEqual(gamescope.pipewire_serial(),'4441')
        with patch('fishing_core.gamescope.subprocess.run',return_value=SimpleNamespace(stdout=PW.replace('gamescope','x'))):
            with self.assertRaises(RuntimeError):gamescope.pipewire_serial()

    def capture(self,frame,check=None):
        cap=gamescope.GamescopeCapture.__new__(gamescope.GamescopeCapture)
        cap.guard=SimpleNamespace(check=check or (lambda:None))
        cap.frames=SimpleNamespace(frame=lambda newer_than:frame)
        return cap

    def test_grab_crops_the_latest_frame_as_bgra(self):
        frame=np.zeros((1080,1920,3),np.uint8);frame[10,20]=(1,2,3)
        shot=self.capture(frame).grab({'left':20,'top':10,'width':4,'height':2})
        pixels=np.frombuffer(shot.bgra,np.uint8).reshape(2,4,4)
        self.assertEqual(tuple(pixels[0,0]),(1,2,3,255))

    def test_grab_refuses_regions_outside_the_game_and_a_lost_window(self):
        frame=np.zeros((1080,1920,3),np.uint8)
        with self.assertRaises(SafetyStop):self.capture(frame).grab({'left':1900,'top':0,'width':40,'height':10})
        def gone():raise RuntimeError('La ventana de Bit Heroes desapareció de gamescope')
        with self.assertRaises(SafetyStop):self.capture(frame,gone).grab({'left':0,'top':0,'width':10,'height':10})

    def frames(self,latest,alive=True):
        frames=gamescope.PipeWireFrames.__new__(gamescope.PipeWireFrames)
        frames.lock=__import__('threading').Lock();frames.latest=latest;frames.stamp=time.monotonic()-5;frames.error=None
        frames.proc=SimpleNamespace(poll=lambda:None if alive else 1)
        return frames

    def test_a_still_screen_reuses_the_last_frame_only_while_the_stream_is_alive(self):
        self.assertEqual(self.frames(bytes(gamescope.FRAME)).frame(time.monotonic(),timeout=0.05).shape,(1080,1920,3))
        with self.assertRaises(RuntimeError):self.frames(bytes(gamescope.FRAME),alive=False).frame(time.monotonic(),timeout=0.05)

    def test_no_frame_at_all_is_an_error(self):
        with self.assertRaises(RuntimeError):self.frames(None).frame(time.monotonic(),timeout=0.01)

    def test_pipewire_close_uses_eos_and_reaps_the_reader_even_after_a_forced_exit(self):
        for timeouts in range(3):
            with self.subTest(timeouts=timeouts):
                frames=self.frames(None);frames.proc=Mock();frames.proc.poll.return_value=None;frames.thread=Mock()
                frames.thread.is_alive.return_value=False
                frames.proc.wait.side_effect=[subprocess.TimeoutExpired('gst-launch-1.0',2)]*timeouts+[0]
                frames.close()
                frames.proc.send_signal.assert_called_once_with(signal.SIGINT)
                self.assertEqual(frames.proc.terminate.call_count,int(timeouts>0))
                self.assertEqual(frames.proc.kill.call_count,int(timeouts>1))
                self.assertEqual(frames.proc.wait.call_count,timeouts+1)
                frames.thread.join.assert_called_once()
                frames.proc.stdout.close.assert_called_once()

    def test_pipewire_close_also_releases_an_already_dead_reader(self):
        frames=self.frames(None,alive=False);frames.proc=Mock();frames.proc.poll.return_value=1;frames.thread=Mock()
        frames.thread.is_alive.return_value=False
        frames.close()
        frames.proc.send_signal.assert_not_called();frames.proc.terminate.assert_not_called();frames.proc.kill.assert_not_called()
        frames.proc.wait.assert_called_once();frames.thread.join.assert_called_once();frames.proc.stdout.close.assert_called_once()

    @unittest.skipIf(os.name=='nt' or shutil.which('gst-launch-1.0') is None,'GStreamer Linux no instalado')
    def test_synthetic_gstreamer_stream_closes_cleanly_without_a_window_or_pipewire(self):
        spawn=subprocess.Popen
        def synthetic(command,**kwargs):
            start=command.index('pipewiresrc');end=command.index('!',start)
            return spawn(command[:start]+['videotestsrc','is-live=true','pattern=black']+command[end:],**kwargs)
        with patch.object(gamescope.subprocess,'Popen',side_effect=synthetic):frames=gamescope.PipeWireFrames('4500')
        try:
            self.assertEqual(frames.frame(time.monotonic(),timeout=2).shape,(1080,1920,3))
            frames.close();frames.close()  # idempotente, incluido el hilo y stdout
            self.assertEqual(frames.proc.returncode,0)
            self.assertFalse(frames.thread.is_alive());self.assertTrue(frames.proc.stdout.closed)
        finally:
            if frames.proc.poll() is None:frames.proc.kill()
            frames.proc.wait(timeout=2);frames.thread.join(timeout=2);frames.proc.stdout.close()

    def test_io_rejects_coordinates_outside_and_checks_f8_and_window_first(self):
        io=gamescope.GamescopeIO.__new__(gamescope.GamescopeIO);io.control_mode=False
        io.game_guard=SimpleNamespace(desktop=Mock(),check=Mock(),display=Mock())
        with self.assertRaises(SafetyStop):io._move((1920,10))
        io.game_guard.desktop.emergency.side_effect=KeyboardInterrupt('F8')
        with self.assertRaises(KeyboardInterrupt):io.click((10,10))
        io.game_guard.display.sync.assert_not_called()

    def guard(self,focused,cls):
        g=gamescope.GamescopeGuard.__new__(gamescope.GamescopeGuard)
        g.window=SimpleNamespace(id=1);state={'focused':focused,'closed':0}
        other=Mock();other.get_wm_class.return_value=cls
        def send(message):state['closed']+=1;state['focused']=1
        other.send_event.side_effect=send
        g.display=Mock();g.display.create_resource_object.return_value=other;g.display.intern_atom.return_value=7
        g.focused=lambda:state['focused']
        return g,state

    def test_a_steam_window_over_the_game_is_closed_and_anything_else_stops(self):
        with patch('fishing_core.gamescope.window_of',return_value=SimpleNamespace(id=1)),patch('fishing_core.gamescope.time.sleep'), \
                patch('Xlib.protocol.event.ClientMessage'):
            g,state=self.guard(2,('steamwebhelper','steam'));g.check();self.assertEqual(state['closed'],1)
            g,state=self.guard(2,('otra','app'))
            with self.assertRaises(RuntimeError):g.check()
            self.assertEqual(state['closed'],0)
            g,state=self.guard(1,None);g.check();self.assertEqual(state['closed'],0)

    def test_shared_frames_read_the_latest_published_frame_and_detect_a_dead_server(self):
        import os,struct,tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path=os.path.join(tmp,'frame')
            with open(path,'wb') as f:
                frame=np.zeros((1080,1920,3),np.uint8);frame[5,6]=(9,8,7)
                f.write(struct.pack('<Qd',3,time.time())+frame.tobytes())
            with patch.object(gamescope,'SHM',path):
                reader=gamescope.SharedFrames()
                try:
                    with patch('fishing_core.gamescope.server_alive',return_value=True):
                        self.assertEqual(tuple(reader.frame(time.monotonic(),timeout=0.05)[5,6]),(9,8,7))
                    with patch('fishing_core.gamescope.server_alive',return_value=False):
                        with self.assertRaises(RuntimeError):reader.frame(time.monotonic(),timeout=0)
                finally:reader.close()
            with open(path,'r+b') as f:f.write(struct.pack('<Qd',0,0.0))
            with patch.object(gamescope,'SHM',path):
                reader=gamescope.SharedFrames()
                try:
                    with patch('fishing_core.gamescope.server_alive',return_value=False):
                        with self.assertRaises(RuntimeError):reader.frame(time.monotonic(),timeout=0.01)
                finally:reader.close()

    def test_backend_selection(self):
        with patch.dict('os.environ',{'FARM_BACKEND':'gamescope'}):
            self.assertIs(gamescope.backend()[0],gamescope.GamescopeIO)
        with patch.dict('os.environ',{'FARM_BACKEND':''}):
            self.assertEqual(gamescope.backend()[0].__name__,'LinuxIO')

    def test_brave_input_opt_in_is_limited_and_requires_complete_live_identity(self):
        env={**self.account_env(),'FARM_ACCOUNT':'personal','FARM_BRAVE_PID':'1234',
             'FARM_BRAVE_CDP_PORT':'45678','FARM_BRAVE_TARGET_ID':'A'*32}
        with patch.dict(os.environ,env,clear=True),patch('fishing_core.brave.browser_identity',return_value=('brave','stamp')) as identity:
            with self.assertRaises(ValueError):gamescope.backend()
            identity.assert_not_called();os.environ['FARM_SINGLE_DUNGEON']='1'
            self.assertIs(gamescope.backend()[0],gamescope.GamescopeIO)
            identity.assert_called_once_with(1234,45678,'personal')
            identity.side_effect=RuntimeError('Brave no confirmado')
            with self.assertRaises(RuntimeError):gamescope.backend()
            identity.reset_mock();del os.environ['FARM_BRAVE_TARGET_ID']
            with self.assertRaises(ValueError):gamescope.backend()
            identity.assert_not_called()

    def test_read_only_backend_initializes_guards_but_blocks_every_input_method(self):
        env={**self.account_env('personal'),'FARM_BRAVE_PID':'1234','FARM_BRAVE_CDP_PORT':'45678','FARM_BRAVE_TARGET_ID':'A'*32}
        with patch.dict(os.environ,env,clear=True),patch.object(gamescope,'GamescopeGuard') as guard, \
                patch('Xlib.ext.xtest.fake_input') as native:
            factory,_=gamescope.backend(read_only=True);io=factory()
            guard.assert_called_once_with(read_only=True)
            for action,args in ((io._move,((10,20),)),(io.click,((10,20),)),(io.cast_click,((10,20),)),
                                (io.wheel,(1,)),(io.escape,())):
                with self.assertRaisesRegex(SafetyStop,'observación'):action(*args)
            native.assert_not_called();guard.return_value.web.key.assert_not_called();io.close()
            with self.assertRaises(ValueError):gamescope.backend()

    def test_read_only_guard_never_closes_a_steam_popup_or_restores_focus(self):
        guard,_=self.guard(2,('steamwebhelper','steam'));guard.read_only=True;guard.restore_focus=Mock()
        with patch.object(gamescope,'window_of',return_value=SimpleNamespace(id=1)):
            with self.assertRaises(RuntimeError):guard.check()
            guard.restore_focus.assert_not_called()

    def test_direct_focus_restore_is_also_inert_in_observation_mode(self):
        guard,state=self.guard(2,('steamwebhelper','steam'));guard.read_only=True
        with patch.object(gamescope.time,'sleep'),patch('Xlib.protocol.event.ClientMessage') as message:
            self.assertFalse(guard.restore_focus())
        self.assertEqual(state,{'focused':2,'closed':0});message.assert_not_called()

    def test_shared_frames_refuse_truncation_replacement_or_symlink_before_reading_memory(self):
        import struct
        class Unreadable:
            def __getitem__(self,key):raise AssertionError('Se leyó la memoria modificada')
        for change in ('truncate','replace','symlink'):
            with self.subTest(change=change),tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
                path=Path(tmp)/'frame';path.write_bytes(struct.pack('<Qd',3,time.time())+bytes(gamescope.FRAME))
                with patch.object(gamescope,'SHM',str(path)),patch.object(gamescope,'server_alive',return_value=True):
                    reader=gamescope.SharedFrames()
                    try:
                        if change=='truncate':
                            with path.open('r+b') as stream:stream.truncate(0)
                        else:
                            previous=path.with_name('previous');path.rename(previous)
                            if change=='replace':path.write_bytes(previous.read_bytes())
                            else:path.symlink_to(previous)
                        with patch.object(reader,'map',Unreadable()),self.assertRaisesRegex(RuntimeError,'memoria de imagen'):
                            reader.frame(time.monotonic(),timeout=0)
                    finally:reader.close()

    def test_read_only_backend_still_requires_an_explicit_gamescope_account(self):
        for env in ({},{'FARM_BACKEND':'gamescope'},{'FARM_ACCOUNT':'personal'}):
            with patch.dict(os.environ,env,clear=True),self.assertRaises(ValueError):gamescope.backend(read_only=True)

    def account_env(self,account='steam'):
        return {'FARM_ACCOUNT':account,'FARM_BACKEND':'gamescope',
                'FARM_GAMESCOPE_DISPLAY':':12','FARM_GAMESCOPE_SERIAL':'4500'}

    def test_account_selects_exact_video_serial_and_legacy_refuses_ambiguous_nodes(self):
        nodes=PW+PW.replace('4441','4500')
        with patch.dict(os.environ,self.account_env(),clear=True),patch.object(gamescope.subprocess,'run',return_value=SimpleNamespace(stdout=nodes)):
            self.assertEqual(gamescope.pipewire_serial(),'4500')
        with patch.dict(os.environ,{},clear=True),patch.object(gamescope.subprocess,'run',return_value=SimpleNamespace(stdout=nodes)):
            with self.assertRaises(RuntimeError):gamescope.pipewire_serial()
        with patch.dict(os.environ,self.account_env(),clear=True),patch.object(gamescope.subprocess,'run',return_value=SimpleNamespace(stdout=PW)):
            with self.assertRaises(RuntimeError):gamescope.pipewire_serial()

    def test_account_opens_only_its_explicit_display_and_never_falls_back(self):
        connection=Mock()
        with patch.dict(os.environ,self.account_env(),clear=True),patch('Xlib.display.Display',return_value=connection) as open_display, \
                patch.object(gamescope.os,'listdir') as scan,patch.object(gamescope,'window_of',return_value=SimpleNamespace(id=7)):
            self.assertIs(gamescope.find_display(),connection)
            open_display.assert_called_once_with(':12');scan.assert_not_called()
        connection.reset_mock()
        with patch.dict(os.environ,self.account_env(),clear=True),patch('Xlib.display.Display',return_value=connection) as open_display, \
                patch.object(gamescope.os,'listdir') as scan,patch.object(gamescope,'window_of',return_value=None):
            with self.assertRaises(RuntimeError):gamescope.find_display()
            open_display.assert_called_once_with(':12');scan.assert_not_called();connection.close.assert_called_once()

    def test_missing_endpoints_and_uncalibrated_brave_cannot_start_a_backend(self):
        with patch.dict(os.environ,{'FARM_ACCOUNT':'steam'},clear=True):
            with self.assertRaises(ValueError):gamescope.backend()
        for account in ('personal','perfil-1'):
            env={**self.account_env(account),'FARM_BRAVE_PID':'1234','FARM_BRAVE_CDP_PORT':'45678','FARM_BRAVE_TARGET_ID':'A'*32}
            with patch.dict(os.environ,env,clear=True),patch('Xlib.display.Display') as connect:
                with self.assertRaises(ValueError):gamescope.backend()
                with self.assertRaises(ValueError):gamescope.GamescopeGuard()
                connect.assert_not_called()

    def test_account_capture_never_opens_a_fallback_stream_without_its_frame_server(self):
        with patch.dict(os.environ,self.account_env(),clear=True),patch.object(gamescope,'server_alive',return_value=False), \
                patch.object(gamescope,'PipeWireFrames') as stream,patch.object(gamescope,'pipewire_serial',return_value='4500'):
            with self.assertRaises(RuntimeError):gamescope.GamescopeCapture(Mock())
            stream.assert_not_called()

    def test_account_relaunch_never_shuts_down_steam_or_starts_a_game(self):
        for account in ('steam','personal','perfil-1'):
            with patch.dict(os.environ,self.account_env(account),clear=True), \
                    patch.object(gamescope.subprocess,'run') as command,patch.object(gamescope.subprocess,'Popen') as spawn, \
                    patch.object(gamescope,'find_display') as find:
                with self.assertRaises(RuntimeError):gamescope.relaunch_game(timeout=0)
                command.assert_not_called();spawn.assert_not_called();find.assert_not_called()

    def test_replaced_game_window_stops_before_any_input(self):
        guard,_=self.guard(1,None)
        with patch.object(gamescope,'window_of',return_value=SimpleNamespace(id=2)):
            with self.assertRaises(RuntimeError):guard.check()

    def test_brave_web_guard_is_shared_by_input_and_capture_and_never_restores_other_windows(self):
        guard,_=self.guard(1,None);guard.web=Mock();window=SimpleNamespace(id=1)
        with patch.object(gamescope,'window_of',return_value=window):
            guard.check();guard.web.check.assert_called_once_with(window)
            guard.focused=lambda:2;guard.restore_focus=Mock(return_value=True)
            with self.assertRaises(RuntimeError):guard.check()
            guard.restore_focus.assert_not_called()

    def test_capture_checks_the_guard_after_reading_and_rejects_a_wrong_frame_size(self):
        check=Mock(side_effect=[None,RuntimeError('Contenido cambió durante la captura')])
        cap=self.capture(np.zeros((1080,1920,3),np.uint8),check)
        with self.assertRaises(SafetyStop):cap.grab({'left':0,'top':0,'width':10,'height':10})
        self.assertEqual(check.call_count,2)
        with self.assertRaises(SafetyStop):
            self.capture(np.zeros((1024,1920,3),np.uint8)).grab({'left':0,'top':0,'width':10,'height':10})

    def test_brave_escape_uses_cdp_and_releases_even_after_geometry_failure_or_stop(self):
        from Xlib import X
        for failure in (None,RuntimeError('iframe cambió'),KeyboardInterrupt('Detener')):
            io=gamescope.GamescopeIO.__new__(gamescope.GamescopeIO)
            web=Mock();guard=SimpleNamespace(web=web,desktop=Mock(),check=Mock(),display=Mock())
            io.game_guard=guard
            if isinstance(failure,KeyboardInterrupt):guard.desktop.emergency.side_effect=[None,failure]
            elif failure:guard.check.side_effect=[None,failure]
            with patch('Xlib.ext.xtest.fake_input') as native,patch.object(gamescope.time,'sleep'):
                if failure:
                    with self.assertRaises(KeyboardInterrupt if isinstance(failure,KeyboardInterrupt) else SafetyStop):io.escape()
                else:io.escape()
                self.assertEqual([c.args for c in web.key.call_args_list],[('escapeDown',),('escapeUp',)])
                native.assert_not_called()
        guard.web=None;guard.desktop.emergency.side_effect=None;guard.check.side_effect=None
        guard.display.keysym_to_keycode.return_value=9
        with patch('Xlib.ext.xtest.fake_input') as native,patch.object(gamescope.time,'sleep'):
            io.escape();self.assertEqual([c.args[1:] for c in native.call_args_list],[(X.KeyPress,9),(X.KeyRelease,9)])

    def test_a_release_error_cannot_turn_a_user_stop_into_a_retry(self):
        io=gamescope.GamescopeIO.__new__(gamescope.GamescopeIO)
        web=Mock();web.key.side_effect=[None,RuntimeError('CDP cerrado')]
        io.game_guard=SimpleNamespace(web=web,display=Mock(),desktop=Mock(),check=Mock())
        io.game_guard.desktop.emergency.side_effect=[None,KeyboardInterrupt('Detener')]
        with patch('Xlib.ext.xtest.fake_input'),patch.object(gamescope.time,'sleep'),self.assertRaises(KeyboardInterrupt):io.escape()
        web.close.assert_called_once()

    def test_a_cleanup_error_cannot_mask_a_user_stop(self):
        io=gamescope.GamescopeIO.__new__(gamescope.GamescopeIO)
        web=Mock();web.key.side_effect=[None,RuntimeError('CDP cerrado')];web.close.side_effect=RuntimeError('Cierre agotado')
        io.game_guard=SimpleNamespace(web=web,display=Mock(),desktop=Mock(),check=Mock())
        io.game_guard.desktop.emergency.side_effect=[None,KeyboardInterrupt('Detener')]
        with patch.object(gamescope.time,'sleep'),self.assertRaises(KeyboardInterrupt):io.escape()

    def test_initial_guard_failure_closes_the_owned_connections(self):
        guard=Mock();guard.check.side_effect=RuntimeError('geometría inválida')
        with patch.object(gamescope,'GamescopeGuard',return_value=guard),self.assertRaises(SafetyStop):gamescope.GamescopeIO()
        guard.close.assert_called_once()

    def test_a_dom_overlay_stops_brave_before_button_press(self):
        io=gamescope.GamescopeIO.__new__(gamescope.GamescopeIO);io.control_mode=False;io._move=Mock()
        io.game_guard=SimpleNamespace(display=Mock(),web=Mock(),desktop=Mock(),check=Mock())
        io.game_guard.web.point.side_effect=RuntimeError('El punto no corresponde al canvas')
        with patch('Xlib.ext.xtest.fake_input') as native,self.assertRaises(SafetyStop):io.click((10,20))
        native.assert_not_called();io.game_guard.web.point.assert_called_once_with((10,20))

    def test_guard_constructor_wires_cdp_only_for_brave_and_cleans_all_owned_connections(self):
        for account in ('personal','perfil-1','steam'):
            display=Mock();window=SimpleNamespace(id=7);desktop=Mock()
            with patch.dict(os.environ,self.account_env(account),clear=True), \
                    patch.object(gamescope,'require_calibrated_client'),patch.object(gamescope,'find_display',return_value=display), \
                    patch.object(gamescope,'window_of',return_value=window),patch('fishing_core.linux.LinuxAPI',return_value=desktop), \
                    patch('fishing_core.brave.BraveGuard') as web:
                guard=gamescope.GamescopeGuard()
                if account=='steam':web.assert_not_called()
                else:web.assert_called_once_with(display,window)
                guard.close();display.close.assert_called_once();desktop.close.assert_called_once()
                if account!='steam':web.return_value.close.assert_called_once()

    def test_window_requires_full_geometry_and_an_unambiguous_identity(self):
        def window(identifier,height=1080):
            child=Mock();child.id=identifier;child.get_wm_name.return_value='Bit Heroes'
            child.get_geometry.return_value=SimpleNamespace(width=1920,height=height)
            child.query_tree.return_value=SimpleNamespace(children=[])
            return child
        display=Mock();root=display.screen().root;correct=window(1)
        root.query_tree.return_value=SimpleNamespace(children=[window(2,900)])
        self.assertIsNone(gamescope.window_of(display))
        root.query_tree.return_value=SimpleNamespace(children=[correct])
        self.assertIs(gamescope.window_of(display),correct)
        root.query_tree.return_value=SimpleNamespace(children=[correct,window(3)])
        with self.assertRaises(RuntimeError):gamescope.window_of(display)

    def test_brave_window_uses_approved_pid_and_profile_not_its_changing_web_title(self):
        from fishing_core.telemetry import ROOT
        def window(identifier,pid=1234,account='personal',height=1080):
            child=Mock();child.id=identifier
            child.get_wm_name.side_effect=AssertionError('No leer títulos web')
            child.get_wm_class.return_value=(f'brave-browser ({ROOT}/runs/accounts/{account}/brave-data)','Brave-browser')
            child.get_full_property.return_value=SimpleNamespace(value=[pid])
            child.get_geometry.return_value=SimpleNamespace(width=1920,height=height)
            child.query_tree.return_value=SimpleNamespace(children=[])
            return child
        env={**self.account_env('personal'),'FARM_BRAVE_PID':'1234','FARM_BRAVE_CDP_PORT':'45678','FARM_BRAVE_TARGET_ID':'A'*32}
        with patch.dict(os.environ,env,clear=True):
            display=Mock();root=display.screen().root;correct=window(1)
            wrong=[window(2,pid=999),window(3,account='perfil-1'),window(4,height=1024)]
            root.query_tree.return_value=SimpleNamespace(children=wrong)
            self.assertIsNone(gamescope.window_of(display))
            root.query_tree.return_value=SimpleNamespace(children=wrong+[correct])
            self.assertIs(gamescope.window_of(display),correct)
            root.query_tree.return_value=SimpleNamespace(children=[correct,window(5)])
            with self.assertRaises(RuntimeError):gamescope.window_of(display)

    @unittest.skipIf(os.name=='nt','Servidor de imagen Linux')
    def test_second_frame_server_does_not_overwrite_the_first_servers_memory(self):
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp,patch.dict(os.environ,{'XDG_RUNTIME_DIR':tmp},clear=True), \
                patch.object(gamescope,'SHM',str(Path(tmp)/'frame')),patch.object(gamescope,'pipewire_serial',return_value='4500'), \
                patch.object(gamescope,'PipeWireFrames'):
            server=gamescope.FrameServer()
            try:
                server.map[:16]=b'x'*16
                duplicate=None
                try:
                    with self.assertRaises(RuntimeError):duplicate=gamescope.FrameServer()
                finally:
                    if duplicate is not None:duplicate.close()
                self.assertEqual(server.map[:16],b'x'*16)
            finally:server.close()


if __name__=='__main__':unittest.main()
