from pathlib import Path
import unittest

import cv2
import numpy as np

from rookie_arena_vision import RookieArenaVision
from rookie_arena import RookieArenaRunner


ROOT=Path(__file__).resolve().parent


class RookieArenaVisionTests(unittest.TestCase):
    def test_idle_icon_sequence_works_without_visible_skills(self):
        frame=cv2.cvtColor(cv2.imread(str(ROOT/'tests/fixtures/rookie_arena/manual_rinak.png')),cv2.COLOR_BGR2RGB)
        frame[610:720,960:1280]=0
        for index in range(5):
            self.assertIsNone(self.vision.observe(frame,now=index*.4)['auto_on'])
        self.assertIs(self.vision.observe(frame,now=2)['auto_on'],False)
        blank=np.zeros_like(frame)
        self.vision.observe(blank,now=2.4)
        self.assertIsNone(self.vision.observe(frame,now=2.8)['auto_on'])
        self.assertIsNone(self.vision.observe(frame,now=5)['auto_on'])

    def test_rotating_icon_sequence_does_not_become_manual_at_idle_angle(self):
        frame=cv2.cvtColor(cv2.imread(str(ROOT/'tests/fixtures/rookie_arena/manual_rinak.png')),cv2.COLOR_BGR2RGB)
        frame[610:720,960:1280]=0
        original=frame[9:58,1100:1150].copy()
        yy,xx=np.ogrid[:49,:50]
        ring=((xx-24)**2+(yy-24)**2>=12**2)&((xx-24)**2+(yy-24)**2<=24**2)
        seen=[]
        for index,angle in enumerate((0,40,80,120,160,200,240,280,320,0)):
            rotated=cv2.warpAffine(original,cv2.getRotationMatrix2D((24,24),angle,1),(50,49))
            patch=original.copy()
            patch[ring]=rotated[ring]
            frame[9:58,1100:1150]=patch
            seen.append(self.vision.observe(frame,now=index*.4)['auto_on'])
        self.assertNotIn(False,seen)
        self.assertIn(True,seen)

    def test_scene_motion_does_not_count_as_auto_icon_rotation(self):
        frame=cv2.cvtColor(cv2.imread(str(ROOT/'tests/fixtures/rookie_arena/manual_rinak.png')),cv2.COLOR_BGR2RGB)
        frame[610:720,960:1280]=0
        seen=[]
        for index in range(9):
            moving=frame.copy()
            moving[150:500,50:500]=255 if index%2 else 0
            seen.append(self.vision.observe(moving,now=index*.4)['auto_on'])
        self.assertNotIn(True,seen)
        self.assertIs(seen[-1],False)

    def test_rinak_manual_frames_allow_small_slot_position_variations(self):
        original=cv2.cvtColor(cv2.imread(str(ROOT/'tests/fixtures/rookie_arena/manual_rinak.png')),cv2.COLOR_BGR2RGB)
        for scale in (.98,1.,1.02):
            frame=cv2.resize(cv2.resize(original,None,fx=scale,fy=scale),(1280,720))
            for brightness in (-20,0,20):
                obs=self.vision.observe(np.clip(frame.astype(float)+brightness,0,255).astype(np.uint8))
                self.assertIs(obs['auto_on'],False)
        # Frame recognition must not depend on Rinak's skill illustration.
        for x in (977,1077,1177):
            original[633:700,x+16:x+70]=(20,40,80)
        self.assertIs(self.vision.observe(original)['auto_on'],False)
        r=RookieArenaRunner()
        r.state='battle'; r.battle_at=0
        obs=self.vision.observe(original)
        r.step(obs,0); r.step(obs,1)
        self.assertEqual(r.step(obs,2)[0],'auto')

    def test_auto_with_dead_party_members_is_confirmed_without_another_click(self):
        original=cv2.cvtColor(cv2.imread(str(ROOT/'tests/fixtures/rookie_arena/auto_dead_hero.png')),cv2.COLOR_BGR2RGB)
        for scale in (.99,1.,1.01):
            frame=cv2.resize(cv2.resize(original,None,fx=scale,fy=scale),(1280,720))
            obs=self.vision.observe(frame)
            self.assertIs(obs['auto_on'],True)
            r=RookieArenaRunner()
            r.state='battle'; r.battle_at=0; r.auto_used=True; r.auto_at=0
            r.step(obs,26)
            r.step(obs,27)
            self.assertIsNone(r.step(obs,28)[0])
            self.assertTrue(r.auto_verified)
            self.assertIsNone(r.step(obs,40)[0])
        for x in (1004,1082):
            original[610:720,x-30:x+31]=original[610:720,1130:1191]
            self.assertIs(self.vision.observe(original)['auto_on'],True)
        # A plain red block cannot replace a dead HUD slot's label/portrait.
        original[610:720,1130:1191]=(120,0,0)
        self.assertIsNone(self.vision.observe(original)['auto_on'])

    def test_disabled_skill_is_manual_and_enables_auto_once(self):
        original=cv2.cvtColor(cv2.imread(str(ROOT/'tests/fixtures/rookie_arena/manual_disabled_skill.png')),cv2.COLOR_BGR2RGB)
        for scale in (.98,1.,1.02):
            frame=cv2.resize(cv2.resize(original,None,fx=scale,fy=scale),(1280,720))
            for brightness in (-20,0,20):
                adjusted=np.clip(frame.astype(float)+brightness,0,255).astype(np.uint8)
                obs=self.vision.observe(adjusted)
                self.assertIs(obs['auto_on'],False)
                runner=RookieArenaRunner()
                runner.state='battle'; runner.battle_at=0
                runner.step(obs,0)
                runner.step(obs,1)
                self.assertEqual(runner.step(obs,2)[0],'auto')
                self.assertIsNone(runner.step(obs,3)[0])
        # One locked label alone cannot prove that all manual controls exist.
        original[617:715,977:1170]=0
        self.assertIsNone(self.vision.observe(original)['auto_on'])

    def test_refresh_free_and_paid_continue_both_modes_with_actual_images(self):
        def read(name):
            return cv2.cvtColor(cv2.imread(str(ROOT/'tests/fixtures/rookie_arena'/f'{name}.png')),cv2.COLOR_BGR2RGB)
        for mode in ('fixed','sequential'):
            for name,after,remaining in (('refresh_free','refresh_after_free',None),
                                       ('refresh_paid30','refresh_after_paid',30),
                                       ('refresh_paid29','refresh_after_paid',29)):
                runner=RookieArenaRunner(mode=mode,preferred=2)
                failed=self.vision.observe(read('refresh_failed'))
                runner.step(failed,0)
                self.assertEqual(runner.step(failed,1)[0],'open_refresh')
                self.assertEqual(runner.step(failed,5)[0],'open_refresh')
                popup=self.vision.observe(read(name))
                self.assertEqual(popup['screen'],'refresh')
                self.assertEqual(popup['refresh_remaining'],remaining)
                self.assertEqual(popup['refresh_free'],remaining is None)
                runner.step(popup,6)
                self.assertEqual(runner.step(popup,7)[0],'confirmed')
                self.assertEqual(runner.step(popup,8)[0],'confirm_refresh')
                self.assertIsNone(runner.step(popup,12)[0])
                self.assertIsNone(runner.step(failed,13)[0])
                self.assertIsNone(runner.step(failed,14)[0])
                self.assertEqual(runner.failed,{1,2,3})
                fresh=self.vision.observe(read(after))
                self.assertIsNone(runner.step(fresh,15)[0])
                self.assertEqual(runner.step(fresh,16)[0],'refreshed')
                self.assertEqual(runner.count,0)
                self.assertEqual(runner.spent,0)
                self.assertEqual(runner.step(fresh,17)[0],'select_2' if mode=='fixed' else 'select_1')

    def test_refresh_exhausted_unknown_and_unconfirmed_are_not_confirmed(self):
        for remaining,event in ((0,'refresh_exhausted'),(None,None)):
            r=RookieArenaRunner()
            r.state='refresh'; r.refresh_at=0
            obs=dict(screen='refresh',refresh_free=False,refresh_remaining=remaining,refresh_confirm_visible=True)
            r.step(obs,0)
            self.assertEqual(r.step(obs,1)[0],event)
        r=RookieArenaRunner()
        r.state='refresh'; r.refresh_at=0
        popup=dict(screen='refresh',refresh_free=True,refresh_confirm_visible=True)
        r.step(popup,0)
        self.assertEqual(r.step(popup,1)[0],'confirm_refresh')
        self.assertIsNone(r.step(popup,20)[0])
        self.assertEqual(r.step(popup,47)[0],'refresh_uncertain')
        frame=cv2.cvtColor(cv2.imread(str(ROOT/'tests/fixtures/rookie_arena/refresh_paid30.png')),cv2.COLOR_BGR2RGB)
        frame[400:430,713:743]=0
        self.assertIsNone(self.vision.observe(frame)['refresh_remaining'])
        self.assertIsNone(self.vision.observe((frame*.2).astype(np.uint8))['screen'])

    def test_refresh_popup_resampling_and_actual_font_zero(self):
        for name,remaining in (('refresh_free',None),('refresh_paid30',30),('refresh_paid29',29)):
            frame=cv2.cvtColor(cv2.imread(str(ROOT/'tests/fixtures/rookie_arena'/f'{name}.png')),cv2.COLOR_BGR2RGB)
            for scale in (.99,1.,1.01):
                resized=cv2.resize(cv2.resize(frame,None,fx=scale,fy=scale),(1280,720))
                for brightness in (-15,0,15):
                    obs=self.vision.observe(np.clip(resized.astype(float)+brightness,0,255).astype(np.uint8))
                    self.assertEqual(obs['screen'],'refresh')
                    self.assertEqual(obs['refresh_remaining'],remaining)
                    self.assertIs(obs['refresh_confirm_visible'],True)
        frame=cv2.cvtColor(cv2.imread(str(ROOT/'tests/fixtures/rookie_arena/refresh_paid30.png')),cv2.COLOR_BGR2RGB)
        zero=frame[405:423,730:742].copy()
        frame[400:430,713:743]=0
        frame[405:423,718:730]=zero
        self.assertEqual(self.vision.observe(frame)['refresh_remaining'],0)

    def test_friendship_overlay_priority_and_return_to_victory(self):
        def read(name):
            return cv2.cvtColor(cv2.imread(str(ROOT/'tests/fixtures/rookie_arena'/f'{name}.png')),cv2.COLOR_BGR2RGB)
        popup = read('friendship')
        for scale in (.99, 1, 1.01):
            frame=cv2.resize(cv2.resize(popup,None,fx=scale,fy=scale),(1280,720))
            self.assertEqual(self.vision.observe(frame)['screen'],'friendship')
        self.assertIsNone(self.vision.observe((popup*.2).astype(np.uint8))['screen'])
        no_close=popup.copy()
        no_close[525:625,665:850]=0
        self.assertNotEqual(self.vision.observe(no_close)['screen'],'friendship')
        r=RookieArenaRunner(total=1)
        r.state='battle'; r.battle_at=0; r.chosen=1
        for t,name,event in ((1,'friendship','friendship_close'),(3,'friendship_victory','confirm'),(5,'01','done')):
            obs=self.vision.observe(read(name))
            r.step(obs,t)
            self.assertEqual(r.step(obs,t+.5)[0],event)
        self.assertEqual(r.count,1)

    def setUp(self):
        self.vision=RookieArenaVision(ROOT)

    def ref(self, number):
        image=cv2.imread(str(ROOT/'tests'/'fixtures'/'rookie_arena'/f'{number:02}.png'))
        self.assertIsNotNone(image)
        return cv2.cvtColor(image,cv2.COLOR_BGR2RGB)

    def test_reference_screen_classification(self):
        expected={1:'list',2:'list',3:'team',4:'battle',5:'battle',6:'battle',
                  7:'defeat',8:'list',9:'victory',11:'purchase',12:'purchase'}
        for number,screen in expected.items():
            with self.subTest(number=number):
                self.assertEqual(self.vision.observe(self.ref(number))['screen'],screen)

    def test_auto_and_result_controls(self):
        self.assertIs(self.vision.observe(self.ref(4))['auto_on'],False)
        for number in (5,6):
            self.assertIs(self.vision.observe(self.ref(number))['auto_on'],True)
        frame=self.ref(5)
        frame[10:57,1100:1150]=self.ref(4)[10:57,1100:1150]
        self.assertIs(self.vision.observe(frame)['auto_on'],True)
        for number in (7,9):
            self.assertTrue(self.vision.observe(self.ref(number))['confirm_visible'])
            frame=self.ref(number)
            frame[620:700,1090:1250]=0
            self.assertFalse(self.vision.observe(frame)['confirm_visible'])

    def test_manual_auto_state_with_actual_latest_client_and_resampling(self):
        client=cv2.imread(str(ROOT/'tests/fixtures/rookie_arena/manual_latest_client.png'))
        for top in (0,1,2):
            for scale in (.98,1.,1.02):
                frame=cv2.cvtColor(cv2.resize(cv2.resize(client[top:],None,fx=scale,fy=scale),
                                             (1280,720)),cv2.COLOR_BGR2RGB)
                for brightness in (-20,0,20):
                    with self.subTest(top=top,scale=scale,brightness=brightness):
                        adjusted=np.clip(frame.astype(float)+brightness,0,255).astype(np.uint8)
                        self.assertIs(self.vision.observe(adjusted)['auto_on'],False)

    def test_landy_silver_skill_frames_are_manual_across_client_resampling(self):
        client=cv2.imread(str(ROOT/'tests/fixtures/rookie_arena/manual_landy_client.png'))
        self.assertIsNotNone(client)
        for top in (0,1,2):
            for scale in (.97,.99,1.,1.01,1.03):
                frame=cv2.cvtColor(cv2.resize(cv2.resize(client[top:],None,fx=scale,fy=scale),
                                             (1280,720)),cv2.COLOR_BGR2RGB)
                for brightness in (-20,0,20):
                    with self.subTest(top=top,scale=scale,brightness=brightness):
                        adjusted=np.clip(frame.astype(float)+brightness,0,255).astype(np.uint8)
                        self.assertEqual(self.vision.observe(adjusted)['screen'],'battle')
                        self.assertIs(self.vision.observe(adjusted)['auto_on'],False)
        # Bright flat effects lack the three framed controls.
        for colour in ((140,150,180),(10,90,250),(220,220,220)):
            frame=cv2.cvtColor(cv2.resize(client,(1280,720)),cv2.COLOR_BGR2RGB)
            frame[617:720,960:1280]=colour
            self.assertIsNone(self.vision.observe(frame)['auto_on'])

    def test_auto_requires_repeated_checkmarks_not_blue_effects(self):
        frame=self.ref(4)
        frame[671:720,975:1280]=(15,80,220)
        self.assertIsNone(self.vision.observe(frame)['auto_on'])
        # The former broad mean also accepted this vivid animation rectangle.
        frame=self.ref(4)
        frame[617:720,960:1280]=(10,50,240)
        self.assertIsNone(self.vision.observe(frame)['auto_on'])
        for number in (5,6):
            for scale in (.98,1.,1.02):
                frame=cv2.resize(cv2.resize(self.ref(number),None,fx=scale,fy=scale),(1280,720))
                for brightness in (-20,0,20):
                    adjusted=np.clip(frame.astype(float)+brightness,0,255).astype(np.uint8)
                    self.assertIs(self.vision.observe(adjusted)['auto_on'],True)
            # Four blue circles without their white ticks are not proof of auto.
            frame=self.ref(number)
            for x in (1004,1082,1160,1238):
                frame[689:709,x-12:x+13]=(15,80,190)
            self.assertIsNone(self.vision.observe(frame)['auto_on'])
            # A rotating active icon can pass its idle pose. Without checks,
            # four round portrait rims must not become three manual skills.
            frame[10:57,1100:1150]=self.ref(4)[10:57,1100:1150]
            for scale in (.97,1.,1.03):
                resized=cv2.resize(cv2.resize(frame,None,fx=scale,fy=scale),(1280,720))
                for brightness in (-20,0,20):
                    adjusted=np.clip(resized.astype(float)+brightness,0,255).astype(np.uint8)
                    self.assertIsNone(self.vision.observe(adjusted)['auto_on'])

    def test_hidden_controls_leave_auto_unknown_even_with_idle_icon(self):
        frame=self.ref(4)
        frame[610:720,960:1280]=0
        self.assertIsNone(self.vision.observe(frame)['auto_on'])
        animation=cv2.cvtColor(cv2.imread(str(ROOT/'tests/fixtures/rookie_arena/opening_animation.png')),
                               cv2.COLOR_BGR2RGB)
        self.assertIsNone(self.vision.observe(animation)['auto_on'])

    def test_manual_controls_do_not_depend_on_skill_interior_art(self):
        frame=self.ref(4)
        for x in (977,1080,1183):
            frame[629:703,x+12:x+78]=(10,60,170)
        self.assertIs(self.vision.observe(frame)['auto_on'],False)

    def test_promotion_and_rewards_then_continue_with_actual_images(self):
        def image(name):
            return cv2.cvtColor(cv2.imread(str(ROOT/'tests/fixtures/rookie_arena'/f'{name}.png')),cv2.COLOR_BGR2RGB)
        for total in (1, None):
            runner=RookieArenaRunner(mode='sequential', total=total)
            runner.state='battle'
            runner.chosen=1
            now=0
            for frame, expected in ((self.ref(9),'confirm'),
                                    (image('promotion'),'promotion_confirm'),
                                    (image('promotion_rewards'),'reward_close'),
                                    (image('promoted_list'),'done' if total else 'confirmed')):
                obs=self.vision.observe(frame)
                now+=1
                runner.step(obs,now)
                now+=1
                self.assertEqual(runner.step(obs,now)[0], expected)
            self.assertEqual(runner.count,1)
            if total is None:
                self.assertEqual(runner.step(obs,now+1)[0],'select_1')
                self.assertEqual(obs['flags'],8)

    def test_promotion_detection_is_not_tied_to_rank_name(self):
        frame=cv2.cvtColor(cv2.imread(str(ROOT/'tests/fixtures/rookie_arena/promotion.png')),cv2.COLOR_BGR2RGB)
        frame[450:560,400:880]=0
        self.assertEqual(self.vision.observe(frame)['screen'],'promotion')
        frame[615:705,550:745]=0
        self.assertNotEqual(self.vision.observe(frame)['screen'],'promotion')
        for name in ('promotion','promotion_rewards'):
            frame=cv2.cvtColor(cv2.imread(str(ROOT/'tests/fixtures/rookie_arena'/f'{name}.png')),cv2.COLOR_BGR2RGB)
            self.assertIsNone(self.vision.observe((frame*.2).astype(np.uint8))['screen'])

    def test_streak_list_after_victory_and_restart(self):
        frame=cv2.cvtColor(cv2.imread(str(ROOT/'tests/fixtures/rookie_arena/streak.png')),cv2.COLOR_BGR2RGB)
        observation=self.vision.observe(frame)
        self.assertEqual(observation['screen'],'list')
        self.assertEqual(observation['flags'],9)
        # Confirming a win must acknowledge this variant as the next list.
        runner=RookieArenaRunner(total=1)
        runner.state='battle'
        runner.chosen=1
        result=self.vision.observe(self.ref(9))
        runner.step(result,0)
        self.assertEqual(runner.step(result,1)[0],'confirm')
        runner.step(observation,2)
        self.assertEqual(runner.step(observation,3)[0],'done')
        # A new run must select an opponent on the same streak screen.
        runner=RookieArenaRunner(mode='sequential')
        runner.step(observation,0)
        self.assertEqual(runner.step(observation,1)[0],'select_1')
        # List detection must not depend on the changing streak text.
        frame[85:150,320:780]=0
        self.assertEqual(self.vision.observe(frame)['screen'],'list')
        self.assertIsNone(self.vision.observe((frame*.2).astype(np.uint8))['screen'])

    def test_roster_selection_and_red_failure(self):
        first=self.vision.observe(self.ref(1))
        selected=self.vision.observe(self.ref(2))
        self.assertEqual(first['flags'],7)
        self.assertEqual(selected['selected_opponent'],1)
        self.assertTrue(selected['challenge_enabled'])
        self.assertFalse(first['challenge_enabled'])
        self.assertEqual(first['signature'],selected['signature'])
        failed=self.vision.observe(self.ref(8))
        self.assertEqual(failed['failed'],{3})
        self.assertEqual(failed['flags'],6)
        self.assertNotEqual(first['signature'],failed['signature'])

    def test_latest_streak_flags_and_resampled_references(self):
        # The newest screenshot's nine used to be rejected: reducing its
        # 15px glyph to the reference mask discarded the distinguishing tail.
        for name,expected in (('01',7),('08',6),('streak',9),('streak_latest',9)):
            frame=cv2.cvtColor(cv2.imread(str(ROOT/'tests/fixtures/rookie_arena'/f'{name}.png')),cv2.COLOR_BGR2RGB)
            for scale in (.99,1.,1.01):
                with self.subTest(name=name,scale=scale):
                    resized=cv2.resize(cv2.resize(frame,None,fx=scale,fy=scale),(1280,720))
                    observed=self.vision.observe(resized)
                    self.assertEqual(observed['screen'],'list')
                    self.assertEqual(observed['flags'],expected)
                    runner=RookieArenaRunner(mode='sequential')
                    runner.step(observed,0)
                    self.assertEqual(runner.step(observed,1)[0],'select_1')

    def test_client_crop_with_one_pixel_vertical_variation(self):
        client=cv2.imread(str(ROOT/'tests/fixtures/rookie_arena/streak_client.png'))
        # Recreate adjacent title-bar/client crop boundaries without relying
        # on the screenshot's particular normalization pixel alignment.
        padded=cv2.copyMakeBorder(client,1,0,0,0,cv2.BORDER_REPLICATE)
        for top in (0,1,2):
            with self.subTest(top=top):
                frame=cv2.cvtColor(cv2.resize(padded[top:],(1280,720)),cv2.COLOR_BGR2RGB)
                self.assertEqual(self.vision.observe(frame)['flags'],9)

    def test_non_numeric_glyphs_and_missing_flags_remain_unknown(self):
        for text in ('?','X','A','O','B','Z'):
            with self.subTest(text=text):
                crop=np.zeros((32,36,3),np.uint8)
                cv2.putText(crop,text,(10,25),cv2.FONT_HERSHEY_SIMPLEX,.65,(255,255,255),1)
                self.assertIsNone(self.vision._number(crop))
        frame=self.ref(1)
        frame[17:49,530:566]=0
        observed=self.vision.observe(frame)
        self.assertEqual(observed['screen'],'list')
        self.assertIsNone(observed['flags'])

    def test_purchase_currencies_and_owned_resources(self):
        first=self.vision.observe(self.ref(11))
        self.assertIs(first['friendship_available'],True)
        self.assertIs(first['friendship_affordable'],True)
        self.assertIs(first['skystone_affordable'],True)
        self.assertEqual(first['selected_currency'],'friendship')
        cooldown=self.vision.observe(self.ref(12))
        self.assertIs(cooldown['friendship_available'],False)
        self.assertIs(cooldown['skystone_affordable'],True)
        self.assertEqual(cooldown['selected_currency'],'skystone')

    def test_unknown_resources_and_currency_are_not_authorized(self):
        frame=self.ref(11)
        frame[407:435,380:880]=0
        frame[300:400,380:620]=0
        frame[300:440,665:900]=0
        observed=self.vision.observe(frame)
        self.assertEqual(observed['screen'],'purchase')
        self.assertIsNone(observed['friendship_available'])
        self.assertIsNone(observed['friendship_affordable'])
        self.assertIsNone(observed['skystone_affordable'])
        self.assertIsNone(observed['selected_currency'])

    def glyph(self, digit):
        return next(t for d,t in self.vision.digits if d==digit)

    def test_synthetic_zero_and_positive_flags(self):
        # Zero was not supplied in the flags field. This exercises the retained
        # same-font header zero against the actual flags location.
        for digit in range(10):
            frame=self.ref(1)
            frame[17:49,538:566]=15
            glyph=self.glyph(digit)
            h,w=glyph.shape
            frame[24:24+h,543:543+w]=glyph[:,:,None]
            self.assertEqual(self.vision.observe(frame)['flags'],digit)
        frame=self.ref(1)
        frame[17:49,538:566]=15
        self.assertIsNone(self.vision.observe(frame)['flags'])
        frame=self.ref(1)
        frame[17:49,530:566]=15
        for digit,x in ((1,532),(0,544)):
            glyph=self.glyph(digit)
            h,w=glyph.shape
            frame[24:24+h,x:x+w]=glyph[:,:,None]
        self.assertEqual(self.vision.observe(frame)['flags'],10)

    def test_actual_five_flags_across_client_alignment_scale_and_brightness(self):
        client=cv2.imread(str(ROOT/'tests/fixtures/rookie_arena/flags_five_client.png'))
        for top in (0,1,2):
            for scale in (.97,.98,.99,1.,1.01,1.02,1.03):
                resized=cv2.resize(cv2.resize(client[top:],None,fx=scale,fy=scale),(1280,720))
                frame=cv2.cvtColor(resized,cv2.COLOR_BGR2RGB)
                for brightness in (-20,0,20):
                    with self.subTest(top=top,scale=scale,brightness=brightness):
                        adjusted=np.clip(frame.astype(float)+brightness,0,255).astype(np.uint8)
                        self.assertEqual(self.vision._flags(adjusted[24:50,530:566]),5)
        observation=self.vision.observe(cv2.cvtColor(cv2.resize(client,(1280,720)),cv2.COLOR_BGR2RGB))
        self.assertEqual(observation['flags'],5)
        runner=RookieArenaRunner(mode='fixed',preferred=3)
        runner.step(observation,0)
        self.assertEqual(runner.step(observation,1)[0],'select_3')
        purchase=RookieArenaRunner()
        purchase.state='buy_wait'
        purchase.purchase_balance=0
        purchase.purchase_currency='skystone'
        purchase.purchase_at=0
        purchase.step(observation,0)
        self.assertEqual(purchase.step(observation,1)[0],'purchased')
        self.assertEqual(purchase.spent,30)

    def test_shifted_header_reads_flags_and_starts_without_purchase(self):
        frame=cv2.cvtColor(cv2.imread(str(ROOT/'tests/fixtures/rookie_arena/flags_shifted_header.png')),cv2.COLOR_BGR2RGB)
        for scale in (.98,1.,1.02):
            resized=cv2.resize(cv2.resize(frame,None,fx=scale,fy=scale),(1280,720))
            for brightness in (-20,0,20):
                adjusted=np.clip(resized.astype(float)+brightness,0,255).astype(np.uint8)
                observation=self.vision.observe(adjusted)
                self.assertEqual(observation['flags'],5)
                runner=RookieArenaRunner(mode='fixed',preferred=1)
                runner.step(observation,0)
                self.assertEqual(runner.step(observation,1)[0],'select_1')
        frame[24:50,486:502]=0
        self.assertIsNone(self.vision.observe(frame)['flags'])

    def test_shifted_zero_opens_correct_counter_and_buys_once(self):
        def read(name):
            return cv2.cvtColor(cv2.imread(str(ROOT/'tests/fixtures/rookie_arena'/f'{name}.png')),cv2.COLOR_BGR2RGB)
        zero=self.vision.observe(read('zero_shifted_client'))
        self.assertEqual(zero['flags'],0)
        self.assertTrue(475 <= zero['purchase_open_point'][0] <= 485)
        runner=RookieArenaRunner(refill=True,budget=90)
        runner.step(zero,0)
        self.assertEqual(runner.step(zero,1),('open_purchase',zero['purchase_open_point']))
        self.assertEqual(runner.step(zero,5),('open_purchase',zero['purchase_open_point']))
        popup=self.vision.observe(read('purchase_shifted_client'))
        self.assertEqual(popup['screen'],'purchase')
        self.assertIs(popup['friendship_available'],False)
        self.assertIs(popup['skystone_affordable'],True)
        self.assertEqual(popup['selected_currency'],'skystone')
        runner.step(popup,6)
        self.assertEqual(runner.step(popup,7)[0],'confirmed')
        self.assertEqual(runner.step(popup,8)[0],'buy_skystone')
        self.assertIsNone(runner.step(popup,9)[0])
        five=self.vision.observe(read('flags_shifted_header'))
        runner.step(five,10)
        self.assertEqual(runner.step(five,11)[0],'purchased')
        self.assertEqual(runner.spent,30)

    def test_owned_14351_is_not_confused_with_14361(self):
        frame=cv2.cvtColor(cv2.imread(str(ROOT/'tests/fixtures/rookie_arena/purchase_owned_14351.png')),cv2.COLOR_BGR2RGB)
        for scale in (.99,1.,1.01):
            resized=cv2.resize(cv2.resize(frame,None,fx=scale,fy=scale),(1280,720))
            for brightness in (-15,0,15):
                adjusted=np.clip(resized.astype(float)+brightness,0,255).astype(np.uint8)
                self.assertEqual(self.vision._number(adjusted[407:435,710:870],True,True),14351)
                obs=self.vision.observe(adjusted)
                self.assertIs(obs['friendship_available'],False)
                self.assertIs(obs['skystone_affordable'],True)
                self.assertEqual(obs['selected_currency'],'skystone')
                runner=RookieArenaRunner(refill=True,budget=120)
                runner.state='purchase'
                runner.purchase_at=0
                runner.step(obs,0)
                self.assertEqual(runner.step(obs,1)[0],'buy_skystone')
        frame[407:435,788:842]=0
        self.assertIsNone(self.vision.observe(frame)['skystone_affordable'])

    def test_same_font_header_digits_zero_through_ten_under_resampling(self):
        # These are antialiased white header patches from supplied screenshots,
        # separate from the green currency-resource templates.
        glyphs={digit:cv2.cvtColor(cv2.imread(str(ROOT/'assets/rookie_arena'/f'flagdigit_{digit}_header.png')),cv2.COLOR_BGR2RGB)
                for digit in range(10)}
        for value in range(11):
            crop=np.full((26,36,3),20,np.uint8)
            x=4
            for digit in str(value):
                patch=glyphs[int(digit)]
                # Trim background by projection while preserving full grayscale.
                ys,xs=np.nonzero(patch.min(axis=2)>110)
                patch=patch[ys.min():ys.max()+1,xs.min():xs.max()+1]
                h,w=patch.shape[:2]
                crop[3:3+h,x:x+w]=patch
                x+=w+3
            for scale in (.97,.98,.99,1.,1.01,1.02,1.03):
                resized=cv2.resize(cv2.resize(crop,None,fx=scale,fy=scale),(36,26))
                for brightness in (-20,0,20):
                    with self.subTest(value=value,scale=scale,brightness=brightness):
                        adjusted=np.clip(resized.astype(float)+brightness,0,255).astype(np.uint8)
                        self.assertEqual(self.vision._flags(adjusted),value)

    def test_flags_reject_unknown_blank_and_truncated_digits(self):
        for text in ('?','X','A','O','B','Z'):
            crop=np.zeros((26,36,3),np.uint8)
            cv2.putText(crop,text,(10,23),cv2.FONT_HERSHEY_SIMPLEX,.65,(255,255,255),1)
            self.assertIsNone(self.vision._flags(crop),text)
        for shade in (0,20,150,255):
            self.assertIsNone(self.vision._flags(np.full((26,36,3),shade,np.uint8)))
        crop=np.zeros((26,36,3),np.uint8)
        crop[9:17,12:22]=255
        self.assertIsNone(self.vision._flags(crop))

    def test_synthetic_unaffordable_green_owned_count(self):
        frame=self.ref(11)
        frame[407:435,499:610]=0
        glyph=self.glyph(9)
        h,w=glyph.shape
        for x in (503,515):
            frame[413:413+h,x:x+w,1]=glyph
        observed=self.vision.observe(frame)
        self.assertIs(observed['friendship_affordable'],False)

    def test_blank_and_dim_backgrounds_are_unknown(self):
        for shade in (0,40,150,255):
            self.assertIsNone(self.vision.observe(np.full((720,1280,3),shade,np.uint8))['screen'])
        for number in (1,3,4,7,9,11):
            self.assertIsNone(self.vision.observe((self.ref(number)*.2).astype(np.uint8))['screen'])


if __name__=='__main__':
    unittest.main()
