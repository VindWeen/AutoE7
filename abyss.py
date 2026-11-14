"""Acknowledged Abyss transitions; no desktop or clock dependencies."""


class AbyssRunner:
    def __init__(self, total):
        self.total = total
        self.count = 0
        self.state = 'ready'
        self.pending = None
        self.previous = None
        self.stable = 0
        self.used = False
        self.available_frames = 0
        self.cast_at = None
        self.target_due = None
        self.cooldown = 0

    def step(self, visible, now):
        """Return (event, point). Only positive, stable observations acknowledge."""
        screen = next((s for s in ('next', 'ready', 'battle') if s in visible), None)
        if screen != 'battle':
            self.available_frames = 0
        self.stable = self.stable + 1 if screen == self.previous else 1
        self.previous = screen
        if self.pending and now - self.pending[3] > 45:
            return 'timeout', None
        if self.stable < 2 or screen is None:
            return None, None
        if self.pending:
            source, sent, attempts, began = self.pending
            expected = 'battle' if source == 'ready' else 'ready'
            if screen == expected:
                self.pending = None
                if source == 'next':
                    self.count += 1
                    self.state = 'ready'
                    if self.total is not None and self.count >= self.total:
                        return 'done', None
                else:
                    self.state = 'battle'
                    self.used = False
                    self.available_frames = 0
                    self.dim_frames = 0
                    self.cast_at = self.target_due = None
                return 'confirmed', None
            if now - began > 45:
                return 'timeout', None
            if screen == source and now - sent >= 4 and attempts < 5:
                self.pending = source, now, attempts + 1, began
                return 'retry_' + source, self.point(source)
            return None, None
        if screen == 'next':
            self.target_due = None
            self.pending = 'next', now, 0, now
            return 'next', self.point('next')
        if screen == 'ready' and self.state == 'ready':
            self.pending = 'ready', now, 0, now
            return 'ready', self.point('ready')
        if screen != 'battle':
            return None, None
        # Allows starting the tool in a battle already in progress.
        self.state = 'battle'
        self.available_frames = (self.available_frames + 1
                                 if 'available' in visible and 'spent' not in visible else 0)
        if self.used:
            # A confirmed cast only consumes the current charge, not the battle.
            # Require a stable ready icon before arming the next charge.
            if self.available_frames < 2 or now < self.cooldown:
                return None, None
            self.used = False
            self.cast_at = None
            self.dim_frames = 0
        if self.cast_at is not None and 'spent' in visible and 'available' not in visible:
            self.dim_frames = getattr(self, 'dim_frames', 0) + 1
            if self.dim_frames >= 3 and now - self.cast_at >= 2:
                self.used = True
                self.available_frames = 0
                self.target_due = None
                return 'guardian_confirmed', None
        else:
            self.dim_frames = 0
        if self.target_due is not None and now >= self.target_due:
            self.target_due = None
            self.cooldown = now + 3
            return 'target', (940, 360)
        if 'available' in visible and now >= self.cooldown and self.target_due is None:
            self.cast_at = now
            self.target_due = now + .8
            return 'guardian', (904, 667)
        return None, None

    @staticmethod
    def point(source):
        return (1150, 665) if source == 'ready' else (1180, 664)
