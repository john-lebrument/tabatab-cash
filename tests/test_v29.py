import unittest
from pathlib import Path
from unittest.mock import patch

import test_v14
from PIL import Image
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMenu, QLabel
from src.ui.browser_tab import DuplicateResultsDialog, FolderColorDelegate, ROLE_PATH


class FeaturesV29(unittest.TestCase):
    setUpClass = classmethod(test_v14.NewBehaviors.setUpClass.__func__)
    setUp = test_v14.NewBehaviors.setUp
    tearDown = test_v14.NewBehaviors.tearDown

    def test_favorite_menu_can_open_folder_in_explorer(self):
        folder = self.root / 'Favorite folder'
        folder.mkdir()
        self.tab.add_folder_to_favorites(str(folder))
        item = next(self.tab.fav_list.item(i) for i in range(self.tab.fav_list.count())
                    if self.tab.fav_list.item(i).data(ROLE_PATH) == str(folder))
        pos = self.tab.fav_list.visualItemRect(item).center()

        def trigger_action(menu, *args):
            action = next(action for action in menu.actions()
                          if action.text() == 'Ouvrir dans l’explorateur')
            action.trigger()

        with patch.object(QMenu, 'exec', trigger_action), \
                patch('src.ui.browser_tab.open_folder_in_explorer') as open_folder:
            self.tab._show_fav_context_menu(pos)
        open_folder.assert_called_once_with(str(folder))

    def test_heic_fullscreen_decodes_pixels_instead_of_black_pixmap(self):
        path = self.root / 'full-screen.heic'
        Image.new('RGB', (48, 32), (210, 30, 40)).save(path, format='HEIF')
        self.window._on_request_fullscreen([str(path)], str(path))
        self.app.processEvents()
        pixmap = self.window.fullscreen_viewer.current_pixmap
        self.assertFalse(pixmap.isNull())
        self.assertEqual((pixmap.width(), pixmap.height()), (48, 32))

    def test_duplicate_results_use_french_cards_and_image_previews(self):
        first = self.root / 'keeper.png'
        second = self.root / 'duplicate.png'
        Image.new('RGB', (20, 12), 'green').save(first)
        Image.new('RGB', (20, 12), 'green').save(second)
        dialog = DuplicateResultsDialog([('digest', [str(first), str(second)])], [], 1, self.tab)
        labels = [label.text() for label in dialog.findChildren(QLabel)]
        self.assertTrue(any('<b>À CONSERVER</b>' in label for label in labels))
        self.assertTrue(any('<b>À ENVOYER À LA CORBEILLE</b>' in label for label in labels))
        self.assertEqual(dialog.delete_button.text(), 'Supprimer les doublons')
        previews = [label for label in dialog.findChildren(QLabel)
                    if label.pixmap() is not None and not label.pixmap().isNull()]
        self.assertEqual(len(previews), 2)
        dialog.close()

    def test_folder_color_delegate_is_installed_and_vivid(self):
        folder = self.root / 'Colored'
        folder.mkdir()
        self.tab._set_folder_color(str(folder), '#ff1744')
        self.assertIsInstance(self.tab.tree_view.itemDelegate(), FolderColorDelegate)
        index = self.tab.tree_model.index(str(folder))
        self.assertEqual(self.tab.tree_model.data(index, Qt.ItemDataRole.BackgroundRole).color().name(), '#ff1744')

    def test_video_and_zip_controls_share_active_style_and_sort_is_highlighted(self):
        self.assertEqual(self.tab.btn_videos.styleSheet(), self.tab.btn_zips.styleSheet())
        self.assertIn('#16853b', self.tab.btn_videos.styleSheet())
        self.assertIn('border: 2px solid #4c8dcc', self.tab.combo_sort.styleSheet())
        self.assertIn('font-weight: 800', self.tab.findChild(QLabel, 'sortCriteriaLabel').styleSheet())
