"""Positive visual observations of the English Secret Shop (1280 x 720).

No input or game actions live here. Coordinates are client coordinates, with
window chrome removed by the caller, just like the other scenario detectors.
"""
from pathlib import Path

import cv2
import numpy as np


class ShopVision:
    KINDS = ('friendship', 'covenant', 'mystic')

    def __init__(self, root):
        root = Path(root)
        self.templates = {}
        for name in ('title', *self.KINDS, 'buy_modal', 'refresh_modal',
                     'available', 'sold', 'scroll_top', 'scroll_bottom',
                     'buy_friendship'):
            image = cv2.imread(str(root / 'assets' / ('shop_' + name + '.png')), 0)
            if image is None:
                raise ValueError('Missing Secret Shop template: ' + name)
            self.templates[name] = image

    def _match(self, image, name, scales=(.98, 1., 1.02)):
        best = (-1., (0, 0), None)
        for scale in scales:
            t = cv2.resize(self.templates[name], None, fx=scale, fy=scale)
            h, w = t.shape
            if h > image.shape[0] or w > image.shape[1]:
                continue
            _, score, _, location = cv2.minMaxLoc(cv2.matchTemplate(image, t, cv2.TM_CCOEFF_NORMED))
            if score > best[0]:
                best = (score, location, t)
        return best

    def _positive(self, frame, name, box, threshold=.80, brightness=130,
                  scales=(.98, 1., 1.02)):
        x1, y1, x2, y2 = box
        score, (x, y), t = self._match(frame[y1:y2, x1:x2], name, scales)
        if score < threshold or t is None:
            return False
        patch = frame[y1+y:y1+y+t.shape[0], x1+x:x1+x+t.shape[1]]
        mask = t > min(170, float(t.max()) * .8)
        return bool(mask.any() and patch[mask].mean() > brightness)

    def observe(self, gray_frame):
        """Return shop/modal, named rows and endpoint observations.

        items[*].y is the Buy button center, including sold rows. Only rows
        with their complete item name and Buy control visible are returned.
        list_image is a 64x64 uint8 gray array for settled-frame comparisons;
        fingerprint is the same image quantized to hashable bytes.
        """
        frame = np.asarray(gray_frame)
        if frame.ndim == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        if frame.shape != (720, 1280):
            raise ValueError('ShopVision requires a normalized 1280x720 frame')
        list_image = cv2.resize(frame[80:710, 550:1240], (64, 64), interpolation=cv2.INTER_AREA)
        result = dict(shop=False, modal=None, modal_item=None, items=[], top=False,
                      bottom=False, list_image=list_image, fingerprint=(list_image // 16).tobytes())
        if self._positive(frame, 'buy_modal', (425, 205, 865, 272), .78):
            result['modal'] = 'buy'
            # Popup name is rendered slightly smaller than the shop row name.
            for kind in self.KINDS:
                name = 'buy_friendship' if kind == 'friendship' else kind
                if self._positive(frame, name, (630, 325, 1030, 390), .76,
                                  scales=(.86, .90, .94, .98, 1., 1.02)):
                    result['modal_item'] = kind
                    break
            return result
        if self._positive(frame, 'refresh_modal', (495, 295, 790, 365), .80):
            result['modal'] = 'refresh'
            return result
        if not self._positive(frame, 'title', (45, 8, 235, 64), .80, 160):
            return result
        result['shop'] = True
        search = frame[77:686, 680:1025]
        for kind in self.KINDS:
            score, (x, y), template = self._match(search, kind)
            if score < .79 or template is None:
                continue
            buy_y = int(round(77 + y + template.shape[0] / 2 + 24))
            if not 110 <= buy_y <= 696:
                continue
            box = (1060, buy_y-21, 1150, buy_y+22)
            available = self._positive(frame, 'available', box, .76, 130)
            sold = self._positive(frame, 'sold', box, .76, 25)
            if available or sold:
                result['items'].append(dict(kind=kind, y=buy_y, available=available))
        result['items'].sort(key=lambda row: row['y'])
        strip = frame[80:716, 1227:1246]
        top = self._match(strip, 'scroll_top', (1.,))[0]
        bottom = self._match(strip, 'scroll_bottom', (1.,))[0]
        result['top'] = top > .75 and top > bottom + .08
        result['bottom'] = bottom > .75 and bottom > top + .08
        result['endpoint_source'] = 'scrollbar'
        # The game hides/fades its scrollbar when the pointer is elsewhere.
        # Quantity labels remain visible even for sold items. Use all four
        # row positions, never one item's artwork, as the fallback layout.
        if not result['top'] and not result['bottom']:
            centers = self.quantity_rows(frame)
            aligned = lambda expected: all(any(abs(y-e) <= 10 for y in centers) for e in expected)
            result['top'] = aligned((163, 309, 454, 600))
            result['bottom'] = aligned((236, 381, 526, 671))
            result['endpoint_source'] = 'rows'
        return result

    def quantity_rows(self, frame):
        search = frame[65:715, 1065:1148]
        centers = []
        for name in ('available', 'sold'):
            template = self.templates[name]
            scores = cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED)
            for _ in range(7):
                _, score, _, (x, y) = cv2.minMaxLoc(scores)
                if score < .82:
                    break
                patch = search[y:y+template.shape[0], x:x+template.shape[1]]
                mask = template > min(170, float(template.max()) * .8)
                if mask.any() and patch[mask].mean() > (130 if name == 'available' else 25):
                    center = 65 + y + template.shape[0] // 2
                    if not any(abs(center-c) < 14 for c in centers):
                        centers.append(center)
                scores[max(0, y-14):y+15, :] = -1
        return sorted(centers)
