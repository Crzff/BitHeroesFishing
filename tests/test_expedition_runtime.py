"""Expedition offline: capturas reales saneadas; el combate lo cubre observe()."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from fishing_core.dungeon_vision import DungeonVision
from fishing_core.expedition_runtime import ExpeditionRunner

with np.load(Path(__file__).parent/'fixtures/dungeons.npz',allow_pickle=False) as data:
    FRAMES={k:data[k] for k in data.files if k.startswith(('exp_','pvp_team'))}
VISION=DungeonVision()


class FakeGame:
    def __init__(self):
        self.state='exp_home';self.entries=[];self.cost=5
        self.moves={('exp_home',(1830,560)):'exp_window',('exp_map',(960,652)):'exp_portal',
                    ('exp_window',(1370,416)):'exp_cost_menu',('exp_cost_menu',(930,316)):'exp_window_cost1',
                    ('pvp_team',(1215,982)):'battle',('exp_portal',(1362,214)):'exp_map',
                    ('exp_map',(1655,135)):'exp_window',('exp_window',(1490,240)):'exp_home',
                    ('exp_window_cost1',(1490,240)):'exp_home'}

    def click(self,xy):
        xy=tuple(xy)
        if self.state in ('exp_window','exp_window_cost1') and xy==(1280,576):
            self.cost=1 if self.state.endswith('cost1') else 5;self.state='exp_map';return
        if self.state=='exp_portal' and xy==(958,966):self.entries.append(self.cost);self.state='pvp_team';return
        self.state=self.moves[(self.state,xy)]


class ExpeditionRuntimeTests(unittest.TestCase):
    def test_spends_every_badge_lowering_the_cost_and_returns_home(self):
        game=FakeGame();badges={'EXPEDITION':iter([6,1]),'PORTAL':iter([6,1,1,0])}
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);io=Mock();io.click.side_effect=game.click
            channel=SimpleNamespace(directory=path,run_id='test',stop_path=path/'stop.json')
            runner=ExpeditionRunner(io,Mock(),VISION,channel,Mock(),5)
            runner.capture=lambda:FRAMES['exp_portal' if game.state=='battle' else game.state]
            def observe(attempt,cycle,**kw):
                assert game.state=='battle';game.state='exp_portal'
                runner.budget.finish_run(attempt,'DEFEAT' if cycle==1 else 'VICTORY',closure_confirmed=True)
            runner.observe=Mock(side_effect=observe)
            clock=[0.0]
            def sleep(seconds):clock[0]+=seconds
            fake=SimpleNamespace(monotonic=lambda:clock[0],sleep=sleep,perf_counter_ns=lambda:0)
            with patch('fishing_core.dungeon_runtime.time',fake),patch('fishing_core.expedition_runtime.time',fake), \
                    patch.object(ExpeditionRunner,'badges',side_effect=lambda screen:next(badges[screen])):
                runner.run()
        # 6 badges: 5 con coste 5 (derrota: se sigue) y el último con coste 1.
        self.assertEqual(game.entries,[5,1]);self.assertEqual(game.state,'exp_home')
        self.assertEqual(runner.budget.energy_reserved,6);self.assertEqual(runner.budget.gold_reserved,0)


if __name__=='__main__':unittest.main()
