from PySide6.QtCore import Qt, QLineF, QPoint, QPointF, QRect, QRectF
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QWidget, QGraphicsItem, QGraphicsLineItem, QStyleOptionGraphicsItem, QTextEdit
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

        node_a = FlowGraphNode('node a')
        node_b = FlowGraphNode('node b')
        node_c = FlowGraphNode('node c')
        scene.addItem(node_a)
        scene.addItem(node_b)
        scene.addItem(node_c)
        scene_rect = self.scene().sceneRect()
        # node_a.setPos(scene_rect.center())

        print(f'before sceneRect center: {scene_rect.center()}')
        print(f'node_a.pos(): {node_a.pos()}, {node_a.scenePos()}')
        # node_a.setPos(QPointF(-node_a.sceneBoundingRect().width() / 2.0, -node_a.sceneBoundingRect().height() / 2.0))
        node_b.setPos(node_a.pos() + QPointF(-250, 250))
        node_c.setPos(node_a.pos() + QPointF(250, 250))

        center_a = node_a.sceneBoundingRect().center()
        center_b = node_b.sceneBoundingRect().center()

        # line = QGraphicsLineItem(center_a.x(), center_a.y(), center_b.x(), center_b.y())
        # scene.addItem(line)

        edge_a_b = FlowGraphEdge(node_a, node_b)
        # edge_a_c = FlowGraphEdge(node_a, node_c)
        scene.addItem(edge_a_b)
        # scene.addItem(edge_a_c)

        edge_a_b._connect(node_a, node_b)
        # edge_a_c._connect(node_a, node_c)

        self.centerOn(node_a)

        print(f'after sceneRect center: {scene_rect.center()}')

    def mousePressEvent(self, event: QMouseEvent) -> None:
        super().mousePressEvent(event)
        print(event)

    def setGraph(self, g: DiGraph) -> None:
        self._graph = g

        # TODO: Should we automatically reload?
        self.reload()

# TODO: This may eventually become an empty base class that is extended for custom node views.
class FlowGraphNode(QGraphicsItem):

    def __init__(self, data: str):
        super().__init__()
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(data)

    def boundingRect(self) -> QRectF:
        size: QRect = self.text_edit.size()
        # print(f'text edit size: {size}')
        left = -size.width() / 2.0
        top = -size.height() / 2.0
        return QRectF(left, top, size.width(), size.height())

    def paint(self,
              painter: QPainter,
              _option: QStyleOptionGraphicsItem,
              _widget: QWidget):
        # TODO: Is fetching the bounding rect bad for performance? Perhaps cache it?
        rect = self.boundingRect()
        self.text_edit.render(painter, rect.topLeft().toPoint())

# TODO: This may eventually become an empty base class that is extended for custom edge drawing.
class FlowGraphEdge(QGraphicsItem):

    def __init__(self,
                 x: QGraphicsItem,
                 y: QGraphicsItem,
                 color: QColor = Qt.white,
                 width: float = 3.0):
        """The x and y items being connected need to have already been added to a scene
        and positioned before creating their edge object.
        """
        super().__init__()
        self.line: QGraphicsLineItem = QGraphicsLineItem(QLineF(QPointF(0.0, 0.0),
                                                                QPointF(0.0, 0.0)))
        self.color: QColor = color
        self.width: float = width
        self.line.setPen(QPen(self.color, self.width, Qt.SolidLine, Qt.FlatCap, Qt.BevelJoin))

        self._connect(x, y)

    def boundingRect(self) -> QRectF:
        return self.line.boundingRect()

    def paint(self,
              painter: QPainter,
              option: QStyleOptionGraphicsItem,
              widget: QWidget):
        self.line.paint(painter, option, widget)

    @staticmethod
    def srcPos(n: QGraphicsItem) -> QPointF:
        boundingRect = n.sceneBoundingRect()
        # return n.scenePos() + QPointF(boundingRect.width() / 2.0, boundingRect.height())
        return boundingRect.center()

    @staticmethod
    def dstPos(n: QGraphicsItem) -> QPointF:
        boundingRect = n.sceneBoundingRect()
        # return n.scenePos() + QPointF(boundingRect.width() / 2.0, 0.0)
        bottomCenter = boundingRect.center()
        # bottomCenter.setY(boundingRect.top())
        return bottomCenter

    def _connect(self, src: QGraphicsItem, dst: QGraphicsItem) -> None:
        """Update the edge to connect two items in the same scene.
        """
        print(f'src: {src.pos()}, dst: {dst.pos()}')
        print(f'srcPos: {FlowGraphEdge.srcPos(src)}, dstPos: {FlowGraphEdge.dstPos(dst)}')
        print(f'srcRect: {src.sceneBoundingRect()}, dstRect: {dst.sceneBoundingRect()}')
        # print(f'lineSceneRect: {self.line.sceneBoundingRect()}')
        # print(f'lineRect: {self.line.boundingRect()}')
        # print(f'linePos: {self.line.pos()}')
        # print(f'before line.line: {self.line.line()}')

        self.prepareGeometryChange()
        self.line.setLine(QLineF(FlowGraphEdge.srcPos(src), FlowGraphEdge.dstPos(dst)))

        # print(f'after line.line: {self.line.line()}')
