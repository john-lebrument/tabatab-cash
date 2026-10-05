import os
from pathlib import Path
from PyQt6.QtCore import QPoint, QSize, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QIcon,
    QKeySequence,
    QPainter,
    QPen,
    QShortcut,
)
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QMenu,
    QPushButton,
    QStatusBar,
    QTabBar,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.config import ConfigManager
from src.ui.browser_tab import BrowserTabWidget
from src.ui.styles import get_theme_stylesheet
from src.utils.file_ops import is_image_file, is_media_file, move_file, copy_file
from src.utils.image_loader import ThumbnailManager
from src.ui.drag_feedback import drop_action
from src.version import APP_TITLE
from src.utils.windows_integration import configure_default_viewer


class DragDropTabBar(QTabBar):
    """
    Custom QTabBar supporting:
    - Direct '+' button positioned right next to the last tab (Windows 11 Explorer style).
    - Double click on empty tab bar area opens a new tab.
    - Drag & drop of image files directly onto tab headers to move/copy.
    - Clear visual highlight over target tab during drag without crashing the active drag source.
    - Tab reordering.
    """

    files_dropped_on_tab = pyqtSignal(int, list, bool)  # tab_index, file_paths, is_copy
    new_tab_requested = pyqtSignal()
    close_all_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setChangeCurrentOnDrag(False)
        self.setMovable(True)
        self.setTabsClosable(True)
        self.setElideMode(Qt.TextElideMode.ElideMiddle)
        self.setExpanding(False)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)
        self.drag_target_tab: int = -1

        # '+' New Tab button directly on the tab bar
        self.btn_plus = QToolButton(self)
        self.btn_plus.setText("+")
        self.btn_plus.setToolTip("Ouvrir un nouvel onglet (Ctrl + T)")
        self.btn_plus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_plus.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                font-size: 18px;
                font-weight: bold;
                color: #888888;
                padding-bottom: 2px;
            }
            QToolButton:hover {
                background-color: rgba(0, 120, 212, 0.2);
                border: 1px solid #0078d4;
                color: #0078d4;
            }
            QToolButton:pressed {
                background-color: #0078d4;
                color: #ffffff;
            }
        """)
        self.btn_plus.clicked.connect(self.new_tab_requested.emit)

    def _context_menu(self, pos):
        if self.tabAt(pos) >= 0:
            menu = QMenu(self)
            menu.addAction('Fermer tous les onglets').triggered.connect(self.close_all_requested)
            menu.exec(self.mapToGlobal(pos))

    def sizeHint(self):
        size = super().sizeHint()
        return QSize(size.width() + 44, max(size.height(), 30))

    def tabLayoutChange(self):
        super().tabLayoutChange()
        self._position_plus_button()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_plus_button()

    def tabInserted(self, index: int):
        super().tabInserted(index)
        self._position_plus_button()

    def tabRemoved(self, index: int):
        super().tabRemoved(index)
        self._position_plus_button()

    def paintEvent(self, event):
        super().paintEvent(event)

        # Visual highlight when dragging over a tab header
        if 0 <= self.drag_target_tab < self.count():
            rect = self.tabRect(self.drag_target_tab)
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(QPen(QColor(0, 120, 212), 2))
            painter.setBrush(QBrush(QColor(0, 120, 212, 50)))
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 6, 6)
            painter.end()

    def _position_plus_button(self):
        if not hasattr(self, "btn_plus"):
            return
        if self.count() == 0:
            self.btn_plus.hide()
            return

        last_rect = self.tabRect(self.count() - 1)
        btn_w = 30
        btn_h = 26
        x = last_rect.right() + 8
        y = last_rect.top() + (last_rect.height() - btn_h) // 2

        self.btn_plus.setGeometry(x, y, btn_w, btn_h)
        fits = x + btn_w <= self.width()
        self.btn_plus.setVisible(fits)
        # In an overflowing strip, keep one accessible '+' in the corner.
        window = self.window()
        if hasattr(window, "btn_new_tab"):
            window.btn_new_tab.setVisible(not fits)
        self.btn_plus.raise_()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
            if self.tabAt(pos) == -1:
                self.new_tab_requested.emit()
                return
        super().mouseDoubleClickEvent(event)

    def dragEnterEvent(self, event):
        try:
            if event.mimeData().hasUrls():
                event.setDropAction(drop_action(event))
                event.accept()
            else:
                super().dragEnterEvent(event)
        except Exception as e:
            print(f"Error in DragDropTabBar.dragEnterEvent: {e}")

    def dragMoveEvent(self, event):
        try:
            if event.mimeData().hasUrls():
                pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
                tab_index = self.tabAt(pos)
                if tab_index != self.drag_target_tab:
                    self.drag_target_tab = tab_index
                    self.update()
                event.setDropAction(drop_action(event))
                event.accept()
            else:
                super().dragMoveEvent(event)
        except Exception as e:
            print(f"Error in DragDropTabBar.dragMoveEvent: {e}")

    def dragLeaveEvent(self, event):
        try:
            self.drag_target_tab = -1
            self.update()
            super().dragLeaveEvent(event)
        except Exception as e:
            print(f"Error in DragDropTabBar.dragLeaveEvent: {e}")

    def dropEvent(self, event):
        try:
            self.drag_target_tab = -1
            self.update()

            if not event.mimeData().hasUrls():
                super().dropEvent(event)
                return

            pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
            tab_index = self.tabAt(pos)
            if tab_index < 0:
                tab_index = self.currentIndex()

            urls = event.mimeData().urls()
            file_paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
            file_paths = [p for p in file_paths if p and (is_media_file(p) or Path(p).is_dir())]

            if file_paths:
                is_copy = drop_action(event) == Qt.DropAction.CopyAction
                self.files_dropped_on_tab.emit(tab_index, file_paths, is_copy)
                event.setDropAction(Qt.DropAction.CopyAction if is_copy else Qt.DropAction.MoveAction)
                event.accept()
            else:
                super().dropEvent(event)
        except Exception as e:
            print(f"Error in DragDropTabBar.dropEvent: {e}")


class MainWindow(QMainWindow):
    """
    Main application window featuring Windows 11 style tabs,
    theme switcher (Light/Dark persisted), drag-and-drop file organization,
    and integrated fullscreen viewer.
    """

    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config = config_manager
        self._restoring_tabs = True
        self.fullscreen_viewer = None
        self.floating_viewers = set()
        self.thumbnail_manager = ThumbnailManager()

        self.setWindowTitle(APP_TITLE)
        self.resize(
            self.config.get("window_width", 1280),
            self.config.get("window_height", 820),
        )

        # Apply saved theme (Light or Dark)
        self.current_theme = self.config.get("theme", "dark")
        self.setStyleSheet(get_theme_stylesheet(self.current_theme))

        self._init_ui()
        self._init_shortcuts()
        # Paint the window before restoring folders and initializing their views.
        QTimer.singleShot(0, self._load_saved_tabs)

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Tab Widget with Custom TabBar
        self.tab_widget = QTabWidget(self)
        self.custom_tab_bar = DragDropTabBar(self.tab_widget)
        self.custom_tab_bar.files_dropped_on_tab.connect(self._on_files_dropped_on_tab)
        self.custom_tab_bar.new_tab_requested.connect(self.add_new_tab)
        self.custom_tab_bar.close_all_requested.connect(self.close_all_tabs)
        self.tab_widget.setTabBar(self.custom_tab_bar)
        # QTabWidget resets expanding when installing a custom bar.
        self.custom_tab_bar.setExpanding(False)

        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        # Top Right Corner: Theme Toggle Button + "+" New Tab Button
        corner_widget = QWidget(self)
        corner_layout = QHBoxLayout(corner_widget)
        corner_layout.setContentsMargins(0, 0, 6, 0)
        corner_layout.setSpacing(6)
        self.btn_defaults = QPushButton('Associer toutes les images…', corner_widget)
        self.btn_defaults.setToolTip('Enregistrer tous les formats pris en charge puis ouvrir directement la page TABaTAB Cash de Windows')
        self.btn_defaults.clicked.connect(lambda: configure_default_viewer(self))
        corner_layout.addWidget(self.btn_defaults)

        # Theme Toggle
        self.btn_theme = QPushButton(self._get_theme_btn_text(), corner_widget)
        self.btn_theme.setToolTip("Basculer entre Mode Sombre et Mode Clair")
        self.btn_theme.clicked.connect(self.toggle_theme)
        corner_layout.addWidget(self.btn_theme)

        # "+" New Tab button
        self.btn_new_tab = QPushButton("+", corner_widget)
        self.btn_new_tab.setToolTip("Nouvel onglet (Ctrl + T)")
        self.btn_new_tab.setFixedSize(28, 28)
        self.btn_new_tab.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                font-weight: bold;
                border-radius: 14px;
                padding: 0;
            }
        """)
        self.btn_new_tab.clicked.connect(self.add_new_tab)
        corner_layout.addWidget(self.btn_new_tab)
        self.btn_new_tab.hide()

        self.tab_widget.setCornerWidget(corner_widget, Qt.Corner.TopRightCorner)
        main_layout.addWidget(self.tab_widget)

        # Status Bar
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Prêt")

    def _get_theme_btn_text(self) -> str:
        return "☀️ Mode Clair" if self.current_theme == "dark" else "🌙 Mode Sombre"

    def toggle_theme(self):
        """Toggles between dark and light themes and persists choice."""
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self.setStyleSheet(get_theme_stylesheet(self.current_theme))
        self.btn_theme.setText(self._get_theme_btn_text())
        self.config.set("theme", self.current_theme)

    def _init_shortcuts(self):
        # Ctrl+T: New Tab
        sc_new_tab = QShortcut(QKeySequence("Ctrl+T"), self)
        sc_new_tab.activated.connect(self.add_new_tab)

        # Ctrl+W: Close Current Tab
        sc_close_tab = QShortcut(QKeySequence("Ctrl+W"), self)
        sc_close_tab.activated.connect(lambda: self.close_tab(self.tab_widget.currentIndex()))

        # Ctrl+Tab: Switch Tab
        sc_next_tab = QShortcut(QKeySequence("Ctrl+Tab"), self)
        sc_next_tab.activated.connect(self._next_tab)

        # F5: Refresh
        sc_refresh = QShortcut(QKeySequence("F5"), self)
        sc_refresh.activated.connect(self.refresh_current_tab)

    def _load_saved_tabs(self):
        saved_folders = self.config.get("tabs", [])
        pictures = str(Path.home() / "Pictures")
        
        # If no saved tabs, start in Pictures
        if not saved_folders:
            saved_folders = [pictures if Path(pictures).exists() else str(Path.home())]

        for folder in saved_folders:
            if Path(folder).exists():
                self.add_tab(folder, switch_to=False)

        if self.tab_widget.count() == 0:
            self.add_tab(pictures if Path(pictures).exists() else str(Path.home()))

        active_idx = min(self.config.get("active_tab", 0), self.tab_widget.count() - 1)
        self.tab_widget.setCurrentIndex(max(0, active_idx))
        self._restoring_tabs = False
        self._save_tab_state()

    def add_tab(self, folder_path: str, switch_to: bool = True) -> BrowserTabWidget:
        saved_size = self.config.get("thumbnail_size", 150)
        tab = BrowserTabWidget(
            folder_path,
            self.thumbnail_manager,
            initial_thumb_size=saved_size,
            config_manager=self.config,
            parent=self,
        )
        folder_name = Path(folder_path).name or folder_path
        idx = self.tab_widget.addTab(tab, folder_name)
        self.tab_widget.setTabToolTip(idx, folder_path)

        # Connect signals
        tab.folder_changed.connect(lambda p, i=idx: self._on_tab_folder_changed(tab, p))
        tab.request_fullscreen.connect(self._on_request_fullscreen)
        tab.request_floating.connect(self._on_request_floating)
        tab.files_dropped.connect(self._on_tab_files_dropped)
        tab.thumb_view.selection_changed_info.connect(self._on_selection_info)
        tab.thumb_view.image_deleted.connect(self._on_image_deleted)
        tab.thumb_view.image_restored.connect(self._on_image_restored)
        tab.thumb_view.images_renamed.connect(self._on_images_renamed)
        tab.thumb_view.folder_renamed.connect(self._on_folder_relocated)
        tab.folder_renamed.connect(self._on_folder_relocated)
        tab.folder_created.connect(self._on_folder_created)
        tab.folder_deleted.connect(self._on_folder_deleted)
        tab.thumb_view.images_converted.connect(self._on_images_converted)
        tab.thumb_view.images_rotated.connect(self._on_images_rotated)
        tab.thumbnail_size_saved.connect(self._on_thumbnail_size_saved)
        tab.open_in_new_tab_requested.connect(lambda p: self.add_tab(p, switch_to=True))
        tab.favorites_updated.connect(self._on_favorites_updated)

        if switch_to:
            self.tab_widget.setCurrentIndex(idx)

        self._save_tab_state()
        return tab

    def _on_favorites_updated(self):
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if isinstance(tab, BrowserTabWidget):
                tab._populate_favorites()

    def _on_thumbnail_size_saved(self, size: int):
        self.config.set("thumbnail_size", size)

    def add_new_tab(self):
        current_tab = self.get_current_tab_widget()
        folder = current_tab.current_folder if current_tab else str(Path.home() / "Pictures")
        self.add_tab(folder, switch_to=True)

    def close_all_tabs(self):
        while self.tab_widget.count():
            widget = self.tab_widget.widget(0)
            self.tab_widget.removeTab(0)
            widget.deleteLater()
        self.btn_new_tab.show()
        self._save_tab_state()

    def close_tab(self, index: int):
        if self.tab_widget.count() <= 1:
            return

        widget = self.tab_widget.widget(index)
        self.tab_widget.removeTab(index)
        if widget:
            widget.deleteLater()

        self._save_tab_state()

    def _next_tab(self):
        count = self.tab_widget.count()
        if count > 1:
            self.tab_widget.setCurrentIndex((self.tab_widget.currentIndex() + 1) % count)

    def get_current_tab_widget(self) -> BrowserTabWidget | None:
        return self.tab_widget.currentWidget()

    def refresh_current_tab(self):
        current = self.get_current_tab_widget()
        if current:
            current.refresh()

    def _on_tab_folder_changed(self, tab: BrowserTabWidget, new_path: str):
        idx = self.tab_widget.indexOf(tab)
        if idx >= 0:
            name = Path(new_path).name or new_path
            self.tab_widget.setTabText(idx, name)
            self.tab_widget.setTabToolTip(idx, new_path)
            self._save_tab_state()

    def _on_tab_changed(self, index: int):
        self._save_tab_state()
        current = self.get_current_tab_widget()
        if current:
            total = len(current.thumb_view.all_files)
            self.status_bar.showMessage(f"{current.current_folder} — {total} image(s)")

    def _on_selection_info(self, selected_count: int, total_count: int):
        current = self.get_current_tab_widget()
        if current:
            if selected_count > 0:
                self.status_bar.showMessage(
                    f"{current.current_folder} — {selected_count} sélectionnée(s) sur {total_count} image(s)"
                )
            else:
                self.status_bar.showMessage(f"{current.current_folder} — {total_count} image(s)")

    def _on_request_fullscreen(self, all_images: list, current_image: str):
        self._fullscreen_origin = self.get_current_tab_widget()
        if self.fullscreen_viewer is None:
            from src.ui.fullscreen_viewer import FullscreenImageViewer
            self.fullscreen_viewer = FullscreenImageViewer()
            self.fullscreen_viewer.image_modified.connect(self._on_image_modified)
            self.fullscreen_viewer.images_renamed.connect(self._on_images_renamed)
            self.fullscreen_viewer.image_deleted.connect(self._on_image_deleted)
            self.fullscreen_viewer.floating_requested.connect(self._on_request_floating)
            self.fullscreen_viewer.image_restored.connect(self._on_image_restored)
            self.fullscreen_viewer.viewer_closed.connect(self._on_viewer_closed)
        self.fullscreen_viewer.show_images(all_images, current_image, screen=self.screen())

    def open_external_image(self, path):
        path = Path(path).resolve()
        if not path.is_file() or not is_image_file(path):
            QMessageBox.warning(self, 'Ouverture impossible', f'Image introuvable ou format non pris en charge :\n{path}')
            return
        tab = next((self.tab_widget.widget(i) for i in range(self.tab_widget.count())
                    if Path(self.tab_widget.widget(i).current_folder) == path.parent), None)
        if tab is None:
            tab = self.add_tab(str(path.parent))
        else:
            self.tab_widget.setCurrentWidget(tab)
            tab.refresh()
        tab.thumb_view.select_path(str(path))
        self._on_request_fullscreen(tab.thumb_view.all_files, str(path))

    def _on_request_floating(self, all_images, current_image):
        from src.ui.fullscreen_viewer import FullscreenImageViewer
        viewer = FullscreenImageViewer(self, floating=True)
        self.floating_viewers.add(viewer)
        viewer.destroyed.connect(lambda: self.floating_viewers.discard(viewer))
        viewer.image_modified.connect(self._on_image_modified)
        viewer.images_renamed.connect(self._on_images_renamed)
        viewer.image_deleted.connect(self._on_image_deleted)
        viewer.image_restored.connect(self._on_image_restored)
        viewer.floating_requested.connect(self._on_request_floating)
        viewer.show_images(all_images, current_image)
        viewer.raise_()
        viewer.activateWindow()

    def _on_viewer_closed(self, path):
        tab = getattr(self, '_fullscreen_origin', None)
        if tab is not None and self.tab_widget.indexOf(tab) >= 0 and path:
            self.tab_widget.setCurrentWidget(tab)
            if Path(tab.current_folder) != Path(path).parent:
                tab.navigate_to(str(Path(path).parent))
            tab.thumb_view.select_path(path)
            tab.thumb_view.setFocus()

    def _on_folder_created(self, path):
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if Path(tab.current_folder) == Path(path).parent:
                tab.refresh()
        self.status_bar.showMessage(f'Dossier créé : {Path(path).name}', 3000)

    def _on_folder_deleted(self, path):
        removed = Path(path)
        def inside(value):
            candidate = Path(value)
            return candidate == removed or removed in candidate.parents
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            tab.history_back = [p for p in tab.history_back if not inside(p)]
            tab.history_forward = [p for p in tab.history_forward if not inside(p)]
            if inside(tab.current_folder):
                fallback = removed.parent
                while not fallback.is_dir() and fallback != fallback.parent:
                    fallback = fallback.parent
                tab.navigate_to(str(fallback), add_history=False)
            else:
                tab.refresh()
        for viewer in [self.fullscreen_viewer, *self.floating_viewers]:
            if viewer:
                for image in list(viewer.image_list):
                    if inside(image):
                        viewer.remove_image(image)
        self._on_favorites_updated()
        self.status_bar.showMessage(f'Dossier mis à la corbeille : {removed.name}', 3000)

    def _on_folder_relocated(self, old, new):
        old_path, new_path = Path(old), Path(new)
        def remap(path):
            try:
                return str(new_path / Path(path).relative_to(old_path))
            except ValueError:
                return path
        for key in ('custom_favorites', 'hidden_favorites'):
            self.config.set(key, [remap(p) for p in self.config.get(key, [])])
        self.config.set('favorite_order', [[remap(p), custom] for p, custom in self.config.get('favorite_order', [])])
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            tab.history_back = [remap(p) for p in tab.history_back]
            tab.history_forward = [remap(p) for p in tab.history_forward]
            destination = remap(tab.current_folder)
            if destination != tab.current_folder:
                tab.navigate_to(destination, add_history=False)
            else:
                tab.refresh()
        for viewer in [self.fullscreen_viewer, *self.floating_viewers]:
            if viewer:
                viewer.image_list = [remap(p) for p in viewer.image_list]
                if viewer.isVisible():
                    viewer.load_current_image()
        self._on_favorites_updated()
        self._save_tab_state()
        self.status_bar.showMessage(f'Dossier : {new_path.name}', 3000)

    def _on_images_renamed(self, changes):
        self._refresh_changed_paths([(old, new, True) for old, new in changes])
        self.status_bar.showMessage(f'{len(changes)} image(s) renommée(s)', 3000)

    def _on_images_converted(self, changes):
        self._refresh_changed_paths(changes)
        self.status_bar.showMessage(f'{len(changes)} image(s) convertie(s)', 3000)

    def _on_images_rotated(self, paths):
        selected = set(paths)
        for path in paths:
            self.thumbnail_manager.cache.invalidate(path)
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if isinstance(tab, BrowserTabWidget) and any(Path(path).parent == Path(tab.current_folder) for path in paths):
                tab.refresh()
                for row in range(tab.thumb_view.count()):
                    item = tab.thumb_view.item(row)
                    item.setSelected(item.data(Qt.ItemDataRole.UserRole) in selected)
        self.status_bar.showMessage(f'{len(paths)} image(s) tournée(s)', 3000)

    def _refresh_changed_paths(self, changes):
        folders = {Path(p).parent for old, new, replaced in changes for p in (old, new)}
        mapping = {Path(old): new for old, new, replaced in changes if replaced}
        for old, new, replaced in changes:
            self.thumbnail_manager.cache.invalidate(old)
            self.thumbnail_manager.cache.invalidate(new)
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if Path(tab.current_folder) in folders:
                tab.refresh()
        for viewer in [self.fullscreen_viewer, *self.floating_viewers]:
            if viewer and any(Path(p) in mapping for p in viewer.image_list):
                viewer.image_list = [mapping.get(Path(p), p) for p in viewer.image_list]
                viewer.load_current_image()

    def _on_image_restored(self, path):
        self.thumbnail_manager.cache.invalidate(path)
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if Path(tab.current_folder) == Path(path).parent:
                tab.refresh()
                tab.thumb_view.select_path(path)
        self.status_bar.showMessage(f'Image restaurée : {Path(path).name}', 3000)

    def _on_image_deleted(self, path):
        self.thumbnail_manager.cache.invalidate(path)
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if isinstance(tab, BrowserTabWidget) and Path(tab.current_folder) == Path(path).parent:
                tab.refresh()
        for viewer in [self.fullscreen_viewer, *list(self.floating_viewers)]:
            if viewer is not None:
                viewer.remove_image(path)
        self.status_bar.showMessage(f'Image supprimée : {Path(path).name}', 1000)

    def _on_image_modified(self, modified_path: str):
        self.thumbnail_manager.cache.invalidate(modified_path)
        current = self.get_current_tab_widget()
        if current:
            current.refresh()
        self.status_bar.showMessage(f"Image enregistrée : {Path(modified_path).name}", 5000)

    # File Operations between Tabs / Folders
    def _on_files_dropped_on_tab(self, tab_index: int, file_paths: list[str], is_copy: bool):
        target_tab = self.tab_widget.widget(tab_index)
        if not isinstance(target_tab, BrowserTabWidget):
            return

        target_folder = target_tab.current_folder
        self._execute_file_transfer(file_paths, target_folder, is_copy)

    def _on_tab_files_dropped(self, source_files: list[str], target_folder: str, is_copy: bool):
        self._execute_file_transfer(source_files, target_folder, is_copy)

    def _execute_file_transfer(self, file_paths: list[str], target_folder: str, is_copy: bool):
        target_path = Path(target_folder)
        if not target_path.exists():
            return

        action_name = "copiée(s)" if is_copy else "déplacée(s)"
        count = 0
        destinations = []

        for src in file_paths:
            src_p = Path(src)
            # Only ignore if MOVING within the same folder; copying within same folder is allowed
            if not is_copy and src_p.parent.resolve() == target_path.resolve():
                continue
            try:
                is_folder = src_p.is_dir()
                if is_copy:
                    destination = copy_file(src_p, target_path)
                else:
                    destination = move_file(src_p, target_path)
                    if is_folder:
                        self._on_folder_relocated(str(src_p), str(destination))
                count += 1
                destinations.append(str(destination))
            except Exception as e:
                QMessageBox.warning(
                    self, "Erreur de transfert", f"Impossible de traiter {src_p.name} :\n{e}"
                )

        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if isinstance(tab, BrowserTabWidget):
                tab.refresh()
                if Path(tab.current_folder) == target_path:
                    for row in range(tab.thumb_view.count()):
                        item = tab.thumb_view.item(row)
                        item.setSelected(item.data(Qt.ItemDataRole.UserRole) in destinations)

        self.status_bar.showMessage(f"{count} élément(s) {action_name} vers « {target_path.name} »", 5000)

    def _save_tab_state(self):
        if self._restoring_tabs:
            return
        folders = []
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if isinstance(tab, BrowserTabWidget):
                folders.append(tab.current_folder)

        self.config.set("tabs", folders)
        self.config.set("active_tab", self.tab_widget.currentIndex())

    def closeEvent(self, event):
        self.config.set("window_width", self.width())
        self.config.set("window_height", self.height())
        self._save_tab_state()
        if self.fullscreen_viewer is not None:
            self.fullscreen_viewer.close()
        for viewer in list(self.floating_viewers):
            viewer.close()
        super().closeEvent(event)
