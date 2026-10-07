"""Totales de loot: suman por rareza y nombre, ignoran datos corruptos y se reinician."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fishing_core import loot


class LootTests(unittest.TestCase):
    def test_counts_accumulate_and_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'l.json'
            loot.add(path,gold=100,items={'EPIC':1},familiars={'Tealk':1})
            data=loot.add(path,gold=50,xp=7,items={'EPIC':2,'SET':1},spent={'energy':30})
            self.assertEqual((data['gold'],data['xp'],data['items'],data['familiars'],data['spent']),
                             (150,7,{'EPIC':3,'SET':1},{'Tealk':1},{'energy':30}))
            loot.reset(path);self.assertEqual(loot.load(path),loot.empty())

    def test_corrupt_file_reads_as_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'l.json';path.write_text('{"gold":"mucho","items":{"EPIC":-3}}')
            self.assertEqual(loot.load(path),loot.empty())


    def test_recap_cells_are_read_from_real_result_screens(self):
        import numpy as np
        from fishing_core.dungeon_vision import DungeonVision
        with np.load(Path(__file__).parent/'fixtures/dungeons.npz',allow_pickle=False) as data:
            trials,raid=data['loot_recap_trials'],data['loot_recap_raid']
        vision=DungeonVision();read=lambda f:[(c['kind'],c['rarity'],c['amount']) for c in vision.loot_cells(f)]
        self.assertEqual(read(trials),[('MATERIAL','COMMON',6),('XP','COMMON',10100),('GOLD','COMMON',6600),
                                       ('MATERIAL','COMMON',9),('ITEM','RARE',1),('ITEM','COMMON',2)])  # amuleto x2 con flecha
        self.assertEqual(read(raid),[('XP','COMMON',9100),('GOLD','COMMON',7100),('MATERIAL','COMMON',3),
                                     ('ITEM','LEGENDARY',1),('ITEM','RARE',1),('ITEM','RARE',1)])
        with np.load(Path(__file__).parent/'fixtures/dungeons.npz',allow_pickle=False) as data:quest=data['loot_recap_quest']
        self.assertEqual(read(quest),[('MATERIAL','COMMON',1),('XP','COMMON',1400),('GOLD','COMMON',1800),
                                      ('MATERIAL','COMMON',2),('ITEM','COMMON',1),('ITEM','COMMON',1)])  # 4 y 8 en vivo
        with tempfile.TemporaryDirectory() as tmp,patch.object(loot,'ENABLED',True):
            path=Path(tmp)/'l.json';loot.record(vision.loot_cells(trials)+vision.loot_cells(raid),path,Path(tmp)/'album')
            data=loot.load(path)
            self.assertEqual((data['gold'],data['xp'],data['items'],data['materials']),(13700,19200,{'RARE':3,'LEGENDARY':1,'COMMON':2},{'COMMON':18}))
            self.assertEqual(len(list((Path(tmp)/'album').glob('*.png'))),len(data['album']))

    def test_nothing_is_written_unless_farm_all_enabled_it(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(loot,'ENABLED',False),patch.object(loot,'PATH',Path(tmp)/'l.json'):
            loot.spend('ENERGY',30);loot.familiar('Tealk');self.assertFalse((Path(tmp)/'l.json').exists())


    def test_border_colours_of_the_game_map_to_each_rarity(self):
        import numpy as np
        from fishing_core.dungeon_vision import loot_rarity
        colours={(128,252,145):'COMMON',(125,145,254):'RARE',(240,128,112):'EPIC',(243,222,121):'LEGENDARY',
                 (240,80,112):'MYTHIC',(128,240,240):'SET'}  # RGB medidos en el LOOT RECAP
        for rgb,rarity in colours.items():self.assertEqual(loot_rarity(np.uint8(rgb[::-1])),rarity,rgb)


    def test_the_game_description_says_if_a_drop_is_material_consumable_or_equipment(self):
        import numpy as np
        from fishing_core.dungeon_vision import DungeonVision
        with np.load(Path(__file__).parent/'fixtures/dungeons.npz',allow_pickle=False) as data:
            frames={k:data[k] for k in data.files if k.startswith('loot_tip_')}
        vision=DungeonVision();before=frames['loot_tip_before']
        for name,kind in (('consumable','CONSUMABLE'),('material','MATERIAL'),('item','ITEM'),('currency','CURRENCY')):
            self.assertEqual(vision.loot_tooltip(before,frames['loot_tip_'+name]),kind,name)
        self.assertIsNone(vision.loot_tooltip(before,before))  # sin descripción abierta

    def test_known_kinds_are_remembered_per_icon(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'k.json';self.assertIsNone(loot.known_kind('abc',path))
            loot.remember_kind('abc','CONSUMABLE',path);self.assertEqual(loot.known_kind('abc',path),'CONSUMABLE')


    def test_the_bot_only_counts_gold_xp_mythic_and_set_without_hovering(self):
        import numpy as np
        from types import SimpleNamespace
        from unittest.mock import Mock
        from fishing_core.dungeon_runtime import DungeonRunner
        icon=lambda n:np.full((109,109,3),n,np.uint8)
        cells=[{'kind':'GOLD','rarity':'COMMON','amount':500,'icon':icon(1)},{'kind':'MATERIAL','rarity':'RARE','amount':9,'icon':icon(2)},
               {'kind':'ITEM','rarity':'MYTHIC','amount':1,'icon':icon(3)},{'kind':'MATERIAL','rarity':'SET','amount':2,'icon':icon(4)}]
        runner=DungeonRunner.__new__(DungeonRunner);runner.io=Mock();runner.log=Mock();runner.capture=Mock()
        runner.vision=SimpleNamespace(loot_cells=lambda f:cells);runner.loot_kind=Mock()
        with tempfile.TemporaryDirectory() as tmp,patch.object(loot,'ENABLED',True),patch.object(loot,'PATH',Path(tmp)/'l.json'), \
                patch.object(loot,'ALBUM',Path(tmp)/'a'):
            runner.record_loot();data=loot.load()
        self.assertEqual((data['gold'],data['items'],data['materials']),(500,{'MYTHIC':1},{'SET':2}))
        runner.loot_kind.assert_not_called();runner.io._move.assert_not_called()


if __name__=='__main__':unittest.main()
