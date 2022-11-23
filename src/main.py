import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel

from ember.window import EmberWindow

def main(argv=None):
    if argv is None:
        argv = sys.argv

    app = QApplication(sys.argv)
    window = EmberWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main(None)
