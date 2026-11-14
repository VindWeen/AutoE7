from pathlib import Path
import unittest

import cv2
import numpy as np

from secret_shop_vision import ShopVision


ROOT = Path(__file__).resolve().parent


class ShopVisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vision = ShopVision(ROOT)

    def reference(self, name):
        retained = ROOT / 'tests' / 'fixtures' / ('shop_' + name + '.png')
        self.assertTrue(retained.exists(), 'Missing retained fixture: ' + str(retained))
        # Fixtures already exclude the Windows title/border and are 1280x720.
        return cv2.imread(str(retained), cv2.IMREAD_GRAYSCALE)

    def test_empty_and_dark_screen_cannot_be_shop(self):
        for gray in (0, 40, 150):
            result = self.vision.observe(np.full((720, 1280), gray, np.uint8))
            self.assertFalse(result['shop'])
            self.assertIsNone(result['modal'])
            self.assertEqual(result['items'], [])

    def test_all_eight_user_references(self):
        expected = {
            'top': [('friendship', True)], 'bottom': [],
            'covenant': [('covenant', True)],
            'both': [('friendship', True), ('covenant', True)],
            'mystic': [('mystic', True), ('covenant', True)],
            'sold': [('mystic', False), ('covenant', False)],
            'buy': [], 'refresh': [],
        }
        for name, items in expected.items():
            with self.subTest(name=name):
                result = self.vision.observe(self.reference(name))
                self.assertEqual([(i['kind'], i['available']) for i in result['items']], items)
                self.assertEqual(result['modal'], name if name in ('buy', 'refresh') else None)
                self.assertEqual(result['shop'], name not in ('buy', 'refresh'))
                self.assertEqual(result['top'], name in ('top', 'covenant', 'both', 'mystic', 'sold'))
                self.assertEqual(result['bottom'], name == 'bottom')
                self.assertEqual(result['list_image'].shape, (64, 64))
                if name == 'buy':
                    self.assertEqual(result['modal_item'], 'friendship')

    def test_selected_item_can_be_in_lower_rows(self):
        frame = self.reference('bottom')
        source = self.reference('mystic')
        # Move a fully visible shop row to the sixth row of the bottom view.
        frame[605:714, 550:1240] = source[80:189, 550:1240]
        result = self.vision.observe(frame)
        self.assertEqual([(i['kind'], i['available']) for i in result['items']], [('mystic', True)])
        self.assertGreater(result['items'][0]['y'], 650)

    def test_dim_background_does_not_authorize_purchases(self):
        frame = (self.reference('both').astype(np.float32) * .25).astype(np.uint8)
        result = self.vision.observe(frame)
        self.assertFalse(result['shop'])
        self.assertEqual(result['items'], [])

    def test_popup_item_names_at_smaller_scale(self):
        # Actual Covenant/Mystic purchase popups were not supplied. Exercise
        # their smaller name rendering without claiming a real-game check.
        for kind in ('covenant', 'mystic'):
            with self.subTest(kind=kind):
                frame = self.reference('buy')
                frame[327:389, 630:1030] = 45
                name = cv2.resize(self.vision.templates[kind], None, fx=.9, fy=.9)
                h, w = name.shape
                frame[338:338+h, 645:645+w] = name
                result = self.vision.observe(frame)
                self.assertEqual(result['modal'], 'buy')
                self.assertEqual(result['modal_item'], kind)
                self.assertEqual(result['items'], [])

    def test_unrecognized_modal_item_is_not_inferred_from_background(self):
        frame = self.reference('buy')
        frame[327:389, 630:1030] = 45
        result = self.vision.observe(frame)
        self.assertEqual(result['modal'], 'buy')
        self.assertIsNone(result['modal_item'])
        self.assertFalse(result['shop'])
        self.assertEqual(result['items'], [])

    def test_modal_phrase_removed_cannot_match_background(self):
        for name, box in (('buy', (425, 205, 865, 272)),
                          ('refresh', (495, 295, 790, 365))):
            frame = self.reference(name)
            x1, y1, x2, y2 = box
            frame[y1:y2, x1:x2] = 30
            result = self.vision.observe(frame)
            self.assertIsNone(result['modal'])
            self.assertFalse(result['shop'])
            self.assertEqual(result['items'], [])

    def test_client_frame_size_is_explicit(self):
        with self.assertRaises(ValueError):
            self.vision.observe(np.zeros((747, 1280), np.uint8))

    def test_live_top_with_hidden_scrollbar(self):
        result = self.vision.observe(self.reference('hidden_scrollbar'))
        self.assertTrue(result['shop'])
        self.assertTrue(result['top'])
        self.assertFalse(result['bottom'])
        self.assertEqual(result['endpoint_source'], 'rows')

    def test_endpoints_survive_hidden_scrollbar(self):
        for name in ('top', 'bottom', 'sold'):
            with self.subTest(name=name):
                frame = self.reference(name)
                frame[80:716,1227:1246] = 30
                result = self.vision.observe(frame)
                self.assertEqual(result['top'], name != 'bottom')
                self.assertEqual(result['bottom'], name == 'bottom')
                self.assertEqual(result['endpoint_source'], 'rows')


if __name__ == '__main__':
    unittest.main()
