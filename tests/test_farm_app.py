"""App del Farm Bot sin pantalla: catálogo, configuración y pasos que lanzará START."""

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
        for img in (pixel_ui.frame(400,300,'WORLD BOSS'),pixel_ui.checkbox(True),pixel_ui.auto_button(True),
                    pixel_ui.button('HEROIC',200),pixel_ui.icon('quest')):
            self.assertGreater(img.width*img.height,0)



class FarmAppClickTests(unittest.TestCase):
    """Clics simulados sobre las zonas dibujadas; la configuración va a un archivo temporal."""
    def setUp(self):
        import tkinter
        from unittest.mock import patch
        from fishing_core import farm_app
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        patcher=patch.object(farm_config,'PATH',Path(tmp.name)/'cfg.json');patcher.start();self.addCleanup(patcher.stop)
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

    def test_every_screen_renders(self):
        for screen in ('main','quest','boss','raid','trials','pvp','expedition'):
            self.app.screen=screen;self.app.render();self.assertTrue(self.app.zones)

if __name__=='__main__':unittest.main()
