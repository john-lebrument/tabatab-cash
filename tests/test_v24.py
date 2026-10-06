import hashlib
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import test_v14
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QInputDialog, QMenu, QMessageBox
from src.config import ConfigManager
from src.ui.browser_tab import ROLE_PATH
from publish_release import package_release


class FeaturesV24(unittest.TestCase):
    setUpClass = classmethod(test_v14.NewBehaviors.setUpClass.__func__)
    setUp = test_v14.NewBehaviors.setUp
    tearDown = test_v14.NewBehaviors.tearDown
    viewer = test_v14.NewBehaviors.viewer

    def test_image_f2_keeps_extension_and_rejects_collision(self):
        self.grid.select_path(self.paths[0])
        with patch.object(QInputDialog, 'getText', return_value=('Photo', True)):
            QTest.keyClick(self.grid, Qt.Key.Key_F2)
        target = self.root / 'Photo.png'
        self.assertTrue(target.is_file())
        self.assertFalse(Path(self.paths[0]).exists())
        self.assertEqual(self.grid.get_selected_file_paths(), [str(target)])
        with patch.object(QInputDialog, 'getText', return_value=('1', True)), patch.object(QMessageBox, 'warning') as warning:
            QTest.keyClick(self.grid, Qt.Key.Key_F2)
        warning.assert_called_once()
        self.assertTrue(target.is_file())
        self.assertTrue(Path(self.paths[1]).is_file())

    def test_tree_f2_remaps_tabs_favorites_and_history(self):
        folder = self.root / 'Folder'
        child = folder / 'Child'
        child.mkdir(parents=True)
        self.config.set('custom_favorites', [str(child)])
        other = self.window.add_tab(str(child), switch_to=False)
        other.history_back = [str(folder)]
        tree = self.tab.tree_view
        tree.setCurrentIndex(self.tab.tree_model.index(str(folder)))
        with patch.object(QInputDialog, 'getText', return_value=('Renamed', True)):
            QTest.keyClick(tree, Qt.Key.Key_F2)
        destination = self.root / 'Renamed'
        self.assertFalse(folder.exists())
        self.assertEqual(other.current_folder, str(destination / 'Child'))
        self.assertEqual(other.history_back, [str(destination)])
        self.assertEqual(self.config.get('custom_favorites'), [str(destination / 'Child')])

    def test_context_menus_add_clicked_folder_without_navigation(self):
        folder = self.root / 'Favorite'
        folder.mkdir()
        other = self.window.add_tab(str(self.root), switch_to=False)
        self.tab.refresh()
        self.grid.select_path(str(folder))
        selected = self.grid.currentItem()
        point = self.grid.visualItemRect(selected).center()
        seen = []
        def choose(menu, *args):
            action = next(action for action in menu.actions() if action.text() == 'Ajouter aux favoris')
            seen.append(action.text())
            action.trigger()
        with patch.object(QMenu, 'exec', choose):
            self.grid._show_context_menu(point)
            tree = self.tab.tree_view
            tree.setRootIndex(self.tab.tree_model.index(str(self.root)))
            QTest.qWait(200)
            index = self.tab.tree_model.index(str(folder))
            tree.scrollTo(index)
            self.app.processEvents()
            index = self.tab.tree_model.index(str(folder))
            self.tab._show_tree_context_menu(tree.visualRect(index).center())
        self.assertEqual(len(seen), 2)
        self.assertEqual(self.config.get('custom_favorites'), [str(folder)])
        self.assertEqual(self.tab.current_folder, str(self.root))
        self.assertIn(str(folder), [other.fav_list.item(i).data(ROLE_PATH) for i in range(other.fav_list.count())])
        with patch('src.config.get_settings_path', return_value=self.root / 'settings.json'):
            self.assertEqual(ConfigManager().get('custom_favorites'), [str(folder)])

    def test_fullscreen_f2_updates_grid_and_viewer(self):
        viewer = self.viewer()
        with patch.object(QInputDialog, 'getText', return_value=('Fullscreen', True)):
            QTest.keyClick(viewer.view, Qt.Key.Key_F2)
        target = self.root / 'Fullscreen.png'
        self.assertTrue(target.is_file())
        self.assertEqual(viewer.image_list[viewer.current_index], str(target))
        self.assertIn(str(target), self.grid.all_files)
        QTest.keyClick(viewer.view, Qt.Key.Key_Escape)
        self.assertEqual(self.grid.get_selected_file_paths(), [str(target)])

    def test_fullscreen_rename_cancel_leaves_file_unchanged(self):
        viewer = self.viewer()
        with patch.object(QInputDialog, 'getText', return_value=('Canceled', False)):
            QTest.keyClick(viewer.view, Qt.Key.Key_F2)
        self.assertEqual(viewer.image_list[0], self.paths[0])
        self.assertTrue(Path(self.paths[0]).is_file())

    def test_zoom_badge_visible_and_relative_to_fit(self):
        viewer = self.viewer()
        self.assertTrue(viewer.zoom_badge.isVisible())
        self.assertFalse(viewer.hud.isVisible())
        self.assertEqual(viewer.zoom_badge.text(), '100 %')
        baseline = viewer.view.transform().m11()
        QTest.keyClick(viewer.view, Qt.Key.Key_Plus)
        self.assertEqual(viewer.zoom_badge.text(), '125 %')
        self.assertAlmostEqual(viewer.view.transform().m11(), baseline * 1.25)
        QTest.keyClick(viewer.view, Qt.Key.Key_Minus)
        self.assertEqual(viewer.zoom_badge.text(), '100 %')
        QTest.keyClick(viewer.view, Qt.Key.Key_Minus)
        self.assertEqual(viewer.zoom_badge.text(), '80 %')
        QTest.keyClick(viewer.view, Qt.Key.Key_0)
        self.assertEqual(viewer.zoom_badge.text(), '100 %')
        viewer.hud.show()
        viewer.hud.hide()
        self.assertTrue(viewer.zoom_badge.isVisible())
        viewer.next_image()
        self.assertEqual(viewer.zoom_badge.text(), '100 %')
        self.assertEqual(viewer.lbl_zoom.text(), '100 %')

    def test_release_zip_excludes_personal_data_and_checksum_matches(self):
        bundle = self.root / 'Bundle'
        (bundle / '_internal').mkdir(parents=True)
        (bundle / 'TABaTAB Cash.exe').write_bytes(b'executable')
        (bundle / '_internal' / 'runtime.dll').write_bytes(b'runtime')
        (bundle / 'data').mkdir()
        (bundle / 'data' / 'settings.json').write_text('personal paths')
        archive, checksum = package_release(bundle, self.root / 'release')
        with zipfile.ZipFile(archive) as zipped:
            self.assertEqual(set(zipped.namelist()), {'Bundle/TABaTAB Cash.exe', 'Bundle/_internal/runtime.dll'})
            self.assertIsNone(zipped.testzip())
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        self.assertEqual(checksum.read_text().split()[0], digest)
