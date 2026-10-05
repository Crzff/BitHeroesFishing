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
                                       ('MATERIAL','COMMON',9),('ITEM','RARE',1),('MATERIAL','COMMON',2)])
        self.assertEqual(read(raid),[('XP','COMMON',9100),('GOLD','COMMON',7100),('MATERIAL','COMMON',3),
                                     ('ITEM','LEGENDARY',1),('ITEM','RARE',1),('ITEM','RARE',1)])
        with tempfile.TemporaryDirectory() as tmp,patch.object(loot,'ENABLED',True):
            path=Path(tmp)/'l.json';loot.record(vision.loot_cells(trials)+vision.loot_cells(raid),path,Path(tmp)/'album')
            data=loot.load(path)
            self.assertEqual((data['gold'],data['xp'],data['items'],data['materials']),(13700,19200,{'RARE':3,'LEGENDARY':1},{'COMMON':20}))
            self.assertEqual(len(list((Path(tmp)/'album').glob('*.png'))),len(data['album']))

    def test_nothing_is_written_unless_farm_all_enabled_it(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(loot,'ENABLED',False),patch.object(loot,'PATH',Path(tmp)/'l.json'):
            loot.spend('ENERGY',30);loot.familiar('Tealk');self.assertFalse((Path(tmp)/'l.json').exists())


if __name__=='__main__':unittest.main()
