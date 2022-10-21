"""
Basic views for dealing with QGraphicsScene and graph views.

Several classes are based on equivalent code in angr management. Thank you, angr devs!
"""

from typing import Optional
from PySide6.QtWidgets import QApplication, QGraphicsScene, QGraphicsView, QGraphicsSceneMouseEvent, QStyleOptionGraphicsItem
from PySide6.QtCore import QPointF, Qt, QEvent, QMarginsF, QPoint, QRectF, QSize, Signal
from PySide6.QtGui import QImage, QKeyEvent, QMouseEvent, QPainter, QPointingDevice, QVector2D, QWheelEvent

class BaseGraphicsView(QGraphicsView):
    """
    A base graphics view that keeps track of the scene rectangle and the ability to
    save the visibile scene to an image.
    """

    scene_rect_changed = Signal(QRectF)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._scene_rect: QRectF = QRectF()
        self._is_extra_render_pass: bool = False

    @property
    def scene_rect(self):
        return self._scene_rect

    @property
    def is_extra_render_pass(self):
        return self._is_extra_render_pass

    def set_extra_render_pass(self, is_extra_pass: bool):
        """
        Trugger any post-render callbacks.
        """
        self._is_extra_render_pass = is_extra_pass

    def redraw(self):
        """
        Redraw the scene. Do not recompute any items in the view."

        :return: None
        """
        scene = self.scene()
        if scene:
            scene.update(self.sceneRect())

    def viewportEvent(self, event:QEvent) -> bool:
        scene_rect = self.mapToScene(self.viewport().geometry()).boundingRect()
        if scene_rect != self._scene_rect:
            self._scene_rect = scene_rect
            self.scene_rect_changed.emit(scene_rect)

        return super().viewportEvent(event)

    def save_image_to(self, path, left_margin=50, top_margin=50, right_margin=50, bottom_margin=50):
        """
        Save the scene to an image.

        :return: None
        """
        margins = QMarginsF(left_margin, top_margin, right_margin, bottom_margin)

        # Figure out rectangle for source
        old_rect = self.scene().sceneRect()
        min_rect = self.scene().itemsBoundingRect()
        img_rect = min_rect.marginsAdded(margins)

        image = QImage(img_rect.size().toSize(), QImage.Format_ARGB32)
        image.fill(Qt.white)
        painter = QPainter(image)

        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform) #type: ignore

        # Draw the image
        self.scene().setSceneRect(img_rect)
        self.scene().render(painter)
        image.save(path)

        painter.end()

        # Restore old scene rect
        self.scene().setSceneRect(old_rect)

class InteractiveGraphicsView(BaseGraphicsView):
    """
    An interactive graphics view.
    """

    ZOOM_X = True
    ZOOM_Y = True

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._is_dragging = False
        self._is_mouse_pressed = False

        # Scene coordinates
        self._last_coords: Optional[QPointF] = None
        # View coordinates
        self._last_screen_pos: Optional[QPoint] = None

        self.setTransformationAnchor(QGraphicsView.NoAnchor)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.zoom_factor = None

    def _initial_position(self):
        raise NotImplementedError

    def _reset_view(self):
        """
        Reset the view of the scene.
        """

        self.resetTransform()
        self.centerOn(self._initial_position())
        self.zoom(restore=True)

    def _reset_scene(self):
        """
        Reset the scene.
        """

        if self.scene():
            self.scene().clear()
        else:
            scene = QGraphicsScene(self)
            self.setScene(scene)

    def sizeHint(self):
        return QSize(300, 300)

    def zoom(self, out=False, at=None, reset=False, restore=False):
        if at is None:
            at = self.scene().sceneRect().center().toPoint()

        lod = QStyleOptionGraphicsItem.levelOfDetailFromTransform(self.transform())
        zoomInFactor = 1.25
        zoomOutFactor = 1 / zoomInFactor

        if reset:
            zoomFactor = 1 / lod
        elif restore:
            zoomFactor = self.zoom_factor if self.zoom_factor else 1 / lod
        elif not out:
            zoomFactor = zoomInFactor
        else:
            zoomFactor = zoomOutFactor
            # Limit scroll out
            if lod < 0.015:
                return

        # Save the scene position
        old_pos = self.mapToScene(at)

        # Perform zoom
        self.scale(zoomFactor if self.ZOOM_X else 1,
                   zoomFactor if self.ZOOM_Y else 1)
        self.zoom_factor = QStyleOptionGraphicsItem.levelOfDetailFromTransform(self.transform())

        # Get the new position
        new_pos = self.mapToScene(at)

        # Translate view over to new position
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())

    def wheelEvent(self, event):
        print(f'scene rect: {self.scene().sceneRect()}')
        if event.modifiers() & Qt.ControlModifier == Qt.ControlModifier:
            print(f'angleDelta: {event.angleDelta()}')
            is_zoom_out = event.angleDelta().y() < 0
            # TODO: Do we want to use cursor position (the pos() method) instead?
            self.zoom(is_zoom_out, event.globalPosition().toPoint())
        elif is_touchpad(event):
            super().wheelEvent(event)
        else:
            # Allow mouse wheel to be used for horizontal scrolling when modifier is active
            if event.modifiers() & Qt.ShiftModifier == Qt.ShiftModifier:
                event.setModifiers(event.modifiers() & ~Qt.ShiftModifier)
                self.horizontalScrollBar().wheelEvent(event)
            else:
                self.verticalScrollBar().wheelEvent(event)

    def _save_last_coords(self, event):
        event_pos: QPoint = event.pos()
        scene_pos = self.mapToScene(event_pos)
        self._last_coords = scene_pos
        self._last_screen_pos = event_pos

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Equal and is_modifier_active(event, Qt.ControlModifier):
            self.zoom(out=False)
        elif event.key() == Qt.Key_Minus and is_modifier_active(event, Qt.ControlModifier):
            self.zoom(out=True)
        elif event.key() == Qt.Key_0 and is_modifier_active(event, Qt.ControlModifier):
            self.zoom(reset=True)
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._is_mouse_pressed = True
            self._is_dragging = False

            self._save_last_coords(event)
            event.accept()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        SENSITIVITY = 1.0
        if self._is_mouse_pressed:
            mouse_delta = QVector2D(event.pos() - self._last_screen_pos).length() #type: ignore
            if mouse_delta > SENSITIVITY:
                self._is_dragging = True
                scene_pos = self.mapToScene(event.pos())

                self.viewport().setCursor(Qt.ClosedHandCursor)

                delta = scene_pos - self._last_coords #type: ignore
                self.translate(delta.x(), delta.y())

            self._save_last_coords(event)
            event.accept()

        super().mouseMoveEvent(event)

    def dispatchMouseMoveEventToScene(self, event):
        """
        Send unhandled events to the underlying scene.
        """

        if event.type() == QEvent.MouseButtonPress:
            event_type = QEvent.GraphicsSceneMousePress
        elif event.type() == QEvent.MouseButtonRelease:
            event_type = QEvent.GraphicsSceneMouseRelease
        else:
            raise ValueError(f'Unexpected event type {event.type()}')

        # Pulled from angr management,
        # which pulled from QGraphicsView::mousePressEvent in Qt5
        mouse_event = QGraphicsSceneMouseEvent(event_type)
        mouse_press_view_point: QPoint = event.pos()
        mouse_press_scene_point = self.mapToScene(mouse_press_view_point)
        mouse_press_screen_point = event.globalPos()
        last_mouse_move_scene_point = mouse_press_scene_point
        last_mouse_move_screen_point = mouse_press_screen_point
        mouse_press_button = event.button()

        # TODO: This is from angr management code, they were unsure if needed and
        #       based on comment it wasn't available in PySide2. Check out how situation
        #       with PySide6.
        # mouse_event.setWidget(self.viewport())
        mouse_event.setButtonDownScenePos(mouse_press_button, mouse_press_scene_point)
        mouse_event.setButtonDownScreenPos(mouse_press_button, mouse_press_screen_point)
        mouse_event.setScenePos(mouse_press_scene_point)
        mouse_event.setScreenPos(mouse_press_screen_point)
        mouse_event.setLastScenePos(last_mouse_move_scene_point)
        mouse_event.setLastScreenPos(last_mouse_move_screen_point)
        mouse_event.setButtons(event.buttons())
        mouse_event.setButton(event.button())
        mouse_event.setModifiers(event.modifiers())
        mouse_event.setSource(event.source())
        mouse_event.setFlags(event.flags())
        mouse_event.setAccepted(False)
        QApplication.sendEvent(self.scene(), mouse_event)
        return mouse_event

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            if self._is_dragging:
                self.viewport().setCursor(Qt.ArrowCursor)
                event.accept()

        if not event.isAccepted():
            gen_press_event = QMouseEvent(QEvent.MouseButtonPress,
                                          event.pos(),
                                          event.globalPos(),
                                          event.button(),
                                          event.buttons(),
                                          event.modifiers())
            _ = self.dispatchMouseMoveEventToScene(gen_press_event)

            gen_release_event = QMouseEvent(QEvent.MouseButtonRelease,
                                            event.pos(),
                                            event.globalPos(),
                                            event.button(),
                                            event.buttons(),
                                            event.modifiers())
            release_event = self.dispatchMouseMoveEventToScene(gen_release_event)

            if not release_event.isAccepted():
                # TODO: This is from angr management, but method isn't defined
                # self.on_background_click()
                release_event.accept()

        self._is_mouse_pressed = False
        self._is_dragging = False

        super().mouseReleaseEvent(event)

def is_modifier_active(event: QKeyEvent,
                       modifier: Qt.KeyboardModifier) -> bool:
    """
    Check if keyboard modifier is active for event.
    """

    return event.modifiers() & modifier == modifier #type: ignore

def is_touchpad(event: QWheelEvent) -> bool:
    return event.pointerType() == QPointingDevice.PointerType.Finger
