import unittest
from pathlib import Path
from unittest.mock import patch
import test_v14
from PyQt6.QtCore import Qt, QPoint, QPointF, QMimeData, QUrl
from PyQt6.QtGui import QDropEvent, QDragMoveEvent
from PyQt6.QtWidgets import QInputDialog, QMessageBox, QMenu
from PyQt6.QtTest import QTest


class FeaturesV17(unittest.TestCase):
    setUpClass = classmethod(test_v14.NewBehaviors.setUpClass.__func__)
    setUp = test_v14.NewBehaviors.setUp
    tearDown = test_v14.NewBehaviors.tearDown

    def folder(self):
        folder = self.root / 'Source'
        folder.mkdir()
        (folder / 'note.txt').write_text('content')
        return folder

    def test_grid_context_create_and_select(self):
        def choose(menu, *args):
            next(a for a in menu.actions() if a.text() == 'Nouveau dossier…').trigger()
        with patch.object(QMenu, 'exec', choose), patch.object(QInputDialog, 'getText', return_value=('New folder', True)):
            self.grid._show_context_menu(QPoint(700, 600))
        self.assertTrue((self.root / 'New folder').is_dir())
        self.assertEqual(self.grid.get_selected_file_paths(), [str(self.root / 'New folder')])

    def test_tree_context_creates_inside_clicked_folder(self):
        folder = self.folder()
        tree = self.tab.tree_view
        index = self.tab.tree_model.index(str(folder))
        tree.scrollTo(index)
        self.app.processEvents()
        def choose(menu, *args):
            next(a for a in menu.actions() if a.text() == 'Nouveau dossier…').trigger()
        with patch.object(QMenu, 'exec', choose), patch.object(QInputDialog, 'getText', return_value=('Child', True)):
            self.tab._show_tree_context_menu(tree.visualRect(index).center())
        self.assertTrue((folder / 'Child').is_dir())
        self.assertFalse((self.root / 'Child').exists())

    def test_create_collision_invalid_and_cancel_preserve_content(self):
        folder = self.folder()
        for name, accepted in [('Source', True), ('../escape', True), ('Unused', False)]:
            with patch.object(QInputDialog, 'getText', return_value=(name, accepted)), patch.object(QMessageBox, 'warning'):
                self.grid._create_folder()
        self.assertEqual((folder / 'note.txt').read_text(), 'content')
        self.assertFalse((self.root / 'Unused').exists())

    def test_grid_delete_requires_confirmation_and_uses_bin(self):
        folder = self.folder()
        self.tab.refresh()
        self.grid.select_path(str(folder))
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.No), patch('src.ui.folder_actions.QFile') as file:
            QTest.keyClick(self.grid, Qt.Key.Key_Delete)
            file.assert_not_called()
        self.assertTrue(folder.exists())
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes) as confirm, patch('src.ui.folder_actions.QFile') as file:
            file.return_value.moveToTrash.side_effect = lambda: (folder.rename(self.root / 'simulated-bin') or True)
            QTest.keyClick(self.grid, Qt.Key.Key_Delete)
            confirm.assert_called_once()
            file.return_value.moveToTrash.assert_called_once()
        self.assertFalse(folder.exists())
        self.assertEqual((self.root / 'simulated-bin' / 'note.txt').read_text(), 'content')

    def test_tree_delete_key_and_browser_fallback(self):
        folder = self.folder()
        other_tab = self.window.add_tab(str(folder), switch_to=False)
        self.tab.tree_view.setCurrentIndex(self.tab.tree_model.index(str(folder)))
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes), patch('src.ui.folder_actions.QFile') as file:
            file.return_value.moveToTrash.side_effect = lambda: (folder.rename(self.root / 'simulated-bin') or True)
            QTest.keyClick(self.tab.tree_view, Qt.Key.Key_Delete)
        self.assertEqual(other_tab.current_folder, str(self.root))
        self.assertIs(self.window.get_current_tab_widget(), self.tab)

    def test_tree_delete_menu_failure_keeps_folder(self):
        folder = self.folder()
        tree = self.tab.tree_view
        index = self.tab.tree_model.index(str(folder))
        tree.scrollTo(index)
        self.app.processEvents()
        def choose(menu, *args):
            next(a for a in menu.actions() if a.text() == 'Supprimer le dossier (Suppr)').trigger()
        with patch.object(QMenu, 'exec', choose), patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes), patch.object(QMessageBox, 'warning') as warning, patch('src.ui.folder_actions.QFile') as file:
            file.return_value.moveToTrash.return_value = False
            file.return_value.errorString.return_value = 'Unavailable'
            self.tab._show_tree_context_menu(tree.visualRect(index).center())
            warning.assert_called_once()
        self.assertTrue(folder.is_dir())

    def test_file_and_folder_drop_keep_origin_even_after_hover(self):
        folder = self.folder()
        destination = self.root / 'Destination'
        destination.mkdir()
        self.window.add_tab(str(destination), switch_to=False)
        bar = self.window.custom_tab_bar
        self.app.processEvents()
        for source, copy in [(Path(self.paths[0]), True), (folder, False)]:
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(str(source))])
            mods = Qt.KeyboardModifier.ControlModifier if copy else Qt.KeyboardModifier.NoModifier
            point = bar.tabRect(1).center()
            move = QDragMoveEvent(point, Qt.DropAction.CopyAction | Qt.DropAction.MoveAction, mime, Qt.MouseButton.LeftButton, mods)
            bar.dragMoveEvent(move)
            QTest.qWait(600)
            self.assertEqual(bar.currentIndex(), 0)
            drop = QDropEvent(QPointF(point), Qt.DropAction.CopyAction | Qt.DropAction.MoveAction, mime, Qt.MouseButton.LeftButton, mods)
            bar.dropEvent(drop)
            self.assertTrue((destination / source.name).exists())
            self.assertEqual(source.exists(), copy)
            self.assertEqual(bar.currentIndex(), 0)


if __name__ == '__main__':
    unittest.main()
