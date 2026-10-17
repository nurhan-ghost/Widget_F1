"""Application entry point."""
import sys
from PySide6.QtWidgets import QApplication
from .window import StandingsWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("F1 Standings")
    app.setOrganizationName("WidgetF1")
    window = StandingsWindow()
    window.show()
    sys.exit(app.exec())
