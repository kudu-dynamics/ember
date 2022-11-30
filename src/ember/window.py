import sys
from typing import cast, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QGraphicsItem, QGraphicsSimpleTextItem, QMainWindow, QTabWidget
from PySide6.QtGui import QColor, QFont

from .ui.widgets.log import LogWidget
from .ui.widgets.graph import FlowGraphWidget
from .ui.widgets.trace import TraceContext, TraceEntry, TraceWidget
from .log import LogOut

class EmberWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setup()

    def setup(self):
        self.setGeometry(100, 100, 1024, 768)
        self.setWindowTitle('Ember')

        log_w = LogWidget()
        sys.stdout = LogOut(log_w, sys.stdout)
        sys.stderr = LogOut(log_w, sys.stderr, QColor(255, 0, 0))

        log_dock_w = QDockWidget("Log")
        log_dock_w.setWidget(log_w)

        graph_w = FlowGraphWidget(None)
        graph_w.reload()

        trace = TraceContext('A',
                             [TraceEntry(0x0, 'a'),
                              TraceEntry(0x4, 'b'),
                              TraceContext('B',
                                           [TraceEntry(0x10, 'a'),
                                            TraceEntry(0x14, 'b'),
                                            TraceEntry(0x18, 'c'),
                                            TraceContext('C',
                                                         [TraceEntry(0x20, 'a'),
                                                          TraceContext('D',
                                                                       [TraceEntry(0x30, 'a'),
                                                                        TraceEntry(0x34, 'b')]),
                                                          TraceEntry(0x24, 'b'),
                                                          TraceEntry(0x28, 'c')]),
                                            TraceEntry(0x1c, 'd')]),
                              TraceEntry(0x8, 'c'),
                              TraceEntry(0xc, 'd'),
                              TraceContext('BB',
                                           [TraceEntry(0x10, 'a'),
                                            TraceEntry(0x14, 'b'),
                                            TraceEntry(0x18, 'c')])])
        trace_w = TraceWidget(trace)
        trace_w.reload()

        tab_w = QTabWidget()
        tab_w.addTab(graph_w, "Graph View")
        tab_w.addTab(trace_w, "Trace View")

        self.setCentralWidget(tab_w)
        self.addDockWidget(Qt.BottomDockWidgetArea, log_dock_w)

        self.addDockWidget(Qt.BottomDockWidgetArea, log_dock_w)

        self.show()
