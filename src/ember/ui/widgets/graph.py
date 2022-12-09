from PySide6.QtCore import Qt, QLineF, QPoint, QPointF, QRect, QRectF
from PySide6.QtGui import QBrush, QColor, QMouseEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget, QGraphicsItem, QGraphicsPathItem, QGraphicsTextItem, QGraphicsRectItem, QStyleOptionGraphicsItem, QTextEdit
from networkx import DiGraph
from typing import Any, List, Type, TypeAlias, Callable

from .graphics import InteractiveGraphicsView
import ember.graph.layout as graph_layout
from ember.graph.layout import NodeSize, Point

def toQPoint(p: Point) -> QPoint:
    return QPoint(p.x, p.y)

Node: TypeAlias = Any
        
# TODO: This may eventually become an empty base class that is extended for custom node views.
class FlowGraphNode(QGraphicsItem):

    minimum_width: float = 300.0
    minimum_height: float = 50.0
    
    def __init__(self,
                 data: Any,
                 ):
        super().__init__()
        self.data = data
        self.text = QGraphicsTextItem(str(data))
        text_rect = self.text.boundingRect()
        self.width = max(text_rect.width(), self.minimum_width)
        self.height = min(text_rect.height(), self.minimum_height)
        self._bounding_rect = QRectF(0.0, 0.0, self.width, self.height)
        self.rect = QGraphicsRectItem(0.0, 0.0, self.width, self.height)
        self.rect.setBrush(QBrush(QColor(50, 50, 50)))
        self.text.setZValue(1.0)

    def boundingRect(self) -> QRectF:
        # TODO: Should this be centered within the block instead of (0, 0)?
        return self._bounding_rect

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
                 parent: QWidget = None,
                 node_ctor: Callable[[Node], FlowGraphNode] = lambda x: FlowGraphNode(x),
                 edge_ctor: Callable[[FlowGraphNode, FlowGraphNode, List[QPointF]], FlowGraphEdge] = lambda src, dst, pts: FlowGraphEdge(src, dst, pts),
                 sort_node_on: Callable[[Any], Any] = lambda x: x,
                 ):
        super().__init__(parent)

        self._graph = graph
        self._node_ctor = node_ctor
        self._edge_ctor = edge_ctor
        self._sort_node_on = sort_node_on

        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def reload(self):
        self._reset_scene()

        # Setup graph in scene
        # TODO: Replace placeholder
        scene = self.scene()
        if not scene:
            return
        
        scene_nodes = {n: self._node_ctor(n) for n in self._graph.nodes()}
        for n in scene_nodes.values():
            scene.addItem(n)

        def rect_to_size(r: QRectF) -> NodeSize:
            return NodeSize(int(r.width()), int(r.height()))

        # TODO: How should the FlowGraphNode know what to display?
        # TODO: Should the FlowGrpahNode keep a reference to the original node it represents?
        node_sizes = {n: rect_to_size(sn.boundingRect()) for n, sn in scene_nodes.items()}

        layout_result, edges = graph_layout.layout(self._graph, node_sizes, self._sort_node_on)

        print(edges)

        for n, pt in layout_result.nodes.items():
            scene_nodes[n].setPos(QPointF(float(pt.x), float(pt.y)))

        for e, pts in layout_result.edges.items():
            qpts = [QPointF(pt.x, pt.y) for pt in pts]
            fge = self._edge_ctor(e.src, e.dst, qpts)
            scene.addItem(fge)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        super().mousePressEvent(event)
        print(event)

    def setGraph(self, g: DiGraph) -> None:
        self._graph = g

        # TODO: Should we automatically reload?
        self.reload()
