import unittest
import numpy as np
import cv2
from secret_shop import ShopRunner, parse_budget


def scene(items=(), top=True, bottom=False, modal=None, kind=None, image=0):
    return dict(shop=modal is None, modal=modal, modal_item=kind,
                items=[dict(kind=k, y=y, available=a) for k,y,a in items],
                top=top, bottom=bottom, list_image=np.full((8,8), image, dtype=np.uint8))


class ShopTests(unittest.TestCase):
    def stable(self, obs, now):
        first = self.runner.step(obs, now)
        return first if first != (None, None) else self.runner.step(obs, now+.4)

    def setUp(self):
        self.runner = ShopRunner(['friendship', 'covenant', 'mystic'], 3)

    def test_budget(self):
        self.assertIsNone(parse_budget('  '))
        self.assertEqual(parse_budget(' 300 '), 300)
        for text in ('0', '-3', '4', '3.0', 'abc'):
            with self.assertRaises(ValueError): parse_budget(text)
        with self.assertRaises(ValueError): ShopRunner([], None)

    def test_multiple_items_purchase_ack_and_overlap(self):
        items = [('friendship',160,True), ('covenant',310,True)]
        obs = scene(items)
        self.stable(obs,0)
        event, action = self.runner.step(obs,1)
        self.assertEqual(action, ('click',1188,160))
        event, action = self.stable(scene(modal='buy',kind='friendship'),2)
        self.assertEqual(action, ('click',817,510))
        # Dialog disappearing alone is not evidence of a purchase.
        self.stable(obs,3)
        self.assertEqual(self.runner.bought['friendship'],0)
        sold = scene([('friendship',160,False), ('covenant',310,True)])
        self.stable(sold,4)
        self.assertEqual(self.runner.bought['friendship'],1)
        event, action = self.runner.step(sold,5)
        self.assertEqual(action, ('click',1188,310))
        self.stable(scene(modal='buy',kind='covenant'),6)
        sold2=scene([('friendship',160,False),('covenant',310,False)])
        self.stable(sold2,7)
        self.runner.step(sold2,8)
        self.assertEqual(self.runner.state,'seek_bottom')
        self.stable(scene([('covenant',120,False)],top=False,bottom=True),9)
        self.assertEqual(self.runner.bought['covenant'],1)

    def test_wrong_popup_never_confirmed(self):
        obs=scene([('mystic',160,True)])
        self.stable(obs,0); self.runner.step(obs,1)
        event,action=self.stable(scene(modal='buy',kind='covenant'),2)
        self.assertTrue(event.startswith('stop:'))
        self.assertIsNone(action)

    def test_refresh_budget_counts_returned_shop_and_scans_last(self):
        r=self.runner
        self.stable(scene(),0); r.step(scene(),1)
        bottom=scene(top=False,bottom=True)
        self.stable(bottom,2)
        self.assertEqual(r.step(bottom,3)[1],('click',265,665))
        self.assertEqual(self.stable(scene(modal='refresh'),4)[1],('click',748,463))
        self.stable(scene(),5)
        self.assertEqual(r.spent,3)
        r.step(scene(image=80),7)
        self.assertEqual(r.state,'seek_bottom')
        last=scene(top=False,bottom=True,image=80)
        self.stable(last,8)
        self.assertEqual(r.step(last,9),('done',None))
        self.assertEqual(r.spent,3)

    def test_refresh_waits_for_stable_shop_not_just_missing_popup(self):
        r = self.runner
        r.state = 'confirm_refresh'
        r.sent, r.attempts = 0, 0
        self.assertEqual(self.stable(dict(shop=False, modal=None), 1), (None, None))
        self.assertEqual(r.spent, 0)
        self.assertEqual(r.step(scene(), 2), (None, None))
        self.assertEqual(r.spent, 0)
        event, action = r.step(scene(), 2.4)
        self.assertEqual(r.spent, 3)
        self.assertEqual(r.state, 'scan_top')
        self.assertIsNone(action)
        r.step(scene(), 3)
        self.assertEqual(r.spent, 3)

    def test_refresh_return_at_bottom_seeks_top_after_counting_once(self):
        r = self.runner
        r.state = 'confirm_refresh'
        r.spent = 66
        event, action = self.stable(scene(top=False, bottom=True), 5)
        self.assertEqual(r.spent, 69)
        self.assertEqual(r.state, 'seek_top')
        self.assertIsNone(action)
        self.assertEqual(r.step(scene(top=False, bottom=True), 6)[1], ('scroll', 1200))
        self.assertEqual(r.spent, 69)

    def test_refresh_retries_only_while_confirmation_remains_visible(self):
        r = self.runner
        r.state = 'confirm_refresh'
        r.sent, r.attempts = 0, 0
        self.assertEqual(self.stable(scene(modal='refresh'), 4)[1], ('click', 748, 463))
        self.assertEqual(r.spent, 0)
        self.assertEqual(self.stable(dict(shop=False), 6), (None, None))
        self.assertEqual(r.spent, 0)

    def test_scroll_retries_bounded_without_end_ack(self):
        r=self.runner
        unknown=scene(top=False,bottom=False)
        for n in range(5):
            self.assertEqual(self.stable(unknown,n*3)[1],('scroll',1200))
        self.assertTrue(r.step(unknown,16)[0].startswith('stop:'))

    def test_unknown_screen_times_out_without_input(self):
        self.stable(dict(shop=False),0)
        event,action=self.runner.step(dict(shop=False),26)
        self.assertTrue(event.startswith('stop:'))
        self.assertIsNone(action)

    def test_hidden_scrollbar_requires_scroll_before_accepting_top(self):
        obs = scene()
        obs['endpoint_source'] = 'rows'
        self.assertEqual(self.stable(obs,0)[1], ('scroll',1200))
        event, action = self.runner.step(obs,3)
        self.assertEqual(self.runner.state,'scan_top')
        self.assertIsNone(action)

    def test_bottom_fallback_requires_actual_full_scroll(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        def image(name):
            frame=cv2.imread(str(root/'tests'/'fixtures'/('shop_'+name+'.png')),0)
            return cv2.resize(frame[80:710,550:1240],(64,64),interpolation=cv2.INTER_AREA)
        self.runner.top_image=image('top')
        self.assertTrue(self.runner.scrolled_to_bottom(image('bottom')))
        self.assertFalse(self.runner.scrolled_to_bottom(image('top')))
        # A one-half-row scroll also gives a bottom-like row lattice.
        partial=np.roll(image('top'),-7,axis=0)
        self.assertFalse(self.runner.scrolled_to_bottom(partial))
        self.runner.top_image=image('hidden_scrollbar')
        self.assertTrue(self.runner.scrolled_to_bottom(image('live_bottom')))

    def test_stationary_bottom_layout_cannot_skip_unseen_rows(self):
        r=self.runner; r.state='seek_bottom'
        r.top_image=np.zeros((64,64),np.uint8)
        obs=scene(top=False,bottom=True)
        obs['endpoint_source']='rows'
        self.assertEqual(self.stable(obs,0)[1],('scroll',-1200))
        self.assertEqual(r.step(obs,3)[1],('scroll',-1200))
        self.assertEqual(r.state,'seek_bottom')


if __name__ == '__main__': unittest.main()
