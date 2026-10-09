"""GvG offline con capturas guardadas y entradas exclusivamente simuladas."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch

import numpy as np

from fishing_core.control_flow import SafetyStop
from fishing_core.dungeon_vision import DungeonVision
from fishing_core.gvg_runtime import GvgRunner,HOME,PLAY,CLOSE,YES,NO

with np.load(Path(__file__).parent/'fixtures/dungeons.npz',allow_pickle=False) as data:
    FRAMES={k:data[k] for k in data.files if k.startswith(('gvg_','pvp_','home_gvg','home_gauntlet','boss_not_full'))}


class FakeGame:
    def __init__(self,balance=14,confirm='gvg_confirm',not_full=False):
        self.state='home_gvg_gauntlet';self.balance=balance;self.cost=1
        self.confirm=confirm;self.first=True;self.not_full=not_full
        self.plays=[];self.clicks=[];self.vision=None

    def frame(self):
        if self.state=='window':
            frame=FRAMES['gvg_window_14' if self.first else 'gvg_window'].copy()
            self.draw_number(frame,(900,108,1020,145),self.balance)
            self.draw_number(frame,(1210,392,1310,448),self.cost)
            return frame
        if self.state=='menu':
            frame=FRAMES['pvp_cost_menu'].copy()
            ref=self.vision.templates['COST_MENU_BADGES'];h,w=ref.shape[:2]
            frame[110:110+h,800:800+w]=ref
            return frame
        return FRAMES[self.state]

    def draw_number(self,frame,roi,value):
        x,y,r,b=roi;frame[y:b,x:r]=0;x+=15;y+=8
        for digit in str(value):
            ref=self.vision.digits.templates['DIGIT_'+digit];h,w=ref.shape
            frame[y:y+h,x:x+w]=np.repeat((ref*255)[:,:,None],3,axis=2)
            x+=w+8

    def click(self,xy):
        xy=tuple(xy);self.clicks.append(xy)
        if self.state.startswith('home_') and xy==HOME[0]:self.state='window'
        elif self.state=='window' and xy==(1370,416):self.state='menu'
        elif self.state=='menu' and xy[0]==930:
            self.cost=1+(xy[1]-316)//128;self.state='window'
        elif self.state=='window' and xy==PLAY[0]:
            self.plays.append(self.cost);self.balance-=self.cost
            self.state=self.confirm if self.first and self.confirm else 'gvg_select';self.first=False
        elif self.state=='gvg_confirm' and xy==YES[0]:self.state='gvg_select'
        elif self.state=='gvg_flee_confirm' and xy==NO[0]:self.state='gvg_select'
        elif self.state=='gvg_select':
            rows=self.vision.locate_all(self.frame(),'PVP_FIGHT',(1236,330,1544,900))
            x,y=rows[-1];h,w=self.vision.templates['PVP_FIGHT'].shape[:2]
            assert xy==(x+w//2,y+h//2),xy
            self.state='gvg_team'
        elif self.state=='gvg_team' and xy==(1215,982):self.state='boss_not_full' if self.not_full else 'gvg_defeat'
        elif self.state=='boss_not_full' and xy==(816,750):self.state='gvg_defeat'
        elif self.state=='gvg_defeat':
            x,y=self.vision.locate(self.frame(),'RESULT_TOWN',(700,915,1500,1080))
            h,w=self.vision.templates['RESULT_TOWN'].shape[:2]
            assert xy==(x+w//2,y+h//2),xy
            self.state='window'
        elif self.state=='window' and xy==CLOSE[0]:self.state='home_gvg_gauntlet'
        else:raise AssertionError((self.state,xy))


class GvgRuntimeTests(unittest.TestCase):
    def runner(self,game,path):
        io=Mock();io.click.side_effect=game.click
        channel=SimpleNamespace(directory=path,run_id='gvg-test',stop_path=path/'stop.json')
        runner=GvgRunner(io,Mock(),DungeonVision(),channel,Mock(),10)
        game.vision=runner.vision;runner.capture=game.frame
        return runner

    def clock(self):
        clock=[0.0]
        def sleep(seconds):clock[0]+=seconds
        return SimpleNamespace(monotonic=lambda:clock[0],sleep=sleep,perf_counter_ns=lambda:0)

    def execute(self,game):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            runner=self.runner(game,Path(tmp));fake=self.clock()
            with patch('fishing_core.dungeon_runtime.time',fake),patch('fishing_core.pvp_runtime.time',fake), \
                    patch('fishing_core.gvg_runtime.time',fake):runner.run()
            return runner

    def test_spends_14_badges_to_zero_and_defeats_do_not_stop(self):
        game=FakeGame();runner=self.execute(game)
        self.assertEqual(game.plays,[5,5,4]);self.assertEqual(game.balance,0)
        self.assertEqual(game.state,'home_gvg_gauntlet')
        self.assertEqual(runner.budget.resource,'BADGES');self.assertEqual(runner.budget.energy_reserved,14)
        self.assertEqual(runner.budget.payload()['completed_runs'],3)
        self.assertEqual(runner.budget.gold_reserved,0);self.assertEqual(game.clicks.count(YES[0]),1)

    def test_remaining_badge_uses_cost_one(self):
        game=FakeGame(1);self.execute(game);self.assertEqual(game.plays,[1]);self.assertEqual(game.balance,0)

    def test_zero_badges_closes_without_play(self):
        game=FakeGame(0);self.execute(game);self.assertEqual(game.plays,[])

    def test_flee_only_presses_no_and_stops(self):
        game=FakeGame(confirm='gvg_flee_confirm')
        with self.assertRaisesRegex(SafetyStop,'Huida'):self.execute(game)
        self.assertIn(NO[0],game.clicks);self.assertNotIn(YES[0],game.clicks)

    def test_incomplete_team_uses_pvp_confirmation(self):
        game=FakeGame(1,not_full=True);self.execute(game)
        self.assertIn((816,750),game.clicks);self.assertEqual(game.balance,0)

    def test_real_screens_balances_and_home_backgrounds(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            runner=self.runner(FakeGame(),Path(tmp));vision=runner.vision
            for key,screen in (('gvg_window','GVG'),('gvg_window_14','GVG'),('gvg_confirm','GVG_CONFIRM'),
                               ('gvg_flee_confirm','GVG_FLEE'),('gvg_select','PVP_SELECT'),
                               ('gvg_team','TEAM'),('gvg_defeat','WB_DEFEAT')):
                self.assertEqual(vision.screen(FRAMES[key]),screen,key)
            for key,value in (('gvg_window',15),('gvg_window_14',14)):
                self.assertEqual(vision.number(FRAMES[key][108:145,900:1020]),value,key)
                runner.capture=lambda:FRAMES[key]
                with patch('fishing_core.gvg_runtime.time.sleep'):self.assertEqual(runner.badges(),value)
                self.assertEqual(runner.cost_shown(FRAMES[key]),1)
            for key in ('home_gvg_gauntlet','home_gauntlet_steam'):
                self.assertEqual(vision.screen(FRAMES[key]),'HOME')
                self.assertIsNotNone(vision.locate(FRAMES[key],HOME[1],HOME[2]),key)

    def test_changed_guild_text_never_authorizes_yes(self):
        game=FakeGame();bad=FRAMES['gvg_confirm'].copy();bad[420:465,680:1240]=0
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            runner=self.runner(game,Path(tmp));runner.capture=lambda:bad
            fake=self.clock()
            self.assertEqual(runner.vision.screen(bad),'UNKNOWN')
            with patch('fishing_core.gvg_runtime.time',fake),self.assertRaises(SafetyStop):runner.choose_opponent()
            self.assertEqual(game.clicks,[])

    def test_confirmation_is_rechecked_immediately_before_yes(self):
        game=FakeGame()
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            runner=self.runner(game,Path(tmp))
            frames=iter([FRAMES['gvg_confirm']]*4+[FRAMES['gvg_flee_confirm']])
            runner.capture=lambda:next(frames)
            with patch('fishing_core.gvg_runtime.time.sleep'),self.assertRaises(SafetyStop):runner.choose_opponent()
            self.assertNotIn(YES[0],game.clicks)

    def test_unknown_dialog_does_not_authorize_yes(self):
        game=FakeGame()
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            runner=self.runner(game,Path(tmp));foreign=FRAMES['gvg_confirm'].copy()
            foreign[410:665,635:1280]=FRAMES['pvp_home'][410:665,635:1280]
            runner.capture=lambda:foreign
            self.assertEqual(runner.vision.screen(foreign),'UNKNOWN')
            fake=self.clock()
            with patch('fishing_core.gvg_runtime.time',fake),self.assertRaises(SafetyStop):runner.choose_opponent()
            self.assertNotIn(YES[0],game.clicks)


if __name__=='__main__':unittest.main()
