import unittest
from pathlib import Path
from unittest.mock import patch

import test_v14
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMenu

from src.ui.thumbnail_view import ROLE_IS_FOLDER, ROLE_PATH
from src.utils import windows_integration


class FeaturesV22(unittest.TestCase):
    setUpClass = classmethod(test_v14.NewBehaviors.setUpClass.__func__)
    setUp = test_v14.NewBehaviors.setUp
    tearDown = test_v14.NewBehaviors.tearDown

    def _folder_item(self, path):
        return next(self.grid.item(row) for row in range(self.grid.count())
                    if self.grid.item(row).data(ROLE_PATH) == str(path))

    def test_copy_then_select_folder_and_ctrl_v_pastes_inside(self):
        destination = self.root / 'test'
        destination.mkdir()
        self.tab.refresh()
        self.grid.select_path(self.paths[0])
        self.grid.copy_selected()
        folder = self._folder_item(destination)
        self.grid.clearSelection()
        self.grid.setCurrentItem(folder)
        folder.setSelected(True)
        self.grid.paste_images()
        self.assertTrue(Path(self.paths[0]).exists())
        self.assertEqual((destination / '0.png').read_bytes(), Path(self.paths[0]).read_bytes())

    def test_folder_context_menu_offers_paste_into_that_folder(self):
        destination = self.root / 'test'
        destination.mkdir()
        self.tab.refresh()
        folder = self._folder_item(destination)
        position = self.grid.visualItemRect(folder).center()
        actions = []
        def capture(menu, *_args):
            actions.extend(action.text() for action in menu.actions())
        with patch.object(QMenu, 'exec', new=capture):
            self.grid._show_context_menu(position)
        self.assertIn('Coller dans ce dossier (Ctrl+V)', actions)

    def test_all_supported_types_are_registered_before_opening_windows(self):
        executable = self.root / 'TABaTAB Cash.exe'
        with patch('winreg.CreateKey') as create, patch('winreg.SetValueEx') as write, \
             patch.object(windows_integration.ctypes.windll.shell32, 'SHChangeNotify'), \
             patch.object(windows_integration.sys, 'frozen', True, create=True), \
             patch.object(windows_integration.sys, 'executable', str(executable)), \
             patch.object(windows_integration.os, 'startfile') as start:
            windows_integration.configure_default_viewer(self.window)
        keys = [str(call.args[1]) for call in create.call_args_list]
        for extension in windows_integration.COMMON_IMAGE_EXTENSIONS:
            self.assertTrue(any(key.endswith(r'FileAssociations') for key in keys))
            self.assertIn(extension, [call.args[1] for call in write.call_args_list])
        start.assert_called_once()
        self.assertIn('registeredAppUser=TABaTAB%20Cash', start.call_args.args[0])


if __name__ == '__main__':
    unittest.main()
