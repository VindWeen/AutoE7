"""Observation-driven Rookie Arena automation, independent of desktop input.

Coordinates refer to the 1280 x 720 game client, excluding its title bar.
Purchases are sent once and charged only after the flag balance increases.
"""

import random


class RookieArenaRunner:
    TERMINAL_EVENTS = frozenset({
        'done', 'no_flags', 'all_failed', 'budget_exhausted',
        'cannot_purchase', 'purchase_uncertain', 'timeout',
        'refresh_exhausted', 'refresh_uncertain',
    })
    POINTS = {
        'challenge': (640, 663), 'start': (845, 662),
        'auto': (1124, 34), 'confirm': (1168, 665),
        'open_purchase': (550, 34), 'select_friendship': (490, 370),
        'select_skystone': (780, 370), 'buy_friendship': (745, 550),
        'buy_skystone': (745, 550), 'close_purchase': (530, 550),
        'promotion_confirm': (640, 665), 'reward_close': (640, 550),
        'friendship_close': (755, 590),
        'open_refresh': (880, 115), 'confirm_refresh': (813, 499),
    }
    # Click the opponent name area: x=640 intersects the first hero portrait
    # and can open hero details instead of selecting the opponent row.
    OPPONENT_POINTS = {1: (480, 224), 2: (480, 352), 3: (480, 480)}

    def __init__(self, mode='fixed', preferred=1, refill=False, budget=0, total=None):
        if mode not in ('fixed', 'sequential') or preferred not in (1, 2, 3):
            raise ValueError('Invalid opponent selection')
        if budget < 0 or (total is not None and total < 1):
            raise ValueError('Budget must be nonnegative and total positive')
        self.mode, self.preferred = mode, preferred
        self.refill, self.budget, self.total = refill, budget, total
        self.count = self.spent = 0
        self.wins = self.losses = 0
        self.failed = set()
        self.signature = None
        self.chosen = None
        self.state = 'list'
        self.pending = None
        self.friendship_pending = None
        self.auto_used = False
        self.auto_verified = False
        self.auto_at = None
        self.manual_wait = 0.
        self.manual_seen_at = None
        self.auto_previous = None
        self.auto_stable = 0
        self.battle_at = None
        self.previous = None
        self.stable = 0
        self.last_seen = None
        self.progress_at = None
        self.stopped = None
        self.purchase_currency = None
        self.purchase_balance = None
        self.purchase_at = None
        self.purchase_close_sent = False
        self.purchase_open_point = self.POINTS['open_purchase']
        self.refresh_signature = None
        self.refresh_at = None
        self.refresh_candidate = None
        self.refresh_stable = 0
        self.refresh_failed_rows = set()

    def _stop(self, reason):
        self.stopped = reason
        return reason, None

    def _click(self, event, now, expected=None):
        self.progress_at = now
        if expected:
            self.pending = dict(event=event, sent=now, began=now,
                                attempts=1, expected=expected)
        return event, self.purchase_open_point if event == 'open_purchase' else self.POINTS[event]

    def step(self, obs, now):
        """Return one (event, point) per observation; terminal events persist.

        Screens must be seen twice. A result screen implies a visible Confirm;
        callers may additionally supply confirm_visible=False during animation.
        Unknown resource readings never authorize a purchase.
        """
        if self.stopped:
            return self.stopped, None
        screen = obs.get('screen')
        if screen != 'battle':
            self.manual_seen_at = None
        self.stable = self.stable + 1 if screen == self.previous else 1
        self.previous = screen
        if self.last_seen is None:
            self.last_seen = now
            self.progress_at = now
        if screen is not None:
            self.last_seen = now
        if self.pending and self.friendship_pending is None and now - self.pending['began'] > 45:
            return self._stop('timeout')
        if self.state == 'buy_wait' and now - self.purchase_at > 20:
            return self._stop('purchase_uncertain')
        if self.state in ('refresh', 'refresh_wait') and now-self.refresh_at > 45:
            return self._stop('refresh_uncertain')
        if now - self.last_seen > 45:
            return self._stop('timeout')
        if self.state != 'battle' and now - self.progress_at > 60:
            return self._stop('timeout')
        if self.stable < 2 or screen is None:
            return None, None
        if screen == 'list' and obs.get('purchase_open_point') is not None:
            self.purchase_open_point = obs['purchase_open_point']

        if self.state == 'refresh_wait':
            signature=obs.get('signature')
            # Portrait animation can produce a different hash on each frame;
            # it need not repeat exactly to prove departure from the old list.
            # Clearing three visible defeat rows is also positive evidence,
            # even when the new teams share enough portraits to retain a hash.
            cleared=self.refresh_failed_rows == {1,2,3} and not obs.get('failed')
            changed=(screen == 'list' and signature is not None
                     and (signature != self.refresh_signature or cleared)
                     and not obs.get('failed'))
            self.refresh_stable=self.refresh_stable+1 if changed else 0
            self.refresh_candidate=signature if changed else None
            if self.refresh_stable >= 2:
                self.failed.clear()
                self.chosen=None
                self.signature=signature
                self.state='list'
                self.progress_at=now
                return 'refreshed', None
            return None, None  # Never resend Confirm: it can spend Gold.

        if screen == 'refresh' and self.state == 'refresh':
            remaining=obs.get('refresh_remaining')
            if obs.get('refresh_free') is not True:
                if remaining == 0:
                    return self._stop('refresh_exhausted')
                if remaining is None or not 0 < remaining <= 30:
                    return None, None
            if obs.get('refresh_confirm_visible') is not True:
                return None, None
            self.state='refresh_wait'
            self.refresh_at=now
            return self._click('confirm_refresh',now)

        # Friendship notifications interrupt the result flow. Do not replace
        # the pending action or count a battle just for closing this overlay.
        if self.friendship_pending is not None:
            popup = self.friendship_pending
            if now-popup['began'] > 45:
                return self._stop('timeout')
            if screen == 'friendship':
                if now-popup['sent'] >= 4 and popup['attempts'] < 5:
                    popup['sent'] = now
                    popup['attempts'] += 1
                    return self._click('friendship_close', now)
                return None, None
            self.friendship_pending = None
            self.progress_at = now
            if self.pending is not None:
                self.pending['began'] = self.pending['sent'] = now
        if screen == 'friendship' and (self.state in ('battle', 'victory', 'defeat')):
            self.friendship_pending = dict(sent=now, began=now, attempts=1)
            return self._click('friendship_close', now)

        if self.state == 'buy_wait':
            flags = obs.get('flags')
            if flags is not None and flags >= self.purchase_balance + 5:
                if self.purchase_currency == 'skystone':
                    self.spent += 30
                self.state = 'list'
                if screen == 'purchase':
                    return self._click('close_purchase', now, 'list')
                return 'purchased', None
            if (screen == 'purchase' and now - self.purchase_at >= 3
                    and not self.purchase_close_sent):
                self.purchase_close_sent = True
                return self._click('close_purchase', now)
            return None, None  # Never resend an unacknowledged Buy.

        if self.pending:
            p = self.pending
            return_events = ('confirm', 'promotion_confirm', 'reward_close')
            if p['event'] in return_events and self.state == 'victory':
                # Keep the original result uncounted until the actual list
                # returns, including optional promotion/reward screens.
                if screen == 'promotion' and p['event'] != 'promotion_confirm':
                    return self._click('promotion_confirm', now, 'list')
                if screen == 'promotion_rewards' and p['event'] != 'reward_close':
                    return self._click('reward_close', now, 'list')
            if (p['event'] == 'challenge' and screen == 'list'
                    and obs.get('signature') is not None
                    and self.signature is not None
                    and obs['signature'] != self.signature
                    and not obs.get('failed')):
                self.pending = None
                self.state = 'list'
                self.failed.clear()
                return 'confirmed', None
            if screen == p['expected']:
                self.pending = None
                self.progress_at = now
                if p['event'] in return_events:
                    self.count += 1
                    if self.state == 'victory':
                        self.wins += 1
                    elif self.state == 'defeat':
                        self.losses += 1
                    self.state = 'list'
                    if self.total is not None and self.count >= self.total:
                        return self._stop('done')
                elif p['event'] == 'start':
                    self.state = 'battle'
                    self.auto_used = self.auto_verified = False
                    self.auto_at = None
                    self.manual_wait = 0.
                    self.manual_seen_at = None
                    self.auto_previous = None
                    self.auto_stable = 0
                    self.battle_at = now
                elif p['event'] == 'open_purchase':
                    self.state = 'purchase'
                    self.purchase_at = now
                elif p['event'] == 'open_refresh':
                    self.state = 'refresh'
                    self.refresh_at = now
                return 'confirmed', None
            source = {'challenge': 'list', 'start': 'team',
                      'confirm': self.state, 'open_purchase': 'list',
                      'close_purchase': 'purchase', 'promotion_confirm': 'promotion',
                      'reward_close': 'promotion_rewards', 'open_refresh': 'list'}[p['event']]
            if screen == source and now - p['sent'] >= 4 and p['attempts'] < 3:
                if p['event'] == 'confirm' and not obs.get('confirm_visible', True):
                    return None, None
                p['sent'] = now
                p['attempts'] += 1
                return p['event'], self.purchase_open_point if p['event'] == 'open_purchase' else self.POINTS[p['event']]
            return None, None

        if screen in ('victory', 'defeat') and self.state == 'battle':
            if not obs.get('confirm_visible', True):
                return None, None
            if screen == 'victory':
                self.failed.clear()
                self.signature = None
            elif self.chosen:
                self.failed.add(self.chosen)
            self.state = screen
            return self._click('confirm', now, 'list')

        if screen == 'battle' and self.state == 'battle':
            if now - self.battle_at > 1800:
                return self._stop('timeout')
            auto = obs.get('auto_on')
            # Hidden skill controls during enemy turns are not evidence that
            # enabling auto failed. Only count continuously visible manual HUD.
            if auto is False and self.manual_seen_at is not None:
                self.manual_wait += now - self.manual_seen_at
            self.manual_seen_at = now if auto is False else None
            self.auto_stable = self.auto_stable + 1 if auto is not None and auto == self.auto_previous else 1
            self.auto_previous = auto
            if auto is True and self.auto_stable >= 2:
                self.auto_verified = True
            if auto is False and self.auto_stable >= 2:
                self.auto_verified = False
            # A visual observation of auto-on is not a click. If a later,
            # stable manual HUD appears, still enable auto once this battle.
            if not self.auto_used and auto is False and self.auto_stable >= 2:
                self.auto_used = True
                self.auto_at = now
                return self._click('auto', now)
            if not self.auto_verified and (
                    (self.auto_at is not None and now - self.auto_at > 30)
                    or (self.auto_at is None and self.manual_wait > 20)):
                return self._stop('timeout')
            return None, None

        if screen == 'team' and self.state == 'selected':
            return self._click('start', now, 'battle')

        if screen == 'purchase' and self.state == 'purchase':
            if now - self.purchase_at > 20:
                return self._stop('cannot_purchase')
            friendship = obs.get('friendship_available')
            affordable = obs.get('friendship_affordable')
            if friendship is True and affordable is True:
                currency = 'friendship'
            elif friendship is False or affordable is False:
                if self.budget - self.spent < 30:
                    return self._stop('budget_exhausted')
                if obs.get('skystone_affordable') is False:
                    return self._stop('cannot_purchase')
                if obs.get('skystone_affordable') is not True:
                    return None, None
                currency = 'skystone'
            else:
                return None, None
            if obs.get('selected_currency') != currency:
                # Selection is safe to retry, unlike Buy; wait for positive ack.
                if self.purchase_currency != currency or now - self.selection_at >= 3:
                    self.purchase_currency = currency
                    self.selection_at = now
                    return self._click('select_' + currency, now)
                return None, None
            self.purchase_currency = currency
            self.state = 'buy_wait'
            self.purchase_at = now
            self.purchase_close_sent = False
            return self._click('buy_' + currency, now)

        if screen != 'list' or self.state not in ('list', 'select_wait'):
            return None, None
        observed_failed = set(obs.get('failed') or ()) & {1, 2, 3}
        signature = obs.get('signature')
        if signature is not None and self.signature is not None and signature != self.signature:
            # A roster hash may change on returning from defeat. Red rows are
            # stronger evidence that this is still the same opponent batch.
            if not observed_failed:
                self.failed.clear()
                self.state = 'list'
        if signature is not None:
            self.signature = signature
        self.failed.update(observed_failed)
        if self.state == 'select_wait':
            if self.chosen in self.failed:
                self.state = 'list'
            elif (obs.get('selected_opponent') == self.chosen
                  or (obs.get('selected_opponent') is None
                      and obs.get('challenge_enabled') is True)):
                self.state = 'selected'
                return self._click('challenge', now, 'team')
            elif now - self.selection_at >= 4 and self.selection_attempts < 3:
                self.selection_at = now
                self.selection_attempts += 1
                return 'select_' + str(self.chosen), self.OPPONENT_POINTS[self.chosen]
            else:
                return None, None
        remaining = {1, 2, 3} - self.failed
        if not remaining:
            if signature is None:
                return None, None
            self.refresh_signature=signature
            self.refresh_failed_rows=observed_failed.copy()
            self.refresh_candidate=None
            self.refresh_stable=0
            return self._click('open_refresh',now,'refresh')
        flags = obs.get('flags')
        if flags is None:
            return None, None
        if flags <= 0:
            if not self.refill:
                return self._stop('no_flags')
            self.purchase_balance = flags
            return self._click('open_purchase', now, 'purchase')
        if self.mode == 'sequential':
            self.chosen = min(remaining)
        elif self.preferred in remaining:
            self.chosen = self.preferred
        else:
            self.chosen = random.choice(sorted(remaining))
        self.state = 'select_wait'
        self.selection_at = now
        self.selection_attempts = 1
        self.progress_at = now
        return 'select_' + str(self.chosen), self.OPPONENT_POINTS[self.chosen]
