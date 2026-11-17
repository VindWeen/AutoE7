from pathlib import Path
import unittest
import cv2
import numpy as np

from navigation_vision import NavigationVision

ROOT = Path(__file__).resolve().parents[1]


class NavigationVisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vision = NavigationVision(ROOT)

    def test_idle_and_visible_lobby_for_each_mode(self):
        for fixture, expected in (('idle', 'idle'), ('menu', 'lobby'),
                                  ('rabbit_idle', 'idle'), ('rabbit_menu', 'lobby')):
            frame = cv2.imread(str(ROOT / 'tests/fixtures/episode' / (fixture+'.png')), 0)
            for mode in ('shop', 'arena', 'abyss'):
                self.assertEqual(self.vision.observe(frame, mode), (expected, None))

    def test_floor_entry_excludes_other_modes(self):
        frame = cv2.imread(str(ROOT / 'tests/fixtures/navigation/abyss_floors.png'), 0)
        self.assertEqual(self.vision.observe(frame, 'abyss'), ('abyss_floors', None))
        for mode in ('shop', 'arena'):
            self.assertEqual(self.vision.observe(frame, mode), (None, None))
        for scale in (.3, .6, .8):
            self.assertEqual(self.vision.observe((frame*scale).astype(np.uint8), 'abyss'), (None, None))

    def test_floor_entry_survives_tower_animation_without_ignoring_overlays(self):
        for name in ('abyss_floors', 'abyss_floors_animated'):
            frame = cv2.imread(str(ROOT / 'tests/fixtures/navigation' / (name+'.png')), 0)
            self.assertEqual(self.vision.observe(frame, 'abyss'), ('abyss_floors', None))
            # Arbitrary animation changes outside the controls do not matter.
            changed = frame.copy()
            changed[100:600, 300:730] = 0
            self.assertEqual(self.vision.observe(changed, 'abyss'), ('abyss_floors', None))
            covered = frame.copy()
            covered[250:570, 340:940] = 35
            self.assertEqual(self.vision.observe(covered, 'abyss'), (None, None))
            covered = frame.copy()
            covered[630:700, 1000:1270] = 0
            self.assertEqual(self.vision.observe(covered, 'abyss'), (None, None))

    def test_unknown_screens_and_modal_do_not_authorize_navigation(self):
        for scene in ('ready', 'view_story', 'quit_confirmation'):
            frame = cv2.imread(str(ROOT / 'tests/fixtures/episode' / (scene+'.png')), 0)
            for mode in ('shop', 'arena', 'abyss'):
                self.assertEqual(self.vision.observe(frame, mode), (None, None))
        for frame in (None, np.zeros((500, 500), np.uint8), np.zeros((720, 1280), np.uint8)):
            self.assertEqual(self.vision.observe(frame, 'abyss'), (None, None))

    def test_abyss_menu_states_and_tab_selection(self):
        for fixture, expected in (('abyss_hub', 'abyss_hub'), ('battle_right', 'battle_abyss'),
                                  ('battle_left', 'battle_normal'), ('battle_seasonal', 'battle_other')):
            frame = cv2.imread(str(ROOT / 'tests/fixtures/navigation' / (fixture+'.png')), 0)
            with self.subTest(fixture=fixture):
                self.assertEqual(self.vision.observe(frame, 'abyss')[0], expected)
                for mode in ('shop', 'arena'):
                    self.assertEqual(self.vision.observe(frame, mode), (None, None))
                for factor in (.3, .6, .8):
                    self.assertEqual(self.vision.observe((frame*factor).astype(np.uint8), 'abyss'), (None, None))
                covered = frame.copy()
                covered[250:570, 340:940] = 35
                self.assertEqual(self.vision.observe(covered, 'abyss'), (None, None))

    def test_abyss_card_tracks_horizontal_position(self):
        frame = cv2.imread(str(ROOT / 'tests/fixtures/navigation/battle_right.png'), 0)
        for offset in (-300, -150, 150, 280):
            shifted = frame.copy()
            shifted[170:690] = cv2.warpAffine(frame[170:690], np.float32([[1,0,offset],[0,1,0]]), (1280,520))
            screen, point = self.vision.observe(shifted, 'abyss')
            self.assertEqual(screen, 'battle_abyss')
            self.assertAlmostEqual(point[0], 736+offset, delta=3)

    def test_partially_swiped_carousel_can_continue(self):
        frame = cv2.imread(str(ROOT / 'tests/fixtures/navigation/battle_left.png'), 0)
        for offset in (-100, -250, -400):
            shifted = frame.copy()
            shifted[170:690] = cv2.warpAffine(frame[170:690], np.float32([[1,0,offset],[0,1,0]]), (1280,520))
            self.assertEqual(self.vision.observe(shifted, 'abyss'), ('battle_normal', None))

    def test_arena_hub_requires_rookie_entry_and_unobstructed_scene(self):
        frame = cv2.imread(str(ROOT / 'tests/fixtures/navigation/arena_hub.png'), 0)
        self.assertEqual(self.vision.observe(frame, 'arena'), ('arena_hub', None))
        for mode in ('shop', 'abyss'):
            self.assertEqual(self.vision.observe(frame, mode), (None, None))
        covered = frame.copy()
        covered[250:570, 340:940] = 35
        self.assertEqual(self.vision.observe(covered, 'arena'), (None, None))
        self.assertEqual(self.vision.observe((frame*.8).astype(np.uint8), 'arena'), (None, None))


if __name__ == '__main__':
    unittest.main()
