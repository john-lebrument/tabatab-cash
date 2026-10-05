import unittest
from pathlib import Path
from unittest.mock import patch
import test_v14
from PIL import Image
from PyQt6.QtCore import Qt, QPoint, QPointF, QMimeData, QUrl, QEvent
from PyQt6.QtGui import QDragMoveEvent, QDragLeaveEvent, QDropEvent, QEnterEvent
from PyQt6.QtWidgets import QApplication, QInputDialog, QMenu
from PyQt6.QtTest import QTest
from src.utils.file_ops import rename_images, convert_image_format


class FeaturesV15(unittest.TestCase):
    setUpClass = classmethod(test_v14.NewBehaviors.setUpClass.__func__)
    setUp = test_v14.NewBehaviors.setUp
    tearDown = test_v14.NewBehaviors.tearDown
    viewer = test_v14.NewBehaviors.viewer

    def test_f2_single_preserves_extension_and_open_viewer(self):
        viewer = self.viewer()
        viewer.close_fullscreen()
        self.grid.setCurrentRow(0)
        before = Path(self.paths[0]).read_bytes()
        with patch.object(QInputDialog, 'getText', return_value=('Portrait', True)):
            QTest.keyClick(self.grid, Qt.Key.Key_F2)
        destination = self.root / 'Portrait.png'
        self.assertEqual(destination.read_bytes(), before)
        self.assertFalse(Path(self.paths[0]).exists())
        self.assertEqual(viewer.image_list[0], str(destination))
        self.assertEqual(self.grid.get_selected_file_paths(), [str(destination)])

    def test_f2_batch_uses_display_order_and_number(self):
        for path, color in zip(self.paths, ('red', 'green', 'blue')):
            Image.new('RGB', (30, 30), color).save(path)
        self.grid.set_sort('name', 'desc')
        self.grid.selectAll()
        before = [Path(p).read_bytes() for p in self.grid.all_files]
        with patch.object(QInputDialog, 'getText', return_value=('Vacances 007', True)):
            QTest.keyClick(self.grid, Qt.Key.Key_F2)
        for i, content in enumerate(before):
            self.assertEqual((self.root / f'Vacances {7+i:03d}.png').read_bytes(), content)
        self.assertEqual(len(self.grid.selectedItems()), 3)

    def test_rename_collision_and_invalid_names_leave_all_originals(self):
        occupied = self.root / 'Photo 002.png'
        occupied.write_bytes(b'keep me')
        with self.assertRaises(FileExistsError):
            rename_images(self.paths, 'Photo')
        self.assertTrue(all(Path(p).exists() for p in self.paths))
        self.assertFalse((self.root / 'Photo 001.png').exists())
        self.assertEqual(occupied.read_bytes(), b'keep me')
        for name in ('../escape', 'CON', 'bad:name', ''):
            with self.assertRaises(ValueError):
                rename_images(self.paths, name)

    def test_conversion_batch_menu_keep_and_remove_initial(self):
        self.grid.selectAll()
        def select_jpeg_keep(menu, *args):
            conversion = next(a.menu() for a in menu.actions() if 'Convertir' in a.text())
            jpeg = next(a.menu() for a in conversion.actions() if 'JPEG' in a.text())
            jpeg.actions()[0].trigger()
        with patch.object(QMenu, 'exec', select_jpeg_keep):
            self.grid._show_context_menu(self.grid.visualItemRect(self.grid.item(0)).center())
        for path in self.paths:
            self.assertTrue(Path(path).exists())
            with Image.open(Path(path).with_suffix('.jpg')) as image:
                self.assertEqual(image.format, 'JPEG')
        # PNGs already exist: converting JPGs back must not overwrite them.
        originals = {p: Path(p).read_bytes() for p in self.paths}
        self.grid._convert_images([str(Path(p).with_suffix('.jpg')) for p in self.paths], '.png', True)
        for path in self.paths:
            self.assertEqual(Path(path).read_bytes(), originals[path])
            self.assertFalse(Path(path).with_suffix('.jpg').exists())
            with Image.open(self.root / f'{Path(path).stem}_1.png') as image:
                self.assertEqual(image.format, 'PNG')

    def test_conversion_failure_keeps_original_and_cleans_temporary(self):
        original = Path(self.paths[0]).read_bytes()
        with patch('PIL.Image.Image.save', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                convert_image_format(self.paths[0], '.jpg', True)
        self.assertEqual(Path(self.paths[0]).read_bytes(), original)
        self.assertFalse((self.root / '0.jpg').exists())
        self.assertFalse(list(self.root.glob('.xnviewtab-convert-*')))

    def mime(self):
        data = QMimeData()
        data.setUrls([QUrl.fromLocalFile(self.paths[0])])
        return data

    def test_grid_destination_highlight_and_ctrl_switch(self):
        folder = self.root / 'destination'
        folder.mkdir()
        self.tab.refresh()
        pos = self.grid.visualItemRect(self.grid.item(0)).center()
        mime = self.mime()
        for mods, action in ((Qt.KeyboardModifier.ControlModifier, Qt.DropAction.CopyAction),
                             (Qt.KeyboardModifier.NoModifier, Qt.DropAction.MoveAction)):
            event = QDragMoveEvent(pos, Qt.DropAction.CopyAction | Qt.DropAction.MoveAction, mime,
                                   Qt.MouseButton.LeftButton, mods)
            self.grid.dragMoveEvent(event)
            self.assertEqual(event.dropAction(), action)
            self.assertIs(self.grid._drop_folder, self.grid.item(0))
        self.grid.dragLeaveEvent(QDragLeaveEvent())
        self.assertIsNone(self.grid._drop_folder)
        drop = QDropEvent(QPointF(pos), Qt.DropAction.CopyAction | Qt.DropAction.MoveAction, mime,
                         Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier)
        self.grid.dropEvent(drop)
        self.assertTrue(Path(self.paths[0]).exists())
        self.assertTrue((folder / '0.png').exists())

    def test_tree_and_tab_highlight_ctrl_press_and_release(self):
        tree = self.tab.tree_view
        index = self.tab.tree_model.index(str(self.root))
        tree.scrollTo(index)
        self.app.processEvents()
        pos = tree.visualRect(index).center()
        bar = self.window.custom_tab_bar
        mime = self.mime()
        for target, point in ((tree, pos), (bar, bar.tabRect(0).center())):
            for mods, action in ((Qt.KeyboardModifier.ControlModifier, Qt.DropAction.CopyAction),
                                 (Qt.KeyboardModifier.NoModifier, Qt.DropAction.MoveAction)):
                event = QDragMoveEvent(point, Qt.DropAction.CopyAction | Qt.DropAction.MoveAction,
                                       mime, Qt.MouseButton.LeftButton, mods)
                target.dragMoveEvent(event)
                self.assertEqual(event.dropAction(), action)
            if target is tree:
                self.assertEqual(tree._drop_index, index)
            else:
                self.assertEqual(bar.drag_target_tab, 0)
            target.dragLeaveEvent(QDragLeaveEvent())
        self.assertFalse(tree._drop_index.isValid())

    def test_same_folder_ctrl_drop_copies_but_release_does_not(self):
        mime = self.mime()
        for mods, copy in ((Qt.KeyboardModifier.ControlModifier, True),
                           (Qt.KeyboardModifier.NoModifier, False)):
            drop = QDropEvent(QPointF(600, 500), Qt.DropAction.CopyAction | Qt.DropAction.MoveAction,
                             mime, Qt.MouseButton.LeftButton, mods)
            drop.setDropAction(Qt.DropAction.CopyAction)  # stale Qt action after Ctrl release
            self.grid.dropEvent(drop)
            self.assertEqual(drop.isAccepted(), copy)
        self.assertTrue((self.root / '0 - Copie.png').exists())
        self.assertFalse((self.root / '0 - Copie (2).png').exists())
        self.assertTrue(Path(self.paths[0]).exists())

    def test_b_controls_only_while_hovering(self):
        self.window._on_request_floating(self.paths, self.paths[0])
        viewer = next(iter(self.window.floating_viewers))
        self.app.processEvents()
        enter = QEnterEvent(QPointF(30, 30), QPointF(30, 30), QPointF(30, 30))
        QApplication.sendEvent(viewer, enter)
        for control in (viewer.floating_close, viewer.move_handle, viewer.size_grip):
            self.assertTrue(control.isVisible())
        self.assertIn('#ff4040', viewer.floating_close.styleSheet())
        self.assertFalse(viewer.counter.isVisible())
        QApplication.sendEvent(viewer, QEvent(QEvent.Type.Leave))
        for control in (viewer.floating_close, viewer.move_handle, viewer.size_grip):
            self.assertFalse(control.isVisible())


if __name__ == '__main__':
    unittest.main()
