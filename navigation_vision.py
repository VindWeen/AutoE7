"""Strict menu recognition on normalized frames; observations never send input."""
from pathlib import Path
import json

import cv2
import numpy as np

from episode_vision import EpisodeVision


class NavigationVision:
    def __init__(self, root):
        self.lobby = EpisodeVision(root)
        folder = Path(root) / 'assets' / 'navigation'
        self.patterns = json.loads((folder / 'patterns.json').read_text(encoding='utf-8'))
        self.templates = {}
        for name in self.patterns:
            tpls = [cv2.imread(str(folder / (name + '.png')), 0)]
            alt_path = folder / (name + '_alternate.png')
            if alt_path.is_file():
                alt = cv2.imread(str(alt_path), 0)
                if alt is not None:
                    tpls.append(alt)
            if any(t is None for t in tpls):
                raise ValueError('Missing navigation template: ' + name)
            self.templates[name] = tpls

    def match(self, gray, name):
        spec = self.patterns[name]
        x, y, right, bottom = spec['search']
        region = gray[y:bottom, x:right]
        templates = self.templates[name]
        best, point = 0., None
        for template in templates:
            for scale in (.98, 1., 1.02):
                scaled = cv2.resize(template, None, fx=scale, fy=scale)
                h, w = scaled.shape
                if h > region.shape[0] or w > region.shape[1]:
                    continue
                _, score, _, location = cv2.minMaxLoc(cv2.matchTemplate(region, scaled, cv2.TM_CCOEFF_NORMED))
                lx, ly = location
                patch = region[ly:ly+h, lx:lx+w]
                mean = float(scaled.mean())
                if abs(delta := abs(float(patch.mean()) - mean)) > 20 or (mean > 60 and patch.mean() < .88 * mean):
                    continue
                if score > best:
                    best, point = score, (x+lx+w//2, y+ly+h//2)
        return best, point

    def has(self, gray, *names):
        return all(name in self.patterns and self.match(gray, name)[0] >= .90 for name in names)

    def observe(self, gray, mode):
        if not isinstance(gray, np.ndarray) or gray.shape != (720, 1280) or gray.dtype != np.uint8:
            return None, None
        if self.lobby.score(gray, 'lobby_wake') >= .90:
            return 'idle', None
        if self.lobby.score(gray, 'lobby_episode') >= .90:
            # Require the intended entry label in addition to the lobby scene.
            label = {'shop': 'secret_shop', 'arena': 'arena', 'abyss': 'battle'}[mode]
            if self.has(gray, label):
                return 'lobby', None
        if mode == 'arena' and self.has(gray, 'arena_heading', 'rookie_entry', 'arena_scene'):
            return 'arena_hub', None
        if mode == 'abyss':
            # The tower artwork animates continuously. Use the available-floor
            # label in the list instead of requiring a particular animation frame.
            if self.has(gray, 'abyss_title', 'select_team', 'abyss_floor_icon', 'abyss_floor_available'):
                return 'abyss_floors', None
            if self.has(gray, 'abyss_hub_title', 'abyss_normal', 'challenge_mode', 'abyss_hub_scene'):
                return 'abyss_hub', None
            if self.has(gray, 'battle_heading'):
                if self.has(gray, 'normal_unselected', 'seasonal_selected', 'seasonal_art'):
                    return 'battle_other', None
                if not self.has(gray, 'normal_label', 'seasonal_label', 'normal_selected'):
                    return None, None
                score, point = self.match(gray, 'abyss_card')
                art_score, art_point = self.match(gray, 'abyss_card_art')
                if score >= .90 and art_score >= .90 and abs(art_point[0]-point[0]-76) < 15:
                    return 'battle_abyss', (point[0], 420)
                cards = [self.match(gray, name) for name in
                         ('dimensional', 'spirit_altar', 'hunt', 'labyrinth', 'otherworld')]
                visible = [position for confidence, position in cards if confidence >= .90]
                # A partially moved carousel is also resumable. Require two
                # complete cards, including artwork across the center, so a
                # central modal cannot authorize a swipe behind it.
                if len(visible) >= 2 and any(430 < position[0] < 850 for position in visible):
                    return 'battle_normal', None
        return None, None
