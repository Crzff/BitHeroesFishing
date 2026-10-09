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
    FRAMES={k:data[k] for k in data.files if k.startswith(('trials_','pvp_team','gauntlet_','home_gvg','boss_not_full'))}
VISION=DungeonVision()


class FakeGame:
    """El coste se simula aparte: las capturas solo muestran 5 y el menú."""
    def __init__(self):
        self.state='trials_home';self.cost=5;self.plays=[];self.not_full=False

    def click(self,xy):
        xy=tuple(xy)
        if self.state=='trials_home' and xy==(1830,710):self.state='trials_window'
        elif self.state=='trials_window' and xy==(1370,416):self.state='trials_cost_menu'
        elif self.state=='trials_cost_menu' and xy[0]==930:self.cost=(xy[1]-316)//128+1;self.state='trials_window'
        elif self.state=='trials_window' and xy==(1280,580):self.plays.append(self.cost);self.state='pvp_team'
        elif self.state=='pvp_team' and xy==(1215,982):self.state='boss_not_full' if self.not_full else 'battle'
        elif self.state=='boss_not_full' and xy==(816,750):self.state='battle'
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

    def test_gauntlet_victory_banner_closes_the_run_with_town(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);path=Path(tmp.name)
        state={'screen':'gauntlet_victory'};clicks=[]
        def click(xy):
            clicks.append(tuple(xy));assert state['screen']=='gauntlet_victory';state['screen']='gauntlet_window'
        io=Mock();io.click.side_effect=click
        runner=TrialsRunner(io,Mock(),VISION,SimpleNamespace(directory=path,run_id='t',stop_path=path/'s.json'),Mock(),1)
        runner.capture=lambda:FRAMES[state['screen']];runner.record_loot=Mock()
        runner.budget.reserve_entry('t:1',resource='TOKENS',balance=5,cost=5)
        fake=SimpleNamespace(monotonic=lambda:0.0,sleep=lambda s:None,perf_counter_ns=lambda:0)
        with patch('fishing_core.dungeon_runtime.time',fake),patch('fishing_core.trials_runtime.time',fake):
            runner.observe('t:1',1)
        self.assertEqual(state['screen'],'gauntlet_window');self.assertEqual(len(clicks),1);runner.record_loot.assert_called_once()
        self.assertEqual(runner.budget.payload()['completed_runs'],1)

    def test_incomplete_team_warning_is_accepted(self):
        game=FakeGame();game.not_full=True;self.run_trials(game,[5,0])
        self.assertEqual(game.plays,[5]);self.assertEqual(game.state,'trials_home')

    def test_level_list_where_one_wheel_step_does_not_move_is_still_crossed(self):
        # En vivo (Gauntlet, FMANI 440-751): n pasos de rueda mueven n-1 filas; 1 paso no mueve.
        for target in (499,749,441):
            runner=TrialsRunner.__new__(TrialsRunner);top=[751]
            runner.capture=lambda:None
            runner.vision=SimpleNamespace(trials_levels=lambda f:[(317+128*i,top[0]-i) for i in range(5)])
            def wheel(n):top[0]=max(444,min(751,top[0]-(abs(n)-1)*(1 if n>0 else -1)))
            runner.wheel=wheel
            with patch('fishing_core.trials_runtime.time',SimpleNamespace(sleep=lambda s:None)):
                self.assertIsNotNone(runner.scroll_to_level(target),target)

    def menu_runner(self,target):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);path=Path(tmp.name)
        state={'screen':'trials_window','page':0,'shown':499,'clicks':[]}
        io=Mock()
        def click(xy):
            state['clicks'].append(tuple(xy))
            if tuple(xy)==(1416,826):state['screen']=f"trials_menu_{state['page']}"
            elif state['screen'].startswith('trials_menu'):
                rows=VISION.trials_ranges(FRAMES[state['screen']])
                assert [high for y,low,high in rows if y==xy[1]]==[674];state['screen']='trials_levels_674'
            elif state['screen']=='trials_levels_674':
                state['shown']=[n for y,n in VISION.trials_levels(FRAMES['trials_levels_674']) if y==xy[1]][0]
                state['screen']='trials_window'
        io.click.side_effect=click
        runner=TrialsRunner(io,Mock(),VISION,SimpleNamespace(directory=path,run_id='t',stop_path=path/'s.json'),Mock(),1,target)
        runner.capture=lambda:FRAMES[state['screen']]
        runner.difficulty_shown=lambda f:state['shown']
        def wheel(steps):
            if state['screen'].startswith('trials_menu'):
                state['page']=0 if steps<0 else min(7,state['page']+1);state['screen']=f"trials_menu_{state['page']}"
        runner.wheel=wheel
        clock=[0.0]
        def sleep(s):clock[0]+=s
        fake=SimpleNamespace(monotonic=lambda:clock[0],sleep=sleep,perf_counter_ns=lambda:0)
        return runner,state,fake

    def test_difficulty_is_chosen_by_its_range_maximum_across_pages(self):
        runner,state,fake=self.menu_runner(674)
        with patch('fishing_core.dungeon_runtime.time',fake),patch('fishing_core.trials_runtime.time',fake):runner.set_difficulty()
        self.assertEqual(state['shown'],674);self.assertEqual(state['screen'],'trials_window')

    def test_current_difficulty_is_left_alone(self):
        runner,state,fake=self.menu_runner(499)
        with patch('fishing_core.dungeon_runtime.time',fake),patch('fishing_core.trials_runtime.time',fake):runner.set_difficulty()
        self.assertEqual(state['clicks'],[])

    def test_missing_difficulty_stops_without_choosing_or_playing(self):
        runner,state,fake=self.menu_runner(674)
        runner.scroll_to_level=Mock(return_value=None)
        with patch('fishing_core.dungeon_runtime.time',fake),patch('fishing_core.trials_runtime.time',fake):
            with self.assertRaisesRegex(SafetyStop,'674'):runner.set_difficulty()
        self.assertEqual(state['shown'],499)

    def test_home_gauntlet_uses_verified_icon_and_existing_story_wait(self):
        runner,_,fake=self.menu_runner(499)
        state=['home_gvg_gauntlet'];runner.capture=lambda:FRAMES[state[0]]
        runner.ensure_home=Mock(return_value='HOME');runner.set_difficulty=Mock();runner.check=Mock()
        runner.io.click.side_effect=lambda xy:state.__setitem__(0,'gauntlet_story' if state[0]=='home_gvg_gauntlet' else 'gauntlet_window')
        with patch('fishing_core.dungeon_runtime.time',fake),patch('fishing_core.trials_runtime.time',fake):runner.open()
        self.assertEqual([c.args[0] for c in runner.io.click.call_args_list],[(1828,700),(1665,646)])
        self.assertEqual(runner.event_screen(),'GAUNTLET')
        self.assertEqual(TrialsRunner.difficulty_shown(runner,FRAMES['gauntlet_window']),54)


    def test_available_maximum_below_config_is_confirmed_or_stops(self):
        for confirmed in (True,False):
            runner,state,fake=self.menu_runner(499)
            runner.capture=lambda:FRAMES['gauntlet_window'];runner.difficulty_shown=lambda f:state['shown']
            state['shown']=54;runner.click=Mock();runner.wait=Mock()
            runner.vision=Mock();runner.vision.screen.return_value='GAUNTLET'
            runner.vision.trials_ranges.return_value=[(320,1,54)]
            runner.scroll_to=lambda find,label:find(None)
            runner.scroll_to_level=Mock(return_value=320)
            runner.choose=Mock()
            def wait(predicate,*args):
                if args and args[-1]=='dificultad 54':
                    state['shown']=54 if confirmed else 53
                    if not predicate(None):raise SafetyStop('Dificultad sin confirmar')
            runner.wait.side_effect=wait
            with patch('fishing_core.trials_runtime.time',fake):
                if confirmed:runner.set_difficulty()
                else:
                    with self.assertRaises(SafetyStop):runner.set_difficulty()
            runner.scroll_to_level.assert_called_once_with(54)

    def test_a_long_range_is_crossed_by_jumping_toward_the_level(self):
        # Semana con rango 440-755: unos 300 niveles, 5 visibles, cada paso de rueda baja 2 niveles.
        from unittest.mock import patch
        top=[755];steps=[]
        runner=TrialsRunner.__new__(TrialsRunner)
        runner.vision=SimpleNamespace(trials_levels=lambda f:[(317+128*i,top[0]-i) for i in range(5) if top[0]-i>=440])
        runner.capture=lambda:None
        def wheel(n,xy=(930,600)):steps.append(n);top[0]=max(444,min(755,top[0]-2*n))
        runner.wheel=wheel
        with patch('fishing_core.trials_runtime.time.sleep'):y=runner.scroll_to_level(499)
        self.assertIsNotNone(y);self.assertIn(499,[top[0]-i for i in range(5)])
        self.assertLess(len(steps),15)  # salta, no baja de 3 en 3
        top[0]=755
        with patch('fishing_core.trials_runtime.time.sleep'):self.assertIsNone(runner.scroll_to_level(300))  # fuera del rango


    def test_the_wheel_shares_the_signature_used_by_the_loot_recap(self):
        runner=TrialsRunner.__new__(TrialsRunner);runner.io=Mock();runner.check=Mock()
        with patch('fishing_core.trials_runtime.time.sleep'),patch('fishing_core.dungeon_runtime.time.sleep'):
            runner.wheel(1,(1320,770));runner.wheel(-3)  # record_loot y los menús de Trials
        self.assertEqual([c.args for c in runner.io.wheel.call_args_list],[(1,(1320,770)),(-3,(930,600))])


if __name__=='__main__':unittest.main()
