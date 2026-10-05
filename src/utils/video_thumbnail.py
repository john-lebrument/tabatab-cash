"""Serial, silent video previews; actual playback belongs to the OS default app."""
from collections import deque
from PyQt6.QtCore import QObject, QTimer, QUrl, Qt, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer, QVideoSink


class VideoThumbnails(QObject):
    ready = pyqtSignal(str, object, int)
    failed = pyqtSignal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.queue = deque()
        self.current = None
        self.player = QMediaPlayer(self)
        self.sink = QVideoSink(self)
        self.player.setVideoSink(self.sink)
        self.sink.videoFrameChanged.connect(self._frame)
        self.player.errorOccurred.connect(self._error)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(6000)
        self.timer.timeout.connect(self._error)

    def request(self, path, size):
        self.queue.append((path, size))
        if self.current is None:
            self._next()

    def _next(self):
        if self.current is not None or not self.queue:
            return
        self.current = self.queue.popleft()
        self.timer.start()
        self.player.setSource(QUrl.fromLocalFile(self.current[0]))
        self.player.play()

    def _frame(self, frame):
        if self.current is None or not frame.isValid():
            return
        image = frame.toImage()
        if image.isNull():
            return
        path, size = self.current
        image = image.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self._finish()
        self.ready.emit(path, image, size)

    def _error(self, *args):
        if self.current is not None:
            path, size = self.current
            self._finish()
            self.failed.emit(path, size)

    def _finish(self):
        self.current = None
        self.timer.stop()
        self.player.stop()
        QTimer.singleShot(0, self._next)
