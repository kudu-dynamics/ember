from PySide6.QtCore import Qt, QLineF, QPoint, QPointF, QRect, QRectF
from PySide6.QtGui import QBrush, QColor, QMouseEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget, QGraphicsItem, QGraphicsPathItem, QGraphicsTextItem, QGraphicsRectItem, QStyleOptionGraphicsItem, QTextEdit
from networkx import DiGraph
from typing import Any, List

from .graphics import InteractiveGraphicsView
import ember.graph.layout as graph_layout
from ember.graph.layout import NodeSize, Point

def toQPoint(p: Point) -> QPoint:
    return QPoint(p.x, p.y)

# TODO: This may eventually become an empty base class that is extended for custom node views.
class FlowGraphNode(QGraphicsItem):

    def __init__(self,
                 data: str,
                 width: int,
                 height: int):
        super().__init__()
        self.data = data
        self.width = width
        self.height = height
        self.rect = QGraphicsRectItem(0.0, 0.0, width, height)
        self.rect.setBrush(QBrush(QColor(50, 50, 50)))
        self.text = QGraphicsTextItem(data)
        self.text.setZValue(1.0)

    def boundingRect(self) -> QRectF:
        # TODO: Should this be centered within the block instead of (0, 0)?
        return QRectF(0.0,
                      0.0,
                      self.width,
                      self.height)


    def paint(self,
              painter: QPainter,
              _option: QStyleOptionGraphicsItem,
              _widget: QWidget):
        self.rect.paint(painter, _option, _widget)
        self.text.paint(painter, _option, _widget)

# TODO: This may eventually become an empty base class that is extended for custom edge drawing.
class FlowGraphEdge(QGraphicsItem):

    def __init__(self,
                 src: QGraphicsItem,
                 dst: QGraphicsItem,
                 pts: List[QPointF],
                 color: QColor = Qt.white,
                 width: float = 3.0):
        """The x and y items being connected need to have already been added to a scene
        and positioned before creating their edge object.
        """
        super().__init__()

        self.path: QPainterPath = QPainterPath(pts[0])
        for pt in pts[1:]:
            self.path.lineTo(pt)
        self.pathItem: QGraphicsPathItem = QGraphicsPathItem(self.path)

        self.color: QColor = color
        self.width: float = width
        self.pathItem.setPen(QPen(self.color, self.width, Qt.SolidLine, Qt.FlatCap, Qt.BevelJoin))

        self.src = src
        self.dst = dst

    def boundingRect(self) -> QRectF:
        return self.pathItem.boundingRect()

    def paint(self,
              painter: QPainter,
              option: QStyleOptionGraphicsItem,
              widget: QWidget):
        self.pathItem.paint(painter, option, widget)

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

        g = DiGraph()
        g.add_edge('a', 'b')
        g.add_edge('a', 'c')
        g.add_edge('b', 'd')
        g.add_edge('c', 'd')
        g.add_edge('d', 'e')
        g.add_edge('b', 'e')
        # g.add_edge('e', 'e')
        # g.add_edge('e', 'c')
        # g.add_edge('c', 'e')
        g.add_edge('e', 'f')
        g.add_edge('d', 'f')

        scene_nodes = {n: FlowGraphNode(n, 300, 200) for n in g.nodes()}
        for n in scene_nodes.values():
            scene.addItem(n)

        def rect_to_size(r: QRectF) -> NodeSize:
            return NodeSize(int(r.width()), int(r.height()))

        # TODO: How should the FlowGraphNode know what to display?
        # TODO: Should the FlowGrpahNode keep a reference to the original node it represents?
        node_sizes = {n: rect_to_size(sn.boundingRect()) for n, sn in scene_nodes.items()}

        layout_result, edges = graph_layout.layout(g, node_sizes, lambda x: x)

        print(edges)

        for n, pt in layout_result.nodes.items():
            scene_nodes[n].setPos(QPointF(float(pt.x), float(pt.y)))

        for e, pts in layout_result.edges.items():
            qpts = [QPointF(pt.x, pt.y) for pt in pts]
            fge = FlowGraphEdge(e.src, e.dst, qpts)
            scene.addItem(fge)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        super().mousePressEvent(event)
        print(event)

    def setGraph(self, g: DiGraph) -> None:
        self._graph = g

        # TODO: Should we automatically reload?
        self.reload()
