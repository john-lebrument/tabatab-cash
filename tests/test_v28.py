import unittest
from pathlib import Path

import test_v14
from PIL import Image
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtTest import QTest
from src.utils.file_ops import is_image_file


class FeaturesV28(unittest.TestCase):
    setUpClass = classmethod(test_v14.NewBehaviors.setUpClass.__func__)
    setUp = test_v14.NewBehaviors.setUp
    tearDown = test_v14.NewBehaviors.tearDown

    def test_heic_and_heif_are_image_formats(self):
        self.assertTrue(is_image_file('photo.heic'))
        self.assertTrue(is_image_file('photo.HEIF'))
        import src.utils.image_loader  # Registers the HEIF decoder used by the thumbnail worker.
        path = self.root / 'sample.heic'
        Image.new('RGB', (8, 6), 'red').save(path, format='HEIF')
        with Image.open(path) as decoded:
            self.assertEqual(decoded.size, (8, 6))

    def test_folder_color_is_persisted_and_rendered_in_tree(self):
        folder = self.root / 'Colored'
        folder.mkdir()
        self.tab._set_folder_color(str(folder), '#c8e6c9')
        QTest.qWait(100)
        index = self.tab.tree_model.index(str(folder))
        self.assertTrue(index.isValid())
        self.assertEqual(self.tab.tree_model.data(index, Qt.ItemDataRole.BackgroundRole).color(), QColor('#c8e6c9'))
        key = self.tab.tree_model.color_key(folder)
        self.assertEqual(self.config.get('folder_colors')[key], '#c8e6c9')
        self.tab._set_folder_color(str(folder), None)
        self.assertNotIn(key, self.config.get('folder_colors'))

    def test_mouse_back_and_forward_buttons_follow_folder_history(self):
        child = self.root / 'Child'
        child.mkdir()
        self.tab.navigate_to(str(child))
        QTest.mouseClick(self.grid, Qt.MouseButton.BackButton)
        self.assertEqual(Path(self.tab.current_folder), self.root)
        QTest.mouseClick(self.grid, Qt.MouseButton.ForwardButton)
        self.assertEqual(Path(self.tab.current_folder), child)
