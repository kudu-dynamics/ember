import sys
from typing import cast, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QGraphicsItem, QGraphicsSimpleTextItem, QMainWindow, QTextEdit, QWidget
from PySide6.QtGui import QColor, QFont

from ember.ui.widgets.log import LogWidget
from ember.ui.widgets.graph import FlowGraphWidget
from ember.ui.widgets.trace import TraceSnapshot, TraceWidget
from ember.log import LogOut

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

    # main_w = FlowGraphWidget(None)
    # main_w.reload()
    # self.setCentralWidget(main_w)
    # self.addDockWidget(Qt.BottomDockWidgetArea, log_dock_w)


    items: List[TraceSnapshot] = [TraceSnapshot(addr) for addr in [0x0,
                                                                   0x4,
                                                                   0x8]]
    main_w = TraceWidget(items)
    main_w.reload()
    self.setCentralWidget(main_w)
    self.addDockWidget(Qt.BottomDockWidgetArea, log_dock_w)

    self.show()
