"""Regression for CLEAR over a different map background."""
import json
import unittest

import cv2
import numpy as np

from app import App, ROOT


class ClearDetectionTests(unittest.TestCase):
    def setUp(self):
        self.detector = App.__new__(App)
        self.detector.templates = {}
        self.rule = next(r for r in json.loads(
            (ROOT / 'scenarios.json').read_text(encoding='utf-8'))['Đi Map']
            if r['id'] == 'clear')

    def test_reported_clear_and_small_position_changes(self):
        frame = cv2.imread(str(ROOT / 'tests/fixtures/map_clear_background.png'), 0)
        for dx, dy in ((0, 0), (-6, 4), (6, -4)):
            with self.subTest(offset=(dx, dy)):
                shifted = cv2.warpAffine(frame, np.float32([[1, 0, dx], [0, 1, dy]]), (1280, 720))
                self.assertGreaterEqual(self.detector.detect(shifted, self.rule), self.rule['threshold'])

    def test_other_screens_and_missing_letters_do_not_match(self):
        for path in (ROOT / 'tests/fixtures').rglob('*.png'):
            frame = cv2.imread(str(path), 0)
            if frame.shape != (720, 1280) or path.name in ('map_clear_background.png', 'map_clear_castle.png', 'map_clear_factory.png'):
                continue
            with self.subTest(scene=path.name):
                self.assertLess(self.detector.detect(frame, self.rule), self.rule['threshold'])
        frame = cv2.imread(str(ROOT / 'tests/fixtures/map_clear_background.png'), 0)
        frame[402:483, 497:791] = 0
        self.assertLess(self.detector.detect(frame, self.rule), self.rule['threshold'])

    def test_factory_clear_with_brightness_and_position_changes(self):
        frame = cv2.imread(str(ROOT / 'tests/fixtures/map_clear_factory.png'), 0)
        for brightness in (-10, 0, 10):
            for dx in (-3, 0, 3):
                with self.subTest(brightness=brightness, dx=dx):
                    changed = np.clip(frame.astype(float) + brightness, 0, 255).astype(np.uint8)
                    changed = cv2.warpAffine(changed, np.float32([[1, 0, dx], [0, 1, 0]]), (1280, 720))
                    self.assertGreaterEqual(self.detector.detect(changed, self.rule), self.rule['threshold'])

    def test_castle_clear(self):
        frame = cv2.imread(str(ROOT / 'tests/fixtures/map_clear_castle.png'), 0)
        self.assertGreaterEqual(self.detector.detect(frame, self.rule), self.rule['threshold'])

    def test_rank_up_ignores_level_number_and_other_screens(self):
        rule = next(r for r in json.loads((ROOT / 'scenarios.json').read_text(
            encoding='utf-8'))['Đi Map'] if r['id'] == 'map_rank_up')
        frame = cv2.imread(str(ROOT / 'tests/fixtures/map_rank_up.png'), 0)
        for erase_number in (False, True):
            if erase_number:
                frame[238:305, 585:690] = 0
            self.assertGreaterEqual(self.detector.detect(frame, rule), rule['threshold'])
        for path in (ROOT / 'tests/fixtures').rglob('*.png'):
            other = cv2.imread(str(path), 0)
            if other.shape == (720, 1280) and path.name != 'map_rank_up.png':
                with self.subTest(scene=path.name):
                    self.assertLess(self.detector.detect(other, rule), rule['threshold'])

    def test_connection_unlock_title_ignores_hero_and_other_screens(self):
        rule = next(r for r in json.loads((ROOT / 'scenarios.json').read_text(
            encoding='utf-8'))['Đi Map'] if r['id'] == 'connection_unlocked')
        frame = cv2.imread(str(ROOT / 'tests/fixtures/map_connection_unlocked.png'), 0)
        self.assertGreaterEqual(self.detector.detect(frame, rule), rule['threshold'])
        frame[260:450, 350:930] = 0  # Hero and description vary by connection.
        self.assertGreaterEqual(self.detector.detect(frame, rule), rule['threshold'])
        for path in (ROOT / 'tests/fixtures').rglob('*.png'):
            other = cv2.imread(str(path), 0)
            if other.shape == (720, 1280) and path.name != 'map_connection_unlocked.png':
                with self.subTest(scene=path.name):
                    self.assertLess(self.detector.detect(other, rule), rule['threshold'])

    def test_hero_friendship_has_priority_over_underlying_mvp(self):
        rules = json.loads((ROOT / 'scenarios.json').read_text(encoding='utf-8'))['Đi Map']
        rule = next(r for r in rules if r['id'] == 'hero_friendship')
        frame = cv2.imread(str(ROOT / 'tests/fixtures/map_hero_friendship.png'), 0)
        for phase in ('result', 'reward'):
            found = next(r for r in rules if phase in r['phases'] and
                         self.detector.detect(frame, r) >= r.get('threshold', .90))
            self.assertEqual(found['id'], 'hero_friendship')
        frame[270:470, 450:1020] = 0  # Friendship levels and rewards vary.
        self.assertGreaterEqual(self.detector.detect(frame, rule), rule['threshold'])
        for path in (ROOT / 'tests/fixtures').rglob('*.png'):
            other = cv2.imread(str(path), 0)
            if other.shape == (720, 1280) and path.name != 'map_hero_friendship.png':
                with self.subTest(scene=path.name):
                    # Arena uses the same friendship overlay as Map; it is
                    # another positive example of this shared popup title.
                    if path == ROOT / 'tests/fixtures/rookie_arena/friendship.png':
                        self.assertGreaterEqual(self.detector.detect(other, rule), rule['threshold'])
                    else:
                        self.assertLess(self.detector.detect(other, rule), rule['threshold'])


if __name__ == '__main__':
    unittest.main()
