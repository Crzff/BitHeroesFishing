"""Raid offline: entrada con capturas reales saneadas; el combate lo cubre observe()."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from fishing_core.control_flow import SafetyStop
from fishing_core.dungeon_vision import DungeonVision
from fishing_core.raid_runtime import RaidRunner

with np.load(Path(__file__).parent/'fixtures/dungeons.npz',allow_pickle=False) as data:
    FRAMES={k:data[k] for k in data.files if k.startswith('raid_')}
VISION=DungeonVision()


class FakeGame:
    def __init__(self):
        self.state='raid_home_sand';self.summons=0
        self.moves={('raid_home_sand',(90,580)):'raid_window',('raid_window',(1260,786)):'raid_difficulty',
                    ('raid_difficulty',(1370,482)):'raid_team',('raid_team',(1215,982)):'battle',
                    ('raid_window',(1468,236)):'raid_home_sand'}

    def click(self,xy):
        self.summons+=self.state=='raid_window' and tuple(xy)==(1260,786)
        self.state=self.moves[(self.state,tuple(xy))]


class RaidRuntimeTests(unittest.TestCase):
    def run_raid(self,game,shards,runs=5):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);io=Mock();io.click.side_effect=game.click
            channel=SimpleNamespace(directory=path,run_id='test',stop_path=path/'stop.json')
            runner=RaidRunner(io,Mock(),VISION,channel,Mock(),runs)
            runner.capture=lambda:FRAMES['raid_window' if game.state=='battle' else game.state]
            def observe(attempt,cycle,**kw):
                assert game.state=='battle';game.state='raid_window'
                runner.budget.finish_run(attempt,'VICTORY',closure_confirmed=True)
            runner.observe=Mock(side_effect=observe)
            clock=[0.0]
            def sleep(seconds):clock[0]+=seconds
            fake=SimpleNamespace(monotonic=lambda:clock[0],sleep=sleep,perf_counter_ns=lambda:0)
            with patch('fishing_core.dungeon_runtime.time',fake),patch('fishing_core.raid_runtime.time',fake), \
                    patch.object(RaidRunner,'shards',side_effect=shards):
                runner.run()
            return runner

    def test_spends_every_shard_in_storm_heroic_and_closes_the_window(self):
        game=FakeGame();runner=self.run_raid(game,[2,1,0])
        self.assertEqual(game.summons,2);self.assertEqual(game.state,'raid_home_sand')
        self.assertEqual(runner.budget.energy_reserved,2);self.assertEqual(runner.budget.gold_reserved,0)

    def test_another_raid_on_screen_is_never_summoned(self):
        game=FakeGame()
        with patch.object(VISION,'locate',side_effect=lambda f,k,r,*a:None if k=='RAID_STORM' else DungeonVision.locate(VISION,f,k,r,*a)):
            with self.assertRaisesRegex(SafetyStop,'Storm'):self.run_raid(game,[3])
        self.assertEqual(game.summons,0)


if __name__=='__main__':unittest.main()
