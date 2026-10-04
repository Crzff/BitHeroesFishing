"""World Boss offline: capturas reales saneadas y un juego falso que avanza con cada clic."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from fishing_core.boss_runtime import BossRunner
from fishing_core.control_flow import SafetyStop
from fishing_core.dungeon_vision import DungeonVision

with np.load(Path(__file__).parent/'fixtures/dungeons.npz',allow_pickle=False) as data:
    FRAMES={k:data[k] for k in data.files if k.startswith('boss_')}
VISION=DungeonVision()


class FakeGame:
    def __init__(self,summon='boss_summon_normal',lobby='boss_lobby',result='boss_victory',home='boss_home'):
        self.state=home;self.starts=0;self.regroups=0;self.lobby=lobby
        self.moves={('boss_home',(90,430)):'boss_list',('boss_home_town',(90,430)):'boss_list',('boss_home_town2',(90,430)):'boss_list',('boss_list',(1180,966)):'boss_carousel',
                    ('boss_list',(1536,214)):'boss_home',('boss_carousel',(1260,786)):summon,
                    (summon,(1130,842)):lobby,(lobby,(920,984)):'boss_not_full',
                    ('boss_not_full',(816,750)):'boss_battle_off',('boss_battle_off',(1880,530)):result}

    def click(self,xy):
        if self.state in ('boss_victory','boss_defeat'):
            for key,roi,target in (('RESULT_TOWN',(700,915,1500,1080),'boss_list'),
                                   ('RESULT_REGROUP',(650,915,1250,1080),self.lobby)):
                x,y=VISION.locate(FRAMES[self.state],key,roi);h,w=VISION.templates[key].shape[:2]
                if tuple(xy)==(x+w//2,y+h//2):
                    self.regroups+=key=='RESULT_REGROUP';self.state=target;return
            raise AssertionError(xy)
        self.starts+=tuple(xy)==(920,984)
        self.state=self.moves[(self.state,tuple(xy))]


class BossRuntimeTests(unittest.TestCase):
    def run_boss(self,game,runs=1,difficulty='Normal'):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);io=Mock();io.click.side_effect=game.click
            channel=SimpleNamespace(directory=path,run_id='test',stop_path=path/'stop.json')
            runner=BossRunner(io,Mock(),VISION,channel,Mock(),runs,difficulty)
            runner.capture=lambda:FRAMES[game.state]
            clock=[0.0]
            def sleep(seconds):clock[0]+=seconds
            fake=SimpleNamespace(monotonic=lambda:clock[0],sleep=sleep,perf_counter_ns=lambda:0)
            with patch('fishing_core.dungeon_runtime.time',fake),patch('fishing_core.boss_runtime.time',fake):
                try:runner.run()
                finally:self.events=[c.args[0] for c in runner.log.emit.call_args_list]
            return runner

    def test_private_normal_victories_spend_one_xeal_each_and_return_home(self):
        game=FakeGame();runner=self.run_boss(game,runs=2)
        self.assertEqual(game.starts,2);self.assertEqual(game.state,'boss_home')
        self.assertEqual(runner.budget.payload()['completed_runs'],2)
        self.assertEqual(runner.budget.energy_reserved,2);self.assertEqual(runner.budget.gold_reserved,0)
        self.assertEqual(self.events.count('BOSS_COMPLETE'),2)
        self.assertEqual(game.regroups,1)  # la segunda run sale por REGROUP, la última por TOWN

    def test_home_button_is_found_over_a_different_town_background(self):
        for home in ('boss_home_town','boss_home_town2'):
            game=FakeGame(home=home);self.run_boss(game)
            self.assertEqual(game.starts,1)

    def test_heroic_only_runs_when_heroic_was_chosen(self):
        game=FakeGame(summon='boss_summon_heroic')
        with self.assertRaises(SafetyStop):self.run_boss(game,difficulty='Heroic')  # sala pública: Private falta
        self.assertEqual(game.starts,0)
        with self.assertRaises(ValueError):BossRunner(Mock(),Mock(),VISION,Mock(),Mock(),1,'Hard')

    def test_wrong_summon_config_or_shared_lobby_never_press_start(self):
        for game in (FakeGame(summon='boss_summon_heroic'),FakeGame(lobby='boss_lobby_public'),
                     FakeGame(lobby='boss_lobby_joined')):
            with self.subTest(state=game.moves[('boss_carousel',(1260,786))]):
                with self.assertRaises(SafetyStop):self.run_boss(game)
                self.assertEqual(game.starts,0)

    def test_defeat_closes_once_and_stops_without_another_start(self):
        game=FakeGame(result='boss_defeat')
        with self.assertRaisesRegex(SafetyStop,'Derrota'):self.run_boss(game,runs=3)
        self.assertEqual(game.starts,1);self.assertEqual(game.state,'boss_home')

    def test_no_xeals_closes_the_list_without_summoning(self):
        game=FakeGame()
        with patch.object(BossRunner,'xeals',return_value=0):runner=self.run_boss(game,runs=2)
        self.assertEqual(game.state,'boss_home');self.assertEqual(game.starts,0)
        self.assertEqual(runner.budget.energy_reserved,0)


if __name__=='__main__':unittest.main()
