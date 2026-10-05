"""Interactive multi-zone elliptical blur and atomic image saving."""
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps
from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPen
from PyQt6.QtWidgets import QGraphicsObject

from src.utils.file_ops import get_unique_destination_path


def blurred_regions(image, boxes, strength):
    """Return a copy with an elliptical blur applied inside every box."""
    result = image.copy()
    for box in boxes:
        left, top, right, bottom = box
        if right <= left or bottom <= top or not strength:
            continue
        region = result.crop(box)
        radius = max(0.1, min(region.size) * strength / 200)
        blurred = region.filter(ImageFilter.GaussianBlur(radius))
        mask = Image.new('L', region.size, 0)
        ImageDraw.Draw(mask).ellipse((0, 0, region.width - 1, region.height - 1), fill=255)
        result.paste(blurred, (left, top), mask)
    return result


def blurred_region(image, box, strength):
    """Compatibility helper for callers applying one elliptical zone."""
    return blurred_regions(image, [box], strength)


def save_blurs(path, boxes, strength, overwrite=False, rotation=0):
    src = Path(path)
    dest = src if overwrite else get_unique_destination_path(src.parent, f'{src.stem}_flou{src.suffix}')
    with Image.open(src) as source:
        fmt = source.format
        image = ImageOps.exif_transpose(source).convert('RGBA' if 'A' in source.getbands() else 'RGB')
        if rotation:
            image = image.rotate(-rotation, expand=True)
        result = blurred_regions(image, boxes, strength)
        if fmt == 'JPEG':
            result = result.convert('RGB')
        kwargs = {'quality': 95, 'subsampling': 0} if fmt == 'JPEG' else {}
        if source.info.get('icc_profile'):
            kwargs['icc_profile'] = source.info['icc_profile']
    with tempfile.NamedTemporaryFile(dir=dest.parent, suffix=dest.suffix, delete=False) as temporary:
        temp = Path(temporary.name)
    try:
        result.save(temp, format=fmt, **kwargs)
        temp.replace(dest)
    finally:
        temp.unlink(missing_ok=True)
    return dest


def save_blur(path, box, strength, overwrite=False, rotation=0):
    return save_blurs(path, [box], strength, overwrite, rotation)


class BlurSelection(QGraphicsObject):
    """Draw any number of ellipse bounds; starts with no proposed selection."""
    rect_changed = pyqtSignal(QRectF)

    def __init__(self, bounds: QRectF, parent=None):
        super().__init__(parent)
        self.bounds = QRectF(bounds)
        self.rects = []
        self._active = QRectF()
        self._origin = QPointF()
        self._drawing = False
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setZValue(10)

    def boundingRect(self):
        return QRectF(self.bounds)

    def _bounded(self, point):
        return QPointF(max(self.bounds.left(), min(self.bounds.right(), point.x())),
                       max(self.bounds.top(), min(self.bounds.bottom(), point.y())))

    def mousePressEvent(self, event):
        self._origin = self._bounded(event.pos())
        self._active = QRectF(self._origin, self._origin)
        self._drawing = True
        self.update()
        event.accept()

    def mouseMoveEvent(self, event):
        if self._drawing:
            self._active = QRectF(self._origin, self._bounded(event.pos())).normalized().intersected(self.bounds)
            self.update()
            self.rect_changed.emit(QRectF(self._active))
        event.accept()

    def mouseReleaseEvent(self, event):
        if self._drawing:
            self._active = QRectF(self._origin, self._bounded(event.pos())).normalized().intersected(self.bounds)
            if self._active.width() >= 2 and self._active.height() >= 2:
                self.rects.append(QRectF(self._active))
            self._active = QRectF()
            self._drawing = False
            self.update()
            self.rect_changed.emit(QRectF())
        event.accept()

    def paint(self, painter, option, widget=None):
        painter.save()
        pen = QPen(QColor('#00bfff'), 2)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for rect in self.rects:
            painter.drawEllipse(rect)
        if not self._active.isEmpty():
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawEllipse(self._active)
        painter.restore()

    def setRect(self, rect):
        """Programmatic selection used by accessibility helpers and tests."""
        normalized = QRectF(rect).normalized().intersected(self.bounds)
        if normalized.width() >= 1 and normalized.height() >= 1:
            if self.rects:
                self.rects[-1] = normalized
            else:
                self.rects.append(normalized)
            self.update()
            self.rect_changed.emit(QRectF(normalized))

    def addRect(self, rect):
        normalized = QRectF(rect).normalized().intersected(self.bounds)
        if normalized.width() >= 1 and normalized.height() >= 1:
            self.rects.append(normalized)
            self.update()
            self.rect_changed.emit(QRectF(normalized))

    def get_boxes(self):
        boxes = []
        for rect in self.rects:
            left = max(int(self.bounds.left()), round(rect.left()))
            top = max(int(self.bounds.top()), round(rect.top()))
            right = min(int(self.bounds.right()), round(rect.right()))
            bottom = min(int(self.bounds.bottom()), round(rect.bottom()))
            if right > left and bottom > top:
                boxes.append((left, top, right, bottom))
        return boxes

    def get_preview_boxes(self):
        boxes = self.get_boxes()
        if not self._active.isEmpty():
            rect = self._active
            boxes.append((round(rect.left()), round(rect.top()),
                          round(rect.right()), round(rect.bottom())))
        return boxes

    def get_crop_box(self):
        boxes = self.get_boxes()
        return boxes[-1] if boxes else None

    def remove_last(self):
        if self.rects:
            self.rects.pop()
            self.update()
            self.rect_changed.emit(QRectF())

    def clear(self):
        self.rects.clear()
        self._active = QRectF()
        self.update()
        self.rect_changed.emit(QRectF())
