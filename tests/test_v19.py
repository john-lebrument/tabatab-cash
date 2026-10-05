import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import test_v14
from PyQt6.QtCore import Qt, QMimeData, QUrl, QPointF
from PyQt6.QtWidgets import QMessageBox, QMenu, QApplication
from PyQt6.QtTest import QTest
from PIL import Image
from src.utils import file_ops, windows_integration
from build_portable import publish_latest

class FeaturesV19(unittest.TestCase):
    setUpClass = classmethod(test_v14.NewBehaviors.setUpClass.__func__)
    setUp = test_v14.NewBehaviors.setUp
    tearDown = test_v14.NewBehaviors.tearDown
    viewer = test_v14.NewBehaviors.viewer

    def test_no_recycle_fallback_and_undo(self):
        original = Path(self.paths[0]).read_bytes()
        with patch('src.utils.file_ops.QFile') as qfile:
            qfile.return_value.moveToTrash.return_value = False
            file_ops.trash_image(self.paths[0])
        self.assertFalse(Path(self.paths[0]).exists())
        self.assertEqual(file_ops.restore_last_deleted(), self.paths[0])
        self.assertEqual(Path(self.paths[0]).read_bytes(), original)

    def test_native_internal_copy_waits_for_drag_end(self):
        self.grid.select_path(self.paths[0])
        event = MagicMock()
        mime = QMimeData(); mime.setUrls([QUrl.fromLocalFile(self.paths[0])])
        event.mimeData.return_value = mime
        event.source.return_value = self.grid
        event.position.return_value = QPointF(self.grid.visualItemRect(self.grid.item(1)).center())
        event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier
        event.possibleActions.return_value = Qt.DropAction.CopyAction | Qt.DropAction.MoveAction
        copy = self.root / '0 - Copie.png'
        def native(*args):
            self.grid.dropEvent(event)
            self.assertFalse(copy.exists())
        with patch('src.ui.thumbnail_view.QDrag') as drag:
            drag.return_value.exec.side_effect = native
            self.grid.startDrag(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction)
        self.assertEqual(copy.read_bytes(), Path(self.paths[0]).read_bytes())
        self.assertEqual(self.grid.get_selected_file_paths(), [str(copy)])

    def test_video_cut_paste_rename_delete_and_menu(self):
        video = self.root / 'movie.mp4'; video.write_bytes(b'video fixture')
        with patch('src.utils.image_loader.ThumbnailManager.get_thumbnail', return_value=None):
            self.tab.btn_videos.click()
            self.grid.select_path(str(video))
            seen=[]
            def inspect(menu, *args):
                seen.extend(a.text() for a in menu.actions())
            pos=self.grid.visualItemRect(self.grid.currentItem()).center()
            with patch.object(QMenu, 'exec', inspect): self.grid._show_context_menu(pos)
            self.assertTrue(any('Couper' in s for s in seen))
            self.assertFalse(any('Convertir' in s for s in seen))
            QTest.keyClick(self.grid, Qt.Key.Key_X, Qt.KeyboardModifier.ControlModifier)
            destination=self.root/'dest'; destination.mkdir()
            self.tab.navigate_to(str(destination))
            self.grid.paste_images()
            self.assertFalse(video.exists())
            moved=destination/video.name
            self.assertEqual(moved.read_bytes(),b'video fixture')
            clipboard = QApplication.clipboard().mimeData()
            self.assertTrue(clipboard is None or not clipboard.hasUrls())
            changes=file_ops.rename_images([str(moved)],'Renamed')
            renamed=Path(changes[0][1]); self.assertEqual(renamed.suffix,'.mp4')
            with patch('src.utils.file_ops.QFile') as qfile:
                qfile.return_value.moveToTrash.return_value=False
                file_ops.trash_image(renamed)
            self.assertFalse(renamed.exists())
            file_ops.restore_last_deleted(); self.assertTrue(renamed.exists())
            self.assertIn('#16853b',self.tab.btn_videos.styleSheet())
            self.assertIn('ON',self.tab.btn_videos.text())

    def test_rotation_cancel_discard_save(self):
        viewer=self.viewer(); original=Path(self.paths[0]).read_bytes()
        viewer.rotate_image()
        with patch.object(viewer,'_rotation_choice',return_value=QMessageBox.StandardButton.Cancel): viewer.next_image()
        self.assertEqual(viewer.current_index,0)
        with patch.object(viewer,'_rotation_choice',return_value=QMessageBox.StandardButton.Discard): viewer.next_image()
        self.assertEqual(Path(self.paths[0]).read_bytes(),original)
        viewer.prev_image(); viewer.rotate_image()
        with patch.object(viewer,'_rotation_choice',return_value=QMessageBox.StandardButton.Save): viewer.next_image()
        with Image.open(self.paths[0]) as saved: self.assertEqual(saved.size,(240,320))
        self.assertEqual(viewer.current_index,1)

    def test_rotation_save_failure_stays(self):
        viewer=self.viewer(); viewer.rotate_image()
        with patch.object(viewer,'_rotation_choice',return_value=QMessageBox.StandardButton.Save), patch('src.ui.fullscreen_viewer.crop_image',side_effect=OSError('disk full')), patch.object(QMessageBox,'warning'):
            viewer.next_image()
        self.assertEqual(viewer.current_index,0)
        self.assertNotEqual(viewer.rotation_degrees,0)
        viewer.rotation_degrees=0

    def test_explorer_dispatch_no_blocking_stat(self):
        with patch.object(windows_integration.threading,'Thread') as thread, patch.object(Path,'resolve',side_effect=AssertionError('network stat')):
            windows_integration.reveal_in_explorer(self.paths[0])
        thread.return_value.start.assert_called_once()
        self.assertTrue(thread.call_args.kwargs['daemon'])

    def test_association_registration_does_not_override_userchoice(self):
        with patch('winreg.CreateKey') as create, patch('winreg.SetValueEx') as write:
            windows_integration.register_default_viewer(self.root/'TABaTAB Cash.exe')
        keys=[str(c.args[1]) for c in create.call_args_list]
        self.assertFalse(any('UserChoice' in k for k in keys))
        self.assertTrue(any('RegisteredApplications' in k for k in keys))
        values=[c.args[-1] for c in write.call_args_list]
        self.assertIn('"'+str(self.root/'TABaTAB Cash.exe')+'" "%1"',values)

    def test_publish_keeps_local_history_and_unrelated_files(self):
        latest=self.root/'latest'; latest.mkdir()
        old=latest/'TABaTAB_Cash_Portable_v1.8'; old.mkdir(); (old/'app.exe').write_bytes(b'old')
        unrelated=latest/'other.txt'; unrelated.write_text('keep')
        release=self.root/'TABaTAB_Cash_Portable_v1.9'; release.mkdir(); (release/'TABaTAB Cash.exe').write_bytes(b'new')
        published=publish_latest(release,latest)
        self.assertFalse(old.exists()); self.assertTrue(release.exists()); self.assertTrue(unrelated.exists())
        self.assertEqual((published/'TABaTAB Cash.exe').read_bytes(),b'new')
