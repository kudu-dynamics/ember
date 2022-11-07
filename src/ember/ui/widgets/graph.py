from PySide6.QtCore import Qt, QLineF, QPoint, QPointF, QRect, QRectF
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QWidget, QGraphicsItem, QGraphicsLineItem, QGraphicsProxyWidget, QStyleOptionGraphicsItem, QTextEdit
from networkx import DiGraph
from typing import Any

from .graphics import InteractiveGraphicsView
import ember.graph.layout as graph_layout
from ember.graph.layout import NodeSize

# TODO: This may eventually become an empty base class that is extended for custom node views.
class FlowGraphNode(QGraphicsItem):

    def __init__(self, data: str):
        super().__init__()
        self.data = data
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(data)
        self.proxy = QGraphicsProxyWidget(self)
        self.proxy.setWidget(self.text_edit)

    def boundingRect(self) -> QRectF:
        return self.proxy.boundingRect()

    def paint(self,
              painter: QPainter,
              _option: QStyleOptionGraphicsItem,
              _widget: QWidget):
        self.proxy.paint(painter, _option, _widget)

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
        return n.scenePos() + QPointF(boundingRect.width() / 2.0, boundingRect.height())

    @staticmethod
    def dstPos(n: QGraphicsItem) -> QPointF:
        boundingRect = n.sceneBoundingRect()
        return n.scenePos() + QPointF(boundingRect.width() / 2.0, 0.0)

    def _connect(self, src: QGraphicsItem, dst: QGraphicsItem) -> None:
        """Update the edge to connect two items in the same scene.
        """

        self.prepareGeometryChange()
        self.line.setLine(QLineF(FlowGraphEdge.srcPos(src), FlowGraphEdge.dstPos(dst)))

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
        g.add_edge('e', 'e')
        g.add_edge('e', 'f')
        g.add_edge('d', 'f')

        scene_nodes = {n: FlowGraphNode(n) for n in g.nodes()}
        for n in scene_nodes.values():
            scene.addItem(n)

        def rect_to_size(r: QRectF) -> NodeSize:
            return NodeSize(int(r.width()), int(r.height()))

        # TODO: How should the FlowGraphNode know what to display?
        # TODO: Should the FlowGrpahNode keep a reference to the original node it represents?
        node_sizes = {n: rect_to_size(sn.boundingRect()) for n, sn in scene_nodes.items()}

        layout_result = graph_layout.layout(g, node_sizes, lambda x: x)

        for n, pt in layout_result.nodes.items():
            scene_nodes[n].setPos(QPointF(float(pt.x), float(pt.y)))

        # scene_rect = self.scene().sceneRect()

        # node_a.setPos(scene_rect.center())
        # node_b.setPos(node_a.pos() + QPointF(-250, 250))
        # node_c.setPos(node_a.pos() + QPointF(250, 250))

        # center_a = node_a.sceneBoundingRect().center()
        # center_b = node_b.sceneBoundingRect().center()

        # edge_a_b = FlowGraphEdge(node_a, node_b)
        # edge_a_c = FlowGraphEdge(node_a, node_c)
        # scene.addItem(edge_a_b)
        # scene.addItem(edge_a_c)

        # edge_a_b._connect(node_a, node_b)
        # edge_a_c._connect(node_a, node_c)

        # self.centerOn(node_a)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        super().mousePressEvent(event)
        print(event)

    def setGraph(self, g: DiGraph) -> None:
        self._graph = g

        # TODO: Should we automatically reload?
        self.reload()
