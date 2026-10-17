"""Upload a small, metadata-free preview directly to the two search engines."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

from PIL import Image, ImageOps
from PyQt6.QtCore import QObject, QRunnable, QThreadPool, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QApplication, QMessageBox

from src.utils.file_ops import is_image_file
from src.utils.browser_upload import google_browser_upload, close_browser_uploads


USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
              'AppleWebKit/537.36 (KHTML, like Gecko) '
              'Chrome/130.0.0.0 Safari/537.36')
ENGINES = ('Yandex', 'Google Lens')


def image_preview(path):
    """Normalize HEIC, orientation and transparency without editing the original."""
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source)
        image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        rgba = image.convert('RGBA')
        preview = Image.new('RGB', rgba.size, 'white')
        preview.paste(rgba, mask=rgba.getchannel('A'))
        stream = BytesIO()
        preview.save(stream, format='JPEG', quality=90)
        return stream.getvalue()


def upload_image(engine, preview):
    """Yandex results URL or a browser-side upload page for Google Lens."""
    if engine == 'Google Lens':
        return google_browser_upload(preview)
    boundary = 'TABaTAB' + uuid4().hex
    if engine == 'Yandex':
        field = 'upfile'
        url = 'https://yandex.com/images/touch/search?' + urlencode({
            'rpt': 'imageview', 'format': 'json',
            'request': json.dumps({'blocks': [{'block': 'cbir-uploader__get-cbir-id'}]}),
        })
    else:
        raise ValueError('Moteur de recherche inconnu.')
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; '
            'filename="image.jpg"\r\nContent-Type: image/jpeg\r\n\r\n').encode()
    body += preview + f'\r\n--{boundary}--\r\n'.encode()
    request = Request(url, data=body, headers={
        'Content-Type': f'multipart/form-data; boundary={boundary}',
        'User-Agent': USER_AGENT,
    })
    with urlopen(request, timeout=30) as response:
        if engine == 'Yandex':
            data = json.loads(response.read(2 * 1024 * 1024))
            params = data['blocks'][0]['params']
            if not params.get('cbirId'):
                raise ValueError('Yandex n’a pas retourné de résultats pour cette image.')
            return 'https://yandex.com/images/search?' + urlencode({
                'rpt': 'imageview', 'cbir_id': params['cbirId'],
                'url': params.get('originalImageUrl', ''),
            })


class SearchSignals(QObject):
    result = pyqtSignal(str, str, str)  # engine, URL, error
    finished = pyqtSignal(str)


class ImageSearchJob(QRunnable):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.signals = SearchSignals()

    def run(self):
        try:
            preview = image_preview(self.path)
            # A failure or slow response from one engine does not block the other.
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = {executor.submit(upload_image, engine, preview): engine for engine in ENGINES}
                for future in as_completed(futures):
                    engine = futures[future]
                    try:
                        self.signals.result.emit(engine, future.result(), '')
                    except Exception as error:
                        self.signals.result.emit(engine, '', str(error))
        except Exception as error:
            self.signals.result.emit('Yandex et Google Lens', '', str(error))
        finally:
            self.signals.finished.emit(self.path)


class ImageSearchController(QObject):
    """Keep jobs alive even when the originating viewer closes."""
    def __init__(self, parent):
        super().__init__(parent)
        self.jobs = {}
        self.errors = []
        self.dialog = None
        parent.aboutToQuit.connect(close_browser_uploads)

    def start(self, path):
        path = str(Path(path).absolute())
        if path in self.jobs or not is_image_file(path):
            return
        job = ImageSearchJob(path)
        self.jobs[path] = job
        job.signals.result.connect(self._result)
        job.signals.finished.connect(self._finished)
        QThreadPool.globalInstance().start(job)

    def _result(self, engine, url, error):
        if not error and not QDesktopServices.openUrl(QUrl(url)):
            error = 'Impossible d’ouvrir le navigateur par défaut.'
        if error:
            self.errors.append(f'{engine} : {error}')

    def _finished(self, path):
        self.jobs.pop(path, None)
        if not self.jobs and self.errors:
            if self.dialog is None:
                self.dialog = QMessageBox(QMessageBox.Icon.Warning, 'Recherche d’images similaires',
                                          '\n'.join(self.errors))
                self.dialog.finished.connect(self._dismiss_error)
                self.dialog.show()
            else:
                self.dialog.setText(self.dialog.text() + '\n' + '\n'.join(self.errors))
            self.errors.clear()

    def _dismiss_error(self):
        self.dialog.deleteLater()
        self.dialog = None


def search_similar_images(path):
    app = QApplication.instance()
    controller = getattr(app, '_image_search_controller', None)
    if controller is None:
        controller = app._image_search_controller = ImageSearchController(app)
    controller.start(path)
