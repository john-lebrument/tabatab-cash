"""Consistent live Ctrl switching and destination feedback on all drop targets."""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap


def set_large_drag_cursors(drag):
    for action in (Qt.DropAction.CopyAction, Qt.DropAction.MoveAction):
        pix = QPixmap(48, 48)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor('#0078d4'))
        painter.setPen(QPen(QColor('white'), 2))
        painter.drawRoundedRect(3, 3, 40, 40, 7, 7)
        painter.setPen(QPen(QColor('white'), 4))
        painter.drawLine(12, 24, 35, 24)
        if action == Qt.DropAction.CopyAction:
            painter.drawLine(24, 12, 24, 35)
        else:
            painter.drawLine(25, 13, 36, 24)
            painter.drawLine(36, 24, 25, 35)
        painter.end()
        drag.setDragCursor(pix, action)


def drop_action(event):
    if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
        return Qt.DropAction.CopyAction
    if event.possibleActions() & Qt.DropAction.MoveAction:
        return Qt.DropAction.MoveAction
    return Qt.DropAction.CopyAction


def paint_destination(viewport, rect):
    if rect.isEmpty():
        return
    painter = QPainter(viewport)
    painter.setPen(QPen(QColor('#009cde'), 3))
    painter.setBrush(QColor(0, 156, 222, 75))
    painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 4, 4)
    painter.end()
