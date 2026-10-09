"""Lanzador offline: procesos y detección simulados, sin clientes reales."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch

from fishing_core import browser_launcher as launcher
from fishing_core import accounts,brave


class BrowserLauncherTests(unittest.TestCase):
    def test_linux_detection_order_and_missing_browser(self):
        with patch.object(launcher.os,'name','posix'),patch.object(launcher.shutil,'which',side_effect=lambda name:'/bin/'+name if name=='chromium' else None) as which:
            self.assertEqual(launcher.detect_browser(),'/bin/chromium')
            self.assertIn(unittest.mock.call('brave-browser'),which.call_args_list)
        with patch.object(launcher.os,'name','posix'),patch.object(launcher.shutil,'which',return_value=None):
            with self.assertRaises(ValueError):launcher.detect_browser()

    def test_windows_typical_paths(self):
        # Conservar Path de la plataforma anfitriona al simular Windows.
        native=type(Path())
        for relative in ('BraveSoftware/Brave-Browser/Application/brave.exe',
                         'Google/Chrome/Application/chrome.exe','Chromium/Application/chrome.exe',
                         'Microsoft/Edge/Application/msedge.exe'):
            with self.subTest(browser=relative),tempfile.TemporaryDirectory() as tmp:
                binary=native(tmp)/relative;binary.parent.mkdir(parents=True);binary.touch()
                with patch.object(launcher,'Path',native),patch.object(launcher.os,'name','nt'),patch.dict(os.environ,{'LOCALAPPDATA':tmp},clear=True):
                    self.assertEqual(launcher.detect_browser(),str(binary))

    def test_explicit_path_and_firefox_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ('brave','chrome','chromium','microsoft-edge','firefox'):
                path=Path(tmp)/name;path.touch()
                if name=='firefox':
                    with self.assertRaises(ValueError):launcher.detect_browser(path)
                else:self.assertEqual(launcher.detect_browser(path),str(path))

    def launch(self,root,visible=False,failure=None):
        process=Mock(pid=1234);process.poll.return_value=None
        with patch.object(launcher,'ROOT',root),patch.object(launcher,'detect_browser',return_value='/bin/chrome'), \
                patch.object(launcher,'require_closed_profile',side_effect=failure), \
                patch.object(launcher,'browser_identity',return_value=('chrome','stamp')), \
                patch.object(launcher,'prepare_brave',return_value='A'*32) as prepare, \
                patch.object(launcher.subprocess,'Popen',return_value=process) as spawn, \
                patch.object(launcher.socket,'socket') as reserve:
            reserve.return_value.__enter__.return_value.getsockname.return_value=('127.0.0.1',45678)
            if failure:
                with self.assertRaises(RuntimeError):launcher.launch_browser('personal',visible=visible)
                spawn.assert_not_called();return
            owned,session=launcher.launch_browser('personal',visible=visible)
            self.assertIs(owned,process);self.assertEqual(session['FARM_BACKEND'],'cdp')
            prepare.assert_called_once_with(1234,int(session['FARM_BRAVE_CDP_PORT']))
            return spawn.call_args.args[0],session

    def test_exact_flags_visible_and_nonvisible_and_environment_restored(self):
        for visible in (False,True):
            with self.subTest(visible=visible),tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'FARM_ACCOUNT':'steam','FARM_BACKEND':'gamescope'}):
                root=Path(tmp);argv,session=self.launch(root,visible)
                expected=['/bin/chrome',f'--user-data-dir={root}/runs/accounts/personal/brave-data',
                    '--remote-debugging-port='+session['FARM_BRAVE_CDP_PORT'],
                    '--remote-debugging-address=127.0.0.1','--window-size=1920,1080',
                    '--force-device-scale-factor=1','--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows','--disable-renderer-backgrounding',
                    '--no-first-run','--no-default-browser-check',
                    '--window-position=0,0' if visible else '--window-position=-2400,0']
                if not visible:expected.append('--no-startup-window')
                self.assertEqual(argv,expected);self.assertNotIn('--headless',argv)
                self.assertEqual(os.environ['FARM_ACCOUNT'],'steam');self.assertEqual(os.environ['FARM_BACKEND'],'gamescope')
                self.assertFalse((root/'runs/accounts/personal/browser-launch.lock').exists())

    def test_open_profile_blocks_before_creating_process(self):
        with tempfile.TemporaryDirectory() as tmp:self.launch(Path(tmp),failure=RuntimeError('abierto'))

    def test_atomic_session_preserves_other_accounts_and_private_mode(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(launcher,'ROOT',Path(tmp)):
            root=Path(tmp);accounts.prepare_profiles(root);path=root/'runs/accounts/sessions.json'
            other={'steam':{'existing':'kept'},'perfil-1':{'existing':'also kept'}}
            path.write_text(json.dumps(other))
            session={'FARM_BRAVE_PID':'1234','FARM_BRAVE_CDP_PORT':'45678','FARM_BRAVE_TARGET_ID':'A'*32,'FARM_BACKEND':'cdp'}
            replace=os.replace
            def atomic(source,dest):
                self.assertEqual(json.loads(path.read_text()),other)
                self.assertEqual(Path(source).stat().st_mode&0o777,0o600)
                replace(source,dest)
            with patch.object(launcher.os,'replace',side_effect=atomic) as publish:
                launcher.write_session('personal',session)
            publish.assert_called_once();self.assertEqual(json.loads(path.read_text()),{**other,'personal':session})
            self.assertEqual(path.stat().st_mode&0o777,0o600)
            session['FARM_BRAVE_PID']='2345';launcher.write_session('personal',session)
            self.assertEqual(json.loads(path.read_text()),{**other,'personal':session})

    def test_new_registered_browser_writes_its_own_session(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(accounts,'ROOT',Path(tmp)),patch.object(launcher,'ROOT',Path(tmp)):
            accounts.add_account('Amigo','browser')
            session={'FARM_BRAVE_PID':'1234','FARM_BRAVE_CDP_PORT':'45678','FARM_BRAVE_TARGET_ID':'A'*32,'FARM_BACKEND':'cdp'}
            launcher.write_session('amigo',session)
            self.assertEqual(json.loads((Path(tmp)/'runs/accounts/sessions.json').read_text()),{'amigo':session})
            self.assertTrue((Path(tmp)/'runs/accounts/amigo/brave-data').is_dir())
            with self.assertRaises(ValueError):launcher.launch_browser('desconocida')

    def test_failed_replace_preserves_file_and_cleans_temporary(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(launcher,'ROOT',Path(tmp)):
            accounts.prepare_profiles(Path(tmp));path=Path(tmp)/'runs/accounts/sessions.json';path.write_text('{}')
            session={'FARM_BRAVE_PID':'1234','FARM_BRAVE_CDP_PORT':'45678','FARM_BRAVE_TARGET_ID':'A'*32,'FARM_BACKEND':'cdp'}
            with patch.object(launcher.os,'replace',side_effect=OSError('offline')):
                with self.assertRaises(OSError):launcher.write_session('personal',session)
            self.assertEqual(path.read_text(),'{}');self.assertEqual(list(path.parent.glob('.sessions-*')),[])
            self.assertFalse(path.with_suffix('.lock').exists())

    def test_cli_launches_and_writes_without_farming(self):
        session={'example':'mock'}
        with patch.object(launcher,'launch_browser',return_value=(Mock(),session)) as launch,patch.object(launcher,'write_session') as write:
            self.assertEqual(launcher.main(['perfil-1','--visible','--browser','/bin/chrome']),0)
            launch.assert_called_once_with('perfil-1','/bin/chrome',True);write.assert_called_once_with('perfil-1',session)

    def test_windows_account_and_profiles_for_cdp(self):
        native=type(Path())
        with tempfile.TemporaryDirectory() as tmp,patch.object(accounts,'Path',native),patch.object(accounts.os,'name','nt'):
            self.assertEqual(accounts.account_id({'FARM_ACCOUNT':'personal','FARM_BACKEND':'cdp'}),'personal')
            self.assertTrue(accounts.prepare_profiles(tmp)['personal'].is_dir())
            with self.assertRaises(ValueError):accounts.account_id({'FARM_ACCOUNT':'personal','FARM_BACKEND':'gamescope'})

    def test_windows_identity_keeps_profile_port_and_loopback_guards(self):
        row={'ProcessId':1234,'ExecutablePath':'chrome.exe','CommandLine':'mock','CreationDate':'stamp'}
        argv=['chrome.exe',f'--user-data-dir={brave.ROOT}/runs/accounts/personal/brave-data','--remote-debugging-port=45678']
        native=type(Path())
        with patch.object(brave,'Path',native),patch.object(brave,'_windows_processes',return_value=[row]), \
                patch.object(brave,'_windows_argv',return_value=argv),patch.object(brave.subprocess,'run',return_value=Mock(returncode=0,stdout='[{"LocalAddress":"127.0.0.1"}]')) as query:
            self.assertEqual(brave._windows_identity(1234,45678,'personal'),('chrome.exe','stamp'))
            with self.assertRaises(ValueError):brave._windows_identity(1234,45678,'perfil-1')
            query.return_value.stdout='[{"LocalAddress":"0.0.0.0"}]'
            with self.assertRaises(ValueError):brave._windows_identity(1234,45678,'personal')

    def test_preparation_failure_terminates_only_new_process(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(launcher,'ROOT',Path(tmp)), \
                patch.object(launcher,'detect_browser',return_value='/bin/chrome'), \
                patch.object(launcher,'require_closed_profile'), \
                patch.object(launcher,'browser_identity'), \
                patch.object(launcher,'prepare_brave',side_effect=RuntimeError('offline')), \
                patch.object(launcher.subprocess,'Popen') as spawn,patch.object(launcher.socket,'socket') as reserve:
            process=spawn.return_value;process.poll.return_value=None
            reserve.return_value.__enter__.return_value.getsockname.return_value=('127.0.0.1',45678)
            with self.assertRaisesRegex(RuntimeError,'offline'):launcher.launch_browser('personal')
            process.terminate.assert_called_once();process.wait.assert_called_once_with(timeout=5)

    def test_port_reservation_is_loopback_only(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(launcher.socket,'socket') as reserve:
            # launch() también sustituye socket: capturar bind dentro de esa prueba.
            with patch.object(launcher,'ROOT',Path(tmp)),patch.object(launcher,'detect_browser',return_value='/bin/chrome'), \
                    patch.object(launcher,'require_closed_profile'),patch.object(launcher,'browser_identity'), \
                    patch.object(launcher,'prepare_brave',return_value='A'*32),patch.object(launcher.subprocess,'Popen') as spawn:
                spawn.return_value.pid=1234;spawn.return_value.poll.return_value=None
                reserve.return_value.__enter__.return_value.getsockname.return_value=('127.0.0.1',45678)
                launcher.launch_browser('personal')
                reserve.return_value.__enter__.return_value.bind.assert_called_once_with(('127.0.0.1',0))

    def test_windows_preparation_uses_pipe_without_pidfd(self):
        import io
        native=type(Path());process=Mock()
        process.stdout=io.BytesIO(b'{"id":0,"ok":true,"target":"'+b'A'*32+b'"}\n')
        process.stdin=io.BytesIO();process.returncode=0
        with patch.object(brave,'Path',native),patch.object(brave.os,'name','nt'), \
                patch.dict(os.environ,{'FARM_ACCOUNT':'personal','FARM_BACKEND':'cdp'},clear=True), \
                patch.object(brave.shutil,'which',return_value='node.exe'), \
                patch.object(brave,'browser_identity',return_value=('chrome.exe','stamp')) as identity, \
                patch.object(brave.subprocess,'Popen',return_value=process), \
                patch.object(brave.os,'pidfd_open',create=True) as pidfd:
            self.assertEqual(brave.prepare_brave(1234,45678),'A'*32)
            pidfd.assert_not_called();self.assertEqual(identity.call_count,2)
            self.assertTrue(process.stdout.closed);self.assertTrue(process.stdin.closed)

    def test_windows_open_profile_blocks(self):
        profile=Path('/offline/profile')
        with patch.object(brave.os,'name','nt'),patch.object(brave,'_windows_processes',return_value=[{'CommandLine':'mock'}]),patch.object(brave,'_windows_argv',return_value=['chrome.exe',f'--user-data-dir={profile}']):
            with self.assertRaisesRegex(RuntimeError,'abierto'):brave.require_closed_profile(profile)


if __name__=='__main__':unittest.main()
