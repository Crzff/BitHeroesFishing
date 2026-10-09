"""App del Farm Bot sin pantalla: catálogo, configuración y pasos que lanzará START."""

import sys
import tempfile
import unittest
from pathlib import Path

from fishing_core import farm_all, farm_config, pixel_ui
from fishing_core.farm_app import CALIBRATED, familiars_of


class FarmAppTests(unittest.TestCase):
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
        self.assertEqual([name for name,_ in farm_all.steps(loaded)],['Quest','PvP','World Boss','Expedition','Trials'])
        loaded['runes']=True
        self.assertEqual([name for name,_ in farm_all.steps(loaded)][:3],['Runas captura','Quest','Runas Item Find'])

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
            farm_app.FarmApp.on_click(app,SimpleNamespace(x=(x+x1)//2,y=(y+y1)//2))
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


class FarmAppClickTests(unittest.TestCase):
    """Clics simulados sobre las zonas dibujadas; la configuración va a un archivo temporal."""
    def setUp(self):
        import tkinter
        from unittest.mock import patch
        from fishing_core import farm_app
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        patcher=patch.object(farm_config,'PATH',Path(tmp.name)/'cfg.json');patcher.start();self.addCleanup(patcher.stop)
        # Nunca el modo multicuenta real: escribiría en runs/accounts/<cuenta>/farm_config.json.
        multi=patch.object(farm_app,'MULTI_SESSIONS',Path(tmp.name)/'sin-sesiones.json');multi.start();self.addCleanup(multi.stop)
        try:self.app=farm_app.FarmApp()
        except tkinter.TclError:self.skipTest('sin pantalla para Tk')
        self.app.withdraw();self.addCleanup(self.app.destroy)

    def click_where(self,predicate):
        """Pulsa el centro de la primera zona cuya acción cumple predicate."""
        from types import SimpleNamespace
        for x0,y0,x1,y1,action in self.app.zones:
            if predicate(action):self.app.on_click(SimpleNamespace(x=(x0+x1)//2,y=(y0+y1)//2));return
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

    def test_quest_targets_and_gold_quota(self):
        self.app.screen='quest';self.app.render()
        self.click_where(self.by_default('toggle_target','Mummih'));self.click_where(self.by_default('set_gold',100_000))
        q=farm_config.load()['quest'];self.assertEqual((q['targets'],q['max_gold']),(['Tealk','Mummih'],100_000))

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
        for screen in ('main','quest','boss','raid','trials','pvp','expedition','loot'):
            self.app.screen=screen;self.app.render();self.assertTrue(self.app.zones)

if __name__=='__main__':unittest.main()
