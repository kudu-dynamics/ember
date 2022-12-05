from dataclasses import dataclass
from typing import List, Union
from random import randint
import random

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsLineItem, QGraphicsRectItem, QGraphicsScene, QStyleOptionGraphicsItem, QWidget

from .graphics import InteractiveGraphicsView

class TraceEntry:
    def __init__(self,
                 start_addr: int,
                 data: str):
        self.start_addr = start_addr
        self.data = data

class TraceContext:
    def __init__(self,
                 name: str,
                 entries: List[Union[TraceEntry, 'TraceContext']]):
        self.name = name
        self.entries = entries

class TraceItem(QGraphicsItem):
    def __init__(self,
                 trace_entry: TraceEntry,
                 width: float,
                 height: float,
                 parent=None):
        super().__init__(parent=parent)
        self._trace_entry: trace_entry = trace_entry
        self.width = width
        self.height = height
        self.rect = QGraphicsRectItem(0.0, 0.0, width, height)
        self.rect.setBrush(QColor(50, 50, 50))
        self._pen = QPen(QColor(10, 10, 10))
        self._pen.setWidth(3)
        self.rect.setPen(self._pen)

    def boundingRect(self) -> QRectF:
        pen_width = self._pen.width()
        return QRectF(0.0, 0.0, self.width + pen_width, self.height + pen_width)

    def paint(self,
              painter: QPainter,
              _option: QStyleOptionGraphicsItem,
              _widget: QWidget):
        # painter.drawText(boundingRect.center(), hex(self._trace_entry.start_addr))
        boundingRect = self.boundingRect()
        self.rect.paint(painter, _option, _widget)


class TraceWidget(InteractiveGraphicsView):
    """
    A view for vertically displaying linear segments of a trace.

    Segments should be provided at construction. If segments
    are added or removed, or if segments are modified, then
    the `reload()` method should be called.
    """

    def __init__(self, trace: TraceContext, parent=None):
        super().__init__(parent=parent)

        # TODO: We could instead provide trace data and then have
        #       this widget construct the TraceItem/QGraphicsItem
        #       that corresponds to it. This gives us a place to
        #       make global decisions.
        self._trace: List[TraceContext] = trace

    def load_context(self,
                     scene: QGraphicsScene,
                     margin_brushes: List[QBrush],
                     y_pos: float,
                     x_left: float,
                     x_right: float,
                     x_pos: float,
                     ctx: TraceContext) -> float:
        DIVIDER_HEIGHT = 6
        MARGIN_PEN = QPen()
        MARGIN_PEN.setStyle(Qt.NoPen)
        PATTERNS = [Qt.SolidPattern,
                    Qt.Dense1Pattern,
                    Qt.Dense2Pattern,
                    Qt.Dense3Pattern,
                    Qt.Dense4Pattern,
                    Qt.Dense5Pattern,
                    Qt.Dense6Pattern,
                    Qt.Dense7Pattern,
                    Qt.HorPattern,
                    Qt.VerPattern,
                    Qt.CrossPattern,
                    Qt.BDiagPattern,
                    Qt.FDiagPattern,
                    Qt.DiagCrossPattern]

        for entry in ctx.entries:
            if isinstance(entry, TraceContext):
                # Make recursive call to load nested context
                x_margin: float = 50.0
                prev_margin_brushes = margin_brushes.copy()
                margin_brushes.append(QBrush(QColor(randint(100, 255), randint(100, 255), randint(100, 255)),
                                             bs=random.choice(PATTERNS[:2])))
                y_pos = self.load_context(scene, margin_brushes, y_pos, x_left, x_right, x_pos + x_margin, entry)
                margin_brushes = prev_margin_brushes
            else:
                # Position and add the items to the scene
                width = 500.0
                height = 100.0
                item = TraceItem(entry, width, height)
                item.setPos(x_pos, y_pos)
                scene.addItem(item)

                # Draw margin
                # The width of the rect drawn for each of the contexts
                margin_ctx_width = (x_pos - x_left) / len(margin_brushes) if margin_brushes else 0.0
                for idx, margin_brush in enumerate(margin_brushes):
                    margin_rect = QGraphicsRectItem(QRectF(0.0,
                                                           0.0,
                                                           margin_ctx_width,
                                                           height + DIVIDER_HEIGHT))
                    # margin_rect.setZValue(1.0)
                    margin_rect.setPos(x_left + (margin_ctx_width * idx), y_pos)
                    margin_rect.setPen(MARGIN_PEN)
                    margin_rect.setBrush(margin_brush)
                    scene.addItem(margin_rect)

                # Advance y-position
                y_pos += height

                # Draw the segment divider
                divider = QGraphicsLineItem(x_pos, y_pos, x_pos + width, y_pos)
                divider.setPen(QPen(QColor(150, 150, 150)))
                scene.addItem(divider)

                # Update the location for the next item
                y_pos += DIVIDER_HEIGHT

        return y_pos

    def reload(self) -> None:
        self._reset_scene()

        scene = self.scene()
        if not scene:
            return

        # Viewport rect in scene coords
        viewport_rect = self.mapToScene(self.viewport().geometry()).boundingRect()
        print(f'Viewport rect: {viewport_rect}')

        width = 500.0
        height = 300.0

        # Initialize the start positions
        x_left: float = viewport_rect.x()
        x_right: float = x_left + viewport_rect.width()
        x_mid: float = x_left + viewport_rect.width() / 2
        y_top: float = viewport_rect.y()
        y_pos: float = y_top

        print(f'x_left: {x_left}, x_right: {x_right}')

        self.load_context(scene, [], y_pos, x_left, x_right, x_left, self._trace)
