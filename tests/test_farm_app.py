"""App del Farm Bot sin pantalla: catálogo, configuración y pasos que lanzará START."""

import tempfile
import unittest
from pathlib import Path

from fishing_core import farm_all, farm_config, pixel_ui
from fishing_core.farm_app import CALIBRATED, familiars_of


class FarmAppTests(unittest.TestCase):
    def test_tealks_palace_lists_its_four_familiars_and_only_calibrated_routes_are_selectable(self):
        self.assertEqual(set(familiars_of('Z5D3')),{'Mummih','Brute','Sitra','Tealk'})
        self.assertEqual(CALIBRATED,{'Z5D2','Z5D3'})

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


if __name__=='__main__':unittest.main()
