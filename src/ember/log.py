from typing import Optional, TextIO

from PySide6.QtWidgets import QTextEdit
from PySide6.QtGui import QColor
import PySide6.QtGui as QtGui

class LogOut:
  def __init__(self,
               text_edit: QTextEdit,
               alt_out: TextIO,
               color: Optional[QColor] = None):
    self.text_edit = text_edit
    self.alt_out = alt_out
    self.color = color

  def write(self, msg):
    orig_color = self.text_edit.textColor()
    if self.color:
      self.text_edit.setTextColor(self.color)

    self.text_edit.moveCursor(QtGui.QTextCursor.End)
    self.text_edit.insertPlainText(msg)

    if self.color:
      self.text_edit.setTextColor(orig_color)

    # Pass on msg to alternate stream
    if self.alt_out:
      self.alt_out.write(msg)
