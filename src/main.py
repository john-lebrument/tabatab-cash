import sys
from pathlib import Path
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from src.config import ConfigManager
from src.ui.main_window import MainWindow
from src.version import APP_NAME
from src.utils.instance_broker import InstanceBroker, launch_arguments


def get_resource_path(rel_path: str) -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parent.parent
    return base / rel_path


def main():
    # Enable High DPI Scaling
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    path, force_new = launch_arguments(sys.argv[1:])
    broker = InstanceBroker(app)
    if not broker.start(path, force_new):
        return
    app.aboutToQuit.connect(broker.close)
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('TABaTABCash.Viewer')

    # Set Application Icon
    icon_path = get_resource_path("resources/app_icon.png")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    config = ConfigManager()
    window = MainWindow(config)
    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()
    def open_image(image):
        viewer = window.fullscreen_viewer
        if viewer and viewer.isVisible() and not viewer._confirm_rotation():
            return
        window.open_external_image(image)
        target = window.fullscreen_viewer or window
        if target.isMinimized():
            target.showNormal()
            if target is window.fullscreen_viewer:
                target.showFullScreen()
        target.raise_()
        target.activateWindow()

    broker.image_requested.connect(open_image)
    if path:
        QTimer.singleShot(0, lambda: open_image(path))

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
