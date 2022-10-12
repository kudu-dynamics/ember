import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel

from window import EmberWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EmberWindow()
    window.show()
    sys.exit(app.exec())
