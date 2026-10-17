"""Fixed-size desktop shell; networking runs outside the GUI thread."""
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QStandardPaths, QTimer, QSettings
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication, QWidget, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QScrollArea, QButtonGroup, QSystemTrayIcon, QMenu,
)
from .models import parse_entries, gap
from .service import StandingsService
from .theme import STYLE, TEAM_COLORS
from .fonts import interface_font

ROW_HEIGHT = 48


class FetchWorker(QThread):
    loaded = Signal(str, object)
    failed = Signal(str, str)

    def __init__(self, service, mode, force, parent):
        super().__init__(parent)
        self.service, self.mode, self.force = service, mode, force

    def run(self):
        try:
            self.loaded.emit(self.mode, self.service.load(self.mode, self.force))
        except Exception as error:
            self.failed.emit(self.mode, str(error))


def label(text, width=None, name=None):
    widget = QLabel(text)
    if width:
        widget.setFixedWidth(width)
    if name:
        widget.setObjectName(name)
    return widget


class StandingsWindow(QWidget):
    def __init__(self, autoload=True):
        super().__init__()
        self.setWindowTitle("F1 Standings")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(390, 520)
        family = interface_font().replace("'", "\\'")
        self.setStyleSheet(STYLE.replace("'Segoe UI'", f"'{family}'"))
        self.settings = QSettings()
        self.mode = "drivers"
        self.data = {}
        self.workers = {}
        self.pending_quit = False
        self.service = StandingsService(Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)))
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        panel = QFrame(objectName="panel")
        root.addWidget(panel)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(10)
        top = QHBoxLayout()
        title = QVBoxLayout()
        title.setSpacing(0)
        title.addWidget(label("WORLD CHAMPIONSHIP", name="eyebrow"))
        title.addWidget(label("F1 STANDINGS", name="brand"))
        top.addLayout(title)
        top.addStretch()
        self.pin = QPushButton("PIN")
        self.pin.setCheckable(True)
        self.pin.setToolTip("Keep widget on top")
        self.pin.clicked.connect(self.toggle_pin)
        top.addWidget(self.pin)
        close = QPushButton("×")
        close.setFixedWidth(30)
        close.setToolTip("Hide to tray")
        close.clicked.connect(self.close)
        top.addWidget(close)
        layout.addLayout(top)
        self.subtitle = label("CHAMPIONSHIP / WAITING FOR DATA", name="muted")
        layout.addWidget(self.subtitle)
        tabs = QHBoxLayout()
        self.group = QButtonGroup(self)
        for mode in ("drivers", "teams"):
            button = QPushButton(mode.upper())
            button.setCheckable(True)
            button.setChecked(mode == self.mode)
            button.clicked.connect(lambda checked, mode=mode: self.switch_mode(mode))
            self.group.addButton(button)
            tabs.addWidget(button)
        layout.addLayout(tabs)
        header = QHBoxLayout()
        header.setContentsMargins(6, 0, 11, 0)
        for text, width in (("POS", 34), ("", 28), ("ENTRY", 145), ("PTS", 57), ("GAP", 45)):
            header.addWidget(label(text, width, "muted"))
        header.setSpacing(0)
        layout.addLayout(header)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFixedHeight(6 * ROW_HEIGHT)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.scroll.verticalScrollBar().setSingleStep(ROW_HEIGHT)
        layout.addWidget(self.scroll)
        bottom = QHBoxLayout()
        self.status = label("Connecting to Jolpica…", name="muted")
        bottom.addWidget(self.status, 1)
        self.refresh = QPushButton("↻")
        self.refresh.setToolTip("Refresh standings")
        self.refresh.clicked.connect(lambda: self.load(True))
        bottom.addWidget(self.refresh)
        layout.addLayout(bottom)
        self.message("LIGHTS OUT. DATA INCOMING.")
        self.setup_tray()
        self.pin.setChecked(self.settings.value("pinned", False, type=bool))
        self.toggle_pin()
        position = self.settings.value("position")
        if position is not None and any(s.availableGeometry().contains(position) for s in QApplication.screens()):
            self.move(position)
        self.timer = QTimer(self)
        self.timer.setInterval(60 * 60 * 1000)
        self.timer.timeout.connect(self.load)
        self.timer.start()
        if autoload:
            QTimer.singleShot(0, self.load)

    def setup_tray(self):
        self.setWindowIcon(QIcon(str(Path(__file__).parent / "assets" / "app.ico")))
        self.tray = QSystemTrayIcon(self.windowIcon(), self)
        self.tray.setToolTip("F1 Standings")
        menu = QMenu(self)
        menu.addAction("Show widget", self.restore)
        menu.addAction("Refresh", lambda: self.load(True))
        menu.addSeparator()
        menu.addAction("Quit", self.quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.restore() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def restore(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def toggle_pin(self):
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self.pin.isChecked())
        self.settings.setValue("pinned", self.pin.isChecked())
        self.show()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() < 92:
            self.windowHandle().startSystemMove()
        super().mousePressEvent(event)

    def closeEvent(self, event):
        self.settings.setValue("position", self.pos())
        event.ignore()
        if self.tray.isVisible():
            self.hide()
        else:
            self.quit()

    def quit(self):
        self.settings.setValue("position", self.pos())
        self.pending_quit = True
        self.timer.stop()
        self.hide()
        self.tray.hide()
        if not self.workers:
            QApplication.quit()

    def switch_mode(self, mode):
        self.mode = mode
        if mode in self.data:
            self.render(self.data[mode])
        else:
            self.message("LOADING STANDINGS…")
            self.subtitle.setText("CHAMPIONSHIP / WAITING FOR DATA")
        self.load()

    def load(self, force=False):
        if self.pending_quit:
            return
        mode = self.mode
        if mode in self.workers:
            self.refresh.setEnabled(False)
            return
        self.refresh.setEnabled(False)
        self.status.setText("Updating…")
        worker = FetchWorker(self.service, mode, force, self)
        worker.loaded.connect(self.on_loaded)
        worker.failed.connect(self.on_failed)
        worker.finished.connect(lambda: self.worker_finished(mode))
        self.workers[mode] = worker
        worker.start()

    def worker_finished(self, mode):
        self.workers.pop(mode).deleteLater()
        self.refresh.setEnabled(self.mode not in self.workers)
        if self.pending_quit and not self.workers:
            QApplication.quit()

    def on_loaded(self, mode, data):
        self.data[mode] = data
        if mode == self.mode:
            self.render(data)

    def on_failed(self, mode, error):
        if mode == self.mode:
            self.status.setText("Connection failed · click ↻ to retry")
            self.status.setToolTip(error)
            if mode not in self.data:
                self.message("NO STANDINGS YET\nCheck your connection and refresh.")

    def message(self, text):
        message = label(text)
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setStyleSheet("color: #818B9C; background: transparent;")
        self.scroll.setWidget(message)

    def render(self, data):
        current = data["current"]
        try:
            entries = parse_entries(current, self.mode, data.get("previous"))
        except (KeyError, ValueError, TypeError):
            self.on_failed(self.mode, "Invalid standings response")
            return
        self.subtitle.setText(f"{current['season']} SEASON   /   ROUND {int(current['round']):02d}")
        stamp = datetime.fromtimestamp(data["saved_at"]).strftime("%d %b · %H:%M")
        self.status.setText(f"{data['source']} · {stamp}")
        self.status.setToolTip("Jolpica F1 · positions compared with the previous round")
        if not entries:
            self.message("STANDINGS NOT AVAILABLE")
            return
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        rows = QVBoxLayout(content)
        rows.setContentsMargins(0, 0, 0, 0)
        rows.setSpacing(0)
        for entry in entries:
            row = QFrame(objectName="standingRow")
            row.setFixedHeight(ROW_HEIGHT)
            row.setStyleSheet("QFrame#standingRow { background: #191E27; border-bottom: 1px solid #292F3A; border-radius: 0; }")
            line = QHBoxLayout(row)
            line.setContentsMargins(6, 0, 0, 0)
            line.setSpacing(0)
            pos = label(f"{entry.position:02d}", 34)
            pos.setStyleSheet("color: #9BA5B5; font-weight: 700;")
            line.addWidget(pos)
            change = entry.movement
            movement = "—" if change is None else "•" if change == 0 else f"{'▲' if change > 0 else '▼'}{abs(change)}"
            move = label(movement, 28)
            move.setStyleSheet(f"font-size: 9px; color: {'#57D5A0' if change and change > 0 else '#F36A75' if change else '#677384'};")
            move.setToolTip("Change since previous round" if change is not None else "Previous round unavailable")
            line.addWidget(move)
            identity = QWidget()
            identity.setFixedWidth(145)
            identity_layout = QHBoxLayout(identity)
            identity_layout.setContentsMargins(0, 7, 4, 7)
            identity_layout.setSpacing(8)
            stripe = QLabel()
            stripe.setFixedSize(3, 28)
            stripe.setStyleSheet(f"background: {TEAM_COLORS.get(entry.team_id, '#8290A5')}; border-radius: 1px;")
            identity_layout.addWidget(stripe)
            if self.mode == "drivers":
                number = label(entry.number or "—", 32, "driverNumber")
                number.setAlignment(Qt.AlignmentFlag.AlignCenter)
                number.setStyleSheet("color: #9BA5B5; font-size: 16px; font-weight: 700;")
                number.setToolTip("Permanent driver number · Jolpica")
                identity_layout.addWidget(number)
            name = label(entry.code if self.mode == "drivers" else entry.name.upper())
            name.setStyleSheet(f"font-size: {20 if self.mode == 'drivers' else 11}px; font-weight: 800; letter-spacing: 1px;")
            if self.mode == "teams":
                name.setText(name.fontMetrics().elidedText(entry.name.upper(), Qt.TextElideMode.ElideRight, 126))
            name.setToolTip(f"{entry.name} · {entry.team}")
            identity_layout.addWidget(name)
            line.addWidget(identity)
            points = label(f"{entry.points:g}", 57)
            points.setStyleSheet("font-weight: 800; font-size: 15px;")
            line.addWidget(points)
            difference = label(gap(entry.points, entries[0].points), 45)
            difference.setStyleSheet("color: #818B9C; font-size: 11px;")
            line.addWidget(difference)
            rows.addWidget(row)
        rows.addStretch()
        self.scroll.setWidget(content)
