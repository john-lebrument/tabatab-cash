import hashlib
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import test_v14
from PIL import Image
from PyQt6.QtCore import QEvent, QPoint, Qt, QThread, QTimer
from PyQt6.QtGui import QContextMenuEvent, QKeyEvent, QPalette
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QInputDialog, QLabel, QLineEdit, QMenu, QPushButton

from src.ui.fullscreen_viewer import FullscreenImageViewer
from src.utils.image_search import ImageSearchController, ImageSearchJob, image_preview, upload_image


class SearchProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_preview_scales_orients_strips_metadata_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'photo.jpg'
            exif = Image.Exif()
            exif[274] = 6
            exif[315] = 'Private photographer'
            Image.new('RGB', (2400, 1200), 'orange').save(path, exif=exif)
            before = hashlib.sha256(path.read_bytes()).digest()
            with Image.open(BytesIO(image_preview(path))) as result:
                self.assertEqual(result.size, (800, 1600))
                self.assertEqual(dict(result.getexif()), {})
            self.assertEqual(hashlib.sha256(path.read_bytes()).digest(), before)

    def test_transparent_preview_has_white_background(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'alpha.png'
            Image.new('RGBA', (10, 10), (0, 0, 0, 0)).save(path)
            with Image.open(BytesIO(image_preview(path))) as result:
                self.assertEqual(result.getpixel((0, 0)), (255, 255, 255))

    def test_yandex_upload_and_image_specific_result(self):
        response = MagicMock()
        response.read.return_value = json.dumps({'blocks': [{'params': {
            'cbirId': '123/image', 'originalImageUrl': 'https://avatars.mds.yandex.net/photo',
        }}]}).encode()
        with patch('src.utils.image_search.urlopen') as request:
            request.return_value.__enter__.return_value = response
            result = upload_image('Yandex', b'JPEG preview')
        sent = request.call_args.args[0]
        self.assertEqual(urlparse(sent.full_url).hostname, 'yandex.com')
        self.assertIn(b'name="upfile"', sent.data)
        self.assertIn(b'JPEG preview', sent.data)
        self.assertEqual(parse_qs(urlparse(result).query)['cbir_id'], ['123/image'])
        self.assertEqual(request.call_args.kwargs['timeout'], 30)

    def test_google_upload_requires_image_results(self):
        response = MagicMock()
        response.geturl.return_value = 'https://www.google.com/search?vsrid=photo&udm=26'
        with patch('src.utils.image_search.urlopen') as request:
            request.return_value.__enter__.return_value = response
            self.assertIn('vsrid=photo', upload_image('Google Lens', b'JPEG preview'))
            self.assertIn(b'name="encoded_image"', request.call_args.args[0].data)
            for invalid in ('https://search.google/ways-to-search/lens/',
                            'https://www.google.com/', 'https://example.org/search'):
                response.geturl.return_value = invalid
                with self.assertRaises(ValueError):
                    upload_image('Google Lens', b'JPEG preview')

    def test_job_searches_both_engines_even_if_one_fails(self):
        job = ImageSearchJob('local.png')
        results, finished = [], []
        job.signals.result.connect(lambda *args: results.append(args))
        job.signals.finished.connect(finished.append)
        def upload(engine, preview):
            if engine == 'Yandex':
                raise TimeoutError('Délai dépassé')
            return 'https://www.google.com/search?vsrid=photo'
        with patch('src.utils.image_search.image_preview', return_value=b'preview'), \
                patch('src.utils.image_search.upload_image', side_effect=upload):
            job.run()
        QApplication.processEvents()
        by_engine = {engine: (url, error) for engine, url, error in results}
        self.assertEqual(by_engine['Yandex'], ('', 'Délai dépassé'))
        self.assertEqual(by_engine['Google Lens'][1], '')
        self.assertEqual(finished, ['local.png'])


class FeaturesV210(unittest.TestCase):
    setUpClass = classmethod(test_v14.NewBehaviors.setUpClass.__func__)
    setUp = test_v14.NewBehaviors.setUp
    tearDown = test_v14.NewBehaviors.tearDown
    viewer = test_v14.NewBehaviors.viewer

    def test_s_right_click_and_keyboard_menu_search_once_in_both_viewers(self):
        for floating in (False, True):
            viewer = self.viewer() if not floating else FullscreenImageViewer(self.window, floating=True)
            if floating:
                viewer.show_images(self.paths, self.paths[1])
            path = self.paths[1] if floating else self.paths[0]
            with patch('src.ui.fullscreen_viewer.search_similar_images') as search, \
                    patch.object(QMenu, 'exec'):
                QTest.keyClick(viewer.view, Qt.Key.Key_S)
                search.assert_called_once_with(path)
                search.reset_mock()
                QTest.mouseClick(viewer.view.viewport(), Qt.MouseButton.RightButton, pos=QPoint(20, 20))
                # The native context event following a mouse click must not upload again.
                viewer.view.contextMenuEvent(QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(20, 20)))
                search.assert_called_once_with(path)
                search.reset_mock()
                viewer.view.contextMenuEvent(QContextMenuEvent(QContextMenuEvent.Reason.Keyboard, QPoint(20, 20)))
                search.assert_called_once_with(path)
                search.reset_mock()
                with patch.object(viewer, 'save_rotated_image') as save:
                    QTest.keyClick(viewer.view, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
                    save.assert_called_once()
                repeat = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_S, Qt.KeyboardModifier.NoModifier, 's', True)
                viewer.view.keyPressEvent(repeat)
                search.assert_not_called()
            viewer.close_fullscreen()

    def test_grid_search_shortcut_and_menu_target_clicked_image(self):
        self.grid.select_path(self.paths[0])
        with patch('src.ui.thumbnail_view.search_similar_images') as search:
            QTest.keyClick(self.grid, Qt.Key.Key_S)
            search.assert_called_once_with(self.paths[0])
            search.reset_mock()
            self.grid.select_path(self.paths[1])
            item = self.grid.currentItem()
            def choose(menu, *args):
                next(a for a in menu.actions() if a.text().startswith('Images similaires')).trigger()
            with patch.object(QMenu, 'exec', choose):
                self.grid._show_context_menu(self.grid.visualItemRect(item).center())
            search.assert_called_once_with(self.paths[1])

    def test_grid_s_ignores_folder_video_and_empty_selection(self):
        folder = self.root / 'Folder'; folder.mkdir()
        (self.root / 'video.mp4').touch()
        self.grid.show_videos = True
        self.grid.setFolder(str(self.root))
        with patch('src.ui.thumbnail_view.search_similar_images') as search:
            for path in (str(folder), str(self.root / 'video.mp4')):
                self.grid.select_path(path)
                QTest.keyClick(self.grid, Qt.Key.Key_S)
            self.grid.setCurrentRow(-1)
            QTest.keyClick(self.grid, Qt.Key.Key_S)
            search.assert_not_called()

    def test_real_rename_dialog_has_contrasting_text_and_buttons(self):
        for floating in (False, True):
            for theme in ('light', 'dark'):
                if self.window.current_theme != theme:
                    self.window.toggle_theme()
                viewer = self.viewer() if not floating else FullscreenImageViewer(self.window, floating=True)
                if floating:
                    viewer.show_images(self.paths, self.paths[0])
                checks = []
                def inspect_dialog():
                    dialog = QApplication.activeModalWidget()
                    if isinstance(dialog, QInputDialog):
                        controls = dialog.findChildren(QLineEdit) + dialog.findChildren(QLabel) + dialog.findChildren(QPushButton)
                        for control in controls:
                            palette = control.palette()
                            fg = palette.color(QPalette.ColorRole.Text if isinstance(control, QLineEdit) else control.foregroundRole())
                            bg = palette.color(control.backgroundRole())
                            checks.append(abs(fg.lightnessF() - bg.lightnessF()) > .4)
                        dialog.reject()
                QTimer.singleShot(50, inspect_dialog)
                viewer.rename_current_image()
                self.assertTrue(checks)
                self.assertTrue(all(checks), (floating, theme, checks))
                self.assertTrue(Path(self.paths[0]).is_file())
                viewer.close_fullscreen()

    def test_controller_opens_default_browser_reports_errors_and_deduplicates(self):
        controller = ImageSearchController(self.app)
        with patch('src.utils.image_search.QThreadPool.globalInstance') as pool:
            controller.start(self.paths[0])
            controller.start(self.paths[0])
            pool.return_value.start.assert_called_once()
        with patch('src.utils.image_search.QDesktopServices.openUrl', return_value=True) as browser:
            controller._result('Yandex', 'https://yandex.com/images/search?cbir_id=photo', '')
            controller._result('Google Lens', 'https://www.google.com/search?vsrid=photo', '')
            self.assertEqual(browser.call_count, 2)
        controller._result('Yandex', '', 'Connexion indisponible')
        controller._finished(self.paths[0])
        self.assertFalse(controller.jobs)
        self.assertIn('Connexion indisponible', controller.dialog.text())
        controller.dialog.close()
        controller.deleteLater()

    def test_background_job_returns_results_to_gui_thread(self):
        controller = ImageSearchController(self.app)
        opened = []
        def open_browser(url):
            opened.append((url.toString(), QThread.currentThread() == self.app.thread()))
            return True
        def upload(engine, preview):
            self.assertTrue(preview.startswith(b'\xff\xd8'))
            return ('https://yandex.com/images/search?cbir_id=photo' if engine == 'Yandex'
                    else 'https://www.google.com/search?vsrid=photo')
        with patch('src.utils.image_search.upload_image', side_effect=upload), \
                patch('src.utils.image_search.QDesktopServices.openUrl', side_effect=open_browser):
            controller.start(self.paths[0])
            for _ in range(100):
                if not controller.jobs:
                    break
                QTest.qWait(20)
            self.assertFalse(controller.jobs)
        self.assertEqual(len(opened), 2)
        self.assertTrue(all(gui_thread for url, gui_thread in opened))
        controller.deleteLater()
