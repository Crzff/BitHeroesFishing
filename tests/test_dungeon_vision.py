import unittest
from pathlib import Path

import cv2
import numpy as np

from fishing_core.dungeon_vision import DungeonVision

FIXTURES=Path(__file__).parent/'fixtures/dungeons.npz'


class DungeonVisionTests(unittest.TestCase):
    def test_merchant_requires_title_and_decline_and_excludes_other_fixtures(self):
        frame=self.frames['merchant_offer']
        self.assertEqual(self.vision.screen(frame),'MERCHANT')
        for x,y,x1,y1 in ((740,240,1140,315),(1015,790,1225,841)):
            damaged=frame.copy();damaged[y:y1,x:x1]=0
            self.assertNotEqual(self.vision.screen(damaged),'MERCHANT')
        for name,other in self.frames.items():
            if name!='merchant_offer':self.assertNotEqual(self.vision.screen(other),'MERCHANT',name)

    @classmethod
    def setUpClass(cls):
        cls.vision=DungeonVision()
        with np.load(FIXTURES,allow_pickle=False) as data:
            cls.frames={key:data[key] for key in data.files}

    def test_labelled_menu_and_live_states(self):
        for name,screen in [('home','HOME'),('map','MAP_Z5'),('difficulty','DIFFICULTY'),
                            ('team','TEAM'),('settings_gold','SETTINGS'),('auto_off','AUTO_OFF'),
                             ('auto_on','AUTO_ON'),('battle','AUTO_ON_BATTLE'),('story','STORY_ZORUL'),
                            ('result','VICTORY'),('offer','FAMILIAR_OFFER'),('loading','LOADING')]:
            self.assertEqual(self.vision.screen(self.frames[name]),screen,name)

    def test_startup_reward_windows_require_their_title_and_exact_close_without_accepting_dark_overlays(self):
        for name in ('startup_trials_personal','startup_trials_perfil_1','startup_trials_steam',
                     'startup_fishing_personal','startup_fishing_steam'):
            frame=self.frames[name];trials=name.startswith('startup_trials')
            expected='TRIALS_REWARDS' if trials else 'FISHING_REWARDS'
            self.assertEqual(self.vision.screen(frame),expected,name)
            title=(880,115,1130,179) if trials else (823,263,1105,319)
            close=(1600,100,1740,240) if trials else (1280,240,1420,370)
            for x,y,x1,y1 in (title,close):
                damaged=frame.copy();damaged[y:y1,x:x1]=0
                self.assertNotEqual(self.vision.screen(damaged),expected,name)
            self.assertNotEqual(self.vision.screen((frame.astype(np.float32)*.65).astype(np.uint8)),expected,name)

    def test_all_twenty_zone_titles_require_the_active_map_not_a_dark_overlay(self):
        for zone in range(1,21):
            frame=self.frames[f'zones_map_{zone}']
            self.assertEqual(self.vision.map_zone(frame),zone)
            self.assertEqual(self.vision.screen(frame),f'MAP_Z{zone}')
            self.assertIsNone(self.vision.map_zone(frame//2))
            missing=frame.copy();missing[100:205,315:565]=0
            self.assertIsNone(self.vision.map_zone(missing))
        for page in ('top','middle-b','middle-a','bottom'):
            frame=self.frames[f'zones_list_{page}']
            self.assertEqual(self.vision.screen(frame),'ZONES')
            self.assertIsNone(self.vision.map_zone(frame))

    def test_zone_choice_follows_the_visible_name_even_when_the_list_is_repositioned(self):
        for page,start in [('top',1),('middle-b',6),('middle-a',11),('bottom',16)]:
            frame=self.frames[f'zones_list_{page}']
            for zone in range(1,21):
                xy=self.vision.zone_choice(frame,zone)
                self.assertEqual(xy is not None,start<=zone<start+5,(page,zone))
                if xy:
                    self.assertTrue(670<=xy[0]<=1200 and 280<=xy[1]<=900)
                    damaged=frame.copy();x,y=xy;damaged[y-20:y+20,x-40:x+40]=0
                    self.assertIsNone(self.vision.zone_choice(damaged,zone))
            self.assertIsNone(self.vision.zone_choice(frame//2,start))
        before=self.vision.zone_choice(self.frames['zones_list_middle-b'],7)
        after=self.vision.zone_choice(self.frames['zones_reopened'],7)
        self.assertIsNotNone(after);self.assertNotEqual(before,after)
        self.assertIsNone(self.vision.zone_choice(self.frames['zones_map_5'],5))

    def test_dark_overlay_and_unknown_frame_never_authorize_input(self):
        for frame in (np.zeros((1080,1920,3),np.uint8),self.frames['home']//2,
                      self.frames['auto_on']//2):
            self.assertEqual(self.vision.screen(frame),'UNKNOWN')

    def test_home_icons_do_not_depend_on_the_town_background(self):
        frame=self.frames['home_town_moved']
        self.assertEqual(self.vision.screen(frame),'HOME')
        for key,roi in [('HOME_QUEST',(15,15,165,190)),('HOME_SETTINGS',(1760,910,1920,1080))]:
            self.assertIsNotNone(self.vision.locate(frame,key,roi))
            self.assertIsNone(self.vision.locate(frame//2,key,roi))
            x,y,x1,y1=roi;missing=frame.copy();missing[y:y1,x:x1]=0
            self.assertEqual(self.vision.screen(missing),'UNKNOWN')
        self.assertEqual(self.vision.screen(frame//2),'UNKNOWN')

    def test_personal_home_is_recognised_but_dark_missing_or_damaged_icons_are_not(self):
        frame=self.frames['home_personal']
        self.assertEqual(self.vision.screen(frame),'HOME')
        self.assertEqual(self.vision.locate(frame,'HOME_QUEST',(15,15,165,190)),(22,24))
        self.assertEqual(self.vision.locate(frame,'HOME_SETTINGS',(1760,910,1920,1080)),(1780,932))
        self.assertEqual(self.vision.screen(frame//2),'UNKNOWN')
        for box in ((15,15,165,190),(1760,910,1920,1080),(65,45,115,95)):
            damaged=frame.copy();x,y,x1,y1=box;damaged[y:y1,x:x1]=0
            self.assertEqual(self.vision.screen(damaged),'UNKNOWN',box)
        gray=cv2.cvtColor(cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY),cv2.COLOR_GRAY2BGR)
        self.assertEqual(self.vision.screen(gray),'UNKNOWN')

    def test_map_and_battle_auto_use_context_not_hover_brightness(self):
        darker=self.frames['auto_on'].copy()
        darker[435:595,1848:1910]=self.vision.templates['AUTO_ON_BATTLE']
        self.assertEqual(self.vision.screen(darker),'AUTO_ON')
        self.assertEqual(self.vision.screen(self.frames['battle']),'AUTO_ON_BATTLE')
        battle_off=self.frames['battle'].copy()
        battle_off[428:588,1848:1914]=self.vision.templates['AUTO_OFF']
        self.assertEqual(self.vision.screen(battle_off),'AUTO_OFF_BATTLE')

    def test_heroic_hover_and_idle_are_known_but_gray_dark_and_damaged_are_not(self):
        roi=(1200,450,1530,550)
        for name in ('tealk_difficulty','tealk_difficulty_idle'):
            frame=self.frames[name]
            self.assertEqual(self.vision.screen(frame),'DIFFICULTY')
            self.assertEqual(self.vision.cost(frame,'Heroic'),30)
            self.assertIsNotNone(self.vision.locate(frame,'HEROIC',roi),name)
            self.assertIsNone(self.vision.locate(frame//2,'HEROIC',roi))
            gray=frame.copy()
            gray[459:536,1220:1510]=cv2.cvtColor(cv2.cvtColor(gray[459:536,1220:1510],cv2.COLOR_BGR2GRAY),cv2.COLOR_GRAY2BGR)
            self.assertIsNone(self.vision.locate(gray,'HEROIC',roi))
            damaged=frame.copy();damaged[475:520,1275:1465]=0
            self.assertIsNone(self.vision.locate(damaged,'HEROIC',roi))

    def test_numbers_have_no_singleton_or_clock_fallback(self):
        self.assertEqual(self.vision.energy(self.frames['energy']), (342,368))
        self.assertEqual(self.vision.energy(self.frames['team']), (343,368))
        self.assertIsNone(self.vision.energy(self.frames['timer']))
        self.assertEqual(self.vision.cost(self.frames['difficulty'],'Normal'),10)
        self.assertEqual(self.vision.cost(self.frames['difficulty'],'Hard'),20)
        self.assertEqual(self.vision.cost(self.frames['difficulty'],'Heroic'),30)
        self.assertIsNone(self.vision.number(np.zeros((45,80,3),np.uint8)))
        damaged=self.frames['difficulty'].copy();damaged[340:415,625:715]=0
        self.assertIsNone(self.vision.cost(damaged,'Normal'))

    def test_energy_reads_a_zero_in_the_balance_but_never_the_alternating_clock(self):
        # 107/369 real: el 0 de esta fuente puntuaba como 8 (2 huecos) y se rechazaba.
        self.assertEqual(self.vision.screen(self.frames['energy_team_zero']),'TEAM')
        self.assertEqual(self.vision.energy(self.frames['energy_team_zero']),(107,369))
        self.assertIsNone(self.vision.energy(self.frames['energy_team_timer_2']))
        self.assertEqual(self.vision.energy(self.frames['energy_team_large']),(317,368))
        # 61/369: una variante suelta de 8 hacía puntuar los 6 como 8; juego completo 0-9.
        self.assertEqual(self.vision.energy(self.frames['energy_team_61']),(61,369))
        for clock in ('energy_team_clock_153','energy_team_clock_152','energy_team_clock_145','energy_team_clock_144'):
            self.assertIsNone(self.vision.energy(self.frames[clock]),clock)

    def test_recharge_clock_is_told_apart_from_a_balance(self):
        for clock in ('timer','energy_team_timer','energy_team_clock_153','energy_team_clock_144'):
            self.assertTrue(self.vision.energy_clock(self.frames[clock]),clock)
        for other in ('energy_team_zero','energy_team_61','team','home','battle'):
            self.assertFalse(self.vision.energy_clock(self.frames[other]),other)

    def test_native_spending_flags_use_the_parent_checkbox_not_rarity(self):
        self.assertIs(self.vision.setting(self.frames['settings_gold'],'gold'),False)
        self.assertIs(self.vision.setting(self.frames['settings_gems'],'gems'),False)
        self.assertIs(self.vision.setting(self.frames['settings_duplicates'],'duplicates'),True)
        self.assertEqual(self.vision.setting_box(self.frames['settings_duplicates'],'duplicates'),(510,629))
        checked=self.frames['settings_gold'].copy()
        checked[653:717,478:542]=self.vision.templates['CHECKED']
        self.assertIs(self.vision.setting(checked,'gold'),True)
        self.assertIsNone(self.vision.setting(self.frames['home'],'gold'))

    def test_energy_accepts_the_observed_larger_slash_but_not_clock_or_missing_separators(self):
        frame=self.frames['energy_team_large']
        self.assertEqual(self.vision.screen(frame),'TEAM')
        self.assertEqual(self.vision.energy(frame),(317,368))
        self.assertIsNone(self.vision.energy(self.frames['energy_team_timer']))
        self.assertIsNone(self.vision.energy(frame//2))
        for box in [(1106,30,1129,52),(1149,30,1194,52),(880,10,1260,78)]:
            missing=frame.copy();x,y,x1,y1=box;missing[y:y1,x:x1]=0
            self.assertIsNone(self.vision.energy(missing),box)

    def test_tealk_menu_and_hovered_empty_parent_are_conservatively_read(self):
        self.assertEqual(self.vision.screen(self.frames['tealk_home']),'HOME')
        self.assertEqual(self.vision.screen(self.frames['tealk_home']//2),'UNKNOWN')
        self.assertEqual(self.vision.screen(self.frames['tealk_difficulty']),'DIFFICULTY')
        self.assertTrue(self.vision.dungeon_title(self.frames['tealk_difficulty'],'Z5D3'))
        self.assertFalse(self.vision.dungeon_title(self.frames['tealk_difficulty'],'Z5D2'))  # otra dungeon: no se entra
        self.assertEqual(self.vision.cost(self.frames['tealk_difficulty'],'Heroic'),30)
        self.assertEqual(self.vision.screen(self.frames['tealk_team']),'TEAM')
        self.assertIs(self.vision.setting(self.frames['tealk_gold'],'gold'),False)
        self.assertIs(self.vision.setting(self.frames['tealk_gems'],'gems'),False)
        self.assertIs(self.vision.setting(self.frames['tealk_duplicates_on'],'duplicates'),True)
        self.assertIs(self.vision.setting(self.frames['tealk_duplicates_off'],'duplicates'),False)
        self.assertIsNone(self.vision.setting(self.frames['tealk_duplicates_off']//2,'duplicates'))

    def test_familiar_name_is_exact_and_a_decline_confirm_is_not_a_spending_confirm(self):
        for key,name in [('offer_mummih','Mummih'),('offer_brute','Brute'),('offer_sitra','Sitra')]:
            frame=self.frames[key]
            self.assertEqual(self.vision.screen(frame),'FAMILIAR_OFFER')
            self.assertEqual(self.vision.familiar_name(frame),name)
            damaged=frame.copy();damaged[150:160,530:545]=0
            self.assertIsNone(self.vision.familiar_name(damaged))
        self.assertIsNone(self.vision.familiar_name(self.frames['offer']))
        self.assertEqual(self.vision.screen(self.frames['decline_confirm']),'DECLINE_CONFIRM')
        changed=self.frames['decline_confirm'].copy();changed[465:610,700:1220]=0
        self.assertEqual(self.vision.screen(changed),'UNKNOWN')
        self.assertEqual(self.vision.screen(self.frames['tealk_battle_victory']),'BATTLE_VICTORY')


    def test_special_dungeon_window_is_recognised_with_its_fixed_cost(self):
        frame=self.frames['special_entry']
        self.assertEqual(self.vision.screen(frame),'DUNGEON_SPECIAL')
        self.assertTrue(self.vision.dungeon_title(frame,'Z1D4'))
        self.assertEqual(self.vision.cost(frame,'Special'),20);self.assertIsNone(self.vision.cost(frame,'Normal'))


    def test_any_familiar_name_is_read_letter_by_letter_and_matched_only_against_its_route(self):
        vision=DungeonVision();vision.templates={k:v for k,v in vision.templates.items() if not k.startswith('NAME_')}
        z5d3=['Mummih','Brute','Sitra','Tealk']
        for key,name in (('offer_mummih','Mummih'),('offer_brute','Brute'),('offer_sitra','Sitra'),('offer_tealk','Tealk')):
            self.assertEqual(vision.familiar_name(self.frames[key],z5d3),name)
        self.assertEqual(vision.familiar_name(self.frames['offer'],["Melv'guin",'Melvins']),"Melv'guin")
        self.assertIsNone(vision.familiar_name(self.frames['offer'],z5d3))  # fuera de la ruta: nunca otro nombre
        self.assertIsNone(vision.familiar_name(self.frames['offer_tealk']))  # sin candidatos no se adivina


    def test_any_story_dialog_is_recognised_by_its_arrow(self):
        self.assertEqual(self.vision.screen(self.frames['story_agnar']),'STORY')  # Agnar, World Boss
        self.assertEqual(self.vision.screen(self.frames['story_raid']),'STORY')  # Kakunapac, en combate de raid
        self.assertEqual(self.vision.screen(self.frames['story_hero']),'STORY')  # el héroe tapa la flecha


    def test_an_offer_whose_art_covers_persuade_is_still_an_offer_with_its_cost(self):
        frame=self.frames['offer_columbus_rod']  # la caña de Columbus tapa PERSUADE y el último 0
        self.assertEqual(self.vision.screen(frame),'FAMILIAR_OFFER');self.assertEqual(self.vision.offer_cost(frame),8000)


    def test_the_disconnected_from_a_dungeon_notice_is_recognised(self):
        self.assertEqual(self.vision.screen(self.frames['resume_dungeon']),'RESUME_DUNGEON')


    def test_a_capture_whose_art_covers_the_title_is_still_a_capture(self):
        self.assertEqual(self.vision.screen(self.frames['capture_callumoth']),'CAPTURE_SUCCESS')  # alas sobre el título


if __name__=='__main__':unittest.main()
