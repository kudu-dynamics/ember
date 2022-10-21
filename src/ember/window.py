import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QMainWindow, QTextEdit, QWidget
from PySide6.QtGui import QColor

from ui.widgets.log import LogWidget
from ui.widgets.graph import FlowGraphWidget
from log import LogOut

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

    main_w = FlowGraphWidget(None)
    main_w.reload()
    self.setCentralWidget(main_w)
    self.addDockWidget(Qt.BottomDockWidgetArea, log_dock_w)

    self.show()
