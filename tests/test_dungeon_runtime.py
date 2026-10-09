import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch

import numpy as np

from fishing_core.control_flow import SafetyStop
from fishing_core.dungeon_catalog import farm_plan
from fishing_core.dungeon_runtime import NODES, DungeonRunner,validate_supported
from fishing_core.farm_budget import FarmBudget


class DungeonRuntimeTests(unittest.TestCase):
    def test_reconnect_rebaselines_before_capture_if_supported(self):
        for supported in (False,True):
            with self.subTest(supported=supported),tempfile.TemporaryDirectory() as tmp:
                runner,io,vision=self.runner(Path(tmp))
                if not supported:del io.rebaseline_web
                vision.locate.return_value=None
                vision.screen.side_effect=lambda frame:frame
                runner.wait=Mock(side_effect=['DISCONNECTED','HOME','HOME']);runner.click=Mock()
                if supported:io.rebaseline_web.side_effect=lambda:self.assertEqual(runner.wait.call_count,1)
                with patch('fishing_core.dungeon_runtime.time.sleep'):
                    self.assertEqual(runner.ensure_home(),'HOME')
                runner.click.assert_called_once_with('DISCONNECTED',(960,742),'RECONNECT',(770,665,1150,820))
                if supported:io.rebaseline_web.assert_called_once()
                self.assertEqual(runner.wait.call_args_list[1].args[1:],(90,'reconexión'))

    def test_reconnect_retries_without_capture_or_input_until_success_or_90_seconds(self):
        for succeeds in (True,False):
            with self.subTest(succeeds=succeeds),tempfile.TemporaryDirectory() as tmp:
                runner,io,vision=self.runner(Path(tmp));clock=[0.0];errors=[];attempts=[]
                vision.locate.return_value=None;vision.screen.side_effect=lambda frame:frame
                runner.wait=Mock(side_effect=['DISCONNECTED','HOME','HOME']);runner.click=Mock()
                def renew():
                    attempts.append(clock[0])
                    self.assertEqual(runner.wait.call_count,1)
                    self.assertEqual(runner.capture.call_count,1)
                    self.assertEqual(runner.click.call_count,1)
                    io.click.assert_not_called();io._move.assert_not_called();io.escape.assert_not_called()
                    if succeeds and len(attempts)==3:return
                    error=SafetyStop(f'iframe recargando {len(attempts)}');errors.append(error);raise error
                io.rebaseline_web.side_effect=renew
                with patch('fishing_core.dungeon_runtime.time.monotonic',side_effect=lambda:clock[0]), \
                        patch('fishing_core.dungeon_runtime.time.sleep',side_effect=lambda seconds:clock.__setitem__(0,clock[0]+seconds)):
                    if succeeds:self.assertEqual(runner.ensure_home(),'HOME')
                    else:
                        with self.assertRaises(SafetyStop) as caught:runner.ensure_home()
                        self.assertIs(caught.exception,errors[-1])
                        self.assertAlmostEqual(clock[0]-attempts[0],90)
                self.assertEqual(len(attempts),3 if succeeds else 45)
                for index,attempt in enumerate(attempts):self.assertAlmostEqual(attempt-attempts[0],index*2)

    def test_reconnect_does_not_retry_emergency_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,vision=self.runner(Path(tmp))
            vision.locate.return_value=None;vision.screen.side_effect=lambda frame:frame
            runner.wait=Mock(return_value='DISCONNECTED');runner.click=Mock()
            io.emergency.side_effect=KeyboardInterrupt('F8')
            with patch('fishing_core.dungeon_runtime.time.sleep'),self.assertRaises(KeyboardInterrupt):runner.ensure_home()
            io.rebaseline_web.assert_not_called()

    def test_limited_worker_marker_enforces_one_normal_zero_gold_and_no_targets_in_the_shared_validator(self):
        plan=farm_plan('Z1D2','Normal',1,10)
        with patch.dict(os.environ,{'FARM_SINGLE_DUNGEON':'1'},clear=True):
            self.assertEqual(validate_supported(plan)['runs'],1)
            for changes in ({'runs':2},{'energy_limit':11},{'max_gold':1},{'targets':['Bob']},{'difficulty':'Hard'}):
                with self.subTest(changes=changes),self.assertRaises(ValueError):validate_supported({**plan,**changes})

    def test_stop_check_flag_reaches_the_dungeon_process_without_spawning_it(self):
        from fishing_core import dungeon_runtime as runtime
        plan=farm_plan('Z5D2','Normal',1,10)
        with patch.object(runtime,'Mutex'),patch.object(runtime,'Channel'),patch.object(runtime,'atomic_json'), \
                patch.object(runtime,'run_environment',return_value={'FISHING_RUN_ID':'test'}), \
                patch.object(runtime.subprocess,'Popen') as spawn:
            runtime.start_dungeon(None,plan,read_only=True)
            self.assertEqual(spawn.call_args.args[0][-1],'--stop-check')
            self.assertEqual(spawn.call_args.kwargs['env']['FARM_LAUNCHER_PID'],str(os.getpid()))

    def test_stop_check_runtime_dispatches_only_observation_and_cleans_owned_guards(self):
        from fishing_core import dungeon_runtime as runtime
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
            directory=Path(tmp);(directory/'farm_plan.json').write_text(json.dumps(farm_plan('Z5D2','Normal',1,10)))
            io=Mock();capture=Mock()
            with patch.dict(os.environ,{'FISHING_RUN_ID':'test'},clear=True), \
                    patch('fishing_core.gamescope.backend',return_value=(Mock(return_value=io),capture)) as backend, \
                    patch.object(runtime,'Channel',return_value=SimpleNamespace(directory=directory,run_id='test')), \
                    patch.object(runtime,'Mutex') as lock,patch.object(runtime,'Telemetry') as log, \
                    patch.object(runtime,'DungeonVision'),patch.object(runtime,'DungeonRunner') as runner:
                capture.return_value.__enter__=Mock(return_value=Mock());capture.return_value.__exit__=Mock(return_value=False)
                runtime.run_dungeon(read_only=True)
                backend.assert_called_once_with(read_only=True)
                runner.return_value.observe_until_stopped.assert_called_once_with();runner.return_value.run.assert_not_called()
                io.close.assert_called_once_with();log.return_value.close.assert_called_once_with()
                self.assertEqual(lock.return_value.close.call_count,2)

    def test_observation_keeps_f8_ipc_parent_and_deadline_guards_before_any_frame(self):
        for stop in ('F8','IPC','parent','deadline'):
            with self.subTest(stop=stop),tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp, \
                    patch.dict(os.environ,{},clear=True),patch('fishing_core.dungeon_runtime.os.getppid',return_value=1):
                runner,io,vision=self.runner(Path(tmp));io.read_only=True;del runner.capture
                vision.screen.return_value='HOME'
                if stop=='F8':io.emergency.side_effect=KeyboardInterrupt('F8')
                elif stop=='IPC':runner.channel.stop_path.write_text('{}')
                elif stop=='parent':os.environ['FARM_LAUNCHER_PID']='1234'
                else:runner.deadline=time.monotonic()-1
                with self.assertRaises(KeyboardInterrupt if stop=='F8' else SafetyStop):runner.observe_until_stopped()
                runner.cap.grab.assert_not_called();io.click.assert_not_called();io.escape.assert_not_called()
                self.assertFalse((Path(tmp)/'stop_check_ready.json').exists())

    def test_stop_observation_requires_home_and_records_zero_entries_before_waiting_for_stop(self):
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
            runner,io,vision=self.runner(Path(tmp));io.read_only=True;vision.screen.return_value='HOME'
            runner.capture.side_effect=['frame','frame',KeyboardInterrupt('STOP')]
            with self.assertRaises(KeyboardInterrupt):runner.observe_until_stopped()
            ready=json.loads((Path(tmp)/'stop_check_ready.json').read_text())
            self.assertEqual(ready['screen'],'HOME');self.assertEqual(ready['budget']['entries_reserved'],0)
            self.assertEqual(ready['budget']['energy_reserved'],0)
            io.click.assert_not_called();io._move.assert_not_called();io.escape.assert_not_called()

    def test_stop_observation_refuses_unknown_screen_or_an_input_enabled_backend(self):
        for read_only,state in ((False,'HOME'),(True,'UNKNOWN'),(True,'DISCONNECTED')):
            with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
                runner,io,vision=self.runner(Path(tmp));io.read_only=read_only;vision.screen.return_value=state
                with self.assertRaises(SafetyStop):runner.observe_until_stopped()
                self.assertFalse((Path(tmp)/'stop_check_ready.json').exists())
                io.click.assert_not_called();io.escape.assert_not_called()

    def test_uncertified_routes_are_not_silently_substituted(self):
        validate_supported(farm_plan('Z5D2','Normal',1,30))
        validate_supported(farm_plan('Z5D3','Heroic',1,30,'Tealk'))
        validate_supported(farm_plan('Z5D3','Heroic',6,180,'Tealk'))  # repetición, como Z5D2
        validate_supported(farm_plan('Z5D3','Normal',17,170,'Tealk'))  # al agotarse Heroic
        validate_supported(farm_plan('Z5D3','Hard',1,30,'Tealk'));validate_supported(farm_plan('Z5D2','Heroic',1,30))
        validate_supported(farm_plan('Z1D4','Special',1,30))  # especial: ENTER de 20
        for args in [('Z1D2','Normal',1,30,'Tealk'),('Z10D1','Normal',1,30,'')]:  # Z10+: nodos sin calibrar
            with self.assertRaises(ValueError):validate_supported(farm_plan(*args))

    def test_tealk_heroic_reserves_thirty_once_and_rejects_the_normal_cost(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,vision=self.runner(Path(tmp))
            runner.plan=farm_plan('Z5D3','Heroic',1,30,'Tealk');runner.difficulty='Heroic'
            with self.assertRaises(SafetyStop):runner.enter(1)
            io.click.assert_not_called()
            runner.cost=30
            runner.enter(1)
            self.assertEqual(runner.budget.energy_reserved,30)
            with self.assertRaises(SafetyStop):runner.enter(1)
            self.assertEqual(io.click.call_count,1)

    def test_tealk_selection_never_clicks_another_dungeon_or_normal(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,vision=self.runner(Path(tmp));runner.plan=farm_plan('Z5D3','Heroic',1,30,'Tealk');runner.difficulty='Heroic'
            runner.wait=Mock(return_value='frame');runner.click=Mock();runner.select_zone=Mock()
            vision.cost.return_value=30
            runner.select_route()
            self.assertEqual(runner.cost,30)
            runner.select_zone.assert_called_once_with(5)
            self.assertEqual([args.args[:2] for args in runner.click.call_args_list],
                             [('HOME',(90,90)),('MAP_Z5',NODES['Z5D3']),('DIFFICULTY',(1365,495))])
            runner.click.reset_mock();vision.cost.return_value=10
            with self.assertRaises(SafetyStop):runner.select_route()
            self.assertNotIn('DIFFICULTY',[args.args[0] for args in runner.click.call_args_list])

    def runner(self,path):
        plan=farm_plan('Z5D2','Normal',1,30)
        channel=SimpleNamespace(directory=path,run_id='test',stop_path=path/'stop.json')
        io=Mock();vision=Mock(screen=Mock(return_value='TEAM'),energy=Mock(return_value=(100,368)),
                            locate=Mock(return_value=(1000,943)),
                            templates={'TOWN':np.zeros((114,300,3),np.uint8)})  # centro de TOWN en (1150,1000)
        runner=DungeonRunner(io,Mock(),vision,channel,Mock(),plan)
        runner.capture=Mock(return_value='frame')
        def wait(predicate,timeout=10,expected=None):
            if callable(predicate):
                predicate('frame')
                if not predicate('frame'):raise SafetyStop('Lectura no confirmada')
            return 'frame'
        runner.wait=wait
        runner.cost=10;runner.safety_checked=True
        return runner,io,vision

    def test_accept_intent_is_durable_and_reserved_before_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,_=self.runner(Path(tmp))
            def click(_):
                self.assertTrue((Path(tmp)/'entry-1.intent.json').exists())
                self.assertEqual(runner.budget.energy_reserved,10)
            io.click.side_effect=click
            runner.enter(1)
            self.assertEqual(io.click.call_count,1)
            with self.assertRaises(SafetyStop):runner.enter(1)
            self.assertEqual(io.click.call_count,1)

    def test_invalid_energy_cost_or_native_settings_never_send_accept(self):
        cases=[(None,10,True),((5,368),10,True),((100,368),None,True),((100,368),10,False),((100,368),40,True)]
        for balance,cost,safe in cases:
            with tempfile.TemporaryDirectory() as tmp:
                runner,io,vision=self.runner(Path(tmp));vision.energy.return_value=balance
                runner.cost=cost;runner.safety_checked=safe
                with self.assertRaises((SafetyStop,ValueError)):runner.enter(1)
                io.click.assert_not_called()

    def test_stop_focus_change_and_unknown_screen_block_all_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,vision=self.runner(Path(tmp))
            for failure in ('UNKNOWN','stop','focus','F8'):
                vision.screen.return_value='TEAM';io.check_game.side_effect=None;io.emergency.side_effect=None
                if failure=='UNKNOWN':vision.screen.return_value='UNKNOWN'
                if failure=='stop':runner.channel.stop_path.write_text('{}')
                if failure=='focus':io.check_game.side_effect=SafetyStop('focus')
                if failure=='F8':io.emergency.side_effect=KeyboardInterrupt('F8')
                with self.assertRaises((SafetyStop,KeyboardInterrupt)):runner.click('TEAM',(1215,982),'ACCEPT',(1000,930,1420,1035))
                io.click.assert_not_called()
                if runner.channel.stop_path.exists():runner.channel.stop_path.unlink()

    def test_wait_timeout_records_the_last_offer_without_retrying_or_resolving_it(self):
        import cv2
        from fishing_core.dungeon_vision import DungeonVision
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);runner,io,_=self.runner(path);runner.vision=DungeonVision()
            with np.load(Path(__file__).parent/'fixtures/dungeons.npz',allow_pickle=False) as data:
                frame=data['offer_sitra'].copy()
            frame[800:900,200:300]=123  # Información ajena al diálogo: debe ocultarse.
            runner.capture=Mock(return_value=frame)
            pending=path/'decline-1-3.intent.json';pending.write_text('{"effect_confirmed":false}')
            with patch('fishing_core.dungeon_runtime.time.monotonic',side_effect=[0,1,3]), \
                    patch('fishing_core.dungeon_runtime.time.sleep'):
                with self.assertRaisesRegex(SafetyStop,'observada FAMILIAR_OFFER.*Sitra'):
                    DungeonRunner.wait(runner,lambda _:False,timeout=2)
            event=runner.log.emit.call_args
            self.assertEqual(event.args,('DUNGEON_WAIT_TIMEOUT',))
            self.assertEqual(event.kwargs['screen'],'FAMILIAR_OFFER')
            self.assertEqual(event.kwargs['familiar'],'Sitra')
            snapshot=cv2.imread(str(path/event.kwargs['snapshot']))
            self.assertEqual(runner.vision.familiar_name(snapshot),'Sitra')
            self.assertFalse(snapshot[800:900,200:300].any())
            self.assertEqual(len(list(path.glob('wait-timeout-*.png'))),1)
            self.assertEqual(pending.read_text(),'{"effect_confirmed":false}')
            io.click.assert_not_called();io.escape.assert_not_called()
            self.assertEqual(runner.budget.payload()['entries_reserved'],0)

    def test_wait_never_takes_an_extra_capture_after_focus_loss_or_f8(self):
        for error in (SafetyStop('focus'),KeyboardInterrupt('F8')):
            with tempfile.TemporaryDirectory() as tmp:
                runner,io,_=self.runner(Path(tmp));runner.capture=Mock(side_effect=error)
                with self.assertRaises(type(error)):DungeonRunner.wait(runner,'HOME')
                runner.capture.assert_called_once();runner.log.emit.assert_not_called()
                self.assertEqual(list(Path(tmp).iterdir()),[])
                io.click.assert_not_called()

    def test_wait_remains_stopped_without_a_frame_or_when_evidence_cannot_be_written(self):
        import cv2
        for timeout,error in ((0,None),(2,False),(2,cv2.error('disk')),(2,OSError('disk'))):
            with self.subTest(timeout=timeout,error=error),tempfile.TemporaryDirectory() as tmp:
                runner,io,_=self.runner(Path(tmp))
                runner.capture=Mock(return_value=np.zeros((1080,1920,3),np.uint8))
                with patch('fishing_core.dungeon_runtime.time.monotonic',side_effect=[0,1,3]), \
                        patch('fishing_core.dungeon_runtime.time.sleep'), \
                        patch('fishing_core.dungeon_runtime.cv2.imwrite',return_value=False,
                              side_effect=error if isinstance(error,Exception) else None) as write:
                    with self.assertRaisesRegex(SafetyStop,'Pantalla no confirmada'):
                        DungeonRunner.wait(runner,'HOME',timeout=timeout)
                event=runner.log.emit.call_args.kwargs
                self.assertIsNone(event['snapshot'])
                self.assertEqual(event['screen'],'TEAM' if timeout else 'SIN_LECTURA')
                self.assertEqual(write.call_count,1 if timeout else 0)
                self.assertEqual(runner.capture.call_count,1 if timeout else 0)
                io.click.assert_not_called();io.escape.assert_not_called()

    def test_click_leaves_the_button_before_reading_its_new_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,vision=self.runner(Path(tmp));vision.screen.return_value='AUTO_OFF'
            steps=[]
            def click(xy):
                steps.append(('click',xy));vision.screen.return_value='UNKNOWN'  # Botón resaltado.
            def move(xy):
                steps.append(('move',xy));vision.screen.return_value='AUTO_ON'
            io.click.side_effect=click;io._move.side_effect=move
            with patch('fishing_core.dungeon_runtime.time.sleep',side_effect=lambda duration:steps.append(('settle',duration))):
                runner.click('AUTO_OFF',(1880,530))
            self.assertEqual(vision.screen(runner.capture()),'AUTO_ON')
            self.assertEqual(steps,[('click',(1880,530)),('settle',.25),('move',(960,1070))])

    def test_auto_activation_requires_confirmation_and_is_never_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,vision=self.runner(Path(tmp));runner.capture=Mock(return_value=np.zeros((1080,1920,3),np.uint8))
            vision.screen.return_value='AUTO_OFF';runner.click=Mock();requested=[]
            def wait(screen,timeout=10,expected=None):
                requested.append(expected or screen)
                if expected=='Auto del mapa activado':raise SafetyStop('Auto no confirmado')
                if len(requested)>1:raise SafetyStop('La observación continuó sin confirmar Auto')
                return runner.capture.return_value
            runner.wait=wait
            with self.assertRaisesRegex(SafetyStop,'Auto no confirmado'):runner.observe('test:1',1)
            self.assertEqual(requested,['AUTO_OFF','Auto del mapa activado'])
            runner.click.assert_called_once_with('AUTO_OFF',(1880,530))

    def test_town_can_return_to_quest_map_before_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,vision=self.runner(Path(tmp))
            vision.screen.return_value='MAP_Z5';io.escape.side_effect=lambda:setattr(vision.screen,'return_value','HOME')
            runner.go_home()
            io.escape.assert_called_once();io.click.assert_not_called()

    def test_escape_closes_only_recognized_navigation_and_never_retries(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,vision=self.runner(Path(tmp))
            for screen in ('UNKNOWN','FAMILIAR_OFFER','DECLINE_CONFIRM','VICTORY','AUTO_OFF','HOME'):
                vision.screen.return_value=screen
                with self.assertRaises(SafetyStop):runner.close_menu(screen)
            io.escape.assert_not_called();io.click.assert_not_called()
            vision.screen.return_value='SETTINGS';runner.wait=Mock(side_effect=['frame',SafetyStop('Destino no confirmado')])
            with self.assertRaisesRegex(SafetyStop,'Destino no confirmado'):runner.close_menu('SETTINGS')
            io.escape.assert_called_once();io.click.assert_not_called()

    def test_f8_focus_loss_and_stop_block_escape(self):
        for failure in ('F8','focus','stop'):
            with tempfile.TemporaryDirectory() as tmp:
                runner,io,vision=self.runner(Path(tmp));vision.screen.return_value='SETTINGS'
                if failure=='F8':io.emergency.side_effect=KeyboardInterrupt('F8')
                if failure=='focus':io.check_game.side_effect=SafetyStop('focus')
                if failure=='stop':runner.channel.stop_path.write_text('{}')
                with self.assertRaises((SafetyStop,KeyboardInterrupt)):runner.close_menu('SETTINGS')
                io.escape.assert_not_called()

    def test_go_home_unwinds_zones_then_any_known_map_with_escape_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,vision=self.runner(Path(tmp));states=iter(['MAP_Z20','HOME'])
            vision.screen.return_value='ZONES'
            io.escape.side_effect=lambda:setattr(vision.screen,'return_value',next(states))
            runner.go_home()
            self.assertEqual(vision.screen.return_value,'HOME')
            self.assertEqual(io.escape.call_count,2);io.click.assert_not_called()

    def test_zone_selection_uses_real_names_after_scroll_and_confirms_the_destination(self):
        from fishing_core.dungeon_vision import DungeonVision
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,_=self.runner(Path(tmp));runner.vision=vision=DungeonVision()
            with np.load(Path(__file__).parent/'fixtures/dungeons.npz',allow_pickle=False) as data:
                frames={k:data[k] for k in data.files}
            state=['MAP_Z20',16]
            def capture():return frames['zones_list_bottom' if state[0]=='ZONES' and state[1]==16 else
                                        'zones_list_top' if state[0]=='ZONES' else f'zones_map_{state[1]}']
            state[1]=20;runner.capture=capture
            def wait(predicate,timeout=10,expected=None):
                for _ in range(2):
                    frame=capture()
                    okay=predicate(frame) if callable(predicate) else vision.screen(frame)==predicate
                    if not okay:raise SafetyStop('Destino no confirmado')
                return frame
            runner.wait=wait
            def click(xy):
                if state[0]!='ZONES':
                    self.assertEqual(xy,(440,153));state[:]=['ZONES',16]
                else:
                    self.assertEqual(xy,vision.zone_choice(capture(),5));state[:]=['MAP_Z5',5]
            io.click.side_effect=click
            runner.scroll_menu=Mock(side_effect=lambda screen,amount:state.__setitem__(1,1))
            runner.select_zone(5)
            self.assertEqual(vision.map_zone(capture()),5)
            self.assertEqual(io.click.call_count,2)
            self.assertEqual(runner.budget.payload()['entries_reserved'],0)
            io.click.reset_mock();runner.select_zone(5);io.click.assert_not_called()
            for zone in (0,21,True,'5'):
                with self.assertRaises(ValueError):runner.select_zone(zone)
                io.click.assert_not_called()

    def test_changed_zone_name_and_failed_map_confirmation_block_further_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,vision=self.runner(Path(tmp));vision.screen.return_value='ZONES'
            vision.zone_choice.return_value=(930,830)
            runner.wait=Mock(return_value='frame');vision.zone_choice.return_value=None
            with self.assertRaises(SafetyStop):runner.click('ZONES',(930,830),expected_zone=5)
            io.click.assert_not_called()
            vision.zone_choice.return_value=(930,830);vision.screen.return_value='MAP_Z1';runner.scroll_menu=Mock()
            runner.click=Mock()
            def wait(screen,timeout=10):
                if screen=='MAP_Z5':raise SafetyStop('Mapa elegido no confirmado')
                if screen=='ZONES':vision.screen.return_value='ZONES'
                return 'frame'
            runner.wait=wait
            with self.assertRaisesRegex(SafetyStop,'Mapa elegido no confirmado'):runner.select_zone(5)
            self.assertEqual([call.args[0] for call in runner.click.call_args_list],['MAP_Z1','ZONES'])
            self.assertEqual(runner.budget.payload()['entries_reserved'],0)

    def test_zone_not_found_stops_after_bounded_scroll_without_selecting_another(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,vision=self.runner(Path(tmp));vision.screen.return_value='MAP_Z1'
            vision.zone_choice.return_value=None;runner.wait=Mock(return_value='frame')
            runner.click=Mock();runner.scroll_menu=Mock()
            with self.assertRaisesRegex(SafetyStop,'Zona no encontrada'):runner.select_zone(20)
            runner.click.assert_called_once_with('MAP_Z1',(440,153),'ZONES_BUTTON',(315,100,565,205))
            self.assertEqual(runner.scroll_menu.call_count,20)
            self.assertEqual(runner.budget.payload()['entries_reserved'],0)

    def test_settings_scroll_reads_everything_and_the_bot_unticks_spending_and_duplicates(self):
        for unsafe in (None,'gold','gems','duplicates','unknown','no_box'):
            with tempfile.TemporaryDirectory() as tmp:
                runner,io,vision=self.runner(Path(tmp));runner.plan['target']='Tealk'
                position=[0];ticked={unsafe};runner.close_menu=Mock()
                runner.click=Mock(side_effect=lambda screen,xy,*a,**k:ticked.discard(unsafe) if screen=='SETTINGS' else None)
                def scroll(screen,amount):
                    self.assertEqual(screen,'SETTINGS')
                    position[0]=0 if amount<0 else position[0]+amount
                runner.scroll_menu=Mock(side_effect=scroll)
                def setting(frame,name):
                    start={'gold':30,'gems':42,'duplicates':48}[name]
                    if unsafe=='unknown' or not start<=position[0]<start+12:return None
                    return name in ticked or (unsafe=='no_box' and name=='gold')
                vision.setting.side_effect=setting
                vision.setting_box.side_effect=lambda f,name:None if unsafe=='no_box' else (700,500)
                if unsafe in ('unknown','no_box'):
                    with self.assertRaises(SafetyStop):runner.verify_settings()
                    self.assertFalse(runner.safety_checked);runner.close_menu.assert_not_called()
                else:
                    runner.verify_settings()
                    self.assertTrue(runner.safety_checked)
                    self.assertLessEqual(runner.scroll_menu.call_count,10)  # Reset + como máximo 9 avances.
                    runner.close_menu.assert_called_once_with('SETTINGS')
                    self.assertEqual(runner.click.call_count,2 if unsafe else 1)  # SETTINGS + solo la casilla marcada
                io.click.assert_not_called()
                self.assertEqual(runner.budget.payload()['entries_reserved'],0)

    def test_familiar_offer_always_pauses_before_persuade_or_bribe(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,vision=self.runner(Path(tmp))
            runner.capture=Mock(return_value=np.zeros((1080,1920,3),np.uint8))
            vision.screen.return_value='FAMILIAR_OFFER'
            with self.assertRaisesRegex(SafetyStop,'Oferta de familiar'):
                runner.observe('test:1',1)
            io.click.assert_not_called()
            self.assertEqual(runner.budget.gold_reserved,0)

    def test_decline_only_a_stable_known_non_target_and_confirm_that_action(self):
        with np.load(Path(__file__).parent/'fixtures/dungeons.npz',allow_pickle=False) as data:offer=data['offer_brute']
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,vision=self.runner(Path(tmp));runner.plan=farm_plan('Z5D3','Heroic',1,30,'Tealk');runner.difficulty='Heroic'
            vision.familiar_name.return_value='Brute';runner.click=Mock();runner.wait=Mock(return_value=offer)
            self.assertTrue(runner.decline_other(offer,'test:1',1))
            self.assertEqual([call.args[0] for call in runner.click.call_args_list],['FAMILIAR_OFFER','DECLINE_CONFIRM'])
            self.assertEqual(runner.budget.gold_reserved,0)
            self.assertTrue((Path(tmp)/'decline-1.intent.json').exists())
            runner.click.reset_mock()
            for name in (None,'Tealk','tealk'):
                vision.familiar_name.return_value=name
                self.assertFalse(runner.decline_other(offer,'test:1',2))
                runner.click.assert_not_called()
            # Sin objetivo se rechaza cualquier oferta legible, conocida o no; nunca oro ni gemas.
            runner.plan['target']=''
            for offer_id,name in ((3,'Brute'),(4,None)):
                vision.familiar_name.return_value=name
                self.assertTrue(runner.decline_other(offer,'test:1',offer_id))
            self.assertEqual(runner.click.call_count,4);self.assertEqual(runner.budget.gold_reserved,0)
            self.assertFalse(runner.decline_other(np.zeros_like(offer),'test:1',5))

    def test_several_targets_pause_on_any_of_them_and_decline_the_rest(self):
        plan=validate_supported({'dungeon_id':'Z5D3','difficulty':'Heroic','runs':1,'energy_limit':30,'targets':['Mummih','Tealk']})
        self.assertEqual(plan['targets'],['Mummih','Tealk'])
        with self.assertRaises(ValueError):
            validate_supported({'dungeon_id':'Z5D3','difficulty':'Heroic','runs':1,'energy_limit':30,'targets':['Bob']})
        with np.load(Path(__file__).parent/'fixtures/dungeons.npz',allow_pickle=False) as data:offer=data['offer_brute']
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,vision=self.runner(Path(tmp));runner.plan=plan
            runner.click=Mock();runner.wait=Mock(return_value=offer)
            for name,declined in (('Mummih',False),('tealk',False),('Brute',True),('Sitra',True)):
                vision.familiar_name.return_value=name
                self.assertIs(runner.decline_other(offer,'test:1',name),declined,name)

    def test_changed_familiar_before_decline_and_wrong_confirm_never_send_yes(self):
        with np.load(Path(__file__).parent/'fixtures/dungeons.npz',allow_pickle=False) as data:offer=data['offer_brute']
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,vision=self.runner(Path(tmp));vision.screen.return_value='FAMILIAR_OFFER'
            vision.familiar_name.return_value='Tealk'
            with self.assertRaises(SafetyStop):
                runner.click('FAMILIAR_OFFER',(755,955),'DECLINE',(550,890,965,1015),expected_familiar='Brute')
            io.click.assert_not_called()
            runner.plan=farm_plan('Z5D3','Heroic',1,30,'Tealk');runner.difficulty='Heroic';vision.familiar_name.return_value='Brute'
            def wait(screen,timeout=10,expected=None):
                if screen=='DECLINE_CONFIRM':raise SafetyStop('Confirmación distinta')
                return offer
            runner.wait=wait
            with self.assertRaises(SafetyStop):runner.decline_other(offer,'test:1',1)
            io.click.assert_called_once_with((755,955))

    def test_decline_closes_on_any_legible_next_offer_even_the_same_familiar_but_not_unknown(self):
        # 'offer' es Melv'guin, legible en Z5D2 desde el lector por letras.
        from fishing_core.dungeon_vision import DungeonVision
        with np.load(Path(__file__).parent/'fixtures/dungeons.npz',allow_pickle=False) as data:
            frames={k:data[k] for k in ('offer_brute','offer_sitra','offer','decline_confirm')}
        for next_offer in ('offer_sitra','offer_brute','offer','decline_confirm'):
            with self.subTest(next_offer=next_offer),tempfile.TemporaryDirectory() as tmp:
                runner,io,_=self.runner(Path(tmp));runner.plan['target']='Tealk';runner.vision=vision=DungeonVision()
                state=['offer_brute'];runner.capture=lambda:frames[state[0]]
                def wait(predicate,timeout=10,expected=None):
                    for _ in range(2):
                        frame=runner.capture()
                        okay=predicate(frame) if callable(predicate) else vision.screen(frame)==predicate
                        if not okay:raise SafetyStop('Cierre no confirmado')
                    return frame
                runner.wait=wait
                def click(xy):
                    if xy==(755,955):
                        self.assertEqual(state[0],'offer_brute');state[0]='decline_confirm'
                    else:
                        self.assertEqual(xy,(818,752));self.assertEqual(state[0],'decline_confirm');state[0]=next_offer
                io.click.side_effect=click
                with patch('fishing_core.dungeon_runtime.time.sleep'):
                    if next_offer in ('offer_sitra','offer_brute','offer'):self.assertTrue(runner.decline_other(frames['offer_brute'],'test:1','1-1'))
                    else:
                        with self.assertRaises(SafetyStop):runner.decline_other(frames['offer_brute'],'test:1','1-1')
                    self.assertEqual(io.click.call_count,2)
                    intent=json.loads((Path(tmp)/'decline-1-1.intent.json').read_text())
                    self.assertIs(intent['effect_confirmed'],next_offer in ('offer_sitra','offer_brute','offer'))
                    state[0]='offer_brute'
                    with self.assertRaisesRegex(SafetyStop,'Rechazo ya registrado'):
                        runner.decline_other(frames['offer_brute'],'test:1','1-1')
                    self.assertEqual(io.click.call_count,2)
                self.assertEqual(runner.budget.payload()['entries_reserved'],0)
                self.assertEqual(runner.budget.gold_reserved,0)

    def test_without_target_any_legible_next_offer_or_battle_closes_but_not_the_confirm(self):
        from fishing_core.dungeon_vision import DungeonVision
        with np.load(Path(__file__).parent/'fixtures/dungeons.npz',allow_pickle=False) as data:
            frames={k:data[k] for k in ('offer_brute','offer','decline_confirm','battle')}
        for next_screen,closes in (('offer',True),('battle',True),('offer_brute',True),('decline_confirm',False)):
            with self.subTest(next_screen=next_screen),tempfile.TemporaryDirectory() as tmp:
                runner,io,_=self.runner(Path(tmp));runner.plan['target']='';runner.vision=vision=DungeonVision()
                state=['offer_brute'];runner.capture=lambda:frames[state[0]]
                def wait(predicate,timeout=10,expected=None):
                    frame=runner.capture()
                    if not (predicate(frame) if callable(predicate) else vision.screen(frame)==predicate):
                        raise SafetyStop('Cierre no confirmado')
                    return frame
                runner.wait=wait
                def click(xy):state[0]='decline_confirm' if xy==(755,955) else next_screen
                io.click.side_effect=click
                with patch('fishing_core.dungeon_runtime.time.sleep'):
                    if closes:self.assertTrue(runner.decline_other(frames['offer_brute'],'test:1','1-1'))
                    else:
                        with self.assertRaises(SafetyStop):runner.decline_other(frames['offer_brute'],'test:1','1-1')
                intent=json.loads((Path(tmp)/'decline-1-1.intent.json').read_text())
                self.assertIs(intent['effect_confirmed'],closes);self.assertEqual(runner.budget.gold_reserved,0)

    def test_with_target_an_animating_offer_waits_for_a_legible_name_before_deciding(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,vision=self.runner(Path(tmp));runner.plan['target']='Tealk'
            runner.capture=Mock(return_value=np.zeros((1080,1920,3),np.uint8))
            vision.screen.return_value='FAMILIAR_OFFER'
            names=iter([None,'Brute']);vision.familiar_name.side_effect=lambda *_:next(names,'Brute')
            seen=[]
            def decline(frame,attempt,offer):
                seen.append(vision.familiar_name(frame));raise SafetyStop('fin de prueba')
            runner.decline_other=decline
            with self.assertRaisesRegex(SafetyStop,'fin de prueba'):runner.observe('test:1',1)
            self.assertEqual(seen,['Brute']);io.click.assert_not_called()

    def test_battle_waiting_without_auto_is_switched_on_but_not_endlessly(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,vision=self.runner(Path(tmp))
            runner.capture=Mock(return_value=np.zeros((1080,1920,3),np.uint8))
            runner.wait=Mock(return_value=runner.capture.return_value)
            vision.screen.return_value='AUTO_OFF_BATTLE'
            with self.assertRaisesRegex(SafetyStop,'repetidamente'):runner.observe('test:1',1,auto_started=True)
            self.assertEqual(io.click.call_count,3)

    def test_map_auto_stably_off_is_reactivated_but_not_endlessly(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,vision=self.runner(Path(tmp));frame=np.zeros((1080,1920,3),np.uint8)
            runner.capture=Mock(return_value=frame);runner.wait=Mock(return_value=frame)
            runner.click=Mock();runner.go_home=Mock()
            runner.budget.reserve_entry('test:1',resource='ENERGY',balance=100,cost=10)
            vision.screen.side_effect=['AUTO_ON_BATTLE','AUTO_OFF','VICTORY']
            runner.observe('test:1',1)
            self.assertEqual(runner.click.call_args_list[0].args,('AUTO_OFF',(1880,530)))
            runner.click.reset_mock();vision.screen.side_effect=['AUTO_ON','AUTO_ON_BATTLE']+['AUTO_OFF']*10
            vision.screen.side_effect=['AUTO_ON','AUTO_ON_BATTLE']+['AUTO_OFF']*40
            with patch('fishing_core.dungeon_runtime.time.monotonic',side_effect=range(200)), \
                    patch('fishing_core.dungeon_runtime.time.sleep'):
                with self.assertRaisesRegex(SafetyStop,'repetidamente'):runner.observe('test:1',2)
            self.assertEqual(runner.click.call_count,4)

    def test_transient_map_auto_off_during_battle_transition_never_reactivates_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,vision=self.runner(Path(tmp));frame=np.zeros((1080,1920,3),np.uint8)
            runner.capture=Mock(return_value=frame);runner.wait=Mock(return_value=frame)
            runner.click=Mock();runner.go_home=Mock()
            runner.budget.reserve_entry('test:1',resource='ENERGY',balance=100,cost=10)
            vision.screen.side_effect=['AUTO_OFF','AUTO_ON_BATTLE','VICTORY']
            runner.observe('test:1',1,auto_started=True)
            self.assertEqual(runner.budget.payload()['completed_runs'],1)
            self.assertEqual([c.args[0] for c in runner.click.call_args_list],['VICTORY'])

    def test_supervised_continuation_keeps_decline_ids_and_blocks_uncertain_intents(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,vision=self.runner(Path(tmp));runner.capture=Mock(return_value=np.zeros((1080,1920,3),np.uint8))
            path=Path(tmp)/'decline-1-1.intent.json';path.write_text('{"effect_confirmed":false}')
            with self.assertRaisesRegex(SafetyStop,'Rechazo previo sin confirmar'):runner.observe('test:1',1)
            io.click.assert_not_called()
            path.write_text('{"effect_confirmed":true}');vision.screen.side_effect=['FAMILIAR_OFFER','FAMILIAR_OFFER']
            runner.decline_other=Mock(side_effect=[True,False])
            with self.assertRaises(SafetyStop):runner.observe('test:1',1)
            self.assertEqual(runner.decline_other.call_args_list[0].args[-1],'1-2')

    def test_victory_is_counted_only_after_town_and_map_are_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,vision=self.runner(Path(tmp))
            runner.capture=Mock(return_value=np.zeros((1080,1920,3),np.uint8))
            runner.wait=Mock(return_value=runner.capture.return_value)
            vision.screen.return_value='VICTORY'
            runner.budget.reserve_entry('test:1',resource='ENERGY',balance=100,cost=10)
            def close():
                self.assertEqual(runner.budget.payload()['completed_runs'],0)
            runner.go_home=close
            runner.observe('test:1',1)
            self.assertEqual(runner.budget.payload()['completed_runs'],1)
            io.click.assert_called_once_with((1150,1000))

    def energy_clock(self,path,readings):
        runner,io,vision=self.runner(path);runner.wait=DungeonRunner.wait.__get__(runner)
        runner.capture=Mock(return_value=np.zeros((1080,1920,3),np.uint8))
        values=iter(readings);vision.energy=Mock(side_effect=lambda _:next(values,readings[-1]))
        clock=[0.0]
        def sleep(seconds):clock[0]+=seconds
        fake=SimpleNamespace(monotonic=lambda:clock[0],sleep=sleep,perf_counter_ns=time.perf_counter_ns)
        return runner,io,fake

    def test_energy_waits_out_the_recharge_clock_and_reserves_before_one_accept(self):
        with tempfile.TemporaryDirectory() as tmp:
            # ~15 s de reloj (None) y despues saldo estable: 10 s no bastaban.
            runner,io,fake=self.energy_clock(Path(tmp),[None]*125+[(100,368)])
            with patch('fishing_core.dungeon_runtime.time',fake):runner.enter(1)
            io.click.assert_called_once()
            self.assertEqual(runner.budget.energy_reserved,10)

    def test_only_the_clock_means_no_energy_and_ends_without_entering(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,fake=self.energy_clock(Path(tmp),[None])
            runner.vision.energy_clock=Mock(return_value=True);runner.close_menu=Mock()
            with patch('fishing_core.dungeon_runtime.time',fake):self.assertIsNone(runner.enter(1))
            runner.close_menu.assert_called_once_with('TEAM');io.click.assert_not_called()
            self.assertEqual(runner.budget.energy_reserved,0)

    def test_permanent_recharge_clock_stops_without_reserving_or_accept(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,fake=self.energy_clock(Path(tmp),[None]);runner.vision.energy_clock=Mock(return_value=False)
            with patch('fishing_core.dungeon_runtime.time',fake):
                with self.assertRaisesRegex(SafetyStop,'saldo de energía en TEAM'):runner.enter(1)
            io.click.assert_not_called()
            self.assertEqual(runner.budget.energy_reserved,0)

    def test_settings_are_checked_once_and_reruns_skip_navigation(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,_=self.runner(Path(tmp));runner.plan=farm_plan('Z5D2','Normal',3,30)
            runner.go_home=Mock();runner.verify_settings=Mock();runner.select_route=Mock()
            def enter(cycle):
                runner.budget.energy_reserved+=10;runner.balance=50;return f'test:{cycle}'
            runner.enter=Mock(side_effect=enter)
            runner.observe=Mock(side_effect=lambda attempt,cycle,rerun:f'test:{cycle+1}' if rerun else None)
            runner.run()
            runner.verify_settings.assert_called_once();runner.select_route.assert_called_once()
            self.assertEqual([c.kwargs['rerun'] for c in runner.observe.call_args_list],[True,True,False])

    def test_low_energy_lowers_difficulty_in_team_and_stops_below_the_cheapest(self):
        for energy,expected in ((25,'Hard'),(12,'Normal'),(5,None)):
            with self.subTest(energy=energy),tempfile.TemporaryDirectory() as tmp:
                runner,io,vision=self.runner(Path(tmp))
                runner.plan=farm_plan('Z5D3','Heroic',1,30,'Tealk');runner.difficulty='Heroic';runner.cost=30
                vision.energy.return_value=(energy,369)
                vision.cost.side_effect=lambda frame,level:{'Normal':10,'Hard':20,'Heroic':30}[level]
                runner.close_menu=Mock();clicked=[]
                runner.click=Mock(side_effect=lambda screen,xy,key=None,*a,**k:clicked.append(key))
                attempt=runner.enter(1)
                self.assertEqual(runner.difficulty if attempt else None,expected)
                if expected:
                    self.assertEqual(clicked,[expected.upper(),'ACCEPT'])
                    self.assertEqual(runner.budget.energy_reserved,{'Hard':20,'Normal':10}[expected])
                else:
                    self.assertNotIn('ACCEPT',clicked);self.assertEqual(runner.budget.energy_reserved,0)

    def test_victory_reruns_only_when_the_estimated_balance_pays_another_run(self):
        for balance,rerun,expected in ((40,True,(834,996)),(5,True,(1150,1000)),(40,False,(1150,1000))):
            with self.subTest(balance=balance,rerun=rerun),tempfile.TemporaryDirectory() as tmp:
                runner,io,vision=self.runner(Path(tmp))
                runner.capture=Mock(return_value=np.zeros((1080,1920,3),np.uint8))
                runner.wait=Mock(return_value=runner.capture.return_value);runner.go_home=Mock()
                vision.screen.return_value='VICTORY';runner.balance=balance
                runner.budget=FarmBudget(max_runs=3,max_energy=30,max_seconds=60)
                runner.budget.reserve_entry('test:1',resource='ENERGY',balance=100,cost=10)
                rerun_used=expected==(834,996)
                # RERUN entra directamente: la siguiente run queda reservada antes del clic.
                self.assertEqual(runner.observe('test:1',1,rerun=rerun),'test:2' if rerun_used else None)
                io.click.assert_called_once_with(expected)
                self.assertEqual(runner.budget.payload()['completed_runs'],1)
                self.assertEqual(runner.budget.payload()['entries_reserved'],2 if rerun_used else 1)

    def test_open_mode_windows_are_closed_with_their_verified_x_before_starting(self):
        from fishing_core.dungeon_vision import DungeonVision
        with np.load(Path(__file__).parent/'fixtures/dungeons.npz',allow_pickle=False) as data:
            frames={k:data[k] for k in ('trials_window','pvp_window','trials_home')}
        moves={('trials_window',(1490,236)):'pvp_window',('pvp_window',(1494,226)):'trials_home'}
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,_=self.runner(Path(tmp));runner.vision=DungeonVision();state=['trials_window']
            runner.capture=lambda:frames[state[0]];runner.wait=DungeonRunner.wait.__get__(runner)
            io.click.side_effect=lambda xy:state.__setitem__(0,moves[(state[0],tuple(xy))])
            with patch('fishing_core.dungeon_runtime.time.sleep'):
                self.assertEqual(runner.ensure_home(),'HOME')
                state[0]='pvp_window';self.assertEqual(runner.ensure_home(keep=('PVP',)),'PVP')
            self.assertEqual(io.click.call_count,2)

    def test_a_result_screen_left_open_is_closed_with_its_town_button(self):
        from fishing_core.dungeon_vision import DungeonVision
        with np.load(Path(__file__).parent/'fixtures/dungeons.npz',allow_pickle=False) as data:
            frames={k:data[k] for k in ('result','boss_defeat','trials_home')}
        vision=DungeonVision()
        def center(frame,key,roi):
            x,y=vision.locate(frame,key,roi);h,w=vision.templates[key].shape[:2];return (x+w//2,y+h//2)
        for start,key,roi in (('result','TOWN',(700,900,1500,1080)),('boss_defeat','RESULT_TOWN',(700,915,1500,1080))):
            with self.subTest(start=start),tempfile.TemporaryDirectory() as tmp:
                runner,io,_=self.runner(Path(tmp));runner.vision=vision;state=[start]
                runner.capture=lambda:frames[state[0]];runner.wait=DungeonRunner.wait.__get__(runner)
                target=center(frames[start],key,roi)
                io.click.side_effect=lambda xy:state.__setitem__(0,'trials_home' if tuple(xy)==target else 'x')
                with patch('fishing_core.dungeon_runtime.time.sleep'):self.assertEqual(runner.ensure_home(),'HOME')

    def test_disconnection_is_recovered_through_reconnect_daily_reward_and_items(self):
        from fishing_core.dungeon_vision import DungeonVision
        with np.load(Path(__file__).parent/'fixtures/dungeons.npz',allow_pickle=False) as data:
            frames={k:data[k] for k in ('disconnected','season_rewards','items_window','news','trials_home')}
        vision=DungeonVision();x,y=vision.locate(frames['items_window'],'ITEMS_CLOSE',(1200,150,1500,450))
        h,w=vision.templates['ITEMS_CLOSE'].shape[:2]
        moves={('disconnected',(960,742)):'season_rewards',('season_rewards',(960,962)):'items_window',
               ('items_window',(x+w//2,y+h//2)):'news',('news',(1118,964)):'trials_home'}
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,_=self.runner(Path(tmp));runner.vision=vision;state=['disconnected']
            runner.capture=lambda:frames[state[0]];runner.wait=DungeonRunner.wait.__get__(runner)
            io.click.side_effect=lambda xy:state.__setitem__(0,moves[(state[0],tuple(xy))])
            with patch('fishing_core.dungeon_runtime.time.sleep'):self.assertEqual(runner.ensure_home(),'HOME')
            self.assertEqual(io.click.call_count,4)

    def test_run_stops_before_navigating_when_the_next_entry_exceeds_the_energy_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,_=self.runner(Path(tmp));runner.plan=farm_plan('Z5D2','Normal',3,15)
            runner.go_home=Mock();runner.verify_settings=Mock();runner.select_route=Mock();runner.observe=Mock(return_value=None)
            def enter(cycle):
                runner.budget.energy_reserved+=10
                return f'test:{cycle}'
            runner.enter=Mock(side_effect=enter)
            runner.run()
            runner.enter.assert_called_once_with(1)
            runner.verify_settings.assert_called_once();runner.select_route.assert_called_once()
            self.assertEqual(runner.log.emit.call_args.kwargs['message'],'Límite de energía alcanzado')

    def test_wait_requires_two_consecutive_matching_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,_=self.runner(Path(tmp))
            runner.capture=Mock(return_value=np.zeros((1080,1920,3),np.uint8))
            reads=iter([True,False,False])
            with patch('fishing_core.dungeon_runtime.time.monotonic',side_effect=[0,.5,1,1.5,3]), \
                    patch('fishing_core.dungeon_runtime.time.sleep'):
                with self.assertRaises(SafetyStop):DungeonRunner.wait(runner,lambda _:next(reads),timeout=2)
            io.click.assert_not_called()

    def test_check_stops_when_the_supervising_panel_is_gone(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,_=self.runner(Path(tmp))
            with patch.dict('os.environ',{'FARM_LAUNCHER_PID':str(os.getppid())}):runner.check()
            with patch.dict('os.environ',{'FARM_LAUNCHER_PID':str(os.getppid()+1)}):
                with self.assertRaisesRegex(SafetyStop,'panel'):runner.check()

    def test_check_stops_after_the_session_time_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,_=self.runner(Path(tmp));runner.deadline=time.monotonic()-1
            with self.assertRaisesRegex(SafetyStop,'60 minutos'):runner.check()


    def test_restart_mid_run_declines_the_leftover_offer_and_reaches_home_without_spending(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,vision=self.runner(Path(tmp))
            states=['FAMILIAR_OFFER','DECLINE_CONFIRM','AUTO_ON','HOME'];clicks=[]
            vision.screen.side_effect=lambda f:states[0]
            def click(screen,xy,*a,**k):clicks.append((screen,xy));states.pop(0)
            runner.click=Mock(side_effect=click)
            def wait(predicate,timeout=10,expected=None):
                frame='frame';assert predicate(frame);return frame
            runner.wait=wait
            with patch('fishing_core.dungeon_runtime.time.sleep',side_effect=lambda s:states.pop(0) if states[0]=='AUTO_ON' else None):
                self.assertEqual(runner.ensure_home(),'HOME')
            self.assertEqual(clicks,[('FAMILIAR_OFFER',(755,955)),('DECLINE_CONFIRM',(818,752))])  # nunca PERSUADE ni BRIBE
            self.assertEqual(runner.budget.gold_reserved,0)


    def test_an_offer_that_changes_while_deciding_is_re_read_without_clicking(self):
        from fishing_core.dungeon_runtime import OfferChanged
        from fishing_core.dungeon_vision import DungeonVision
        with np.load(Path(__file__).parent/'fixtures/dungeons.npz',allow_pickle=False) as data:
            brute,sitra=data['offer_brute'],data['offer_sitra']
        with tempfile.TemporaryDirectory() as tmp:
            runner,io,_=self.runner(Path(tmp));runner.plan['target']='Tealk';runner.vision=DungeonVision()
            runner.capture=lambda:sitra  # al confirmar ya está la siguiente oferta
            runner.wait=lambda predicate,timeout=10,expected=None:sitra
            with self.assertRaises(OfferChanged):runner.decline_other(brute,'test:1','1-1')
            io.click.assert_not_called();self.assertFalse((Path(tmp)/'decline-1-1.intent.json').exists())


if __name__=='__main__':unittest.main()
