"""Epic Seven visual scenario runner for Windows. F8 stops globally."""
import ctypes as C
from ctypes import wintypes as W
import json
import sys
from pathlib import Path
import time
import tkinter as tk
from tkinter import messagebox

import cv2
import numpy as np
from PIL import ImageGrab
from window_capture import WindowCapture
from window_geometry import fit_window_client
from background_input import BackgroundClicker
from image_matching import tolerant_edges
from abyss import AbyssRunner
from secret_shop import ShopRunner, ITEMS, parse_budget
from secret_shop_vision import ShopVision
from rookie_arena import RookieArenaRunner
from rookie_arena_vision import RookieArenaVision
from desktop_ui import BUILD, build_ui, update_scenario_ui, set_running_ui, apply_language
from app_settings import load_settings
from i18n import translate
from settings_ui import PreferencesController
from mode_preferences import ModePreferences

ROOT = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
RETRY_ACTIONS = {'ready', 'select_team', 'start', 'start_quest', 'skip', 'clear', 'map_rank_up',
                 'mvp_confirm', 'skip_confirm', 'friend_cancel', 'story_clear', 'received_reward',
                 'connection_unlocked', 'hero_friendship'}
REQUIRE_NEXT_SCREEN = {'ready', 'select_team', 'clear', 'mvp_confirm', 'map_rank_up'}
user = C.windll.user32
user.SetProcessDPIAware()
user.GetForegroundWindow.restype = W.HWND
user.IsWindow.argtypes = [W.HWND]
user.IsIconic.argtypes = [W.HWND]
user.GetClientRect.argtypes = [W.HWND, C.POINTER(W.RECT)]
user.ClientToScreen.argtypes = [W.HWND, C.POINTER(W.POINT)]
user.SetForegroundWindow.argtypes = [W.HWND]
user.PostMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
user.PostMessageW.restype = W.BOOL


def windows():
    result = []
    callback = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
    def visit(hwnd, _):
        if user.IsWindowVisible(hwnd):
            title = C.create_unicode_buffer(512)
            user.GetWindowTextW(hwnd, title, 512)
            if title.value:
                result.append((title.value, hwnd))
        return True
    user.EnumWindows(callback(visit), 0)
    return sorted(result)


def bounds(hwnd):
    if not user.IsWindow(hwnd) or user.IsIconic(hwnd):
        raise RuntimeError('Cửa sổ game đã đóng hoặc đang thu nhỏ.')
    rect, point = W.RECT(), W.POINT(0, 0)
    user.GetClientRect(hwnd, C.byref(rect))
    user.ClientToScreen(hwnd, C.byref(point))
    if rect.right < 320 or rect.bottom < 180:
        raise RuntimeError('Vùng game quá nhỏ.')
    return point.x, point.y, point.x + rect.right, point.y + rect.bottom


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('AutoE7 — Kịch bản nhận diện hình ảnh')
        self.root.geometry('820x780')
        self.settings = load_settings()
        self.language = self.settings.language
        self.running = False
        self.templates = {}
        self.window_capture = WindowCapture()
        self.background_clicker = BackgroundClicker(self.root.after)
        self.config = json.loads((ROOT / 'scenarios.json').read_text(encoding='utf-8-sig'))
        self.config.setdefault('Reroll Secret Shop', [])
        self.config.setdefault('Rookie Arena', [])
        build_ui(self)
        self.mode_preferences = ModePreferences(self)
        self.preferences = PreferencesController(self, ROOT)
        apply_language(self)
        self.refresh()
        self.log(f'AutoE7 {BUILD}. Sẵn sàng. Chọn hoạt động và kiểm tra cấu hình trước khi bắt đầu.')
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.root.after(100, self.tick)
        self.preferences.start()
        self.root.mainloop()

    def log(self, text):
        text = translate(text, getattr(self, 'language', 'vi'))
        self.logbox.configure(state='normal')
        self.logbox.insert('end', time.strftime('%H:%M:%S ') + text + '\n')
        self.logbox.see('end'); self.logbox.configure(state='disabled')

    def open_settings(self):
        self.preferences.open()

    def update_limit(self, event=None):
        update_scenario_ui(self)

    def refresh(self):
        if self.running:
            return
        previous = self.window.get()
        self.items = windows()
        self.window['values'] = [f'{title} [{hwnd}]' for title, hwnd in self.items]
        if self.items:
            values = list(self.window['values'])
            index = values.index(previous) if previous in values else next(
                (i for i, (title, _) in enumerate(self.items) if 'epic seven' in title.lower()), 0)
            self.window.current(index)
        else:
            self.window.set('')

    def start(self):
        if self.running: return
        try:
            if self.window.current() < 0 or not self.items:
                raise ValueError('Hãy mở game và chọn cửa sổ Epic Seven trước khi bắt đầu.')
            self.hwnd = self.items[self.window.current()][1]
            is_shop = self.scenario.get() == 'Reroll Secret Shop'
            is_arena = self.scenario.get() == 'Rookie Arena'
            self.total = (None if self.scenario.get() == 'Đi Map' and self.forever.get() else
                          1 if is_shop or self.scenario.get() in ('Abyss (Tháp)', 'Rookie Arena') and self.forever.get()
                          else int(self.limit.get()))
            self.roi = tuple(float(v) for v in self.region.get().split(','))
            a, b, c, d = self.roi
            if not (0 <= a < c <= 1 and 0 <= b < d <= 1 and (self.total is None or self.total > 0)):
                raise ValueError('Vùng game hoặc số vòng không hợp lệ.')
            self.rules = self.config[self.scenario.get()]
            if not self.rules and not (is_shop or is_arena): raise ValueError('Kịch bản Đi Hunt chưa có ảnh mẫu. Hãy bổ sung quy tắc trước.')
            self.arena = None
            self.arena_vision = None
            if is_arena:
                self.arena = RookieArenaRunner(
                    mode='fixed' if self.arena_mode.get() == 'Cố định vị trí ưu tiên' else 'sequential',
                    preferred=int(self.arena_preferred.get()), refill=self.arena_refill.get(),
                    budget=int(self.arena_budget.get()), total=None if self.forever.get() else self.total)
                self.arena_vision = RookieArenaVision(ROOT)
            self.shop = ShopRunner([k for k, v in self.shop_selected.items() if v.get()], parse_budget(self.shop_budget.get())) if is_shop else None
            self.shop_vision = ShopVision(ROOT) if is_shop else None
            self.preview = self.dry.get()
            self.background_input = self.no_mouse.get()
            self.capture_covered = self.hidden_capture.get()
            if self.capture_covered and not self.background_input and not self.preview:
                raise ValueError('Bật Không chiếm chuột để chạy click khi game bị che.')
            self.phase = 'prepare'; self.count = 0
            self.abyss = AbyssRunner(None if self.forever.get() else self.total) if self.scenario.get() == 'Abyss (Tháp)' else None
            self.last_action = time.monotonic(); self.next_action = self.last_action + 2
            self.arena_observation = None
            self.arena_diagnostic_saved = False
            self.arena_blocked_key = None
            self.arena_blocked_since = None
            self.arena_started = self.last_action
            self.previous = None; self.stable = 0; self.last_report = None
            self.awaiting = None
            self.awaiting_missing = 0
            self.background_clicker.error = None
            original_size, target_size = fit_window_client(self.hwnd)
            self.log(f'Khuôn game: {original_size[0]} × {original_size[1]} → '
                     f'{target_size[0]} × {target_size[1]} (vùng client).')
            bounds(self.hwnd)
            if self.capture_covered:
                self.window_capture.start(self.hwnd)
            if not self.background_input and not self.capture_covered:
                user.SetForegroundWindow(self.hwnd)
            self.running = True
            set_running_ui(self, True)
            self.status.set('Đang khởi động…\nBắt đầu nhận diện sau 2 giây. F8 để dừng.')
            self.log('Bắt đầu sau 2 giây. F8 để dừng; timeout không tiến triển: 10 phút.')
            if self.background_input:
                self.log('Gửi click qua cửa sổ, không di chuyển chuột. Cần thử xem game có nhận input này không.')
            if self.capture_covered:
                self.log('Windows Graphics Capture: không thu nhỏ. Ảnh đen tạm thời sẽ chờ loading, tối đa 45 giây.')
        except Exception as exc:
            self.window_capture.close()
            messagebox.showerror(translate('Không thể bắt đầu', self.language), translate(str(exc), self.language))

    def stop(self, reason):
        if self.running:
            self.background_clicker.release()
            self.running = False; self.window_capture.close()
            set_running_ui(self, False)
            self.log(reason)
            arena=getattr(self,'arena',None)
            if arena is not None:
                reason += f'\nThắng {arena.wins} · Thua {arena.losses} · Tổng {arena.count} trận'
            self.status.set(reason)

    def close(self):
        if not self.mode_preferences.close():
            messagebox.showwarning(translate('Cài đặt', self.language), translate(
                'Không lưu được cấu hình hoạt động. Vui lòng kiểm tra quyền ghi.', self.language), parent=self.root)
        self.preferences.close()
        self.background_clicker.release()
        self.running = False
        self.window_capture.close()
        self.root.destroy()

    def detect(self, frame, rule):
        # Normalize game content to reference resolution before matching.
        key = rule['id']
        if key not in self.templates:
            src = cv2.imread(str(ROOT / 'assets' / rule['image']))
            if src is None: raise RuntimeError('Thiếu ảnh mẫu: ' + rule['image'])
            self.templates[key] = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
        template = self.templates[key]
        x1, y1, x2, y2 = rule['rect']
        # A small local search tolerates slight screenshot differences.
        margin = rule.get('search_margin', 18)
        left, top = max(0, x1-margin), max(0, y1-margin)
        search = frame[top:min(720, y2+margin), left:min(1280, x2+margin)]
        if 'binary_threshold' in rule:
            cutoff = rule['binary_threshold']
            search = cv2.threshold(search, cutoff, 255, cv2.THRESH_BINARY)[1]
            template = cv2.threshold(template, cutoff, 255, cv2.THRESH_BINARY)[1]
        if rule.get('match') == 'tolerant_edges':
            return tolerant_edges(search, template, rule.get('scales', [1]))
        if rule.get('match') == 'edges':
            # Story artwork and fades change the background behind Skip.
            # Compare letter contours instead of absolute background brightness.
            search = cv2.Canny(search, 60, 140)
            best = 0
            for scale in rule.get('scales', [1]):
                scaled = cv2.resize(template, None, fx=scale, fy=scale)
                edges = cv2.Canny(scaled, 60, 140)
                if edges.shape[0] > search.shape[0] or edges.shape[1] > search.shape[1]:
                    continue
                _, score, _, _ = cv2.minMaxLoc(cv2.matchTemplate(search, edges, cv2.TM_CCOEFF_NORMED))
                best = max(best, score)
            return best
        score, _, _, _ = (0, 0, 0, 0)
        _, score, _, loc = cv2.minMaxLoc(cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED))
        # Correlation alone also matches dimmed buttons behind modal dialogs.
        patch = search[loc[1]:loc[1]+template.shape[0], loc[0]:loc[0]+template.shape[1]]
        error = np.mean(np.abs(patch.astype(float)-template.astype(float)))
        return score if error < rule.get('max_error', 28) else 0

    def tick(self):
        try:
            if self.running:
                if self.background_clicker.error:
                    raise RuntimeError(self.background_clicker.error)
                if user.GetAsyncKeyState(0x77) & 0x8000:
                    self.stop('Đã dừng bằng F8.'); return
                now = time.monotonic()
                if now-self.last_action > 600:
                    self.stop('Dừng: 10 phút không có tiến triển.'); return
                if now < self.next_action: return
                if not self.background_input and not self.capture_covered and user.GetForegroundWindow() != self.hwnd:
                    self.status.set('Tạm chờ: đưa cửa sổ game lên trước.'); return
                l, t, r, b = bounds(self.hwnd)
                a, c, d, e = self.roi
                region = (l+int((r-l)*a), t+int((b-t)*c), l+int((r-l)*d), t+int((b-t)*e))
                if self.capture_covered:
                    full = self.window_capture.poll(self.hwnd, r-l, b-t)
                    if full is None:
                        self.stable = 0
                        self.previous = None
                        self.awaiting_missing = 0
                        if getattr(self, 'shop', None) is not None:
                            self.shop.previous = None
                            self.shop.stable = 0
                        self.status.set(self.window_capture.wait_reason); return
                    shot = full[region[1]-t:region[3]-t, region[0]-l:region[2]-l]
                else:
                    shot = np.array(ImageGrab.grab(bbox=region, all_screens=True))
                frame = cv2.cvtColor(cv2.resize(shot, (1280,720)), cv2.COLOR_RGB2GRAY)
                if getattr(self, 'arena', None) is not None:
                    self.tick_arena(cv2.resize(shot, (1280, 720)), now, region, l, t)
                    return
                if getattr(self, 'shop', None) is not None:
                    self.tick_shop(frame, now, region, l, t)
                    return
                if getattr(self, 'abyss', None) is not None:
                    self.tick_abyss(frame, now, region, l, t)
                    return
                retry_attempt = 0
                found = None
                best_key, best_score = '', 0
                for rule in self.rules:
                    if self.phase not in rule['phases']: continue
                    score = self.detect(frame, rule)
                    if score > best_score:
                        best_key, best_score = rule['id'], score
                    if score >= rule.get('threshold', .90):
                        found = rule; break
                if self.awaiting is not None:
                    sent_rule, sent_at, attempts = self.awaiting
                    # A queued message is not proof that the game accepted it.
                    source_visible = self.detect(frame, sent_rule) >= sent_rule.get('threshold', .90)
                    self.awaiting_missing = 0 if source_visible else getattr(self, 'awaiting_missing', 0)+1
                    # Skip can remain visible behind its confirmation dialog.
                    # A detected next action must take priority over that text.
                    next_action = found is not None and found['id'] != sent_rule['id'] and not (
                        found['id'] in ('skip', 'skip_intro', 'skip_text') and sent_rule['id'] in ('skip', 'skip_intro', 'skip_text'))
                    # Ready/Select Team must reach a recognized next screen.
                    # Starting a quest can lead to normal combat with no button
                    # to detect, so require two valid frames without Start.
                    waiting = source_visible or sent_rule['id'] in REQUIRE_NEXT_SCREEN or (
                        sent_rule['id'] in ('start', 'start_quest') and self.awaiting_missing < 2)
                    if waiting and not next_action:
                        if source_visible and sent_rule['id'] in RETRY_ACTIONS and attempts < 3 and now-sent_at >= 3:
                            # Retry only with the source button recognized in
                            # the current image and no next screen detected.
                            retry_attempt = attempts+1
                            found = sent_rule
                            self.awaiting = None
                            self.previous = sent_rule['id']
                            self.stable = 1
                            self.log(f'Thử lại {sent_rule["id"]} lần {retry_attempt}/3: vẫn nhận diện màn cũ, chưa thấy bước tiếp theo.')
                        elif now-sent_at > 12:
                            self.stop('Dừng: chưa xác nhận được màn kế tiếp sau click ' + sent_rule['id'] + ' trong 12 giây.')
                            return
                        else:
                            self.status.set('Đã gửi click, chờ màn kế tiếp: ' + sent_rule['id'])
                            return
                    else:
                        self.log(('Đã nhận diện bước kế tiếp sau click: ' if next_action else 'Nút đã biến mất sau click: ') + sent_rule['id'])
                        self.awaiting = None
                key = found['id'] if found else None
                self.stable = self.stable+1 if key == self.previous else 1
                self.previous = key
                if not found or self.stable < 2:
                    self.status.set(f'Vòng {self.count}/{self.total if self.total is not None else "∞"} · {self.phase} · đang chờ nhận diện\nGần nhất: {best_key} {best_score:.2f}')
                    return
                self.status.set('Nhận diện: ' + key)
                if self.preview:
                    if key != self.last_report: self.log('Nhận diện: ' + key)
                    self.last_report = key
                    return
                if key == 'ready' and self.phase == 'reward':
                    self.count += 1
                    self.log(f'Hoàn thành vòng {self.count}/{self.total if self.total is not None else "∞"}')
                    if self.total is not None and self.count >= self.total:
                        self.stop('Đã hoàn thành số vòng yêu cầu.'); return
                x, y = found['click']
                screen_x = region[0]+int(x/1280*(region[2]-region[0]))
                screen_y = region[1]+int(y/720*(region[3]-region[1]))
                if self.background_input:
                    client_x, client_y = screen_x-l, screen_y-t
                    # Compute only client-local coordinates for background input.
                    self.background_clicker.click(self.hwnd, client_x, client_y)
                    self.log(f'Gửi click nền: {key} · HWND={self.hwnd} · client=({client_x},{client_y})')
                else:
                    # Recheck focus immediately before injecting desktop input.
                    if user.GetForegroundWindow() != self.hwnd: return
                    user.SetCursorPos(screen_x, screen_y)
                    user.mouse_event(2, 0, 0, 0, 0); user.mouse_event(4, 0, 0, 0, 0)
                self.awaiting = found, now, retry_attempt
                self.awaiting_missing = 0
                # Optional dialogs can occur on either side of MVP Confirm.
                # Closing them must preserve the stage that was interrupted.
                if found['next'] != '$same':
                    self.phase = found['next']
                self.last_action = now; self.next_action = now+1.5
                self.stable = 0
                if not self.background_input:
                    self.log('Click: ' + key)
        except Exception as exc:
            self.stop('Lỗi: ' + str(exc))
        finally:
            self.root.after(400, self.tick)

    def tick_arena(self, frame, now, region, l, t):
        obs = self.arena_vision.observe(frame, now=now)
        observed = (obs.get('screen'), obs.get('flags'), obs.get('selected_opponent'), obs.get('auto_on'))
        # Transient missing battle art during skill animations is normal.
        # Keep the last positive observation to avoid flooding the log.
        if observed[0] is not None and observed != self.arena_observation:
            self.arena_observation = observed
            self.log(f'Arena nhận diện: màn={observed[0]} · lượt={observed[1]} · chọn={observed[2]} · auto={observed[3]} · nguồn={obs.get("auto_source")}')
        auto_blocked = (obs.get('screen') == 'battle' and self.arena.state == 'battle'
                        and not self.arena.auto_verified and self.arena.battle_at is not None
                        and now-self.arena.battle_at >= 6)
        blocked_key = ('unknown_screen' if obs.get('screen') is None else
                       'flags' if obs.get('screen') == 'list' and obs.get('flags') is None else
                       'auto' if auto_blocked else
                       'refresh' if self.arena.state == 'refresh_wait' else None)
        blocked = blocked_key is not None
        if blocked_key != self.arena_blocked_key:
            self.arena_blocked_key = blocked_key
            self.arena_blocked_since = now if blocked else None
            self.arena_diagnostic_saved = False
        if blocked and not self.arena_diagnostic_saved and now-self.arena_blocked_since >= 3:
            self.arena_diagnostic_saved = True
            try:
                diagnostic = ROOT / 'diagnostics' / 'rookie-arena-last.png'
                diagnostic.parent.mkdir(exist_ok=True)
                if cv2.imwrite(str(diagnostic), cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)):
                    diagnostic.with_suffix('.json').write_text(json.dumps({
                        'build': BUILD, 'screen': obs.get('screen'), 'flags': obs.get('flags'),
                        'runner_state': self.arena.state, 'completed': self.arena.count,
                        'auto_on': obs.get('auto_on'), 'auto_click_sent': self.arena.auto_used,
                        'auto_verified': self.arena.auto_verified,
                        'auto_source': obs.get('auto_source'),
                        'auto_click_age': now-self.arena.auto_at if self.arena.auto_at is not None else None,
                        'failed': sorted(obs.get('failed', ())),
                        'signature': obs.get('signature'),
                        'refresh_signature': self.arena.refresh_signature,
                        'refresh_failed_rows': sorted(self.arena.refresh_failed_rows),
                        'refresh_stable': self.arena.refresh_stable,
                    }, ensure_ascii=False, indent=2), encoding='utf-8')
                    self.log('Đã lưu ảnh chẩn đoán: ' + str(diagnostic))
            except (OSError, cv2.error) as exc:
                self.log('Không lưu được ảnh chẩn đoán: ' + str(exc))
        if self.preview:
            self.status.set('Rookie Arena · chỉ nhận diện\n'
                            f'Màn: {obs.get("screen")} · lượt: {obs.get("flags")} · '
                            f'ô thua: {sorted(obs.get("failed", ()))}\n'
                            f'Auto: {obs.get("auto_on")} · tiền đã chọn: {obs.get("selected_currency")}')
            return
        # Recheck before advancing the state machine, which assumes input is sent.
        if not self.background_input and user.GetForegroundWindow() != self.hwnd:
            return
        event, point = self.arena.step(obs, now)
        self.count = self.arena.count
        limit = self.arena.total if self.arena.total is not None else '∞'
        detail = ('Chưa nhận diện được màn game.' if obs.get('screen') is None else
                  'Đã thấy danh sách nhưng chưa đọc được số lượt.' if obs.get('screen') == 'list' and obs.get('flags') is None else
                  f'Đang đánh · auto: {obs.get("auto_on")} · đã gửi click: {self.arena.auto_used}' if obs.get('screen') == 'battle' else
                  f'Màn: {obs.get("screen")} · lượt: {obs.get("flags")} · {self.arena.state}')
        self.status.set(f'Rookie Arena · trận {self.count}/{limit} · Thắng {self.arena.wins} · Thua {self.arena.losses}\n'
                        f'{self.arena.spent}/{self.arena.budget} SkyStone · {detail}')
        reasons = {
            'done': 'Đã hoàn thành số trận yêu cầu.', 'no_flags': 'Hết lượt đánh.',
            'all_failed': 'Đã thua cả 3 đối thủ.', 'budget_exhausted': 'Hết ngân sách SkyStone.',
            'cannot_purchase': 'Không mua thêm lượt được hoặc không xác minh được tài nguyên.',
            'purchase_uncertain': 'Chưa xác minh được mua lượt; dừng để tránh mua trùng.',
            'refresh_exhausted': 'Đã hết lượt refresh trả Gold trong ngày.',
            'refresh_uncertain': 'Chưa xác minh được refresh danh sách; dừng để tránh xác nhận trùng.',
            'timeout': ('Không xác nhận được auto đã bật trong thời gian chờ.'
                        if self.arena.state == 'battle' and not self.arena.auto_verified else
                        'Không xác nhận được bước tiếp theo trong thời gian chờ.')}
        if event in reasons:
            self.stop('Rookie Arena: ' + reasons[event]); return
        if event:
            self.log('Rookie Arena: ' + event)
            self.last_action = now
        if point is None:
            return
        x, y = point
        sx = region[0] + int(x / 1280 * (region[2] - region[0]))
        sy = region[1] + int(y / 720 * (region[3] - region[1]))
        if self.background_input:
            self.background_clicker.click(self.hwnd, sx-l, sy-t)
        else:
            user.SetCursorPos(sx, sy)
            user.mouse_event(2, 0, 0, 0, 0); user.mouse_event(4, 0, 0, 0, 0)
        self.next_action = now + 1

    def tick_shop(self, frame, now, region, l, t):
        obs = self.shop_vision.observe(frame)
        summary = ', '.join(ITEMS[i['kind']] + (' (0/1)' if not i['available'] else '') for i in obs['items'])
        if self.preview:
            self.status.set('Shop · chỉ nhận diện · ' + str(obs['modal'] or summary or 'đang chờ shop'))
            return
        event, action = self.shop.step(obs, now)
        budget = self.shop.budget if self.shop.budget is not None else '∞'
        counts = ' · '.join(f'{ITEMS[k]}: {n}' for k, n in self.shop.bought.items())
        self.status.set(f'Shop · {self.shop.spent}/{budget} Skystone · {self.shop.state}\n{counts}')
        if event == 'done':
            self.stop(f'Đã dùng đủ {self.shop.spent} Skystone và quét/mua xong shop cuối. {counts}'); return
        if event and event.startswith('stop:'):
            diagnostic = ROOT / 'diagnostics'
            diagnostic.mkdir(exist_ok=True)
            cv2.imwrite(str(diagnostic / 'shop-last.png'), frame)
            if self.shop.top_image is not None:
                cv2.imwrite(str(diagnostic / 'shop-before-refresh.png'), self.shop.top_image)
            (diagnostic / 'shop-last.json').write_text(json.dumps({
                'state': self.shop.state, 'spent': self.shop.spent,
                'reason': event, 'shop': obs['shop'], 'modal': obs['modal'],
                'top': obs['top'], 'bottom': obs['bottom'],
                'endpoint_source': obs.get('endpoint_source'), 'items': obs['items'],
            }, ensure_ascii=False, indent=2), encoding='utf-8')
            self.stop('Dừng Shop: ' + event[5:]); return
        if event:
            self.log('Shop: ' + event)
            self.last_action = now
        if action is None:
            return
        x, y = (980, 370) if action[0] == 'scroll' else action[1:]
        sx = region[0] + int(x / 1280 * (region[2] - region[0]))
        sy = region[1] + int(y / 720 * (region[3] - region[1]))
        if self.background_input:
            if action[0] == 'scroll':
                self.background_clicker.scroll(self.hwnd, sx-l, sy-t, action[1])
            else:
                self.background_clicker.click(self.hwnd, sx-l, sy-t)
        else:
            if user.GetForegroundWindow() != self.hwnd:
                self.stop('Dừng Shop: game mất focus trước thao tác.'); return
            user.SetCursorPos(sx, sy)
            if action[0] == 'scroll':
                user.mouse_event(0x0800, 0, 0, action[1], 0)
            else:
                user.mouse_event(2, 0, 0, 0, 0); user.mouse_event(4, 0, 0, 0, 0)
        self.next_action = now + 1

    def tick_abyss(self, frame, now, region, l, t):
        visible = {rule.get('observation', rule['id'].removeprefix('abyss_')) for rule in self.rules
                   if self.detect(frame, rule) >= rule.get('threshold', .85)}
        if self.preview:
            self.status.set('Abyss · chỉ nhận diện: ' + ', '.join(sorted(visible)))
            return
        event, point = self.abyss.step(visible, now)
        self.count = self.abyss.count
        limit = self.abyss.total if self.abyss.total is not None else '∞'
        self.status.set(f'Abyss · tầng {self.count}/{limit} · {self.abyss.state}')
        if event == 'done':
            self.stop('Đã hoàn thành số tầng Abyss yêu cầu.'); return
        if event == 'timeout':
            self.stop('Dừng Abyss: chưa xác nhận chuyển màn sau 45 giây và tối đa 5 lần thử lại.'); return
        if event:
            self.log('Abyss: ' + event)
        if event in ('confirmed', 'guardian_confirmed'):
            self.last_action = now
        if point is None:
            return
        x, y = point
        sx = region[0] + int(x / 1280 * (region[2] - region[0]))
        sy = region[1] + int(y / 720 * (region[3] - region[1]))
        if self.background_input:
            self.background_clicker.click(self.hwnd, sx-l, sy-t)
        else:
            if user.GetForegroundWindow() != self.hwnd:
                self.stop('Dừng Abyss: game mất focus trước khi click.'); return
            user.SetCursorPos(sx, sy)
            user.mouse_event(2, 0, 0, 0, 0); user.mouse_event(4, 0, 0, 0, 0)


if __name__ == '__main__':
    if '--self-test' in sys.argv:
        # Used to verify the portable build without clicking any game window.
        import traceback
        report = {'ok': False}
        try:
            from windows_capture import WindowsCapture
            config = json.loads((ROOT/'scenarios.json').read_text(encoding='utf-8-sig'))
            samples = 0
            for rules in config.values():
                for rule in rules:
                    sample = cv2.imread(str(ROOT/'assets'/rule['image']))
                    if sample is None:
                        raise RuntimeError('Missing template: '+rule['image'])
                    samples += 1
            shop_vision = ShopVision(ROOT)
            samples += len(shop_vision.templates)
            RookieArenaVision(ROOT)
            arena_sample = None
            if '--arena-test-image' in sys.argv:
                path = sys.argv[sys.argv.index('--arena-test-image') + 1]
                sample = cv2.imread(path)
                if sample is None or sample.shape != (720, 1280, 3):
                    raise ValueError('Arena test image must be normalized 1280x720')
                obs = RookieArenaVision(ROOT).observe(cv2.cvtColor(sample, cv2.COLOR_BGR2RGB))
                arena_sample = {'screen': obs['screen'], 'flags': obs['flags'], 'auto_on': obs['auto_on']}
            test_root = tk.Tk()
            test_root.withdraw()
            test_root.update()
            test_root.destroy()
            report = {'ok': True, 'templates': samples, 'opencv': cv2.__version__,
                      'numpy': np.__version__, 'frozen': bool(getattr(sys, 'frozen', False)),
                      'python': sys.version, 'graphics_capture': WindowsCapture.__module__}
            report['build'] = BUILD
            if arena_sample is not None:
                report['arena_sample'] = arena_sample
        except Exception:
            report['error'] = traceback.format_exc()
        (ROOT/'self-test.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        sys.exit(0 if report['ok'] else 1)
    else:
        App()
