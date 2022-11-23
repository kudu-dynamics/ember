from dataclasses import dataclass
from typing import List

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsLineItem, QStyleOptionGraphicsItem, QWidget

from .graphics import InteractiveGraphicsView

@dataclass
class TraceSnapshot:
  instr_addr: int


class TraceItem(QGraphicsItem):
  def __init__(self,
               snapshot: TraceSnapshot,
               width: float,
               height: float,
               bg_color: QColor,
               parent=None):
    super().__init__(parent=parent)
    self._snapshot: TraceSnapshot = snapshot
    self._bg_color: QColor = bg_color
    self.width = width
    self.height = height

  def boundingRect(self) -> QRectF:
    return QRectF(-self.width / 2, -self.height / 2, self.width, self.height)

  def paint(self,
            painter: QPainter,
            _option: QStyleOptionGraphicsItem,
            _widget: QWidget):
    boundingRect = self.boundingRect()
    painter.fillRect(boundingRect, self._bg_color)
    painter.drawText(boundingRect.center(), hex(self._snapshot.instr_addr))


class TraceWidget(InteractiveGraphicsView):
  """
  A view for vertically displaying linear segments of a trace.

  Segments should be provided at construction. If segments
  are added or removed, or if segments are modified, then
  the `reload()` method should be called.
  """

  def __init__(self, trace: List[TraceSnapshot], parent=None):
    super().__init__(parent=parent)

    # TODO: We could instead provide trace data and then have
    #       this widget construct the TraceItem/QGraphicsItem
    #       that corresponds to it. This gives us a place to
    #       make global decisions.
    self._trace: List[TraceSnapshot] = trace

  def reload(self) -> None:
      self._reset_scene()

      scene = self.scene()
      if not scene:
          return

      # Viewport rect in scene coords
      viewport_rect = self.mapToScene(self.viewport().geometry()).boundingRect()
      print(f'Viewport rect: {viewport_rect}')

      # Initialize the start positions
      x_left: float = viewport_rect.x()
      x_right: float = x_left + viewport_rect.width()
      x_mid: float = x_left + viewport_rect.width() / 2
      y_top: float = viewport_rect.y()
      y_pos: float = y_top

      print(f'x_left: {x_left}, x_right: {x_right}')

      for snapshot in self._trace:
          # Position and add the items to the scene
          item = TraceItem(snapshot, viewport_rect.width(), viewport_rect.height() / 4, QColor('green'))
          y_pos += item.boundingRect().height() / 2
          item.setPos(x_mid, y_pos)
          scene.addItem(item)
          print(f'Add item: {x_mid}, {y_pos}')
          print(f'Item size: {item.boundingRect()}')

          # Draw the segment divider
          y_pos += item.boundingRect().height() / 2
          divider = QGraphicsLineItem(x_left, y_pos, x_right, y_pos)
          divider.setPen(QPen(QColor(150, 150, 150)))
          scene.addItem(divider)
          print(f'Add divider: {y_pos}')

          # Update the location for the next item
          DIVIDER_HEIGHT = 6
          y_pos += DIVIDER_HEIGHT

      viewport_rect = self.mapToScene(self.viewport().geometry()).boundingRect()
      print(f'After viewport rect: {viewport_rect}')
