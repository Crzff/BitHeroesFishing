"""App del Farm Bot sin pantalla: catálogo, configuración y pasos que lanzará START."""

import sys
import tempfile
import unittest
from pathlib import Path

from fishing_core import farm_all, farm_config, pixel_ui
from fishing_core.farm_app import CALIBRATED, familiars_of


def setUpModule():
    from unittest.mock import patch
    from fishing_core import accounts
    temporary=tempfile.TemporaryDirectory()
    unittest.addModuleCleanup(temporary.cleanup)
    patcher=patch.object(accounts,'ROOT',Path(temporary.name))
    patcher.start();unittest.addModuleCleanup(patcher.stop)


class FarmAppTests(unittest.TestCase):
    def test_new_accounts_have_no_targets_and_old_gold_limits_are_ignored(self):
        from unittest.mock import patch
        from fishing_core.farm_budget import UNLIMITED_GOLD
        for account in (None,'personal','perfil1','steam'):
            with tempfile.TemporaryDirectory() as tmp,patch.dict('os.environ',{} if account is None else {'FARM_ACCOUNT':account},clear=True):
                path=Path(tmp)/'cfg.json';config=farm_config.load(path)
                self.assertEqual(config['quest']['targets'],[])
                self.assertEqual(farm_all.quest_plan(config)['max_gold'],0)
                config['quest'].update(targets=['Tealk'],max_gold='antiguo')
                config['raid']['max_gold']={'ignorado':True}
                farm_config.save(config,path);loaded=farm_config.load(path)
                self.assertNotIn('max_gold',loaded['quest']);self.assertNotIn('max_gold',loaded['raid'])
                self.assertEqual(farm_all.quest_plan(loaded)['max_gold'],UNLIMITED_GOLD)
                self.assertEqual(farm_all.quest_plan(loaded,single=True)['max_gold'],0)

    def test_tealks_palace_lists_its_four_familiars_and_only_calibrated_routes_are_selectable(self):
        self.assertEqual(set(familiars_of('Z5D3')),{'Mummih','Brute','Sitra','Tealk'})
        self.assertEqual(len(CALIBRATED),31);self.assertLessEqual({'Z1D1','Z1D4','Z5D2','Z5D3','Z9D1'},CALIBRATED)
        self.assertNotIn('Z10D1',CALIBRATED)

    def test_config_round_trip_drives_the_steps_in_crzf_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'cfg.json';config=farm_config.load(path)
            config['quest']['targets']=['Mummih','Tealk'];config['modes']['raid']=False;config['runes']=False
            farm_config.save(config,path);loaded=farm_config.load(path)
        self.assertEqual(loaded['quest']['targets'],['Mummih','Tealk'])
        self.assertEqual([name for name,_ in farm_all.steps(loaded)],['Boosts','Quest','PvP','World Boss','GvG','Trials'])
        loaded['runes']=True
        self.assertEqual([name for name,_ in farm_all.steps(loaded)][:4],['Boosts','Runas captura','Quest','Runas Item Find'])

    def test_broken_config_falls_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'cfg.json';path.write_text('{roto')
            self.assertEqual(farm_config.load(path),farm_config.DEFAULT)

    def test_pixel_widgets_render(self):
        for img in (pixel_ui.frame(800,600,'WORLD BOSS'),pixel_ui.frame(800,600,'RAID','raid'),pixel_ui.panel(300,200),pixel_ui.loot_button(),pixel_ui.checkbox(True),pixel_ui.auto_button(True),
                    pixel_ui.button('HEROIC',200),pixel_ui.icon('quest')):
            self.assertGreater(img.width*img.height,0)

    def test_ui_art_is_not_clipped_or_carrying_the_original_screen_background(self):
        import json
        from PIL import Image
        for name in (*farm_config.MODES,'res/chest'):
            with self.subTest(icon=name),Image.open(pixel_ui.ICONS/f'{name}.png') as img:
                x0,y0,x1,y1=img.getchannel('A').getbbox()
                self.assertTrue(0<x0<x1<img.width and 0<y0<y1<img.height,'falta margen transparente')
        meta=json.loads((pixel_ui.ICONS/'frame/frames.json').read_text())
        for style in ('settings','raid'):
            with self.subTest(frame=style),Image.open(pixel_ui.ICONS/f'frame/{style}_plaque.png') as img:
                alpha=img.getchannel('A')
                x0,y0,x1,y1=alpha.getbbox()
                self.assertTrue(0<x0<x1<img.width and 0<y0<y1<img.height,'la placa incluye bordes del cuerpo')
                for point in ((0,0),(img.width-1,0),(0,img.height-1),(img.width-1,img.height-1)):
                    self.assertEqual(alpha.getpixel(point),0,'la placa incluye fondo o cuerpo del marco')
                w,h=meta[style]['size'];x0,y0,x1,y1=meta[style]['close']
                self.assertTrue(0<=x0<x1<=w and 0<=y0<y1<=h,'la X queda fuera del recorte')

    def test_frame_builder_keeps_only_the_plaque_not_the_body_under_it(self):
        import numpy as np
        from scripts.build_ui_frames import SPECS,build
        spec=SPECS['settings'];frame=np.full((1080,1920,3),100,np.uint8)
        _,plaque=build(frame,spec)
        self.assertEqual(int(plaque[105,0,3]),0)



class FarmAppStopTests(unittest.TestCase):
    """STOP sin pantalla ni juego; señales reales solo a procesos de prueba propios."""
    @unittest.skipUnless(sys.platform=='linux','Parada conjunta Linux')
    def test_stop_signals_three_account_probes_and_leaves_other_python_alive(self):
        import os
        import subprocess
        from types import SimpleNamespace
        from unittest.mock import patch
        from fishing_core import global_stop
        from fishing_core.farm_app import FarmApp
        processes=[]
        try:
            for account in ('personal','perfil-1','steam'):
                p=subprocess.Popen([sys.executable,'-B','-m','fishing_core.global_stop','--probe'],
                                   cwd=global_stop.ROOT,env={**os.environ,'FARM_ACCOUNT':account},
                                   stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                processes.append(p);self.assertEqual(p.stdout.readline().strip(),'PROBE_READY')
            other=subprocess.Popen([sys.executable,'-B','-c','import signal;print("OTHER_READY",flush=True);signal.pause()'],
                                   cwd=global_stop.ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            processes.append(other);self.assertEqual(other.stdout.readline().strip(),'OTHER_READY')
            app=SimpleNamespace(process=processes[0],status='EN MARCHA')
            real_stop=global_stop.stop_workers
            with tempfile.TemporaryDirectory() as tmp:
                for p in processes:(Path(tmp)/str(p.pid)).symlink_to(Path('/proc')/str(p.pid))
                with patch.object(global_stop,'stop_workers',side_effect=lambda:real_stop(Path(tmp))) as stop:
                    FarmApp.toggle_run(app)
                    stop.assert_called_once_with()
            self.assertEqual(app.status,'DETENIENDO...')
            for p in processes[:3]:
                out,err=p.communicate(timeout=5)
                self.assertEqual(p.returncode,0,err);self.assertIn('PROBE_STOPPED',out)
            self.assertIsNone(other.poll(),'STOP alcanzó un proceso ajeno')
        finally:
            for p in processes:
                if p.poll() is None:p.terminate()
                p.communicate(timeout=5)

    def test_closing_the_running_panel_uses_the_same_stop_action(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        from fishing_core.farm_app import FarmApp
        actions=[]
        app=SimpleNamespace(process=Mock(),toggle_run=lambda:actions.append('stop'),
                            destroy=lambda:actions.append('destroy'))
        FarmApp.quit_app(app)
        self.assertEqual(actions,['stop','destroy'])

    def test_non_linux_stop_keeps_the_existing_process_signal(self):
        import signal
        from types import SimpleNamespace
        from unittest.mock import Mock,patch
        from fishing_core.farm_app import FarmApp
        app=SimpleNamespace(process=Mock(),status='EN MARCHA')
        with patch('fishing_core.farm_app.sys.platform','win32'):
            FarmApp.toggle_run(app)
        app.process.send_signal.assert_called_once_with(signal.SIGINT)
        self.assertEqual(app.status,'DETENIENDO...')


class FarmAppTrialTests(unittest.TestCase):
    def test_observation_panel_without_sessions_is_refused_before_creating_a_window(self):
        from unittest.mock import patch
        from fishing_core import farm_app
        with patch.object(farm_app.tk.Tk,'__init__',side_effect=AssertionError('No crear ventana sin cuentas')) as window:
            with self.assertRaisesRegex(ValueError,'cuentas'):farm_app.FarmApp(read_only=True)
            window.assert_not_called()

    def test_stop_check_panel_starts_only_input_disabled_supervisor(self):
        from types import SimpleNamespace
        from unittest.mock import Mock,patch
        from fishing_core import farm_app,farm_multi
        app=SimpleNamespace(process=None,sessions={},read_only=True,status='LISTO',save=Mock(),follow=Mock())
        with patch.object(farm_multi,'start_trial') as start,patch.object(farm_app.threading,'Thread'):
            farm_app.FarmApp.toggle_run(app)
            start.assert_called_once_with({},read_only=True);app.save.assert_not_called()

    def test_trial_screen_draws_offline_with_only_stop_start_and_close_actions(self):
        from types import MethodType,SimpleNamespace
        from unittest.mock import Mock
        from PIL import Image
        from fishing_core import farm_app
        for running,read_only in ((False,False),(True,False),(False,True),(True,True)):
            app=SimpleNamespace(img=Image.new('RGBA',(farm_app.W,farm_app.H)),zones=[],process=Mock() if running else None,
                                read_only=read_only,status='PRUEBA BLOQUEADA',toggle_run=Mock(),quit_app=Mock(),render=Mock())
            for name in ('put','label','window'):setattr(app,name,MethodType(getattr(farm_app.FarmApp,name),app))
            farm_app.FarmApp.draw_trial(app)
            self.assertEqual(len(app.zones),2)
            for x,y,x1,y1,action in app.zones:
                self.assertTrue(0<=x<x1<=farm_app.W and 0<=y<y1<=farm_app.H)
            x,y,x1,y1,_=app.zones[-1]
            app.pending_clicks=[];app.pressed_zones=set();app.click_job=None;app.present=Mock();app.after=Mock()
            app.flush_clicks=MethodType(farm_app.FarmApp.flush_clicks,app)
            farm_app.FarmApp.on_click(app,SimpleNamespace(x=(x+x1)//2,y=(y+y1)//2))
            farm_app.FarmApp.flush_clicks(app)
            app.toggle_run.assert_called_once_with();app.quit_app.assert_not_called()

    def test_trial_start_uses_supervisor_without_saving_or_launching_legacy_modes(self):
        from types import SimpleNamespace
        from unittest.mock import Mock,patch
        from fishing_core import farm_app,farm_multi
        data={'test':'only endpoints are passed'};process=Mock()
        app=SimpleNamespace(process=None,sessions=data,status='LISTO',save=Mock(),follow=Mock())
        with patch.object(farm_multi,'start_trial',return_value=process) as start, \
                patch.object(farm_app.subprocess,'Popen') as legacy,patch.object(farm_app.threading,'Thread') as thread:
            farm_app.FarmApp.toggle_run(app)
            start.assert_called_once_with(data);legacy.assert_not_called();app.save.assert_not_called()
            self.assertIs(app.process,process);thread.return_value.start.assert_called_once()

    def test_blocked_trial_start_does_not_save_or_touch_any_client(self):
        from types import SimpleNamespace
        from unittest.mock import Mock,patch
        from fishing_core import farm_app,farm_multi
        app=SimpleNamespace(process=None,sessions={},status='LISTO',save=Mock())
        with patch.object(farm_multi,'start_trial',side_effect=ValueError('PRIVATE_TEST_MARKER')), \
                patch.object(farm_app.subprocess,'Popen') as spawn,patch.object(farm_app.threading,'Thread') as thread:
            farm_app.FarmApp.toggle_run(app)
            spawn.assert_not_called();thread.assert_not_called();app.save.assert_not_called()
            self.assertIsNone(app.process);self.assertIn('BLOQUEADA',app.status);self.assertNotIn('PRIVATE_TEST_MARKER',app.status)

    def test_trial_follow_and_failed_worker_exit_never_claim_all_resources_spent(self):
        from types import SimpleNamespace
        from unittest.mock import Mock,patch
        from fishing_core import farm_app
        for trial,code,lines in (({},0,['Personal: OK (prueba limitada)\n']),({},1,[]),(None,1,[])):
            with self.subTest(trial=trial,code=code),tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
                process=Mock(pid=123,stdout=lines);process.wait.return_value=code
                app=SimpleNamespace(sessions=trial,after=Mock(),finish=Mock(),set_status=Mock())
                with patch.object(farm_app,'runs_root',return_value=Path(tmp)):farm_app.FarmApp.follow(app,process)
                status=app.after.call_args.args[-1]
                self.assertNotIn('TODO GASTADO',status)
                self.assertIn('PRUEBA COMPLETADA' if code==0 else 'PARADO',status)

    def test_trial_main_requires_explicit_flag_and_endpoint_payload(self):
        from unittest.mock import patch
        from fishing_core import farm_app,farm_multi
        with patch.object(farm_multi,'read_sessions',return_value={'endpoints':'offline fixture'}) as read, \
                patch.object(farm_multi,'trial_environments') as validate, \
                patch.object(farm_app,'FarmApp') as app:
            farm_app.main(['--trial']);read.assert_called_once_with()
            validate.assert_called_once_with({'endpoints':'offline fixture'})
            app.assert_called_once_with(sessions={'endpoints':'offline fixture'});app.return_value.mainloop.assert_called_once()

    def test_stop_check_main_keeps_the_read_only_flag_with_the_endpoint_payload(self):
        from unittest.mock import patch
        from fishing_core import farm_app,farm_multi
        with patch.object(farm_multi,'read_sessions',return_value={'endpoints':'offline fixture'}), \
                patch.object(farm_multi,'trial_environments'),patch.object(farm_app,'FarmApp') as app:
            farm_app.main(['--stop-check'])
            app.assert_called_once_with(sessions={'endpoints':'offline fixture'},read_only=True)
            app.return_value.mainloop.assert_called_once_with()


class FarmAppMultiTests(unittest.TestCase):
    """Panel multicuenta con Tk simulado y estado exclusivamente temporal."""
    def setUp(self):
        import json
        from unittest.mock import Mock,patch
        from fishing_core import farm_app,accounts
        from tests.test_farm_multi import sessions
        self.farm_app=farm_app;self.data=sessions()
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        patcher=patch.object(accounts,'ROOT',self.root);patcher.start();self.addCleanup(patcher.stop)
        path=self.root/'sessions.json';path.write_text(json.dumps(self.data))
        def account_root(root,env=None):return self.root/(env or {}).get('FARM_ACCOUNT','default')
        for target,name,value in ((farm_app,'MULTI_SESSIONS',path),(farm_app,'state_root',account_root),
                                  (farm_app,'MULTI_STATUS',self.root/'multi_status.json'),
                                  (farm_app,'ENABLED_ACCOUNTS',self.root/'enabled.json'),
                                  (farm_app,'runs_root',account_root),(farm_config,'PATH',self.root/'default.json')):
            patcher=patch.object(target,name,value);patcher.start();self.addCleanup(patcher.stop)
        for account in self.data:
            config=farm_config.load(self.root/'missing.json');config['quest']['max_gold']=list(self.data).index(account)*1000
            farm_config.save(config,self.root/account/'farm_config.json')
        # __init__ real, sin intérprete Tk, ventanas ni renderizado gráfico.
        for target,name,value in ((farm_app.tk.Tk,'__init__',Mock(return_value=None)),
                                  (farm_app.tk,'Canvas',Mock()),(farm_app.FarmApp,'title',Mock()),
                                  (farm_app.FarmApp,'resizable',Mock()),(farm_app.FarmApp,'configure',Mock()),
                                  (farm_app.FarmApp,'protocol',Mock()),(farm_app.FarmApp,'render',Mock())):
            patcher=patch.object(target,name,value);patcher.start();self.addCleanup(patcher.stop)
        patcher=patch.object(farm_app.FarmApp,'after',Mock());patcher.start();self.addCleanup(patcher.stop)
        self.app=farm_app.FarmApp()
        self.assertEqual(self.app.multi,self.data);self.assertEqual(self.app.account,'steam')

    def test_live_supervisor_stop_and_three_account_lines(self):
        import json
        from unittest.mock import Mock,patch
        rows={a:{'step':'Raid','state':'EN MARCHA','detail':''} for a in self.data}
        rows['perfil-1'].update(step='Quest',state='PARADO',detail='x'*80)
        self.farm_app.MULTI_STATUS.write_text(json.dumps({'supervisor_pid':123,'accounts':rows}))
        with patch.object(self.farm_app.os,'kill') as kill,patch.object(Path,'read_bytes',return_value=b'python\0-m\0fishing_core.farm_multi\0--farm\0'), \
                patch.object(self.app,'label') as label,patch.object(self.farm_app.ui,'auto_button',return_value=Mock()) as button, \
                patch.object(self.app,'put'),patch.object(self.app,'window',return_value=(0,0,1100,850)):
            self.app.refresh_multi_status();self.assertTrue(self.app.running())
            self.app.draw_main();self.assertTrue(button.call_args.args[0])
            texts=[c.args[0] for c in label.call_args_list]
            for text in ('Steam · RAID · EN MARCHA','FMANI · RAID · EN MARCHA','KORTZZ · QUEST · PARADO: '+'x'*60):self.assertIn(text,texts)
            self.app.toggle_run();kill.assert_called_with(123,self.farm_app.signal.SIGINT)
        self.app.after.assert_called_with(2000,self.app.refresh_multi_status)

    def test_dead_or_wrong_supervisor_and_corrupt_status_allow_start(self):
        import json
        from unittest.mock import patch
        self.farm_app.MULTI_STATUS.write_text(json.dumps({'supervisor_pid':123,'accounts':{}}))
        with patch.object(self.farm_app.os,'kill',side_effect=ProcessLookupError):
            self.app.refresh_multi_status();self.assertFalse(self.app.running())
        with patch.object(self.farm_app.os,'kill'),patch.object(Path,'read_bytes',return_value=b'other\0--farm\0'):
            self.app.refresh_multi_status();self.assertFalse(self.app.running())
        for text in ('{roto','[]','{"supervisor_pid":123,"accounts":{"steam":null}}'):
            self.farm_app.MULTI_STATUS.write_text(text);self.app.refresh_multi_status();self.assertFalse(self.app.running())

    def test_choose_account_loads_its_config_and_isolates_save(self):
        paths={account:self.root/account/'farm_config.json' for account in self.data}
        for account in self.data:
            before={a:path.read_bytes() for a,path in paths.items()}
            self.app.choose_account(account)
            self.assertEqual(self.app.config_data,farm_config.load(paths[account]))
            self.assertEqual(self.app.config_path(),paths[account])
            self.assertEqual(self.app.loot_root(),self.root/account)
            self.app.config_data['runes']=not self.app.config_data['runes'];self.app.save()
            self.assertEqual(farm_config.load(paths[account]),self.app.config_data)
            self.assertNotEqual(paths[account].read_bytes(),before[account])
            for other in self.data:
                if other!=account:self.assertEqual(paths[other].read_bytes(),before[other])
        self.assertFalse((self.root/'default.json').exists())

    def test_enabled_accounts_persist_and_start_only_selected(self):
        import json
        from unittest.mock import Mock,patch
        from fishing_core import farm_multi
        self.app.toggle_account('perfil-1')
        self.assertEqual(json.loads(self.farm_app.ENABLED_ACCOUNTS.read_text()),self.app.enabled_accounts)
        self.assertEqual(self.farm_app.FarmApp().enabled_accounts,self.app.enabled_accounts)
        with patch.object(farm_multi,'start_farm',return_value=Mock()) as start,patch.object(self.farm_app.threading,'Thread'):
            self.app.toggle_run()
            start.assert_called_once_with({a:r for a,r in self.data.items() if a!='perfil-1'})
        before=self.farm_app.ENABLED_ACCOUNTS.read_bytes();boosts=self.app.config_data['boosts']
        boosts_buy=self.app.config_data['boosts_buy']
        self.app.toggle_account('steam');self.app.toggle_boosts();self.app.toggle_boosts_buy()
        self.assertEqual(self.farm_app.ENABLED_ACCOUNTS.read_bytes(),before)
        self.assertEqual(self.app.config_data['boosts'],boosts)
        self.assertEqual(self.app.config_data['boosts_buy'],boosts_buy)

    def test_no_enabled_account_does_not_start(self):
        from unittest.mock import patch
        from fishing_core import farm_multi
        self.app.enabled_accounts=dict.fromkeys(self.data,False)
        with patch.object(farm_multi,'start_farm') as start:
            self.app.toggle_run();start.assert_not_called()
        self.assertEqual(self.app.status,'ACTIVA AL MENOS UNA CUENTA')

    def test_boosts_saved_per_account(self):
        for account in self.data:
            self.app.choose_account(account)
            before=self.app.config_data['boosts'];self.app.toggle_boosts()
            self.assertEqual(farm_config.load(self.app.config_path())['boosts'],not before)
            before=self.app.config_data['boosts_buy'];self.app.toggle_boosts_buy()
            self.assertEqual(farm_config.load(self.app.config_path())['boosts_buy'],not before)

    def test_new_checkboxes_are_drawn_and_blocked_while_running(self):
        from unittest.mock import patch
        for running in (False,True):
            self.app.img=self.farm_app.Image.new('RGBA',(self.farm_app.W,self.farm_app.H))
            self.app.zones=[]
            with patch.object(self.app,'running',return_value=running),patch.object(self.app,'label') as label:
                self.app.draw_main()
            actions=[action for *box,action in self.app.zones]
            self.assertEqual(sum(getattr(a,'__name__','')=='toggle_boosts' for a in actions),int(not running))
            self.assertEqual(sum('toggle_account' in getattr(getattr(a,'__code__',None),'co_names',()) for a in actions),3*int(not running))
            texts=[c.args[0] for c in label.call_args_list]
            self.assertEqual(texts.count('FARMEAR'),3)
            self.assertIn('BOOSTS MINOR (SI NO HAY NINGUNO)',texts)
            self.assertIn('COMPRAR MINOR CON ORO SI FALTA',texts)
            self.assertEqual(sum(getattr(a,'__name__','')=='toggle_boosts_buy' for a in actions),int(not running))
            for x0,y0,x1,y1,action in self.app.zones:
                self.assertLessEqual(x1,self.farm_app.W);self.assertLessEqual(y1,self.farm_app.H)

    def test_unlaunched_accounts_are_grey_and_empty_selection_notice_visible(self):
        from unittest.mock import patch
        self.app.account_status={'steam':{'state':'EN MARCHA','step':'Quest','detail':''}}
        with patch.object(self.app,'label') as label:
            self.app.draw_account_status(0,0)
        for name in ('FMANI','KORTZZ'):
            self.assertIn(unittest.mock.call(f'{name} · DESACTIVADA',0,24 if name=='FMANI' else 48,14,self.farm_app.ui.DIM),label.call_args_list)
        self.app.status='ACTIVA AL MENOS UNA CUENTA';self.app.zones=[]
        with patch.object(self.app,'put'),patch.object(self.app,'label') as label:
            self.app.draw_main()
        self.assertIn(self.app.status,[c.args[0] for c in label.call_args_list])

    def test_multi_start_uses_farm_supervisor_without_legacy_worker(self):
        from unittest.mock import Mock,patch
        from fishing_core import farm_multi
        process=Mock()
        with patch.object(farm_multi,'start_farm',return_value=process) as start, \
                patch.object(self.farm_app.subprocess,'Popen') as legacy, \
                patch.object(self.farm_app.threading,'Thread') as thread:
            self.app.toggle_run()
            start.assert_called_once_with(self.data);legacy.assert_not_called()
            self.assertIs(self.app.process,process)
            thread.assert_called_once_with(target=self.app.follow,args=(process,),daemon=True)
            thread.return_value.start.assert_called_once()


class FarmAppAccountsTests(unittest.TestCase):
    setUp=FarmAppMultiTests.setUp
    def test_four_tabs_and_eight_fit_without_overlap(self):
        from unittest.mock import patch
        from fishing_core import accounts
        accounts.add_account('Cuarta','browser');self.app.refresh_accounts()
        self.assertEqual(self.app.account_tabs()[-1],('cuarta','Cuarta'))
        self.assertEqual(len(self.app.account_tabs()),4)
        for i in range(4):accounts.add_account(f'Extra {i}','browser')
        self.app.refresh_accounts();self.app.img=self.farm_app.Image.new('RGBA',(self.farm_app.W,self.farm_app.H));self.app.zones=[]
        with patch.object(self.app,'label'):self.app.draw_main()
        tabs=[z for z in self.app.zones if 'choose_account' in getattr(getattr(z[-1],'__code__',None),'co_names',())]
        self.assertEqual(len(tabs),8)
        for left,right in zip(tabs,tabs[1:]):self.assertLessEqual(left[2],right[0])
        self.assertTrue(self.app.enabled_accounts['cuarta'])

    def test_add_remove_and_steam_disabled(self):
        from unittest.mock import patch
        self.app.screen='add_account';self.app.img=self.farm_app.Image.new('RGBA',(self.farm_app.W,self.farm_app.H));self.app.zones=[]
        self.app.draw_add_account()
        kinds=[a.__defaults__ for *box,a in self.app.zones if 'create_account' in getattr(getattr(a,'__code__',None),'co_names',())]
        self.assertEqual(kinds,[('browser',)])
        with patch.object(self.farm_app.simpledialog,'askstring',return_value='Nueva'):
            self.app.create_account('browser')
        self.assertIn(('nueva','Nueva'),self.app.account_tabs());self.assertEqual(self.app.screen,'accounts')
        with patch.object(self.farm_app.messagebox,'askyesno',return_value=False):self.app.delete_account('nueva')
        self.assertIn('nueva',self.app.enabled_accounts)
        with patch.object(self.farm_app.messagebox,'askyesno',return_value=True) as confirm:self.app.delete_account('nueva')
        self.assertIn('no se borran',confirm.call_args.args[1]);self.assertNotIn('nueva',self.app.enabled_accounts)
        self.assertTrue((self.root/'steam'/'farm_config.json').exists())

    def test_browser_launches_in_thread_and_results_polled_by_tk(self):
        import threading
        from unittest.mock import patch
        main=threading.get_ident()
        for visible in (True,False):
            calls=[];threads=[];real_thread=threading.Thread
            def factory(**kwargs):
                thread=real_thread(**kwargs);threads.append(thread);return thread
            def launch(account,visible):
                calls.append((account,visible,threading.get_ident()));return object(),{'fixture':'session'}
            with patch.object(self.farm_app,'launch_browser',side_effect=launch),patch.object(self.farm_app,'write_session') as write, \
                    patch.object(self.farm_app.messagebox,'showinfo') as info,patch.object(self.farm_app.threading,'Thread',side_effect=factory):
                self.app.open_browser('personal',visible)
                threads[0].join(timeout=2);self.assertFalse(threads[0].is_alive())
                self.assertEqual(calls[0][:2],('personal',visible));self.assertNotEqual(calls[0][2],main)
                if visible:write.assert_not_called();info.assert_called_once()
                else:write.assert_called_once_with('personal',{'fixture':'session'})
                self.app.poll_browser();self.assertFalse(self.app.browser_busy)

    def test_new_active_missing_session_blocks_start_and_stale_removed_session_ignored(self):
        from unittest.mock import patch
        from fishing_core import accounts,farm_multi
        accounts.add_account('Nueva','browser');self.app.refresh_accounts()
        with patch.object(farm_multi,'start_farm') as start:self.app.toggle_run();start.assert_not_called()
        self.assertIn('FALTAN SESIONES',self.app.status)
        self.app.toggle_account('nueva');accounts.remove_account('personal');self.app.refresh_accounts()
        with patch.object(farm_multi,'start_farm') as start,patch.object(self.farm_app.threading,'Thread'):
            self.app.toggle_run();self.assertEqual(set(start.call_args.args[0]),{'steam','perfil-1'})

    def test_browser_error_and_running_block_management(self):
        from unittest.mock import patch
        with patch.object(self.farm_app,'launch_browser',side_effect=ValueError('fallo offline')), \
                patch.object(self.farm_app.threading,'Thread') as thread:
            self.app.open_browser('personal',False);thread.call_args.kwargs['target']();self.app.poll_browser()
        self.assertIn('fallo offline',self.app.status)
        with patch.object(self.app,'running',return_value=True),patch.object(self.farm_app,'add_account') as add, \
                patch.object(self.farm_app,'launch_browser') as launch:
            self.app.create_account('browser');self.app.open_browser('personal',False)
            add.assert_not_called();launch.assert_not_called()


class FarmAppClickTests(unittest.TestCase):
    """Clics simulados sobre las zonas dibujadas; la configuración va a un archivo temporal."""
    def setUp(self):
        import tkinter
        from unittest.mock import patch
        from fishing_core import farm_app
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        patcher=patch.object(farm_config,'PATH',Path(tmp.name)/'farm_config.json');patcher.start();self.addCleanup(patcher.stop)
        # Nunca el modo multicuenta real: escribiría en runs/accounts/<cuenta>/farm_config.json.
        multi=patch.object(farm_app,'MULTI_SESSIONS',Path(tmp.name)/'sin-sesiones.json');multi.start();self.addCleanup(multi.stop)
        status=patch.object(farm_app,'MULTI_STATUS',Path(tmp.name)/'sin-estado.json');status.start();self.addCleanup(status.stop)
        enabled=patch.object(farm_app,'ENABLED_ACCOUNTS',Path(tmp.name)/'enabled.json');enabled.start();self.addCleanup(enabled.stop)
        from unittest.mock import Mock
        from fishing_core import accounts
        for target,name,value in ((accounts,'ROOT',Path(tmp.name)),
                                  (farm_app,'state_root',lambda root,env=None:Path(tmp.name)),
                                  (farm_app,'runs_root',lambda root,env=None:Path(tmp.name)),
                                  (farm_app.tk.Tk,'__init__',Mock(return_value=None)),
                                  (farm_app.tk,'Canvas',Mock()),
                                  (farm_app.ImageTk,'PhotoImage',lambda image:image)):
            patcher=patch.object(target,name,value);patcher.start();self.addCleanup(patcher.stop)
        for name in ('title','resizable','configure','protocol','after','after_cancel','bind','withdraw','destroy'):
            patcher=patch.object(farm_app.FarmApp,name,Mock());patcher.start();self.addCleanup(patcher.stop)
        self.app=farm_app.FarmApp();self.app.raid_scroll=0;self.app.loot_job=None

    def click_where(self,predicate):
        """Pulsa el centro de la primera zona cuya acción cumple predicate."""
        from types import SimpleNamespace
        for x0,y0,x1,y1,action in self.app.zones:
            if predicate(action):
                self.app.on_click(SimpleNamespace(x=(x0+x1)//2,y=(y0+y1)//2))
                self.app.after_cancel(self.app.click_job);self.app.flush_clicks();return
        self.fail('zona no encontrada')

    def by_default(self,name,value=None):
        return lambda action:getattr(action,'__defaults__',None) and (value is None or value in action.__defaults__) and \
            getattr(action,'__code__',None) and name in action.__code__.co_names

    def test_icon_opens_its_window_and_checkbox_toggles_the_mode(self):
        self.click_where(self.by_default('open_mode','boss'));self.assertEqual(self.app.screen,'boss')
        self.click_where(lambda a:getattr(a,'__name__','')=='go_main');self.assertEqual(self.app.screen,'main')
        self.click_where(self.by_default('toggle_mode','raid'))
        self.assertFalse(farm_config.load()['modes']['raid'])

    def test_boss_tier_and_difficulty_are_saved_and_tier_stays_valid(self):
        self.app.screen='boss';self.app.render()
        self.click_where(self.by_default('set_boss','TITANS_ATTACK'))
        self.assertEqual((farm_config.load()['boss']['boss'],farm_config.load()['boss']['tier']),('TITANS_ATTACK',11))
        self.assertRaises(AssertionError,self.click_where,self.by_default('set_tier',8))  # Titans no tiene T8
        down=lambda a:getattr(a,'__name__','')=='<lambda>' and 'scroll_tiers' in a.__code__.co_names and 1 in (a.__code__.co_consts or ())
        self.click_where(self.by_default('set_boss','NETHERWORLD'));self.app.tier_scroll=0;self.app.render()
        self.assertRaises(AssertionError,self.click_where,self.by_default('set_tier',3))  # T3 bajo el scroll
        for _ in range(7):self.click_where(down)
        self.click_where(self.by_default('set_tier',3));self.assertEqual(farm_config.load()['boss']['tier'],3)
        self.click_where(self.by_default('set_boss','TITANS_ATTACK'));self.assertEqual(farm_config.load()['boss']['tier'],11)
        up=lambda a:getattr(a,'__name__','')=='<lambda>' and 'scroll_tiers' in a.__code__.co_names and -1 in (a.__code__.co_consts or ())
        for _ in range(3):self.click_where(up)
        self.click_where(self.by_default('set_tier',13))
        self.click_where(self.by_default('set_tier',13));self.click_where(lambda a:getattr(a,'__defaults__',None)==('HARD',))
        self.assertEqual(farm_config.load()['boss'],{'boss':'TITANS_ATTACK','tier':13,'difficulty':'Hard'})

    def test_quest_targets_without_gold_buttons(self):
        self.app.screen='quest';self.app.render()
        self.click_where(self.by_default('toggle_target','Mummih'))
        q=farm_config.load()['quest'];self.assertEqual(q['targets'],['Mummih'])
        self.assertNotIn('max_gold',q)
        for screen in ('quest','raid'):
            self.app.screen=screen;self.app.render()
            self.assertRaises(AssertionError,self.click_where,self.by_default('set_gold',100_000))
            self.assertRaises(AssertionError,self.click_where,self.by_default('set_raid_gold',100_000))

    def test_trials_range_and_level_stay_inside_the_range(self):
        self.app.screen='trials';self.app.render()
        self.click_where(lambda a:getattr(a,'__defaults__',None) and a.__defaults__[0]==(10,640,674,'set'))
        self.assertEqual(farm_config.load()['trials']['difficulty'],674)
        self.click_where(self.by_default('step_level',10));self.assertEqual(farm_config.load()['trials']['difficulty'],674)
        self.click_where(self.by_default('step_level',-10));self.assertEqual(farm_config.load()['trials']['difficulty'],664)

    def test_the_loot_window_refreshes_itself_while_open(self):
        from unittest.mock import patch
        self.app.screen='loot';self.app.render();self.assertIsNotNone(self.app.loot_job)
        with patch.object(self.app,'render') as render:self.app.refresh_loot();render.assert_called_once()
        self.app.screen='main'
        with patch.object(self.app,'render') as render:self.app.refresh_loot();render.assert_not_called()

    def test_every_screen_renders(self):
        for screen in ('main','quest','boss','raid','trials','pvp','expedition','loot','accounts','add_account'):
            self.app.screen=screen;self.app.render();self.assertTrue(self.app.zones)

class FarmAppAnimationTests(unittest.TestCase):
    def make_app(self):
        from types import SimpleNamespace,MethodType
        from unittest.mock import Mock
        from fishing_core.farm_app import FarmApp
        app=SimpleNamespace(pending_clicks=[],pending_wheel=[],click_job=None,wheel_job=None,
                            pressed_zones=set(),hover_zone=None,zones=[],wheel_zone=(0,0,100,100),
                            tier_scroll=0,raid_scroll=0,after=Mock(return_value='job'),render=Mock(),present=Mock())
        for name in ('on_click','flush_clicks','on_wheel','flush_wheel','scroll_tiers','scroll_raids','on_hover'):
            setattr(app,name,MethodType(getattr(FarmApp,name),app))
        return app

    def test_fifty_wheel_events_schedule_one_render_and_keep_all_steps(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        from fishing_core.farm_app import FarmApp
        for kind in ('tiers','raids','trials'):
            app=self.make_app()
            if kind=='trials':
                from types import MethodType
                app.config_data={'trials':{'difficulty':700}};app.save=Mock()
                app.wheel_action=MethodType(FarmApp.step_level,app)
            else:app.wheel_action=app.scroll_tiers if kind=='tiers' else app.scroll_raids
            for _ in range(50):app.on_wheel(SimpleNamespace(x=10,y=10),1)
            app.after.assert_called_once_with(16,app.flush_wheel);app.render.assert_not_called()
            app.flush_wheel();self.assertLessEqual(app.render.call_count,2)
            self.assertEqual(app.config_data['trials']['difficulty'] if kind=='trials' else
                             app.tier_scroll if kind=='tiers' else app.raid_scroll,750 if kind=='trials' else 50)
            self.assertIsNone(app.wheel_job)

    def test_click_burst_sinks_once_then_runs_every_action_and_renders_once(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        app=self.make_app();action=Mock();app.zones=[(0,0,30,30,action)]
        for _ in range(50):app.on_click(SimpleNamespace(x=10,y=10))
        action.assert_not_called();app.present.assert_called_once_with()
        self.assertEqual(app.pressed_zones,{(0,0,30,30)})
        app.after.assert_called_once_with(90,app.flush_clicks)
        app.flush_clicks();self.assertEqual(action.call_count,50)
        app.render.assert_called_once_with();self.assertFalse(app.pressed_zones)

    def test_hover_only_presents_when_zone_changes(self):
        from types import SimpleNamespace
        app=self.make_app();app.zones=[(0,0,30,30,lambda:None)]
        for _ in range(50):app.on_hover(SimpleNamespace(x=10,y=10))
        app.present.assert_called_once_with();app.render.assert_not_called()
        app.on_hover(None);self.assertEqual(app.present.call_count,2)

    def test_present_darkens_and_moves_pressed_zone_four_pixels(self):
        from unittest.mock import Mock,patch
        from PIL import Image
        from fishing_core import farm_app
        app=self.make_app();app.img=Image.new('RGBA',(50,50),(25,40,58,255));app.canvas=Mock()
        app.img.paste((200,100,60,255),(10,10,20,20));app.zones=[(10,10,20,20,lambda:None)]
        app.pressed_zones={(10,10,20,20)}
        with patch.object(farm_app.ImageTk,'PhotoImage',side_effect=lambda img:img.copy()):
            farm_app.FarmApp.present(app)
        self.assertEqual(app.photo.getpixel((10,10)),(25,40,58,255))
        self.assertEqual(app.photo.getpixel((10,14)),(164,82,49,255))

if __name__=='__main__':unittest.main()
