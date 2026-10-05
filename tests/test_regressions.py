import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PIL import Image
from PyQt6.QtCore import QMimeData, QPoint, QPointF, QSize, Qt, QUrl
from PyQt6.QtGui import QDragEnterEvent, QDragMoveEvent, QDragLeaveEvent, QPixmap
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication
from src.config import ConfigManager
from src.ui.main_window import MainWindow
from src.ui.thumbnail_view import ThumbnailView
from src.ui.fullscreen_viewer import FullscreenImageViewer
from src.utils.image_loader import ThumbnailManager


class RegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.path = self.root / 'small.png'
        Image.new('RGB', (40, 20), 'red').save(self.path)
        self.manager = ThumbnailManager()
        self.widgets = []

    def tearDown(self):
        self.manager.pool.waitForDone()
        self.app.processEvents()
        for widget in self.widgets:
            widget.close()
            widget.deleteLater()
        self.app.processEvents()
        self.temp.cleanup()

    def wait_until(self, predicate):
        end = time.monotonic() + 5
        while not predicate() and time.monotonic() < end:
            QTest.qWait(20)
        self.assertTrue(predicate())

    def window(self):
        with patch('src.config.get_settings_path', return_value=self.root / 'settings.json'):
            config = ConfigManager()
        config.settings['tabs'] = [str(self.root)]
        window = MainWindow(config)
        self.widgets.append(window)
        window.show()
        self.app.processEvents()
        return window

    def test_plus_after_last_tab_and_click(self):
        window = self.window()
        bar = window.custom_tab_bar
        self.assertTrue(bar.btn_plus.isVisible())
        self.assertGreater(bar.btn_plus.x(), bar.tabRect(bar.count() - 1).right())
        self.assertLessEqual(bar.btn_plus.geometry().right(), bar.rect().right())
        self.assertFalse(window.btn_new_tab.isVisible())
        count = bar.count()
        QTest.mouseClick(bar.btn_plus, Qt.MouseButton.LeftButton)
        self.app.processEvents()
        self.assertEqual(bar.count(), count + 1)
        window.close_tab(0)
        self.app.processEvents()
        self.assertTrue(bar.btn_plus.isVisible())
        for i in range(15):
            window.add_tab(str(self.root))
        self.app.processEvents()
        self.assertTrue(bar.btn_plus.isVisible() or window.btn_new_tab.isVisible())

    def test_drag_hover_and_leave_keep_origin_tab(self):
        window = self.window()
        window.add_tab(str(self.root))
        bar = window.custom_tab_bar
        bar.setCurrentIndex(0)
        self.app.processEvents()
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(self.path))])
        pos = bar.tabRect(1).center()
        enter = QDragEnterEvent(pos, Qt.DropAction.MoveAction, mime,
                                Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        move = QDragMoveEvent(pos, Qt.DropAction.MoveAction, mime,
                              Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(bar, enter)
        QApplication.sendEvent(bar, move)
        QTest.qWait(550)
        self.assertEqual(bar.currentIndex(), 0)
        bar.setCurrentIndex(0)
        QApplication.sendEvent(bar, QDragLeaveEvent())
        QTest.qWait(550)
        self.assertEqual(bar.currentIndex(), 0)

    def test_small_image_enlargement_and_stale_result(self):
        view = ThumbnailView(self.manager)
        self.widgets.append(view)
        view.resize(800, 700)
        view.show()
        view.setFolder(str(self.root))
        view.setThumbnailSize(400)
        key = f'{self.path}_400'
        self.wait_until(lambda: self.manager.cache.get(key) is not None)
        pix = view.item(0).icon().pixmap(QSize(400, 400))
        self.assertEqual((pix.width(), pix.height()), (400, 200))
        stale = QPixmap(80, 40)
        view._on_thumbnail_ready(str(self.path), stale, 80, 40, 20)
        self.assertEqual(view.item(0).icon().pixmap(QSize(400, 400)).width(), 400)
        self.assertNotIn(key, self.manager.pending_tasks)
        # Two tabs sharing a manager must retain their own requested sizes.
        other = ThumbnailView(self.manager)
        self.widgets.append(other)
        other.show()
        other.setFolder(str(self.root))
        other.setThumbnailSize(100)
        self.wait_until(lambda: self.manager.cache.get(f'{self.path}_100') is not None)
        self.assertEqual(view.item(0).icon().pixmap(QSize(400, 400)).width(), 400)

    def test_fullscreen_right_click_and_crop(self):
        viewer = FullscreenImageViewer()
        self.widgets.append(viewer)
        viewer.show_images([str(self.path)], str(self.path))
        viewer.hud.hide()
        QTest.mouseClick(viewer.view.viewport(), Qt.MouseButton.RightButton, pos=QPoint(20, 20))
        self.assertTrue(viewer.hud.isVisible())
        QTest.mouseClick(viewer.btn_crop, Qt.MouseButton.LeftButton)
        self.assertTrue(viewer.crop_mode)
        viewer.hud.hide()
        QTest.mouseClick(viewer.view.viewport(), Qt.MouseButton.RightButton, pos=QPoint(20, 20))
        self.assertTrue(viewer.hud.isVisible())
        self.assertTrue(viewer.crop_mode)

    def test_startup_restoration_does_not_overwrite_saved_tabs(self):
        window = self.window()
        self.assertIsNone(window.fullscreen_viewer)
        self.assertEqual(window.config.get('tabs'), [str(self.root)])


if __name__ == '__main__':
    unittest.main()
