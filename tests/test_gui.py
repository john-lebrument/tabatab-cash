import os
import sys
import unittest
from unittest.mock import patch
from pathlib import Path
from PIL import Image

os.environ["QT_QPA_PLATFORM"] = "offscreen"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtWidgets import QApplication
from src.config import ConfigManager
from src.ui.main_window import MainWindow
from src.ui.fullscreen_viewer import FullscreenImageViewer


class TestGUIComponents(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    @classmethod
    def tearDownClass(cls):
        cls.app.processEvents()

    def setUp(self):
        self.previous_widgets = set(self.app.topLevelWidgets())
        self.test_dir = PROJECT_ROOT / "tests" / "temp_gui_test"
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.settings_patch = patch('src.config.get_settings_path', return_value=self.test_dir / 'settings.json')
        self.settings_patch.start()
        self.addCleanup(self.settings_patch.stop)
        self.img_path = self.test_dir / "sample.jpg"
        img = Image.new("RGB", (640, 480), color=(0, 128, 255))
        img.save(self.img_path)

    def tearDown(self):
        import shutil
        from PyQt6.QtCore import QThreadPool, QCoreApplication, QEvent
        QThreadPool.globalInstance().waitForDone()
        self.app.processEvents()
        for widget in set(self.app.topLevelWidgets()) - self.previous_widgets:
            widget.close()
            widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_main_window_init_and_tabs(self):
        config = ConfigManager()
        window = MainWindow(config)
        self.app.processEvents()
        self.assertIsNotNone(window)
        # Add tab
        tab = window.add_tab(str(self.test_dir))
        self.assertIsNotNone(tab)
        self.assertEqual(tab.current_folder, str(self.test_dir.resolve()))
        window.close()

    def test_fullscreen_viewer(self):
        viewer = FullscreenImageViewer()
        viewer.show_images([str(self.img_path)], str(self.img_path))
        self.assertEqual(viewer.current_index, 0)
        self.assertIsNotNone(viewer.current_pixmap)
        self.assertEqual(viewer.current_pixmap.width(), 640)
        self.assertEqual(viewer.current_pixmap.height(), 480)

        # Test zoom
        initial_factor = viewer.zoom_factor
        viewer.zoom_in()
        self.assertGreater(viewer.zoom_factor, initial_factor)
        viewer.zoom_out()
        self.assertAlmostEqual(viewer.zoom_factor, initial_factor, places=2)

        # Test crop mode toggle
        viewer.toggle_crop_mode()
        self.assertTrue(viewer.crop_mode)
        self.assertIsNotNone(viewer.crop_item)

        box = viewer.crop_item.get_crop_box()
        self.assertEqual(len(box), 4)

        viewer.cancel_crop()
        self.assertFalse(viewer.crop_mode)

        # Test rotation 90° (Touche L)
        viewer.rotate_image(-90)
        self.assertEqual(viewer.current_pixmap.width(), 480)
        self.assertEqual(viewer.current_pixmap.height(), 640)

        viewer.close()

    def test_subfolders_and_theme(self):
        # Create a subfolder
        sub = self.test_dir / "SousDossier"
        sub.mkdir(exist_ok=True)

        config = ConfigManager()
        window = MainWindow(config)
        self.app.processEvents()
        tab = window.add_tab(str(self.test_dir))

        # Check that both subfolder and image exist in the grid
        items_count = tab.thumb_view.count()
        self.assertEqual(items_count, 2)  # 1 folder + 1 image

        # Verify theme toggle
        old_theme = window.current_theme
        window.toggle_theme()
        self.assertNotEqual(window.current_theme, old_theme)
        self.assertEqual(config.get("theme"), window.current_theme)
        window.close()

    def test_favorites_and_large_thumbnails(self):
        config = ConfigManager()
        window = MainWindow(config)
        self.app.processEvents()
        tab = window.add_tab(str(self.test_dir))

        # Test adding custom favorite
        initial_favs_count = tab.fav_list.count()
        tab.add_current_to_favorites()
        self.assertEqual(tab.fav_list.count(), initial_favs_count + 1)
        self.assertIn(str(self.test_dir.resolve()), config.get("custom_favorites"))

        # Test large thumbnail size (up to 600)
        tab.thumb_view.setThumbnailSize(500)
        self.assertEqual(tab.thumb_view.current_thumb_size, 500)

        # Test removing favorite
        tab.remove_custom_favorite(str(self.test_dir.resolve()))
        self.assertEqual(tab.fav_list.count(), initial_favs_count)
        self.assertNotIn(str(self.test_dir.resolve()), config.get("custom_favorites"))

        window.close()


if __name__ == "__main__":
    unittest.main()
