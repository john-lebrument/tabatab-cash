import os
import string
from pathlib import Path
from PyQt6.QtCore import QDir, QModelIndex, QSize, Qt, pyqtSignal, QMimeData, QUrl, QTimer
from PyQt6.QtGui import QFileSystemModel, QIcon, QFont, QDrag, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QInputDialog,
    QMessageBox,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QSlider,
    QSplitter,
    QTreeView,
    QVBoxLayout,
    QWidget,
    QAbstractItemView,
)

from src.ui.thumbnail_view import ThumbnailView
from src.utils.image_loader import ThumbnailManager
from src.ui.drag_feedback import drop_action, paint_destination, set_large_drag_cursors
from src.ui.breadcrumb_bar import BreadcrumbBar
from src.ui.folder_actions import create_folder, delete_folders
from src.utils.file_ops import rename_folder
from src.utils.favorites import export_favorites, import_favorites


class FavoritesList(QListWidget):
    order_changed = pyqtSignal()
    paste_requested = pyqtSignal(str)

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.Paste):
            item = self.currentItem()
            if item:
                self.paste_requested.emit(item.data(ROLE_PATH))
            event.accept()
            return
        super().keyPressEvent(event)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragDropOverwriteMode(False)

    def dropEvent(self, event):
        if event.source() is not self:
            event.ignore()
            return
        super().dropEvent(event)
        if event.isAccepted():
            QTimer.singleShot(0, self.order_changed.emit)


class FolderTree(QTreeView):
    files_dropped = pyqtSignal(list, str, bool)
    delete_requested = pyqtSignal(str)
    rename_requested = pyqtSignal(str)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F2:
            if not event.isAutoRepeat() and self.currentIndex().isValid():
                self.rename_requested.emit(self.model().filePath(self.currentIndex()))
            event.accept()
            return
        if event.key() == Qt.Key.Key_Delete:
            if not event.isAutoRepeat() and self.currentIndex().isValid():
                self.delete_requested.emit(self.model().filePath(self.currentIndex()))
            event.accept()
            return
        super().keyPressEvent(event)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self._drop_index = QModelIndex()
        self.setAutoScroll(False)
        self._drag_position = None
        self._expand_timer = QTimer(self)
        self._expand_timer.setSingleShot(True)
        self._expand_timer.setInterval(700)
        self._expand_timer.timeout.connect(self._expand_hovered_folder)
        self._scroll_timer = QTimer(self)
        self._scroll_timer.setInterval(60)
        self._scroll_timer.timeout.connect(self._scroll_drag)

    def _track_drag(self, position):
        self._drag_position = position
        index = self.indexAt(position)
        if index != self._drop_index:
            self._expand_timer.stop()
            self._drop_index = index
            if index.isValid() and not self.isExpanded(index):
                self._expand_timer.start()
        self.viewport().update()
        if position.y() < 32 or position.y() >= self.viewport().height() - 32:
            if not self._scroll_timer.isActive():
                self._scroll_timer.start()
        else:
            self._scroll_timer.stop()

    def _expand_hovered_folder(self):
        if self._drag_position is not None and self._drop_index.isValid():
            if self.indexAt(self._drag_position) == self._drop_index:
                self.expand(self._drop_index)

    def _scroll_drag(self):
        if self._drag_position is None:
            self._scroll_timer.stop()
            return
        y = self._drag_position.y()
        direction = -1 if y < 32 else (1 if y >= self.viewport().height() - 32 else 0)
        bar = self.verticalScrollBar()
        bar.setValue(bar.value() + direction * max(1, bar.singleStep()))
        self._track_drag(self._drag_position)

    def _stop_drag(self):
        self._expand_timer.stop()
        self._scroll_timer.stop()
        self._drag_position = None
        self._drop_index = QModelIndex()
        self.viewport().update()

    def startDrag(self, supported_actions):
        index = self.currentIndex()
        if not index.isValid():
            return
        path = self.model().filePath(index)
        if Path(path) == Path(Path(path).anchor):
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(path)])
        drag.setMimeData(mime)
        set_large_drag_cursors(drag)
        drag.setPixmap(self.model().fileIcon(index).pixmap(64, 64))
        drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction, Qt.DropAction.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(drop_action(event))
            event.accept()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            self._track_drag(event.position().toPoint())
            event.setDropAction(drop_action(event))
            event.accept()
        else:
            self._stop_drag()
            event.ignore()

    def dragLeaveEvent(self, event):
        self._stop_drag()
        super().dragLeaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._drop_index.isValid():
            rect = self.visualRect(self._drop_index)
            rect.setLeft(0)
            rect.setRight(self.viewport().width() - 1)
            paint_destination(self.viewport(), rect)

    def dropEvent(self, event):
        self._stop_drag()
        index = self.indexAt(event.position().toPoint())
        if index.isValid() and event.mimeData().hasUrls():
            from src.utils.file_ops import is_media_file
            paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
            paths = [p for p in paths if Path(p).is_dir() or (Path(p).is_file() and is_media_file(p))]
            copy = drop_action(event) == Qt.DropAction.CopyAction
            self.files_dropped.emit(paths, self.model().filePath(index), copy)
            event.setDropAction(Qt.DropAction.CopyAction if copy else Qt.DropAction.MoveAction)
            event.accept()

ROLE_PATH = Qt.ItemDataRole.UserRole
ROLE_IS_CUSTOM_FAV = Qt.ItemDataRole.UserRole + 1


class BrowserTabWidget(QWidget):
    """
    Independent browser tab representing a folder view with customizable Favorites,
    French Quick Access shortcuts, address bar, folder tree, and thumbnail grid.
    """

    folder_changed = pyqtSignal(str)
    request_fullscreen = pyqtSignal(list, str)  # all_images, clicked_image
    request_floating = pyqtSignal(list, str)
    files_dropped = pyqtSignal(list, str, bool)
    thumbnail_size_saved = pyqtSignal(int)
    open_in_new_tab_requested = pyqtSignal(str)
    favorites_updated = pyqtSignal()
    folder_created = pyqtSignal(str)
    folder_deleted = pyqtSignal(str)
    folder_renamed = pyqtSignal(str, str)

    def __init__(
        self,
        initial_folder: str,
        thumbnail_manager: ThumbnailManager,
        initial_thumb_size: int = 150,
        config_manager=None,
        parent=None,
    ):
        super().__init__(parent)
        self.thumbnail_manager = thumbnail_manager
        self.config = config_manager or (parent.config if hasattr(parent, "config") else None)
        self.current_folder: str = str(Path(initial_folder).resolve())
        self.current_thumb_size: int = initial_thumb_size
        self.history_back: list[str] = []
        self.history_forward: list[str] = []
        self.is_navigating_history: bool = False

        self._init_ui()
        self.navigate_to(self.current_folder, add_history=False)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # 1. Navigation & Address Bar
        nav_bar = QHBoxLayout()
        nav_bar.setSpacing(6)

        self.btn_back = QPushButton("◀", self)
        self.btn_back.setToolTip("Précédent (Alt + Gauche)")
        self.btn_back.setFixedWidth(32)
        self.btn_back.clicked.connect(self.go_back)
        nav_bar.addWidget(self.btn_back)

        self.btn_forward = QPushButton("▶", self)
        self.btn_forward.setToolTip("Suivant (Alt + Droite)")
        self.btn_forward.setFixedWidth(32)
        self.btn_forward.clicked.connect(self.go_forward)
        nav_bar.addWidget(self.btn_forward)

        self.btn_up = QPushButton("▲", self)
        self.btn_up.setToolTip("Dossier parent (Alt + Haut)")
        self.btn_up.setFixedWidth(32)
        self.btn_up.clicked.connect(self.go_up)
        nav_bar.addWidget(self.btn_up)

        self.breadcrumb = BreadcrumbBar(self)
        self.breadcrumb.navigate_requested.connect(self.navigate_to)
        self.path_edit = self.breadcrumb.edit
        self.path_edit.setPlaceholderText("Entrez le chemin d'un dossier...")
        self.path_edit.returnPressed.connect(self._on_path_entered)
        nav_bar.addWidget(self.breadcrumb, 1)

        # Star Favorite button inside toolbar
        self.btn_fav_star = QPushButton("☆", self)
        self.btn_fav_star.setToolTip("Ajouter/Retirer ce dossier des favoris")
        self.btn_fav_star.setFixedWidth(32)
        self.btn_fav_star.clicked.connect(self.toggle_current_favorite)
        nav_bar.addWidget(self.btn_fav_star)

        self.btn_browse = QPushButton("📁 Parcourir...", self)
        self.btn_browse.clicked.connect(self.browse_folder)
        nav_bar.addWidget(self.btn_browse)

        self.btn_refresh = QPushButton("🔄", self)
        self.btn_refresh.setToolTip("Actualiser (F5)")
        self.btn_refresh.setFixedWidth(32)
        self.btn_refresh.clicked.connect(self.refresh)
        nav_bar.addWidget(self.btn_refresh)

        # 2. Thumbnail Size Controls (Presets up to 600px + Slider + Label)
        nav_bar.addSpacing(8)
        lbl_size = QLabel("Taille :", self)
        nav_bar.addWidget(lbl_size)

        self.combo_presets = QComboBox(self)
        self.combo_presets.addItems([
            "Petites (90px)",
            "Moyennes (160px)",
            "Grandes (260px)",
            "Très grandes (380px)",
            "Géantes (500px)",
            "Maximales (600px)",
        ])
        self.combo_presets.currentIndexChanged.connect(self._on_preset_changed)
        nav_bar.addWidget(self.combo_presets)

        self.slider_size = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_size.setRange(64, 600)
        self.slider_size.setValue(self.current_thumb_size)
        self.slider_size.setFixedWidth(110)
        self.slider_size.valueChanged.connect(self._on_slider_changed)
        nav_bar.addWidget(self.slider_size)

        self.lbl_size_val = QLabel(f"{self.current_thumb_size}px", self)
        self.lbl_size_val.setFixedWidth(46)
        nav_bar.addWidget(self.lbl_size_val)

        main_layout.addLayout(nav_bar)

        sort_bar = QHBoxLayout()
        sort_bar.addWidget(QLabel('Trier par :', self))
        self.combo_sort = QComboBox(self)
        for label, key in [('Nom', 'name'), ('Date de modification', 'date'),
                           ('Date de création', 'created'), ('Taille du fichier', 'size'),
                           ('Type de fichier', 'type')]:
            self.combo_sort.addItem(label, key)
        saved_sort = self.config.get('sort_by', 'name') if self.config else 'name'
        self.combo_sort.setCurrentIndex(max(0, self.combo_sort.findData(saved_sort)))
        self.combo_order = QComboBox(self)
        self.combo_order.addItem('Croissant ↑', 'asc')
        self.combo_order.addItem('Décroissant ↓', 'desc')
        saved_order = self.config.get('sort_order', 'asc') if self.config else 'asc'
        self.combo_order.setCurrentIndex(max(0, self.combo_order.findData(saved_order)))
        sort_bar.addWidget(self.combo_sort)
        sort_bar.addWidget(self.combo_order)
        self.btn_videos = QPushButton('Vidéos', self)
        self.btn_videos.setCheckable(True)
        self.btn_videos.setStyleSheet('QPushButton { background: #555; color: white; border: 1px solid #777; padding: 6px 14px; font-weight: bold; } QPushButton:checked { background: #16853b; border: 2px solid #70ef94; color: white; }')
        self.btn_videos.toggled.connect(lambda checked: self.btn_videos.setText('Vidéos : ON' if checked else 'Vidéos : OFF'))
        self.btn_videos.setText('Vidéos : OFF')
        self.btn_videos.setToolTip('Afficher ou masquer les vidéos ; un double-clic ouvre le lecteur vidéo par défaut')
        self.btn_videos.setChecked(bool(self.config.get('show_videos', False)) if self.config else False)
        sort_bar.addWidget(self.btn_videos)
        sort_bar.addStretch()
        hint = QLabel('Ctrl+C : copier  ·  dossier + Ctrl+V : coller dedans  ·  Ctrl+glisser : copier', self)
        hint.setStyleSheet('color: #888888; padding-right: 8px;')
        sort_bar.addWidget(hint)
        main_layout.addLayout(sort_bar)

        # 3. Central Splitter: Left Sidebar (Favorites + Tree) & Right Thumbnail Grid
        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # Left Sidebar container
        left_widget = QWidget(self.splitter)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)

        # Favorites header with "+ Ajouter" button
        fav_header = QHBoxLayout()
        fav_header.setContentsMargins(4, 4, 4, 2)
        lbl_fav = QLabel(" ⭐ FAVORIS", left_widget)
        lbl_fav.setStyleSheet("font-weight: bold; color: #0078d4;")
        btn_add_fav = QPushButton("+ Ajouter", left_widget)
        btn_add_fav.setToolTip("Ajouter le dossier courant aux favoris")
        btn_add_fav.setFixedWidth(70)
        btn_add_fav.setStyleSheet("padding: 2px 6px; font-size: 11px;")
        btn_add_fav.clicked.connect(self.add_current_to_favorites)
        fav_header.addWidget(lbl_fav)
        fav_header.addStretch()
        fav_header.addWidget(btn_add_fav)
        self.btn_favorites_menu = QPushButton('⋯', left_widget)
        self.btn_favorites_menu.setToolTip('Importer ou exporter les favoris')
        self.btn_favorites_menu.setFixedWidth(30)
        favorites_menu = QMenu(self.btn_favorites_menu)
        self._add_favorites_exchange_actions(favorites_menu)
        self.btn_favorites_menu.setMenu(favorites_menu)
        fav_header.addWidget(self.btn_favorites_menu)
        left_layout.addLayout(fav_header)

        # Favorites ListWidget
        self.fav_list = FavoritesList(left_widget)
        self.fav_list.order_changed.connect(self._save_favorite_order)
        self.fav_list.setObjectName("favoritesList")
        self.fav_list.setMaximumHeight(180)
        self.fav_list.setSpacing(1)
        self.fav_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.fav_list.customContextMenuRequested.connect(self._show_fav_context_menu)
        self._populate_favorites()
        self.fav_list.itemClicked.connect(self._on_favorite_clicked)
        left_layout.addWidget(self.fav_list)

        # Folder Tree header
        lbl_tree = QLabel(" 📁 EXPLORATEUR", left_widget)
        lbl_tree.setStyleSheet("font-weight: bold; padding: 4px; color: #888888;")
        left_layout.addWidget(lbl_tree)

        # Folder Tree View
        self.tree_model = QFileSystemModel()
        self.tree_model.setRootPath(QDir.rootPath())
        self.tree_model.setFilter(QDir.Filter.Dirs | QDir.Filter.NoDotAndDotDot | QDir.Filter.Drives)

        self.tree_view = FolderTree(left_widget)
        self.tree_view.files_dropped.connect(self._on_files_dropped)
        self.tree_view.delete_requested.connect(self._delete_tree_folder)
        self.tree_view.rename_requested.connect(self._rename_tree_folder)
        self.tree_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self._show_tree_context_menu)
        self.tree_view.setModel(self.tree_model)
        for col in range(1, 4):
            self.tree_view.hideColumn(col)
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setIndentation(10)
        self.tree_view.setStyleSheet('QTreeView { padding: 0; } QTreeView::item { padding: 4px 1px; }')
        self.tree_view.setAnimated(True)
        self.tree_view.clicked.connect(self._on_tree_clicked)
        left_layout.addWidget(self.tree_view, 1)

        # Right: Thumbnail Grid
        self.thumb_view = ThumbnailView(self.thumbnail_manager, self.splitter)
        self.thumb_view.favorites_provider = self._favorite_destinations
        self.thumb_view.sort_requested.connect(self._set_sort_from_menu)
        self.fav_list.paste_requested.connect(self.thumb_view.paste_images)
        self.thumb_view.show_videos = self.btn_videos.isChecked()
        self.btn_videos.toggled.connect(self._toggle_videos)
        self.thumb_view.setThumbnailSize(self.current_thumb_size)
        self.thumb_view.set_sort(self.combo_sort.currentData(), self.combo_order.currentData())
        self.combo_sort.currentIndexChanged.connect(self._on_sort_changed)
        self.combo_order.currentIndexChanged.connect(self._on_sort_changed)
        self.thumb_view.image_double_clicked.connect(self._on_image_double_clicked)
        self.thumb_view.floating_requested.connect(
            lambda path: self.request_floating.emit(list(self.thumb_view.all_files), path))
        self.thumb_view.folder_double_clicked.connect(self.navigate_to)  # Enter subfolder
        self.thumb_view.open_in_new_tab_requested.connect(self.open_in_new_tab_requested)
        self.thumb_view.add_favorite_requested.connect(self.add_folder_to_favorites)
        self.thumb_view.folder_created.connect(self.folder_created)
        self.thumb_view.folder_deleted.connect(self.folder_deleted)
        self.thumb_view.files_dropped.connect(self._on_files_dropped)
        self.thumb_view.thumbnail_size_changed.connect(self._on_view_size_changed)

        self.splitter.addWidget(left_widget)
        self.splitter.addWidget(self.thumb_view)
        self.splitter.setSizes([230, 770])

        main_layout.addWidget(self.splitter, 1)

    def _toggle_videos(self, visible):
        self.thumb_view.set_show_videos(visible)
        if self.config:
            self.config.set('show_videos', visible)

    def _on_sort_changed(self):
        criterion, order = self.combo_sort.currentData(), self.combo_order.currentData()
        self.thumb_view.set_sort(criterion, order)
        if self.config:
            self.config.set('sort_by', criterion)
            self.config.set('sort_order', order)

    def _set_sort_from_menu(self, criterion, order):
        self.combo_sort.blockSignals(True)
        self.combo_order.blockSignals(True)
        self.combo_sort.setCurrentIndex(self.combo_sort.findData(criterion))
        self.combo_order.setCurrentIndex(self.combo_order.findData(order))
        self.combo_sort.blockSignals(False)
        self.combo_order.blockSignals(False)
        self._on_sort_changed()

    def _favorite_destinations(self):
        return [(self.fav_list.item(i).text(), self.fav_list.item(i).data(ROLE_PATH))
                for i in range(self.fav_list.count())
                if Path(self.fav_list.item(i).data(ROLE_PATH)).is_dir()]

    def _add_favorites_exchange_actions(self, menu):
        menu.addAction('Exporter les favoris…').triggered.connect(self.export_favorites)
        menu.addAction('Importer les favoris…').triggered.connect(self.import_favorites)

    def export_favorites(self):
        if not self.config:
            return
        filename, _ = QFileDialog.getSaveFileName(self, 'Exporter les favoris', 'TABaTAB_favoris.json', 'Favoris JSON (*.json)')
        if filename:
            try:
                export_favorites(self.config, filename)
            except OSError as error:
                QMessageBox.warning(self, 'Export impossible', str(error))

    def import_favorites(self):
        if not self.config:
            return
        filename, _ = QFileDialog.getOpenFileName(self, 'Importer les favoris', '', 'Favoris JSON (*.json)')
        if filename:
            try:
                import_favorites(self.config, filename)
            except (OSError, ValueError) as error:
                QMessageBox.warning(self, 'Import impossible', str(error))
                return
            self.favorites_updated.emit()
            self._populate_favorites()
            self._update_fav_star_button()
            QMessageBox.information(self, 'Favoris importés', 'Les favoris ont été ajoutés sans doublons. Les dossiers inaccessibles sont conservés et apparaîtront lorsqu’ils seront disponibles.')

    def _show_tree_context_menu(self, pos):
        index = self.tree_view.indexAt(pos)
        path = self.tree_model.filePath(index) if index.isValid() else self.current_folder
        menu = QMenu(self)
        menu.addAction('Nouveau dossier…').triggered.connect(lambda: self._create_tree_folder(path))
        if index.isValid():
            menu.addAction('Ouvrir dans un nouvel onglet').triggered.connect(lambda: self.open_in_new_tab_requested.emit(path))
            menu.addAction('Ajouter aux favoris').triggered.connect(lambda: self.add_folder_to_favorites(path))
            rename = menu.addAction('Renommer le dossier (F2)')
            rename.setEnabled(Path(path).resolve() != Path(Path(path).resolve().anchor))
            rename.triggered.connect(lambda: self._rename_tree_folder(path))
            delete = menu.addAction('Supprimer le dossier (Suppr)')
            delete.setEnabled(Path(path).resolve() != Path(Path(path).resolve().anchor))
            delete.triggered.connect(lambda: self._delete_tree_folder(path))
        menu.exec(self.tree_view.viewport().mapToGlobal(pos))

    def _rename_tree_folder(self, path):
        source = Path(path).resolve()
        if source == Path(source.anchor):
            return
        name, accepted = QInputDialog.getText(self, 'Renommer le dossier', 'Nouveau nom :', text=source.name)
        if not accepted:
            return
        try:
            destination = rename_folder(str(source), name)
            self.folder_renamed.emit(str(source), destination)
            index = self.tree_model.index(destination)
            self.tree_view.setCurrentIndex(index)
            self.tree_view.scrollTo(index)
        except (ValueError, OSError) as error:
            QMessageBox.warning(self, 'Renommage impossible', str(error))

    def _create_tree_folder(self, parent):
        path = create_folder(self, parent)
        if path:
            self.folder_created.emit(path)
            self.tree_view.expand(self.tree_model.index(parent))

    def _delete_tree_folder(self, path):
        for deleted in delete_folders(self, [path]):
            self.folder_deleted.emit(deleted)

    def _populate_favorites(self):
        """Populates default system shortcuts and custom user-added favorites with compact height."""
        self.fav_list.clear()
        compact_size = QSize(0, 23)
        hidden = self.config.get('hidden_favorites', []) if self.config else []

        # 1. Custom User Favorites first
        custom_favs = self.config.get("custom_favorites", []) if self.config else []
        for fav_path in custom_favs:
            p = Path(fav_path)
            if p.is_dir():
                item = QListWidgetItem(f"⭐ {p.name}")
                item.setToolTip(fav_path)
                item.setData(ROLE_PATH, str(p.resolve()))
                item.setData(ROLE_IS_CUSTOM_FAV, True)
                item.setSizeHint(compact_size)
                self.fav_list.addItem(item)

        # 2. Standard System Shortcuts
        home = Path.home()
        shortcuts = [
            ("🖼️ Images", home / "Pictures"),
            ("🖥️ Bureau", home / "Desktop"),
            ("📥 Téléchargements", home / "Downloads"),
            ("📄 Documents", home / "Documents"),
            ("🏠 Dossier Personnel", home),
        ]

        for label, path in shortcuts:
            if path.exists() and str(path.resolve()) not in hidden:
                item = QListWidgetItem(label)
                item.setToolTip(str(path))
                item.setData(ROLE_PATH, str(path.resolve()))
                item.setData(ROLE_IS_CUSTOM_FAV, False)
                item.setSizeHint(compact_size)
                self.fav_list.addItem(item)

        # 3. Windows Drives (C:, D:, etc.)
        for letter in string.ascii_uppercase:
            drive_path = Path(f"{letter}:\\")
            if drive_path.exists() and str(drive_path.resolve()) not in hidden:
                item = QListWidgetItem(f"💾 Disque ({letter}:)")
                item.setToolTip(str(drive_path))
                item.setData(ROLE_PATH, str(drive_path))
                item.setData(ROLE_IS_CUSTOM_FAV, False)
                item.setSizeHint(compact_size)
                self.fav_list.addItem(item)

        for i in range(self.fav_list.count()):
            item = self.fav_list.item(i)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsDropEnabled)
        order = self.config.get('favorite_order', []) if self.config else []
        if order:
            items = [self.fav_list.takeItem(0) for _ in range(self.fav_list.count())]
            def position(item):
                key = [item.data(ROLE_PATH), bool(item.data(ROLE_IS_CUSTOM_FAV))]
                return order.index(key) if key in order else len(order)
            for item in sorted(items, key=position):
                self.fav_list.addItem(item)

    def _save_favorite_order(self):
        if self.config:
            order = [[self.fav_list.item(i).data(ROLE_PATH), bool(self.fav_list.item(i).data(ROLE_IS_CUSTOM_FAV))]
                     for i in range(self.fav_list.count())]
            self.config.set('favorite_order', order)
            self.favorites_updated.emit()

    def _on_favorite_clicked(self, item: QListWidgetItem):
        path = item.data(ROLE_PATH)
        if path:
            self.navigate_to(path)

    def _show_fav_context_menu(self, pos):
        item = self.fav_list.itemAt(pos)
        if not item:
            menu = QMenu(self)
            self._add_favorites_exchange_actions(menu)
            menu.exec(self.fav_list.viewport().mapToGlobal(pos))
            return

        path = item.data(ROLE_PATH)
        is_custom = item.data(ROLE_IS_CUSTOM_FAV)

        menu = QMenu(self)
        act_open = menu.addAction("📂 Ouvrir")
        act_open.triggered.connect(lambda: self.navigate_to(path))

        act_new_tab = menu.addAction("➕ Ouvrir dans un nouvel onglet")
        act_new_tab.triggered.connect(lambda: self.open_in_new_tab_requested.emit(path))

        copy = menu.addAction('Copier les images sélectionnées dans ce dossier')
        copy.setEnabled(bool(self.thumb_view.get_selected_file_paths()))
        copy.triggered.connect(lambda: self.files_dropped.emit(
            [p for p in self.thumb_view.get_selected_file_paths() if Path(p).is_file()], path, True))
        paste = menu.addAction('Coller dans ce dossier (Ctrl+V)')
        mime = QApplication.clipboard().mimeData()
        paste.setEnabled(mime is not None and (mime.hasUrls() or mime.hasImage()))
        paste.triggered.connect(lambda: self.thumb_view.paste_images(path))

        menu.addSeparator()

        act_remove = menu.addAction("🗑 Retirer des favoris")
        act_remove.triggered.connect(lambda: self.remove_custom_favorite(path))

        act_copy = menu.addAction("📋 Copier le chemin")
        act_copy.triggered.connect(lambda: QApplication.clipboard().setText(path))

        menu.addSeparator()
        self._add_favorites_exchange_actions(menu)

        menu.exec(self.fav_list.mapToGlobal(pos))

    def add_current_to_favorites(self):
        self.add_folder_to_favorites(self.current_folder)

    def add_folder_to_favorites(self, path):
        if not path or not self.config or not Path(path).is_dir():
            return
        favs = list(self.config.get("custom_favorites", []))
        resolved = str(Path(path).resolve())
        if not any(Path(fav).resolve() == Path(resolved) for fav in favs):
            favs.append(resolved)
            self.config.set("custom_favorites", favs)
            hidden = self.config.get('hidden_favorites', [])
            self.config.set('hidden_favorites', [fav for fav in hidden if Path(fav).resolve() != Path(resolved)])
            self.favorites_updated.emit()
            self._populate_favorites()
            self._update_fav_star_button()

    def remove_custom_favorite(self, path: str):
        if not self.config:
            return
        favs = list(self.config.get("custom_favorites", []))
        resolved = str(Path(path).resolve())
        if resolved in favs:
            favs.remove(resolved)
            self.config.set("custom_favorites", favs)
        else:
            hidden = list(self.config.get('hidden_favorites', []))
            if resolved not in hidden:
                hidden.append(resolved)
                self.config.set('hidden_favorites', hidden)
        self.favorites_updated.emit()
        self._populate_favorites()
        self._update_fav_star_button()

    def toggle_current_favorite(self):
        if not self.current_folder or not self.config:
            return
        favs = list(self.config.get("custom_favorites", []))
        resolved = str(Path(self.current_folder).resolve())
        if resolved in favs:
            self.remove_custom_favorite(resolved)
        else:
            self.add_current_to_favorites()

    def _update_fav_star_button(self):
        if not self.config:
            return
        favs = self.config.get("custom_favorites", [])
        resolved = str(Path(self.current_folder).resolve())
        if resolved in favs:
            self.btn_fav_star.setText("⭐")
            self.btn_fav_star.setToolTip("Ce dossier est dans vos favoris (cliquer pour retirer)")
        else:
            self.btn_fav_star.setText("☆")
            self.btn_fav_star.setToolTip("Ajouter ce dossier aux favoris")

    def navigate_to(self, folder_path: str, add_history: bool = True):
        p = Path(folder_path).resolve()
        if not p.exists() or not p.is_dir():
            return

        resolved_str = str(p)
        if add_history and not self.is_navigating_history and self.current_folder:
            self.history_back.append(self.current_folder)
            self.history_forward.clear()

        self.current_folder = resolved_str
        self.path_edit.setText(resolved_str)
        self.breadcrumb.set_path(resolved_str)
        self.thumb_view.setFolder(resolved_str)
        self._update_fav_star_button()

        # Highlight in Tree
        idx = self.tree_model.index(resolved_str)
        if idx.isValid():
            self.tree_view.setCurrentIndex(idx)
            self.tree_view.scrollTo(idx)

        self._update_history_buttons()
        self.folder_changed.emit(resolved_str)

    def go_back(self):
        if self.history_back:
            self.is_navigating_history = True
            prev = self.history_back.pop()
            self.history_forward.append(self.current_folder)
            self.navigate_to(prev, add_history=False)
            self.is_navigating_history = False
            self._update_history_buttons()

    def go_forward(self):
        if self.history_forward:
            self.is_navigating_history = True
            nxt = self.history_forward.pop()
            self.history_back.append(self.current_folder)
            self.navigate_to(nxt, add_history=False)
            self.is_navigating_history = False
            self._update_history_buttons()

    def go_up(self):
        parent = Path(self.current_folder).parent
        if parent.exists() and parent != Path(self.current_folder):
            self.navigate_to(str(parent))

    def refresh(self):
        self.thumb_view.setFolder(self.current_folder)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Sélectionner un dossier d'images", self.current_folder
        )
        if folder:
            self.navigate_to(folder)

    def _on_path_entered(self):
        text = self.path_edit.text().strip()
        if text:
            self.navigate_to(text)

    def _on_tree_clicked(self, index: QModelIndex):
        folder_path = self.tree_model.filePath(index)
        if folder_path:
            self.navigate_to(folder_path)

    def _on_slider_changed(self, value: int):
        self.current_thumb_size = value
        self.lbl_size_val.setText(f"{value}px")
        self.thumb_view.setThumbnailSize(value)
        self.thumbnail_size_saved.emit(value)

    def _on_preset_changed(self, index: int):
        presets = [90, 160, 260, 380, 500, 600]
        if 0 <= index < len(presets):
            size = presets[index]
            self.slider_size.blockSignals(True)
            self.slider_size.setValue(size)
            self.slider_size.blockSignals(False)
            self._on_slider_changed(size)

    def _on_view_size_changed(self, new_size: int):
        self.current_thumb_size = new_size
        self.slider_size.blockSignals(True)
        self.slider_size.setValue(new_size)
        self.slider_size.blockSignals(False)
        self.lbl_size_val.setText(f"{new_size}px")
        self.thumbnail_size_saved.emit(new_size)

    def _on_image_double_clicked(self, file_path: str):
        self.request_fullscreen.emit(self.thumb_view.all_files, file_path)

    def _on_files_dropped(self, source_files: list, target_folder: str, is_copy: bool):
        self.files_dropped.emit(source_files, target_folder, is_copy)

    def _update_history_buttons(self):
        self.btn_back.setEnabled(len(self.history_back) > 0)
        self.btn_forward.setEnabled(len(self.history_forward) > 0)
