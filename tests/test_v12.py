import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PIL import Image
from PyQt6.QtCore import QPoint, QPointF, QRectF, Qt, QMimeData, QUrl, QCoreApplication, QEvent
from PyQt6.QtGui import QDropEvent, QWheelEvent, QKeyEvent
from PyQt6.QtTest import QTest, QSignalSpy
from PyQt6.QtWidgets import QApplication, QDialog
from src.config import ConfigManager
from src.ui.main_window import MainWindow
from src.ui.thumbnail_view import ThumbnailView, ROLE_PATH
from src.ui.fullscreen_viewer import FullscreenImageViewer, CropConfirmDialog
from src.ui.crop_overlay import CropOverlayItem
from src.utils.file_ops import crop_image, trash_image
from src.utils.image_loader import ThumbnailManager


class FeaturesV12(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.path = self.root / 'image2.png'
        Image.new('RGB', (800, 600), 'red').save(self.path)
        self.manager = ThumbnailManager()
        self.widgets = []

    def tearDown(self):
        for w in self.widgets:
            w.close()
            w.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.manager.pool.waitForDone()
        self.app.processEvents()
        self.temp.cleanup()

    def viewer(self, images=None):
        w = FullscreenImageViewer()
        self.widgets.append(w)
        w.show_images(images or [str(self.path)], str(self.path))
        self.app.processEvents()
        return w

    def grid(self):
        w = ThumbnailView(self.manager)
        self.widgets.append(w)
        w.setFolder(str(self.root))
        w.show()
        self.app.processEvents()
        return w

    def test_hud_only_on_right_click(self):
        viewer = self.viewer()
        self.assertFalse(viewer.hud.isVisible())
        QTest.mouseMove(viewer.view.viewport(), QPoint(50, 60))
        self.assertFalse(viewer.hud.isVisible())
        viewer.rotate_image(90)
        self.assertFalse(viewer.hud.isVisible())
        QTest.mouseClick(viewer.view.viewport(), Qt.MouseButton.RightButton, pos=QPoint(50, 60))
        self.assertTrue(viewer.hud.isVisible())
        viewer.next_image()
        self.assertFalse(viewer.hud.isVisible())
        viewer.close_fullscreen()
        viewer.show_images([str(self.path)], str(self.path))
        self.assertFalse(viewer.hud.isVisible())

    def test_x_crop_panel_dimensions_escape_and_nudge(self):
        viewer = self.viewer()
        QTest.keyClick(viewer.view, Qt.Key.Key_X)
        self.assertTrue(viewer.crop_mode)
        self.assertTrue(viewer.crop_panel.isVisible())
        self.assertFalse(viewer.hud.isVisible())
        self.assertEqual(viewer.crop_dimensions.text(), '640 × 480 px')
        x = viewer.crop_item.rect().x()
        QTest.keyClick(viewer.view, Qt.Key.Key_Right)
        self.assertEqual(viewer.crop_item.rect().x(), x + 1)
        self.assertEqual(viewer.current_index, 0)
        viewer.crop_ratio.setCurrentIndex(viewer.crop_ratio.findData(16/9))
        self.assertAlmostEqual(viewer.crop_item.rect().width() / viewer.crop_item.rect().height(), 16/9)
        viewer._flip_crop_ratio()
        self.assertAlmostEqual(viewer.crop_item.ratio, 9/16)
        QTest.keyClick(viewer.view, Qt.Key.Key_Escape)
        self.assertFalse(viewer.crop_mode)
        self.assertFalse(viewer.crop_panel.isVisible())
        self.assertTrue(viewer.isVisible())

    def test_counter_and_independent_navigation_list(self):
        other = self.root / 'image10.png'
        Image.new('RGB', (100, 100), 'blue').save(other)
        images = [str(self.path), str(other)]
        viewer = self.viewer(images)
        self.assertEqual('\n'.join(viewer.counter.text().splitlines()[:2]), '1 / 2\n1 image restante')
        self.assertEqual(viewer.counter.pos(), QPoint(20, 20))
        images.clear()
        viewer.next_image()
        self.assertEqual('\n'.join(viewer.counter.text().splitlines()[:2]), '2 / 2\n0 images restantes')
        self.assertTrue(viewer.counter.isVisible())
        self.assertFalse(viewer.hud.isVisible())

    def test_copy_paste_same_folder_and_another_tab(self):
        with patch('src.config.get_settings_path', return_value=self.root / 'settings.json'):
            config = ConfigManager()
        config.settings['tabs'] = [str(self.root)]
        window = MainWindow(config)
        self.widgets.append(window)
        window.show()
        self.app.processEvents()
        grid = window.get_current_tab_widget().thumb_view
        grid.setCurrentRow(0)
        QTest.keyClick(grid, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
        urls = QApplication.clipboard().mimeData().urls()
        self.assertEqual(Path(urls[0].toLocalFile()), self.path)
        QTest.keyClick(grid, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
        self.assertTrue((self.root / 'image2 - Copie.png').exists())
        self.assertTrue(self.path.exists())
        target = self.root / 'destination'
        target.mkdir()
        tab = window.add_tab(str(target))
        QTest.keyClick(tab.thumb_view, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual((target / 'image2.png').read_bytes(), self.path.read_bytes())

    def test_ctrl_drop_is_copy(self):
        grid = self.grid()
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(self.path))])
        spy = QSignalSpy(grid.files_dropped)
        drop = QDropEvent(QPointF(700, 600), Qt.DropAction.CopyAction | Qt.DropAction.MoveAction,
                          mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier)
        grid.dropEvent(drop)
        self.assertEqual(len(spy), 1)
        self.assertTrue(spy[0][2])
        self.assertEqual(drop.dropAction(), Qt.DropAction.CopyAction)

    def test_sorting_natural_date_size_type_and_selection(self):
        image10 = self.root / 'image10.jpg'
        Image.new('RGB', (20, 10), 'blue').save(image10)
        os.utime(self.path, (100, 100))
        os.utime(image10, (200, 200))
        (self.root / 'folder').mkdir()
        grid = self.grid()
        self.assertEqual([Path(p).name for p in grid.all_files], ['image2.png', 'image10.jpg'])
        grid.setCurrentRow(1)
        selected = grid.get_selected_file_paths()
        grid.set_sort('name', 'desc')
        self.assertEqual([Path(p).name for p in grid.all_files], ['image10.jpg', 'image2.png'])
        self.assertEqual(grid.get_selected_file_paths(), selected)
        self.assertEqual(Path(grid.item(0).data(ROLE_PATH)).name, 'folder')
        grid.set_sort('date', 'asc')
        self.assertEqual(grid.all_files, [str(self.path), str(image10)])
        grid.set_sort('size', 'asc')
        self.assertEqual(grid.all_files, [str(p) for p in sorted([self.path, image10], key=lambda p:p.stat().st_size)])
        grid.set_sort('type', 'asc')
        self.assertEqual(grid.all_files, [str(image10), str(self.path)])

    def test_crop_selection_bounds_new_rectangle_and_ratio(self):
        crop = CropOverlayItem(QRectF(0, 0, 800, 600))
        crop.begin_drag(QPointF(10, 10))
        crop.update_drag(QPointF(300, 200))
        self.assertEqual(crop.get_crop_box(), (10, 10, 300, 200))
        crop.set_ratio(16/9)
        corner = crop.rect().bottomRight()
        crop.begin_drag(corner)
        crop.update_drag(QPointF(1600, 1600))
        r = crop.rect()
        self.assertAlmostEqual(r.width() / r.height(), 16/9)
        self.assertTrue(crop.bounds.contains(r))
        crop.begin_drag(r.center())
        crop.update_drag(QPointF(-1000, -1000))
        self.assertTrue(crop.bounds.contains(crop.rect()))
        crop.nudge(9999, 9999)
        self.assertTrue(crop.bounds.contains(crop.rect()))

    def test_crop_tiny_image_valid(self):
        crop = CropOverlayItem(QRectF(0, 0, 1, 1))
        crop.set_ratio(16/9)
        self.assertEqual(crop.get_crop_box(), (0, 0, 1, 1))

    def test_crop_after_rotation_matches_displayed_pixels(self):
        # Non-symmetric source exposes coordinate/orientation mistakes.
        img = Image.new('RGB', (80, 40), 'red')
        img.paste('blue', (40, 0, 80, 40))
        img.save(self.path)
        for angle in (0, 90, 180, 270):
            expected = img.rotate(-angle, expand=True).crop((3, 5, 25, 30))
            dest = crop_image(self.path, (3, 5, 25, 30), rotation_degrees=angle)
            with Image.open(dest) as saved:
                self.assertEqual(saved.size, expected.size)
                self.assertEqual(saved.tobytes(), expected.tobytes())
        with Image.open(self.path) as original:
            self.assertEqual(original.size, (80, 40))

    def test_crop_failed_save_does_not_modify_original(self):
        original = self.path.read_bytes()
        with patch('PIL.Image.Image.save', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                crop_image(self.path, (0, 0, 20, 20), overwrite=True)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertFalse(list(self.root.glob('.xnviewtab-crop-*')))

    def test_crop_save_copy_updates_counter_and_cache(self):
        viewer = self.viewer()
        viewer.start_crop_mode()
        viewer.crop_item.setRect(QRectF(10, 20, 100, 80))
        def choose_copy(dialog):
            dialog.choice = 'copy'
            return QDialog.DialogCode.Accepted
        with patch.object(CropConfirmDialog, 'exec', choose_copy):
            viewer.apply_crop()
        with Image.open(self.root / 'image2_crop.png') as saved:
            self.assertEqual(saved.size, (100, 80))
        self.assertEqual('\n'.join(viewer.counter.text().splitlines()[:2]), '2 / 2\n0 images restantes')
        self.assertFalse(viewer.crop_mode)
        self.assertFalse(viewer.hud.isVisible())

    def test_delete_to_trash_without_confirmation_and_last_image(self):
        other = self.root / 'other.png'
        Image.new('RGB', (40, 40), 'green').save(other)
        viewer = self.viewer([str(self.path), str(other)])
        spy = QSignalSpy(viewer.image_deleted)
        with patch('src.ui.fullscreen_viewer.trash_image') as trash, patch('PyQt6.QtWidgets.QMessageBox.question') as confirm:
            QTest.keyClick(viewer.view, Qt.Key.Key_Delete)
            trash.assert_called_once_with(str(self.path))
            confirm.assert_not_called()
            self.assertEqual(viewer.image_list, [str(other)])
            self.assertEqual(viewer.current_index, 0)
            self.assertEqual('\n'.join(viewer.counter.text().splitlines()[:2]), '1 / 1\n0 images restantes')
            self.assertEqual(len(spy), 1)
            # Holding Delete does not wipe out a run of images through auto-repeat.
            repeat = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Delete,
                               Qt.KeyboardModifier.NoModifier, '', True)
            QApplication.sendEvent(viewer.view, repeat)
            self.assertEqual(len(viewer.image_list), 1)
            QTest.keyClick(viewer.view, Qt.Key.Key_Delete)
            self.assertTrue(viewer.isVisible())
            self.assertEqual(viewer.current_index, -1)

    def test_deletion_failure_retains_photo(self):
        with patch('src.utils.file_ops.QFile') as qfile, patch('pathlib.Path.unlink', side_effect=PermissionError('Access denied')):
            qfile.return_value.moveToTrash.return_value = False
            qfile.return_value.errorString.return_value = 'Corbeille indisponible'
            with self.assertRaises(OSError):
                trash_image(self.path)
        self.assertTrue(self.path.exists())
        viewer = self.viewer()
        with patch('src.ui.fullscreen_viewer.trash_image', side_effect=OSError('unavailable')), patch('PyQt6.QtWidgets.QMessageBox.warning') as warning:
            viewer.delete_current_image()
            warning.assert_called_once()
            self.assertEqual(viewer.image_list, [str(self.path)])
            self.assertTrue(self.path.exists())

    def test_wheel_navigates_ctrl_wheel_zooms_yellow_counter(self):
        other = self.root / 'other.png'
        Image.new('RGB', (800, 600), 'green').save(other)
        viewer = self.viewer([str(self.path), str(other)])
        def wheel(delta, mods=Qt.KeyboardModifier.NoModifier):
            event = QWheelEvent(QPointF(50, 50), QPointF(50, 50), QPoint(), QPoint(0, delta),
                                Qt.MouseButton.NoButton, mods, Qt.ScrollPhase.NoScrollPhase, False)
            QApplication.sendEvent(viewer.view.viewport(), event)
        wheel(-120)
        self.assertEqual(viewer.current_index, 1)
        wheel(120)
        self.assertEqual(viewer.current_index, 0)
        zoom = viewer.zoom_factor
        wheel(120, Qt.KeyboardModifier.ControlModifier)
        self.assertGreater(viewer.zoom_factor, zoom)
        self.assertEqual(viewer.current_index, 0)
        self.assertIn('#ffd54f', viewer.counter.styleSheet())
        self.assertFalse(viewer.hud.isVisible())

    def test_borderless_native_size_zoom_and_scrollbars(self):
        Image.new('RGB', (400, 300), 'blue').save(self.path)
        viewer = FullscreenImageViewer(floating=True)
        self.widgets.append(viewer)
        viewer.show_images([str(self.path)], str(self.path))
        self.app.processEvents()
        self.assertTrue(viewer.windowFlags() & Qt.WindowType.FramelessWindowHint)
        self.assertFalse(viewer.isFullScreen())
        self.assertEqual((viewer.width(), viewer.height()), (400, 300))
        self.assertEqual(viewer.zoom_factor, 1.0)
        self.assertEqual(viewer.view.horizontalScrollBar().maximum(), 0)
        viewer.resize(200, 150)
        self.app.processEvents()
        self.assertEqual(viewer.zoom_factor, 0.5)
        self.assertFalse(viewer.view.horizontalScrollBar().isVisible())
        self.assertFalse(viewer.view.verticalScrollBar().isVisible())
        viewer.zoom_in()
        self.assertGreater(viewer.zoom_factor, 0.5)
        self.assertFalse(viewer.size_grip.isVisible())
        self.assertFalse(viewer.counter.isVisible())
        self.assertFalse(viewer.move_handle.isVisible())

    def test_b_from_grid_and_fullscreen_and_tree_indentation(self):
        with patch('src.config.get_settings_path', return_value=self.root / 'settings.json'):
            config = ConfigManager()
        config.settings['tabs'] = [str(self.root)]
        window = MainWindow(config)
        self.widgets.append(window)
        window.show()
        self.app.processEvents()
        tab = window.get_current_tab_widget()
        self.assertEqual(tab.tree_view.indentation(), 10)
        tab.thumb_view.setCurrentRow(0)
        QTest.keyClick(tab.thumb_view, Qt.Key.Key_B)
        self.assertEqual(len(window.floating_viewers), 1)
        floating = next(iter(window.floating_viewers))
        self.assertTrue(floating.floating)
        window._on_request_fullscreen(tab.thumb_view.all_files, str(self.path))
        QTest.keyClick(window.fullscreen_viewer.view, Qt.Key.Key_B)
        self.assertEqual(len(window.floating_viewers), 2)

    def test_ctrl_drop_onto_another_tab_preserves_source(self):
        with patch('src.config.get_settings_path', return_value=self.root / 'settings.json'):
            config = ConfigManager()
        config.settings['tabs'] = [str(self.root)]
        window = MainWindow(config)
        self.widgets.append(window)
        window.show()
        self.app.processEvents()
        target = self.root / 'destination'
        target.mkdir()
        window.add_tab(str(target))
        bar = window.custom_tab_bar
        self.app.processEvents()
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(self.path))])
        drop = QDropEvent(QPointF(bar.tabRect(1).center()), Qt.DropAction.CopyAction | Qt.DropAction.MoveAction,
                          mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier)
        bar.dropEvent(drop)
        self.assertTrue(self.path.exists())
        self.assertEqual((target / self.path.name).read_bytes(), self.path.read_bytes())
        self.assertEqual(drop.dropAction(), Qt.DropAction.CopyAction)


if __name__ == '__main__':
    unittest.main()
