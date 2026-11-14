import unittest
from unittest.mock import Mock, patch

import numpy as np
import cv2

from mode_navigation import ModeNavigation
from app import App, ROOT
from navigation_vision import NavigationVision


class NavigationTests(unittest.TestCase):
    def observe(self, runner, screen, now, point=None):
        first = runner.step(screen, now, point)
        second = runner.step(screen, now+.5, point)
        return first if first[0] is not None else second

    def test_all_lobby_paths_wait_for_positive_transitions(self):
        routes = {
            'shop': [('idle', 'wake'), ('lobby', 'shop')],
            'arena': [('idle', 'wake'), ('lobby', 'arena'), ('arena_hub', 'rookie')],
            'abyss': [('idle', 'wake'), ('lobby', 'battle'), ('battle_other', 'normal'),
                      ('battle_normal', 'swipe'), ('battle_abyss', 'abyss_card'),
                      ('abyss_hub', 'abyss'), ('abyss_floors', 'select_team')],
        }
        for mode, path in routes.items():
            with self.subTest(mode=mode):
                runner = ModeNavigation(mode)
                for i, (screen, action) in enumerate(path):
                    event, point = self.observe(runner, screen, i*5, (800, 420))
                    self.assertEqual(event, action)
                    self.assertIsNotNone(point)
                self.assertEqual(self.observe(runner, 'terminal', 50), ('entered', None))
                self.assertFalse(runner.active)

    def test_restart_on_each_intermediate_screen(self):
        for mode, path in ModeNavigation.PATHS.items():
            for screen, (event, action, _) in path.items():
                with self.subTest(mode=mode, screen=screen):
                    runner = ModeNavigation(mode)
                    self.assertEqual(self.observe(runner, screen, 0), (event, action))

    def test_unknown_or_unexpected_screen_never_acknowledges_or_clicks(self):
        runner = ModeNavigation('abyss')
        self.observe(runner, 'lobby', 0)
        self.assertEqual(self.observe(runner, None, 5), (None, None))
        self.assertEqual(self.observe(runner, 'arena_hub', 10), (None, None))
        self.assertIsNotNone(runner.pending)
        self.assertEqual(runner.step(None, 46), ('timeout', None))

    def test_retries_only_visible_source_and_are_bounded(self):
        runner = ModeNavigation('abyss')
        self.observe(runner, 'battle_normal', 0)
        for now in (5, 10, 15):
            self.assertEqual(self.observe(runner, 'battle_normal', now)[0], 'swipe')
        self.assertEqual(self.observe(runner, 'battle_normal', 20), (None, None))
        self.assertEqual(runner.step('battle_normal', 46), ('timeout', None))

    def test_already_in_mode_needs_two_frames_and_no_navigation_click(self):
        for mode in ModeNavigation.PATHS:
            runner = ModeNavigation(mode)
            self.assertEqual(runner.step('terminal', 0), (None, None))
            self.assertEqual(runner.step('terminal', .5), ('entered', None))

    def test_dynamic_abyss_card_position_and_other_modes_are_excluded(self):
        runner = ModeNavigation('abyss')
        self.assertEqual(self.observe(runner, 'battle_abyss', 0, (700, 440)),
                         ('abyss_card', ('click', 700, 440)))
        for mode in ('shop', 'arena'):
            self.assertEqual(self.observe(ModeNavigation(mode), 'battle_abyss', 0, (700, 440)),
                             (None, None))


class AppNavigationTests(unittest.TestCase):
    def make_app(self, screen='lobby', preview=False, background=True):
        app = App.__new__(App)
        app.navigation = ModeNavigation('abyss')
        app.navigation_vision = Mock()
        app.navigation_vision.observe.return_value = (screen, None)
        app.background_input = background
        app.preview = preview
        app.background_clicker = Mock()
        app.status = Mock()
        app.stop = Mock()
        app.log = Mock()
        app.hwnd = 123
        app.running = True
        app.root = Mock()
        app.frame = np.zeros((720, 1280), np.uint8)
        return app

    def tick(self, app, now, terminal=False):
        return app.tick_navigation(app.frame, now, (300, 200, 1580, 920), 300, 200, terminal)

    def test_preview_does_not_advance_or_click(self):
        app = self.make_app(preview=True)
        self.tick(app, 0)
        self.tick(app, .5)
        self.assertIsNone(app.navigation.pending)
        app.background_clicker.click.assert_not_called()

    def test_navigation_evidence_precedes_generic_terminal_and_maps_client_coordinates(self):
        app = self.make_app()
        self.tick(app, 0, terminal=True)
        self.tick(app, .5, terminal=True)
        app.background_clicker.click.assert_called_once_with(123, 1200, 325)
        self.assertTrue(app.navigation.active)

    def test_swipe_dispatch_and_foreground_stop_release(self):
        app = self.make_app('battle_normal')
        self.tick(app, 0)
        self.tick(app, .5)
        app.background_clicker.drag.assert_called_once_with(123, 1110, 420, 250, 420)
        app = self.make_app('battle_normal', background=False)
        with patch('app.user') as user:
            user.GetForegroundWindow.return_value = 123
            user.GetAsyncKeyState.return_value = 0
            self.tick(app, 0)
            self.tick(app, .5)
            callback = app.root.after.call_args.args[1]
            app.running = False
            callback()
            self.assertIsNone(app.navigation_drag_token)
            user.mouse_event.assert_any_call(4, 0, 0, 0, 0)

    def test_real_frames_follow_all_routes_without_premature_runner_entry(self):
        routes = {
            'shop': ['episode/idle', 'episode/menu'],
            'arena': ['episode/idle', 'episode/menu', 'navigation/arena_hub'],
            'abyss': ['episode/idle', 'episode/menu', 'navigation/battle_seasonal',
                      'navigation/battle_left', 'navigation/battle_right',
                      'navigation/abyss_hub', 'navigation/abyss_floors_animated'],
        }
        for mode, frames in routes.items():
            with self.subTest(mode=mode):
                app = self.make_app()
                app.navigation = ModeNavigation(mode)
                app.navigation_vision = NavigationVision(ROOT)
                for index, scene in enumerate(frames):
                    app.frame = cv2.imread(str(ROOT/'tests/fixtures'/(scene+'.png')), 0)
                    self.assertTrue(self.tick(app, index*5))
                    self.assertTrue(self.tick(app, index*5+.5))
                self.assertEqual(app.background_clicker.click.call_count,
                                 len(frames) - (1 if mode == 'abyss' else 0))
                self.assertEqual(app.background_clicker.drag.call_count, int(mode == 'abyss'))
                app.frame = np.zeros((720,1280), np.uint8)
                self.assertTrue(self.tick(app, 40, terminal=True))
                self.assertFalse(self.tick(app, 40.5, terminal=True))
                self.assertFalse(app.navigation.active)


if __name__ == '__main__':
    unittest.main()
