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
        self.state='raid_home_sand';self.summons=0;self.picked=[]
        self.moves={('raid_home_sand',(90,580)):'raid_astaroth',('raid_astaroth',(440,624)):'raid_window',
                    ('raid_window',(1260,786)):'raid_difficulty',
                    ('raid_difficulty',(1370,482)):'raid_team',('raid_difficulty',(958,482)):'raid_team',('raid_team',(1215,982)):'battle',
                    ('raid_window',(1468,236)):'raid_home_sand'}

    def click(self,xy):
        self.summons+=self.state=='raid_window' and tuple(xy)==(1260,786)
        if self.state=='raid_difficulty':self.picked.append(tuple(xy))
        self.state=self.moves[(self.state,tuple(xy))]


class RaidRuntimeTests(unittest.TestCase):
    def test_raid_persuades_all_with_unlimited_gold_ignoring_legacy_limits(self):
        from fishing_core.farm_budget import UNLIMITED_GOLD
        for old_limit in (0,250_000,UNLIMITED_GOLD,'antiguo'):
            runner=RaidRunner(Mock(),Mock(),Mock(),Mock(),Mock(),1,max_gold=old_limit)
            self.assertTrue(runner.persuade_all)
            self.assertEqual(runner.budget.max_gold,UNLIMITED_GOLD)
            runner.capture=Mock(return_value='offer');runner.offer_name=Mock(return_value='Bob');runner.persuade=Mock()
            runner.channel.run_id='test'
            runner.finish_leftover_run('FAMILIAR_OFFER')
            runner.persuade.assert_called_once_with('offer','test:resume','resume-1','Bob')

    def run_raid(self,game,shards,runs=5,difficulty='Heroic',reruns=0):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);io=Mock();io.click.side_effect=game.click
            channel=SimpleNamespace(directory=path,run_id='test',stop_path=path/'stop.json')
            runner=RaidRunner(io,Mock(),VISION,channel,Mock(),runs,'STORM',difficulty)
            runner.capture=lambda:FRAMES['raid_window' if game.state=='battle' else game.state]
            left=[reruns]
            def observe(attempt,cycle,**kw):
                assert game.state=='battle'
                runner.budget.finish_run(attempt,'VICTORY',closure_confirmed=True)
                if kw.get('rerun') and left[0]:  # RERUN: la siguiente raid empieza sin SUMMON ni TEAM
                    left[0]-=1;following=f'test:{cycle+1}'
                    runner.budget.reserve_entry(following,resource=runner.entry_resource,balance=5,cost=1);return following
                game.state='raid_window'
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

    def test_chosen_raid_is_found_by_name_and_difficulty_button_is_used(self):
        game=FakeGame();self.run_raid(game,[1,0],difficulty='Hard')
        self.assertEqual(game.picked,[(958,482)]);self.assertEqual(game.summons,1)

    def test_another_raid_on_screen_is_never_summoned(self):
        game=FakeGame()
        with patch.object(VISION,'locate',side_effect=lambda f,k,r,*a,**kw:None if k=='RAID_NAME_STORM' else DungeonVision.locate(VISION,f,k,r,*a,**kw)):
            game.moves[('raid_window',(440,624))]='raid_astaroth'
            with self.assertRaisesRegex(SafetyStop,'Storm'):self.run_raid(game,[3])
        self.assertEqual(game.summons,0)


    def test_rerun_chains_raids_without_summoning_again_and_spends_shards(self):
        game=FakeGame();runner=self.run_raid(game,[3,0],reruns=2)
        self.assertEqual(game.summons,1)  # una sola entrada por SUMMON; las otras dos por RERUN
        self.assertEqual(runner.budget.energy_reserved,3);self.assertEqual(runner.budget.resource,'SHARDS')
        self.assertEqual([c.kwargs['rerun'] for c in runner.observe.call_args_list],[True,True,True])


    def test_every_game_raid_is_listed_with_its_tier(self):
        from fishing_core.raid_runtime import RAID_TIER,RAIDS
        self.assertEqual(len(RAIDS),18)
        self.assertEqual((RAID_TIER['STORM'],RAID_TIER['TIKAL_DIKI'],RAID_TIER['HENS_HIDEAWAY']),(13,14,21))

    def test_a_raid_without_name_image_is_found_by_reading_its_title(self):
        from fishing_core.raid_runtime import RAIDS
        names=list(RAIDS.values())
        self.assertEqual(VISION.raid_title(FRAMES['raid_window'],names),'Storm')


if __name__=='__main__':unittest.main()
