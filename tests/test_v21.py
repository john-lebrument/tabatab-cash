import unittest
from pathlib import Path
from unittest.mock import patch

import test_v14
from PIL import Image
from PyQt6.QtCore import QMimeData, QRectF, Qt, QUrl
from PyQt6.QtGui import QDragMoveEvent

from src.ui.thumbnail_view import ROLE_IS_FOLDER, ROLE_PATH
from src.ui.blur_tool import BlurSelection, blurred_regions, save_blurs


class FeaturesV21(unittest.TestCase):
    setUpClass = classmethod(test_v14.NewBehaviors.setUpClass.__func__)
    setUp = test_v14.NewBehaviors.setUp
    tearDown = test_v14.NewBehaviors.tearDown
    viewer = test_v14.NewBehaviors.viewer

    def test_unconfirmed_internal_drag_never_moves_to_hovered_grid_folder(self):
        destination = self.root / 'destination'
        destination.mkdir()
        self.tab.refresh()
        folder_item = next(self.grid.item(row) for row in range(self.grid.count())
                           if self.grid.item(row).data(ROLE_IS_FOLDER))
        self.grid.select_path(self.paths[0])
        position = self.grid.visualItemRect(folder_item).center()
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(self.paths[0])])

        def native_drag(*_args):
            event = QDragMoveEvent(position,
                Qt.DropAction.CopyAction | Qt.DropAction.MoveAction,
                mime,
                Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
            self.grid.dragMoveEvent(event)
            return Qt.DropAction.MoveAction

        with patch('src.ui.thumbnail_view.QDrag') as drag:
            drag.return_value.exec.side_effect = native_drag
            drag.return_value.target.return_value = self.grid.viewport()
            self.grid.startDrag(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction)
        self.assertTrue(Path(self.paths[0]).exists())
        self.assertFalse((destination / '0.png').exists())

    def test_blur_starts_empty_and_collects_multiple_ovals(self):
        viewer = self.viewer()
        viewer.start_blur()
        self.assertEqual(viewer.blur_item.get_boxes(), [])
        viewer.blur_item.addRect(QRectF(20, 30, 60, 70))
        viewer.blur_item.addRect(QRectF(180, 100, 80, 90))
        viewer._update_blur_preview()
        self.assertEqual(len(viewer.blur_item.get_boxes()), 2)
        self.assertEqual(viewer.blur_count.text(), '2 zones')
        viewer._remove_last_blur()
        self.assertEqual(len(viewer.blur_item.get_boxes()), 1)

    def test_multiple_blurs_are_elliptical_and_saved_together(self):
        source = self.root / 'pattern.png'
        image = Image.new('RGB', (160, 100))
        pixels = image.load()
        for y in range(image.height):
            for x in range(image.width):
                pixels[x, y] = (255 if (x + y) % 2 else 0, x % 256, y % 256)
        image.save(source)
        boxes = [(10, 10, 70, 70), (90, 20, 150, 80)]
        preview = blurred_regions(image, boxes, 80)
        self.assertEqual(preview.getpixel((10, 10)), image.getpixel((10, 10)))
        self.assertNotEqual(preview.getpixel((40, 40)), image.getpixel((40, 40)))
        self.assertNotEqual(preview.getpixel((120, 50)), image.getpixel((120, 50)))
        self.assertEqual(preview.getpixel((80, 50)), image.getpixel((80, 50)))
        result = save_blurs(source, boxes, 80)
        with Image.open(result) as saved:
            self.assertEqual(saved.getpixel((10, 10)), image.getpixel((10, 10)))
            self.assertNotEqual(saved.getpixel((40, 40)), image.getpixel((40, 40)))


if __name__ == '__main__':
    unittest.main()
