"""Aislamiento multicuenta sin navegador, juego, captura ni input."""

import json
import os
import stat
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from fishing_core import accounts
from fishing_core.processes import Mutex
from fishing_core.protocol import Channel


class BrokerEndpointTests(unittest.TestCase):
    def test_endpoint_metadata_and_session_formats(self):
        from unittest.mock import Mock
        endpoint=str(accounts.ROOT/'runs/cdp-test/cdp.sock')
        info=Mock(st_mode=stat.S_IFSOCK|0o600,st_uid=os.getuid())
        directory=Mock(st_mode=stat.S_IFDIR|0o700,st_uid=os.getuid())
        env={'FARM_ACCOUNT':'personal','FARM_BACKEND':'cdp','FARM_BRAVE_PID':'1234',
             'FARM_BRAVE_CDP_ENDPOINT':endpoint,'FARM_BRAVE_TARGET_ID':'A'*32}
        with patch.object(Path,'is_symlink',return_value=False),patch.object(Path,'lstat',return_value=info), \
                patch.object(Path,'stat',return_value=directory):
            self.assertEqual(accounts.brave_target(env),(1234,endpoint,'A'*32))
            from fishing_core import farm_multi,browser_launcher
            self.assertEqual(farm_multi.trial_environments({'personal':{k:v for k,v in env.items() if k!='FARM_ACCOUNT'}},farm=True)['personal']['FARM_BRAVE_CDP_ENDPOINT'],endpoint)
            with self.assertRaises(ValueError):accounts.brave_target({**env,'FARM_BRAVE_CDP_PORT':'9222'})
            for mode in (stat.S_IFSOCK|0o666,stat.S_IFREG|0o600):
                info.st_mode=mode
                with self.assertRaises(ValueError):accounts.brave_target(env)
            info.st_mode=stat.S_IFSOCK|0o600;directory.st_mode=stat.S_IFDIR|0o755
            with self.assertRaises(ValueError):accounts.brave_target(env)
            directory.st_mode=stat.S_IFDIR|0o700;info.st_uid=os.getuid()+1
            with self.assertRaises(ValueError):accounts.brave_target(env)
        with self.assertRaises(ValueError):accounts.validate_cdp_endpoint('/tmp/cdp.sock')
        with patch.object(Path,'is_symlink',return_value=True):
            with self.assertRaises(ValueError):accounts.validate_cdp_endpoint(endpoint)
        with patch.object(Path,'is_symlink',return_value=False),patch.object(Path,'lstat',side_effect=FileNotFoundError):
            with self.assertRaises(ValueError):accounts.validate_cdp_endpoint(endpoint)

    def test_windows_pipe_pattern(self):
        pipe=r'\\.\pipe\bitheroes-12345678-1234-1234-1234-123456789abc'
        with patch.object(accounts.os,'name','nt'):
            self.assertEqual(accounts.validate_cdp_endpoint(pipe),pipe)
            for bad in (pipe+'x',pipe.replace('bitheroes','other'),'1234'):
                with self.assertRaises(ValueError):accounts.validate_cdp_endpoint(bad)
from fishing_core.telemetry import ROOT, Telemetry


class AccountTests(unittest.TestCase):
    @unittest.skipIf(os.name=='nt','Permisos y enlaces POSIX')
    def test_registry_secures_existing_run_directories_and_rejects_parent_link(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp,patch.object(accounts,'ROOT',Path(tmp)):
            root=Path(tmp);runs=root/'runs';runs.mkdir(mode=0o755)
            parent=runs/'accounts';parent.mkdir(mode=0o755)
            previous=os.umask(0)
            try:accounts.save_accounts(accounts.DEFAULT_ACCOUNTS)
            finally:os.umask(previous)
            self.assertEqual((parent/'accounts.json').stat().st_mode&0o777,0o600)
            for path in (runs,parent):self.assertEqual(path.stat().st_mode&0o777,0o700)
            linked=root/'linked';linked.mkdir();(linked/'runs').symlink_to(runs,target_is_directory=True)
            before=(parent/'accounts.json').read_bytes()
            with patch.object(accounts,'ROOT',linked),self.assertRaises(ValueError):
                accounts.save_accounts(accounts.DEFAULT_ACCOUNTS)
            self.assertEqual((parent/'accounts.json').read_bytes(),before)

    def test_registry_defaults_do_not_write_and_are_independent(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(accounts,'ROOT',Path(tmp)):
            self.assertEqual(accounts.load_accounts(),accounts.DEFAULT_ACCOUNTS)
            self.assertEqual(accounts.account_names(),{'steam':'Steam','personal':'FMANI','perfil-1':'KORTZZ'})
            records=accounts.load_accounts();records[0]['name']='Otro'
            self.assertEqual(accounts.steam_account(),'steam')
            self.assertEqual(accounts.browser_accounts(),['personal','perfil-1'])
            self.assertFalse((Path(tmp)/'runs').exists())

    def test_registry_add_remove_collision_and_private_atomic_file(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(accounts,'ROOT',Path(tmp)):
            self.assertEqual(accounts.add_account('Amigo','browser'),'amigo')
            self.assertEqual(accounts.add_account('Amigo','browser'),'amigo-2')
            self.assertEqual(accounts.account_id({'FARM_ACCOUNT':'amigo','FARM_BACKEND':'cdp'}),'amigo')
            profile=accounts.prepare_profiles(tmp)['amigo'];marker=profile/'sentinel';marker.write_text('conservar')
            accounts.remove_account('amigo')
            self.assertEqual(marker.read_text(),'conservar')
            with self.assertRaises(ValueError):accounts.account_id({'FARM_ACCOUNT':'amigo'})
            path=Path(tmp)/'runs/accounts/accounts.json'
            self.assertEqual(path.stat().st_mode&0o777,0o600)
            self.assertEqual(list(path.parent.glob('.accounts-*')),[])

    def test_registry_rejects_invalid_records_without_changing_file(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(accounts,'ROOT',Path(tmp)):
            accounts.save_accounts(accounts.DEFAULT_ACCOUNTS)
            record={'id':'amigo','name':'Amigo','type':'browser'}
            invalid=[None,{},[record,record],accounts.DEFAULT_ACCOUNTS+[dict(record,type='steam')],
                     [dict(record,id=f'a{i}') for i in range(9)]]
            for field,values in {'id':['','../a','A','a_','a'*33,1],
                                 'name':['','a'*25,'a\n',1], 'type':['other',None,[]]}.items():
                invalid.extend([[dict(record,**{field:value})] for value in values])
            for records in invalid:
                with self.subTest(records=records),self.assertRaises(ValueError):accounts.save_accounts(records)
            self.assertEqual(accounts.load_accounts(),accounts.DEFAULT_ACCOUNTS)
            with self.assertRaises(ValueError):accounts.add_account('Steam nueva','steam')
            with self.assertRaises(ValueError):accounts.remove_account('desconocida')

    def test_new_browser_account_is_accepted_by_cdp_supervisor(self):
        from fishing_core import farm_multi
        with tempfile.TemporaryDirectory() as tmp,patch.object(accounts,'ROOT',Path(tmp)):
            accounts.add_account('Amigo','browser')
            session={'FARM_BACKEND':'cdp','FARM_BRAVE_PID':'1234','FARM_BRAVE_CDP_PORT':'45678','FARM_BRAVE_TARGET_ID':'A'*32}
            env=farm_multi.trial_environments({'amigo':session},farm=True)['amigo']
            self.assertEqual(accounts.brave_target(env),(1234,45678,'A'*32))
            self.assertEqual(env['FARM_ACCOUNT'],'amigo')

    def test_failed_atomic_registry_write_preserves_previous_records(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(accounts,'ROOT',Path(tmp)):
            accounts.save_accounts(accounts.DEFAULT_ACCOUNTS)
            with patch.object(accounts.os,'replace',side_effect=OSError('fallo')):
                with self.assertRaises(OSError):accounts.add_account('Amigo','browser')
            self.assertEqual(accounts.load_accounts(),accounts.DEFAULT_ACCOUNTS)
            self.assertEqual(list((Path(tmp)/'runs/accounts').glob('.accounts-*')),[])

    def test_cdp_import_path_requires_browser_but_no_display_or_serial(self):
        env={'FARM_ACCOUNT':'personal','FARM_BACKEND':'cdp','FARM_BRAVE_PID':'1234',
             'FARM_BRAVE_CDP_PORT':'45678','FARM_BRAVE_TARGET_ID':'A'*32}
        self.assertTrue(accounts.shm_path(env).endswith('-personal-cdp'))
        with self.assertRaises(ValueError):accounts.shm_path({**env,'FARM_ACCOUNT':'steam'})

    def test_legacy_paths_are_unchanged_and_account_ids_are_allowlisted(self):
        with patch.dict(os.environ,{},clear=True):
            self.assertIsNone(accounts.account_id())
            self.assertEqual(accounts.state_root(ROOT),ROOT)
            self.assertEqual(accounts.runs_root(ROOT),ROOT/'runs')
            self.assertEqual(accounts.mutex_role('CONTROL'),'CONTROL')
            self.assertEqual(accounts.shm_path(),'/dev/shm/bitheroes-gamescope-frame')
        for invalid in ('','../personal','Personal','otra','steam;exit'):
            with self.subTest(invalid=invalid),patch.dict(os.environ,{'FARM_ACCOUNT':invalid}):
                with self.assertRaises(ValueError):accounts.state_root(ROOT)

    def test_all_default_paths_are_scoped_in_a_fresh_process(self):
        code="""
import json
from fishing_core import accounts, farm_config, loot, farm_all, gamescope
from fishing_core.protocol import session_directory
from fishing_core.telemetry import ROOT
print(json.dumps([str(p) for p in (farm_config.PATH,loot.PATH,loot.ALBUM,loot.KINDS,
    farm_all.PROGRESS,session_directory('same-run'),accounts.state_root(ROOT)/'CONTROL_LOG.txt',gamescope.SHM)]))
"""
        paths=[]
        for account in accounts.account_names():
            env={**os.environ,'FARM_ACCOUNT':account,'FARM_BACKEND':'gamescope',
                 'FARM_GAMESCOPE_DISPLAY':':12','FARM_GAMESCOPE_SERIAL':'4500'}
            out=subprocess.run([sys.executable,'-B','-c',code],cwd=ROOT,env=env,capture_output=True,text=True,check=True)
            values=json.loads(out.stdout);paths.append(values)
            for value in values[:-1]:self.assertTrue(Path(value).is_relative_to(ROOT/'runs/accounts'/account),value)
        for column in zip(*paths):self.assertEqual(len(set(column)),3)

    def test_same_run_id_has_independent_ipc_and_logs(self):
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
            root=Path(tmp);channels=[];logs=[]
            for account in accounts.account_names():
                with patch.dict(os.environ,{'FARM_ACCOUNT':account}):
                    channel=Channel('same-run',root);channel.stop('TEST',account);channels.append(channel)
                    log=Telemetry('TEST','same-run',root);log.close();logs.append(log)
            self.assertEqual([json.loads(c.stop_path.read_text())['reason'] for c in channels],list(accounts.account_names()))
            self.assertEqual(len({c.directory for c in channels}),3)
            self.assertEqual([log.directory for log in logs],[c.directory for c in channels])
            self.assertEqual(len({log.legacy_log for log in logs}),3)

    @unittest.skipIf(os.name=='nt','Exclusividad concurrente Linux')
    def test_three_real_workers_coexist_but_duplicates_and_legacy_steam_are_blocked(self):
        code="""
import sys
from fishing_core.processes import Mutex
try:lock=Mutex(sys.argv[1])
except RuntimeError:
    print('duplicate',flush=True);sys.exit(2)
print('ready',flush=True)
sys.stdin.readline()
lock.close()
"""
        workers=[];role='TEST_'+uuid4().hex
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
            try:
                for account in accounts.account_names():
                    env={**os.environ,'FARM_ACCOUNT':account,'XDG_RUNTIME_DIR':tmp}
                    worker=subprocess.Popen([sys.executable,'-B','-c',code,role],cwd=ROOT,env=env,
                                            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                    workers.append(worker)
                    self.assertEqual(worker.stdout.readline().strip(),'ready')
                    duplicate=subprocess.run([sys.executable,'-B','-c',code,role],cwd=ROOT,env=env,
                                             input='\n',capture_output=True,text=True,timeout=10)
                    self.assertEqual((duplicate.returncode,duplicate.stdout.strip()),(2,'duplicate'))
                legacy={**os.environ,'XDG_RUNTIME_DIR':tmp};legacy.pop('FARM_ACCOUNT',None)
                out=subprocess.run([sys.executable,'-B','-c',code,role],cwd=ROOT,env=legacy,
                                   input='\n',capture_output=True,text=True,timeout=10)
                self.assertEqual(out.returncode,2)
                self.assertTrue(all(w.poll() is None for w in workers))
            finally:
                for worker in workers:
                    try:worker.communicate('\n',timeout=5)
                    except subprocess.TimeoutExpired:worker.kill();worker.communicate()

    def test_gamescope_requires_local_display_serial_and_background_backend(self):
        env={'FARM_ACCOUNT':'steam','FARM_BACKEND':'gamescope',
             'FARM_GAMESCOPE_DISPLAY':':12','FARM_GAMESCOPE_SERIAL':'4500'}
        with patch.dict(os.environ,env,clear=True):
            self.assertEqual(accounts.gamescope_target(),(':12','4500'))
        for key in ('FARM_BACKEND','FARM_GAMESCOPE_DISPLAY','FARM_GAMESCOPE_SERIAL'):
            bad={**env};bad.pop(key)
            with self.subTest(key=key),patch.dict(os.environ,bad,clear=True):
                with self.assertRaises(ValueError):accounts.gamescope_target()
        for display,serial in (('host:12','4500'),(':12','0'),(':12','abc'),(':12','1 ! filesink'),(':12','18446744073709551616')):
            with self.subTest(display=display,serial=serial),patch.dict(os.environ,{**env,'FARM_GAMESCOPE_DISPLAY':display,'FARM_GAMESCOPE_SERIAL':serial},clear=True):
                with self.assertRaises(ValueError):accounts.gamescope_target()

    def test_shared_memory_is_bound_to_the_accounts_exact_endpoints(self):
        env={'FARM_ACCOUNT':'steam','FARM_BACKEND':'gamescope','FARM_GAMESCOPE_DISPLAY':':12','FARM_GAMESCOPE_SERIAL':'4500'}
        with patch.dict(os.environ,env,clear=True):first=accounts.shm_path()
        with patch.dict(os.environ,{**env,'FARM_GAMESCOPE_SERIAL':'4501'},clear=True):second=accounts.shm_path()
        with patch.dict(os.environ,{**env,'FARM_GAMESCOPE_DISPLAY':':13'},clear=True):third=accounts.shm_path()
        self.assertEqual(len({first,second,third}),3)
        before=dict(os.environ)
        self.assertEqual(accounts.shm_path(env),first)
        self.assertEqual(dict(os.environ),before)

    def test_brave_endpoints_are_explicit_local_numbers_and_a_pinned_target(self):
        env={'FARM_ACCOUNT':'personal','FARM_BRAVE_PID':'1234','FARM_BRAVE_CDP_PORT':'45678',
             'FARM_BRAVE_TARGET_ID':'A'*32}
        self.assertEqual(accounts.brave_target(env),(1234,45678,'A'*32))
        for account in (None,'steam'):
            self.assertIsNone(accounts.brave_target({} if account is None else {'FARM_ACCOUNT':account}))
        for key in ('FARM_BRAVE_PID','FARM_BRAVE_CDP_PORT','FARM_BRAVE_TARGET_ID'):
            bad={**env};bad.pop(key)
            with self.subTest(key=key),self.assertRaises(ValueError):accounts.brave_target(bad)
        for key,value in (('FARM_BRAVE_PID','0'),('FARM_BRAVE_PID','2147483648'),
                          ('FARM_BRAVE_CDP_PORT','65536'),('FARM_BRAVE_CDP_PORT','host:45678'),
                          ('FARM_BRAVE_TARGET_ID','../another'),('FARM_BRAVE_TARGET_ID','')):
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                accounts.brave_target({**env,key:value})

    def test_prepare_creates_only_two_empty_private_directories_and_preserves_existing_files(self):
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
            root=Path(tmp);profiles=accounts.prepare_profiles(root)
            self.assertEqual(set(profiles),{'personal','perfil-1'})
            self.assertEqual(len(set(profiles.values())),2)
            for path in profiles.values():
                self.assertEqual(list(path.iterdir()),[])
                if os.name!='nt':self.assertEqual(path.stat().st_mode&0o777,0o700)
            marker=profiles['personal']/'sentinel';marker.write_text('preserve')
            self.assertEqual(accounts.prepare_profiles(root),profiles)
            self.assertEqual(marker.read_text(),'preserve')

    def test_fresh_accounts_default_to_no_gold_without_changing_legacy_defaults(self):
        from fishing_core import farm_config
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
            missing=Path(tmp)/'missing.json'
            with patch.dict(os.environ,{'FARM_ACCOUNT':'personal'}):
                config=farm_config.load(missing)
                # Cuentas nuevas: sin familiar objetivo y sin cuota de oro configurable (el oro lo decide el objetivo).
                self.assertEqual(config['quest']['targets'],[])
                self.assertNotIn('max_gold',config['quest']);self.assertNotIn('max_gold',config['raid'])

    def test_account_never_falls_back_to_desktop_window_api(self):
        from fishing_core.game_window import window_api
        for account in accounts.account_names():
            with patch.dict(os.environ,{'FARM_ACCOUNT':account}),patch('fishing_core.linux.LinuxAPI') as desktop:
                with self.assertRaises(RuntimeError):window_api()
                desktop.assert_not_called()

    @unittest.skipIf(os.name=='nt','Symlink Linux')
    def test_prepare_rejects_symlinked_profile_parent(self):
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
            root=Path(tmp);outside=root/'untouched';outside.mkdir()
            (root/'runs').symlink_to(outside,target_is_directory=True)
            with self.assertRaises(ValueError):accounts.prepare_profiles(root)
            self.assertEqual(list(outside.iterdir()),[])


if __name__=='__main__':unittest.main()
