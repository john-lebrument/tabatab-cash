import json
import unittest
from pathlib import Path
from unittest.mock import patch
import test_v14
from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QImage
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QMenu
from src.ui.browser_tab import ROLE_PATH
from src.utils.favorites import export_favorites, import_favorites

class FeaturesV25(unittest.TestCase):
    setUpClass = classmethod(test_v14.NewBehaviors.setUpClass.__func__)
    setUp = test_v14.NewBehaviors.setUp
    tearDown = test_v14.NewBehaviors.tearDown

    def test_sort_context_on_background_and_image_preserves_selection(self):
        self.grid.select_path(self.paths[1])
        def choose(menu, *args):
            submenu = next(a.menu() for a in menu.actions() if a.text() == 'Trier les miniatures')
            next(a for a in submenu.actions() if a.text() == 'Décroissant ↓').trigger()
        for point in [QPoint(-1, -1), self.grid.visualItemRect(self.grid.currentItem()).center()]:
            with patch.object(QMenu, 'exec', choose):
                self.grid._show_context_menu(point)
            self.assertEqual(self.grid.sort_order, 'desc')
            self.assertEqual(self.tab.combo_order.currentData(), 'desc')
            self.assertEqual(self.config.get('sort_order'), 'desc')
            self.assertEqual(self.grid.get_selected_file_paths(), [self.paths[1]])
        self.assertEqual(self.grid.all_files, list(reversed(self.paths)))

    def test_export_import_merge_order_and_invalid_is_atomic(self):
        folder = self.root / 'Favorite'
        folder.mkdir()
        missing = str(self.root / 'Disconnected')
        self.config.set('custom_favorites', [str(folder), missing])
        self.config.set('favorite_order', [[missing, True], [str(folder), True]])
        filename = self.root / 'favorites.json'
        export_favorites(self.config, filename)
        self.config.set('custom_favorites', [str(self.root)])
        self.config.set('favorite_order', [])
        import_favorites(self.config, filename)
        import_favorites(self.config, filename)
        self.assertEqual(self.config.get('custom_favorites'), [str(self.root), str(folder), missing])
        self.assertEqual(self.config.get('favorite_order'), [[missing, True], [str(folder), True]])
        before = dict(self.config.settings)
        payload = json.loads(filename.read_text(encoding='utf-8'))
        payload['favorite_order'] = [['broken']]
        filename.write_text(json.dumps(payload), encoding='utf-8')
        with self.assertRaises(ValueError):
            import_favorites(self.config, filename)
        self.assertEqual(self.config.settings, before)

    def test_paste_shortcut_into_favorite_copies_and_avoids_overwrite(self):
        folder = self.root / 'Favorite'
        folder.mkdir()
        self.tab.add_folder_to_favorites(str(folder))
        other = self.window.add_tab(str(folder), switch_to=False)
        self.grid.select_path(self.paths[0])
        self.grid.copy_selected()
        fav = self.tab.fav_list
        item = next(fav.item(i) for i in range(fav.count()) if fav.item(i).data(ROLE_PATH) == str(folder))
        fav.setCurrentItem(item)
        for _ in range(2):
            QTest.keyClick(fav, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
        self.assertTrue(Path(self.paths[0]).exists())
        self.assertEqual(len(list(folder.glob('*.png'))), 2)
        self.assertEqual(len(other.thumb_view.all_files), 2)
        self.assertEqual(self.tab.current_folder, str(self.root))
        QApplication.clipboard().clear()

    def test_favorite_menu_copies_selected_without_navigation(self):
        folder = self.root / 'Favorite'
        folder.mkdir()
        self.tab.add_folder_to_favorites(str(folder))
        self.grid.select_path(self.paths[0])
        fav = self.tab.fav_list
        item = next(fav.item(i) for i in range(fav.count()) if fav.item(i).data(ROLE_PATH) == str(folder))
        def choose(menu, *args):
            next(a for a in menu.actions() if a.text() == 'Copier les images sélectionnées dans ce dossier').trigger()
        with patch.object(QMenu, 'exec', choose):
            self.tab._show_fav_context_menu(fav.visualItemRect(item).center())
        self.assertTrue((folder / '0.png').exists())
        self.assertTrue(Path(self.paths[0]).exists())
        self.assertEqual(self.tab.current_folder, str(self.root))

    def test_bitmap_clipboard_pastes_unique_png_and_refreshes(self):
        folder = self.root / 'Favorite'
        folder.mkdir()
        other = self.window.add_tab(str(folder), switch_to=False)
        image = QImage(10, 10, QImage.Format.Format_RGB32)
        image.fill(Qt.GlobalColor.red)
        QApplication.clipboard().setImage(image)
        self.grid.paste_images(str(folder))
        self.grid.paste_images(str(folder))
        self.assertEqual(len(other.thumb_view.all_files), 2)
        self.assertTrue((folder / 'Image collée.png').exists())
        self.assertTrue((folder / 'Image collée (1).png').exists())
        QApplication.clipboard().clear()
