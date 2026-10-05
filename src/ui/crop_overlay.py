"""Crop selection in image pixels, with screen-sized handles and ratio constraints."""
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QColor, QPen, QPainterPath
from PyQt6.QtWidgets import QGraphicsObject

HANDLE_NONE = 0
HANDLE_TOP_LEFT = 1
HANDLE_TOP = 2
HANDLE_TOP_RIGHT = 3
HANDLE_RIGHT = 4
HANDLE_BOTTOM_RIGHT = 5
HANDLE_BOTTOM = 6
HANDLE_BOTTOM_LEFT = 7
HANDLE_LEFT = 8
HANDLE_INSIDE = 9
HANDLE_NEW = 10


class CropOverlayItem(QGraphicsObject):
    rect_changed = pyqtSignal(QRectF)

    def __init__(self, bounds: QRectF, parent=None):
        super().__init__(parent)
        self.bounds = QRectF(bounds)
        self._rect = QRectF()
        self.ratio = None
        self.active_handle = HANDLE_NONE
        self.drag_start_pos = QPointF()
        self.rect_at_drag_start = QRectF()
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setZValue(10)
        self.reset_selection()

    def boundingRect(self):
        # Covers the shaded area too, so clicking outside starts a new selection.
        return QRectF(self.bounds)

    def rect(self):
        return QRectF(self._rect)

    def setRect(self, rect):
        r = rect.normalized().intersected(self.bounds)
        if r.width() < 1 or r.height() < 1:
            return
        self._rect = r
        self.update()
        self.rect_changed.emit(self.rect())

    def reset_selection(self):
        self.setRect(self.bounds.adjusted(self.bounds.width() * .1, self.bounds.height() * .1,
                                          -self.bounds.width() * .1, -self.bounds.height() * .1)
                     if min(self.bounds.width(), self.bounds.height()) >= 2 else self.bounds)
        if self.ratio:
            self.set_ratio(self.ratio)

    def set_ratio(self, ratio):
        self.ratio = float(ratio) if ratio and ratio > 0 else None
        if not self.ratio:
            return
        r = self.rect()
        width = min(r.width(), r.height() * self.ratio)
        height = width / self.ratio
        # If a tiny image cannot support this ratio, retain a valid selection.
        if min(width, height) < 1:
            return
        self.setRect(QRectF(r.center().x() - width / 2, r.center().y() - height / 2, width, height))

    def _scale(self):
        views = self.scene().views() if self.scene() else []
        return max(.001, abs(views[0].transform().m11())) if views else 1.0

    def get_handle_rects(self):
        r = self.rect()
        size = 10 / self._scale()
        centers = {
            HANDLE_TOP_LEFT: r.topLeft(), HANDLE_TOP: QPointF(r.center().x(), r.top()),
            HANDLE_TOP_RIGHT: r.topRight(), HANDLE_RIGHT: QPointF(r.right(), r.center().y()),
            HANDLE_BOTTOM_RIGHT: r.bottomRight(), HANDLE_BOTTOM: QPointF(r.center().x(), r.bottom()),
            HANDLE_BOTTOM_LEFT: r.bottomLeft(), HANDLE_LEFT: QPointF(r.left(), r.center().y()),
        }
        return {key: QRectF(p.x() - size / 2, p.y() - size / 2, size, size)
                for key, p in centers.items()}

    def hit_test_handle(self, pos):
        tolerance = 3 / self._scale()
        for handle, r in self.get_handle_rects().items():
            if r.adjusted(-tolerance, -tolerance, tolerance, tolerance).contains(pos):
                return handle
        return HANDLE_INSIDE if self.rect().contains(pos) else HANDLE_NONE

    def hoverMoveEvent(self, event):
        handle = self.hit_test_handle(event.pos())
        cursor = {
            HANDLE_TOP_LEFT: Qt.CursorShape.SizeFDiagCursor,
            HANDLE_BOTTOM_RIGHT: Qt.CursorShape.SizeFDiagCursor,
            HANDLE_TOP_RIGHT: Qt.CursorShape.SizeBDiagCursor,
            HANDLE_BOTTOM_LEFT: Qt.CursorShape.SizeBDiagCursor,
            HANDLE_TOP: Qt.CursorShape.SizeVerCursor, HANDLE_BOTTOM: Qt.CursorShape.SizeVerCursor,
            HANDLE_LEFT: Qt.CursorShape.SizeHorCursor, HANDLE_RIGHT: Qt.CursorShape.SizeHorCursor,
            HANDLE_INSIDE: Qt.CursorShape.SizeAllCursor,
        }.get(handle, Qt.CursorShape.CrossCursor)
        self.setCursor(cursor)
        event.accept()

    def _bounded_point(self, point):
        return QPointF(max(self.bounds.left(), min(self.bounds.right(), point.x())),
                       max(self.bounds.top(), min(self.bounds.bottom(), point.y())))

    def begin_drag(self, point):
        self.active_handle = self.hit_test_handle(point) or HANDLE_NEW
        self.drag_start_pos = self._bounded_point(point)
        self.rect_at_drag_start = self.rect()

    def _anchored_rect(self, anchor, point, ratio):
        point = self._bounded_point(point)
        sx = 1 if point.x() >= anchor.x() else -1
        sy = 1 if point.y() >= anchor.y() else -1
        w, h = abs(point.x() - anchor.x()), abs(point.y() - anchor.y())
        if ratio:
            w = max(w, h * ratio)
            h = w / ratio
            max_w = self.bounds.right() - anchor.x() if sx > 0 else anchor.x() - self.bounds.left()
            max_h = self.bounds.bottom() - anchor.y() if sy > 0 else anchor.y() - self.bounds.top()
            scale = min(1, max_w / max(w, .001), max_h / max(h, .001))
            w, h = w * scale, h * scale
        return QRectF(anchor, QPointF(anchor.x() + sx * w, anchor.y() + sy * h)).normalized()

    def update_drag(self, point, lock_ratio=False):
        r = self.rect_at_drag_start
        handle = self.active_handle
        ratio = self.ratio or (r.width() / r.height() if lock_ratio and r.height() else None)
        if handle == HANDLE_INSIDE:
            delta = point - self.drag_start_pos
            dx = max(self.bounds.left() - r.left(), min(self.bounds.right() - r.right(), delta.x()))
            dy = max(self.bounds.top() - r.top(), min(self.bounds.bottom() - r.bottom(), delta.y()))
            self.setRect(r.translated(dx, dy))
        elif handle == HANDLE_NEW:
            self.setRect(self._anchored_rect(self.drag_start_pos, point, ratio))
        elif handle in (HANDLE_TOP_LEFT, HANDLE_TOP_RIGHT, HANDLE_BOTTOM_LEFT, HANDLE_BOTTOM_RIGHT):
            anchors = {HANDLE_TOP_LEFT: r.bottomRight(), HANDLE_TOP_RIGHT: r.bottomLeft(),
                       HANDLE_BOTTOM_LEFT: r.topRight(), HANDLE_BOTTOM_RIGHT: r.topLeft()}
            # Prevent the dragged corner crossing its opposite corner.
            x = min(point.x(), r.right() - 1) if handle in (HANDLE_TOP_LEFT, HANDLE_BOTTOM_LEFT) else max(point.x(), r.left() + 1)
            y = min(point.y(), r.bottom() - 1) if handle in (HANDLE_TOP_LEFT, HANDLE_TOP_RIGHT) else max(point.y(), r.top() + 1)
            self.setRect(self._anchored_rect(anchors[handle], QPointF(x, y), ratio))
        elif handle in (HANDLE_LEFT, HANDLE_RIGHT):
            x = self._bounded_point(point).x()
            w = max(1, r.right() - x if handle == HANDLE_LEFT else x - r.left())
            h = r.height()
            if ratio:
                max_h = 2 * min(r.center().y() - self.bounds.top(), self.bounds.bottom() - r.center().y())
                w = min(w, max_h * ratio)
                h = w / ratio
            self.setRect(QRectF(r.right() - w if handle == HANDLE_LEFT else r.left(),
                                r.center().y() - h / 2, w, h))
        elif handle in (HANDLE_TOP, HANDLE_BOTTOM):
            y = self._bounded_point(point).y()
            h = max(1, r.bottom() - y if handle == HANDLE_TOP else y - r.top())
            w = r.width()
            if ratio:
                max_w = 2 * min(r.center().x() - self.bounds.left(), self.bounds.right() - r.center().x())
                h = min(h, max_w / ratio)
                w = h * ratio
            self.setRect(QRectF(r.center().x() - w / 2,
                                r.bottom() - h if handle == HANDLE_TOP else r.top(), w, h))

    def nudge(self, dx, dy):
        r = self.rect()
        dx = max(self.bounds.left() - r.left(), min(self.bounds.right() - r.right(), dx))
        dy = max(self.bounds.top() - r.top(), min(self.bounds.bottom() - r.bottom(), dy))
        self.setRect(r.translated(dx, dy))

    def mousePressEvent(self, event):
        self.begin_drag(event.pos())
        event.accept()

    def mouseMoveEvent(self, event):
        self.update_drag(event.pos(), bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier))
        event.accept()

    def mouseReleaseEvent(self, event):
        self.active_handle = HANDLE_NONE
        event.accept()

    def paint(self, painter, option, widget=None):
        painter.save()
        painter.setClipRect(self.bounds)
        shade = QPainterPath()
        shade.setFillRule(Qt.FillRule.OddEvenFill)
        shade.addRect(self.bounds)
        shade.addRect(self.rect())
        painter.fillPath(shade, QColor(0, 0, 0, 165))
        pen = QPen(QColor('#ffffff'), 1.5)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(self.rect())
        grid = QPen(QColor(255, 255, 255, 110), 1, Qt.PenStyle.DashLine)
        grid.setCosmetic(True)
        painter.setPen(grid)
        r = self.rect()
        for fraction in (1 / 3, 2 / 3):
            painter.drawLine(QPointF(r.left() + r.width() * fraction, r.top()),
                             QPointF(r.left() + r.width() * fraction, r.bottom()))
            painter.drawLine(QPointF(r.left(), r.top() + r.height() * fraction),
                             QPointF(r.right(), r.top() + r.height() * fraction))
        pen.setColor(QColor('#0078d4'))
        painter.setPen(pen)
        painter.setBrush(QColor('white'))
        for rect in self.get_handle_rects().values():
            painter.drawRect(rect)
        painter.restore()

    def get_crop_box(self):
        r = self.rect()
        left = max(int(self.bounds.left()), min(int(self.bounds.right()) - 1, round(r.left())))
        top = max(int(self.bounds.top()), min(int(self.bounds.bottom()) - 1, round(r.top())))
        right = max(left + 1, min(int(self.bounds.right()), round(r.right())))
        bottom = max(top + 1, min(int(self.bounds.bottom()), round(r.bottom())))
        return left, top, right, bottom
