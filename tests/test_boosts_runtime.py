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
            if xy==(1102,748):self.state='inventory_consumables_bottom';return
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
        self.assertIn((1102,748),game.clicks)
        self.assertNotIn((814,748),game.clicks);self.assertEqual(game.used,[])

    @patch('fishing_core.boosts_runtime.time.sleep')
    def test_wrong_confirmation_without_no_has_no_dialog_click(self,sleep):
        runner,game=self.runner(wrong=True)
        locate=runner.locate
        with patch.object(runner,'locate',side_effect=lambda frame,key,roi:None if key=='no' else locate(frame,key,roi)):
            with self.assertRaises(SafetyStop):runner.run()
        self.assertNotIn((1102,748),game.clicks);self.assertNotIn((814,748),game.clicks)

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


class ShopGame(Game):
    def __init__(self,frames,**kwargs):
        super().__init__(frames,missing=('item_find',),**kwargs)
        self.bought=[];self.bad=None;self.after_yes='shop_boosts_top'

    def frame(self):
        frame=super().frame()
        if self.state=='shop_boosts_top' and self.bad=='diamond':
            frame[480:548,570:636]=self.frames['shop_boosts_top'][480:548,1188:1254]
        if self.state=='shop_purchase_confirm':
            if self.bad=='currency':frame[562:604,1028:1180]=0
            if self.bad=='name':
                frame[473:558,722:1195]=self.frames['consume_confirm_gold'][473:558,722:1195]
            if self.bad=='price':frame[562:604,850:1003]=0
            if self.bad=='yes':frame[695:800,690:945]=0
        return frame

    def click(self,xy):
        if xy==(1748,100):
            assert self.state=='home_no_boosts';self.clicks.append(xy);self.state='shop_featured'
        elif self.state=='shop_featured':
            assert xy==(1116,218);self.clicks.append(xy);self.state='shop_boosts_top'
        elif self.state.startswith('shop_boosts'):
            self.clicks.append(xy)
            if xy==(1660,146):self.state='home_no_boosts'
            else:
                assert xy==self.runner.shop_article(self.frame(),'item_find')
                self.state='shop_purchase_confirm'
        elif self.state=='shop_purchase_confirm':
            self.clicks.append(xy)
            if xy==(1102,748):self.state='shop_boosts_after_no'
            else:
                assert xy==(814,748)
                assert (self.runner.channel.directory/'boost-item_find.intent.json').exists()
                import json
                quota=json.loads(self.runner.quota_path().read_text())['purchases']
                assert len(quota)==1 and quota[0]['confirmed'] is False and quota[0]['cost']==10000
                self.bought.append('item_find');self.missing=();self.state=self.after_yes
        else:
            super().click(xy)
            if xy==(1652,112) and not self.bought and not self.used:self.state='home_no_boosts'


class ShopRunner(SimRunner):
    def wheel(self,amount,xy):
        if self.io.state.startswith('shop_boosts'):
            self.check();assert xy==(930,600)
            self.io.state='shop_boosts_top'
        else:super().wheel(amount,xy)


class BoostsShopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with np.load('tests/fixtures/dungeons.npz') as data:
            cls.frames={n:data[n] for n in data.files if n.startswith((
                'home_no_boosts','home_four_boosts','inventory_','consume_confirm_',
                'boost_activated','shop_'))}

    def runner(self,**kwargs):
        import tempfile
        directory=tempfile.TemporaryDirectory(dir='tests');self.addCleanup(directory.cleanup)
        game=ShopGame(self.frames,**kwargs)
        runner=ShopRunner(game,None,DungeonVision(),SimpleNamespace(
            directory=Path(directory.name),stop_path=Path(directory.name)/'stop'),game)
        runner.quota_path=lambda:Path(directory.name)/'boost_purchases.json'
        config=patch('fishing_core.farm_config.load',return_value={'boosts_buy':True})
        config.start();self.addCleanup(config.stop)
        game.runner=runner
        return runner,game

    def review_missing(self,runner,game):
        # Aísla la ausencia única: consume() real verifica que Item Find no está.
        with patch.object(runner,'consume',side_effect=lambda k: False if k=='item_find' else True):
            missing=runner.run()
        self.assertEqual(missing,[BOOSTS['item_find']])
        return missing

    @patch('fishing_core.boosts_runtime.time.sleep')
    def test_real_item_find_purchase_then_consume(self,sleep):
        runner,game=self.runner();missing=self.review_missing(runner,game)
        runner.buy_missing(missing)
        self.assertEqual(game.bought,['item_find']);self.assertEqual(game.used,['item_find'])
        self.assertEqual(sum(event=='BOOST_BOUGHT' for event,_ in game.events),1)
        self.assertEqual(game.clicks.count((814,748)),2)
        self.assertEqual(runner.missing,[])
        import json
        intent=json.loads((runner.channel.directory/'boost-item_find.intent.json').read_text())
        self.assertTrue(intent['effect_confirmed']);self.assertEqual(intent['cost'],10000)
        quota=json.loads(runner.quota_path().read_text())['purchases']
        self.assertEqual(len(quota),1);self.assertTrue(quota[0]['confirmed'])

    @patch('fishing_core.boosts_runtime.time.sleep')
    def test_diamond_never_clicked(self,sleep):
        runner,game=self.runner();missing=self.review_missing(runner,game);game.bad='diamond'
        with self.assertRaises(SafetyStop):runner.buy_missing(missing)
        self.assertEqual(game.clicks[-1],(1116,218));self.assertEqual(game.bought,[])

    @patch('fishing_core.boosts_runtime.time.sleep')
    def test_bad_confirmation_no_then_stop(self,sleep):
        for bad in ('currency','name','price','yes'):
            with self.subTest(bad=bad):
                runner,game=self.runner();missing=self.review_missing(runner,game);game.bad=bad
                with self.assertRaises(SafetyStop):runner.buy_missing(missing)
                self.assertEqual(game.clicks[-1],(1102,748));self.assertEqual(game.bought,[])
                path=runner.channel.directory/'boost-item_find.intent.json'
                self.assertEqual(path.exists(),bad=='yes')

    @patch('fishing_core.boosts_runtime.time.sleep')
    def test_ambiguous_names_no_then_stop(self,sleep):
        runner,game=self.runner();missing=self.review_missing(runner,game)
        original=runner.locate
        def ambiguous(frame,key,roi):
            if game.state=='shop_purchase_confirm' and key=='purchase_name_xp':return (742,478)
            return original(frame,key,roi)
        with patch.object(runner,'locate',side_effect=ambiguous):
            with self.assertRaises(SafetyStop):runner.buy_missing(missing)
        self.assertEqual(game.clicks[-1],(1102,748));self.assertEqual(game.bought,[])
        self.assertFalse(runner.quota_path().exists())

    @patch('fishing_core.boosts_runtime.time.sleep')
    def test_active_never_opens_shop(self,sleep):
        runner,game=self.runner(active=True)
        runner.buy_missing(runner.run());self.assertEqual(game.clicks,[])

    @patch('fishing_core.boosts_runtime.time.sleep')
    def test_intent_blocks_repeat(self,sleep):
        runner,game=self.runner();missing=self.review_missing(runner,game)
        (runner.channel.directory/'boost-item_find.intent.json').write_text('{}')
        before=game.clicks.copy()
        with self.assertRaises(SafetyStop):runner.buy_missing(missing)
        self.assertEqual(game.clicks,before)

    def test_without_run_no_purchase(self):
        runner,game=self.runner()
        with self.assertRaises(SafetyStop):runner.buy_missing([BOOSTS['item_find']])
        self.assertEqual(game.clicks,[])

    def test_duplicates_and_unknown_boosts_never_open_shop(self):
        runner,game=self.runner()
        for missing in ([BOOSTS['item_find']]*5,['Major Item Find Scroll']):
            runner.missing=missing.copy()
            with self.assertRaises(SafetyStop):runner.buy_missing(missing)
        self.assertEqual(game.clicks,[])

    @patch('fishing_core.boosts_runtime.time.sleep')
    def test_confirmation_changes_after_intent_no_yes(self,sleep):
        runner,game=self.runner();missing=self.review_missing(runner,game)
        from fishing_core.protocol import atomic_json
        def record(path,data):
            atomic_json(path,data);game.bad='name'
        with patch('fishing_core.boosts_runtime.atomic_json',side_effect=record):
            with self.assertRaises(SafetyStop):runner.buy_missing(missing)
        self.assertEqual(game.clicks[-1],(1102,748));self.assertEqual(game.bought,[])
        self.assertTrue((runner.channel.directory/'boost-item_find.intent.json').exists())

    @patch('fishing_core.boosts_runtime.time.sleep')
    def test_quantity_changes_before_price_click_stops(self,sleep):
        runner,game=self.runner();missing=self.review_missing(runner,game)
        original=runner.shop_article;calls=[]
        def changed(frame,kind):
            calls.append(kind)
            if len(calls)==2:frame[960:1020,870:980]=0
            return original(frame,kind)
        with patch.object(runner,'shop_article',side_effect=changed):
            with self.assertRaises(SafetyStop):runner.buy_missing(missing)
        self.assertEqual(game.clicks[-1],(1116,218));self.assertEqual(game.bought,[])

    def test_all_minor_names_prices_and_1x(self):
        runner,game=self.runner()
        for kind,key in (('item_find','top'),('xp','top'),('gold','middle'),('speed','bottom')):
            with self.subTest(kind=kind):
                frame=self.frames['shop_boosts_'+key].copy()
                self.assertIsNotNone(runner.shop_article(frame,kind))
                frame[960:1020,870:980]=0
                with self.assertRaises(SafetyStop):runner.shop_article(frame,kind)
        self.assertTrue(runner.purchase_valid(self.frames['shop_purchase_confirm'],'item_find'))

    def test_real_confirmations_only_validate_their_own_article(self):
        runner,game=self.runner()
        for kind in BOOSTS:
            frame=self.frames['shop_purchase_confirm'+('' if kind=='item_find' else '_'+kind)]
            for expected in BOOSTS:
                with self.subTest(kind=kind,expected=expected):
                    self.assertEqual(runner.purchase_valid(frame,expected),kind==expected)
            blank=frame.copy();blank[450:558,630:1290]=0
            self.assertFalse(runner.purchase_valid(blank,kind))
            no_price=frame.copy()
            if kind=='gold':no_price[518:562,1020:1230]=0
            else:no_price[562:609,690:1005 if kind in ('item_find','xp') else 947]=0
            self.assertFalse(runner.purchase_valid(no_price,kind))
        frame=self.frames['shop_purchase_confirm'].copy()
        ref=runner.vision.templates['BOOST_PURCHASE_NAME_SPEED']
        h,w=ref.shape[:2];frame[605:605+h,690:690+w]=ref
        self.assertFalse(runner.purchase_valid(frame,'item_find'))
        original=runner.locate
        with patch.object(runner,'locate',side_effect=lambda f,k,r: (740,478) if k=='purchase_name_xp' else original(f,k,r)):
            self.assertFalse(runner.purchase_valid(self.frames['shop_purchase_confirm'],'item_find'))

    @patch('fishing_core.boosts_runtime.time.sleep')
    def test_buy_disabled_never_opens_shop(self,sleep):
        runner,game=self.runner();missing=self.review_missing(runner,game)
        before=game.clicks.copy()
        with patch('fishing_core.farm_config.load',return_value={'boosts_buy':False}):runner.buy_missing(missing)
        self.assertEqual(game.clicks,before);self.assertEqual(game.bought,[])

    @patch('fishing_core.boosts_runtime.time.sleep')
    def test_exhausted_persistent_quota_never_opens_shop(self,sleep):
        from fishing_core.protocol import atomic_json
        import time
        runner,game=self.runner();missing=self.review_missing(runner,game)
        for kinds in (['gold']*4,['item_find']*3):
            with self.subTest(kinds=kinds):
                atomic_json(runner.quota_path(),{'purchases':[{'boost':k,'cost':10000 if k=='item_find' else 5000,
                    'time':time.time(),'confirmed':False} for k in kinds]})
                before=game.clicks.copy();runner.buy_missing(missing)
                self.assertEqual(game.clicks,before);self.assertEqual(game.bought,[])
                self.assertEqual(game.events[-1][0],'BOOST_QUOTA')

    def test_quota_expiry_and_invalid_data(self):
        from fishing_core.protocol import atomic_json
        import time
        runner,game=self.runner()
        with patch('fishing_core.boosts_runtime.time.time',return_value=100000):
            atomic_json(runner.quota_path(),{'purchases':[{'boost':'xp','cost':10000,'time':13600,'confirmed':False}]})
            self.assertEqual(runner.quota()[1],[])
        atomic_json(runner.quota_path(),{'purchases':[{'boost':'xp','cost':1,'time':time.time(),'confirmed':True}]})
        with self.assertRaises(SafetyStop):runner.quota()

    def test_quota_is_shared_between_session_directories(self):
        from fishing_core.protocol import atomic_json
        import time
        first,game=self.runner();second,other=self.runner()
        second.quota_path=first.quota_path
        atomic_json(first.quota_path(),{'purchases':[{'boost':'xp','cost':10000,'time':time.time(),'confirmed':False}]*3})
        self.assertFalse(second.quota_available(second.quota()[1],['item_find']))
        self.assertEqual(game.bought,[]);self.assertEqual(other.bought,[])

    @patch('fishing_core.boosts_runtime.time.sleep')
    def test_unknown_after_yes_no_further_clicks(self,sleep):
        runner,game=self.runner();missing=self.review_missing(runner,game)
        game.after_yes='inventory_filter'
        with self.assertRaises(SafetyStop):runner.buy_missing(missing)
        self.assertEqual(game.clicks[-1],(814,748));self.assertEqual(game.bought,['item_find'])
        self.assertFalse(any(event=='BOOST_BOUGHT' for event,_ in game.events))
        import json
        self.assertFalse(json.loads(runner.quota_path().read_text())['purchases'][0]['confirmed'])


class BoostShopIconTests(unittest.TestCase):
    def test_animated_shop_icon_is_found_on_every_home_and_nowhere_else(self):
        from unittest.mock import Mock
        from fishing_core.dungeon_vision import DungeonVision
        from fishing_core.boosts_runtime import BoostsRunner
        with np.load(Path(__file__).parent/'fixtures/dungeons.npz',allow_pickle=False) as data:frames={k:data[k] for k in data.files}
        runner=BoostsRunner(Mock(),Mock(),DungeonVision(),Mock(),Mock())
        for name in ('home_no_boosts','home_four_boosts','home_gvg_gauntlet','home_gauntlet_steam'):
            self.assertEqual(runner.locate(frames[name],'shop',(1700,60,1880,180)),(1715,78),name)
        for name in ('inventory_filter','gauntlet_window','shop_featured'):
            self.assertIsNone(runner.locate(frames[name],'shop',(1700,60,1880,180)),name)


class BoostDetectionTests(unittest.TestCase):
    def test_active_boosts_are_found_by_their_frame_whatever_the_bar_colour(self):
        from unittest.mock import Mock
        with np.load(Path(__file__).parent/'fixtures/dungeons.npz',allow_pickle=False) as data:frames={k:data[k] for k in data.files}
        runner=BoostsRunner(Mock(),Mock(),DungeonVision(),Mock(),Mock())
        for name,active in (('home_four_boosts',True),('home_boosts_yellow',True),('home_no_boosts',False),
                            ('home_gvg_gauntlet',False),('home_gauntlet_steam',False)):
            self.assertEqual(runner.boosts_active(frames[name]),active,name)
        roi=(980,535,1405,625)
        self.assertIsNotNone(runner.locate(frames['inventory_filter_selected'],'consumables_selected',roi))
        self.assertIsNotNone(runner.locate(frames['inventory_filter'],'consumables',roi))


class BoostProfileFilterTests(unittest.TestCase):
    def test_filter_button_is_found_on_kortzz_profile(self):
        from unittest.mock import Mock
        with np.load(Path(__file__).parent/'fixtures/dungeons.npz',allow_pickle=False) as data:frame=data['profile_kortzz_filtered']
        runner=BoostsRunner(Mock(),Mock(),DungeonVision(),Mock(),Mock())
        self.assertIsNotNone(runner.locate(frame,'filter',(1070,180,1605,295)))


class BoostLetterButtonTests(unittest.TestCase):
    def test_home_anchor_does_not_depend_on_the_daily_letter(self):
        from unittest.mock import Mock
        with np.load(Path(__file__).parent/'fixtures/dungeons.npz',allow_pickle=False) as data:frames={k:data[k] for k in data.files}
        runner=BoostsRunner(Mock(),Mock(),DungeonVision(),Mock(),Mock())
        for name in ('home_no_boosts','home_letter_t','home_four_boosts'):  # letras F y T
            self.assertIsNotNone(runner.locate(frames[name],'slot',(320,955,430,1080)),name)
        self.assertFalse(runner.boosts_active(frames['home_letter_t']))


class BoostCollectAndSteamTests(unittest.TestCase):
    def test_items_window_after_purchase_and_steam_active_boosts(self):
        from unittest.mock import Mock
        with np.load(Path(__file__).parent/'fixtures/dungeons.npz',allow_pickle=False) as data:frames={k:data[k] for k in data.files}
        runner=BoostsRunner(Mock(),Mock(),DungeonVision(),Mock(),Mock())
        self.assertTrue(runner.items_ready(frames['shop_items_collect']))
        self.assertEqual([k for k in frames if runner.items_ready(frames[k])],['shop_items_collect'])
        self.assertTrue(runner.boosts_active(frames['home_steam_four_boosts']))
        for name in ('home_no_boosts','home_letter_t','home_gvg_gauntlet','home_gauntlet_steam'):
            self.assertFalse(runner.boosts_active(frames[name]),name)
