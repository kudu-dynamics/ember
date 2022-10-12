from PySide6.QtWidgets import QWidget

class EmberWindow(QWidget):
  def __init__(self):
    super().__init__()

    self.setup()

  def setup(self):
    self.setGeometry(100, 100, 200, 150)
    self.setWindowTitle('Ember')

    self.show()
