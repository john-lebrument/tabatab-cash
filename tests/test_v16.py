import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import test_v14
from PyQt6.QtCore import Qt, QPointF, QMimeData, QUrl, QModelIndex
from PyQt6.QtGui import QDropEvent
from PyQt6.QtWidgets import QInputDialog
from PyQt6.QtTest import QTest
from src.utils.file_ops import copy_file, move_file, rename_images, rename_folder
from src.ui.drag_feedback import set_large_drag_cursors
from src.ui.thumbnail_view import ROLE_PATH


class FeaturesV16(unittest.TestCase):
    setUpClass = classmethod(test_v14.NewBehaviors.setUpClass.__func__)
    setUp = test_v14.NewBehaviors.setUp
    tearDown = test_v14.NewBehaviors.tearDown

    def folder(self):
        folder = self.root / 'Source'
        (folder / 'Sub').mkdir(parents=True)
        (folder / 'Sub' / 'note.txt').write_text('folder content')
        return folder

    def test_folder_copy_move_and_descendant_rejection(self):
        source = self.folder()
        for operation in (copy_file, move_file):
            with self.assertRaises(OSError):
                operation(source, source / 'Sub')
            with self.assertRaises(OSError):
                operation(source, source)
        duplicate = copy_file(source, self.root)
        self.assertEqual((duplicate / 'Sub' / 'note.txt').read_text(), 'folder content')
        target = self.root / 'Destination'
        target.mkdir()
        moved = move_file(source, target)
        self.assertFalse(source.exists())
        self.assertEqual((moved / 'Sub' / 'note.txt').read_text(), 'folder content')
        self.assertTrue(duplicate.exists())

    def test_folder_f2_updates_tabs_and_favorites(self):
        source = self.folder()
        self.config.set('custom_favorites', [str(source / 'Sub')])
        child_tab = self.window.add_tab(str(source / 'Sub'), switch_to=False)
        self.tab.refresh()
        self.grid.select_path(str(source))
        with patch.object(QInputDialog, 'getText', return_value=('Renamed', True)):
            QTest.keyClick(self.grid, Qt.Key.Key_F2)
        destination = self.root / 'Renamed'
        self.assertFalse(source.exists())
        self.assertEqual(child_tab.current_folder, str(destination / 'Sub'))
        self.assertEqual(self.config.get('custom_favorites'), [str(destination / 'Sub')])
        self.assertEqual(self.grid.get_selected_file_paths(), [str(destination)])

    def test_folder_move_from_grid_to_tree(self):
        source = self.folder()
        target = self.root / 'Destination'
        target.mkdir()
        child_tab = self.window.add_tab(str(source / 'Sub'), switch_to=False)
        tree = self.tab.tree_view
        index = self.tab.tree_model.index(str(target))
        tree.scrollTo(index)
        self.app.processEvents()
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(source))])
        drop = QDropEvent(QPointF(tree.visualRect(index).center()), Qt.DropAction.CopyAction | Qt.DropAction.MoveAction,
                         mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        tree.dropEvent(drop)
        self.assertTrue(drop.isAccepted())
        self.assertFalse(source.exists())
        self.assertEqual(child_tab.current_folder, str(target / 'Source' / 'Sub'))

    def test_folder_collision_does_not_merge(self):
        source = self.folder()
        other = self.root / 'Other'
        other.mkdir()
        with self.assertRaises(FileExistsError):
            rename_folder(source, 'Other')
        self.assertTrue((source / 'Sub' / 'note.txt').exists())
        destination = self.root / 'Destination'
        (destination / 'Source').mkdir(parents=True)
        moved = move_file(source, destination)
        self.assertEqual(moved.name, 'Source_1')
        self.assertTrue((destination / 'Source').exists())

    def test_batch_default_three_digits_and_overflow(self):
        changes = rename_images(self.paths, 'Image')
        self.assertEqual([Path(new).name for old, new in changes], ['Image 001.png', 'Image 002.png', 'Image 003.png'])
        changes = rename_images([new for old, new in changes], 'Photo 999')
        self.assertEqual([Path(new).name for old, new in changes], ['Photo 999.png', 'Photo 1000.png', 'Photo 1001.png'])

    def test_breadcrumb_parent_click_and_edit_escape(self):
        source = self.folder()
        self.tab.navigate_to(str(source / 'Sub'))
        breadcrumb = self.tab.breadcrumb
        parent_button = breadcrumb.buttons[-2]
        QTest.mouseClick(parent_button, Qt.MouseButton.LeftButton)
        self.assertEqual(self.tab.current_folder, str(source))
        self.assertTrue(self.tab.history_back)
        QTest.keyClick(self.grid, Qt.Key.Key_D, Qt.KeyboardModifier.AltModifier)
        self.assertIs(breadcrumb.stack.currentWidget(), self.tab.path_edit)
        self.tab.path_edit.setText('cancel this')
        QTest.keyClick(self.tab.path_edit, Qt.Key.Key_Escape)
        self.assertEqual(self.tab.path_edit.text(), str(source))
        breadcrumb.start_edit()
        self.tab.path_edit.setText(str(self.root))
        QTest.keyClick(self.tab.path_edit, Qt.Key.Key_Return)
        self.assertEqual(self.tab.current_folder, str(self.root))
        self.assertIs(breadcrumb.stack.currentWidget(), breadcrumb.scroll)

    def test_favorites_order_saved_and_shared(self):
        source = self.folder()
        self.config.set('custom_favorites', [str(source), str(source / 'Sub')])
        self.tab._populate_favorites()
        other_tab = self.window.add_tab(str(self.root), switch_to=False)
        favorites = self.tab.fav_list
        # Same model operation as InternalMove; notification occurs after drop.
        self.assertTrue(favorites.model().moveRows(QModelIndex(), 0, 1, QModelIndex(), 2))
        favorites.order_changed.emit()
        self.assertEqual(favorites.item(0).data(ROLE_PATH), str(source / 'Sub'))
        self.assertEqual(other_tab.fav_list.item(0).data(ROLE_PATH), str(source / 'Sub'))
        self.tab._populate_favorites()
        self.assertEqual(favorites.item(0).data(ROLE_PATH), str(source / 'Sub'))
        self.assertTrue(self.config.get('favorite_order'))

    def test_large_copy_and_move_cursor_images(self):
        drag = MagicMock()
        set_large_drag_cursors(drag)
        self.assertEqual(drag.setDragCursor.call_count, 2)
        for call in drag.setDragCursor.call_args_list:
            self.assertEqual(call.args[0].width(), 48)
            self.assertFalse(call.args[0].isNull())

    def test_tree_starts_folder_drag(self):
        source = self.folder()
        self.tab.tree_view.setCurrentIndex(self.tab.tree_model.index(str(source)))
        with patch('src.ui.browser_tab.QDrag') as drag:
            self.tab.tree_view.startDrag(Qt.DropAction.MoveAction)
            mime = drag.return_value.setMimeData.call_args.args[0]
            self.assertEqual(Path(mime.urls()[0].toLocalFile()), source)
            drag.return_value.exec.assert_called_once()


if __name__ == '__main__':
    unittest.main()
