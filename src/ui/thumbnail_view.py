import os
import re
import time
from pathlib import Path
from PyQt6.QtCore import (
    QMimeData,
    QEvent,
    QItemSelectionModel,
    QPoint,
    QRect,
    QSize,
    Qt,
    QUrl,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QAction,
    QColor,
    QDrag,
    QIcon,
    QPainter,
    QPixmap,
    QWheelEvent,
    QFont,
    QKeySequence,
    QDesktopServices,
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QInputDialog,
)

from src.utils.file_ops import is_image_file, move_file, copy_file, convert_image_format, trash_image, restore_last_deleted
from src.utils.image_loader import ThumbnailManager
from src.utils.file_ops import rename_images, rename_folder, rotate_image_file
from src.ui.drag_feedback import drop_action, paint_destination, set_large_drag_cursors
from src.ui.folder_actions import create_folder, delete_folders
from src.utils.file_ops import is_video_file, is_media_file
from src.utils.windows_integration import reveal_in_explorer

# Item data roles
ROLE_PATH = Qt.ItemDataRole.UserRole
ROLE_IS_FOLDER = Qt.ItemDataRole.UserRole + 1


class ThumbnailItem(QListWidgetItem):
    """ListWidgetItem representing either a subfolder or an image file."""

    def __init__(self, file_path: str, size: int, is_folder: bool = False):
        super().__init__()
        self.file_path = file_path
        self.is_folder = is_folder
        self.filename = Path(file_path).name or file_path

        display_text = f"📁 {self.filename}" if is_folder else self.filename
        self.setText(display_text)
        self.setData(ROLE_PATH, file_path)
        self.setData(ROLE_IS_FOLDER, is_folder)
        self.setSizeHint(QSize(size + 24, size + 50))
        self.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)


class ThumbnailView(QListWidget):
    """
    Thumbnail grid displaying both subfolders and image files.
    Supports Ctrl+Wheel zooming, multi-selection, and inter-tab/folder drag & drop.
    """

    image_double_clicked = pyqtSignal(str)
    floating_requested = pyqtSignal(str)
    folder_double_clicked = pyqtSignal(str)
    open_in_new_tab_requested = pyqtSignal(str)
    add_favorite_requested = pyqtSignal(str)
    sort_requested = pyqtSignal(str, str)
    image_deleted = pyqtSignal(str)
    image_restored = pyqtSignal(str)
    clipboard_image_saved = pyqtSignal(str)
    images_renamed = pyqtSignal(list)
    folder_renamed = pyqtSignal(str, str)
    folder_created = pyqtSignal(str)
    folder_deleted = pyqtSignal(str)
    images_converted = pyqtSignal(list)
    images_rotated = pyqtSignal(list)
    files_dropped = pyqtSignal(list, str, bool)  # source_files, target_folder, is_copy
    selection_changed_info = pyqtSignal(int, int)  # selected_count, total_count
    thumbnail_size_changed = pyqtSignal(int)

    def __init__(self, thumbnail_manager: ThumbnailManager, parent=None):
        super().__init__(parent)
        self.thumbnail_manager = thumbnail_manager
        self.current_folder: str = ""
        self.current_thumb_size: int = 150
        self.all_files: list[str] = []
        self.show_videos = False
        self._last_video_open = ('', 0)
        self.drag_start_pos: QPoint | None = None
        self.sort_by = 'name'
        self.sort_order = 'asc'
        self._drop_folder = None
        self._last_drop_target_folder = None

        self._folder_icon_cache: dict[int, QIcon] = {}
        self._thumbnail_timer = QTimer(self)
        self._thumbnail_timer.setSingleShot(True)
        self._thumbnail_timer.setInterval(80)
        self._thumbnail_timer.timeout.connect(self.refresh_visible_thumbnails)
        self._setup_view()
        self.thumbnail_manager.thumbnail_ready.connect(self._on_thumbnail_ready)
        self.verticalScrollBar().valueChanged.connect(lambda: self._thumbnail_timer.start())

    def _setup_view(self):
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setMovement(QListWidget.Movement.Static)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSpacing(8)
        self.setWordWrap(True)
        self.setUniformItemSizes(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

        self.setThumbnailSize(self.current_thumb_size)
        # IconMode with Static movement disables drops on the actual viewport.
        # File transfers must be enabled there, not only on the outer widget.
        self.viewport().setAcceptDrops(True)

        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def setThumbnailSize(self, size: int):
        self.current_thumb_size = max(60, min(600, size))
        self.setIconSize(QSize(self.current_thumb_size, self.current_thumb_size))
        self.setGridSize(QSize(self.current_thumb_size + 24, self.current_thumb_size + 52))
        
        # Update existing items size hint
        for i in range(self.count()):
            item = self.item(i)
            item.setSizeHint(QSize(self.current_thumb_size + 24, self.current_thumb_size + 52))
            if item.data(ROLE_IS_FOLDER):
                item.setIcon(self._get_folder_icon(self.current_thumb_size))
            elif not item.icon().isNull():
                pix = item.icon().pixmap(QSize(600, 600))
                item.setIcon(QIcon(pix.scaled(self.iconSize(), Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation)))

        self._thumbnail_timer.start()

    def setFolder(self, folder_path: str):
        self._drop_folder = None
        self.current_folder = folder_path
        self.clear()
        self.all_files.clear()

        p = Path(folder_path)
        if not p.exists() or not p.is_dir():
            return

        try:
            entries = list(p.iterdir())
        except Exception as e:
            print(f"Error accessing directory {folder_path}: {e}")
            return

        # 1. First add subdirectories
        subdirs = sorted([d for d in entries if d.is_dir()], key=self._sort_key,
                         reverse=self.sort_order == 'desc')
        folder_icon = self._get_folder_icon(self.current_thumb_size)
        for d in subdirs:
            dir_str = str(d)
            item = ThumbnailItem(dir_str, self.current_thumb_size, is_folder=True)
            item.setIcon(folder_icon)
            self.addItem(item)

        # 2. Then add image files
        images = sorted([f for f in entries if f.is_file() and (is_image_file(f) or (self.show_videos and is_video_file(f)))],
                        key=self._sort_key, reverse=self.sort_order == 'desc')
        placeholder = self._create_placeholder_pixmap(self.current_thumb_size)

        for f in images:
            file_str = str(f)
            if is_image_file(f):
                self.all_files.append(file_str)
            item = ThumbnailItem(file_str, self.current_thumb_size, is_folder=False)
            if is_video_file(f):
                item.setText(f'▶ {f.name}')
                item.setToolTip('Vidéo — cliquer pour ouvrir dans le lecteur par défaut')
            
            # Check cache
            cached = self.thumbnail_manager.cache.get(f"{file_str}_{self.current_thumb_size}")
            if cached:
                item.setIcon(QIcon(cached))
            else:
                item.setIcon(QIcon(self._video_placeholder(self.current_thumb_size) if is_video_file(f) else placeholder))

            self.addItem(item)

        self.selection_changed_info.emit(0, len(self.all_files))
        self._thumbnail_timer.start()

    @staticmethod
    def _natural_name(path):
        return tuple((1, int(part)) if part.isdigit() else (0, part.casefold())
                     for part in re.split(r'(\d+)', path.name))

    def _sort_key(self, path):
        name = self._natural_name(path)
        if self.sort_by == 'name':
            return name
        if self.sort_by == 'type':
            return (path.suffix.casefold(), name)
        try:
            stat = path.stat()
            value = {'date': stat.st_mtime, 'created': getattr(stat, 'st_birthtime', stat.st_ctime),
                     'size': stat.st_size}.get(self.sort_by, 0)
        except OSError:
            value = 0
        return (value, name)

    def set_sort(self, criterion, order):
        self.sort_by = criterion if criterion in ('name', 'date', 'created', 'size', 'type') else 'name'
        self.sort_order = 'desc' if order == 'desc' else 'asc'
        if self.current_folder:
            selected = set(self.get_selected_file_paths())
            current = self.currentItem().data(ROLE_PATH) if self.currentItem() else None
            self.setFolder(self.current_folder)
            for i in range(self.count()):
                item = self.item(i)
                if item.data(ROLE_PATH) == current:
                    self.setCurrentRow(i, QItemSelectionModel.SelectionFlag.NoUpdate)
                item.setSelected(item.data(ROLE_PATH) in selected)

    def copy_selected(self):
        self._set_clipboard(False)

    def cut_selected(self):
        self._set_clipboard(True)

    def _set_clipboard(self, cut):
        paths = [p for p in self.get_selected_file_paths() if Path(p).is_file() and is_media_file(p)]
        if not paths:
            return
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(p) for p in paths])
        mime.setData('application/x-tabatab-cut', b'1' if cut else b'0')
        mime.setData('application/x-qt-windows-mime;value="Preferred DropEffect"', (2 if cut else 1).to_bytes(4, 'little'))
        QApplication.clipboard().setMimeData(mime)

    def paste_images(self, target_folder=None):
        mime = QApplication.clipboard().mimeData()
        if target_folder is None:
            current = self.currentItem()
            if current and current.isSelected() and current.data(ROLE_IS_FOLDER):
                target_folder = current.data(ROLE_PATH)
            else:
                target_folder = self.current_folder
        if not target_folder or mime is None:
            return
        if not Path(target_folder).is_dir():
            QMessageBox.warning(self, 'Collage impossible', 'Le dossier de destination est inaccessible.')
            return
        if not mime.hasUrls():
            if mime.hasImage():
                image = QApplication.clipboard().image()
                if image.isNull():
                    return
                destination = Path(target_folder) / 'Image collée.png'
                number = 1
                while destination.exists():
                    destination = Path(target_folder) / f'Image collée ({number}).png'
                    number += 1
                if not image.save(str(destination), 'PNG'):
                    QMessageBox.warning(self, 'Collage impossible', "Impossible d'enregistrer l'image dans ce dossier.")
                else:
                    self.clipboard_image_saved.emit(str(destination))
            return
        paths = [u.toLocalFile() for u in mime.urls() if u.isLocalFile()]
        paths = [p for p in paths if Path(p).is_file() and is_media_file(p)]
        if paths:
            effect = bytes(mime.data('application/x-qt-windows-mime;value="Preferred DropEffect"'))
            cut = bytes(mime.data('application/x-tabatab-cut')) == b'1' or int.from_bytes(effect or b'\0', 'little') == 2
            self.files_dropped.emit(paths, str(target_folder), not cut)
            if cut:
                remaining = [p for p in paths if Path(p).exists()]
                if not remaining:
                    QApplication.clipboard().clear()
                else:
                    rest = QMimeData()
                    rest.setUrls([QUrl.fromLocalFile(p) for p in remaining])
                    rest.setData('application/x-tabatab-cut', b'1')
                    rest.setData('application/x-qt-windows-mime;value="Preferred DropEffect"', (2).to_bytes(4, 'little'))
                    QApplication.clipboard().setMimeData(rest)

    def refresh_visible_thumbnails(self):
        """Decode only visible images (plus one screen ahead), not the entire folder."""
        if not self.isVisible():
            return
        visible = self.viewport().rect().adjusted(0, -self.viewport().height(), 0, self.viewport().height())
        for i in range(self.count()):
            item = self.item(i)
            if not item.data(ROLE_IS_FOLDER) and self.visualItemRect(item).intersects(visible):
                file_path = item.data(ROLE_PATH)
                if file_path:
                    cached = self.thumbnail_manager.get_thumbnail(file_path, self.current_thumb_size)
                    if cached:
                        item.setIcon(QIcon(cached))

    def _get_folder_icon(self, size: int) -> QIcon:
        if size in self._folder_icon_cache:
            return self._folder_icon_cache[size]

        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw stylish modern folder graphic
        w = size * 0.75
        h = size * 0.6
        x = (size - w) / 2
        y = (size - h) / 2

        # Folder tab (back)
        painter.setBrush(QColor(220, 160, 40))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRect(int(x), int(y), int(w * 0.45), int(h * 0.35)), 4, 4)

        # Folder body (front)
        painter.setBrush(QColor(255, 195, 60))
        painter.drawRoundedRect(QRect(int(x), int(y + h * 0.2), int(w), int(h * 0.8)), 6, 6)

        # Subtle interior line
        painter.setPen(QColor(255, 255, 255, 100))
        painter.drawLine(int(x + 4), int(y + h * 0.25), int(x + w - 4), int(y + h * 0.25))

        painter.end()

        icon = QIcon(pix)
        self._folder_icon_cache[size] = icon
        return icon

    def _create_placeholder_pixmap(self, size: int) -> QPixmap:
        pix = QPixmap(size, size)
        pix.fill(QColor(40, 40, 40, 60))
        painter = QPainter(pix)
        painter.setPen(QColor(100, 100, 100, 120))
        painter.drawRect(0, 0, size - 1, size - 1)
        painter.setPen(QColor(140, 140, 140))
        font = QFont("Segoe UI", max(9, int(size * 0.08)))
        painter.setFont(font)
        painter.drawText(QRect(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, "🖼 Chargement")
        painter.end()
        return pix

    def showEvent(self, event):
        super().showEvent(event)
        self._thumbnail_timer.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._thumbnail_timer.start()

    def _on_thumbnail_ready(self, file_path: str, pixmap: QPixmap, size: int, orig_w: int, orig_h: int):
        if size != self.current_thumb_size:
            return
        for i in range(self.count()):
            item = self.item(i)
            if item.data(ROLE_PATH) == file_path:
                item.setIcon(QIcon(pixmap))
                break

    def _video_placeholder(self, size):
        pix = QPixmap(size, size)
        pix.fill(QColor('#243e57'))
        painter = QPainter(pix)
        painter.setPen(QColor('white'))
        painter.setFont(QFont('Segoe UI', max(12, size // 8)))
        painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, '▶\nVIDÉO')
        painter.end()
        return pix

    def set_show_videos(self, visible):
        self.show_videos = bool(visible)
        self.setFolder(self.current_folder)

    def _open_video(self, path):
        now = time.monotonic()
        if self._last_video_open[0] == path and now - self._last_video_open[1] < 0.8:
            return
        self._last_video_open = (path, now)
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(path)):
            QMessageBox.warning(self, 'Lecture vidéo', 'Impossible de lancer le lecteur vidéo par défaut.')

    def _on_item_double_clicked(self, item: QListWidgetItem):
        path = item.data(ROLE_PATH)
        is_folder = item.data(ROLE_IS_FOLDER)
        if is_folder:
            self.folder_double_clicked.emit(path)
        elif is_video_file(path):
            self._open_video(path)
        else:
            self.image_double_clicked.emit(path)

    def _on_selection_changed(self):
        sel_images = [i for i in self.selectedItems() if not i.data(ROLE_IS_FOLDER) and is_image_file(i.data(ROLE_PATH))]
        self.selection_changed_info.emit(len(sel_images), len(self.all_files))

    def get_selected_file_paths(self) -> list[str]:
        return [item.data(ROLE_PATH) for item in self.selectedItems() if item.data(ROLE_PATH)]

    # Ctrl + Mouse Wheel for instant thumbnail resize
    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            step = 25 if delta > 0 else -25
            new_size = max(64, min(600, self.current_thumb_size + step))
            if new_size != self.current_thumb_size:
                self.setThumbnailSize(new_size)
                self.thumbnail_size_changed.emit(new_size)
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        self.drag_start_pos = event.position().toPoint() if event.button() == Qt.MouseButton.LeftButton else None
        self._pressed_path = self.itemAt(self.drag_start_pos).data(ROLE_PATH) if self.drag_start_pos is not None and self.itemAt(self.drag_start_pos) else None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (self.drag_start_pos is not None and self._pressed_path
                and event.buttons() & Qt.MouseButton.LeftButton
                and (event.position().toPoint() - self.drag_start_pos).manhattanLength() >= QApplication.startDragDistance()):
            # Ctrl-click can deselect the image before Qt starts the drag.
            for i in range(self.count()):
                if self.item(i).data(ROLE_PATH) == self._pressed_path:
                    self.item(i).setSelected(True)
            self.drag_start_pos = None
            self.startDrag(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction)
            return
        super().mouseMoveEvent(event)

    def startDrag(self, supported_actions):
        selected_files = self.get_selected_file_paths()
        if not selected_files:
            return

        self._pending_internal_drop = None
        self._last_drop_target_folder = None
        drag = QDrag(self)
        set_large_drag_cursors(drag)
        mime_data = QMimeData()
        urls = [QUrl.fromLocalFile(p) for p in selected_files]
        mime_data.setUrls(urls)
        drag.setMimeData(mime_data)

        # Drag pixmap
        current_item = self.currentItem()
        if current_item and not current_item.icon().isNull():
            pix = current_item.icon().pixmap(QSize(96, 96))
            drag.setPixmap(pix)
            drag.setHotSpot(QPoint(pix.width() // 2, pix.height() // 2))

        default = Qt.DropAction.CopyAction if QApplication.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier else Qt.DropAction.MoveAction
        result = drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction, default)
        self.drag_start_pos = None
        if self._pending_internal_drop:
            # Refresh the source model only after the native drag has finished.
            self.files_dropped.emit(*self._pending_internal_drop)
            self._pending_internal_drop = None
        elif result in (Qt.DropAction.CopyAction, Qt.DropAction.MoveAction) and drag.target() in (self, self.viewport()):
            # Some Windows/Qt combinations accept an internal drop without
            # forwarding dropEvent. Complete the Explorer-style Ctrl+drag here.
            target = self._last_drop_target_folder or self.current_folder
            self.files_dropped.emit(selected_files, target, result == Qt.DropAction.CopyAction)
        self._last_drop_target_folder = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(drop_action(event))
            event.accept()
        else:
            super().dragEnterEvent(event)

    def viewportEvent(self, event):
        # QListView's IconMode has its own internal item-reordering path.
        # Route file drops before that path can consume the viewport event.
        handlers = {
            QEvent.Type.DragEnter: self.dragEnterEvent,
            QEvent.Type.DragMove: self.dragMoveEvent,
            QEvent.Type.Drop: self.dropEvent,
            QEvent.Type.DragLeave: self.dragLeaveEvent,
        }
        handler = handlers.get(event.type())
        if handler is not None:
            handler(event)
            return True
        return super().viewportEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            item = self.itemAt(event.position().toPoint())
            self._drop_folder = item if item and item.data(ROLE_IS_FOLDER) else None
            self._last_drop_target_folder = (self._drop_folder.data(ROLE_PATH)
                                             if self._drop_folder else self.current_folder)
            self.viewport().update()
            event.setDropAction(drop_action(event))
            event.accept()
        else:
            super().dragMoveEvent(event)

    def dragLeaveEvent(self, event):
        self._drop_folder = None
        self.viewport().update()
        super().dragLeaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._drop_folder is not None:
            paint_destination(self.viewport(), self.visualItemRect(self._drop_folder))

    def dropEvent(self, event):
        self._drop_folder = None
        self.viewport().update()
        try:
            if not event.mimeData().hasUrls() or not self.current_folder:
                super().dropEvent(event)
                return

            urls = event.mimeData().urls()
            source_paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
            source_paths = [p for p in source_paths if p and (is_media_file(p) or Path(p).is_dir())]

            if not source_paths:
                return

            # Check if dropped onto a subfolder item
            pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
            target_folder = self.current_folder
            item_under_cursor = self.itemAt(pos)
            if item_under_cursor and item_under_cursor.data(ROLE_IS_FOLDER):
                target_folder = item_under_cursor.data(ROLE_PATH)

            is_copy = drop_action(event) == Qt.DropAction.CopyAction

            # Avoid dropping into identical folder if MOVE; allow if COPY
            if not is_copy and all(str(Path(p).parent.resolve()) == str(Path(target_folder).resolve()) for p in source_paths):
                event.ignore()
                return

            if event.source() is self:
                self._pending_internal_drop = (source_paths, target_folder, is_copy)
            else:
                self.files_dropped.emit(source_paths, target_folder, is_copy)
            event.setDropAction(Qt.DropAction.CopyAction if is_copy else Qt.DropAction.MoveAction)
            event.accept()
        except Exception as e:
            print(f"Error in ThumbnailView.dropEvent: {e}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_X and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.cut_selected()
            event.accept()
            return
        if event.matches(QKeySequence.StandardKey.Undo):
            try:
                path = restore_last_deleted()
                if path:
                    self.setFolder(self.current_folder)
                    self.select_path(path)
                    self.image_restored.emit(path)
            except OSError as error:
                QMessageBox.warning(self, 'Restauration impossible', str(error))
            return
        if event.matches(QKeySequence.StandardKey.Copy):
            self.copy_selected()
            event.accept()
            return
        if event.matches(QKeySequence.StandardKey.Paste):
            self.paste_images()
            event.accept()
            return
        key = event.key()
        if key == Qt.Key.Key_F2:
            if not event.isAutoRepeat():
                self._rename_selected()
            event.accept()
            return
        if key == Qt.Key.Key_B and not event.modifiers():
            for path in self.get_selected_file_paths():
                if Path(path).is_file() and is_image_file(path):
                    self.floating_requested.emit(path)
            event.accept()
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            item = self.currentItem()
            if item:
                self._on_item_double_clicked(item)
                return
        elif key == Qt.Key.Key_Delete:
            if not event.isAutoRepeat():
                self._delete_selected(bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier))
            return
        super().keyPressEvent(event)

    def _rename_selected(self):
        items = sorted(self.selectedItems(), key=self.row)
        folders = [i for i in items if i.data(ROLE_IS_FOLDER)]
        if folders:
            if len(items) != 1:
                QMessageBox.information(self, 'Renommer un dossier', 'Sélectionnez un seul dossier pour le renommer.')
                return
            path = folders[0].data(ROLE_PATH)
            name, accepted = QInputDialog.getText(self, 'Renommer le dossier', 'Nouveau nom :', text=Path(path).name)
            if accepted:
                try:
                    destination = rename_folder(path, name)
                    self.folder_renamed.emit(path, destination)
                    self.setFolder(self.current_folder)
                    self.select_path(destination)
                except (ValueError, OSError) as error:
                    QMessageBox.warning(self, 'Renommage impossible', str(error))
            return
        paths = [i.data(ROLE_PATH) for i in items if not i.data(ROLE_IS_FOLDER)]
        if not paths:
            return
        label = ('Nom du premier fichier (sans extension).\n'
                 'Exemple : Photo → Photo 001, Photo 002, Photo 003…\n'
                 'La numérotation suit l’ordre affiché des fichiers sélectionnés.'
                 if len(paths) > 1 else 'Nouveau nom (sans extension) :')
        name, accepted = QInputDialog.getText(self, f'Renommer {len(paths)} fichier(s)', label,
                                             text=Path(paths[0]).stem)
        if not accepted:
            return
        try:
            changes = rename_images(paths, name)
            self.images_renamed.emit(changes)
            self.setFolder(self.current_folder)
            selected = {new for old, new in changes}
            for i in range(self.count()):
                self.item(i).setSelected(self.item(i).data(ROLE_PATH) in selected)
            if self.selectedItems():
                first = self.selectedItems()[0]
                self.setCurrentItem(first, QItemSelectionModel.SelectionFlag.NoUpdate)
                self.scrollToItem(first)
        except (ValueError, OSError) as error:
            QMessageBox.warning(self, 'Renommage impossible', str(error))

    def select_path(self, path):
        for i in range(self.count()):
            if Path(self.item(i).data(ROLE_PATH)) == Path(path):
                self.clearSelection()
                self.setCurrentRow(i)
                self.scrollToItem(self.item(i))
                break

    def _delete_selected(self, permanent=False):
        selected = self.get_selected_file_paths()
        if not selected:
            return

        folders = [p for p in selected if Path(p).is_dir()]
        if folders:
            deleted = delete_folders(self, folders)
            if not deleted:
                return
            for path in deleted:
                self.folder_deleted.emit(path)

        for p in selected:
            if not Path(p).is_file() or not is_media_file(p):
                continue
            try:
                if permanent:
                    Path(p).unlink()
                else:
                    trash_image(p)
                self.image_deleted.emit(p)
            except OSError as error:
                QMessageBox.warning(self, 'Suppression impossible', str(error))
        self.setFolder(self.current_folder)

    def _create_folder(self):
        path = create_folder(self, self.current_folder)
        if path:
            self.folder_created.emit(path)
            self.setFolder(self.current_folder)
            self.select_path(path)

    def _rotate_selected(self, degrees):
        paths = [p for p in self.get_selected_file_paths() if Path(p).is_file() and is_image_file(p)]
        if not paths:
            return
        rotated = []
        errors = []
        for path in paths:
            try:
                rotate_image_file(path, degrees)
                self.thumbnail_manager.cache.invalidate(path)
                rotated.append(path)
            except OSError as error:
                errors.append(f'{Path(path).name} : {error}')
        if rotated:
            self.setFolder(self.current_folder)
            for row in range(self.count()):
                item = self.item(row)
                item.setSelected(item.data(ROLE_PATH) in rotated)
            self.images_rotated.emit(rotated)
        if errors:
            QMessageBox.warning(self, 'Rotation incomplète', '\n'.join(errors))

    def _add_sort_menu(self, menu):
        submenu = menu.addMenu('Trier les miniatures')
        for label, key in [('Nom', 'name'), ('Date de modification', 'date'),
                           ('Date de création', 'created'), ('Taille du fichier', 'size'),
                           ('Type de fichier', 'type')]:
            action = submenu.addAction(label)
            action.setCheckable(True)
            action.setChecked(self.sort_by == key)
            action.triggered.connect(lambda checked=False, key=key: self.sort_requested.emit(key, self.sort_order))
        submenu.addSeparator()
        for label, order in [('Croissant ↑', 'asc'), ('Décroissant ↓', 'desc')]:
            action = submenu.addAction(label)
            action.setCheckable(True)
            action.setChecked(self.sort_order == order)
            action.triggered.connect(lambda checked=False, order=order: self.sort_requested.emit(self.sort_by, order))

    def _show_context_menu(self, pos: QPoint):
        item = self.itemAt(pos)
        if not item:
            menu = QMenu(self)
            self._add_sort_menu(menu)
            menu.addAction('Nouveau dossier…').triggered.connect(self._create_folder)
            paste = menu.addAction('Coller dans le dossier actuel (Ctrl+V)')
            paste.triggered.connect(self.paste_images)
            menu.exec(self.mapToGlobal(pos))
            return

        if not item.isSelected():
            self.setCurrentItem(item)

        file_path = item.data(ROLE_PATH)
        is_folder = item.data(ROLE_IS_FOLDER)
        menu = QMenu(self)
        self._add_sort_menu(menu)
        menu.addAction('Nouveau dossier…').triggered.connect(self._create_folder)
        if not is_folder:
            menu.addAction('Copier (Ctrl+C)').triggered.connect(self.copy_selected)
            destinations = self.favorites_provider() if hasattr(self, 'favorites_provider') else []
            if destinations:
                favorites_menu = menu.addMenu('Copier dans un dossier favori')
                for label, destination in destinations:
                    action = favorites_menu.addAction(label)
                    action.setToolTip(destination)
                    action.triggered.connect(lambda checked=False, destination=destination:
                        self.files_dropped.emit(self.get_selected_file_paths(), destination, True))
            menu.addAction('Couper (Ctrl+X)').triggered.connect(self.cut_selected)
            menu.addAction('Renommer (F2)').triggered.connect(self._rename_selected)
        if is_folder:
            menu.addAction('Coller dans ce dossier (Ctrl+V)').triggered.connect(
                lambda: self.paste_images(file_path))
        else:
            menu.addAction('Coller dans le dossier actuel (Ctrl+V)').triggered.connect(self.paste_images)
        menu.addSeparator()

        if is_folder:
            menu.addAction('Renommer le dossier (F2)').triggered.connect(self._rename_selected)
            menu.addAction('Ajouter aux favoris').triggered.connect(lambda: self.add_favorite_requested.emit(file_path))
            menu.addAction('Ouvrir dans un nouvel onglet').triggered.connect(lambda: self.open_in_new_tab_requested.emit(file_path))
            act_open = menu.addAction("📁 Ouvrir ce dossier")
            act_open.triggered.connect(lambda: self.folder_double_clicked.emit(file_path))
        elif is_video_file(file_path):
            menu.addAction('Ouvrir dans le lecteur vidéo par défaut').triggered.connect(lambda: self._open_video(file_path))
        else:
            act_view = menu.addAction("👁 Ouvrir en plein écran (Double-clic / Espace)")
            act_view.triggered.connect(lambda: self.image_double_clicked.emit(file_path))

        # Format conversion submenu for image(s)
        selected_files = self.get_selected_file_paths()
        selected_images = [p for p in selected_files if is_image_file(p)]
        if file_path and not is_folder and is_image_file(file_path) and file_path not in selected_images:
            selected_images = [file_path]

        if selected_images and not is_video_file(file_path):
            menu.addSeparator()
            rotate_menu = menu.addMenu(f"Faire pivoter ({len(selected_images)})")
            rotate_menu.addAction('↺ 90° vers la gauche').triggered.connect(
                lambda: self._rotate_selected(-90))
            rotate_menu.addAction('↻ 90° vers la droite').triggered.connect(
                lambda: self._rotate_selected(90))
            count_suffix = f" ({len(selected_images)})" if len(selected_images) > 1 else ""
            conv_menu = menu.addMenu(f"🔄 Convertir{count_suffix}...")

            formats = [
                ("JPEG (.jpg)", ".jpg"),
                ("PNG (.png)", ".png"),
                ("WebP (.webp)", ".webp"),
                ("BMP (.bmp)", ".bmp"),
            ]

            for fmt_name, fmt_ext in formats:
                sub = conv_menu.addMenu(f"📄 En {fmt_name}")

                act_keep = sub.addAction(f"➕ Conserver les deux formats (créer copie {fmt_ext})")
                act_keep.triggered.connect(
                    lambda checked=False, ext=fmt_ext, imgs=selected_images: self._convert_images(
                        imgs, ext, overwrite=False
                    )
                )

                act_replace = sub.addAction("Convertir et supprimer le format initial")
                act_replace.triggered.connect(
                    lambda checked=False, ext=fmt_ext, imgs=selected_images: self._convert_images(
                        imgs, ext, overwrite=True
                    )
                )

        menu.addSeparator()

        act_copy_path = menu.addAction("📋 Copier le chemin d'accès")
        act_copy_path.triggered.connect(lambda: QApplication.clipboard().setText(file_path))

        act_explorer = menu.addAction("Afficher dans l'explorateur Windows")
        act_explorer.triggered.connect(lambda: reveal_in_explorer(file_path))

        menu.addSeparator()

        act_del = menu.addAction("🗑 Supprimer")
        act_del.triggered.connect(self._delete_selected)

        menu.exec(self.mapToGlobal(pos))

    def _convert_images(self, file_paths: list[str], target_ext: str, overwrite: bool):
        """Converts selected images to the target format with overwrite or keep-both options."""
        converted_count = 0
        changes = []
        errors = []

        for p in file_paths:
            try:
                destination = convert_image_format(p, target_ext, overwrite=overwrite)
                changes.append((p, str(destination), overwrite))
                converted_count += 1
            except Exception as e:
                errors.append(f"{Path(p).name} : {e}")

        # Refresh folder view to show new thumbnails
        self.setFolder(self.current_folder)
        if changes:
            self.images_converted.emit(changes)
            selected = {new for old, new, replaced in changes}
            for i in range(self.count()):
                self.item(i).setSelected(self.item(i).data(ROLE_PATH) in selected)
            if self.selectedItems():
                first = self.selectedItems()[0]
                self.setCurrentItem(first, QItemSelectionModel.SelectionFlag.NoUpdate)
                self.scrollToItem(first)

        if errors:
            QMessageBox.warning(
                self,
                "Conversion terminée avec erreurs",
                f"{converted_count} image(s) convertie(s).\nErreurs rencontrées :\n" + "\n".join(errors[:5]),
            )
