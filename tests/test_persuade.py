"""Persuade con oro sobre objetivos: capturas reales saneadas, nunca BRIBE (gemas)."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from fishing_core.control_flow import SafetyStop
from fishing_core.dungeon_runtime import DungeonRunner, validate_supported
from fishing_core.dungeon_vision import DungeonVision

with np.load(Path(__file__).parent/'fixtures/dungeons.npz',allow_pickle=False) as data:
    FRAMES={k:data[k] for k in ('offer_tealk_cost','persuade_confirm','capture_success','battle','decline_confirm','offer_sitra')}
VISION=DungeonVision()
BRIBE=(1390,704)


class FakeGame:
    def __init__(self,result='capture_success',confirm='persuade_confirm'):
        self.state='offer_tealk_cost';self.result=result;self.confirm=confirm;self.clicks=[]

    def click(self,xy):
        xy=tuple(xy);self.clicks.append(xy)
        assert xy!=BRIBE,'nunca BRIBE'
        moves={('offer_tealk_cost',(528,704)):self.confirm,('persuade_confirm',(814,750)):self.result,
               ('capture_success',(958,962)):'battle',('offer_tealk_cost',(755,955)):'decline_confirm',
               ('decline_confirm',(818,752)):'battle'}
        self.state=moves[(self.state,xy)]


class PersuadeTests(unittest.TestCase):
    def run_offer(self,game,max_gold):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);path=Path(tmp.name)
        plan=validate_supported({'dungeon_id':'Z5D3','difficulty':'Heroic','runs':1,'energy_limit':30,
                                 'targets':['Tealk'],'max_gold':max_gold})
        io=Mock();io.click.side_effect=game.click
        runner=DungeonRunner(io,Mock(),VISION,SimpleNamespace(directory=path,run_id='t',stop_path=path/'stop.json'),Mock(),plan)
        runner.capture=lambda:FRAMES[game.state]
        runner.budget.reserve_entry('t:1',resource='ENERGY',balance=100,cost=30)
        clock=[0.0]
        def sleep(s):clock[0]+=s
        fake=SimpleNamespace(monotonic=lambda:clock[0],sleep=sleep,perf_counter_ns=lambda:0)
        with patch('fishing_core.dungeon_runtime.time',fake):
            runner.persuade(FRAMES['offer_tealk_cost'],'t:1','1-1','Tealk')
        return runner,path

    def test_capture_spends_the_read_gold_once_and_closes_the_window(self):
        game=FakeGame();runner,path=self.run_offer(game,10_000)
        self.assertEqual(game.clicks,[(528,704),(814,750),(958,962)]);self.assertEqual(game.state,'battle')
        self.assertEqual(runner.budget.gold_reserved,4000);self.assertIsNone(runner.budget.pending_gold)
        intent=json.loads((path/'persuade-1-1.intent.json').read_text())
        self.assertEqual((intent['captured'],intent['effect_confirmed'],intent['currency']),(True,True,'GOLD'))

    def test_failed_persuade_returns_to_battle_and_is_recorded(self):
        game=FakeGame(result='battle');runner,path=self.run_offer(game,10_000)
        self.assertEqual(game.clicks,[(528,704),(814,750)])
        self.assertFalse(json.loads((path/'persuade-1-1.intent.json').read_text())['captured'])

    def test_failed_persuade_followed_by_another_offer_counts_as_not_joined(self):
        game=FakeGame(result='offer_sitra');runner,path=self.run_offer(game,10_000)
        self.assertEqual(game.clicks,[(528,704),(814,750)]);self.assertIsNone(runner.budget.pending_gold)
        self.assertFalse(json.loads((path/'persuade-1-1.intent.json').read_text())['captured'])

    def test_the_same_target_offer_after_yes_is_ambiguous_and_stops(self):
        game=FakeGame(result='offer_tealk_cost')
        with self.assertRaises(SafetyStop):self.run_offer(game,10_000)
        self.assertEqual(game.clicks,[(528,704),(814,750)])

    def test_without_gold_quota_the_target_is_declined_not_paid(self):
        game=FakeGame();runner,path=self.run_offer(game,0)
        self.assertNotIn((528,704),game.clicks);self.assertEqual(runner.budget.gold_reserved,0)
        self.assertEqual(game.clicks,[(755,955),(818,752)])

    def test_a_confirm_that_is_not_the_gold_dialog_never_gets_yes(self):
        game=FakeGame(confirm='decline_confirm')
        with self.assertRaises(SafetyStop):self.run_offer(game,10_000)
        self.assertEqual(game.clicks,[(528,704)])

    def test_gold_quota_must_be_a_bounded_integer(self):
        for bad in (-1,'100',10_000_001,1.5):
            with self.assertRaises(ValueError):
                validate_supported({'dungeon_id':'Z5D3','difficulty':'Heroic','runs':1,'energy_limit':30,'max_gold':bad})


if __name__=='__main__':unittest.main()
