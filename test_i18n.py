"""Translation checks independent of Tk and Windows capture dependencies."""
import unittest

from i18n import CATALOGUE, TEMPLATES, translate


class TranslationTests(unittest.TestCase):
    def test_vietnamese_default_and_unknown_are_unchanged(self):
        for text in ('Sẵn sàng', 'unrecognized text', '', None):
            self.assertEqual(translate(text), text)
            self.assertEqual(translate(text, 'invalid'), text)
        self.assertEqual(translate('unrecognized text', 'en'), 'unrecognized text')

    def test_all_catalogue_entries(self):
        for source, target in CATALOGUE.items():
            with self.subTest(source=source):
                self.assertEqual(translate(source, 'en'), target)
                self.assertEqual(translate(source, 'vi'), source)

    def test_all_templates_preserve_fields(self):
        from string import Formatter
        for source, target in TEMPLATES:
            fields = {name: 'opaque-' + name for _, name, _, _ in Formatter().parse(source) if name}
            with self.subTest(source=source):
                message = source.format_map(fields)
                self.assertEqual(translate(message, 'en'), target.format_map(fields))
                self.assertEqual(translate(message, 'vi'), message)

    def test_paths_titles_and_braces_are_not_rewritten(self):
        path = r'C:\Đi Map\Sẵn sàng\{version}.png'
        self.assertEqual(translate('Thiếu ảnh mẫu: ' + path, 'en'), 'Missing reference image: ' + path)
        self.assertEqual(translate('Epic Seven · Đi Map [1234]', 'en'), 'Epic Seven · Đi Map [1234]')
        self.assertEqual(translate(path, 'en'), path)

    def test_nested_errors_and_summaries(self):
        self.assertEqual(translate('Lỗi: Cửa sổ game không còn hợp lệ.', 'en'),
                         'Error: The game window is no longer valid.')
        self.assertEqual(translate('Shop: Cuộn tới đầu danh sách', 'en'), 'Shop: Scroll to top of the list')
        self.assertEqual(translate('Dừng Shop: Không xác nhận được cuối danh sách sau 5 lần cuộn.', 'en'),
                         'Shop stopped: Unable to confirm bottom of the list after 5 scrolls.')
        self.assertEqual(translate('Đã dừng.\nThắng 3 · Thua 1 · Tổng 4 trận', 'en'),
                         'Stopped.\nWins 3 · Losses 1 · Total 4 battles')
        self.assertEqual(translate('Rookie Arena · trận 2/∞ · Thắng 1 · Thua 1\n0/30 SkyStone · Chưa nhận diện được màn game.', 'en'),
                         'Rookie Arena · battle 2/∞ · Wins 1 · Losses 1\n0/30 SkyStone · Game screen not recognized yet.')

    def test_scenario_and_selection_labels(self):
        self.assertEqual(translate('Đi Map', 'en'), 'Adventure')
        self.assertEqual(translate('Đi Hunt', 'en'), 'Hunt')
        self.assertEqual(translate('Abyss (Tháp)', 'en'), 'Abyss (Tower)')
        self.assertEqual(translate('Cố định vị trí ưu tiên', 'en'), 'Fixed preferred position')


if __name__ == '__main__':
    unittest.main()
