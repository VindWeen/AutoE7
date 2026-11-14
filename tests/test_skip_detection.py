"""Real screenshot crops: Skip scenes must match; game controls must not."""
import json
from pathlib import Path
import unittest

import cv2
import numpy as np
from app import App, ROOT
from image_matching import tolerant_edges


class SkipDetectionTests(unittest.TestCase):
    def test_story_scenes_and_negative_controls(self):
        detector = App.__new__(App)
        detector.templates = {}
        rules = json.loads((ROOT/'scenarios.json').read_text(encoding='utf-8-sig'))['Đi Map']
        rules = [r for r in rules if r['id'] in ('skip', 'skip_intro', 'skip_text')]
        for name in ('skip_new', 'skip_intro', 'skip_story', 'skip_rose', 'skip_knight', 'confirm', 'team', 'clear', 'mvp'):
            with self.subTest(scene=name):
                frame = np.zeros((720, 1280), dtype=np.uint8)
                crop = cv2.imread(str(ROOT/'tests'/'fixtures'/f'{name}.png'), cv2.IMREAD_GRAYSCALE)
                frame[:90,1140:] = crop
                matched = any(detector.detect(frame, rule) >= rule['threshold'] for rule in rules)
                self.assertEqual(matched, name.startswith('skip_'))

    def test_blank_and_dense_noise_do_not_match(self):
        template = cv2.imread(str(ROOT/'assets'/'skip_text.png'), 0)
        blank = np.zeros((80, 120), np.uint8)
        noise = np.random.default_rng(42).integers(0, 256, (80, 120), dtype=np.uint8)
        for image in (blank, noise):
            self.assertLess(tolerant_edges(image, template, [1]), .93)


if __name__ == '__main__':
    unittest.main()
