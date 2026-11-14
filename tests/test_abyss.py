import unittest
from abyss import AbyssRunner


class AbyssTests(unittest.TestCase):
    def observe(self, runner, visible, now):
        runner.step(set(visible), now)
        return runner.step(set(visible), now + .4)

    def test_retry_requires_source_and_positive_ack(self):
        r = AbyssRunner(1)
        self.assertEqual(self.observe(r, ['ready'], 0)[0], 'ready')
        self.assertEqual(self.observe(r, [], 5), (None, None))
        self.assertIsNotNone(r.pending)
        self.assertEqual(self.observe(r, ['ready'], 6)[0], 'retry_ready')
        self.assertEqual(self.observe(r, ['battle'], 7)[0], 'confirmed')
        self.assertEqual(r.count, 0)

    def test_floor_count_only_after_return_to_ready(self):
        r = AbyssRunner(1)
        self.assertEqual(self.observe(r, ['next'], 0)[0], 'next')
        self.observe(r, ['next'], 5)
        self.assertEqual(r.count, 0)
        self.assertEqual(self.observe(r, ['ready'], 7)[0], 'done')
        self.assertEqual(r.count, 1)

    def test_loading_times_out_without_blind_clicks(self):
        r = AbyssRunner(None)
        self.observe(r, ['ready'], 0)
        self.assertEqual(r.step(set(), 46), ('timeout', None))

    def test_guardian_retries_until_stable_dim(self):
        r = AbyssRunner(None)
        self.assertEqual(self.observe(r, ['battle', 'available'], 0)[0], 'guardian')
        self.assertEqual(r.step({'battle','available'}, 1.3)[0], 'target')
        self.assertEqual(r.step({'battle','available'}, 4.4)[0], 'guardian')
        r.step({'battle'}, 5.3)
        r.step({'battle','spent'}, 7)
        r.step({'battle','spent'}, 7.4)
        self.assertEqual(r.step({'battle','spent'}, 7.8)[0], 'guardian_confirmed')
        self.assertEqual(r.step({'battle','available'}, 12), (None, None))
        self.assertEqual(r.step({'battle','available'}, 12.4)[0], 'guardian')
        self.assertEqual(r.step({'battle','available'}, 13.3)[0], 'target')
        r.step({'battle', 'spent'}, 15)
        r.step({'battle', 'spent'}, 15.4)
        self.assertEqual(r.step({'battle', 'spent'}, 15.8)[0], 'guardian_confirmed')
        self.assertEqual(r.step({'battle', 'available'}, 20), (None, None))
        self.assertEqual(r.step({'battle', 'available'}, 20.4)[0], 'guardian')

    def test_guardian_recharge_requires_consecutive_available_observations(self):
        r = AbyssRunner(None)
        self.observe(r, ['battle', 'available'], 0)
        r.step({'battle', 'available'}, 1.3)
        for now in (3, 3.4, 3.8):
            r.step({'battle', 'spent'}, now)
        self.assertTrue(r.used)
        for visible in ({'battle', 'available'}, {'battle', 'spent'},
                        {'battle', 'available', 'spent'}, {'battle', 'available'}):
            self.assertEqual(r.step(visible, 10), (None, None))
        self.assertEqual(r.step({'battle', 'available'}, 10.4)[0], 'guardian')


if __name__ == '__main__':
    unittest.main()
