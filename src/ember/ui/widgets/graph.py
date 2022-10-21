from PySide6.QtCore import Qt, QPoint, QRect, QRectF
from PySide6.QtGui import QMouseEvent, QPainter
from PySide6.QtWidgets import QWidget, QGraphicsItem, QStyleOptionGraphicsItem, QTextEdit
from networkx import DiGraph

from .graphics import InteractiveGraphicsView

class FlowGraphWidget(InteractiveGraphicsView):

    def __init__(self,
                 graph: DiGraph,
                 parent: QWidget = None):
        super().__init__(parent)

        self._graph = graph

        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def reload(self):
        self._reset_scene()

        # Setup graph in scene
        # TODO: Replace placeholder
        scene = self.scene()
        if not scene:
            return

        node = FlowGraphNode()
        scene.addItem(node)
        node.setPos(self.scene().sceneRect().center())

    def mousePressEvent(self, event: QMouseEvent) -> None:
        super().mousePressEvent(event)
        print(event)

    def setGraph(self, g: DiGraph) -> None:
        self._graph = g

        # TODO: Should we automatically reload?
        self.reload()


class FlowGraphNode(QGraphicsItem):

    def __init__(self):
        super().__init__()
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText("hello node")

    def boundingRect(self) -> QRectF:
        # TODO: Figure out the correct way to do this
        size: QRect = self.text_edit.size()
        return QRectF(0.0, 0.0, size.width(), size.height())

    def paint(self,
              painter: QPainter,
              option: QStyleOptionGraphicsItem,
              widget: QWidget):
        self.text_edit.render(painter, QPoint(0, 0))
