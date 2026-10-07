import unittest
from pathlib import Path
from unittest.mock import patch
import test_v14
from PIL import Image, ImageOps
from PyQt6.QtCore import Qt, QMimeData, QUrl, QPointF
from PyQt6.QtGui import QDropEvent
from PyQt6.QtTest import QTest
from src.utils.file_ops import crop_image
from src.utils.duplicates import find_duplicates, recycle_duplicates
from src.ui.thumbnail_view import ROLE_PATH


class FeaturesV27(unittest.TestCase):
    setUpClass = classmethod(test_v14.NewBehaviors.setUpClass.__func__)
    setUp = test_v14.NewBehaviors.setUp
    tearDown = test_v14.NewBehaviors.tearDown
    viewer = test_v14.NewBehaviors.viewer

    def asymmetrical(self):
        image = Image.new('RGB', (60, 40), 'red')
        image.paste('blue', (0, 0, 20, 40))
        image.save(self.paths[0])
        return image

    def test_h_mirrors_selected_file_twice_without_changing_dimensions(self):
        image = self.asymmetrical()
        self.grid.select_path(self.paths[0])
        QTest.keyClick(self.grid, Qt.Key.Key_H)
        with Image.open(self.paths[0]) as result:
            self.assertEqual(result.tobytes(), ImageOps.mirror(image).tobytes())
        QTest.keyClick(self.grid, Qt.Key.Key_H)
        with Image.open(self.paths[0]) as result:
            self.assertEqual(result.tobytes(), image.tobytes())

    def test_fullscreen_rotation_then_mirror_saves_preview_orientation(self):
        image = self.asymmetrical()
        viewer = self.viewer()
        viewer.rotate_image(90)
        QTest.keyClick(viewer.view, Qt.Key.Key_H)
        self.assertTrue(viewer.horizontal_mirror)
        self.assertEqual(viewer.rotation_degrees, 270)
        target = self.root / 'transformed.png'
        crop_image(self.paths[0], (0, 0, 40, 60), target,
                   rotation_degrees=viewer.rotation_degrees, horizontal_mirror=viewer.horizontal_mirror)
        expected = ImageOps.mirror(image.rotate(-90, expand=True))
        with Image.open(target) as result:
            self.assertEqual(result.tobytes(), expected.tobytes())
        viewer.load_current_image()
        self.assertFalse(viewer.horizontal_mirror)

    def test_home_end_scroll_to_first_and_last_image_after_folders(self):
        (self.root / 'aaa').mkdir()
        for i in range(90): Image.new('RGB', (10, 10)).save(self.root / f'photo{i:03}.png')
        self.tab.refresh(); self.app.processEvents()
        QTest.keyClick(self.grid, Qt.Key.Key_End)
        self.assertEqual(Path(self.grid.currentItem().data(ROLE_PATH)).name, 'photo089.png')
        self.assertGreater(self.grid.verticalScrollBar().value(), 0)
        QTest.keyClick(self.grid, Qt.Key.Key_Home)
        self.assertEqual(Path(self.grid.currentItem().data(ROLE_PATH)).name, '0.png')
        self.assertEqual(self.grid.verticalScrollBar().value(), 0)

    def test_directory_watch_adds_and_sorts_external_photo_preserving_selection(self):
        self.grid.select_path(self.paths[1])
        new = self.root / '_new.png'
        Image.new('RGB', (10, 10)).save(new)
        for _ in range(40):
            if str(new) in self.grid.all_files: break
            QTest.qWait(50)
        self.assertIn(str(new), self.grid.all_files)
        self.assertEqual(self.grid.all_files, [str(p) for p in sorted([Path(p) for p in self.paths] + [new], key=self.grid._sort_key)])
        self.assertEqual(self.grid.get_selected_file_paths(), [self.paths[1]])
        new.unlink()
        for _ in range(40):
            if str(new) not in self.grid.all_files: break
            QTest.qWait(50)
        self.assertNotIn(str(new), self.grid.all_files)

    def test_switch_to_existing_tab_reads_new_files(self):
        folder = self.root / 'Other'; folder.mkdir()
        other = self.window.add_tab(str(folder))
        new = self.root / 'new.png'; Image.new('RGB', (10, 10)).save(new)
        self.window.tab_widget.setCurrentWidget(self.tab)
        self.assertIn(str(new), self.grid.all_files)

    def test_zip_toggle_opens_archive_without_adding_it_to_image_viewer(self):
        zipfile = self.root / 'test.ZIP'; zipfile.write_bytes(b'PK')
        self.tab.refresh()
        self.assertNotIn(str(zipfile), self.grid.get_selected_file_paths())
        self.tab.btn_zips.setChecked(True)
        item = next(self.grid.item(i) for i in range(self.grid.count()) if self.grid.item(i).data(ROLE_PATH) == str(zipfile))
        with patch('src.ui.thumbnail_view.QDesktopServices.openUrl', return_value=True) as opened:
            self.grid._on_item_double_clicked(item)
        self.assertEqual(Path(opened.call_args.args[0].toLocalFile()), zipfile)
        self.assertNotIn(str(zipfile), self.grid.all_files)
        self.tab.btn_zips.setChecked(False)
        self.assertNotIn(str(zipfile), [self.grid.item(i).data(ROLE_PATH) for i in range(self.grid.count())])

    def test_duplicates_use_contents_across_extensions_ignore_subfolders(self):
        # Existing test pictures also form one exact duplicate group.
        a = self.root / 'A.txt'; b = self.root / 'B.zip'; c = self.root / 'C.txt'
        a.write_bytes(b'abc'); b.write_bytes(b'abc'); c.write_bytes(b'abd')
        sub = self.root / 'sub'; sub.mkdir(); (sub / 'D.txt').write_bytes(b'abc')
        groups, errors = find_duplicates(self.root)
        self.assertEqual(errors, [])
        group = next(paths for digest, paths in groups if a in paths)
        self.assertEqual(group, [a, b])

    def test_duplicate_changed_or_keeper_missing_is_never_recycled(self):
        a = self.root / 'A.txt'; b = self.root / 'B.txt'
        a.write_bytes(b'abc'); b.write_bytes(b'abc')
        groups, _ = find_duplicates(self.root)
        groups = [(digest, paths) for digest, paths in groups if a in paths]
        b.write_bytes(b'abd')
        with patch('src.utils.duplicates.QFile') as file:
            removed, errors = recycle_duplicates(groups)
        file.assert_not_called(); self.assertFalse(removed); self.assertTrue(errors)
        b.write_bytes(b'abc'); a.unlink()
        with patch('src.utils.duplicates.QFile') as file:
            removed, errors = recycle_duplicates(groups)
        file.assert_not_called(); self.assertTrue(b.exists()); self.assertTrue(errors)

    def test_duplicate_unavailable_recycle_bin_preserves_file(self):
        groups, _ = find_duplicates(self.root)
        with patch('src.utils.duplicates.QFile') as file:
            file.return_value.moveToTrash.return_value = False
            removed, errors = recycle_duplicates(groups)
        self.assertFalse(removed); self.assertTrue(errors)
        self.assertTrue(all(Path(p).exists() for p in self.paths))

    def test_tab_drop_rejects_empty_strip(self):
        bar = self.window.custom_tab_bar
        mime = QMimeData(); mime.setUrls([QUrl.fromLocalFile(self.paths[0])])
        event = QDropEvent(QPointF(-1, -1), Qt.DropAction.MoveAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        bar.dropEvent(event)
        self.assertFalse(event.isAccepted()); self.assertTrue(Path(self.paths[0]).exists())

    def test_native_grid_accept_without_drop_does_not_use_old_hover(self):
        folder = self.root / 'Charlie'; folder.mkdir()
        self.tab.refresh(); self.grid.select_path(self.paths[0])
        with patch('src.ui.thumbnail_view.QDrag') as drag:
            def result(*args):
                self.grid._last_drop_target_folder = str(folder)
                return Qt.DropAction.MoveAction
            drag.return_value.exec.side_effect = result
            drag.return_value.target.return_value = self.grid.viewport()
            self.grid.startDrag(Qt.DropAction.MoveAction)
        self.assertTrue(Path(self.paths[0]).exists())
        self.assertFalse(list(folder.iterdir()))

    def test_internal_tab_drop_captures_root_then_transfers_after_drag(self):
        target = self.root / 'Destination'; target.mkdir()
        for name in ('Alpha', 'Beta', 'Charlie'): (target / name).mkdir()
        target_tab = self.window.add_tab(str(target), switch_to=False)
        self.grid.select_path(self.paths[0])
        bar = self.window.custom_tab_bar
        mime = QMimeData(); mime.setUrls([QUrl.fromLocalFile(self.paths[0])])
        native = QDropEvent(QPointF(bar.tabRect(1).center()), Qt.DropAction.MoveAction,
                            mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        grid = self.grid
        class SourcedEvent:
            def source(self): return grid
            def __getattr__(self, name): return getattr(native, name)
        def native_drag(*args):
            bar.dropEvent(SourcedEvent())
            self.assertTrue(native.isAccepted())
            self.assertTrue(Path(self.paths[0]).exists())
            self.assertEqual(Path(grid._pending_internal_drop[1]), target)
            return Qt.DropAction.MoveAction
        with patch('src.ui.thumbnail_view.QDrag') as drag:
            drag.return_value.exec.side_effect = native_drag
            grid.startDrag(Qt.DropAction.MoveAction)
        self.assertFalse(Path(self.paths[0]).exists())
        self.assertTrue((target / '0.png').exists())
        self.assertFalse((target / 'Charlie' / '0.png').exists())

    def test_recycling_identical_duplicates_keeps_first_copy(self):
        a = self.root / 'A.txt'; b = self.root / 'B.txt'
        a.write_bytes(b'abc'); b.write_bytes(b'abc')
        groups, _ = find_duplicates(self.root)
        groups = [(digest, paths) for digest, paths in groups if a in paths]
        class FakeRecycle:
            def __init__(self, path): self.path = Path(path)
            def moveToTrash(self): self.path.rename(self.root / 'recycled.txt'); return True
        FakeRecycle.root = self.root
        with patch('src.utils.duplicates.QFile', FakeRecycle):
            removed, errors = recycle_duplicates(groups)
        self.assertEqual(removed, [str(b)]); self.assertFalse(errors)
        self.assertTrue(a.exists()); self.assertFalse(b.exists())


if __name__ == '__main__': unittest.main()
