"""Per-mode restoration must preserve independent values and never start a game."""
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app_settings import load_settings, save_settings
from mode_preferences import ModePreferences
from tests import test_preferences_ui


class ModePreferencesTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_preferences_ui.PreferencesUITests()
        self.fixture.setUp()
        self.app = self.fixture.app
        self.temporary = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.path = Path(self.temporary.name) / 'settings.json'
        self.controller = ModePreferences(self.app, self.path)

    def tearDown(self):
        self.controller.close()
        self.fixture.tearDown()
        self.temporary.cleanup()

    def select(self, mode):
        self.app.scenario.current(self.app.scenario.source_values.index(mode))
        self.controller.select_mode()

    def test_modes_keep_independent_counts_and_run_options(self):
        episode = self.app.scenario.get()
        self.app.limit.set('5')
        self.app.forever.set(True)
        self.app.no_mouse.set(True)
        self.select('Abyss (Tháp)')
        self.assertEqual(self.app.limit.get(), '1')
        self.assertFalse(self.app.forever.get())
        self.assertFalse(self.app.no_mouse.get())
        self.app.limit.set('8')
        self.select(episode)
        self.assertEqual(self.app.limit.get(), '5')
        self.assertTrue(self.app.forever.get())
        self.assertTrue(self.app.no_mouse.get())
        self.select('Abyss (Tháp)')
        self.assertEqual(self.app.limit.get(), '8')

    def test_shop_and_arena_specific_preferences_survive_switches(self):
        self.select('Reroll Secret Shop')
        self.app.shop_budget.insert(0, '300')
        self.app.shop_selected['covenant'].set(False)
        self.select('Rookie Arena')
        self.app.arena_mode.current(1)
        self.app.arena_preferred.set('3')
        self.app.arena_refill.set(True)
        self.app.arena_budget.delete(0, 'end')
        self.app.arena_budget.insert(0, '60')
        self.select('Reroll Secret Shop')
        self.assertEqual(self.app.shop_budget.get(), '300')
        self.assertFalse(self.app.shop_selected['covenant'].get())
        self.select('Rookie Arena')
        self.assertEqual(self.app.arena_mode.current(), 1)
        self.assertEqual(self.app.arena_preferred.get(), '3')
        self.assertTrue(self.app.arena_refill.get())
        self.assertEqual(self.app.arena_budget.get(), '60')

    def test_restart_restores_last_mode_without_starting_automation(self):
        self.select('Rookie Arena')
        self.app.limit.set('12')
        self.app.dry.set(False)
        self.app.advanced_open.set(True)
        self.app.region.delete(0, 'end')
        self.app.region.insert(0, '0,0.04,0.97,1')
        self.assertTrue(self.controller.close())
        settings = load_settings(self.path)
        self.fixture.tearDown()
        self.fixture = test_preferences_ui.PreferencesUITests()
        self.fixture.setUp()
        self.app = self.fixture.app
        self.app.settings = settings
        with patch.object(self.app, 'start') as start:
            self.controller = ModePreferences(self.app, self.path)
        start.assert_not_called()
        self.assertEqual(self.app.scenario.get(), 'Rookie Arena')
        self.assertEqual(self.app.limit.get(), '12')
        self.assertFalse(self.app.dry.get())
        self.assertTrue(self.app.advanced_open.get())
        self.assertEqual(self.app.region.get(), '0,0.04,0.97,1')
        self.assertFalse(self.app.running)

    def test_auto_save_and_general_settings_preserve_each_other(self):
        self.app.limit.set('7')
        self.assertIsNotNone(self.controller.pending)
        with patch('settings_ui.save_settings', side_effect=lambda settings: save_settings(settings, self.path)):
            self.fixture.controller.save(language='en', auto=False)
        self.assertTrue(self.controller.flush())
        saved = load_settings(self.path)
        self.assertEqual(saved.language, 'en')
        self.assertFalse(saved.check_updates)
        self.assertEqual(saved.mode_settings[self.app.scenario.get()]['limit'], '7')

    def test_unknown_saved_mode_falls_back_to_first_activity(self):
        self.controller.close()
        self.app.settings = replace(self.app.settings, last_mode='removed mode')
        self.controller = ModePreferences(self.app, self.path)
        self.assertEqual(self.app.scenario.get(), self.app.scenario.source_values[0])

    def test_edited_values_are_saved_automatically_without_close(self):
        self.app.limit.set('9')
        self.app.root.after(700, self.app.root.quit)
        self.app.root.mainloop()
        saved = load_settings(self.path)
        self.assertEqual(saved.mode_settings[self.app.scenario.get()]['limit'], '9')
        self.assertIsNone(self.controller.pending)

    def test_write_failure_is_reported_and_preserves_previous_file(self):
        self.assertTrue(self.controller.flush())
        old = self.path.read_bytes()
        self.app.limit.set('25')
        with patch('mode_preferences.save_settings', return_value=False), patch.object(self.app, 'log') as log:
            self.assertFalse(self.controller.flush())
            self.assertFalse(self.controller.flush())
        self.assertEqual(self.path.read_bytes(), old)
        log.assert_called_once()


if __name__ == '__main__':
    unittest.main()
