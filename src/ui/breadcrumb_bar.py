from pathlib import Path
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QStackedWidget, QLineEdit, QScrollArea, QToolButton, QMenu, QLabel, QSizePolicy


class PathEdit(QLineEdit):
    cancelled = pyqtSignal()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
        else:
            super().keyPressEvent(event)


class BreadcrumbBar(QWidget):
    navigate_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.buttons = []
        self.path = ''
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget(self)
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setFixedHeight(34)
        self.crumbs = QWidget()
        self.crumb_layout = QHBoxLayout(self.crumbs)
        self.crumb_layout.setContentsMargins(2, 0, 2, 0)
        self.crumb_layout.setSpacing(2)
        self.scroll.setWidget(self.crumbs)
        self.stack.addWidget(self.scroll)
        self.edit = PathEdit(self)
        self.edit.cancelled.connect(self.finish_edit)
        self.stack.addWidget(self.edit)
        self.ancestors = QToolButton(self)
        self.ancestors.setText('…')
        self.ancestors.setToolTip('Tous les dossiers du chemin')
        self.ancestors.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        layout.addWidget(self.ancestors)
        layout.addWidget(self.stack, 1)
        edit_button = QToolButton(self)
        edit_button.setText('Chemin')
        edit_button.setToolTip('Saisir ou copier le chemin (Alt+D)')
        edit_button.clicked.connect(self.start_edit)
        layout.addWidget(edit_button)
        shortcut = QShortcut(QKeySequence('Alt+D'), self)
        shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        # Attach to the tab, so Alt+D also works from the thumbnail grid.
        shortcut.setParent(parent or self)
        shortcut.activated.connect(self.start_edit)

    def set_path(self, path):
        self.path = str(path)
        self.edit.setText(self.path)
        while self.crumb_layout.count():
            item = self.crumb_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.buttons.clear()
        old_menu = self.ancestors.menu()
        menu = QMenu(self.ancestors)
        current = Path(path)
        for ancestor in [*reversed(current.parents), current]:
            value = str(ancestor)
            button = QToolButton(self.crumbs)
            button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
            button.setText(ancestor.name or ancestor.anchor)
            button.ensurePolished()
            button.setFixedWidth(button.fontMetrics().horizontalAdvance(button.text()) + 24)
            button.setToolTip(value)
            button.clicked.connect(lambda checked=False, p=value: self.navigate_requested.emit(p))
            menu.addAction(value).triggered.connect(lambda checked=False, p=value: self.navigate_requested.emit(p))
            if self.buttons:
                self.crumb_layout.addWidget(QLabel('›', self.crumbs))
            self.crumb_layout.addWidget(button)
            self.buttons.append(button)
        self.crumb_layout.addStretch()
        self.crumbs.setMinimumWidth(sum(button.width() for button in self.buttons) + 20 * len(self.buttons))
        self.ancestors.setMenu(menu)
        if old_menu:
            old_menu.deleteLater()
        self.stack.setCurrentWidget(self.scroll)
        QTimer.singleShot(0, self._reveal_current)

    def _reveal_current(self):
        if self.buttons:
            self.scroll.ensureWidgetVisible(self.buttons[-1])

    def start_edit(self):
        self.stack.setCurrentWidget(self.edit)
        self.edit.setFocus()
        self.edit.selectAll()

    def finish_edit(self):
        self.edit.setText(self.path)
        self.stack.setCurrentWidget(self.scroll)
