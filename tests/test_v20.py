import unittest
from pathlib import Path
from unittest.mock import patch

import test_v14
from PIL import Image
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox


class FeaturesV20(unittest.TestCase):
    setUpClass = classmethod(test_v14.NewBehaviors.setUpClass.__func__)
    setUp = test_v14.NewBehaviors.setUp
    tearDown = test_v14.NewBehaviors.tearDown
    viewer = test_v14.NewBehaviors.viewer

    def test_batch_rotation_from_thumbnails(self):
        self.grid.setCurrentRow(0)
        self.grid.item(1).setSelected(True)
        self.grid._rotate_selected(-90)
        for path in self.paths[:2]:
            with Image.open(path) as image:
                self.assertEqual(image.size, (240, 320))
        with Image.open(self.paths[2]) as image:
            self.assertEqual(image.size, (320, 240))
        self.assertEqual(set(self.grid.get_selected_file_paths()), set(self.paths[:2]))
        self.assertIn('2 image(s) tournée(s)', self.window.status_bar.currentMessage())

    def test_video_single_click_does_not_open_double_click_does(self):
        video = self.root / 'film.mp4'
        video.write_bytes(b'video')
        self.grid.set_show_videos(True)
        item = next(self.grid.item(row) for row in range(self.grid.count())
                    if self.grid.item(row).data(Qt.ItemDataRole.UserRole) == str(video))
        with patch('src.ui.thumbnail_view.QDesktopServices.openUrl', return_value=True) as launch:
            self.grid.itemClicked.emit(item)
            launch.assert_not_called()
            self.grid.itemDoubleClicked.emit(item)
            launch.assert_called_once()

    def test_internal_ctrl_drag_fallback_creates_copy(self):
        self.grid.select_path(self.paths[0])
        with patch('src.ui.thumbnail_view.QApplication.keyboardModifiers',
                   return_value=Qt.KeyboardModifier.ControlModifier), \
             patch('src.ui.thumbnail_view.QDrag') as drag:
            drag.return_value.exec.return_value = Qt.DropAction.CopyAction
            drag.return_value.target.return_value = self.grid.viewport()
            self.grid.startDrag(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction)
        self.assertTrue((self.root / '0 - Copie.png').exists())

    def test_rotation_question_has_readable_explicit_style(self):
        viewer = self.viewer()
        viewer.rotate_image()

        with patch.object(QMessageBox, 'exec', return_value=0):
            self.assertEqual(viewer._rotation_choice(), QMessageBox.StandardButton.Cancel)
        dialog = viewer._last_rotation_dialog
        self.assertIn('color: white', dialog.styleSheet())
        self.assertEqual(dialog.button(QMessageBox.StandardButton.Save).text(), 'Enregistrer')
        self.assertEqual(dialog.button(QMessageBox.StandardButton.Discard).text(), 'Ne pas enregistrer')
        viewer.rotation_degrees = 0


if __name__ == '__main__':
    unittest.main()
