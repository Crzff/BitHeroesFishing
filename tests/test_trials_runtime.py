"""Trials offline: capturas reales saneadas; el combate lo cubre observe()."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from fishing_core.control_flow import SafetyStop
from fishing_core.dungeon_vision import DungeonVision
from fishing_core.trials_runtime import TrialsRunner

with np.load(Path(__file__).parent/'fixtures/dungeons.npz',allow_pickle=False) as data:
    FRAMES={k:data[k] for k in data.files if k.startswith(('trials_','pvp_team'))}
VISION=DungeonVision()


class FakeGame:
    """El coste se simula aparte: las capturas solo muestran 5 y el menú."""
    def __init__(self):
        self.state='trials_home';self.cost=5;self.plays=[]

    def click(self,xy):
        xy=tuple(xy)
        if self.state=='trials_home' and xy==(1830,710):self.state='trials_window'
        elif self.state=='trials_window' and xy==(1370,416):self.state='trials_cost_menu'
        elif self.state=='trials_cost_menu' and xy[0]==930:self.cost=(xy[1]-316)//128+1;self.state='trials_window'
        elif self.state=='trials_window' and xy==(1280,580):self.plays.append(self.cost);self.state='pvp_team'
        elif self.state=='pvp_team' and xy==(1215,982):self.state='battle'
        elif self.state=='trials_window' and xy==(1490,236):self.state='trials_home'
        else:raise AssertionError((self.state,xy))


class TrialsRuntimeTests(unittest.TestCase):
    def run_trials(self,game,tokens,runs=5):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);io=Mock();io.click.side_effect=game.click
            channel=SimpleNamespace(directory=path,run_id='test',stop_path=path/'stop.json')
            runner=TrialsRunner(io,Mock(),VISION,channel,Mock(),runs)
            runner.capture=lambda:FRAMES['trials_window' if game.state=='battle' else game.state]
            runner.cost_shown=lambda frame:game.cost
            def observe(attempt,cycle,**kw):
                assert game.state=='battle';game.state='trials_window'
                runner.budget.finish_run(attempt,'DEFEAT' if cycle==1 else 'VICTORY',closure_confirmed=True)
            runner.observe=Mock(side_effect=observe)
            clock=[0.0]
            def sleep(seconds):clock[0]+=seconds
            fake=SimpleNamespace(monotonic=lambda:clock[0],sleep=sleep,perf_counter_ns=lambda:0)
            with patch('fishing_core.dungeon_runtime.time',fake),patch('fishing_core.trials_runtime.time',fake), \
                    patch.object(TrialsRunner,'tokens',side_effect=tokens):
                runner.run()
            return runner

    def test_spends_every_token_lowering_the_cost_and_continues_after_a_defeat(self):
        game=FakeGame();runner=self.run_trials(game,[7,2,0])
        self.assertEqual(game.plays,[5,2]);self.assertEqual(game.state,'trials_home')
        self.assertEqual(runner.budget.energy_reserved,7);self.assertEqual(runner.budget.gold_reserved,0)

    def test_other_difficulty_never_plays(self):
        game=FakeGame()
        with patch.object(VISION,'locate',side_effect=lambda f,k,r,*a:None if k=='TRIALS_DIFF_499' else DungeonVision.locate(VISION,f,k,r,*a)):
            with self.assertRaisesRegex(SafetyStop,'499'):self.run_trials(game,[7])
        self.assertEqual(game.plays,[])


if __name__=='__main__':unittest.main()
