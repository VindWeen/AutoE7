"""Guardian artwork variants use the same Abyss observation."""
import json
import unittest

import cv2
import numpy as np

from app import App, ROOT


class AbyssDetectionTests(unittest.TestCase):
    def setUp(self):
        self.detector = App.__new__(App)
        self.detector.templates = {}
        self.rules = json.loads((ROOT / 'scenarios.json').read_text(
            encoding='utf-8'))['Abyss (Tháp)']
        self.available = [r for r in self.rules if r.get(
            'observation', r['id'].removeprefix('abyss_')) == 'available']

    def detects_available(self, frame):
        return any(self.detector.detect(frame, r) >= r['threshold']
                   for r in self.available)

    def test_alternate_guardian_on_both_reported_screens(self):
        for index in (1, 2):
            frame = cv2.imread(str(ROOT / f'tests/fixtures/abyss_guardian_alternate_{index}.png'), 0)
            for dx, dy in ((0, 0), (-3, 2), (3, -2)):
                with self.subTest(index=index, offset=(dx, dy)):
                    shifted = cv2.warpAffine(frame, np.float32(
                        [[1, 0, dx], [0, 1, dy]]), (1280, 720))
                    self.assertTrue(self.detects_available(shifted))

    def test_original_guardian_still_matches_and_spent_does_not(self):
        for name, expected in (('available', True), ('spent', False)):
            rule = next(r for r in self.rules if r['id'] == 'abyss_' + name)
            frame = np.zeros((720, 1280), dtype=np.uint8)
            template = cv2.imread(str(ROOT / 'assets' / rule['image']), 0)
            x, y = rule['rect'][:2]
            h, w = template.shape
            frame[y:y+h, x:x+w] = template
            self.assertEqual(self.detects_available(frame), expected)

    def test_missing_or_heavily_dimmed_alternate_icon_does_not_match(self):
        frame = cv2.imread(str(ROOT / 'tests/fixtures/abyss_guardian_alternate_2.png'), 0)
        frame[610:720, 840:960] = 0
        self.assertFalse(self.detects_available(frame))
        frame = cv2.imread(str(ROOT / 'tests/fixtures/abyss_guardian_alternate_2.png'), 0)
        self.assertFalse(self.detects_available((frame * .2).astype(np.uint8)))


if __name__ == '__main__':
    unittest.main()
