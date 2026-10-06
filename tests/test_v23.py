import unittest
from pathlib import Path
from unittest.mock import patch

import test_v14
from PyQt6.QtCore import QMimeData, QUrl, Qt, QPointF, QPoint
from PyQt6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent, QDragLeaveEvent
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication


class FeaturesV23(unittest.TestCase):
    setUpClass = classmethod(test_v14.NewBehaviors.setUpClass.__func__)
    setUp = test_v14.NewBehaviors.setUp
    tearDown = test_v14.NewBehaviors.tearDown

    def mime(self, paths):
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(path) for path in paths])
        return mime

    def test_viewport_drop_multiple_files_ctrl_changes_before_release(self):
        folder = self.root / 'test'
        folder.mkdir()
        self.tab.refresh()
        point = self.grid.visualItemRect(self.grid.item(0)).center()
        mime = self.mime(self.paths[:2])
        actions = Qt.DropAction.CopyAction | Qt.DropAction.MoveAction
        viewport = self.grid.viewport()
        for copy in (True, False):
            enter = QDragEnterEvent(point, actions, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
            QApplication.sendEvent(viewport, enter)
            self.assertTrue(enter.isAccepted())
            for mods in (Qt.KeyboardModifier.ControlModifier, Qt.KeyboardModifier.NoModifier):
                move = QDragMoveEvent(point, actions, mime, Qt.MouseButton.LeftButton, mods)
                QApplication.sendEvent(viewport, move)
                self.assertTrue(move.isAccepted())
            drop = QDropEvent(QPointF(point), actions, mime, Qt.MouseButton.LeftButton,
                             Qt.KeyboardModifier.ControlModifier if copy else Qt.KeyboardModifier.NoModifier)
            QApplication.sendEvent(viewport, drop)
            self.assertTrue(drop.isAccepted())
            for path in self.paths[:2]:
                self.assertEqual(Path(path).exists(), copy)
                self.assertTrue((folder / Path(path).name).exists())

    def test_tree_hover_opens_without_navigating_and_leave_cancels(self):
        folder = self.root / 'test'
        (folder / 'child').mkdir(parents=True)
        tree = self.tab.tree_view
        tree.setRootIndex(self.tab.tree_model.index(str(self.root)))
        QTest.qWait(200)
        index = self.tab.tree_model.index(str(folder))
        tree.collapse(index)
        point = tree.visualRect(index).center()
        mime = self.mime(self.paths[:1])
        move = QDragMoveEvent(point, Qt.DropAction.MoveAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        tree.dragMoveEvent(move)
        self.assertFalse(tree.isExpanded(index))
        QTest.qWait(850)
        index = self.tab.tree_model.index(str(folder))
        self.assertTrue(tree.isExpanded(index))
        self.assertEqual(Path(self.tab.current_folder), self.root)
        tree.collapse(index)
        tree.dragLeaveEvent(QDragLeaveEvent())
        tree.dragMoveEvent(move)
        tree.dragLeaveEvent(QDragLeaveEvent())
        QTest.qWait(800)
        index = self.tab.tree_model.index(str(folder))
        self.assertFalse(tree.isExpanded(index))

    def test_tree_stationary_drag_scrolls_both_directions_and_stops(self):
        for n in range(70):
            (self.root / f'folder{n:03}').mkdir()
        tree = self.tab.tree_view
        tree.setRootIndex(self.tab.tree_model.index(str(self.root)))
        bar = tree.verticalScrollBar()
        # QFileSystemModel loads asynchronously; wait for the actual rows.
        for _ in range(100):
            if bar.maximum() > 0:
                break
            QTest.qWait(50)
        self.assertGreater(bar.maximum(), 0)
        mime = self.mime(self.paths[:1])
        def hover(y):
            tree.dragMoveEvent(QDragMoveEvent(QPoint(50, y), Qt.DropAction.MoveAction,
                                mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
        bar.setValue(0)
        hover(tree.viewport().height() - 2)
        QTest.qWait(400)
        self.assertGreater(bar.value(), 0)
        value = bar.value()
        hover(2)
        QTest.qWait(250)
        self.assertLess(bar.value(), value)
        tree.dragLeaveEvent(QDragLeaveEvent())
        value = bar.value()
        QTest.qWait(180)
        self.assertEqual(bar.value(), value)
        self.assertFalse(tree._expand_timer.isActive())
