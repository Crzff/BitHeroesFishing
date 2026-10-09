"""Aislamiento multicuenta sin navegador, juego, captura ni input."""

import json
import os
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
from fishing_core.telemetry import ROOT, Telemetry


class AccountTests(unittest.TestCase):
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
        for account in accounts.NAMES:
            env={**os.environ,'FARM_ACCOUNT':account,'FARM_BACKEND':'gamescope',
                 'FARM_GAMESCOPE_DISPLAY':':12','FARM_GAMESCOPE_SERIAL':'4500'}
            out=subprocess.run([sys.executable,'-B','-c',code],cwd=ROOT,env=env,capture_output=True,text=True,check=True)
            values=json.loads(out.stdout);paths.append(values)
            for value in values[:-1]:self.assertTrue(Path(value).is_relative_to(ROOT/'runs/accounts'/account),value)
        for column in zip(*paths):self.assertEqual(len(set(column)),3)

    def test_same_run_id_has_independent_ipc_and_logs(self):
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
            root=Path(tmp);channels=[];logs=[]
            for account in accounts.NAMES:
                with patch.dict(os.environ,{'FARM_ACCOUNT':account}):
                    channel=Channel('same-run',root);channel.stop('TEST',account);channels.append(channel)
                    log=Telemetry('TEST','same-run',root);log.close();logs.append(log)
            self.assertEqual([json.loads(c.stop_path.read_text())['reason'] for c in channels],list(accounts.NAMES))
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
                for account in accounts.NAMES:
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
                self.assertEqual((config['quest']['max_gold'],config['raid']['max_gold']),(0,0))
            self.assertEqual(farm_config.DEFAULT['quest']['max_gold'],50_000)
            self.assertEqual(farm_config.DEFAULT['raid']['max_gold'],250_000)

    def test_account_never_falls_back_to_desktop_window_api(self):
        from fishing_core.game_window import window_api
        for account in accounts.NAMES:
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
