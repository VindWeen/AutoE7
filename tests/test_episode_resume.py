"""Episode restarts recognize the current screen without blind recovery clicks."""
import json
import unittest
from unittest.mock import Mock, patch

import numpy as np
import cv2
from app import App, ROOT


class EpisodeResumeTests(unittest.TestCase):
    def make_app(self, *visible, preview=False):
        app = App.__new__(App)
        app.rules = json.loads((ROOT / 'scenarios.json').read_text(encoding='utf-8-sig'))['Đi Map']
        app.running = True
        app.episode_active = True
        app.episode_round_pending = False
        app.phase = 'resume'
        app.count, app.total = 0, 1
        app.root = Mock()
        app.status = Mock()
        app.log = Mock()
        app.stop = Mock(side_effect=lambda reason: setattr(app, 'running', False))
        app.background_clicker = Mock(error=None)
        app.background_input = True
        app.capture_covered = False
        app.hwnd = 123
        app.roi = (0, 0, 1, 1)
        app.last_action = app.next_action = 100
        app.awaiting = None
        app.awaiting_missing = 0
        app.previous = None
        app.stable = 0
        app.last_report = None
        app.preview = preview
        app.frame = np.zeros((720, 1280, 3), np.uint8)
        app.visible = set(visible)
        app.detect = lambda frame, rule: float(rule['id'] in app.visible)
        return app

    def tick(self, app, now):
        with patch('app.time.monotonic', return_value=now), patch('app.user') as user, \
                patch('app.bounds', return_value=(300, 200, 1580, 920)), \
                patch('app.ImageGrab.grab', side_effect=lambda **kwargs: app.frame):
            user.GetAsyncKeyState.return_value = 0
            user.GetForegroundWindow.return_value = 123
            app.tick()

    def observe(self, app, now, *visible):
        app.visible = set(visible)
        self.tick(app, now)
        self.tick(app, now + .5)

    def test_restart_at_each_supported_stage_screen(self):
        actions = ('ready', 'view_story', 'select_team', 'start', 'start_quest', 'skip', 'skip_confirm',
                   'clear', 'mvp_confirm', 'friend_cancel', 'story_clear', 'received_reward',
                   'hero_friendship', 'connection_unlocked', 'map_rank_up')
        for action in actions:
            with self.subTest(action=action):
                app = self.make_app(action)
                self.observe(app, 100, action)
                rule = next(rule for rule in app.rules if rule['id'] == action)
                app.background_clicker.click.assert_called_once_with(123, *rule['click'])
                self.assertEqual(app.count, 0)
                self.assertEqual(app.phase, 'resume' if rule['next'] == '$same' else rule['next'])

    def test_unknown_combat_waits_then_recovers_on_clear(self):
        app = self.make_app()
        self.observe(app, 100)
        self.observe(app, 110)
        app.background_clicker.click.assert_not_called()
        app.stop.assert_not_called()
        self.observe(app, 120, 'clear')
        app.background_clicker.click.assert_called_once()
        self.assertEqual(app.phase, 'result')

    def test_preview_never_clicks_or_counts_resumed_screens(self):
        for rule in self.make_app().rules:
            with self.subTest(action=rule['id']):
                app = self.make_app(rule['id'], preview=True)
                self.observe(app, 100, rule['id'])
                app.background_clicker.click.assert_not_called()
                self.assertEqual(app.phase, 'resume')
                self.assertEqual(app.count, 0)
                self.assertFalse(app.episode_round_pending)

    def test_resumed_result_counts_once_only_after_return_to_ready(self):
        for result in ('mvp_confirm', 'friend_cancel', 'hero_friendship', 'connection_unlocked',
                       'story_clear', 'received_reward', 'map_rank_up'):
            with self.subTest(result=result):
                app = self.make_app(result)
                self.observe(app, 100, result)
                self.assertEqual(app.count, 0)
                self.observe(app, 103, 'ready')
                self.assertEqual(app.count, 1)
                self.assertFalse(app.episode_round_pending)
                self.assertFalse(app.running)
                self.assertEqual(app.background_clicker.click.call_count, 1)

    def test_initial_ready_is_not_a_finished_run(self):
        app = self.make_app('ready')
        self.observe(app, 100, 'ready')
        self.assertEqual(app.count, 0)
        self.assertFalse(app.episode_round_pending)
        self.observe(app, 103, 'start')
        self.observe(app, 106, 'clear')
        self.observe(app, 109, 'mvp_confirm')
        self.observe(app, 112, 'ready')
        self.assertEqual(app.count, 1)
        self.assertEqual(app.background_clicker.click.call_count, 4)
        app.stop.assert_called_once()

    def test_initial_view_story_is_not_a_finished_run_and_completes_after_return(self):
        app = self.make_app('view_story')
        self.observe(app, 100, 'view_story')
        self.assertEqual(app.count, 0)
        self.assertTrue(app.episode_round_pending)
        self.observe(app, 103, 'skip')
        self.observe(app, 106, 'skip_confirm')
        self.observe(app, 109, 'story_clear')
        self.observe(app, 112, 'view_story')
        self.assertEqual(app.count, 1)
        self.assertEqual(app.background_clicker.click.call_count, 4)
        app.stop.assert_called_once()

    def test_view_story_without_reward_dialog_completes_round(self):
        app = self.make_app('view_story')
        self.observe(app, 100, 'view_story')
        self.assertEqual(app.count, 0)
        self.assertTrue(app.episode_round_pending)
        self.observe(app, 103, 'skip')
        self.observe(app, 106, 'skip_confirm')
        self.observe(app, 109, 'ready')
        self.assertEqual(app.count, 1)
        self.assertFalse(app.episode_round_pending)

    def test_modal_priority_over_underlying_skip_or_mvp(self):
        for popup, underneath in (('skip_confirm', 'skip'), ('friend_cancel', 'mvp_confirm'),
                                 ('hero_friendship', 'mvp_confirm'), ('mvp_confirm', 'clear'),
                                 ('friend_cancel', 'clear'), ('story_clear', 'ready'),
                                 ('skip_confirm', 'start'), ('received_reward', 'select_team')):
            with self.subTest(popup=popup):
                app = self.make_app(popup, underneath)
                self.observe(app, 100, popup, underneath)
                self.assertEqual(app.awaiting[0]['id'], popup)

    def test_actual_start_and_restart_reset_recovery_but_never_click(self):
        app = self.make_app()
        app.running = False
        app.window = Mock()
        app.window.current.return_value = 0
        app.items = [('Epic Seven', 123)]
        app.scenario = Mock()
        app.scenario.get.return_value = 'Đi Map'
        app.config = {'Đi Map': app.rules}
        app.forever = Mock()
        app.forever.get.return_value = False
        app.limit = Mock()
        app.limit.get.return_value = '2'
        app.region = Mock()
        app.region.get.return_value = '0,0,1,1'
        app.dry = Mock()
        app.dry.get.return_value = False
        app.no_mouse = Mock()
        app.no_mouse.get.return_value = True
        app.hidden_capture = Mock()
        app.hidden_capture.get.return_value = False
        app.window_capture = Mock()
        app.language = 'vi'
        with patch('app.fit_window_client', return_value=((1280, 720), (1280, 720))), \
                patch('app.bounds', return_value=(0, 0, 1280, 720)), \
                patch('app.set_running_ui'), patch('app.messagebox.showerror') as error:
            for _ in range(2):
                app.phase = 'reward'
                app.count = 7
                app.episode_round_pending = True
                App.start(app)
                self.assertTrue(app.running)
                self.assertEqual(app.phase, 'resume')
                self.assertEqual(app.count, 0)
                self.assertFalse(app.episode_round_pending)
                self.assertIsNone(app.awaiting)
                App.stop(app, 'test stop')
        error.assert_not_called()
        app.background_clicker.click.assert_not_called()

    def test_other_modes_keep_existing_phase_filter(self):
        app = self.make_app('clear')
        app.episode_active = False
        app.phase = 'prepare'
        self.observe(app, 100, 'clear')
        app.background_clicker.click.assert_not_called()

    def test_lobby_recovery_uses_real_images_and_requires_menu_then_ready(self):
        app = self.make_app()
        del app.detect
        app.templates = {}
        for now, scene, expected in ((100, 'idle', 'lobby_wake'),
                                     (103, 'menu', 'lobby_episode'), (106, 'ready', 'ready')):
            gray = cv2.imread(str(ROOT / 'tests/fixtures/episode' / (scene + '.png')), 0)
            app.frame = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
            self.observe(app, now)
            self.assertIsNotNone(app.awaiting)
            self.assertEqual(app.awaiting[0]['id'], expected)
        self.assertEqual(app.count, 0)
        self.assertEqual(app.phase, 'support')
        self.assertEqual(app.background_clicker.click.call_count, 3)
        app.background_clicker.click.assert_any_call(123, 640, 580)

    def test_unknown_real_quit_dialog_does_not_trigger_resume_clicks(self):
        app = self.make_app()
        del app.detect
        app.templates = {}
        gray = cv2.imread(str(ROOT / 'tests/fixtures/episode/quit_confirmation.png'), 0)
        app.frame = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        self.observe(app, 100)
        app.background_clicker.click.assert_not_called()
        self.assertEqual(app.count, 0)

    def test_view_story_real_image_detection(self):
        app = self.make_app()
        del app.detect
        app.templates = {}
        gray = cv2.imread(str(ROOT / 'tests/fixtures/episode/view_story.png'), 0)
        app.frame = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        self.observe(app, 100)
        self.assertIsNotNone(app.awaiting)
        self.assertEqual(app.awaiting[0]['id'], 'view_story')
        self.assertEqual(app.phase, 'battle')
        app.background_clicker.click.assert_called_once_with(123, 1120, 660)

    def test_lobby_click_retry_limit_and_positive_acknowledgement(self):
        for action in ('lobby_wake', 'lobby_episode'):
            with self.subTest(action=action):
                app = self.make_app(action)
                self.observe(app, 100, action)
                for now in (104, 108, 112):
                    self.tick(app, now)
                self.assertEqual(app.background_clicker.click.call_count, 4)
                self.assertEqual(app.awaiting[2], 3)
                # Disappearance into an unknown frame is not proof of success.
                app.visible = set()
                self.tick(app, 114)
                self.assertIsNotNone(app.awaiting)
                self.assertEqual(app.background_clicker.click.call_count, 4)
                self.tick(app, 125)
                app.stop.assert_called_once()


if __name__ == '__main__':
    unittest.main()
