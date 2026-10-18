"""Interruptible paint-only animations; geometry never changes."""
from PySide6.QtCore import QEasingCurve, QVariantAnimation, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QWidget, QGraphicsOpacityEffect


class StandingsRows(QWidget):
    """One timeline per table, destroyed with its rows on replacement."""

    def __init__(self):
        super().__init__()
        self.effects = []
        self.rows = []
        self.motion = QVariantAnimation(self)
        self.motion.setDuration(305)
        self.motion.setStartValue(0.0)
        self.motion.setEndValue(305.0)
        self.motion.valueChanged.connect(self.advance)
        self.motion.finished.connect(self.finish_entrance)

    def add_row(self, row):
        effect = QGraphicsOpacityEffect(row)
        effect.setOpacity(0.0)
        row.setGraphicsEffect(effect)
        self.effects.append(effect)
        self.rows.append(row)

    def advance(self, elapsed):
        for index, effect in enumerate(self.effects):
            # Only the six visible rows stagger; lower rows are ready on scroll.
            delay = index * 25 if index < 6 else 0
            progress = max(0.0, min(1.0, (elapsed - delay) / 180))
            effect.setOpacity(1 - (1 - progress) ** 3)

    def stop_motion(self):
        self.motion.stop()

    def finish_entrance(self):
        # Qt's effect source can retain a clipped pixmap when a row moves across
        # a scroll viewport edge, even at opacity 1. Remove the effect entirely.
        self.motion.stop()
        if not self.effects:
            return
        self.effects.clear()
        for row in self.rows:
            row.setGraphicsEffect(None)
            row.update()



class HoverRow(QFrame):
    def __init__(self):
        super().__init__()
        self.amount = 0.0
        self.motion = QVariantAnimation(self)
        self.motion.setDuration(120)
        self.motion.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.motion.valueChanged.connect(self.advance)

    def advance(self, value):
        self.amount = float(value)
        self.update()

    def target(self, value):
        self.motion.stop()
        self.motion.setStartValue(self.amount)
        self.motion.setEndValue(value)
        self.motion.start()

    def enterEvent(self, event):
        self.target(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.target(0.0)
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        base, hover = QColor('#191E27'), QColor('#2A3341')
        color = QColor(*[round(a + (b - a) * self.amount) for a, b in
                         zip(base.getRgb()[:3], hover.getRgb()[:3])])
        painter.fillRect(self.rect(), color)
        painter.setPen(QColor('#292F3A'))
        painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)


class AnimatedPortrait(QLabel):
    def __init__(self, text):
        super().__init__(text)
        self.image = QPixmap()
        self.progress = 1.0
        self.motion = QVariantAnimation(self)
        self.motion.setDuration(200)
        self.motion.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.motion.valueChanged.connect(self.advance)

    def advance(self, value):
        self.progress = float(value)
        self.update()

    def clear(self):
        self.motion.stop()
        self.image = QPixmap()
        self.progress = 1.0
        super().clear()

    def present(self, pixmap):
        self.clear()
        self.image = pixmap
        self.progress = 0.0
        self.motion.setStartValue(0.0)
        self.motion.setEndValue(1.0)
        self.motion.start()

    def finish_motion(self):
        self.motion.stop()
        self.progress = 1.0
        self.update()

    def paintEvent(self, event):
        if self.image.isNull():
            return super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setOpacity(self.progress)
        x = (self.width() - self.image.width()) / 2 - 8 * (1 - self.progress)
        y = (self.height() - self.image.height()) / 2
        painter.drawPixmap(round(x), round(y), self.image)
