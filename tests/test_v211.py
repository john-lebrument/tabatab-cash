import base64
import unittest
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from unittest.mock import patch

import test_v14
from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QMenu

from src.ui.fullscreen_viewer import FullscreenImageViewer
from src.utils.browser_upload import BrowserUploadBridge


class BrowserUploadTests(unittest.TestCase):
    def setUp(self):
        self.bridge = BrowserUploadBridge()

    def tearDown(self):
        self.bridge.close()

    def test_form_transfers_image_in_browser_and_allows_google_redirects(self):
        preview = b'JPEG bytes from local photo'
        url = self.bridge.add(preview)
        self.assertEqual(urlparse(url).hostname, '127.0.0.1')
        with urlopen(url, timeout=3) as response:
            body = response.read().decode('utf-8')
            self.assertEqual(response.headers['Cache-Control'], 'no-store')
            self.assertEqual(response.headers['Referrer-Policy'], 'no-referrer')
            self.assertIn('form-action https://*.google.com https://google.com',
                          response.headers['Content-Security-Policy'])
        self.assertIn('action="https://lens.google.com/upload?hl=fr"', body)
        self.assertIn('enctype="multipart/form-data"', body)
        self.assertIn('name="encoded_image"', body)
        self.assertIn('new File([bytes]', body)
        self.assertIn('requestSubmit()', body)
        self.assertIn(base64.b64encode(preview).decode(), body)
        # A reload before submission still has access to the prepared image.
        with urlopen(url, timeout=3) as response:
            self.assertEqual(response.status, 200)

    def test_unknown_routes_and_foreign_host_are_rejected(self):
        url = self.bridge.add(b'preview')
        with self.assertRaises(HTTPError) as missing:
            urlopen(url + '/unknown', timeout=3)
        self.assertEqual(missing.exception.code, 404)
        missing.exception.close()
        with self.assertRaises(HTTPError) as foreign:
            urlopen(Request(url, headers={'Host': 'example.org'}), timeout=3)
        self.assertEqual(foreign.exception.code, 403)
        foreign.exception.close()

    def test_expiration_and_capacity_bound_image_retention(self):
        self.bridge.max_pending = 2
        first = self.bridge.add(b'first')
        self.bridge.add(b'second')
        self.bridge.add(b'third')
        self.assertEqual(len(self.bridge.pending), 2)
        self.assertNotIn(urlparse(first).path, self.bridge.pending)
        with patch('src.utils.browser_upload.time.monotonic', return_value=10**12):
            with self.bridge.lock:
                self.bridge._expire()
        self.assertFalse(self.bridge.pending)


class ToolsV211(unittest.TestCase):
    setUpClass = classmethod(test_v14.NewBehaviors.setUpClass.__func__)
    setUp = test_v14.NewBehaviors.setUp
    tearDown = test_v14.NewBehaviors.tearDown
    viewer = test_v14.NewBehaviors.viewer

    def test_fullscreen_right_click_waits_for_search_button(self):
        viewer = self.viewer()
        with patch('src.ui.fullscreen_viewer.search_similar_images') as search:
            QTest.mouseClick(viewer.view.viewport(), Qt.MouseButton.RightButton, pos=QPoint(20, 20))
            self.assertTrue(viewer.hud.isVisible())
            self.assertTrue(viewer.btn_search.isVisible())
            search.assert_not_called()
            QTest.mouseClick(viewer.btn_search, Qt.MouseButton.LeftButton)
            search.assert_called_once_with(self.paths[0])

    def test_small_floating_window_menu_can_cancel_or_choose_search(self):
        viewer = FullscreenImageViewer(self.window, floating=True)
        viewer.show_images(self.paths, self.paths[1])
        viewer.resize(220, 180)
        self.app.processEvents()
        with patch('src.ui.fullscreen_viewer.search_similar_images') as search:
            with patch.object(QMenu, 'exec'):
                QTest.mouseClick(viewer.view.viewport(), Qt.MouseButton.RightButton, pos=QPoint(20, 20))
            search.assert_not_called()
            def choose(menu, *args):
                next(a for a in menu.actions() if a.text().startswith('Images similaires')).trigger()
            with patch.object(QMenu, 'exec', choose):
                QTest.mouseClick(viewer.view.viewport(), Qt.MouseButton.RightButton, pos=QPoint(20, 20))
            search.assert_called_once_with(self.paths[1])
        viewer.close()
