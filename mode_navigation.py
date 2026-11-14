"""Acknowledged entry paths from the lobby; independent of desktop input."""


class ModeNavigation:
    PATHS = {
        'shop': {'lobby': ('shop', ('click', 58, 330), {'terminal'})},
        'arena': {
            'lobby': ('arena', ('click', 1200, 390), {'arena_hub', 'terminal'}),
            'arena_hub': ('rookie', ('click', 470, 640), {'terminal'}),
        },
        'abyss': {
            'lobby': ('battle', ('click', 1200, 325), {'battle_normal', 'battle_other', 'battle_abyss',
                                                     'abyss_hub', 'abyss_floors', 'terminal'}),
            'battle_other': ('normal', ('click', 120, 120), {'battle_normal', 'battle_abyss'}),
            'battle_normal': ('swipe', ('drag', 1110, 420, 250, 420), {'battle_abyss'}),
            'abyss_hub': ('abyss', ('click', 1140, 245), {'abyss_floors'}),
            'abyss_floors': ('select_team', ('click', 1130, 665), {'terminal'}),
        },
    }

    def __init__(self, mode):
        self.mode = mode
        self.active = True
        self.previous = None
        self.stable = 0
        self.pending = None
        self.last_seen = None

    def step(self, screen, now, point=None):
        """Return (event, action). Unknown frames never acknowledge a click."""
        if not self.active:
            return 'entered', None
        if self.last_seen is None:
            self.last_seen = now
        self.stable = self.stable + 1 if screen == self.previous else 1
        self.previous = screen
        if self.pending and now - self.pending['began'] > 45:
            return 'timeout', None
        if now - self.last_seen > 60:
            return 'timeout', None
        if self.stable < 2 or screen is None:
            return None, None
        self.last_seen = now
        if self.pending:
            pending = self.pending
            if screen in pending['expected']:
                self.pending = None
            elif screen == pending['source'] and now - pending['sent'] >= 4 and pending['attempts'] < 3:
                pending['sent'] = now
                pending['attempts'] += 1
                return pending['event'], pending['action']
            else:
                return None, None
        if screen == 'terminal':
            self.active = False
            return 'entered', None
        if screen == 'idle':
            event, action, expected = 'wake', ('click', 640, 580), {'lobby'}
        elif screen == 'battle_abyss' and self.mode == 'abyss' and point is not None:
            event, action, expected = 'abyss_card', ('click', *point), {'abyss_hub', 'abyss_floors'}
        else:
            route = self.PATHS[self.mode].get(screen)
            if route is None:
                return None, None
            event, action, expected = route
        self.pending = dict(source=screen, event=event, action=action,
                            expected=expected, sent=now, began=now, attempts=0)
        return event, action
