from collections import OrderedDict
from pathlib import Path
from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QImage, QPixmap
from PIL import Image, ImageOps
from src.utils.file_ops import is_video_file


class ImageLoaderSignals(QObject):
    thumbnail_ready = pyqtSignal(str, QImage, int, int, int)
    error = pyqtSignal(str, int, str)


class ThumbnailWorker(QRunnable):
    """Background worker to generate a thumbnail for a single image."""

    def __init__(self, file_path: str, target_size: int, signals: ImageLoaderSignals):
        super().__init__()
        self.file_path = file_path
        self.target_size = target_size
        self.signals = signals

    @pyqtSlot()
    def run(self):
        try:
            with Image.open(self.file_path) as img:
                orig_w, orig_h = img.size
                # Fast transpose based on EXIF
                img.draft("RGB", (self.target_size, self.target_size))
                img = ImageOps.exif_transpose(img)
                img.thumbnail((self.target_size, self.target_size), Image.Resampling.LANCZOS)
                # Pillow.thumbnail does not enlarge small originals.
                factor = self.target_size / max(img.size)
                if factor > 1:
                    img = img.resize((max(1, round(img.width * factor)),
                                      max(1, round(img.height * factor))), Image.Resampling.LANCZOS)
                
                # Convert to RGBA
                if img.mode != "RGBA":
                    img = img.convert("RGBA")

                data = img.tobytes("raw", "RGBA")
                qimage = QImage(data, img.width, img.height, QImage.Format.Format_RGBA8888).copy()
                self.signals.thumbnail_ready.emit(self.file_path, qimage, self.target_size, orig_w, orig_h)
        except Exception as e:
            # Emits error or fallback
            self.signals.error.emit(self.file_path, self.target_size, str(e))


class ThumbnailCache:
    """Thread-safe LRU cache for pixmaps."""

    def __init__(self, max_items: int = 1500):
        self.max_items = max_items
        self._cache = OrderedDict()

    def get(self, key: str) -> QPixmap | None:
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def put(self, key: str, pixmap: QPixmap):
        self._cache[key] = pixmap
        if len(self._cache) > self.max_items:
            self._cache.popitem(last=False)

    def clear(self):
        self._cache.clear()

    def invalidate(self, file_path):
        prefix = f'{file_path}_'
        for key in list(self._cache):
            if key.startswith(prefix):
                del self._cache[key]


class ThumbnailManager(QObject):
    """Manages parallel generation of thumbnails using QThreadPool."""

    thumbnail_ready = pyqtSignal(str, QPixmap, int, int, int)

    def __init__(self, max_threads: int = 6):
        super().__init__()
        self.pool = QThreadPool.globalInstance()
        self.pool.setMaxThreadCount(max_threads)
        self.signals = ImageLoaderSignals()
        self.cache = ThumbnailCache()
        self.pending_tasks: set[str] = set()
        self.video_failures = set()
        self.video_loader = None

        self.signals.thumbnail_ready.connect(self._on_thumbnail_ready)
        self.signals.error.connect(self._on_thumbnail_error)

    def get_thumbnail(self, file_path: str, size: int) -> QPixmap | None:
        cache_key = f"{file_path}_{size}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        if is_video_file(file_path):
            if cache_key not in self.pending_tasks and cache_key not in self.video_failures:
                if self.video_loader is None:
                    from src.utils.video_thumbnail import VideoThumbnails
                    self.video_loader = VideoThumbnails(self)
                    self.video_loader.ready.connect(lambda path, image, size: self._on_thumbnail_ready(path, image, size, image.width(), image.height()))
                    self.video_loader.failed.connect(self._video_failed)
                self.pending_tasks.add(cache_key)
                self.video_loader.request(file_path, size)
            return None

        # Enqueue background generation if not already processing
        if cache_key not in self.pending_tasks:
            self.pending_tasks.add(cache_key)
            worker = ThumbnailWorker(file_path, size, self.signals)
            self.pool.start(worker)

        return None

    def _video_failed(self, path, size):
        key = f'{path}_{size}'
        self.pending_tasks.discard(key)
        self.video_failures.add(key)

    def _on_thumbnail_ready(self, file_path: str, image: QImage, size: int, orig_w: int, orig_h: int):
        # QPixmap belongs to the GUI thread; workers produce owned QImages only.
        pixmap = QPixmap.fromImage(image)
        cache_key = f"{file_path}_{size}"
        self.cache.put(cache_key, pixmap)
        self.pending_tasks.discard(cache_key)
        self.thumbnail_ready.emit(file_path, pixmap, size, orig_w, orig_h)

    def _on_thumbnail_error(self, file_path: str, size: int, error_msg: str):
        self.pending_tasks.discard(f"{file_path}_{size}")
