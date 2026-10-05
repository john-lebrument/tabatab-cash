import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import test_v14
from PIL import Image
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from src.ui.thumbnail_view import ROLE_PATH
from src.version import APP_TITLE, APP_VERSION


class FeaturesV18(unittest.TestCase):
    setUpClass = classmethod(test_v14.NewBehaviors.setUpClass.__func__)
    setUp = test_v14.NewBehaviors.setUp
    tearDown = test_v14.NewBehaviors.tearDown
    viewer = test_v14.NewBehaviors.viewer

    def test_brand_and_version_title(self):
        self.assertEqual(self.window.windowTitle(), APP_TITLE)
        self.assertIn('TABaTAB Cash', APP_TITLE)
        self.assertIn(APP_VERSION, APP_TITLE)

    def test_video_toggle_persisted_and_excluded_from_fullscreen(self):
        video = self.root / 'movie.MP4'
        video.write_bytes(b'fixture')
        self.tab.refresh()
        self.assertEqual(self.grid.count(), 3)
        with patch('src.utils.image_loader.ThumbnailManager.get_thumbnail', return_value=None):
            self.tab.btn_videos.click()
            self.assertEqual(self.grid.count(), 4)
            self.assertTrue(self.config.get('show_videos'))
            self.assertNotIn(str(video), self.grid.all_files)
            new_tab = self.window.add_tab(str(self.root), switch_to=False)
            self.assertTrue(new_tab.btn_videos.isChecked())
            self.tab.btn_videos.click()
            self.assertEqual(self.grid.count(), 3)

    def test_video_opens_only_on_double_click(self):
        video = self.root / 'movie.mp4'
        video.write_bytes(b'fixture')
        self.grid.set_show_videos(True)
        item = next(self.grid.item(i) for i in range(self.grid.count()) if self.grid.item(i).data(ROLE_PATH) == str(video))
        with patch('src.ui.thumbnail_view.QDesktopServices.openUrl', return_value=True) as open_url:
            self.grid.itemClicked.emit(item)
            open_url.assert_not_called()
            self.grid._on_item_double_clicked(item)
            open_url.assert_called_once()
            self.assertEqual(Path(open_url.call_args.args[0].toLocalFile()), video)
        self.assertIsNone(self.window.fullscreen_viewer)

    def test_external_image_opens_requested_photo_fullscreen(self):
        folder = self.root / 'Images avec espaces'
        folder.mkdir()
        path = folder / 'ma photo é.png'
        Image.new('RGB', (30, 40), 'blue').save(path)
        self.window.open_external_image(str(path))
        viewer = self.window.fullscreen_viewer
        self.assertTrue(viewer.isFullScreen())
        self.assertEqual(viewer.image_list[viewer.current_index], str(path))
        self.assertEqual(self.window.get_current_tab_widget().current_folder, str(folder))
        viewer.close_fullscreen()
        self.assertEqual(self.window.get_current_tab_widget().thumb_view.get_selected_file_paths(), [str(path)])

    def test_m_cycles_screens_without_changing_photo(self):
        viewer = self.viewer()
        first, second = MagicMock(), MagicMock()
        index = viewer.current_index
        with patch.object(QApplication, 'screens', return_value=[first, second]), patch.object(viewer, 'screen', return_value=first), patch.object(viewer, 'move_to_screen') as move:
            QTest.keyClick(viewer.view, Qt.Key.Key_M)
            move.assert_called_once_with(second)
        self.assertEqual(viewer.current_index, index)

    def test_screen_transfer_sets_target_geometry(self):
        viewer = self.viewer()
        target = MagicMock()
        target.geometry.return_value = QRect(-1920, 0, 1920, 1080)
        handle = MagicMock()
        with patch.object(viewer, 'windowHandle', return_value=handle), patch.object(viewer, 'showNormal'), patch.object(viewer, 'setGeometry') as geometry, patch.object(viewer, 'showFullScreen') as fullscreen:
            viewer.move_to_screen(target)
            handle.setScreen.assert_called_once_with(target)
            geometry.assert_called_once_with(QRect(-1920, 0, 1920, 1080))
            fullscreen.assert_called_once()

    def test_single_monitor_message(self):
        viewer = self.viewer()
        with patch.object(QApplication, 'screens', return_value=[viewer.screen()]):
            viewer.move_to_next_screen()
        self.assertEqual(viewer.toast.text(), 'Un seul écran est disponible')

    def test_video_frame_becomes_cached_thumbnail(self):
        from src.utils.video_thumbnail import VideoThumbnails
        with patch('src.utils.video_thumbnail.QMediaPlayer'), patch('src.utils.video_thumbnail.QVideoSink'):
            loader = VideoThumbnails(self.window)
            loader.ready.connect(lambda p, image, size: self.window.thumbnail_manager._on_thumbnail_ready(p, image, size, image.width(), image.height()))
            loader.request('clip.mp4', 150)
            frame = MagicMock()
            frame.toImage.return_value = QImage(320, 200, QImage.Format.Format_RGB32)
            loader._frame(frame)
            pix = self.window.thumbnail_manager.cache.get('clip.mp4_150')
            self.assertIsNotNone(pix)
            self.assertEqual(pix.width(), 150)
            self.assertIsNone(loader.current)


if __name__ == '__main__':
    unittest.main()
