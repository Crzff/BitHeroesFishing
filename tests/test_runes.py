"""Runas menores de dos cuentas distintas: tipo por símbolo y rareza por color, sin plantillas por cuenta."""

import unittest
from pathlib import Path

import numpy as np

from fishing_core.dungeon_vision import DungeonVision
from fishing_core.runes_runtime import LIST_ROI, SLOTS

with np.load(Path(__file__).parent/'fixtures/dungeons.npz',allow_pickle=False) as data:
    FRAMES={k:data[k] for k in data.files if k.startswith(('runes_','rune_tooltip'))}
VISION=DungeonVision()


class RuneTests(unittest.TestCase):
    def listed(self,key):
        return [(k,r,v) for _,k,r,v in VISION.runes_in(FRAMES[key],LIST_ROI)]

    def test_list_of_each_account_reads_type_rarity_and_bonus(self):
        self.assertEqual(self.listed('runes_list_a'),[('VRYN','MYTHIC',37.5),('ZYRK','LEGENDARY',20),('DAR','EPIC',15)])
        self.assertEqual(self.listed('runes_list_b'),[('ZYRK','MYTHIC',25),('QUINDI','LEGENDARY',20)])

    def test_equipped_slots_on_the_board(self):
        def slots(key):return [VISION.rune(FRAMES[key][y-90:y+90,x-90:x+90]) for x,y in SLOTS]
        self.assertEqual(slots('runes_board_a'),[('VRYN','MYTHIC',37.5),('VRYN','LEGENDARY',30)])
        self.assertEqual(slots('runes_board_b'),[('VRYN','LEGENDARY',30),('VRYN','LEGENDARY',30)])

    def test_nothing_is_read_on_an_empty_area(self):
        self.assertEqual(VISION.runes_in(np.zeros((1080,1920,3),np.uint8),LIST_ROI),[])


    def test_the_tooltip_names_the_rune_type_even_when_the_symbol_fails(self):
        self.assertEqual(VISION.tooltip_kind(FRAMES['rune_tooltip_before'],FRAMES['rune_tooltip_after']),'ZYRK')
        self.assertIsNone(VISION.tooltip_kind(FRAMES['rune_tooltip_before'],FRAMES['rune_tooltip_before']))


if __name__=='__main__':unittest.main()
