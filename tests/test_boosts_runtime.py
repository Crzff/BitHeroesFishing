"""Juego simulado con capturas BGR reales; ningún backend gráfico ni input real."""
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from pathlib import Path

import numpy as np

from fishing_core.boosts_runtime import BoostsRunner,BOOSTS,LIST_ROI
from fishing_core.control_flow import SafetyStop
from fishing_core.dungeon_vision import DungeonVision


class Game:
    def __init__(self,frames,active=False,wrong=False,missing=()):
        self.frames=frames;self.state='home_four_boosts' if active else 'home_no_boosts'
        self.wrong=wrong;self.missing=missing;self.clicks=[];self.moves=[];self.used=[];self.events=[]
        self.runner=None;self.pending=None

    def frame(self):
        frame=self.frames[self.state].copy()
        if self.state=='inventory_consumables_bottom':
            boxes={'speed':(1104,348),'gold':(1252,348),'xp':(1400,348),'item_find':(1104,496)}
            for kind in self.missing:
                x,y=boxes[kind];frame[y:y+128,x:x+129]=0
        return frame

    def emergency(self):pass
    def check_game(self):pass
    def check(self):pass
    def emit(self,event,**data):self.events.append((event,data))
    def _move(self,xy):self.moves.append(xy)

    def click(self,xy):
        self.clicks.append(xy)
        if self.state=='home_no_boosts':
            assert xy==(90,1010);self.state='inventory_consumables_top'
        elif self.state=='inventory_filter':
            assert xy==(1186,578);self.state='inventory_consumables_top'
        elif self.state.startswith('inventory_consumables'):
            if xy==(1338,238):self.state='inventory_filter'
            elif xy==(1652,112):self.state='home_four_boosts'
            else:
                verified=[]
                for kind in BOOSTS:
                    pos=self.runner.locate(self.frame(),kind,LIST_ROI)
                    if pos is not None:
                        ref=self.runner.vision.templates['BOOST_'+kind.upper()]
                        if xy==(pos[0]+ref.shape[1]//2,pos[1]+ref.shape[0]//2):verified.append(kind)
                assert len(verified)==1,'Clic en celda no verificada'
                self.pending=verified[0]
                other='speed' if self.pending!='speed' else 'gold'
                self.state='consume_confirm_'+(other if self.wrong else self.pending)
        elif self.state.startswith('consume_confirm_'):
            assert xy==(814,748);assert self.state=='consume_confirm_'+self.pending
            self.used.append(self.pending);self.state='boost_activated'
        elif self.state=='boost_activated':
            assert xy==(960,994);self.state='inventory_consumables_bottom'
        else:raise AssertionError(self.state)


class SimRunner(BoostsRunner):
    def capture(self):self.check();return self.io.frame()
    def ensure_home(self):
        self.check()
        if self.vision.screen(self.capture())!='HOME':raise SafetyStop('No está en Home')
    def wheel(self,amount,xy):
        self.check();assert self.io.state.startswith('inventory_consumables')
        self.io.state='inventory_consumables_bottom';self.io._move((960,1070))
    def wait(self,predicate,timeout=10,expected=None):
        return super().wait(predicate,min(timeout,.5),expected)


class BoostsRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with np.load('tests/fixtures/dungeons.npz') as frames:
            cls.frames={n:frames[n] for n in frames.files if n.startswith(('home_no_boosts','home_four_boosts','inventory_','consume_confirm_','boost_activated'))}

    def runner(self,**kwargs):
        game=Game(self.frames,**kwargs)
        runner=SimRunner(game,None,DungeonVision(),SimpleNamespace(stop_path=Path('tests/nonexistent-boost-stop')),game)
        game.runner=runner
        return runner,game

    @patch('fishing_core.boosts_runtime.time.sleep')
    def test_consumes_four_verified_minor_cells(self,sleep):
        runner,game=self.runner()
        self.assertEqual(runner.run(),[])
        self.assertEqual(game.used,list(BOOSTS))
        self.assertEqual(game.clicks.count((814,748)),4)
        self.assertEqual(game.clicks.count((960,994)),4)
        self.assertEqual(game.clicks[-1],(1652,112))
        self.assertGreaterEqual(len(game.moves),len(game.clicks))
        self.assertTrue(all(p==(960,1070) for p in game.moves))
        self.assertEqual(game.state,'home_four_boosts')

    @patch('fishing_core.boosts_runtime.time.sleep')
    def test_active_has_no_clicks(self,sleep):
        runner,game=self.runner(active=True)
        self.assertEqual(runner.run(),[]);self.assertEqual(game.clicks,[])
        self.assertIn(('BOOSTS_STATUS',{'message':'ya activos'}),game.events)

    @patch('fishing_core.boosts_runtime.time.sleep')
    def test_wrong_confirmation_stops_before_yes(self,sleep):
        runner,game=self.runner(wrong=True)
        with self.assertRaises(SafetyStop):runner.run()
        self.assertNotIn((814,748),game.clicks);self.assertEqual(game.used,[])

    @patch('fishing_core.boosts_runtime.time.sleep')
    def test_missing_returns_names_and_closes(self,sleep):
        runner,game=self.runner(missing=('gold','xp'))
        self.assertEqual(runner.run(),[BOOSTS['xp'],BOOSTS['gold']])
        self.assertEqual(game.used,['item_find','speed'])
        self.assertEqual(sum(e=='BOOST_MISSING' for e,_ in game.events),2)
        self.assertEqual(game.clicks[-1],(1652,112))

    def test_one_active_on_different_background(self):
        runner,game=self.runner()
        frame=self.frames['home_no_boosts'].copy()
        frame[960:1080,425:1100]=17
        frame[1047:1067,438:517]=self.frames['home_four_boosts'][1047:1067,438:517]
        self.assertIsNotNone(runner.locate(frame,'active',(425,1038,1100,1075)))
        self.assertIsNone(runner.locate(self.frames['home_no_boosts'],'active',(425,1038,1100,1075)))

    def test_blue_and_red_borders_do_not_match(self):
        runner,game=self.runner()
        original=self.frames['inventory_consumables_bottom']
        for color in ((230,80,50),(70,50,240)):
            frame=original.copy();cell=frame[348:476,1252:1381]
            green=(cell[:,:,1]>150)&(cell[:,:,0]<160)&(cell[:,:,2]<160)
            cell[green]=color
            self.assertIsNone(runner.locate(frame,'gold',LIST_ROI))

    def test_name_changed_immediately_before_yes(self):
        runner,game=self.runner()
        game.state='consume_confirm_gold'
        with self.assertRaises(SafetyStop):
            runner.press((814,748),'confirm_item_find',(690,455,1230,625),('yes',(690,695,945,800)))
        self.assertEqual(game.clicks,[])

    def test_yes_absent_never_spends(self):
        runner,game=self.runner()
        frame=self.frames['consume_confirm_item_find'].copy()
        frame[695:800,690:945]=0
        with patch.object(runner,'capture',return_value=frame):
            with self.assertRaises(SafetyStop):
                runner.press((814,748),'confirm_item_find',(690,455,1230,625),('yes',(690,695,945,800)))
        self.assertEqual(game.clicks,[])
