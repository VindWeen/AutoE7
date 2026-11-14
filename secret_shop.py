"""Secret Shop state machine. Actions require positive visual acknowledgement."""
import numpy as np
import cv2

ITEMS = {'friendship': 'Friendship Points', 'covenant': 'Covenant Bookmarks',
         'mystic': 'Mystic Medals'}


def parse_budget(text):
    text = text.strip()
    if not text:
        return None
    if not text.isascii() or not text.isdigit() or int(text) <= 0 or int(text) % 3:
        raise ValueError('Skystone phải là số nguyên dương chia hết cho 3; để trống để chạy tới khi dừng.')
    return int(text)


class ShopRunner:
    def __init__(self, selected, budget):
        if not selected or not set(selected) <= ITEMS.keys():
            raise ValueError('Chọn ít nhất một item cần mua.')
        self.selected = set(selected)
        self.budget = budget
        self.spent = 0
        self.bought = dict.fromkeys(ITEMS, 0)
        self.state = 'seek_top'
        self.pending = None
        self.previous = None
        self.stable = 0
        self.until = 0
        self.entered = None
        self.scroll_attempts = 0
        self.top_image = None
        self.confirmed_modal = False

    def transition(self, state, now):
        self.state = state
        self.entered = now
        self.scroll_attempts = 0

    def step(self, obs, now):
        """Return (event, action). action is ('click', x, y) or ('scroll', delta)."""
        if self.entered is None:
            self.entered = now
        if now - self.entered > 25:
            return 'stop:Không xác nhận được bước ' + self.state + ' trong 25 giây.', None
        signature = (obs.get('shop'), obs.get('modal'), obs.get('modal_item'),
                     obs.get('top'), obs.get('bottom'),
                     tuple((i['kind'], round(i['y']/4), i['available']) for i in obs.get('items', [])))
        self.stable = self.stable + 1 if signature == self.previous else 1
        self.previous = signature
        if self.stable < 2 or now < self.until:
            return None, None
        modal = obs.get('modal')
        shop = obs.get('shop') and modal is None
        items = obs.get('items', [])
        if self.state in ('seek_top', 'seek_bottom'):
            if not shop:
                return None, None
            end = 'top' if self.state == 'seek_top' else 'bottom'
            position = 'đầu danh sách' if end == 'top' else 'cuối danh sách'
            fallback = obs.get('endpoint_source') == 'rows'
            acknowledged = obs.get(end) and (not fallback or self.scroll_attempts > 0)
            if acknowledged and fallback and end == 'bottom':
                acknowledged = self.scrolled_to_bottom(obs.get('list_image'))
            if acknowledged:
                self.transition('scan_' + end, now)
                return 'Đã xác nhận ' + position, None
            if self.scroll_attempts >= 5:
                return 'stop:Không xác nhận được ' + position + ' sau 5 lần cuộn.', None
            self.scroll_attempts += 1
            self.until = now + 2
            return 'Cuộn tới ' + position, ('scroll', 1200 if end == 'top' else -1200)
        if self.state in ('scan_top', 'scan_bottom'):
            if not shop:
                return None, None
            end = 'top' if self.state == 'scan_top' else 'bottom'
            if not obs.get(end):
                self.transition('seek_' + end, now)
                return None, None
            # Keep scanning after each purchase: several selected items may coexist.
            matches = [i for i in items if i['kind'] in self.selected and i['available']]
            if self.state == 'scan_top':
                self.top_image = obs.get('list_image')
            if matches:
                self.pending = dict(matches[0], resume=self.state)
                self.transition('open_buy', now)
                self.attempts = 0
                self.sent = now
                return 'Mở mua ' + ITEMS[self.pending['kind']], ('click', 1188, self.pending['y'])
            if self.state == 'scan_top':
                self.transition('seek_bottom', now)
                return None, None
            if self.budget is not None and self.spent >= self.budget:
                return 'done', None
            self.transition('open_refresh', now)
            self.sent, self.attempts = now, 0
            return 'Mở Refresh', ('click', 265, 665)
        if self.state == 'open_buy':
            if modal == 'buy':
                if obs.get('modal_item') != self.pending['kind']:
                    return 'stop:Popup mua không khớp item đã chọn; chưa xác nhận Buy.', None
                self.transition('confirm_buy', now)
                self.sent, self.attempts = now, 0
                return 'Xác nhận mua ' + ITEMS[self.pending['kind']], ('click', 817, 510)
            row = self.row(items)
            if shop and row and row['available']:
                return self.retry(now, ('click', 1188, row['y']), 'Buy')
            return None, None
        if self.state == 'confirm_buy':
            row = self.row(items)
            if shop and row and not row['available']:
                self.bought[self.pending['kind']] += 1
                resume = self.pending['resume']
                self.pending = None
                self.transition(resume, now)
                return 'Đã mua: dòng chuyển 0/1', None
            if modal == 'buy':
                if obs.get('modal_item') != self.pending['kind']:
                    return 'stop:Item trong popup mua đã thay đổi.', None
                return self.retry(now, ('click', 817, 510), 'xác nhận Buy')
            return None, None
        if self.state == 'open_refresh':
            if modal == 'refresh':
                self.transition('confirm_refresh', now)
                self.sent, self.attempts = now, 0
                return 'Xác nhận Refresh (3 Skystone)', ('click', 748, 463)
            if shop:
                return self.retry(now, ('click', 265, 665), 'Refresh')
            return None, None
        if self.state == 'confirm_refresh':
            if modal == 'refresh':
                # Only repeat while the same confirmation dialog is positively visible.
                return self.retry(now, ('click', 748, 463), 'xác nhận Refresh')
            if shop:
                # Two stable observations have already been required above.
                # Returning to the shop after Confirm acknowledges the refresh;
                # the new inventory may look identical to the previous one.
                self.spent += 3
                self.transition('scan_top' if obs.get('top') else 'seek_top', now)
                return 'Đã refresh: ' + str(self.spent) + ' Skystone', None
            return None, None
        return None, None

    def scrolled_to_bottom(self, image):
        # Rows repeat at ~145 px. A matching row layout alone can also occur
        # halfway down. Require the old middle rows to have moved ~220 px up.
        if image is None or self.top_image is None:
            return False
        previous = np.asarray(self.top_image, dtype=np.uint8)
        current = np.asarray(image, dtype=np.uint8)
        if previous.shape != (64, 64) or current.shape != (64, 64):
            return False
        patch = previous[26:56, :44]
        if float(patch.std()) < 5:
            return False
        scores = cv2.matchTemplate(current[:39, :44], patch, cv2.TM_CCOEFF_NORMED)
        return bool(float(scores.max()) >= .76)

    def row(self, items):
        return next((i for i in items if i['kind'] == self.pending['kind']
                     and abs(i['y'] - self.pending['y']) < 12), None)

    def retry(self, now, action, name):
        if now - self.sent < 3:
            return None, None
        if self.attempts >= 3:
            return 'stop:Không xác nhận được ' + name + ' sau 3 lần thử lại.', None
        self.attempts += 1
        self.sent = now
        self.until = now + 1
        return 'Thử lại ' + name + ' ' + str(self.attempts) + '/3', action
