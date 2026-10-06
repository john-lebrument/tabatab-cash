from pathlib import Path
from PyQt6.QtCore import Qt, QPoint, QRectF, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QKeySequence,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
    QImageReader,
    QTransform,
    QWheelEvent,
)
from PyQt6.QtWidgets import (
    QDialog,
    QInputDialog,
    QComboBox,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QSizeGrip,
    QSlider,
    QApplication,
)

from src.ui.crop_overlay import CropOverlayItem
from src.utils.file_ops import crop_image, trash_image, restore_last_deleted, rename_images
from src.ui.blur_tool import BlurSelection, blurred_regions, save_blurs
from src.utils.windows_integration import reveal_in_explorer


class WindowMoveHandle(QLabel):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 180))
        painter.setPen(QPen(QColor('white'), 1.5))
        x, y = self.width() // 2, self.height() // 2
        painter.drawLine(x - 8, y, x + 8, y)
        painter.drawLine(x, y - 8, x, y + 8)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            tip_x, tip_y = x + dx * 8, y + dy * 8
            painter.drawLine(tip_x, tip_y, tip_x - dx * 3 + dy * 3, tip_y - dy * 3 + dx * 3)
            painter.drawLine(tip_x, tip_y, tip_x - dx * 3 - dy * 3, tip_y - dy * 3 - dx * 3)
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.window().windowHandle():
            self.window().windowHandle().startSystemMove()
            event.accept()


class FloatingCloseButton(QPushButton):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor('black'))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor('#ff4040'), 2.5))
        painter.drawLine(7, 6, self.width() - 7, self.height() - 6)
        painter.drawLine(self.width() - 7, 6, 7, self.height() - 6)
        painter.end()


class WindowSizeGrip(QSizeGrip):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 180))
        painter.setPen(QPen(QColor('white'), 1.5))
        for offset in (4, 9, 14):
            painter.drawLine(self.width() - offset, self.height() - 3,
                             self.width() - 3, self.height() - offset)
        painter.end()



class CropConfirmDialog(QDialog):
    """Clean modern dialog to choose between saving as copy or overwriting."""

    def __init__(self, parent=None, title_text='Enregistrement du recadrage :'):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.choice = None  # "overwrite", "copy", or None
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                border: 2px solid #0078d4;
                border-radius: 10px;
                padding: 16px;
            }
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton {
                background-color: #383838;
                border: 1px solid #555555;
                border-radius: 6px;
                color: #ffffff;
                padding: 8px 16px;
                font-size: 13px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #0078d4;
                border-color: #0078d4;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel(title_text, self)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        btn_layout = QHBoxLayout()
        btn_copy = QPushButton("Enregistrer une copie", self)
        btn_overwrite = QPushButton("Écraser l'original", self)
        btn_cancel = QPushButton("Annuler", self)

        btn_copy.clicked.connect(self._on_copy)
        btn_overwrite.clicked.connect(self._on_overwrite)
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(btn_copy)
        btn_layout.addWidget(btn_overwrite)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def _on_copy(self):
        self.choice = "copy"
        self.accept()

    def _on_overwrite(self):
        self.choice = "overwrite"
        self.accept()


class FullscreenGraphicsView(QGraphicsView):
    """Custom view forwarding all key presses to the parent FullscreenImageViewer."""

    def __init__(self, scene, viewer, parent=None):
        super().__init__(scene, parent)
        self.viewer = viewer

    def keyPressEvent(self, event):
        self.viewer.keyPressEvent(event)

    def mousePressEvent(self, event):
        if self.viewer.floating and event.button() == Qt.MouseButton.LeftButton:
            point = self.viewport().mapTo(self.viewer, event.position().toPoint())
            edges = Qt.Edge(0)
            if point.x() < 6:
                edges |= Qt.Edge.LeftEdge
            elif point.x() >= self.viewer.width() - 6:
                edges |= Qt.Edge.RightEdge
            if point.y() < 6:
                edges |= Qt.Edge.TopEdge
            elif point.y() >= self.viewer.height() - 6:
                edges |= Qt.Edge.BottomEdge
            handle = self.viewer.windowHandle()
            if handle and edges and handle.startSystemResize(edges):
                event.accept()
                return
            if handle and event.modifiers() & Qt.KeyboardModifier.AltModifier:
                handle.startSystemMove()
                event.accept()
                return
        if event.button() == Qt.MouseButton.RightButton:
            self.viewer._show_hud()
            event.accept()
            return
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        self.viewer.wheelEvent(event)

    def contextMenuEvent(self, event):
        self.viewer._show_hud()
        event.accept()


class FullscreenImageViewer(QWidget):
    """
    Frameless, pure fullscreen image viewer.
    - Double click or Escape: Close viewer
    - +/- keys or Ctrl+mouse wheel: Zoom; wheel: navigate
    - Left/Right arrows: Navigate images
    - X/C key or toolbar button: Interactive cropping
    - Space key: Next image
    """

    image_modified = pyqtSignal(str)  # emitted when an image is cropped/saved
    images_renamed = pyqtSignal(list)
    image_deleted = pyqtSignal(str)
    image_restored = pyqtSignal(str)
    viewer_closed = pyqtSignal(str)
    floating_requested = pyqtSignal(list, str)
    navigate_requested = pyqtSignal(int)  # -1 for prev, +1 for next

    def __init__(self, parent=None, floating=False):
        super().__init__(parent, Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.floating = floating
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, floating)
        if floating:
            self.setMinimumSize(64, 64)
        self._wheel_remainder = 0
        self.setStyleSheet("background-color: #000000;")

        self.image_list: list[str] = []
        self.current_index: int = -1
        self.current_pixmap: QPixmap | None = None
        self.pixmap_item: QGraphicsPixmapItem | None = None
        self.crop_item: CropOverlayItem | None = None
        self.crop_mode: bool = False
        self.rotation_degrees = 0
        self.blur_item = None
        self.blur_source = None
        self._deleted_positions = {}
        self.blur_timer = QTimer(self)
        self.blur_timer.setSingleShot(True)
        self.blur_timer.setInterval(75)
        self.blur_timer.timeout.connect(self._preview_blur)

        self.zoom_factor: float = 1.0
        self.fit_zoom_factor: float = 1.0

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Graphics Scene & View (using custom view to capture arrow keys properly)
        self.scene = QGraphicsScene(self)
        self.view = FullscreenGraphicsView(self.scene, self, self)
        self.view.setStyleSheet("background: #000000; border: none;")
        self.view.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )
        scroll_policy = Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        self.view.setHorizontalScrollBarPolicy(scroll_policy)
        self.view.setVerticalScrollBarPolicy(scroll_policy)
        self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

        layout.addWidget(self.view)

        # Floating HUD Toolbar
        self.hud = QWidget(self)
        self.hud.setStyleSheet("""
            QWidget {
                background-color: rgba(26, 26, 26, 220);
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 8px;
            }
            QPushButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 5px;
                color: #ffffff;
                padding: 6px 10px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 40);
                border-color: rgba(255, 255, 255, 60);
            }
            QPushButton:pressed {
                background-color: #0078d4;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 12px;
                padding: 0 8px;
            }
        """)

        hud_stack = QVBoxLayout(self.hud)
        hud_stack.setContentsMargins(4, 4, 4, 4)
        hud_layout = QHBoxLayout()
        hud_stack.addLayout(hud_layout)
        hud_layout.setContentsMargins(8, 4, 8, 4)
        hud_layout.setSpacing(6)

        self.btn_prev = QPushButton("◀ Précédente", self.hud)
        self.btn_prev.clicked.connect(self.prev_image)
        hud_layout.addWidget(self.btn_prev)

        self.btn_next = QPushButton("Suivante ▶", self.hud)
        self.btn_next.clicked.connect(self.next_image)
        hud_layout.addWidget(self.btn_next)

        hud_layout.addSpacing(10)

        self.btn_zoom_out = QPushButton("−", self.hud)
        self.btn_zoom_out.setToolTip("Dézoomer (-)")
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        hud_layout.addWidget(self.btn_zoom_out)

        self.lbl_zoom = QLabel("100%", self.hud)
        hud_layout.addWidget(self.lbl_zoom)

        self.btn_zoom_in = QPushButton("+", self.hud)
        self.btn_zoom_in.setToolTip("Zoomer (+)")
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        hud_layout.addWidget(self.btn_zoom_in)

        self.btn_fit = QPushButton("⛶ Ajuster", self.hud)
        self.btn_fit.setToolTip("Ajuster à l'écran (0)")
        self.btn_fit.clicked.connect(self.fit_to_screen)
        hud_layout.addWidget(self.btn_fit)
        self.btn_screen = QPushButton('Écran suivant (M)', self.hud)
        self.btn_screen.clicked.connect(self.move_to_next_screen)
        self.btn_screen.setVisible(not self.floating)
        hud_layout.addWidget(self.btn_screen)
        self.btn_explorer = QPushButton("Afficher dans l'explorateur Windows", self.hud)
        self.btn_explorer.clicked.connect(self.reveal_current_image)
        hud_layout.addWidget(self.btn_explorer)

        hud_layout.addSpacing(10)

        hud_layout = QHBoxLayout()
        hud_stack.addLayout(hud_layout)
        self.btn_rot_l = QPushButton("↺ 90°", self.hud)
        self.btn_rot_l.setToolTip("Rotation 90° Gauche (Touche L)")
        self.btn_rot_l.clicked.connect(lambda: self.rotate_image(-90))
        hud_layout.addWidget(self.btn_rot_l)

        self.btn_rot_r = QPushButton("↻ 90°", self.hud)
        self.btn_rot_r.setToolTip("Rotation 90° Droite (Touche R)")
        self.btn_rot_r.clicked.connect(lambda: self.rotate_image(90))
        hud_layout.addWidget(self.btn_rot_r)

        self.btn_save_rot = QPushButton("💾 Sauvegarder", self.hud)
        self.btn_save_rot.setToolTip("Sauvegarder la rotation (Ctrl + S)")
        self.btn_save_rot.setStyleSheet("background-color: #0078d4; font-weight: bold;")
        self.btn_save_rot.clicked.connect(self.save_rotated_image)
        self.btn_save_rot.hide()
        hud_layout.addWidget(self.btn_save_rot)

        hud_layout.addSpacing(10)

        self.btn_crop = QPushButton("✂ Recadrer", self.hud)
        self.btn_crop.setToolTip("Activer le recadrage (X ou C)")
        self.btn_crop.clicked.connect(self.toggle_crop_mode)
        hud_layout.addWidget(self.btn_crop)
        self.btn_blur = QPushButton('Flouter (F)', self.hud)
        self.btn_blur.clicked.connect(self.start_blur)
        hud_layout.addWidget(self.btn_blur)

        self.btn_crop_apply = QPushButton("✔ Valider Recadrage", self.hud)
        self.btn_crop_apply.setStyleSheet("background-color: #0078d4; font-weight: bold;")
        self.btn_crop_apply.clicked.connect(self.apply_crop)
        self.btn_crop_apply.hide()
        hud_layout.addWidget(self.btn_crop_apply)

        self.btn_crop_cancel = QPushButton("✕ Annuler", self.hud)
        self.btn_crop_cancel.clicked.connect(self.cancel_crop)
        self.btn_crop_cancel.hide()
        hud_layout.addWidget(self.btn_crop_cancel)

        hud_layout.addSpacing(10)

        self.lbl_info = QLabel("", self.hud)
        self.lbl_info.setMaximumWidth(240)
        self.lbl_info.setWordWrap(True)
        hud_layout.addWidget(self.lbl_info)

        self.btn_close = QPushButton("✕ Quitter", self.hud)
        self.btn_close.setToolTip("Fermer le plein écran (Échap)")
        self.btn_close.clicked.connect(self.close_fullscreen)
        hud_layout.addWidget(self.btn_close)

        # Timer to auto-hide HUD
        self.hud_timer = QTimer(self)
        self.hud_timer.setInterval(3500)
        self.hud_timer.timeout.connect(self._fade_out_hud)

        self.setMouseTracking(True)
        self.view.setMouseTracking(True)
        self.hud.hide()

        self.counter = QLabel(self)
        self.counter.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.counter.setStyleSheet('background: rgba(0,0,0,155); color: #ffd54f; '
                                   'border-radius: 7px; padding: 8px 12px; font-size: 14px;')
        self.counter.hide()
        self.zoom_badge = QLabel('100 %', self)
        self.zoom_badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.zoom_badge.setStyleSheet('background: rgba(0,0,0,155); color: white; '
                                      'border-radius: 7px; padding: 8px 12px; font-size: 14px;')
        self.zoom_badge.hide()
        self.toast = QLabel(self)
        self.toast.setStyleSheet('background: #252525; color: white; padding: 10px; border-radius: 5px;')
        self.toast.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.toast.hide()
        self.toast_timer = QTimer(self)
        self.toast_timer.setSingleShot(True)
        self.toast_timer.timeout.connect(self.toast.hide)

        self.blur_panel = QWidget(self)
        self.blur_panel.setStyleSheet('QWidget { background: #252525; color: white; } QPushButton { padding: 8px; }')
        blur_layout = QHBoxLayout(self.blur_panel)
        blur_layout.addWidget(QLabel('Flou :', self.blur_panel))
        self.blur_slider = QSlider(Qt.Orientation.Horizontal, self.blur_panel)
        self.blur_slider.setRange(0, 100)
        self.blur_slider.setValue(30)
        self.blur_slider.setMinimumWidth(180)
        self.blur_slider.valueChanged.connect(lambda: self.blur_timer.start())
        blur_layout.addWidget(self.blur_slider)
        self.blur_value = QLabel('30 %', self.blur_panel)
        self.blur_slider.valueChanged.connect(lambda value: self.blur_value.setText(f'{value} %'))
        blur_layout.addWidget(self.blur_value)
        self.blur_count = QLabel('0 zone', self.blur_panel)
        blur_layout.addWidget(self.blur_count)
        undo_blur_button = QPushButton('Effacer la dernière zone', self.blur_panel)
        undo_blur_button.clicked.connect(self._remove_last_blur)
        blur_layout.addWidget(undo_blur_button)
        save_blur_button = QPushButton('Enregistrer…', self.blur_panel)
        save_blur_button.clicked.connect(self.apply_blur)
        blur_layout.addWidget(save_blur_button)
        cancel_blur_button = QPushButton('Annuler', self.blur_panel)
        cancel_blur_button.clicked.connect(self.cancel_blur)
        blur_layout.addWidget(cancel_blur_button)
        self.blur_panel.hide()

        self.crop_panel = QWidget(self)
        self.crop_panel.setStyleSheet('QWidget { background: #252525; color: white; } '
                                     'QPushButton, QComboBox { padding: 7px; border: 1px solid #666; '
                                     'border-radius: 4px; } QPushButton:hover { background: #0078d4; }')
        crop_layout = QVBoxLayout(self.crop_panel)
        controls = QHBoxLayout()
        controls.addWidget(QLabel('Recadrage', self.crop_panel))
        self.crop_ratio = QComboBox(self.crop_panel)
        for label, ratio in [('Libre', None), ('Original', 'original'), ('Carré 1:1', 1.0),
                             ('4:3', 4/3), ('3:2', 3/2), ('16:9', 16/9),
                             ('3:4', 3/4), ('2:3', 2/3), ('9:16', 9/16)]:
            self.crop_ratio.addItem(label, ratio)
        self.crop_ratio.currentIndexChanged.connect(self._change_crop_ratio)
        controls.addWidget(self.crop_ratio)
        self.btn_ratio_flip = QPushButton('↔', self.crop_panel)
        self.btn_ratio_flip.setToolTip('Inverser les proportions : portrait / paysage')
        self.btn_ratio_flip.clicked.connect(self._flip_crop_ratio)
        controls.addWidget(self.btn_ratio_flip)
        self.crop_dimensions = QLabel(self.crop_panel)
        controls.addWidget(self.crop_dimensions)
        reset = QPushButton('Réinitialiser', self.crop_panel)
        reset.clicked.connect(lambda: self.crop_item.reset_selection() if self.crop_item else None)
        controls.addWidget(reset)
        save = QPushButton('Enregistrer…', self.crop_panel)
        save.setStyleSheet('background: #0078d4;')
        save.clicked.connect(self.apply_crop)
        controls.addWidget(save)
        cancel = QPushButton('Annuler', self.crop_panel)
        cancel.clicked.connect(self.cancel_crop)
        controls.addWidget(cancel)
        crop_layout.addLayout(controls)
        hint = QLabel('Poignées : redimensionner · Intérieur : déplacer · Extérieur : nouvelle sélection\n'
                      'Maj : proportions fixes · Flèches : 1 px (Maj : 10 px) · Entrée : enregistrer · Échap : annuler', self.crop_panel)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        crop_layout.addWidget(hint)
        self.crop_panel.hide()
        if self.floating:
            self.size_grip = WindowSizeGrip(self)
            self.size_grip.setFixedSize(20, 20)
            self.size_grip.setStyleSheet('background: rgba(70,70,70,150);')
            self.size_grip.hide()
            self.move_handle = WindowMoveHandle('✥', self)
            self.move_handle.setFixedSize(26, 22)
            self.move_handle.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.move_handle.setCursor(Qt.CursorShape.SizeAllCursor)
            self.move_handle.setToolTip('Glisser pour déplacer la fenêtre (ou Alt+glisser sur l’image)')
            self.move_handle.setStyleSheet('color: white; background: rgba(0,0,0,130);')
            self.move_handle.hide()
            self.floating_close = FloatingCloseButton('×', self)
            self.floating_close.setToolTip('Fermer cette image')
            self.floating_close.setAccessibleName('Fermer cette image')
            self.floating_close.setFixedSize(24, 22)
            self.floating_close.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.floating_close.setStyleSheet('color: #ff4040; background: black; border: none; font-size: 20px; font-weight: bold;')
            self.floating_close.clicked.connect(self.close_fullscreen)
            self.floating_close.hide()

    def move_to_screen(self, screen):
        if screen is None:
            return
        self.winId()
        self.showNormal()
        self.windowHandle().setScreen(screen)
        self.setGeometry(screen.geometry())
        self.showFullScreen()
        self._position_hud()
        self.fit_to_screen()
        self.activateWindow()
        self.view.setFocus()

    def move_to_next_screen(self):
        screens = QApplication.screens()
        if len(screens) < 2:
            self.show_message('Un seul écran est disponible')
            return
        current = self.screen()
        index = screens.index(current) if current in screens else -1
        self.move_to_screen(screens[(index + 1) % len(screens)])
        self.show_message(f'Écran {(index + 1) % len(screens) + 1}')

    def show_images(self, image_paths: list[str], current_path: str, screen=None):
        """Opens fullscreen viewer with the given image list."""
        self.image_list = list(image_paths)
        self.hud_timer.stop()
        self.hud.hide()
        try:
            self.current_index = self.image_list.index(current_path)
        except ValueError:
            self.current_index = 0

        if self.floating:
            self.load_current_image()
            if self.current_pixmap and not self.current_pixmap.isNull():
                available = self.screen().availableGeometry()
                factor = min(1, available.width() / self.current_pixmap.width(), available.height() / self.current_pixmap.height())
                self.resize(round(self.current_pixmap.width() * factor), round(self.current_pixmap.height() * factor))
                self.move(available.center() - self.rect().center())
            self.show()
            self.fit_to_screen()
        else:
            if screen is not None:
                self.winId()
                self.windowHandle().setScreen(screen)
                self.setGeometry(screen.geometry())
            self.showFullScreen()
            self.load_current_image()
        self._position_hud()
        self.view.setFocus()

    def load_current_image(self):
        if not self.image_list or self.current_index < 0 or self.current_index >= len(self.image_list):
            return

        file_path = self.image_list[self.current_index]
        self.cancel_blur()
        self.cancel_crop()
        self.hud.hide()
        self.hud_timer.stop()
        self.rotation_degrees = 0
        self.btn_save_rot.hide()
        self._update_counter()

        reader = QImageReader(file_path)
        reader.setAutoTransform(True)
        self.current_pixmap = QPixmap.fromImage(reader.read())
        if self.current_pixmap.isNull():
            return

        self.scene.clear()
        self.pixmap_item = self.scene.addPixmap(self.current_pixmap)
        self.scene.setSceneRect(QRectF(self.current_pixmap.rect()))

        self.fit_to_screen()

        # Update info label
        w = self.current_pixmap.width()
        h = self.current_pixmap.height()
        name = Path(file_path).name
        idx_str = f"{self.current_index + 1}/{len(self.image_list)}"
        self.lbl_info.setText(f"{name}  ({w}×{h})  [{idx_str}]")

    def _update_counter(self):
        total = len(self.image_list)
        remaining = max(0, total - self.current_index - 1)
        suffix = 'image restante' if remaining == 1 else 'images restantes'
        name = Path(self.image_list[self.current_index]).name if 0 <= self.current_index < total else ''
        metrics = self.counter.fontMetrics()
        self.counter.setText(f'{self.current_index + 1} / {total}\n{remaining} {suffix}\n'
                             + metrics.elidedText(name, Qt.TextElideMode.ElideMiddle, max(120, self.width() - 80)))
        self.counter.setToolTip(name)
        if self.floating:
            self.counter.hide()
            return
        self.counter.adjustSize()
        self.counter.move(20, 20)
        self.counter.show()
        self.counter.raise_()
        self._position_zoom_badge()

    def fit_to_screen(self):
        if not self.current_pixmap or self.current_pixmap.isNull():
            return
        self.view.resetTransform()
        view_rect = self.view.viewport().rect()
        scene_rect = self.scene.sceneRect()
        if scene_rect.isEmpty():
            return

        scale_x = view_rect.width() / scene_rect.width()
        scale_y = view_rect.height() / scene_rect.height()
        factor = min(scale_x, scale_y)

        self.view.scale(factor, factor)
        self.zoom_factor = factor
        self.fit_zoom_factor = factor
        self._update_zoom_label()

    def zoom_in(self):
        self._apply_zoom(1.25)

    def zoom_out(self):
        self._apply_zoom(0.8)

    def _apply_zoom(self, factor: float):
        if not self.current_pixmap:
            return
        new_factor = self.zoom_factor * factor
        # Zoom is relative to the image fitted to the screen (100%).
        if 0.02 <= new_factor / self.fit_zoom_factor <= 30.0:
            self.view.scale(factor, factor)
            self.zoom_factor = new_factor
            self._update_zoom_label()

    def _update_zoom_label(self):
        pct = round(self.zoom_factor / self.fit_zoom_factor * 100)
        self.lbl_zoom.setText(f"{pct} %")
        self.zoom_badge.setText(f"{pct} %")
        self._position_zoom_badge()
        self.zoom_badge.setVisible(not self.floating)
        self.zoom_badge.raise_()

    def _position_zoom_badge(self):
        if hasattr(self, 'zoom_badge'):
            self.zoom_badge.adjustSize()
            self.zoom_badge.move(20, self.counter.y() + self.counter.height() + 4)

    def rename_current_image(self):
        if not (0 <= self.current_index < len(self.image_list)):
            return
        if self.crop_mode or self.blur_item or not self._confirm_rotation():
            return
        path = self.image_list[self.current_index]
        name, accepted = QInputDialog.getText(self, 'Renommer l’image', 'Nouveau nom (sans extension) :', text=Path(path).stem)
        if not accepted:
            return
        try:
            changes = rename_images([path], name)
            self.images_renamed.emit(changes)
            self.image_list[self.current_index] = changes[0][1]
            self.load_current_image()
        except (ValueError, OSError) as error:
            QMessageBox.warning(self, 'Renommage impossible', str(error))

    def reveal_current_image(self):
        if 0 <= self.current_index < len(self.image_list):
            reveal_in_explorer(self.image_list[self.current_index])

    def _rotation_choice(self):
        dialog = QMessageBox(QMessageBox.Icon.Question, 'Enregistrer la rotation ?',
            "Souhaitez-vous enregistrer la nouvelle orientation de cette image ?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            self)
        dialog.setDefaultButton(QMessageBox.StandardButton.Save)
        dialog.button(QMessageBox.StandardButton.Save).setText('Enregistrer')
        dialog.button(QMessageBox.StandardButton.Discard).setText('Ne pas enregistrer')
        dialog.button(QMessageBox.StandardButton.Cancel).setText('Annuler')
        dialog.setStyleSheet('''
            QMessageBox { background-color: #2b2b2b; }
            QMessageBox QLabel { background: transparent; color: white; min-width: 360px; }
            QMessageBox QPushButton { background: #3a3a3a; color: white; border: 1px solid #777;
                                     border-radius: 4px; min-width: 110px; padding: 7px 12px; }
            QMessageBox QPushButton:hover { background: #0078d4; border-color: #55aaff; }
        ''')
        self._last_rotation_dialog = dialog
        dialog.exec()
        if dialog.clickedButton() == dialog.button(QMessageBox.StandardButton.Save):
            choice = QMessageBox.StandardButton.Save
        elif dialog.clickedButton() == dialog.button(QMessageBox.StandardButton.Discard):
            choice = QMessageBox.StandardButton.Discard
        else:
            choice = QMessageBox.StandardButton.Cancel
        return choice

    def _confirm_rotation(self):
        if not self.rotation_degrees or not 0 <= self.current_index < len(self.image_list):
            return True
        choice = self._rotation_choice()
        if choice == QMessageBox.StandardButton.Cancel:
            return False
        if choice == QMessageBox.StandardButton.Save:
            path = self.image_list[self.current_index]
            try:
                crop_image(path, (0, 0, self.current_pixmap.width(), self.current_pixmap.height()),
                           overwrite=True, rotation_degrees=self.rotation_degrees)
                self.image_modified.emit(path)
            except Exception as error:
                QMessageBox.warning(self, 'Rotation non enregistrée', str(error))
                return False
        self.rotation_degrees = 0
        self.btn_save_rot.hide()
        return True

    def prev_image(self):
        if not self.image_list:
            return
        if self.current_index <= 0 or not self._confirm_rotation():
            return
        self.current_index = max(0, self.current_index - 1)
        self.load_current_image()

    def next_image(self):
        if not self.image_list:
            return
        if self.current_index >= len(self.image_list) - 1:
            self.hud.hide()
            self.show_message('Fin du répertoire')
            return
        if not self._confirm_rotation():
            return
        self.current_index += 1
        self.load_current_image()
        if self.current_index == len(self.image_list) - 1:
            self.show_message('Fin du répertoire')

    def delete_current_image(self, permanent=False):
        if not 0 <= self.current_index < len(self.image_list):
            return
        path = self.image_list[self.current_index]
        deleted_position = self.current_index
        try:
            if permanent:
                Path(path).unlink()
            else:
                trash_image(path)
        except OSError as error:
            QMessageBox.warning(self, 'Corbeille indisponible', str(error))
            return
        self._deleted_positions[path] = deleted_position
        self.remove_image(path)
        self.image_deleted.emit(path)
        self.show_message('Image supprimée', 1000)

    def show_message(self, text, duration=1000):
        self.toast.setText(text)
        self.toast.adjustSize()
        self.toast.move(20, 20)
        self.toast.show()
        self.toast.raise_()
        self.toast_timer.start(duration)

    def undo_delete(self):
        try:
            path = restore_last_deleted()
            if path:
                if path not in self.image_list:
                    self.image_list.insert(self._deleted_positions.pop(path, max(0, self.current_index)), path)
                self.current_index = self.image_list.index(path)
                self.load_current_image()
                self.image_restored.emit(path)
                self.show_message('Image restaurée')
        except OSError as error:
            QMessageBox.warning(self, 'Restauration impossible', str(error))

    def remove_image(self, path):
        if not any(Path(p) == Path(path) for p in self.image_list):
            return
        current = self.image_list[self.current_index] if self.current_index >= 0 else None
        self.image_list = [p for p in self.image_list if Path(p) != Path(path)]
        if not self.image_list:
            self.current_index = -1
            self.counter.setText('0 / 0')
            self.cancel_blur()
            self.cancel_crop()
            self.scene.clear()
            self.current_pixmap = None
            self.zoom_badge.hide()
            self.pixmap_item = None
            # Keep the viewer open so Ctrl+Z can restore the last image too.
        elif current in self.image_list:
            self.current_index = self.image_list.index(current)
            self._update_counter()
        else:
            self.current_index = min(self.current_index, len(self.image_list) - 1)
            self.load_current_image()

    def start_blur(self):
        if self.blur_item:
            self.cancel_blur()
            return
        if not self.current_pixmap or self.current_pixmap.isNull():
            return
        from PIL.ImageQt import fromqimage
        self.cancel_crop()
        self.hud.hide()
        self.blur_source = fromqimage(self.current_pixmap.toImage()).convert('RGBA')
        self.blur_item = BlurSelection(QRectF(self.current_pixmap.rect()))
        self.scene.addItem(self.blur_item)
        self.blur_item.rect_changed.connect(self._blur_selection_changed)
        self.view.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.blur_panel.show()
        self._position_hud()
        self.blur_panel.raise_()
        self.view.setViewportMargins(0, 0, 0, self.blur_panel.height() + 40)
        self.fit_to_screen()
        self._update_blur_preview()
        self.view.setFocus()

    def _blur_selection_changed(self):
        self.blur_timer.start()
        if self.blur_item:
            count = len(self.blur_item.get_boxes())
            self.blur_count.setText(f'{count} zone' + ('s' if count != 1 else ''))

    def _update_blur_preview(self):
        self._blur_selection_changed()
        self._preview_blur()

    def _preview_blur(self):
        if self.blur_item is None or self.blur_source is None:
            return
        from PIL.ImageQt import ImageQt
        result = blurred_regions(self.blur_source, self.blur_item.get_preview_boxes(), self.blur_slider.value())
        self.pixmap_item.setPixmap(QPixmap.fromImage(ImageQt(result)))

    def _remove_last_blur(self):
        if self.blur_item:
            self.blur_item.remove_last()
            self._update_blur_preview()

    def cancel_blur(self):
        self.blur_timer.stop()
        if self.blur_item is not None:
            self.scene.removeItem(self.blur_item)
            self.blur_item = None
            if self.pixmap_item and self.current_pixmap:
                self.pixmap_item.setPixmap(self.current_pixmap)
            self.view.setViewportMargins(0, 0, 0, 0)
            self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.fit_to_screen()
        self.blur_source = None
        self.blur_panel.hide()
        self.view.setFocus()

    def apply_blur(self):
        if self.blur_item is None or self.current_index < 0:
            return
        boxes = self.blur_item.get_boxes()
        if not boxes:
            self.show_message('Dessinez au moins une zone à flouter')
            return
        dialog = CropConfirmDialog(self, 'Enregistrement du floutage :')
        if dialog.exec() != QDialog.DialogCode.Accepted or not dialog.choice:
            return
        try:
            path = save_blurs(self.image_list[self.current_index], boxes,
                              self.blur_slider.value(), dialog.choice == 'overwrite', self.rotation_degrees)
            self.cancel_blur()
            if dialog.choice == 'copy':
                self.image_list.insert(self.current_index + 1, str(path))
                self.current_index += 1
            self.load_current_image()
            self.image_modified.emit(str(path))
            self.show_message('Floutage enregistré')
        except Exception as error:
            QMessageBox.warning(self, 'Enregistrement impossible', str(error))

    def toggle_crop_mode(self):
        if self.crop_mode:
            self.cancel_crop()
        else:
            self.start_crop_mode()

    def start_crop_mode(self):
        self.cancel_blur()
        if not self.current_pixmap or self.crop_mode:
            return
        if self.floating:
            available = self.screen().availableGeometry()
            self.resize(max(self.width(), min(1000, available.width())),
                        max(self.height(), min(650, available.height())))
        self.crop_mode = True
        self.view.setDragMode(QGraphicsView.DragMode.NoDrag)

        # Add Crop Overlay to scene
        self.crop_item = CropOverlayItem(QRectF(self.current_pixmap.rect()))
        self.scene.addItem(self.crop_item)
        self.crop_item.rect_changed.connect(self._update_crop_dimensions)
        self._change_crop_ratio()
        self._update_crop_dimensions()

        self.btn_crop.setText("✂ Quitter Recadrage")
        self.crop_panel.show()
        self._position_hud()
        self.crop_panel.raise_()
        self.fit_to_screen()
        self.view.setFocus()

    def _update_crop_dimensions(self, rect=None):
        if self.crop_item:
            left, top, right, bottom = self.crop_item.get_crop_box()
            self.crop_dimensions.setText(f'{right - left} × {bottom - top} px')

    def _change_crop_ratio(self, index=None):
        if not self.crop_item:
            return
        ratio = self.crop_ratio.currentData()
        if ratio == 'original':
            ratio = self.current_pixmap.width() / self.current_pixmap.height()
        self.crop_item.set_ratio(ratio)
        self.btn_ratio_flip.setEnabled(ratio is not None)
        self.view.setFocus()

    def _flip_crop_ratio(self):
        if self.crop_item and self.crop_item.ratio:
            ratio = 1 / self.crop_item.ratio
            index = self.crop_ratio.findData(ratio)
            if index < 0:
                self.crop_ratio.addItem(f'Ratio {ratio:.3f}', ratio)
                index = self.crop_ratio.count() - 1
            self.crop_ratio.setCurrentIndex(index)
            self.view.setFocus()

    def cancel_crop(self):
        if self.crop_item:
            self.scene.removeItem(self.crop_item)
            self.crop_item = None
        self.crop_mode = False
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.btn_crop.setText("✂ Recadrer")
        self.btn_crop_apply.hide()
        self.btn_crop_cancel.hide()
        self.crop_panel.hide()
        self.view.setViewportMargins(0, 0, 0, 0)
        self.fit_to_screen()
        self.view.setFocus()

    def apply_crop(self):
        if not self.crop_item or not self.image_list or self.current_index < 0:
            return

        crop_box = self.crop_item.get_crop_box()
        file_path = self.image_list[self.current_index]

        dlg = CropConfirmDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.choice:
            overwrite = (dlg.choice == "overwrite")
            try:
                saved_path = crop_image(file_path, crop_box, overwrite=overwrite,
                                        rotation_degrees=self.rotation_degrees)
                self.cancel_crop()
                if not overwrite:
                    # Add newly created file to image list and select it
                    self.image_list.insert(self.current_index + 1, str(saved_path))
                    self.current_index += 1
                self.load_current_image()
                self.image_modified.emit(str(saved_path))
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Impossible de recadrer l'image :\n{e}")

    def rotate_image(self, angle: int = -90):
        """Rotates the displayed image by angle degrees (-90 for Left, 90 for Right)."""
        if not self.current_pixmap or self.current_pixmap.isNull():
            return
        self.cancel_blur()
        self.cancel_crop()
        transform = QTransform().rotate(angle)
        self.current_pixmap = self.current_pixmap.transformed(
            transform, Qt.TransformationMode.SmoothTransformation
        )
        self.rotation_degrees = (self.rotation_degrees + angle) % 360
        self.scene.clear()
        self.pixmap_item = self.scene.addPixmap(self.current_pixmap)
        self.scene.setSceneRect(QRectF(self.current_pixmap.rect()))
        self.fit_to_screen()
        self.btn_save_rot.show()
        self._position_hud()

        # Update info label with new dimensions
        w = self.current_pixmap.width()
        h = self.current_pixmap.height()
        if self.image_list and 0 <= self.current_index < len(self.image_list):
            name = Path(self.image_list[self.current_index]).name
            idx_str = f"{self.current_index + 1}/{len(self.image_list)}"
            self.lbl_info.setText(f"{name}  ({w}×{h})  [{idx_str}] [Tournée]")

    def save_rotated_image(self):
        """Prompts to save or overwrite the rotated image."""
        if not self.image_list or self.current_index < 0 or not self.current_pixmap:
            return

        file_path = self.image_list[self.current_index]
        dlg = CropConfirmDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.choice:
            overwrite = (dlg.choice == "overwrite")
            try:
                if overwrite:
                    dest = Path(file_path)
                else:
                    from src.utils.file_ops import get_unique_destination_path
                    src_p = Path(file_path)
                    dest = get_unique_destination_path(src_p.parent, f"{src_p.stem}_rot{src_p.suffix}")

                crop_image(file_path, (0, 0, self.current_pixmap.width(), self.current_pixmap.height()),
                           destination_path=dest, overwrite=overwrite, rotation_degrees=self.rotation_degrees)
                if not overwrite:
                    self.image_list.insert(self.current_index + 1, str(dest))
                    self.current_index += 1

                self.btn_save_rot.hide()
                self.load_current_image()
                self.image_modified.emit(str(dest))
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Impossible d'enregistrer la rotation :\n{e}")

    def close_fullscreen(self):
        self.cancel_blur()
        self.cancel_crop()
        self.btn_save_rot.hide()
        self.hud.hide()
        self.hud_timer.stop()
        if self.floating:
            self.close()
        else:
            self.hide()
            self.viewer_closed.emit(self.image_list[self.current_index] if 0 <= self.current_index < len(self.image_list) else '')

    # Event handlers
    def closeEvent(self, event):
        if not self.floating:
            self.cancel_blur()
            self.cancel_crop()
            self.viewer_closed.emit(self.image_list[self.current_index] if 0 <= self.current_index < len(self.image_list) else '')
        super().closeEvent(event)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_F2:
            if not event.isAutoRepeat():
                self.rename_current_image()
            event.accept()
            return
        if key == Qt.Key.Key_M and not event.modifiers() and not self.floating:
            self.move_to_next_screen()
            return
        if event.matches(QKeySequence.StandardKey.Undo):
            self.undo_delete()
            return
        if key == Qt.Key.Key_F and not event.modifiers():
            self.start_blur()
            return
        if self.blur_item:
            if key == Qt.Key.Key_Escape:
                self.cancel_blur()
                return
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.apply_blur()
                return
        if key in (Qt.Key.Key_Home, Qt.Key.Key_End) and self.image_list:
            target = 0 if key == Qt.Key.Key_Home else len(self.image_list) - 1
            if target == self.current_index or not self._confirm_rotation():
                return
            self.current_index = target
            self.load_current_image()
            if key == Qt.Key.Key_End:
                self.show_message('Fin du répertoire')
            return
        if key == Qt.Key.Key_Delete:
            if not event.isAutoRepeat():
                self.delete_current_image(bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier))
            event.accept()
            return
        if key == Qt.Key.Key_B and not event.modifiers():
            if 0 <= self.current_index < len(self.image_list):
                self.floating_requested.emit(list(self.image_list), self.image_list[self.current_index])
            event.accept()
            return

        # Crop validation shortcut
        if self.crop_mode:
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.apply_crop()
                return
            elif key == Qt.Key.Key_Escape:
                self.cancel_crop()
                return
            elif key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
                step = 10 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1
                dx, dy = {Qt.Key.Key_Left: (-step, 0), Qt.Key.Key_Right: (step, 0),
                          Qt.Key.Key_Up: (0, -step), Qt.Key.Key_Down: (0, step)}[key]
                self.crop_item.nudge(dx, dy)
                return

        # General shortcuts
        if key == Qt.Key.Key_Escape:
            self.close_fullscreen()
        elif key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self.zoom_in()
        elif key in (Qt.Key.Key_Minus, Qt.Key.Key_Underscore):
            self.zoom_out()
        elif key in (Qt.Key.Key_0, Qt.Key.Key_Asterisk):
            self.fit_to_screen()
        elif key in (Qt.Key.Key_Left, Qt.Key.Key_Up, Qt.Key.Key_PageUp, Qt.Key.Key_Backspace):
            self.prev_image()
        elif key in (Qt.Key.Key_Right, Qt.Key.Key_Down, Qt.Key.Key_PageDown, Qt.Key.Key_Space):
            self.next_image()
        elif key == Qt.Key.Key_L:
            # 90° rotation requested by user (Counter-clockwise / Left)
            self.rotate_image(-90)
        elif key == Qt.Key.Key_R:
            # 90° rotation clockwise
            self.rotate_image(90)
        elif key in (Qt.Key.Key_C, Qt.Key.Key_X):
            self.toggle_crop_mode()
        elif (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and key == Qt.Key.Key_S:
            self.save_rotated_image()
        else:
            super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if not self.crop_mode and not self.blur_item:
                self.close_fullscreen()
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if delta > 0:
                self.zoom_in()
            elif delta < 0:
                self.zoom_out()
        else:
            self._wheel_remainder += delta or event.pixelDelta().y() * 3
            while abs(self._wheel_remainder) >= 120:
                if self._wheel_remainder > 0:
                    self.prev_image()
                    self._wheel_remainder -= 120
                else:
                    self.next_image()
                    self._wheel_remainder += 120
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        super().mouseMoveEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_hud()
        self._position_zoom_badge()
        if self.floating and self.current_pixmap:
            self.fit_to_screen()

    def enterEvent(self, event):
        super().enterEvent(event)
        if self.floating:
            for control in (self.floating_close, self.move_handle, self.size_grip):
                control.show()
                control.raise_()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        if self.floating:
            for control in (self.floating_close, self.move_handle, self.size_grip):
                control.hide()
            self.hud.hide()

    def _position_hud(self):
        if not hasattr(self, 'hud'):
            return
        hud_w = self.hud.sizeHint().width()
        hud_h = self.hud.sizeHint().height()
        x = (self.width() - hud_w) // 2
        y = self.height() - hud_h - 24
        self.hud.setGeometry(x, y, hud_w, hud_h)
        if hasattr(self, 'blur_panel'):
            self.blur_panel.adjustSize()
            self.blur_panel.move(max(0, (self.width() - self.blur_panel.width()) // 2), self.height() - self.blur_panel.height() - 20)
        if self.floating and hasattr(self, 'size_grip'):
            self.size_grip.move(self.width() - 20, self.height() - 20)
            self.size_grip.raise_()
            self.move_handle.move(max(0, (self.width() - 26) // 2), 4)
            self.floating_close.move(self.width() - 28, 4)
            self.move_handle.raise_()
            self.floating_close.raise_()
        if hasattr(self, 'crop_panel'):
            panel_w = min(self.width() - 32, self.crop_panel.sizeHint().width())
            panel_h = self.crop_panel.sizeHint().height()
            panel_y = y - panel_h - 12 if self.hud.isVisible() else self.height() - panel_h - 24
            self.crop_panel.setGeometry(max(16, (self.width() - panel_w) // 2),
                                        max(20, panel_y), panel_w, panel_h)
            if self.crop_mode:
                self.view.setViewportMargins(0, 0, 0, self.height() - max(20, panel_y) + 16)

    def _show_hud(self):
        if self.floating and self.width() < self.hud.sizeHint().width() + 20:
            # Keep every control accessible in small borderless image windows.
            from PyQt6.QtWidgets import QMenu
            menu = QMenu(self)
            menu.addAction("Afficher dans l'explorateur Windows").triggered.connect(self.reveal_current_image)
            for label, action in [('Précédente ←', self.prev_image), ('Suivante →', self.next_image),
                                  ('Zoom +', self.zoom_in), ('Zoom −', self.zoom_out),
                                  ('Ajuster (0)', self.fit_to_screen), ('Recadrer (X)', self.toggle_crop_mode),
                                  ('Fermer (Échap)', self.close_fullscreen)]:
                menu.addAction(label).triggered.connect(action)
            from PyQt6.QtGui import QCursor
            menu.exec(QCursor.pos())
            return
        self.hud.show()
        self._position_hud()
        self.hud.raise_()
        if self.crop_mode:
            self.fit_to_screen()
        self.hud_timer.start()

    def _fade_out_hud(self):
        # Only hide if crop mode is not active and mouse is not inside HUD
        if not self.crop_mode and not self.hud.underMouse():
            self.hud.hide()
            self.hud_timer.stop()
