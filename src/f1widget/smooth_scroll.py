"""Interruptible wheel scrolling with native scrollbar and touchpad control."""
from PySide6.QtCore import QEvent, QEasingCurve, QVariantAnimation
from PySide6.QtWidgets import QScrollArea
from .motion import StandingsRows


class SmoothScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.target = 0.0
        self.direction = 0
        self.applying_frame = False
        self.motion = QVariantAnimation(self)
        self.motion.setDuration(160)
        self.motion.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.motion.valueChanged.connect(self.apply_frame)
        bar = self.verticalScrollBar()
        bar.installEventFilter(self)
        bar.sliderPressed.connect(self.stop_motion)
        bar.actionTriggered.connect(self.stop_motion)
        bar.rangeChanged.connect(self.stop_motion)
        bar.valueChanged.connect(self.external_value_changed)

    def stop_motion(self, *args):
        self.motion.stop()
        self.target = float(self.verticalScrollBar().value())
        self.direction = 0

    def external_value_changed(self, value):
        if not self.applying_frame:
            self.stop_motion()

    def apply_frame(self, value):
        self.applying_frame = True
        try:
            self.verticalScrollBar().setValue(round(value))
        finally:
            self.applying_frame = False

    def setWidget(self, widget):
        self.stop_motion()
        super().setWidget(widget)
        self.stop_motion()

    def scrollContentsBy(self, dx, dy):
        content = self.widget()
        if isinstance(content, StandingsRows):
            # Finish the entrance before any wheel, touchpad or scrollbar move.
            content.finish_entrance()
        super().scrollContentsBy(dx, dy)

    def eventFilter(self, watched, event):
        if watched is self.verticalScrollBar() and event.type() == QEvent.Type.Wheel:
            self.wheelEvent(event)
            return True
        return super().eventFilter(watched, event)

    def wheelEvent(self, event):
        bar = self.verticalScrollBar()
        # Pixel events already contain touchpad momentum; don't add another tail.
        if not event.pixelDelta().isNull():
            self.stop_motion()
            bar.setValue(bar.value() - event.pixelDelta().y())
            event.accept()
            return
        delta = -event.angleDelta().y() / 120 * bar.singleStep()
        if not delta:
            event.accept()
            return
        direction = 1 if delta > 0 else -1
        current = float(bar.value())
        # Reverse immediately from the visible position, discarding old momentum.
        base = self.target if direction == self.direction else current
        target = max(bar.minimum(), min(bar.maximum(), base + delta))
        event.accept()
        if target == self.target and direction == self.direction:
            return
        self.motion.stop()
        self.target = target
        self.direction = direction
        if target == current:
            return
        self.motion.setStartValue(current)
        self.motion.setEndValue(float(target))
        self.motion.start()
