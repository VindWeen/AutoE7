"""Regression checks for language switches and asynchronous update notices."""
import json
import tkinter as tk
import unittest
from unittest.mock import patch

from app import App, ROOT
from app_settings import AppSettings
from desktop_ui import build_ui, apply_language, set_running_ui
from settings_ui import PreferencesController
from updates import ReleaseConfig, UpdateResult


class PreferencesUITests(unittest.TestCase):
    def setUp(self):
        self.app = App.__new__(App)
        try:
            self.app.root = tk.Tk()
        except tk.TclError as error:
            self.skipTest(str(error))
        self.app.root.withdraw()
        self.app.settings = AppSettings()
        self.app.language = 'vi'
        self.app.running = False
        self.app.config = json.loads((ROOT / 'scenarios.json').read_text(encoding='utf-8-sig'))
        self.app.config.setdefault('Reroll Secret Shop', [])
        self.app.config.setdefault('Rookie Arena', [])
        build_ui(self.app)
        self.controller = PreferencesController(self.app, ROOT)
        self.controller.config = ReleaseConfig('2026.11.14-r1', '')
        self.app.preferences = self.controller
        self.app.root.update_idletasks()

    def tearDown(self):
        if hasattr(self, 'controller'):
            self.controller.close()
            self.app.root.destroy()

    def switch(self, language):
        self.app.language = language
        apply_language(self.app)

    def test_language_changes_preserve_automation_keys_and_form_values(self):
        self.app.scenario.current(list(self.app.config).index('Rookie Arena'))
        self.app.arena_mode.current(1)
        self.app.shop_budget.insert(0, '300')
        self.app.update_limit()
        for language in ('en', 'vi', 'en'):
            self.switch(language)
            self.app.update_limit()
            self.assertEqual(self.app.scenario.get(), 'Rookie Arena')
            self.assertEqual(self.app.arena_mode.get(), 'Tuần tự 1 → 2 → 3')
            self.assertEqual(self.app.shop_budget.get(), '300')
        self.assertEqual(self.app.start_button.cget('text'), 'Start')
        self.assertEqual(self.app.limit_label.cget('text'), 'Battles')
        self.assertEqual(str(self.app.arena_preferred.cget('state')), 'disabled')
        self.app.arena_mode.current(0)
        self.app.update_limit()
        self.assertEqual(str(self.app.arena_preferred.cget('state')), 'readonly')
        self.app.running = True
        set_running_ui(self.app, True)
        self.switch('vi')
        self.assertEqual(str(self.app.start_button.cget('state')), 'disabled')

    def test_status_can_be_translated_again_without_losing_original(self):
        self.app.status.set('Đã dừng.')
        self.switch('en')
        self.assertEqual(self.app.status.get(), 'Stopped.')
        self.switch('vi')
        self.assertEqual(self.app.status.get(), 'Đã dừng.')

    def test_saved_language_applies_without_recreating_form(self):
        self.controller.open()
        window = self.app.scenario
        with patch('settings_ui.save_settings', return_value=True) as save:
            self.controller.save(language='en', auto=False)
        save.assert_called_once_with(AppSettings('en', False))
        self.assertIs(self.app.scenario, window)
        self.assertEqual(self.app.start_button.cget('text'), 'Start')
        self.assertEqual(self.controller.dialog.title(), 'Settings')

    def test_storage_failure_keeps_previous_preferences(self):
        with patch('settings_ui.save_settings', return_value=False), patch('settings_ui.messagebox.showerror'):
            self.controller.save(language='en')
        self.assertEqual(self.app.settings, AppSettings())
        self.assertEqual(self.app.language, 'vi')

    def test_available_update_does_not_interrupt_running_game(self):
        self.app.running = True
        self.controller.results.put(UpdateResult('available', '2026.11.14-r1',
            'v2026.11.14-r2', 'https://github.com/example/AutoE7/releases/tag/v2026.11.14-r2', 'Notes'))
        with patch.object(self.controller, 'show_release') as show:
            self.controller.poll()
        show.assert_not_called()
        self.assertIsNotNone(self.controller.latest)
        self.assertEqual(self.app.update_button.cget('text'), 'Có bản mới: v2026.11.14-r2 · Xem cập nhật')

    def test_startup_is_scheduled_once_and_shared_with_manual_check(self):
        self.controller.config = ReleaseConfig('2026.11.14-r1', 'example/AutoE7')
        self.controller.start()
        callback = self.controller.start_id
        self.controller.start()
        self.assertEqual(self.controller.start_id, callback)
        with patch('settings_ui.Thread') as worker:
            self.controller.startup_check()
            self.controller.startup_check()
            self.controller.check(manual=True)
        worker.assert_called_once()
        self.assertTrue(self.controller.busy)
        self.assertEqual(self.app.update_status.cget('text'), 'Đang kiểm tra cập nhật…')
        self.assertEqual(str(self.app.start_button.cget('state')), 'normal')

    def test_startup_available_is_inline_even_when_not_running(self):
        self.controller.results.put(UpdateResult('available', '2026.11.14-r1', 'v2026.11.14-r2',
            'https://github.com/example/AutoE7/releases/tag/v2026.11.14-r2', 'Notes'))
        with patch.object(self.controller, 'show_release') as show:
            self.controller.poll()
            show.assert_not_called()
            self.app.update_button.invoke()
            show.assert_called_once()
        self.assertEqual(self.app.update_button.winfo_manager(), 'pack')
        self.assertEqual(self.app.update_status.winfo_manager(), '')

    def test_latest_status_replaces_old_update_and_switches_language(self):
        self.controller.results.put(UpdateResult('available', '2026.11.14-r1', 'v2026.11.14-r2'))
        self.controller.poll()
        self.controller.results.put(UpdateResult('up_to_date', '2026.11.14-r2'))
        self.controller.poll()
        self.assertIsNone(self.controller.latest)
        self.assertEqual(self.app.update_button.winfo_manager(), '')
        self.assertEqual(self.app.update_status.cget('text'), 'Bạn đang dùng phiên bản mới nhất.')
        self.switch('en')
        self.assertEqual(self.app.update_status.cget('text'), 'You are using the latest version.')
        self.switch('vi')
        self.assertEqual(self.app.update_status.cget('text'), 'Bạn đang dùng phiên bản mới nhất.')

    def test_worker_failure_reports_inline_and_leaves_tool_usable(self):
        with patch('settings_ui.Thread') as worker, patch('settings_ui.check_for_updates', side_effect=OSError):
            self.controller.check()
            worker.call_args.kwargs['target']()
        with patch('settings_ui.messagebox.showinfo') as info:
            self.controller.poll()
            info.assert_not_called()
        self.assertFalse(self.controller.busy)
        self.assertIn('Vẫn có thể sử dụng', self.app.update_status.cget('text'))
        self.assertEqual(str(self.app.start_button.cget('state')), 'normal')

    def test_disabled_auto_check_does_not_leave_loading_status(self):
        self.app.settings = AppSettings(check_updates=False)
        self.controller.config = ReleaseConfig('2026.11.14-r1', 'example/AutoE7')
        with patch('settings_ui.Thread') as worker:
            self.controller.start()
            self.controller.startup_check()
            worker.assert_not_called()
        self.assertIsNone(self.controller.start_id)
        self.assertEqual(self.app.update_status.cget('text'), 'Tự kiểm tra cập nhật đang tắt.')

    def test_release_dialog_only_opens_browser_on_explicit_action(self):
        self.controller.latest = UpdateResult('available', '2026.11.14-r1', 'v2026.11.14-r2',
            'https://github.com/example/AutoE7/releases/tag/v2026.11.14-r2', 'Notes')
        with patch('settings_ui.webbrowser.open', return_value=True) as browser:
            self.controller.show_release()
            browser.assert_not_called()
            self.controller.open_download()
            browser.assert_called_once_with(self.controller.latest.release_url)

    def test_repeated_checks_share_one_background_request(self):
        with patch('settings_ui.Thread') as worker:
            self.controller.check()
            self.controller.check(manual=True)
        worker.assert_called_once()
        self.assertTrue(self.controller.manual)

    def test_manual_check_cancels_delayed_startup_check(self):
        self.controller.start_id = self.app.root.after(1200, self.controller.startup_check)
        callback = self.controller.start_id
        with patch('settings_ui.Thread'):
            self.controller.check(manual=True)
        self.assertNotIn(callback, self.app.root.tk.call('after', 'info'))

    def test_settings_opened_in_english_switches_feedback_back_to_vietnamese(self):
        self.switch('en')
        self.controller.open()
        self.assertEqual(self.controller.feedback.cget('text'), 'GitHub repository has not been configured.')
        with patch('settings_ui.save_settings', return_value=True):
            self.controller.save(language='vi')
        self.assertEqual(self.controller.feedback.cget('text'), 'Chưa cấu hình repo GitHub.')

    def test_dialog_is_complete_before_first_show(self):
        self.app.root.deiconify()
        self.app.root.update_idletasks()
        observed = []
        toplevel = tk.Toplevel
        def create(parent):
            window = toplevel(parent)
            def mapped(event):
                if event.widget == window:
                    frames = window.winfo_children()
                    observed.append(sum(len(frame.winfo_children()) for frame in frames))
            window.bind('<Map>', mapped)
            return window
        with patch('settings_ui.tk.Toplevel', side_effect=create):
            self.controller.open()
            self.app.root.update()
        self.assertTrue(observed)
        self.assertTrue(all(count >= 8 for count in observed), observed)
        self.assertEqual(self.app.settings_button.cget('text'), 'Cài đặt')
        self.switch('en')
        self.assertEqual(self.app.settings_button.cget('text'), 'Settings')


if __name__ == '__main__':
    unittest.main()
