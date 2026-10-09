"""Runas menores de dos cuentas distintas: tipo por símbolo y rareza por color, sin plantillas por cuenta."""

import unittest
from unittest.mock import Mock, patch
from pathlib import Path

import numpy as np

from fishing_core.dungeon_vision import DungeonVision
from fishing_core.runes_runtime import INSERT_ROI, LIST_ROI, OPTIONS_CLOSE, SLOTS, SWITCH, RunesRunner

with np.load(Path(__file__).parent/'fixtures/dungeons.npz',allow_pickle=False) as data:
    FRAMES={k:data[k] for k in data.files if k.startswith(('runes_','rune_tooltip','rune_options_'))}
VISION=DungeonVision()


class EmptySlotTests(unittest.TestCase):
    def runner(self):
        runner=RunesRunner(Mock(),Mock(),DungeonVision(),Mock(),Mock())
        runner.check=Mock()
        runner.board=Mock()
        return runner

    def test_real_empty_options_has_insert_but_no_active_switch(self):
        runner=self.runner();frame=FRAMES['rune_options_empty_slot']
        self.assertIsNotNone(runner.vision.locate(frame,'RUNE_INSERT',INSERT_ROI))
        self.assertIsNone(runner.vision.locate(frame,'RUNE_SWITCH',SWITCH[2]))
        template=runner.vision.templates['RUNE_INSERT']
        RunesRunner(Mock(),Mock(),runner.vision,Mock(),Mock())
        self.assertIs(runner.vision.templates['RUNE_INSERT'],template)

    def empty_wait(self,predicate,timeout,expected):
        self.assertEqual(timeout,10)
        self.assertEqual(expected,'opciones de runa')
        frame=FRAMES['rune_options_empty_slot']
        self.assertTrue(predicate(frame))
        return frame

    @patch('fishing_core.runes_runtime.time.sleep')
    def test_apply_skips_both_empty_slots_without_inserting_or_melting(self,sleep):
        runner=self.runner();runner.wait=self.empty_wait
        runner.slot_runes=Mock(return_value=[None,None])
        runner.scan=Mock();runner.click_best=Mock();runner.close_list=Mock()
        self.assertTrue(runner.apply('ITEM_FIND'))
        self.assertEqual([c.args[0] for c in runner.io.click.call_args_list],
                         [SLOTS[0],OPTIONS_CLOSE,SLOTS[1],OPTIONS_CLOSE])
        runner.scan.assert_not_called();runner.click_best.assert_not_called()
        runner.close_list.assert_not_called()
        self.assertEqual([c.args[0] for c in runner.log.emit.call_args_list],['RUNE_SLOT_EMPTY']*2)
        self.assertEqual([c.kwargs['slot'] for c in runner.log.emit.call_args_list],[0,1])
        self.assertEqual(runner.board.call_count,4)

    @patch('fishing_core.runes_runtime.time.sleep')
    def test_apply_continues_with_occupied_slot_after_empty_slot(self,sleep):
        runner=self.runner();runner.wait=self.empty_wait
        runner.slot_runes=Mock(return_value=[('VRYN','LEGENDARY',30),None])
        open_list=runner.open_list
        runner.open_list=Mock(side_effect=lambda slot:open_list(slot) if slot==1 else FRAMES['runes_list_a'])
        runner.scan=Mock(return_value=(30,'LEGENDARY',0,(960,560)))
        runner.close_list=Mock();runner.click_best=Mock()
        self.assertTrue(runner.apply('ITEM_FIND'))
        self.assertEqual([c.args[0] for c in runner.open_list.call_args_list],[1,0])
        runner.scan.assert_called_once_with('VRYN')
        runner.close_list.assert_called_once_with();runner.click_best.assert_not_called()
        self.assertEqual([c.args[0] for c in runner.io.click.call_args_list],[SLOTS[1],OPTIONS_CLOSE])

    @patch('fishing_core.runes_runtime.time.sleep')
    def test_leave_runes_closes_real_empty_options(self,sleep):
        runner=self.runner()
        runner.capture=Mock(side_effect=[FRAMES['rune_options_empty_slot'],np.zeros((1080,1920,3),np.uint8)])
        runner.leave_runes()
        runner.io.click.assert_called_once_with(OPTIONS_CLOSE)
        runner.check.assert_called_once_with()


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
        # El borde cambia de color según la runa: amarillo pálido o blanco.
        self.assertEqual(VISION.tooltip_kind(FRAMES['rune_tooltip_white_before'],FRAMES['rune_tooltip_white_after']),'VRYN')
        self.assertTrue(VISION.tooltip_visible(FRAMES['rune_tooltip_white_after']))
        self.assertFalse(VISION.tooltip_visible(FRAMES['rune_tooltip_white_before']))


if __name__=='__main__':unittest.main()
