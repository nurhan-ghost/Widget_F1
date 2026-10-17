"""Mode selector with one interruptible, paint-only sliding highlight."""
from PySide6.QtCore import Qt, QRectF, Signal, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QButtonGroup


class ModeTabs(QWidget):
    mode_requested = Signal(str)
    modes = ("drivers", "teams")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self.current_mode = "drivers"
        self.progress = 0.0
        self.motion = QVariantAnimation(self)
        self.motion.setDuration(200)
        self.motion.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.motion.valueChanged.connect(self.advance)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.group = QButtonGroup(self)
        self.buttons = {}
        for mode in self.modes:
            button = QPushButton(mode.upper())
            button.setCheckable(True)
            button.setChecked(mode == self.current_mode)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet("""
                QPushButton, QPushButton:hover, QPushButton:checked,
                QPushButton:pressed { background: transparent; border: none;
                    padding: 7px 10px; color: #EEF1F5; }
                QPushButton:focus { border: 1px solid #A6AFBF; }
            """)
            self.group.addButton(button)
            self.buttons[mode] = button
            layout.addWidget(button, 1)
            button.clicked.connect(lambda checked=False, mode=mode: self.request_mode(mode))

    def request_mode(self, mode):
        if mode != self.current_mode:
            self.set_current(mode)
            self.mode_requested.emit(mode)

    def set_current(self, mode):
        if mode not in self.modes:
            raise ValueError(f"Unknown standings mode: {mode}")
        if mode == self.current_mode:
            return
        self.current_mode = mode
        self.buttons[mode].setChecked(True)
        self.motion.stop()
        self.motion.setStartValue(self.progress)
        self.motion.setEndValue(float(self.modes.index(mode)))
        self.motion.start()

    def advance(self, value):
        self.progress = float(value)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rects = [QRectF(self.buttons[mode].geometry()).adjusted(.5, .5, -.5, -.5)
                 for mode in self.modes]
        painter.setPen(QColor('#303744'))
        painter.setBrush(QColor('#1C212B'))
        for rect in rects:
            painter.drawRoundedRect(rect, 7, 7)
        left, right = rects
        rect = QRectF(left.x() + (right.x() - left.x()) * self.progress, left.y(),
                      left.width() + (right.width() - left.width()) * self.progress, left.height())
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor('#E5343D'))
        painter.drawRoundedRect(rect, 7, 7)
