"""Conservative lobby observations on normalized grayscale 1280x720 frames.

These observations never send input. An unknown or dimmed scene returns zero.
"""
from pathlib import Path

import cv2
import numpy as np


class EpisodeVision:
    THEMES = [
        {
            'anchors': {
                'lobby_anchor': (180, 145, 325, 255),
                'lobby_barrels': (790, 145, 900, 235),
                'lobby_floor': (490, 595, 700, 685),
                'lobby_table': (470, 450, 540, 510),
                'lobby_counter': (780, 260, 850, 300),
            },
            'idle': {
                'idle_episode': (1130, 165, 1240, 210),
                'idle_battle': (1155, 300, 1240, 365),
                'idle_shop': (1140, 475, 1240, 545),
            },
            'labels': {
                'episode_button': (1126, 170, 1238, 202),
                'battle_label': (1164, 310, 1242, 340),
            },
            'prefix_menu': 'menu_',
        },
        {
            'anchors': {
                'rabbit_chandelier': (570, 40, 710, 130),
                'rabbit_arch_l': (175, 190, 235, 260),
                'rabbit_stairs_r': (965, 335, 1045, 405),
                'rabbit_heart': (590, 420, 690, 490),
                'rabbit_carpet': (430, 600, 530, 670),
            },
            'idle': {
                'rabbit_idle_episode': (1130, 165, 1240, 210),
                'rabbit_idle_battle': (1155, 300, 1240, 365),
                'rabbit_idle_shop': (1140, 475, 1240, 545),
            },
            'labels': {
                'rabbit_episode_button': (1126, 170, 1238, 202),
                'rabbit_battle_label': (1164, 310, 1242, 340),
            },
            'prefix_menu': 'menu_',
        },
    ]
    ANCHORS = THEMES[0]['anchors']
    IDLE = THEMES[0]['idle']
    LABELS = THEMES[0]['labels']

    def __init__(self, root):
        self.templates = {}
        names = set()
        for theme in self.THEMES:
            names.update(theme['anchors'])
            names.update(theme['prefix_menu'] + name for name in theme['anchors'])
            names.update(theme['idle'])
            names.update(theme['labels'])
        for name in names:
            template = cv2.imread(str(Path(root) / 'assets' / 'episode' / (name + '.png')), 0)
            if template is None:
                raise ValueError('Missing Episode template: ' + name)
            self.templates[name] = template

    def _match(self, gray, name, box):
        x, y, right, bottom = box
        template = self.templates[name]
        region = gray[max(0, y-4):min(720, bottom+4), max(0, x-4):min(1280, right+4)]
        best = 0.
        for scale in (.98, 1., 1.02):
            scaled = cv2.resize(template, None, fx=scale, fy=scale)
            h, w = scaled.shape
            if h > region.shape[0] or w > region.shape[1]:
                continue
            _, correlation, _, location = cv2.minMaxLoc(cv2.matchTemplate(region, scaled, cv2.TM_CCOEFF_NORMED))
            lx, ly = location
            patch = region[ly:ly+h, lx:lx+w]
            # Correlation alone accepts a modal's dimmed background. Preserve
            # absolute luminance as well as scene shape, allowing modest drift.
            delta = float(patch.mean()) - float(scaled.mean())
            mean = float(scaled.mean())
            if abs(delta) > 22 or (mean >= 60 and float(patch.mean()) < .86 * mean):
                continue
            best = max(best, correlation)
        return max(0., min(1., best))

    def score(self, gray, rule_id):
        """Return 0..1; callers authorize a lobby action only at >= .90."""
        if rule_id not in ('lobby_wake', 'lobby_episode'):
            return 0.
        if not isinstance(gray, np.ndarray) or gray.shape != (720, 1280) or gray.dtype != np.uint8:
            return 0.
        return max(self._score_theme(gray, rule_id, theme) for theme in self.THEMES)

    def _score_theme(self, gray, rule_id, theme):
        prefix = theme['prefix_menu'] if rule_id == 'lobby_episode' else ''
        anchor = min(self._match(gray, prefix + name, box) for name, box in theme['anchors'].items())
        if anchor < .90:
            return 0.
        labels = min(self._match(gray, name, box) for name, box in theme['labels'].items())
        if rule_id == 'lobby_episode':
            return min(anchor, labels)
        # Wake only when the right-hand background is actually unobstructed.
        # Explicitly exclude the visible menu even if its labels drift slightly.
        if labels >= .75:
            return 0.
        return min(anchor, *(self._match(gray, name, box) for name, box in theme['idle'].items()))
