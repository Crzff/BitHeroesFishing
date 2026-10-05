"""Totales de loot: suman por rareza y nombre, ignoran datos corruptos y se reinician."""

import tempfile
import unittest
from pathlib import Path

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


if __name__=='__main__':unittest.main()
