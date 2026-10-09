"""PvP offline: capturas reales saneadas; tickets simulados como en la sesión real."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from fishing_core.control_flow import SafetyStop
from fishing_core.dungeon_vision import DungeonVision
from fishing_core.pvp_runtime import PvpRunner

with np.load(Path(__file__).parent/'fixtures/dungeons.npz',allow_pickle=False) as data:
    FRAMES={k:data[k] for k in data.files if k.startswith(('pvp_','boss_victory','boss_not_full'))}
VISION=DungeonVision()


class FakeGame:
    def __init__(self,results):
        self.state='pvp_home';self.results=iter(results);self.plays=[];self.cost=5
        self.moves={('pvp_home',(90,280)):'pvp_window',('pvp_select',(1390,769)):'pvp_team',
                    ('pvp_window',(1370,416)):'pvp_cost_menu',('pvp_cost_menu',(930,316)):'pvp_window_cost1',
                    ('pvp_window',(1494,226)):'pvp_home',('pvp_window_cost1',(1494,226)):'pvp_home'}

    def click(self,xy):
        xy=tuple(xy)
        if self.state in ('pvp_window','pvp_window_cost1') and xy==(1280,568):
            self.plays.append(1 if self.state.endswith('cost1') else 5);self.state='pvp_select';return
        if self.state=='pvp_team' and xy==(1215,982):self.state=next(self.results);return
        if self.state=='boss_not_full' and xy==(816,750):self.state=next(self.results);return
        if self.state in ('boss_victory','pvp_defeat'):
            x,y=VISION.locate(FRAMES[self.state],'RESULT_TOWN',(700,915,1500,1080))
            h,w=VISION.templates['RESULT_TOWN'].shape[:2]
            assert xy==(x+w//2,y+h//2),xy
            self.state='pvp_window_cost1' if self.plays[-1]==1 else 'pvp_window';return
        self.state=self.moves[(self.state,xy)]


class PvpRuntimeTests(unittest.TestCase):
    def run_pvp(self,game,tickets,fights=10):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);io=Mock();io.click.side_effect=game.click
            channel=SimpleNamespace(directory=path,run_id='test',stop_path=path/'stop.json')
            runner=PvpRunner(io,Mock(),VISION,channel,Mock(),fights)
            runner.capture=lambda:FRAMES[game.state]
            clock=[0.0]
            def sleep(seconds):clock[0]+=seconds
            fake=SimpleNamespace(monotonic=lambda:clock[0],sleep=sleep,perf_counter_ns=lambda:0)
            with patch('fishing_core.dungeon_runtime.time',fake),patch('fishing_core.pvp_runtime.time',fake), \
                    patch.object(PvpRunner,'tickets',side_effect=tickets):
                runner.run()
            return runner

    def test_spends_every_ticket_lowering_the_cost_and_keeps_going_after_a_defeat(self):
        game=FakeGame(['boss_victory','pvp_defeat','boss_victory'])
        runner=self.run_pvp(game,[11,6,1,0])
        self.assertEqual(game.plays,[5,5,1]);self.assertEqual(game.state,'pvp_home')
        self.assertEqual(runner.budget.energy_reserved,11)
        self.assertEqual(runner.budget.payload()['completed_runs'],3);self.assertEqual(runner.budget.gold_reserved,0)

    def test_incomplete_team_warning_is_accepted_and_the_fight_goes_on(self):
        game=FakeGame(['boss_not_full','boss_victory'])
        self.run_pvp(game,[5,0])
        self.assertEqual(game.plays,[5]);self.assertEqual(game.state,'pvp_home')

    def test_chosen_opponent_row_gets_the_fight(self):
        game=FakeGame(['boss_victory']);clicks=[]
        original=game.click
        def spy(xy):
            clicks.append(tuple(xy))
            if game.state=='pvp_select':game.state='pvp_team';return
            original(xy)
        game.click=spy
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);io=Mock();io.click.side_effect=game.click
            runner=PvpRunner(io,Mock(),VISION,SimpleNamespace(directory=path,run_id='t',stop_path=path/'s.json'),Mock(),1,1)
            runner.capture=lambda:FRAMES[game.state]
            clock=[0.0]
            def sleep(s):clock[0]+=s
            fake=SimpleNamespace(monotonic=lambda:clock[0],sleep=sleep,perf_counter_ns=lambda:0)
            with patch('fishing_core.dungeon_runtime.time',fake),patch('fishing_core.pvp_runtime.time',fake), \
                    patch.object(PvpRunner,'tickets',side_effect=[5,0]):runner.run()
        self.assertIn((1390,423),clicks);self.assertNotIn((1390,769),clicks)
        with self.assertRaises(ValueError):PvpRunner(Mock(),Mock(),VISION,Mock(),Mock(),1,5)

    def test_no_tickets_closes_the_window_without_playing(self):
        game=FakeGame([]);self.run_pvp(game,[0])
        self.assertEqual(game.plays,[]);self.assertEqual(game.state,'pvp_home')

    def test_cost_that_does_not_change_never_presses_play(self):
        game=FakeGame([]);game.moves[('pvp_cost_menu',(930,316))]='pvp_window'  # sigue en 5
        with self.assertRaises(SafetyStop):self.run_pvp(game,[1])
        self.assertEqual(game.plays,[])


    def test_scrolls_to_the_bottom_where_the_richest_rival_is(self):
        for opponent,y in ((4,820),(1,474)):
            io=Mock();runner=PvpRunner(io,Mock(),VISION,Mock(),Mock(),1,opponent);runner.check=Mock()
            frame=FRAMES['pvp_select_scrolled'];runner.capture=lambda:frame
            with patch('fishing_core.pvp_runtime.time.sleep'),patch('fishing_core.dungeon_runtime.time.sleep'):runner.choose_opponent()
            io.wheel.assert_called_once();self.assertGreater(io.wheel.call_args.args[0],0)  # hacia abajo
            self.assertEqual(io.click.call_args.args[0],(1390,y))


if __name__=='__main__':unittest.main()
