"""Cadena de modos: pausa si el usuario usa el ordenador, un reintento y reanudación tras START."""

import tempfile
import os
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from fishing_core import farm_all
from fishing_core.control_flow import SafetyStop
from fishing_core.processes import Mutex


class RunStepsTests(unittest.TestCase):
    def run_chain(self,plan,progress,waits=True):
        results=[]
        with patch.object(farm_all,'steps',return_value=plan),patch.object(farm_all,'PROGRESS',progress), \
                patch.object(farm_all,'wait_for_game_focus',return_value=waits) as focus:
            farm_all.run_steps({},results,False,lambda m:False,lambda:False,{})
        return results,focus

    def failing(self,*errors):
        calls=[];errors=list(errors)
        def step():
            calls.append(1)
            if errors:raise errors.pop(0)
        return step,calls

    def test_focus_loss_pauses_and_the_same_mode_continues(self):
        with tempfile.TemporaryDirectory() as tmp:
            quest,calls=self.failing(SafetyStop('Steam perdio el foco o cambio su identidad en niri; no se envia input'))
            results,focus=self.run_chain([('Quest',quest),('PvP',lambda:None)],Path(tmp)/'p.json')
            self.assertEqual(results,[('Quest','OK'),('PvP','OK')]);self.assertEqual(len(calls),2);focus.assert_called_once()
            self.assertFalse((Path(tmp)/'p.json').exists())  # ciclo completo: el próximo START empieza de nuevo

    def test_other_stops_are_retried_once_and_then_the_next_start_resumes(self):
        with tempfile.TemporaryDirectory() as tmp:
            progress=Path(tmp)/'p.json';ran=[]
            raid,calls=self.failing(SafetyStop('Pantalla no confirmada'),SafetyStop('Pantalla no confirmada'))
            results,_=self.run_chain([('Quest',lambda:ran.append('Quest')),('Raid',raid),('Trials',lambda:ran.append('Trials'))],progress)
            self.assertEqual(results,[('Quest','OK'),('Raid','Pantalla no confirmada')]);self.assertEqual(len(calls),2)
            results,_=self.run_chain([('Quest',lambda:ran.append('Quest')),('Raid',lambda:None),('Trials',lambda:ran.append('Trials'))],progress)
            self.assertEqual(results[0],('Quest','OK (ya hecho)'));self.assertEqual(ran,['Quest','Trials'])


    def test_reaching_the_one_hour_session_limit_opens_another_session_without_using_the_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            limit=SafetyStop('Límite de sesión: 60 minutos')
            raid,calls=self.failing(limit,limit,limit,SafetyStop('Pantalla no confirmada'))
            results,_=self.run_chain([('Raid',raid)],Path(tmp)/'p.json')
            self.assertEqual(results,[('Raid','OK')]);self.assertEqual(len(calls),5)  # 3 sesiones más + 1 reintento

    def test_account_crash_does_not_signal_a_frame_server_or_relaunch_any_game(self):
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp,patch.dict(os.environ,{'FARM_ACCOUNT':'steam'}), \
                patch.object(farm_all,'PROGRESS',Path(tmp)/'progress.json'),patch.object(farm_all,'stop_frame_server') as stop:
            quest,calls=self.failing(SafetyStop('gamescope no responde'),SafetyStop('gamescope no responde'))
            relaunch=Mock(return_value=False);results=[]
            with patch.object(farm_all,'steps',return_value=[('Quest',quest)]):
                farm_all.run_steps({},results,True,lambda m:True,relaunch,{'proc':None})
            self.assertEqual(results,[('Quest','gamescope no responde')]);self.assertEqual(len(calls),2)
            stop.assert_not_called();relaunch.assert_not_called()

    def test_brave_safety_stops_do_not_restart_or_accept_a_new_client_baseline(self):
        for account in ('personal','perfil-1'):
            for message in ('Cambió la identidad de Brave','El proceso Brave original terminó',
                            'CDP no confirma la identidad, foco o geometría de Brave',
                            'Geometría no confirmada','DISCONNECTED','Pantalla UNKNOWN'):
                with self.subTest(account=account,message=message),tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp, \
                        patch.dict(os.environ,{'FARM_ACCOUNT':account}),patch.object(farm_all,'PROGRESS',Path(tmp)/'progress.json'):
                    quest,calls=self.failing(SafetyStop(message));next_mode=Mock();results=[];relaunch=Mock()
                    with patch.object(farm_all,'steps',return_value=[('Quest',quest),('PvP',next_mode)]):
                        farm_all.run_steps({},results,True,lambda m:True,relaunch,{'proc':None})
                    relaunch.assert_not_called()  # un cliente Brave nunca se relanza ni se sustituye
                    if 'Cambió la identidad' in message or 'terminó' in message:
                        self.assertEqual(results,[('Quest',message)]);self.assertEqual(len(calls),1);next_mode.assert_not_called()
                    else:  # fallo momentáneo: un único reintento con los mismos endpoints fijados
                        self.assertEqual(results,[('Quest','OK'),('PvP','OK')]);self.assertEqual(len(calls),2)

    def test_a_second_brave_stop_in_the_same_mode_is_final(self):
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp, \
                patch.dict(os.environ,{'FARM_ACCOUNT':'personal'}),patch.object(farm_all,'PROGRESS',Path(tmp)/'progress.json'):
            quest,calls=self.failing(SafetyStop('Pantalla UNKNOWN'),SafetyStop('Pantalla UNKNOWN'));results=[]
            with patch.object(farm_all,'steps',return_value=[('Quest',quest)]):
                farm_all.run_steps({},results,True,lambda m:False,Mock(),{'proc':None})
            self.assertEqual(results,[('Quest','Pantalla UNKNOWN')]);self.assertEqual(len(calls),2)

    def test_duplicate_chain_is_refused_before_loading_config_or_starting_a_frame_server(self):
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp, \
                patch.dict(os.environ,{'XDG_RUNTIME_DIR':tmp,'FARM_ACCOUNT':'steam','FARM_BACKEND':'gamescope',
                                      'FARM_GAMESCOPE_DISPLAY':':12','FARM_GAMESCOPE_SERIAL':'4500'}), \
                patch.object(farm_all.farm_config,'load',return_value={}) as load, \
                patch.object(farm_all,'start_frame_server') as start,patch.object(farm_all,'run_steps'), \
                patch.object(farm_all.loot,'ENABLED',False):
            lock=Mutex('FARM_ALL')
            try:
                with self.assertRaises(RuntimeError):farm_all.main([])
                load.assert_not_called();start.assert_not_called()
            finally:lock.close()

    def test_failed_frame_server_start_is_reported_instead_of_using_an_unavailable_stream(self):
        process=Mock();process.poll.return_value=2
        with patch('fishing_core.gamescope.server_alive',return_value=False), \
                patch.object(farm_all.subprocess,'Popen',return_value=process),patch.object(farm_all.time,'sleep'):
            with self.assertRaises(RuntimeError):farm_all.start_frame_server()


class SingleDungeonTests(unittest.TestCase):
    def test_main_reports_failures_and_closes_lock(self):
        for result in ('OK','OK (ya hecho)','F8','Pantalla UNKNOWN','Derrota'):
            with self.subTest(result=result),patch.dict(os.environ,{},clear=True), \
                    patch('fishing_core.gamescope.require_calibrated_client'), \
                    patch('fishing_core.processes.Mutex') as mutex, \
                    patch.object(farm_all.farm_config,'load',return_value={}), \
                    patch.object(farm_all,'run_steps',side_effect=lambda c,r,*args:r.append(('Quest',result))), \
                    patch.object(farm_all,'report') as report:
                if result.startswith('OK'):farm_all.main([])
                else:
                    with self.assertRaises(SystemExit) as exc:farm_all.main([])
                    self.assertEqual(exc.exception.code,1)
                report.assert_called_once_with([('Quest',result)])
                mutex.return_value.close.assert_called_once()

    def test_limited_worker_marker_cannot_run_or_save_the_general_chain(self):
        env={'FARM_ACCOUNT':'steam','FARM_BACKEND':'gamescope','FARM_GAMESCOPE_DISPLAY':':12',
             'FARM_GAMESCOPE_SERIAL':'4500','FARM_SINGLE_DUNGEON':'1'}
        with patch.dict(os.environ,env,clear=True),patch('fishing_core.processes.Mutex'), \
                patch.object(farm_all.farm_config,'load',return_value={}) as load, \
                patch.object(farm_all,'start_frame_server') as server,patch.object(farm_all,'run_steps') as chain:
            with self.assertRaises(ValueError):farm_all.main([])
            load.assert_not_called();server.assert_not_called();chain.assert_not_called()

    def test_steam_without_legacy_files_can_still_start_its_own_frame_server(self):
        from fishing_core import gamescope
        env={'FARM_ACCOUNT':'steam','FARM_BACKEND':'gamescope','FARM_GAMESCOPE_DISPLAY':':12','FARM_GAMESCOPE_SERIAL':'4500'}
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp,patch.dict(os.environ,env,clear=True), \
                patch.object(gamescope,'LEGACY_SHM',str(Path(tmp)/'absent')), \
                patch.object(gamescope,'server_alive',side_effect=[False,True]), \
                patch.object(farm_all.subprocess,'Popen') as spawn:
            self.assertIs(farm_all.start_frame_server(),spawn.return_value)
            self.assertEqual(spawn.call_count,1)

    def test_farming_never_starts_or_reuses_a_stream_when_unverified_legacy_steam_files_remain(self):
        from fishing_core import gamescope
        env={'FARM_ACCOUNT':'steam','FARM_BACKEND':'gamescope','FARM_GAMESCOPE_DISPLAY':':12','FARM_GAMESCOPE_SERIAL':'4500'}
        for existing in ('frame','pid','symlink'):
            for alive in (False,True):
                with self.subTest(existing=existing,alive=alive),tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
                    source=Path(tmp)/'frame'
                    if existing=='frame':source.write_bytes(b'keep')
                    elif existing=='pid':Path(str(source)+'.pid').write_text('123')
                    else:source.symlink_to(source.with_name('missing'))
                    with patch.dict(os.environ,env,clear=True),patch.object(gamescope,'LEGACY_SHM',str(source)), \
                            patch.object(gamescope,'server_alive',return_value=alive), \
                            patch.object(gamescope,'legacy_steam_frames',return_value=False) as legacy, \
                            patch.object(farm_all.subprocess,'Popen') as spawn:
                        with self.assertRaisesRegex(RuntimeError,'antiguo'):farm_all.start_frame_server()
                        spawn.assert_not_called();legacy.assert_called_once()
                    if existing=='frame':self.assertEqual(source.read_bytes(),b'keep')
                    elif existing=='pid':self.assertEqual(Path(str(source)+'.pid').read_text(),'123')
                    else:self.assertTrue(source.is_symlink())

    def test_stop_check_never_duplicates_a_verified_or_uncertain_legacy_steam_stream(self):
        from fishing_core import gamescope
        env={'FARM_ACCOUNT':'steam','FARM_BACKEND':'gamescope','FARM_GAMESCOPE_DISPLAY':':12','FARM_GAMESCOPE_SERIAL':'4500'}
        for verified,existing in ((True,None),(False,'frame'),(False,'pid')):
            with self.subTest(verified=verified,existing=existing),tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
                source=Path(tmp)/'frame'
                if existing=='frame':source.touch()
                elif existing=='pid':Path(str(source)+'.pid').write_text('123')
                with patch.dict(os.environ,env,clear=True),patch.object(gamescope,'LEGACY_SHM',str(source)), \
                        patch.object(gamescope,'server_alive',return_value=False), \
                        patch.object(gamescope,'legacy_steam_frames',return_value=verified), \
                        patch.object(farm_all.subprocess,'Popen') as spawn:
                    if verified:self.assertIsNone(farm_all.start_frame_server(read_only=True))
                    else:
                        with self.assertRaisesRegex(RuntimeError,'antiguo'):farm_all.start_frame_server(read_only=True)
                    spawn.assert_not_called()

    def test_farming_reuses_verified_legacy_steam_but_refuses_a_second_account_source(self):
        from fishing_core import gamescope
        env={'FARM_ACCOUNT':'steam','FARM_BACKEND':'gamescope','FARM_GAMESCOPE_DISPLAY':':12','FARM_GAMESCOPE_SERIAL':'4500'}
        for alive in (False,True):
            with self.subTest(alive=alive),tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp, \
                    patch.dict(os.environ,env,clear=True),patch.object(gamescope,'LEGACY_SHM',str(Path(tmp)/'legacy')), \
                    patch.object(gamescope,'server_alive',return_value=alive), \
                    patch.object(gamescope,'legacy_steam_frames',return_value=True), \
                    patch.object(farm_all.subprocess,'Popen') as spawn:
                if alive:
                    with self.assertRaisesRegex(RuntimeError,'ambigua'):farm_all.start_frame_server()
                else:self.assertIsNone(farm_all.start_frame_server())
                spawn.assert_not_called()

    def test_stop_check_selects_read_only_worker_and_cannot_mix_with_farming_flags(self):
        from fishing_core import farm_config
        env={'FARM_ACCOUNT':'personal','FARM_BACKEND':'gamescope','FARM_GAMESCOPE_DISPLAY':':12','FARM_GAMESCOPE_SERIAL':'4500'}
        env.update(FARM_BRAVE_PID='1234',FARM_BRAVE_CDP_PORT='45678',FARM_BRAVE_TARGET_ID='A'*32)
        with patch.dict(os.environ,env),patch('fishing_core.processes.Mutex'), \
                patch.object(farm_config,'load',return_value=farm_config.DEFAULT),patch.object(farm_all,'start_frame_server') as server, \
                patch.object(farm_all,'quest') as quest,patch.object(farm_all,'run_steps') as steps:
            farm_all.main(['--stop-check'])
            server.assert_called_once_with(read_only=True);quest.assert_called_once_with(farm_config.DEFAULT,single=True,read_only=True)
            steps.assert_not_called()
            with self.assertRaises(ValueError):farm_all.main(['--stop-check','--runes'])

    def test_trial_plan_overrides_spending_and_targets_without_changing_config(self):
        import copy
        from fishing_core import farm_config
        config=copy.deepcopy(farm_config.DEFAULT);before=copy.deepcopy(config)
        plan=farm_all.quest_plan(config,single=True)
        self.assertEqual((plan['dungeon_id'],plan['difficulty'],plan['runs'],plan['energy_limit'],plan['max_gold'],plan['targets']),
                         ('Z5D3','Normal',1,10,0,[]))
        self.assertEqual(config,before)
        legacy=farm_all.quest_plan(config)
        self.assertEqual((legacy['difficulty'],legacy['runs'],legacy['energy_limit'],legacy['max_gold'],legacy['targets']),
                         ('Heroic',60,1000,50_000,['Tealk']))

    def test_trial_refuses_special_or_uncalibrated_routes_without_substitution(self):
        from fishing_core import farm_config
        for dungeon in ('Z1D4','Z10D1','unknown'):
            config={**farm_config.DEFAULT,'quest':{'dungeon':dungeon}}
            with self.subTest(dungeon=dungeon),self.assertRaises(ValueError):farm_all.quest_plan(config,single=True)

    def test_single_dungeon_main_does_not_resume_retry_or_save_preferences(self):
        from fishing_core import farm_config
        with patch.dict(os.environ,{'FARM_ACCOUNT':'steam','FARM_BACKEND':'gamescope','FARM_GAMESCOPE_DISPLAY':':12',
                                    'FARM_GAMESCOPE_SERIAL':'4500'}), \
                patch('fishing_core.processes.Mutex') as mutex,patch.object(farm_config,'load',return_value=farm_config.DEFAULT), \
                patch.object(farm_config,'save') as save,patch.object(farm_all,'start_frame_server'), \
                patch.object(farm_all,'quest',side_effect=SafetyStop('UNKNOWN')) as quest, \
                patch.object(farm_all,'run_steps') as steps,patch.object(farm_all,'load_progress') as resume, \
                patch.object(farm_all.loot,'ENABLED',False):
            with self.assertRaises(SafetyStop):farm_all.main(['--single-dungeon'])
            quest.assert_called_once_with(farm_config.DEFAULT,single=True)
            save.assert_not_called();steps.assert_not_called();resume.assert_not_called();mutex.return_value.close.assert_called_once()

    def test_user_stop_closes_the_owned_dungeon_before_releasing_its_mutex(self):
        from fishing_core import dungeon_runtime, farm_config
        process=Mock();process.wait.side_effect=KeyboardInterrupt;channel=Mock();mutex=Mock();actions=[]
        mutex.close.side_effect=lambda:actions.append('unlock')
        with patch.dict(os.environ,{'FARM_BACKEND':'gamescope'}), \
                patch.object(dungeon_runtime,'start_dungeon',return_value=(process,channel,mutex)), \
                patch('fishing_core.processes.close_children',side_effect=lambda *args:actions.append('stop')) as close:
            with self.assertRaises(KeyboardInterrupt):farm_all.quest(farm_config.DEFAULT)
            close.assert_called_once_with((process,),channel)
        self.assertEqual(actions,['stop','unlock'])

    def test_losing_the_supervisor_stops_the_owned_dungeon_without_a_restart(self):
        import subprocess
        from fishing_core import dungeon_runtime, farm_config
        process=Mock();process.wait.side_effect=subprocess.TimeoutExpired('dungeon',.2)
        channel=Mock();mutex=Mock()
        with patch.dict(os.environ,{'FARM_BACKEND':'gamescope','FARM_SUPERVISOR_PID':'1234'}), \
                patch.object(farm_all.os,'getppid',side_effect=[1234,1234,1]), \
                patch.object(dungeon_runtime,'start_dungeon',return_value=(process,channel,mutex)), \
                patch('fishing_core.processes.close_children') as close:
            with self.assertRaisesRegex(SafetyStop,'supervisor'):farm_all.quest(farm_config.DEFAULT,single=True)
            process.wait.assert_called_once_with(timeout=.2);close.assert_called_once_with((process,),channel)
            mutex.close.assert_called_once()

    def test_missing_supervisor_is_refused_before_starting_the_dungeon(self):
        from fishing_core import dungeon_runtime,farm_config
        with patch.dict(os.environ,{'FARM_BACKEND':'gamescope','FARM_SUPERVISOR_PID':'1234'}), \
                patch.object(farm_all.os,'getppid',return_value=1),patch.object(dungeon_runtime,'start_dungeon') as start:
            with self.assertRaisesRegex(SafetyStop,'supervisor'):farm_all.quest(farm_config.DEFAULT,single=True)
            start.assert_not_called()


if __name__=='__main__':unittest.main()


class FarmAllBoostsStepTests(unittest.TestCase):
    def test_weekly_expedition_uses_gvg_and_can_return_to_expedition(self):
        import copy
        from fishing_core import farm_config
        config=copy.deepcopy(farm_config.DEFAULT)
        config['boosts']=False;config['runes']=False
        config['modes']={key:key=='expedition' for key in config['modes']}
        for weekly,name,module,function in (('GVG','GvG','gvg_runtime','run_gvg'),
                                             ('EXPEDITION','Expedition','expedition_runtime','run_expedition')):
            with self.subTest(weekly=weekly),patch.object(farm_all,'WEEKLY_EXPEDITION',weekly), \
                    patch(f'fishing_core.{module}.{function}') as run:
                steps=farm_all.steps(config);self.assertEqual([n for n,_ in steps],[name])
                steps[0][1]();run.assert_called_once_with(60)

    def test_boosts_go_first_and_can_be_turned_off(self):
        from fishing_core import farm_config
        config=farm_config.load(Path('/nonexistent/farm_config.json'))
        self.assertEqual(farm_all.steps(config)[0][0],'Boosts')
        config['boosts']=False
        self.assertNotIn('Boosts',[name for name,_ in farm_all.steps(config)])
