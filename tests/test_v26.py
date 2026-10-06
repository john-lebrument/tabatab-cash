import json
import subprocess
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import test_v14
from PyQt6.QtCore import QMimeData, QUrl, Qt, QPointF, QPoint, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent, QDragLeaveEvent
from PyQt6.QtTest import QTest, QSignalSpy
from PyQt6.QtWidgets import QApplication, QMessageBox
from src.ui.browser_tab import ROLE_PATH, FavoriteDelegate
from src.utils.instance_broker import InstanceBroker, launch_arguments


class FeaturesV26(unittest.TestCase):
    setUpClass = classmethod(test_v14.NewBehaviors.setUpClass.__func__)
    setUp = test_v14.NewBehaviors.setUp
    tearDown = test_v14.NewBehaviors.tearDown
    viewer = test_v14.NewBehaviors.viewer

    def favorite(self):
        folder = self.root / 'Destination'
        folder.mkdir()
        self.tab.add_folder_to_favorites(str(folder))
        fav = self.tab.fav_list
        item = next(fav.item(i) for i in range(fav.count()) if fav.item(i).data(ROLE_PATH) == str(folder))
        return folder, fav, item

    def test_drop_files_on_favorite_ctrl_copy_then_move(self):
        folder, fav, item = self.favorite()
        note = self.root / 'document.txt'
        note.write_text('content')
        point = fav.visualItemRect(item).center()
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(self.paths[0]), QUrl.fromLocalFile(str(note))])
        actions = Qt.DropAction.CopyAction | Qt.DropAction.MoveAction
        for copy in (True, False):
            enter = QDragEnterEvent(point, actions, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
            QApplication.sendEvent(fav.viewport(), enter)
            self.assertTrue(enter.isAccepted())
            for modifier in (Qt.KeyboardModifier.NoModifier, Qt.KeyboardModifier.ControlModifier):
                move = QDragMoveEvent(point, actions, mime, Qt.MouseButton.LeftButton, modifier)
                QApplication.sendEvent(fav.viewport(), move)
                self.assertEqual(move.dropAction(), Qt.DropAction.CopyAction if modifier else Qt.DropAction.MoveAction)
                self.assertIs(fav._drop_item, item)
            drop = QDropEvent(QPointF(point), actions, mime, Qt.MouseButton.LeftButton,
                              Qt.KeyboardModifier.ControlModifier if copy else Qt.KeyboardModifier.NoModifier)
            QApplication.sendEvent(fav.viewport(), drop)
            self.assertTrue(drop.isAccepted())
            self.assertEqual(note.exists(), copy)
            self.assertEqual(Path(self.paths[0]).exists(), copy)
            self.assertTrue((folder / 'document.txt').exists())
            self.assertEqual(self.tab.current_folder, str(self.root))
        self.assertEqual(len(list(folder.glob('*.txt'))), 2)

    def test_favorite_empty_area_rejects_drop_and_leave_clears_feedback(self):
        folder, fav, item = self.favorite()
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(self.paths[0])])
        point = fav.visualItemRect(item).center()
        move = QDragMoveEvent(point, Qt.DropAction.MoveAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        fav.dragMoveEvent(move)
        self.assertIsNotNone(fav._drop_item)
        fav.dragLeaveEvent(QDragLeaveEvent())
        self.assertIsNone(fav._drop_item)
        drop = QDropEvent(QPointF(-1, -1), Qt.DropAction.MoveAction, mime,
                          Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        fav.dropEvent(drop)
        self.assertFalse(drop.isAccepted())
        self.assertTrue(Path(self.paths[0]).exists())

    def test_close_cross_removes_favorite_without_navigation_or_deleting_folder(self):
        folder, fav, item = self.favorite()
        other = self.window.add_tab(str(self.root), switch_to=False)
        point = FavoriteDelegate.close_rect(fav.visualItemRect(item)).center()
        with patch.object(QMessageBox, 'question') as question:
            QTest.mouseClick(fav.viewport(), Qt.MouseButton.LeftButton, pos=point)
        question.assert_not_called()
        self.assertNotIn(str(folder), self.config.get('custom_favorites'))
        self.assertTrue(folder.is_dir())
        self.assertEqual(self.tab.current_folder, str(self.root))
        self.assertNotIn(str(folder), [other.fav_list.item(i).data(ROLE_PATH) for i in range(other.fav_list.count())])

    def test_tree_underscore_before_numbers_and_natural_sort(self):
        names = ['Alpha', '10 ten', '2 two', '_Zulu', '__First']
        for name in names:
            (self.root / name).mkdir()
        model = self.tab.tree_model
        index = model.index(str(self.root))
        self.tab.tree_view.setRootIndex(index)
        for _ in range(100):
            index = model.index(str(self.root))
            if model.rowCount(index) == len(names):
                break
            QTest.qWait(50)
        actual = [Path(model.filePath(model.index(row, 0, index))).name for row in range(model.rowCount(index))]
        self.assertEqual(actual, ['__First', '_Zulu', '2 two', '10 ten', 'Alpha'])
        self.assertEqual(Path(model.filePath(model.index(str(self.root / '_Zulu')))).name, '_Zulu')

    def test_fullscreen_left_information_updates_filename_and_zoom(self):
        viewer = self.viewer()
        self.assertIn('0.png', viewer.counter.text())
        self.assertEqual(viewer.zoom_badge.x(), viewer.counter.x())
        self.assertGreaterEqual(viewer.zoom_badge.y(), viewer.counter.geometry().bottom())
        QTest.keyClick(viewer.view, Qt.Key.Key_Plus)
        self.assertEqual(viewer.zoom_badge.text(), '125 %')
        viewer.next_image()
        self.assertIn('1.png', viewer.counter.text())
        self.assertEqual(viewer.zoom_badge.text(), '100 %')
        self.assertFalse(viewer.hud.isVisible())

    def test_image_request_forwarded_between_processes_and_extra_instance_election(self):
        name = 'TABaTABTest-' + uuid.uuid4().hex
        primary = InstanceBroker(name=name)
        extra = InstanceBroker(name=name)
        try:
            self.assertTrue(primary.start())
            self.assertTrue(extra.start())  # Taskbar middle-click: no photo argument.
            self.assertFalse(extra.server.isListening())
            primary.image_requested.connect(self.window.open_external_image)
            spy = QSignalSpy(primary.image_requested)
            script = ('from PyQt6.QtCore import QCoreApplication; '
                      'from src.utils.instance_broker import InstanceBroker; '
                      'app=QCoreApplication([]); '
                      f'b=InstanceBroker(name={name!r}); '
                      f'raise SystemExit(0 if not b.start({self.paths[1]!r}) else 1)')
            child = subprocess.Popen([sys.executable, '-c', script], cwd=Path(__file__).resolve().parents[1],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            for _ in range(200):
                if child.poll() is not None:
                    break
                QTest.qWait(50)
            if child.poll() is None:
                child.kill()
            output, errors = child.communicate(timeout=5)
            self.assertEqual(child.returncode, 0, errors.decode(errors='replace'))
            self.assertEqual(len(spy), 1)
            viewer = self.window.fullscreen_viewer
            self.assertEqual(viewer.image_list[viewer.current_index], self.paths[1])
            primary.close()
            self.assertTrue(extra.try_own())
        finally:
            primary.close()
            extra.close()

    def test_launch_arguments_file_url_and_force_new(self):
        self.assertEqual(launch_arguments([]), (None, False))
        self.assertEqual(launch_arguments([QUrl.fromLocalFile(self.paths[0]).toString()]), (self.paths[0], False))
        self.assertEqual(launch_arguments(['--new-instance', self.paths[0]]), (self.paths[0], True))
