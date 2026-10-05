import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PIL import Image, ImageChops
from PyQt6.QtCore import Qt, QPoint, QPointF, QRectF, QEvent, QCoreApplication, QMimeData, QUrl
from PyQt6.QtGui import QMouseEvent, QDropEvent
from PyQt6.QtWidgets import QApplication, QDialog, QMenu
from PyQt6.QtTest import QTest
from src.config import ConfigManager
from src.ui.main_window import MainWindow
from src.ui.fullscreen_viewer import CropConfirmDialog
from src.ui.blur_tool import save_blur
from src.utils import file_ops


class NewBehaviors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.paths = []
        for i in range(3):
            path = self.root / f'{i}.png'
            image = Image.new('RGB', (320, 240), 'white')
            image.paste('black', (100, 80, 170, 160))
            image.save(path)
            self.paths.append(str(path))
        with patch('src.config.get_settings_path', return_value=self.root / 'settings.json'):
            self.config = ConfigManager()
        self.config.settings['tabs'] = [str(self.root)]
        self.window = MainWindow(self.config)
        self.window.show()
        self.app.processEvents()
        self.tab = self.window.get_current_tab_widget()
        self.grid = self.tab.thumb_view

    def tearDown(self):
        self.window.thumbnail_manager.pool.waitForDone()
        self.window.close()
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        file_ops._deleted_images.clear()
        self.temp.cleanup()

    def viewer(self):
        self.window._on_request_fullscreen(self.paths, self.paths[0])
        self.app.processEvents()
        return self.window.fullscreen_viewer

    def test_home_end_bounds_and_selection_on_exit(self):
        viewer = self.viewer()
        QTest.keyClick(viewer.view, Qt.Key.Key_End)
        self.assertEqual(viewer.current_index, 2)
        self.assertEqual(viewer.toast.text(), 'Fin du répertoire')
        viewer.next_image()
        self.assertEqual(viewer.current_index, 2)
        QTest.keyClick(viewer.view, Qt.Key.Key_Home)
        viewer.prev_image()
        self.assertEqual(viewer.current_index, 0)
        viewer.next_image()
        QTest.keyClick(viewer.view, Qt.Key.Key_Escape)
        self.assertEqual(self.grid.get_selected_file_paths(), [self.paths[1]])

    def test_ctrl_drag_starts_even_when_ctrl_deselects(self):
        self.grid.setCurrentRow(0)
        pos = self.grid.visualItemRect(self.grid.item(0)).center()
        QTest.mousePress(self.grid.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier, pos)
        move = QMouseEvent(QEvent.Type.MouseMove, QPointF(pos + QPoint(40, 0)), QPointF(pos + QPoint(40, 0)),
                          Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier)
        with patch('src.ui.thumbnail_view.QDrag') as drag:
            QApplication.sendEvent(self.grid.viewport(), move)
            drag.return_value.exec.assert_called_once()
            urls = drag.return_value.setMimeData.call_args.args[0].urls()
            self.assertEqual(Path(urls[0].toLocalFile()), Path(self.paths[0]))
        QTest.mouseRelease(self.grid.viewport(), Qt.MouseButton.LeftButton, pos=pos)

    def test_multi_b_and_hover_controls(self):
        self.grid.setCurrentRow(0)
        self.grid.item(1).setSelected(True)
        QTest.keyClick(self.grid, Qt.Key.Key_B)
        self.assertEqual(len(self.window.floating_viewers), 2)
        for viewer in self.window.floating_viewers:
            self.assertFalse(viewer.counter.isVisible())
            self.assertFalse(viewer.move_handle.isVisible())
            self.assertFalse(viewer.size_grip.isVisible())
            QApplication.sendEvent(viewer, QEvent(QEvent.Type.Leave))
            self.assertFalse(viewer.floating_close.isVisible())

    def test_delete_recycle_undo_and_permanent(self):
        self.grid.setCurrentRow(0)
        before = Path(self.paths[0]).read_bytes()
        # QFile's OS boundary is faked; all file/undo/UI operations are real.
        with patch('src.utils.file_ops.QFile') as file, patch('PyQt6.QtWidgets.QMessageBox.question') as confirm:
            file.return_value.moveToTrash.side_effect = lambda: (Path(self.paths[0]).unlink() or True)
            QTest.keyClick(self.grid, Qt.Key.Key_Delete)
            confirm.assert_not_called()
            self.assertFalse(Path(self.paths[0]).exists())
        QTest.keyClick(self.grid, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(Path(self.paths[0]).read_bytes(), before)
        self.assertIn('Image restaurée', self.window.status_bar.currentMessage())
        with patch('src.ui.thumbnail_view.trash_image') as trash:
            QTest.keyClick(self.grid, Qt.Key.Key_Delete, Qt.KeyboardModifier.ShiftModifier)
            trash.assert_not_called()
        self.assertFalse(Path(self.paths[0]).exists())

    def test_last_delete_toast_and_undo(self):
        viewer = self.viewer()
        viewer.show_images([self.paths[0]], self.paths[0])
        with patch('src.utils.file_ops.QFile') as file:
            file.return_value.moveToTrash.side_effect = lambda: (Path(self.paths[0]).unlink() or True)
            QTest.keyClick(viewer.view, Qt.Key.Key_Delete)
        self.assertTrue(viewer.toast.isVisible())
        self.assertEqual(viewer.toast.text(), 'Image supprimée')
        QTest.qWait(1100)
        self.assertFalse(viewer.toast.isVisible())
        QTest.keyClick(viewer.view, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(viewer.image_list, [self.paths[0]])
        self.assertTrue(Path(self.paths[0]).exists())
        self.assertEqual(viewer.toast.text(), 'Image restaurée')

    def test_blur_preview_cancel_and_saved_pixels(self):
        viewer = self.viewer()
        before = Path(self.paths[0]).read_bytes()
        QTest.keyClick(viewer.view, Qt.Key.Key_F)
        self.assertIsNotNone(viewer.blur_item)
        viewer.blur_item.setRect(QRectF(70, 60, 130, 130))
        viewer.blur_slider.setValue(80)
        viewer._preview_blur()
        self.assertNotEqual(viewer.pixmap_item.pixmap().toImage(), viewer.current_pixmap.toImage())
        QTest.keyClick(viewer.view, Qt.Key.Key_Escape)
        self.assertEqual(viewer.pixmap_item.pixmap().toImage(), viewer.current_pixmap.toImage())
        self.assertEqual(Path(self.paths[0]).read_bytes(), before)
        viewer.start_blur()
        viewer.blur_item.setRect(QRectF(70, 60, 130, 130))
        def copy(dialog):
            dialog.choice = 'copy'
            return QDialog.DialogCode.Accepted
        with patch.object(CropConfirmDialog, 'exec', copy):
            viewer.apply_blur()
        with Image.open(self.paths[0]) as original, Image.open(self.root / '0_flou.png') as result:
            difference = ImageChops.difference(original, result)
            bounds = difference.getbbox()
            self.assertIsNotNone(bounds)
            self.assertGreaterEqual(bounds[0], 70)
            self.assertLessEqual(bounds[2], 200)
            self.assertEqual(original.size, result.size)
        self.assertEqual(Path(self.paths[0]).read_bytes(), before)

    def test_blur_save_failure_keeps_original(self):
        original = Path(self.paths[0]).read_bytes()
        with patch('PIL.Image.Image.save', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                save_blur(self.paths[0], (60, 60, 200, 200), 50, overwrite=True)
        self.assertEqual(Path(self.paths[0]).read_bytes(), original)

    def test_large_floating_image_fits_screen(self):
        Image.new('RGB', (6000, 1500), 'green').save(self.paths[0])
        self.window._on_request_floating(self.paths, self.paths[0])
        viewer = next(iter(self.window.floating_viewers))
        self.app.processEvents()
        available = viewer.screen().availableGeometry()
        self.assertLessEqual(viewer.width(), available.width())
        self.assertLessEqual(viewer.height(), available.height())
        self.assertLess(viewer.zoom_factor, 1)
        self.assertFalse(viewer.view.horizontalScrollBar().isVisible())

    def test_favorite_removal_and_folder_new_tab_menus(self):
        self.tab.add_current_to_favorites()
        self.assertIn(str(self.root), self.config.get('custom_favorites'))
        def remove(menu, *args):
            next(a for a in menu.actions() if 'Retirer des favoris' in a.text()).trigger()
        pos = self.tab.fav_list.visualItemRect(self.tab.fav_list.item(0)).center()
        with patch.object(QMenu, 'exec', remove):
            self.tab._show_fav_context_menu(pos)
        self.assertNotIn(str(self.root), self.config.get('custom_favorites'))
        self.assertTrue(self.root.exists())
        folder = self.root / 'subfolder'
        folder.mkdir()
        self.tab.refresh()
        def new_tab(menu, *args):
            next(a for a in menu.actions() if a.text() == 'Ouvrir dans un nouvel onglet').trigger()
        pos = self.grid.visualItemRect(self.grid.item(0)).center()
        with patch.object(QMenu, 'exec', new_tab):
            self.grid._show_context_menu(pos)
        self.assertEqual(Path(self.window.get_current_tab_widget().current_folder), folder)

    def test_move_to_folder_and_close_all_menu(self):
        destination = self.root / 'destination'
        destination.mkdir()
        self.tab.refresh()
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(self.paths[0])])
        pos = self.grid.visualItemRect(self.grid.item(0)).center()
        drop = QDropEvent(QPointF(pos), Qt.DropAction.MoveAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        self.grid.dropEvent(drop)
        self.assertTrue((destination / '0.png').exists())
        self.assertFalse(Path(self.paths[0]).exists())
        def choose(menu, *args):
            action = next(a for a in menu.actions() if a.text() == 'Fermer tous les onglets')
            action.trigger()
        self.window.add_tab(str(destination))
        with patch.object(QMenu, 'exec', choose):
            self.window.custom_tab_bar._context_menu(self.window.custom_tab_bar.tabRect(0).center())
        self.assertEqual(self.window.tab_widget.count(), 0)
        self.window.add_new_tab()
        self.assertEqual(self.window.tab_widget.count(), 1)


if __name__ == '__main__':
    unittest.main()
