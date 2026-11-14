import unittest
from rookie_arena import RookieArenaRunner


class ArenaTests(unittest.TestCase):
    def test_fresh_run_adopts_team_and_battle_without_challenging_again(self):
        r = RookieArenaRunner(total=1)
        self.assertEqual(self.see(r, 'team'), 'start')
        self.assertEqual(r.count, 0)
        self.assertEqual(self.see(r, 'battle', auto_on=True), 'confirmed')
        self.assertEqual(self.finish(r, victory=True), 'done')
        self.assertEqual((r.count, r.wins), (1, 1))
        r = RookieArenaRunner()
        self.assertIsNone(self.see(r, 'battle', auto_on=True))
        self.assertEqual(r.state, 'battle')
        self.assertIsNone(self.see(r, 'battle', auto_on=True))
        self.assertTrue(r.auto_verified)
        self.assertFalse(r.auto_used)

    def test_fresh_run_results_count_once_at_list(self):
        for screen, wins, losses in (('victory', 1, 0), ('defeat', 0, 1),
                                      ('promotion', 1, 0), ('promotion_rewards', 1, 0)):
            with self.subTest(screen=screen):
                r = RookieArenaRunner(total=1)
                self.assertIn(self.see(r, screen),
                              ('confirm', 'promotion_confirm', 'reward_close'))
                self.assertEqual(r.count, 0)
                self.assertEqual(self.see(r, 'list', flags=4), 'done')
                self.assertEqual((r.count, r.wins, r.losses), (1, wins, losses))
                self.assertEqual(self.see(r, 'list', flags=4), 'done')
                self.assertEqual(r.count, 1)

    def test_resumed_result_waits_for_visible_confirm(self):
        r = RookieArenaRunner()
        self.assertIsNone(self.see(r, 'victory', confirm_visible=False))
        self.assertEqual(r.state, 'battle')
        self.assertEqual(self.see(r, 'victory', confirm_visible=True), 'confirm')

    def test_fresh_friendship_can_resume_result_or_list(self):
        for next_screen in ('victory', 'list'):
            with self.subTest(next_screen=next_screen):
                r = RookieArenaRunner(total=1)
                self.assertEqual(self.see(r, 'friendship'), 'friendship_close')
                self.assertEqual(r.count, 0)
                if next_screen == 'victory':
                    self.assertEqual(self.see(r, 'victory'), 'confirm')
                    self.assertEqual(self.see(r, 'list', flags=4), 'done')
                else:
                    self.assertEqual(self.see(r, 'list', flags=4), 'select_1')
                    self.assertEqual((r.count, r.wins, r.losses), (0, 0, 0))

    def test_fresh_purchase_closes_without_repeating_or_charging_prior_buy(self):
        for refill in (False, True):
            with self.subTest(refill=refill):
                r = RookieArenaRunner(refill=refill, budget=30)
                self.assertEqual(self.see(r, 'purchase', flags=5,
                    friendship_available=False, skystone_affordable=True,
                    selected_currency='skystone'), 'close_purchase')
                self.assertIsNone(self.see(r, 'purchase', flags=5))
                self.assertEqual(self.see(r, 'list', flags=5), 'confirmed')
                self.assertEqual(r.spent, 0)
                self.assertEqual(self.see(r, 'list', flags=5), 'select_1')

    def test_resumed_purchase_rechecks_current_refill_policy_from_list(self):
        for refill, expected in ((False, 'no_flags'), (True, 'open_purchase')):
            with self.subTest(refill=refill):
                r = RookieArenaRunner(refill=refill, budget=30)
                self.assertEqual(self.see(r, 'purchase'), 'close_purchase')
                self.assertEqual(self.see(r, 'list', flags=0), 'confirmed')
                self.assertEqual(self.see(r, 'list', flags=0), expected)
                self.assertEqual(r.spent, 0)

    def test_fresh_refresh_cancels_before_reconsidering_failed_roster(self):
        for free in (True, False):
            with self.subTest(free=free):
                r = RookieArenaRunner()
                self.assertEqual(self.see(r, 'refresh', refresh_free=free,
                    refresh_remaining=30, refresh_confirm_visible=True), 'cancel_refresh')
                self.assertEqual(r.pending['expected'], 'list')
                self.assertEqual(self.see(r, 'list', flags=3, signature='old',
                                          failed={1, 2, 3}), 'confirmed')
                self.assertEqual(self.see(r, 'list', flags=3, signature='old',
                                          failed={1, 2, 3}), 'open_refresh')
                self.assertEqual(r.count, 0)

    def test_unknown_start_waits_and_recovered_modal_retries_are_bounded(self):
        r = RookieArenaRunner()
        self.assertIsNone(self.see(r, None))
        self.assertTrue(r.resume_pending)
        self.assertEqual(self.see(r, 'team'), 'start')
        for screen, event in (('purchase', 'close_purchase'), ('refresh', 'cancel_refresh')):
            r = RookieArenaRunner()
            self.assertEqual(self.see(r, screen), event)
            began = r.pending['began']
            self.assertEqual(r.step({'screen': screen}, began + 4.1)[0], event)
            self.assertEqual(r.step({'screen': screen}, began + 8.2)[0], event)
            self.assertIsNone(r.step({'screen': screen}, began + 12)[0])
            self.assertEqual(r.step({'screen': screen}, began + 46)[0], 'timeout')
            self.assertEqual((r.count, r.spent), (0, 0))

    def test_refresh_verification_accepts_animated_roster_or_cleared_defeats(self):
        for initial_rows,signatures in (({1,2,3},('old','old')),
                                        (set(),('new-animation-a','new-animation-b'))):
            r=RookieArenaRunner()
            r.state='refresh_wait'; r.refresh_at=0
            r.refresh_signature='old'
            r.refresh_failed_rows=initial_rows
            r.failed={1,2,3}
            r.step(dict(screen='list',signature=signatures[0],failed=set()),0)
            self.assertIsNone(r.step(dict(screen='list',signature=signatures[0],failed=set()),1)[0])
            self.assertEqual(r.step(dict(screen='list',signature=signatures[1],failed=set()),2)[0],'refreshed')
            self.assertEqual(r.failed,set())
        r=RookieArenaRunner()
        r.state='refresh_wait'; r.refresh_at=0; r.refresh_signature='old'
        for now in (0,1,2,3):
            self.assertIsNone(r.step(dict(screen='list',signature='old',failed=set()),now)[0])
        self.assertEqual(r.state,'refresh_wait')

    def test_win_loss_totals_commit_at_list_and_reset_each_run(self):
        runner=RookieArenaRunner()
        runner.state='battle'; runner.battle_at=0; runner.chosen=1
        defeat=dict(screen='defeat',confirm_visible=True)
        runner.step(defeat,0)
        self.assertEqual(runner.step(defeat,1)[0],'confirm')
        self.assertEqual((runner.wins,runner.losses,runner.count),(0,0,0))
        runner.step(defeat,5)
        listing=dict(screen='list',flags=4,signature='one',failed={1})
        runner.step(listing,6)
        runner.step(listing,7)
        self.assertEqual((runner.wins,runner.losses,runner.count),(0,1,1))
        runner.state='battle'; runner.battle_at=8; runner.chosen=2
        victory=dict(screen='victory',confirm_visible=True)
        runner.step(victory,8)
        self.assertEqual(runner.step(victory,9)[0],'confirm')
        promotion=dict(screen='promotion')
        runner.step(promotion,10)
        runner.step(promotion,11)
        rewards=dict(screen='promotion_rewards')
        runner.step(rewards,12)
        runner.step(rewards,13)
        self.assertEqual((runner.wins,runner.losses,runner.count),(0,1,1))
        listing=dict(screen='list',flags=3,signature='two',failed=set())
        runner.step(listing,14)
        runner.step(listing,15)
        runner.step(listing,16)
        self.assertEqual((runner.wins,runner.losses,runner.count),(1,1,2))
        fresh=RookieArenaRunner()
        self.assertEqual((fresh.wins,fresh.losses,fresh.count),(0,0,0))

    def test_friendship_popup_then_victory_counts_only_at_list(self):
        r = RookieArenaRunner(total=1)
        self.now = 0
        self.enter(r)
        self.assertEqual(self.see(r, 'friendship'), 'friendship_close')
        self.assertEqual(r.state, 'battle')
        self.assertEqual(r.count, 0)
        self.assertIsNone(self.see(r, 'friendship'))
        self.assertEqual(self.see(r, 'victory'), 'confirm')
        self.assertEqual(r.count, 0)
        self.assertEqual(self.see(r, 'list', flags=4), 'done')
        self.assertEqual(r.count, 1)

    def test_friendship_preserves_pending_confirm_and_bounded_retries(self):
        r = RookieArenaRunner()
        self.now = 0
        self.enter(r)
        self.see(r, 'victory')
        original = r.pending
        self.assertEqual(self.see(r, 'friendship'), 'friendship_close')
        self.assertIs(r.pending, original)
        began = r.friendship_pending['began']
        for attempt in range(1, 5):
            self.assertEqual(r.step({'screen': 'friendship'}, began+4.1*attempt)[0], 'friendship_close')
        self.assertIsNone(r.step({'screen': 'friendship'}, began+25)[0])
        self.assertEqual(r.step({'screen': 'friendship'}, began+46)[0], 'timeout')
        self.assertEqual(r.count, 0)

    def test_friendship_resumes_existing_victory_confirmation(self):
        r = RookieArenaRunner(total=1)
        self.now = 0
        self.enter(r)
        self.see(r, 'victory')
        original = r.pending
        self.assertEqual(self.see(r, 'friendship'), 'friendship_close')
        self.assertIsNone(self.see(r, 'victory'))
        self.assertIsNone(r.friendship_pending)
        self.assertIs(r.pending, original)
        self.assertEqual(self.see(r, 'list', flags=4), 'done')
        self.assertEqual(r.count, 1)

    def setUp(self):
        self.now = 0

    def see(self, runner, screen, **fields):
        self.now += 1
        obs = dict(screen=screen, **fields)
        first = runner.step(obs, self.now)[0]
        self.now += .2
        second = runner.step(obs, self.now)[0]
        return first or second

    def enter(self, runner, **fields):
        fields = dict(flags=5, signature='a', **fields)
        selection = self.see(runner, 'list', **fields)
        self.assertTrue(selection.startswith('select_'))
        self.assertEqual(self.see(runner, 'list', selected_opponent=runner.chosen, **fields), 'challenge')
        self.assertEqual(self.see(runner, 'team'), 'confirmed')
        self.assertEqual(self.see(runner, 'team'), 'start')
        self.assertEqual(self.see(runner, 'battle', auto_on=False), 'confirmed')
        return selection

    def finish(self, runner, victory=False, **fields):
        self.assertEqual(self.see(runner, 'victory' if victory else 'defeat'), 'confirm')
        return self.see(runner, 'list', flags=4, signature='a', **fields)

    def test_opponent_selection_and_retry_avoid_profile_and_hero_portraits(self):
        for row, top in ((1, 172), (2, 300), (3, 428)):
            with self.subTest(row=row):
                r = RookieArenaRunner(preferred=row)
                obs = dict(screen='list', flags=3, signature='same',
                           selected_opponent=None, challenge_enabled=False)
                r.step(obs, 0)
                event, point = r.step(obs, .4)
                self.assertEqual(event, 'select_' + str(row))
                # Name area lies between the player profile and hero portraits.
                self.assertTrue(400 < point[0] < 560)
                self.assertTrue(top + 10 < point[1] < top + 95)
                retry_event, retry_point = r.step(obs, 5)
                self.assertEqual((retry_event, retry_point), (event, point))
                self.assertEqual(r.state, 'select_wait')
                obs['selected_opponent'] = row
                self.assertEqual(r.step(obs, 6)[0], 'challenge')

    def test_auto_once_and_limit_after_confirm(self):
        r = RookieArenaRunner(total=1)
        self.enter(r)
        self.assertEqual(self.see(r, 'battle', auto_on=False), 'auto')
        self.assertIsNone(self.see(r, 'battle', auto_on=False))
        self.assertIsNone(self.see(r, 'battle', auto_on=True))
        self.assertEqual(self.finish(r, victory=True), 'done')
        self.assertEqual(r.count, 1)

    def test_sequential_losses_refresh_after_three_confirmed(self):
        r = RookieArenaRunner(mode='sequential')
        for row in (1, 2, 3):
            fields = dict(failed=set(range(1, row)))
            self.assertEqual(self.enter(r, **fields), 'select_' + str(row))
            self.assertEqual(self.finish(r, failed=set(range(1, row + 1))), 'confirmed')
        self.assertEqual(self.see(r, 'list', flags=2, signature='a', failed={1, 2, 3}), 'open_refresh')
        self.assertEqual(r.count, 3)

    def test_fixed_avoids_failed_and_win_resets(self):
        r = RookieArenaRunner(preferred=3)
        self.assertEqual(self.enter(r), 'select_3')
        self.finish(r, failed={3})
        selection = self.enter(r, failed={3})
        self.assertIn(selection, ('select_1', 'select_2'))
        self.finish(r, victory=True)
        self.assertEqual(self.see(r, 'list', flags=3, signature='new'), 'select_3')

    def purchase(self, r, **fields):
        self.assertEqual(self.see(r, 'list', flags=0), 'open_purchase')
        self.assertEqual(self.see(r, 'purchase', **fields), 'confirmed')
        return self.see(r, 'purchase', **fields)

    def test_friendship_priority_and_verified_charge(self):
        r = RookieArenaRunner(refill=True, budget=60)
        fields = dict(friendship_available=True, friendship_affordable=True,
                      skystone_affordable=True, selected_currency='skystone')
        self.assertEqual(self.purchase(r, **fields), 'select_friendship')
        fields['selected_currency'] = 'friendship'
        self.assertEqual(self.see(r, 'purchase', **fields), 'buy_friendship')
        self.assertIsNone(self.see(r, 'purchase', flags=0, **fields))
        self.assertEqual(self.see(r, 'list', flags=5), 'purchased')
        self.assertEqual(r.spent, 0)

    def test_sky_fallback_budget_and_no_duplicate_buy(self):
        r = RookieArenaRunner(refill=True, budget=30)
        fields = dict(friendship_available=True, friendship_affordable=False,
                      skystone_affordable=True, selected_currency='skystone')
        self.assertEqual(self.purchase(r, **fields), 'buy_skystone')
        self.assertEqual(r.spent, 0)
        self.assertIsNone(self.see(r, 'purchase', flags=0, **fields))
        self.assertEqual(self.see(r, 'list', flags=5), 'purchased')
        self.assertEqual(r.spent, 30)
        self.assertEqual(self.purchase(r, **fields), 'budget_exhausted')

    def test_unknown_affordability_never_buys(self):
        r = RookieArenaRunner(refill=True, budget=100)
        fields = dict(friendship_available=False, skystone_affordable=None,
                      selected_currency='skystone')
        self.assertIsNone(self.purchase(r, **fields))
        self.assertEqual(r.spent, 0)
        self.assertEqual(r.step(dict(screen='purchase', **fields), self.now + 21)[0], 'cannot_purchase')

    def test_purchase_uncertain_stops_without_charge(self):
        r = RookieArenaRunner(refill=True, budget=30)
        fields = dict(friendship_available=False, skystone_affordable=True,
                      selected_currency='skystone')
        self.purchase(r, **fields)
        self.assertEqual(r.step(dict(screen='list', flags=0), self.now + 21)[0], 'purchase_uncertain')
        self.assertEqual(r.spent, 0)

    def test_modal_after_buy_closes_once_then_verifies_balance(self):
        r = RookieArenaRunner(refill=True, budget=30)
        fields = dict(friendship_available=False, skystone_affordable=True,
                      selected_currency='skystone')
        self.assertEqual(self.purchase(r, **fields), 'buy_skystone')
        bought_at = r.purchase_at
        self.assertEqual(r.step(dict(screen='purchase', flags=None), bought_at + 3)[0], 'close_purchase')
        self.assertIsNone(r.step(dict(screen='purchase', flags=None), bought_at + 7)[0])
        self.assertEqual(r.state, 'buy_wait')
        self.assertEqual(r.spent, 0)
        r.step(dict(screen='list', flags=5), bought_at + 8)
        self.assertEqual(r.step(dict(screen='list', flags=5), bought_at + 8.2)[0], 'purchased')
        self.assertEqual(r.spent, 30)

    def test_modal_close_keeps_original_uncertain_timeout(self):
        r = RookieArenaRunner(refill=True, budget=30)
        fields = dict(friendship_available=False, skystone_affordable=True,
                      selected_currency='skystone')
        self.purchase(r, **fields)
        bought_at = r.purchase_at
        r.step(dict(screen='purchase'), bought_at + 3)
        self.assertEqual(r.step(dict(screen='purchase'), bought_at + 21)[0], 'purchase_uncertain')
        self.assertEqual(r.spent, 0)

    def test_refresh_resets_but_red_roster_change_does_not(self):
        r = RookieArenaRunner(mode='sequential')
        r.failed = {1}
        r.signature = 'old'
        self.assertEqual(self.see(r, 'list', flags=3, signature='changed', failed={1}), 'select_2')
        r.state = 'list'
        self.assertEqual(self.see(r, 'list', flags=3, signature='fresh', failed=set()), 'select_1')

    def test_stop_without_flags_and_missing_transition(self):
        r = RookieArenaRunner()
        self.assertEqual(self.see(r, 'list', flags=0), 'no_flags')
        r = RookieArenaRunner()
        self.see(r, 'list', flags=5)
        self.see(r, 'list', flags=5, challenge_enabled=True)
        self.assertEqual(r.step({'screen': None}, self.now + 46)[0], 'timeout')

    def test_selection_requires_ack_and_refresh_cancels_pending_challenge(self):
        r = RookieArenaRunner()
        self.assertEqual(self.see(r, 'list', flags=5, signature='old'), 'select_1')
        self.assertIsNone(self.see(r, 'list', flags=5, signature='old', challenge_enabled=False))
        self.assertEqual(self.see(r, 'list', flags=5, signature='old', selected_opponent=1), 'challenge')
        self.assertEqual(self.see(r, 'list', flags=5, signature='new'), 'confirmed')
        self.assertIsNone(r.pending)
        self.assertEqual(r.state, 'select_wait')

    def test_already_auto_never_toggles_and_result_requires_confirm(self):
        r = RookieArenaRunner()
        self.enter(r)
        self.assertIsNone(self.see(r, 'battle', auto_on=True))
        self.assertIsNone(self.see(r, 'defeat', confirm_visible=False))
        self.assertEqual(r.count, 0)
        self.assertEqual(self.see(r, 'defeat', confirm_visible=True), 'confirm')

    def test_auto_on_observation_does_not_consume_single_click(self):
        r = RookieArenaRunner()
        self.enter(r)
        self.assertIsNone(self.see(r, 'battle', auto_on=True))
        self.assertTrue(r.auto_verified)
        self.assertFalse(r.auto_used)
        # Regression: an earlier false-positive True must not permanently
        # suppress the one click when manual skills are now clearly visible.
        self.assertEqual(self.see(r, 'battle', auto_on=False), 'auto')
        self.assertFalse(r.auto_verified)
        self.assertIsNone(self.see(r, 'battle', auto_on=False))
        self.assertIsNone(self.see(r, 'battle', auto_on=True))
        self.assertIsNone(self.see(r, 'battle', auto_on=False))
        self.assertTrue(r.auto_used)

    def test_auto_requires_two_matching_hud_observations(self):
        r = RookieArenaRunner()
        r.state = 'battle'
        r.battle_at = 0
        for now, auto in enumerate((None, False, True, False, None, True, True)):
            self.assertIsNone(r.step({'screen': 'battle', 'auto_on': auto}, now)[0])
        self.assertTrue(r.auto_verified)
        self.assertFalse(r.auto_used)
        self.assertIsNone(r.step({'screen': 'battle', 'auto_on': False}, 7)[0])
        self.assertEqual(r.step({'screen': 'battle', 'auto_on': False}, 8)[0], 'auto')

    def test_unacknowledged_auto_click_times_out_without_second_toggle(self):
        r = RookieArenaRunner()
        self.enter(r)
        self.assertEqual(self.see(r, 'battle', auto_on=False), 'auto')
        sent_at = r.auto_at
        self.assertIsNone(r.step({'screen': 'battle', 'auto_on': False}, sent_at+5)[0])
        self.assertEqual(r.step({'screen': 'battle', 'auto_on': False}, sent_at+31)[0], 'timeout')

    def test_enemy_opening_and_hidden_skills_do_not_expire_auto_wait(self):
        r = RookieArenaRunner()
        r.state='battle'
        r.battle_at=0
        for now in (0,1,20,31,45):
            self.assertIsNone(r.step({'screen':'battle','auto_on':None},now)[0])
        self.assertIsNone(r.step({'screen':'battle','auto_on':False},46)[0])
        self.assertIsNone(r.step({'screen':'battle','auto_on':None},47)[0])
        self.assertIsNone(r.step({'screen':None},48)[0])
        self.assertIsNone(r.step({'screen':'battle','auto_on':False},65)[0])
        self.assertIsNone(r.step({'screen':'battle','auto_on':False},66)[0])
        self.assertEqual(r.step({'screen':'battle','auto_on':False},67)[0],'auto')
        self.assertEqual(r.manual_wait,1)
        self.assertIsNone(r.step({'screen':'battle','auto_on':True},68)[0])
        self.assertIsNone(r.step({'screen':'battle','auto_on':True},69)[0])
        self.assertTrue(r.auto_verified)

    def test_promotion_chain_counts_once_after_return_to_list(self):
        r = RookieArenaRunner(total=1)
        self.enter(r)
        self.assertEqual(self.see(r, 'victory'), 'confirm')
        self.assertEqual(self.see(r, 'promotion'), 'promotion_confirm')
        self.assertEqual(r.count, 0)
        self.assertEqual(self.see(r, 'promotion_rewards'), 'reward_close')
        self.assertEqual(r.count, 0)
        self.assertEqual(self.see(r, 'list', flags=8), 'done')
        self.assertEqual(r.count, 1)

    def test_promotion_retries_require_source_and_remain_bounded(self):
        r = RookieArenaRunner()
        self.enter(r)
        self.see(r, 'victory')
        self.see(r, 'promotion')
        began = r.pending['began']
        obs = {'screen': 'promotion'}
        self.assertEqual(r.step(obs, began+4.1)[0], 'promotion_confirm')
        self.assertEqual(r.step(obs, began+8.2)[0], 'promotion_confirm')
        self.assertIsNone(r.step(obs, began+12)[0])
        self.assertEqual(r.step(obs, began+46)[0], 'timeout')
        self.assertEqual(r.count, 0)


if __name__ == '__main__':
    unittest.main()
