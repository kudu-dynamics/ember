from PySide6.QtWidgets import QTextEdit

class LogWidget(QTextEdit):

  def __init__(self):
    super().__init__()

    self.setReadOnly(True)
