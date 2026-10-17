"""Expandable driver card and its background loader."""
from PySide6.QtCore import Qt, QThread, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPixmap
from pathlib import Path
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QGraphicsOpacityEffect
from .theme import TEAM_COLORS
from .motion import AnimatedPortrait


class CardViewport(QWidget):
    """Clip a full-size card instead of compressing its internal layout."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(0)
        self.card = DriverCard(self)
        self.card.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.card.setGeometry(0, 0, self.width(), 218)


class ProfileWorker(QThread):
    loaded = Signal(object, object)
    portrait_loaded = Signal(object, bytes)

    def __init__(self, service, entry, key, parent):
        super().__init__(parent)
        self.service, self.entry, self.key = service, entry, key

    def run(self):
        try:
            data = self.service.load(self.entry, self.key[1], self.key[2])
        except Exception:
            data = None
        self.loaded.emit(self.key, data)
        self.portrait_loaded.emit(self.key, self.service.portrait(self.entry))


class DriverCard(QFrame):
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("driverCard")
        self.setFixedHeight(218)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        body = QHBoxLayout()
        body.setSpacing(6)
        info_panel = QWidget()
        info_panel.setFixedWidth(118)
        self.text_opacity = QGraphicsOpacityEffect(info_panel)
        self.text_opacity.setOpacity(1.0)
        info_panel.setGraphicsEffect(self.text_opacity)
        self.text_motion = QPropertyAnimation(self.text_opacity, b"opacity", self)
        self.text_motion.setDuration(160)
        self.text_motion.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.info = QVBoxLayout(info_panel)
        self.info.setContentsMargins(0, 0, 0, 0)
        self.info.setSpacing(6)
        self.title = QLabel()
        self.title.setStyleSheet("font-size: 22px;")
        self.info.addWidget(self.title)
        self.close_button = QPushButton("×", self)
        self.close_button.setFixedSize(20, 20)
        self.close_button.setStyleSheet("padding: 0; border: none; background: transparent;")
        self.close_button.setToolTip("Close driver card")
        self.close_button.clicked.connect(self.closed)
        self.team = QLabel()
        self.team.setWordWrap(True)
        self.starts = QLabel()
        self.wins = QLabel()
        self.win_race = QLabel()
        self.win_race.setWordWrap(True)
        self.win_race.setStyleSheet("font-size: 9px; color: #9BA5B5;")
        self.win_race.setMaximumHeight(30)
        self.podiums = QLabel()
        self.position = QLabel()
        for widget in (self.team, self.starts, self.wins, self.podiums, self.position):
            widget.setStyleSheet("font-size: 11px;")
            self.info.addWidget(widget)
            if widget is self.wins:
                self.info.addWidget(self.win_race)
        self.info.addStretch()
        body.addWidget(info_panel)
        self.portrait = AnimatedPortrait("Loading photo…")
        self.portrait.setFixedSize(130, 170)
        self.portrait.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.portrait.setWordWrap(True)
        body.addWidget(self.portrait, 0, Qt.AlignmentFlag.AlignTop)
        body.addStretch(1)
        layout.addLayout(body)
        self.source = QLabel()
        self.source.setOpenExternalLinks(True)
        self.source.setStyleSheet("font-size: 8px; color: #818B9C;")
        layout.addWidget(self.source)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.close_button.move(self.width() - 26, 8)
        self.close_button.raise_()

    def set_driver(self, entry, season, round_number):
        self.stop_motion()
        self.custom_portrait = (Path(__file__).parent / "assets" / "portraits" / f"{entry.identity}.png").is_file()
        color = TEAM_COLORS.get(entry.team_id, "#8290A5")
        self.setStyleSheet(f"QFrame#driverCard {{ background: #191E27; border-left: 3px solid {color}; border-radius: 3px; }}")
        self.title.setText(f"{entry.number or '—'}  {entry.code}")
        self.title.setToolTip(entry.name)
        self.team.setText(f"Team: {entry.team}")
        self.team.setStyleSheet(f"font-size: 11px; color: {color};")
        self.starts.setText("Starts: …")
        self.wins.setText("Wins: …")
        self.wins.setToolTip("")
        self.win_race.hide()
        self.podiums.setText("Podiums: …")
        self.position.setText(f"WDC: P{entry.position} · {entry.points:g} pts")
        self.portrait.clear()
        self.portrait.setText("Loading photo…")
        self.portrait.setStyleSheet("background: transparent; color: #818B9C; font-size: 10px;")
        self.portrait.setToolTip(entry.name)
        self.source.setText(f"{season} · THROUGH ROUND {round_number} · LOADING")
        self.text_opacity.setOpacity(0.35)
        self.text_motion.setStartValue(0.35)
        self.text_motion.setEndValue(1.0)
        self.text_motion.start()

    def stop_motion(self):
        self.text_motion.stop()
        self.text_opacity.setOpacity(1.0)
        self.portrait.finish_motion()

    def set_stats(self, data):
        if data is None:
            self.starts.setText("Starts: unavailable")
            self.wins.setText("Wins: unavailable")
            self.podiums.setText("Podiums: unavailable")
            self.source.setText("Stats unavailable · close and reopen to retry")
            return
        self.starts.setText(f"Starts: {data['starts']} races")
        self.wins.setText(f"Wins: {len(data['wins'])}")
        self.wins.setToolTip("\n".join(data["wins"]) or "No Grand Prix wins this season")
        if data["wins"]:
            latest = data["wins"][-1].replace("Grand Prix", "GP")
            self.win_race.setText(latest if len(data["wins"]) == 1 else f"Latest: {latest}")
            self.win_race.show()
        self.podiums.setText(f"Podiums: {data['podiums']}")
        photo_credit = '<a style="color:#9BA5B5" href="https://uniqrenders.com">UniqRenders</a>' if self.custom_portrait else "OpenF1"
        self.source.setText(f"{data['source']} · Jolpica / {photo_credit} · GP stats")

    def set_portrait(self, content):
        pixmap = QPixmap()
        if content and pixmap.loadFromData(content):
            if self.custom_portrait:
                # Display the upper torso without changing the original PNG asset.
                height = int(pixmap.height() * 0.82)
                width = min(pixmap.width(), int(height * 130 / 170))
                pixmap = pixmap.copy((pixmap.width() - width) // 2, 0, width, height)
            self.portrait.present(pixmap.scaled(130, 170, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.portrait.setText("Photo unavailable")
