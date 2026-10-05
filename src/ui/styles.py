"""Windows 11 Fluent Theme stylesheets for XNViewTab (Dark & Light)."""

DARK_THEME = """
/* Global Window & Font */
QWidget {
    background-color: #202020;
    color: #f3f3f3;
    font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;
    font-size: 13px;
    selection-background-color: #0078d4;
    selection-color: #ffffff;
}

/* Main Window */
QMainWindow {
    background-color: #1a1a1a;
}

/* ToolBar & Navigation Bar */
QToolBar {
    background-color: #262626;
    border-bottom: 1px solid #333333;
    spacing: 6px;
    padding: 4px 8px;
}

/* QTabBar - Windows 11 Style */
QTabWidget::pane {
    border: none;
    background-color: #202020;
}

QTabBar {
    background-color: #181818;
    qproperty-drawBase: 0;
    margin-top: 4px;
    padding-left: 6px;
}

QTabBar::tab {
    background-color: #222222;
    color: #cccccc;
    border: 1px solid #303030;
    border-bottom: none;
    border-top-left-radius: 7px;
    border-top-right-radius: 7px;
    padding: 7px 16px;
    margin-right: 3px;
    min-width: 100px;
    max-width: 220px;
}

QTabBar::tab:hover {
    background-color: #2c2c2c;
    color: #ffffff;
}

QTabBar::tab:selected {
    background-color: #2a2a2a;
    color: #ffffff;
    border-color: #3d3d3d;
    border-bottom: 2px solid #0078d4;
}

QTabBar::close-button {
    image: none;
    subcontrol-position: right;
    margin-left: 6px;
    padding: 2px;
    border-radius: 4px;
}

QTabBar::close-button:hover {
    background-color: #e81123;
    color: white;
}

/* Push Buttons */
QPushButton {
    background-color: #2e2e2e;
    border: 1px solid #3d3d3d;
    border-radius: 5px;
    color: #ffffff;
    padding: 5px 12px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #383838;
    border-color: #4a4a4a;
}

QPushButton:pressed {
    background-color: #252525;
    border-color: #0078d4;
}

QPushButton:disabled {
    background-color: #222222;
    color: #666666;
    border-color: #2a2a2a;
}

/* Line Edit (Address bar / Search) */
QLineEdit {
    background-color: #2a2a2a;
    border: 1px solid #383838;
    border-radius: 5px;
    padding: 5px 10px;
    color: #ffffff;
}

QLineEdit:focus {
    border: 1px solid #0078d4;
    background-color: #2e2e2e;
}

/* Thumbnail Grid / ListWidget */
QListWidget {
    background-color: #202020;
    border: none;
    outline: none;
    padding: 8px;
}

QListWidget::item {
    background-color: #282828;
    border: 1px solid transparent;
    border-radius: 8px;
    margin: 4px;
    padding: 6px;
    color: #e0e0e0;
}

QListWidget::item:hover {
    background-color: #333333;
    border-color: #444444;
}

QListWidget::item:selected {
    background-color: #1f3d5c;
    border: 1px solid #0078d4;
    color: #ffffff;
}

/* Tree View & Favorites (Folder Tree) */
QTreeView, QListWidget#favoritesList {
    background-color: #1d1d1d;
    border: none;
    border-right: 1px solid #2e2e2e;
    color: #cccccc;
    outline: none;
    padding: 4px;
}

QTreeView::item {
    padding: 5px 8px;
    border-radius: 4px;
}

QListWidget#favoritesList::item {
    padding: 2px 6px;
    margin: 1px 2px;
    border-radius: 4px;
    font-size: 12px;
}

QTreeView::item:hover, QListWidget#favoritesList::item:hover {
    background-color: #2a2a2a;
    color: #ffffff;
}

QTreeView::item:selected, QListWidget#favoritesList::item:selected {
    background-color: #0078d4;
    color: #ffffff;
}

/* Splitter */
QSplitter::handle {
    background-color: #2b2b2b;
}

QSplitter::handle:hover {
    background-color: #0078d4;
}

/* ScrollBar - Modern slim */
QScrollBar:vertical {
    background-color: transparent;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #3e3e3e;
    min-height: 24px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #555555;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: transparent;
    height: 10px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #3e3e3e;
    min-width: 24px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #555555;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Status Bar */
QStatusBar {
    background-color: #1c1c1c;
    border-top: 1px solid #2d2d2d;
    color: #888888;
    font-size: 12px;
}

/* Slider (Thumbnail Size Zoom) */
QSlider::groove:horizontal {
    height: 4px;
    background: #3a3a3a;
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background: #0078d4;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    border: 2px solid #0078d4;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background: #0078d4;
    border-color: #ffffff;
}

/* Menu */
QMenu {
    background-color: #252525;
    border: 1px solid #383838;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 24px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #0078d4;
    color: white;
}
"""

LIGHT_THEME = """
/* Global Window & Font */
QWidget {
    background-color: #f3f3f3;
    color: #1a1a1a;
    font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;
    font-size: 13px;
    selection-background-color: #0078d4;
    selection-color: #ffffff;
}

/* Main Window */
QMainWindow {
    background-color: #f0f0f0;
}

/* ToolBar & Navigation Bar */
QToolBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e0e0e0;
    spacing: 6px;
    padding: 4px 8px;
}

/* QTabBar - Windows 11 Light Style */
QTabWidget::pane {
    border: none;
    background-color: #f8f8f8;
}

QTabBar {
    background-color: #e8e8e8;
    qproperty-drawBase: 0;
    margin-top: 4px;
    padding-left: 6px;
}

QTabBar::tab {
    background-color: #eeeeee;
    color: #444444;
    border: 1px solid #d5d5d5;
    border-bottom: none;
    border-top-left-radius: 7px;
    border-top-right-radius: 7px;
    padding: 7px 16px;
    margin-right: 3px;
    min-width: 100px;
    max-width: 220px;
}

QTabBar::tab:hover {
    background-color: #fbfbfb;
    color: #111111;
}

QTabBar::tab:selected {
    background-color: #f8f8f8;
    color: #000000;
    border-color: #cccccc;
    border-bottom: 2px solid #0078d4;
}

QTabBar::close-button {
    image: none;
    subcontrol-position: right;
    margin-left: 6px;
    padding: 2px;
    border-radius: 4px;
}

QTabBar::close-button:hover {
    background-color: #e81123;
    color: white;
}

/* Push Buttons */
QPushButton {
    background-color: #ffffff;
    border: 1px solid #d0d0d0;
    border-radius: 5px;
    color: #1a1a1a;
    padding: 5px 12px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #f4f4f4;
    border-color: #b0b0b0;
}

QPushButton:pressed {
    background-color: #e8e8e8;
    border-color: #0078d4;
}

QPushButton:disabled {
    background-color: #f9f9f9;
    color: #999999;
    border-color: #e0e0e0;
}

/* Line Edit (Address bar / Search) */
QLineEdit {
    background-color: #ffffff;
    border: 1px solid #d0d0d0;
    border-radius: 5px;
    padding: 5px 10px;
    color: #1a1a1a;
}

QLineEdit:focus {
    border: 1px solid #0078d4;
    background-color: #ffffff;
}

/* Thumbnail Grid / ListWidget */
QListWidget {
    background-color: #ffffff;
    border: none;
    outline: none;
    padding: 8px;
}

QListWidget::item {
    background-color: #f5f6f8;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    margin: 4px;
    padding: 6px;
    color: #1f2937;
}

QListWidget::item:hover {
    background-color: #eef2f7;
    border-color: #cbd5e1;
}

QListWidget::item:selected {
    background-color: #dbeafe;
    border: 1px solid #0078d4;
    color: #0f172a;
}

/* Tree View & Favorites (Folder Tree) */
QTreeView, QListWidget#favoritesList {
    background-color: #f8f8f8;
    border: none;
    border-right: 1px solid #e0e0e0;
    color: #222222;
    outline: none;
    padding: 4px;
}

QTreeView::item {
    padding: 5px 8px;
    border-radius: 4px;
}

QListWidget#favoritesList::item {
    padding: 2px 6px;
    margin: 1px 2px;
    border-radius: 4px;
    font-size: 12px;
}

QTreeView::item:hover, QListWidget#favoritesList::item:hover {
    background-color: #e9e9e9;
    color: #000000;
}

QTreeView::item:selected, QListWidget#favoritesList::item:selected {
    background-color: #0078d4;
    color: #ffffff;
}

/* Splitter */
QSplitter::handle {
    background-color: #dedede;
}

QSplitter::handle:hover {
    background-color: #0078d4;
}

/* ScrollBar - Modern slim light */
QScrollBar:vertical {
    background-color: transparent;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #cccccc;
    min-height: 24px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #aaaaaa;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: transparent;
    height: 10px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #cccccc;
    min-width: 24px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #aaaaaa;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Status Bar */
QStatusBar {
    background-color: #ebebeb;
    border-top: 1px solid #dedede;
    color: #555555;
    font-size: 12px;
}

/* Slider (Thumbnail Size Zoom) */
QSlider::groove:horizontal {
    height: 4px;
    background: #d0d0d0;
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background: #0078d4;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    border: 2px solid #0078d4;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background: #0078d4;
    border-color: #ffffff;
}

/* Menu */
QMenu {
    background-color: #ffffff;
    border: 1px solid #d5d5d5;
    border-radius: 6px;
    padding: 4px;
    color: #1a1a1a;
}

QMenu::item {
    padding: 6px 24px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #0078d4;
    color: white;
}
"""


def get_theme_stylesheet(theme_name: str) -> str:
    """Returns the CSS stylesheet according to the requested theme name."""
    if theme_name == "light":
        return LIGHT_THEME
    return DARK_THEME
