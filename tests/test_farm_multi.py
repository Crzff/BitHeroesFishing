"""Supervisor multicuenta: dobles offline, sin clientes, captura ni input."""
import copy
import json
import os
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch

from fishing_core import farm_multi


def sessions():
    return {account:{'FARM_GAMESCOPE_DISPLAY':f':{12+i}','FARM_GAMESCOPE_SERIAL':str(4500+i),
                     **({'FARM_BRAVE_PID':str(1234+i),'FARM_BRAVE_CDP_PORT':str(45678+i),
                         'FARM_BRAVE_TARGET_ID':('A' if i==0 else 'B')*32} if account!='steam' else {})}
            for i,account in enumerate(('personal','perfil-1','steam'))}


class MultiFarmTests(unittest.TestCase):
    def test_cdp_sessions_propagate_worker_backend_and_reject_shared_endpoints(self):
        data=sessions()
        data['personal']={k:v for k,v in data['personal'].items() if k in farm_multi.BRAVE_KEYS}
        data['personal']['FARM_BACKEND']='cdp'
        with patch.dict(os.environ,{'FARM_GAMESCOPE_DISPLAY':':99','FARM_GAMESCOPE_SERIAL':'999'},clear=True), \
                patch.object(farm_multi,'require_calibrated_client'),patch.object(farm_multi,'Mutex'), \
                patch.object(farm_multi.subprocess,'Popen',side_effect=[Mock(stdout=[],poll=Mock(return_value=0)) for _ in data]) as spawn, \
                patch.object(farm_multi,'close_children'),patch('builtins.print'):
            farm_multi.run_farm(data)
            env=spawn.call_args_list[0].kwargs['env']
            self.assertEqual(env['FARM_BACKEND'],'cdp');self.assertEqual(env['FARM_MULTI_FARM'],'1')
            self.assertFalse(farm_multi.DISPLAY_KEYS&set(env))
            self.assertEqual(spawn.call_args_list[-1].kwargs['env']['FARM_BACKEND'],'gamescope')
        for key in farm_multi.BRAVE_KEYS:
            bad=copy.deepcopy(data);bad['perfil-1'][key]=bad['personal'][key]
            with self.subTest(key=key),self.assertRaises(ValueError):farm_multi.trial_environments(bad,farm=True)
        bad=copy.deepcopy(data);bad['steam']['FARM_BACKEND']='cdp'
        with self.assertRaises(ValueError):farm_multi.trial_environments(bad,farm=True)
        with self.assertRaises(ValueError):farm_multi.trial_environments(data)

    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.status_path=Path(tmp.name)/'multi_status.json'
        patcher=patch.object(farm_multi,'MULTI_STATUS',self.status_path);patcher.start();self.addCleanup(patcher.stop)

    def test_farm_subset_status_and_trial_still_requires_three(self):
        data={a:r for a,r in sessions().items() if a!='perfil-1'}
        with patch.object(farm_multi,'require_calibrated_client') as check,patch.object(farm_multi,'Mutex'), \
                patch.object(farm_multi.subprocess,'Popen',side_effect=[Mock(stdout=[],poll=Mock(return_value=0)) for _ in data]), \
                patch.object(farm_multi,'close_children'),patch('builtins.print'):
            self.assertEqual(farm_multi.run_farm(data),dict.fromkeys(data,0))
            self.assertEqual(check.call_count,2)
        self.assertEqual(set(json.loads(self.status_path.read_text())['accounts']),set(data))
        for read_only in (False,True):
            with self.assertRaises(ValueError):farm_multi.validate_trial(data,read_only)

    def test_farm_subset_rejects_empty_unknown_incomplete_and_shared_endpoints(self):
        data={a:r for a,r in sessions().items() if a!='perfil-1'}
        incomplete=copy.deepcopy(data);incomplete['steam'].pop('FARM_GAMESCOPE_SERIAL')
        shared=copy.deepcopy(data);shared['steam']['FARM_GAMESCOPE_DISPLAY']=shared['personal']['FARM_GAMESCOPE_DISPLAY']
        for invalid in ({},{'unknown':{}},incomplete,shared):
            with self.subTest(invalid=invalid),patch.object(farm_multi.subprocess,'Popen') as spawn:
                with self.assertRaises(ValueError):farm_multi.start_farm(invalid)
                spawn.assert_not_called()

    def test_status_steps_results_and_terminal_codes(self):
        children=[Mock(stdout=['== Quest (reintento)\n','Quest: motivo\n'],poll=Mock(return_value=code)) for code in (0,1,0)]
        snapshots=[];atomic=farm_multi.atomic_json
        def write(path,data):
            snapshots.append(copy.deepcopy(data));atomic(path,data)
        with patch.object(farm_multi,'require_calibrated_client'),patch.object(farm_multi,'Mutex'), \
                patch.object(farm_multi.subprocess,'Popen',side_effect=children),patch.object(farm_multi,'close_children'), \
                patch.object(farm_multi,'atomic_json',side_effect=write),patch('builtins.print'):
            farm_multi.run_farm(sessions())
        data=json.loads(self.status_path.read_text());self.assertEqual(data['supervisor_pid'],os.getpid())
        self.assertTrue(all(r['step']=='Iniciando' and r['state']=='EN MARCHA' for r in snapshots[0]['accounts'].values()))
        for account,code in zip(sessions(),(0,1,0)):
            row=data['accounts'][account]
            self.assertEqual((row['step'],row['detail'],row['state']),('Quest','motivo','TERMINADO' if code==0 else 'PARADO'))
        self.assertTrue(any(r['detail']=='Quest (reintento)' for s in snapshots for r in s['accounts'].values()))

    def test_status_write_error_does_not_stop_farm(self):
        with patch.object(farm_multi,'require_calibrated_client'),patch.object(farm_multi,'Mutex'), \
                patch.object(farm_multi.subprocess,'Popen',side_effect=[Mock(stdout=[],poll=Mock(return_value=0)) for _ in range(3)]), \
                patch.object(farm_multi,'close_children'),patch.object(farm_multi,'atomic_json',side_effect=OSError),patch('builtins.print'):
            self.assertEqual(farm_multi.run_farm(sessions()),dict.fromkeys(sessions(),0))

    def test_workers_keep_own_account_and_failure_does_not_stop_survivors(self):
        children=[Mock(stdout=['== Quest\n']) for _ in range(3)];data=sessions()
        children[0].poll.side_effect=[None,None,0,0]
        children[1].poll.return_value=1
        children[2].poll.side_effect=[None,0,0]
        checked=[]
        def spawn(argv,**kwargs):
            self.assertEqual(checked,list(data))
            self.assertEqual(argv[3:],['-m','fishing_core.farm_all'])
            account=kwargs['env']['FARM_ACCOUNT']
            self.assertEqual(kwargs['env']['FARM_MULTI_FARM'],'1')
            return children[list(data).index(account)]
        with patch.object(farm_multi,'require_calibrated_client',side_effect=lambda env:checked.append(env['FARM_ACCOUNT'])), \
                patch.object(farm_multi,'Mutex') as mutex,patch.object(farm_multi.subprocess,'Popen',side_effect=spawn) as popen, \
                patch.object(farm_multi,'close_children') as close,patch.object(farm_multi.time,'sleep') as sleep, \
                patch('builtins.print') as output:
            self.assertEqual(farm_multi.run_farm(data),{'perfil-1':1,'steam':0,'personal':0})
            self.assertEqual(popen.call_count,3)
            announcements=[call.args[0] for call in output.call_args_list if not call.args[0].startswith('[')]
            self.assertEqual(announcements,[f'{farm_multi.account_names()[a]}: {status}' for a,status in
                             (('perfil-1','PARADO (código 1)'),('steam','TERMINADO'),('personal','TERMINADO'))])
            for account in data:self.assertIn(f'[{farm_multi.account_names()[account]}] == Quest',[call.args[0] for call in output.call_args_list])
            self.assertEqual(sleep.call_args_list,[unittest.mock.call(.1),unittest.mock.call(.1)])
            close.assert_called_once_with(children);mutex.assert_called_once_with('MULTI_SUPERVISOR')
            mutex.return_value.close.assert_called_once()
        for child in children:child.send_signal.assert_not_called();child.wait.assert_not_called()

    def test_supervisor_exception_signals_only_live_workers_and_releases_lock(self):
        for error in (RuntimeError('monitor failed'),KeyboardInterrupt()):
            children=[Mock(stdout=[]) for _ in range(3)]
            children[0].poll.return_value=0
            for child in children[1:]:child.poll.return_value=None
            with self.subTest(error=type(error).__name__),patch.object(farm_multi,'require_calibrated_client'), \
                    patch.object(farm_multi,'Mutex') as mutex,patch.object(farm_multi.subprocess,'Popen',side_effect=children), \
                    patch.object(farm_multi.time,'sleep',side_effect=error),patch.object(farm_multi,'close_children') as close:
                with self.assertRaises(type(error)):farm_multi.run_farm(sessions())
                rows=json.loads(self.status_path.read_text())['accounts']
                self.assertEqual(rows['personal']['state'],'TERMINADO')
                for account in ('perfil-1','steam'):self.assertEqual((rows[account]['state'],rows[account]['detail']),('PARADO','STOP'))
                children[0].send_signal.assert_not_called()
                for child in children[1:]:child.send_signal.assert_called_once_with(signal.SIGINT)
                close.assert_called_once_with(children);mutex.return_value.close.assert_called_once()

    def test_failed_account_preflight_blocks_every_launch(self):
        for entry in (farm_multi.validate_farm,farm_multi.run_farm,farm_multi.start_farm):
            for account in sessions():
                def validate(env):
                    if env['FARM_ACCOUNT']==account:raise RuntimeError('cliente no calibrado')
                with self.subTest(entry=entry.__name__,account=account), \
                        patch.object(farm_multi,'require_calibrated_client',side_effect=validate), \
                        patch.object(farm_multi.subprocess,'Popen') as spawn:
                    with self.assertRaises(RuntimeError):entry(sessions())
                    spawn.assert_not_called()

    def test_panel_start_and_cli_pass_sessions_to_farm_supervisor(self):
        import io
        import json
        process=Mock();data=sessions()
        with patch.object(farm_multi,'require_calibrated_client') as validate, \
                patch.object(farm_multi.subprocess,'Popen',return_value=process) as spawn:
            self.assertIs(farm_multi.start_farm(data),process)
            self.assertEqual(validate.call_count,3)
            self.assertEqual(spawn.call_args.args[0][3:],['-m','fishing_core.farm_multi','--farm'])
            self.assertEqual(json.loads(process.stdin.write.call_args.args[0]),data)
            process.stdin.close.assert_called_once()
        with patch.object(farm_multi.sys,'stdin',io.StringIO(json.dumps(data))),patch.object(farm_multi,'run_farm') as run:
            farm_multi.main(['--farm']);run.assert_called_once_with(data)


class MultiTrialTests(unittest.TestCase):
    def test_only_dungeon_trial_marks_workers_and_checks_live_brave_before_any_spawn(self):
        with patch('fishing_core.brave.browser_identity',return_value=('brave','stamp')) as identity, \
                patch.object(farm_multi.subprocess,'Popen') as spawn:
            envs=farm_multi.validate_trial(sessions())
            self.assertTrue(all(env['FARM_SINGLE_DUNGEON']=='1' for env in envs.values()))
            self.assertEqual([call.args for call in identity.call_args_list],[(1234,45678,'personal'),(1235,45679,'perfil-1')])
            identity.reset_mock();observing=farm_multi.validate_trial(sessions(),read_only=True)
            self.assertTrue(all('FARM_SINGLE_DUNGEON' not in env for env in observing.values()));identity.assert_not_called()
            identity.side_effect=RuntimeError('Brave no confirmado')
            with self.assertRaises(RuntimeError):farm_multi.run_trial(sessions())
            spawn.assert_not_called()

    def test_all_observation_workers_use_the_input_disabled_flag_and_explicit_accounts(self):
        children=[Mock() for _ in range(3)]
        for process in children:process.poll.return_value=0
        with patch.object(farm_multi,'Mutex'),patch.object(farm_multi,'close_children'), \
                patch.object(farm_multi.subprocess,'Popen',side_effect=children) as spawn:
            self.assertEqual(farm_multi.run_trial(sessions(),read_only=True),{account:0 for account in sessions()})
            self.assertEqual([call.kwargs['env']['FARM_ACCOUNT'] for call in spawn.call_args_list],list(sessions()))
            self.assertTrue(all(call.args[0][-1]=='--stop-check' for call in spawn.call_args_list))

    def test_observation_launch_uses_the_separate_flag_without_enabling_the_farm_backend(self):
        process=Mock()
        with patch.object(farm_multi.subprocess,'Popen',return_value=process) as spawn:
            self.assertIs(farm_multi.start_trial(sessions(),read_only=True),process)
            self.assertEqual(spawn.call_args.args[0][-2:],['fishing_core.farm_multi','--stop-check'])
        with self.assertRaises(RuntimeError):farm_multi.validate_trial(sessions())  # Brave ficticio sin confirmar

    def test_panel_launch_keeps_the_guard_and_sends_only_endpoints_over_stdin(self):
        import json
        with patch.object(farm_multi.subprocess,'Popen') as spawn:
            with self.assertRaisesRegex(RuntimeError,'Brave'):farm_multi.start_trial(sessions())
            spawn.assert_not_called()
        process=Mock()
        with patch.object(farm_multi,'require_calibrated_client'), \
                patch.object(farm_multi.subprocess,'Popen',return_value=process) as spawn:
            self.assertIs(farm_multi.start_trial(sessions()),process)
            self.assertEqual(spawn.call_args.args[0][-1],'fishing_core.farm_multi')
            self.assertEqual(json.loads(process.stdin.write.call_args.args[0]),sessions())
            process.stdin.close.assert_called_once()

    def test_failed_stdin_delivery_stops_only_the_new_supervisor(self):
        process=Mock();process.stdin.write.side_effect=BrokenPipeError()
        with patch.object(farm_multi,'require_calibrated_client'), \
                patch.object(farm_multi.subprocess,'Popen',return_value=process), \
                patch.object(farm_multi,'close_children') as close:
            with self.assertRaises(BrokenPipeError):farm_multi.start_trial(sessions())
            process.send_signal.assert_called_once_with(signal.SIGINT);close.assert_called_once_with([process])

    def test_cli_rejects_bad_payloads_and_never_echoes_private_fields(self):
        import io
        for text in ('{broken PRIVATE_TEST_MARKER','[]','x'*8193):
            with patch.object(farm_multi.sys,'stdin',io.StringIO(text)), \
                    patch.object(farm_multi,'run_trial') as run:
                with self.assertRaises(ValueError) as error:farm_multi.main([])
                self.assertNotIn('PRIVATE_TEST_MARKER',str(error.exception));run.assert_not_called()
        with patch.object(farm_multi.sys,'stdin',io.StringIO('{}')),patch.object(farm_multi,'run_trial') as run:
            farm_multi.main([]);run.assert_called_once_with({})

    def test_endpoint_validation_is_pure_and_clears_inherited_client_identity(self):
        data=sessions();before=copy.deepcopy(data)
        with patch.dict(os.environ,{'FARM_BRAVE_PID':'999','FARM_BRAVE_CDP_PORT':'888','FARM_BRAVE_TARGET_ID':'C'*32,
                                    'FISHING_GAME_WINDOW':'stale','FARM_LAUNCHER_PID':'111','FISHING_RUN_ID':'old'},clear=True):
            parent=dict(os.environ);envs=farm_multi.trial_environments(data)
            self.assertEqual(dict(os.environ),parent)
        self.assertEqual(data,before);self.assertEqual(set(envs),set(data))
        for account,env in envs.items():
            self.assertEqual(env['FARM_ACCOUNT'],account);self.assertEqual(env['FARM_BACKEND'],'gamescope')
            for key in ('FISHING_GAME_WINDOW','FARM_LAUNCHER_PID','FISHING_RUN_ID'):self.assertNotIn(key,env)
        self.assertNotIn('FARM_BRAVE_PID',envs['steam'])

    def test_missing_invalid_extra_or_aliased_endpoints_are_refused_before_spawning(self):
        cases=[None,[],{}, {'personal':{}}, {**sessions(),'other':{}}]
        for key,value in (('FARM_GAMESCOPE_DISPLAY',':12.0'),('FARM_GAMESCOPE_SERIAL','4500'),
                          ('FARM_BRAVE_PID','1234'),('FARM_BRAVE_CDP_PORT','45678'),('FARM_BRAVE_TARGET_ID','a'*32)):
            data=sessions();data['perfil-1'][key]=value;cases.append(data)
        for key,value in (('FARM_GAMESCOPE_DISPLAY','host:12'),('FARM_GAMESCOPE_SERIAL',0),('FARM_BRAVE_PID',False),
                          ('FARM_BRAVE_CDP_PORT','65536'),('FARM_BRAVE_TARGET_ID',''),('PYTHONPATH','/untrusted')):
            data=sessions();data['personal'][key]=value;cases.append(data)
        data=sessions();del data['personal']['FARM_BRAVE_PID'];cases.append(data)
        for data in cases:
            with self.subTest(data_type=type(data).__name__),patch.object(farm_multi,'require_calibrated_client'), \
                    patch.object(farm_multi,'Mutex'),patch.object(farm_multi.subprocess,'Popen') as spawn:
                with self.assertRaises(ValueError):farm_multi.run_trial(data)
                spawn.assert_not_called()

    def test_unconfirmed_brave_blocks_all_workers_including_steam(self):
        with patch.object(farm_multi.subprocess,'Popen') as spawn:
            with self.assertRaisesRegex(RuntimeError,'Brave'):farm_multi.run_trial(sessions())
            spawn.assert_not_called()

    def test_all_accounts_are_checked_before_three_workers_run_concurrently(self):
        checked=[];children=[Mock() for _ in range(3)];data=sessions()
        for p in children:p.poll.side_effect=[None,0,0]
        def spawn(argv,**kwargs):
            self.assertEqual(checked,list(data),'No arrancar parcialmente antes de validar las tres cuentas')
            self.assertEqual(argv[-2:],['fishing_core.farm_all','--single-dungeon'])
            self.assertEqual(kwargs['env']['FARM_SUPERVISOR_PID'],str(os.getpid()))
            calls.append(kwargs['env']['FARM_ACCOUNT'])
            return children[len(calls)-1]
        calls=[]
        with patch.object(farm_multi,'require_calibrated_client',side_effect=lambda env:checked.append(env['FARM_ACCOUNT'])), \
                patch.object(farm_multi,'Mutex'),patch.object(farm_multi.subprocess,'Popen',side_effect=spawn), \
                patch.object(farm_multi,'close_children') as close,patch.object(farm_multi.time,'sleep') as wait:
            self.assertEqual(farm_multi.run_trial(data),{account:0 for account in data})
            self.assertEqual(calls,list(data));wait.assert_called_once_with(.05)
            close.assert_called_once_with(children)
        for p in children:p.send_signal.assert_not_called()

    def test_worker_failure_stops_only_owned_survivors_without_restarting(self):
        children=[Mock() for _ in range(3)]
        children[0].poll.return_value=2
        for p in children[1:]:p.poll.return_value=None
        with patch.object(farm_multi,'require_calibrated_client'),patch.object(farm_multi,'Mutex') as mutex, \
                patch.object(farm_multi.subprocess,'Popen',side_effect=children) as spawn, \
                patch.object(farm_multi,'close_children') as close:
            with self.assertRaises(RuntimeError):farm_multi.run_trial(sessions())
            self.assertEqual(spawn.call_count,3);close.assert_called_once_with(children)
            mutex.return_value.close.assert_called_once()
        children[0].send_signal.assert_not_called()
        for p in children[1:]:p.send_signal.assert_called_once_with(signal.SIGINT)

    def test_partial_launch_stop_and_cleanup_error_release_supervisor_lock(self):
        for error in (OSError('spawn failed'),KeyboardInterrupt()):
            child=Mock();child.poll.return_value=None
            with patch.object(farm_multi,'require_calibrated_client'),patch.object(farm_multi,'Mutex') as mutex, \
                    patch.object(farm_multi.subprocess,'Popen',side_effect=[child,error]), \
                    patch.object(farm_multi,'close_children') as close:
                with self.assertRaises(type(error)):farm_multi.run_trial(sessions())
                child.send_signal.assert_called_once_with(signal.SIGINT);close.assert_called_once_with([child])
                mutex.return_value.close.assert_called_once()

    def test_stop_during_monitoring_and_signal_error_still_clean_up_every_worker(self):
        children=[Mock() for _ in range(3)]
        for p in children:p.poll.return_value=None
        children[0].send_signal.side_effect=ProcessLookupError()
        with patch.object(farm_multi,'require_calibrated_client'),patch.object(farm_multi,'Mutex') as mutex, \
                patch.object(farm_multi.subprocess,'Popen',side_effect=children), \
                patch.object(farm_multi.time,'sleep',side_effect=KeyboardInterrupt), \
                patch.object(farm_multi,'close_children',side_effect=RuntimeError('cleanup')) as close:
            with self.assertRaises(RuntimeError):farm_multi.run_trial(sessions())
            for p in children:p.send_signal.assert_called_once_with(signal.SIGINT)
            close.assert_called_once_with(children);mutex.return_value.close.assert_called_once()

    @unittest.skipUnless(sys.platform=='linux','Probes inertes Linux')
    def test_real_three_probe_supervision_uses_panel_stop_and_preserves_other_process(self):
        from types import SimpleNamespace
        from fishing_core import farm_app,global_stop
        real_spawn=subprocess.Popen;real_sleep=farm_multi.time.sleep;real_stop=global_stop.stop_workers
        workers=[]
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp, \
                patch.dict(os.environ,{'XDG_RUNTIME_DIR':tmp}):
            other=real_spawn([sys.executable,'-B','-c','import signal;print("READY",flush=True);signal.pause()'],
                             cwd=farm_multi.ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                self.assertEqual(other.stdout.readline().strip(),'READY')
                def spawn(argv,**kwargs):
                    p=real_spawn([sys.executable,'-B','-m','fishing_core.global_stop','--probe'],
                                 **kwargs,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                    workers.append(p);self.assertEqual(p.stdout.readline().strip(),'PROBE_READY');return p
                stopped=False
                def request_stop(delay):
                    nonlocal stopped
                    if not stopped:
                        self.assertEqual(len(workers),3);self.assertTrue(all(p.poll() is None for p in workers))
                        selection=Path(tmp)/'proc';selection.mkdir()
                        for p in [*workers,other]:(selection/str(p.pid)).symlink_to(Path('/proc')/str(p.pid))
                        app=SimpleNamespace(process=workers[0],status='EN MARCHA')
                        with patch.object(global_stop,'stop_workers',side_effect=lambda:real_stop(selection)):
                            farm_app.FarmApp.toggle_run(app)
                        self.assertEqual(app.status,'DETENIENDO...');stopped=True
                    real_sleep(delay)
                with patch.object(farm_multi,'require_calibrated_client'), \
                        patch.object(farm_multi.subprocess,'Popen',side_effect=spawn) as launched, \
                        patch.object(farm_multi.time,'sleep',side_effect=request_stop):
                    self.assertEqual(farm_multi.run_trial(sessions()),{account:0 for account in sessions()})
                    self.assertEqual(launched.call_count,3)
                for p in workers:
                    out,err=p.communicate(timeout=5);self.assertEqual(p.returncode,0,err);self.assertIn('PROBE_STOPPED',out)
                self.assertIsNone(other.poll(),'STOP del supervisor alcanzó otro Python')
            finally:
                for p in [*workers,other]:
                    if p.poll() is None:p.terminate()
                    p.communicate(timeout=5)


if __name__=='__main__':unittest.main()
