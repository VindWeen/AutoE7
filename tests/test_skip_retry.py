import unittest
from unittest.mock import Mock, patch
import numpy as np
from app import App, ROOT


class SkipRetryTests(unittest.TestCase):
    def make_app(self, elapsed=4, attempts=0, confirm=False):
        app = App.__new__(App)
        skip = {'id':'skip', 'phases':['battle'], 'threshold':.93, 'click':[1218,39], 'next':'battle'}
        dialog = {'id':'skip_confirm','phases':['battle'],'click':[748,458],'next':'battle'}
        app.running = True
        app.background_clicker = Mock(error=None)
        app.root = Mock()
        app.status = Mock()
        app.log = Mock()
        app.stop = Mock()
        app.last_action = 100
        app.next_action = 100
        app.background_input = True
        app.capture_covered = False
        app.hwnd = 123
        app.roi = (0,0,1,1)
        app.rules = [dialog,skip]
        app.phase = 'battle'
        app.awaiting = (skip,100,attempts)
        app.previous = None
        app.stable = 0
        app.preview = False
        app.count, app.total = 0,1
        app.detect = lambda frame,rule: 1 if rule['id']=='skip' or confirm else 0
        return app

    def tick(self, app, now):
        with patch('app.time.monotonic',return_value=now), patch('app.user') as user, patch('app.bounds',return_value=(300,200,1580,920)), patch('app.ImageGrab.grab',return_value=np.zeros((720,1280,3),np.uint8)):
            user.GetAsyncKeyState.return_value = 0
            user.GetForegroundWindow.return_value = 123
            app.tick()
            return user

    def test_retry_is_client_local_and_counted(self):
        app = self.make_app()
        self.tick(app,104)
        app.background_clicker.click.assert_called_once_with(123,1218,39)
        self.assertEqual(app.awaiting[2],1)

    def test_confirm_prevents_retry(self):
        app = self.make_app(confirm=True)
        self.tick(app,104)
        app.background_clicker.click.assert_not_called()
        self.assertIsNone(app.awaiting)
        self.assertEqual(app.previous,'skip_confirm')

    def test_no_retry_before_interval(self):
        app = self.make_app()
        self.tick(app,102)
        app.background_clicker.click.assert_not_called()

    def test_retry_limit_stops(self):
        app = self.make_app(attempts=3)
        self.tick(app,113)
        app.stop.assert_called_once()
        app.background_clicker.click.assert_not_called()

    def clear_app(self, visible=True, next_screen=False):
        app = self.make_app()
        clear = {'id':'clear','phases':['battle','result'],'click':[1240,674],'next':'result'}
        mvp = {'id':'mvp_confirm','phases':['result'],'click':[1166,660],'next':'reward'}
        app.phase = 'result'
        app.rules = [clear,mvp]
        app.awaiting = (clear,100,0)
        app.detect = lambda frame,rule: float((rule['id']=='clear' and visible) or (rule['id']=='mvp_confirm' and next_screen))
        return app

    def test_clear_animation_dropout_does_not_confirm_success(self):
        app = self.clear_app(visible=False)
        self.tick(app,104)
        self.assertIsNotNone(app.awaiting)
        app.background_clicker.click.assert_not_called()

    def test_clear_retries_while_waiting_for_mvp(self):
        app = self.clear_app()
        self.tick(app,104)
        app.background_clicker.click.assert_called_once_with(123,1240,674)
        self.assertEqual(app.awaiting[2],1)

    def test_mvp_acknowledges_clear_without_retry(self):
        app = self.clear_app(visible=False,next_screen=True)
        self.tick(app,104)
        self.assertIsNone(app.awaiting)
        app.background_clicker.click.assert_not_called()

    def test_clear_can_be_rediscovered_in_result_phase(self):
        app = self.clear_app()
        app.awaiting = None
        self.tick(app,104)
        self.tick(app,105)
        app.background_clicker.click.assert_called_once_with(123,1240,674)

    def preparation_app(self, action, visible=True, next_screen=False, attempts=0):
        app = self.make_app()
        phases = {'ready':'support','view_story':'battle','select_team':'team','start':'battle','start_quest':'battle'}
        source = {'id':action,'phases':['prepare'],'click':[1100,660],'next':phases[action]}
        target = {'id':'skip' if action in ('start','start_quest','view_story') else 'start',
                  'phases':[phases[action]],'click':[1200,40],'next':'battle'}
        app.phase = phases[action]
        app.rules = [source,target]
        app.awaiting = source,100,attempts
        app.detect = lambda frame,rule: float((rule['id']==action and visible) or (rule is target and next_screen))
        return app

    def test_all_preparation_buttons_retry_after_three_seconds(self):
        for action in ('ready','view_story','select_team','start','start_quest'):
            with self.subTest(action=action):
                app = self.preparation_app(action)
                self.tick(app,104)
                app.background_clicker.click.assert_called_once_with(123,1100,660)
                self.assertEqual(app.awaiting[2],1)
                self.assertEqual(app.count,0)

    def test_ready_and_team_wait_for_next_screen_on_dropout(self):
        for action in ('ready','select_team'):
            with self.subTest(action=action):
                app = self.preparation_app(action,visible=False)
                self.tick(app,104)
                self.assertIsNotNone(app.awaiting)
                app.background_clicker.click.assert_not_called()

    def test_start_accepts_normal_combat_after_two_valid_frames(self):
        for action in ('start_quest', 'view_story'):
            with self.subTest(action=action):
                app = self.preparation_app(action, visible=False)
                self.tick(app, 104)
                self.assertIsNotNone(app.awaiting)
                self.tick(app, 105)
                self.assertIsNone(app.awaiting)
                app.background_clicker.click.assert_not_called()

    def test_preparation_retries_stop_at_limit(self):
        for action in ('ready', 'view_story', 'select_team', 'start', 'start_quest'):
            with self.subTest(action=action):
                app = self.preparation_app(action, attempts=3)
                self.tick(app, 113)
                app.stop.assert_called_once()
                app.background_clicker.click.assert_not_called()

    def test_preparation_next_screen_prevents_old_button_retry(self):
        app = self.preparation_app('ready',visible=False,next_screen=True)
        self.tick(app,104)
        self.assertIsNone(app.awaiting)
        app.background_clicker.click.assert_not_called()

    def test_regular_mouse_mode_also_tracks_and_retries(self):
        app = self.preparation_app('ready')
        app.background_input = False
        user = self.tick(app,104)
        user.SetCursorPos.assert_called_once_with(1400,860)
        self.assertEqual(user.mouse_event.call_count,2)
        self.assertEqual(app.awaiting[2],1)
        app.background_clicker.click.assert_not_called()

    def result_app(self, action, visible=True, next_screen=False, attempts=0):
        app = self.make_app()
        source = {'id':action,'phases':['reward'],'click':[1166,660],'next':'$same'}
        target = {'id':'friend_cancel' if action=='mvp_confirm' else 'ready',
                  'phases':['reward'],'click':[530,529],'next':'$same'}
        app.phase = 'reward'
        app.rules = [target,source]
        app.awaiting = source,100,attempts
        app.detect = lambda frame,rule: float((rule is source and visible) or (rule is target and next_screen))
        return app

    def test_confirm_and_popup_buttons_retry(self):
        for action in ('mvp_confirm','skip_confirm','friend_cancel','story_clear','received_reward','map_rank_up','connection_unlocked','hero_friendship'):
            with self.subTest(action=action):
                app = self.result_app(action)
                self.tick(app,104)
                app.background_clicker.click.assert_called_once_with(123,1166,660)
                self.assertEqual(app.awaiting[2],1)

    def test_mvp_dropout_waits_for_reward_screen(self):
        app = self.result_app('mvp_confirm',visible=False)
        self.tick(app,104)
        self.assertIsNotNone(app.awaiting)
        app.background_clicker.click.assert_not_called()

    def test_rank_up_returns_to_clear_without_counting_round(self):
        app = self.make_app()
        rules = __import__('json').loads((ROOT / 'scenarios.json').read_text(encoding='utf-8'))['Đi Map']
        rank = next(r for r in rules if r['id'] == 'map_rank_up')
        app.rules = rules
        app.awaiting = None
        app.detect = lambda frame, rule: float(rule['id'] == 'map_rank_up')
        self.tick(app, 104)
        self.tick(app, 105)
        app.background_clicker.click.assert_called_once_with(123, 636, 691)
        self.assertEqual(app.phase, 'battle')
        app.detect = lambda frame, rule: float(rule['id'] == 'clear')
        self.tick(app, 107)
        self.tick(app, 108)
        self.assertEqual(app.awaiting[0]['id'], 'clear')
        self.assertEqual(app.phase, 'result')
        self.assertEqual(app.count, 0)

    def test_friend_popup_after_mvp_prevents_mvp_retry(self):
        app = self.result_app('mvp_confirm',visible=True,next_screen=True)
        self.tick(app,104)
        self.assertIsNone(app.awaiting)
        app.background_clicker.click.assert_not_called()
        self.assertEqual(app.previous,'friend_cancel')

    def test_mvp_can_be_rediscovered_while_waiting_for_rewards(self):
        app = self.result_app('mvp_confirm')
        app.awaiting = None
        self.tick(app,104)
        self.tick(app,105)
        app.background_clicker.click.assert_called_once_with(123,1166,660)

    def test_map_round_limit_and_run_until_stopped(self):
        for total in (1, None):
            with self.subTest(total=total):
                app = self.make_app()
                ready = {'id': 'ready', 'phases': ['reward'],
                         'click': [1120, 660], 'next': 'support'}
                app.rules = [ready]
                app.phase = 'reward'
                app.awaiting = None
                app.total = total
                app.detect = lambda frame, rule: 1
                self.tick(app, 104)
                self.tick(app, 105)
                self.assertEqual(app.count, 1)
                if total is None:
                    app.stop.assert_not_called()
                    app.background_clicker.click.assert_called_once_with(123, 1120, 660)
                    self.assertEqual(app.phase, 'support')
                    app.log.assert_called_with('Gửi click nền: ready · HWND=123 · client=(1120,660)')
                else:
                    app.stop.assert_called_once_with('Đã hoàn thành số vòng yêu cầu.')
                    app.background_clicker.click.assert_not_called()

    def test_connection_unlock_after_mvp_continues_reward_flow(self):
        app = self.make_app()
        rules = __import__('json').loads((ROOT / 'scenarios.json').read_text(encoding='utf-8'))['Đi Map']
        app.rules = rules
        app.phase = 'reward'
        app.awaiting = (next(r for r in rules if r['id'] == 'mvp_confirm'), 100, 0)
        for index, key in enumerate(('connection_unlocked', 'story_clear', 'received_reward')):
            app.detect = lambda frame, rule, key=key: float(rule['id'] == key)
            now = 104 + index * 4
            self.tick(app, now)
            self.tick(app, now + 1)
            self.assertEqual(app.awaiting[0]['id'], key)
            self.assertEqual(app.phase, 'reward')
            self.assertEqual(app.count, 0)
        self.assertEqual(app.background_clicker.click.call_args_list[0].args, (123, 640, 515))
        app.stop.assert_not_called()

    def test_hero_friendship_closes_before_mvp_without_counting_round(self):
        app = self.make_app()
        rules = __import__('json').loads((ROOT / 'scenarios.json').read_text(encoding='utf-8'))['Đi Map']
        app.rules = rules
        app.phase = 'result'
        app.awaiting = (next(r for r in rules if r['id'] == 'clear'), 100, 0)
        app.detect = lambda frame, rule: float(rule['id'] in ('hero_friendship', 'mvp_confirm'))
        self.tick(app, 104)
        self.tick(app, 105)
        app.background_clicker.click.assert_called_once_with(123, 756, 593)
        self.assertEqual(app.phase, 'result')
        self.assertEqual(app.count, 0)
        app.detect = lambda frame, rule: float(rule['id'] == 'mvp_confirm')
        self.tick(app, 107)
        self.tick(app, 108)
        self.assertEqual(app.awaiting[0]['id'], 'mvp_confirm')
        self.assertEqual(app.phase, 'reward')
        self.assertEqual(app.count, 0)
        app.stop.assert_not_called()


if __name__ == '__main__':
    unittest.main()
