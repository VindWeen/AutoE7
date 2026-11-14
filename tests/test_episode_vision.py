"""Real lobby scenes with private HUD removed; no input to the game."""
from pathlib import Path
import unittest

import cv2
import numpy as np

from episode_vision import EpisodeVision


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests' / 'fixtures'


class EpisodeVisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vision = EpisodeVision(ROOT)

    def frame(self, name):
        return cv2.imread(str(FIXTURES / 'episode' / (name + '.png')), 0)

    def assert_unknown(self, frame):
        for rule in ('lobby_wake', 'lobby_episode'):
            self.assertLess(self.vision.score(frame, rule), .90, rule)

    def test_real_lobby_states_are_mutually_exclusive(self):
        for scene, expected, other in (
            ('idle', 'lobby_wake', 'lobby_episode'),
            ('menu', 'lobby_episode', 'lobby_wake'),
        ):
            frame = self.frame(scene)
            self.assertGreaterEqual(self.vision.score(frame, expected), .90)
            self.assertLess(self.vision.score(frame, other), .90)

    def test_small_brightness_position_and_resampling_drift(self):
        for scene, rule in (('idle', 'lobby_wake'), ('menu', 'lobby_episode')):
            original = self.frame(scene)
            variants = [np.clip(original.astype(float) + delta, 0, 255).astype(np.uint8) for delta in (-8, 8)]
            variants += [cv2.warpAffine(original, np.float32([[1, 0, dx], [0, 1, dy]]), (1280, 720))
                         for dx, dy in ((-2, 2), (2, -2))]
            variants += [cv2.resize(cv2.resize(original, None, fx=scale, fy=scale), (1280, 720))
                         for scale in (.97, 1.03)]
            for index, frame in enumerate(variants):
                with self.subTest(scene=scene, variant=index):
                    self.assertGreaterEqual(self.vision.score(frame, rule), .90)
                    self.assertLess(self.vision.score(frame, 'lobby_episode' if rule == 'lobby_wake' else 'lobby_wake'), .90)

    def test_ready_map_and_real_quit_popup_are_unknown(self):
        for scene in ('ready', 'quit_confirmation'):
            with self.subTest(scene=scene):
                self.assert_unknown(self.frame(scene))

    def test_dimmed_lobbies_and_obscured_scene_are_unknown(self):
        for scene in ('idle', 'menu'):
            original = self.frame(scene)
            for gain in (.35, .60, .75, .85):
                with self.subTest(scene=scene, gain=gain):
                    self.assert_unknown((original * gain).astype(np.uint8))
            # A central opaque modal must not authorize navigation even when
            # unchanged background is visible on both edges of the screen.
            modal = original.copy()
            modal[260:550, 350:930] = 60
            self.assert_unknown(modal)
            truncated = original.copy()
            truncated[430:] = 0
            self.assert_unknown(truncated)

    def test_all_existing_non_lobby_fixtures_are_negative(self):
        for path in FIXTURES.rglob('*.png'):
            if path.parent.name == 'episode':
                continue
            with self.subTest(fixture=path.name):
                frame = cv2.imread(str(path), 0)
                if frame.shape != (720, 1280):
                    frame = cv2.resize(frame, (1280, 720))
                self.assert_unknown(frame)

    def test_invalid_empty_and_noise_frames_are_unknown(self):
        for frame in (None, np.zeros((360, 640), np.uint8),
                      np.zeros((720, 1280), np.uint8),
                      np.full((720, 1280), 255, np.uint8),
                      np.random.default_rng(71).integers(0, 256, (720, 1280), dtype=np.uint8)):
            self.assert_unknown(frame)
        self.assertEqual(self.vision.score(self.frame('idle'), 'unknown_rule'), 0.)


if __name__ == '__main__':
    unittest.main()
