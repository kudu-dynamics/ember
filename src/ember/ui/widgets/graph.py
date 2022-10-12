from PySide6.QtCore import Qt

from .graphics import InteractiveGraphicsView

class FlowGraphWidget(InteractiveGraphicsView):

    def __init__(self, graph, parent=None):
        super().__init__(parent)

        self._graph = graph

        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

    def reload(self):
        self._reset_scene()
