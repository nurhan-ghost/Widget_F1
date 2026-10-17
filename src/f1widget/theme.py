"""Visual tokens and constructor accents."""
TEAM_COLORS = {
    "ferrari": "#E8002D", "mclaren": "#FF8000", "mercedes": "#27F4D2",
    "red_bull": "#4781EF", "aston_martin": "#229971", "alpine": "#F282B4",
    "williams": "#64C4FF", "rb": "#6692FF", "racing_bulls": "#6692FF",
    "haas": "#D9DEE2", "sauber": "#52E252", "audi": "#F23A46", "cadillac": "#C4B6A0",
}

STYLE = """
QWidget { color: #EEF1F5; font-family: 'Segoe UI'; font-size: 12px; }
QFrame#panel { background: rgba(15, 18, 24, 245); border: 1px solid #30353F; border-radius: 16px; }
QLabel { background: transparent; border: none; }
QLabel#brand { font-size: 22px; font-weight: 900; font-style: italic; letter-spacing: 1px; }
QLabel#eyebrow { color: #FC4C51; font-size: 10px; font-weight: 800; letter-spacing: 2px; }
QLabel#muted { color: #818B9C; font-size: 10px; }
QPushButton { background: #1C212B; border: 1px solid #303744; border-radius: 7px; padding: 7px 10px; font-weight: 700; }
QPushButton:hover { background: #2A313F; }
QPushButton:checked { background: #E5343D; color: white; border-color: #E5343D; }
QPushButton:disabled { color: #626B79; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { width: 5px; background: #171B23; margin: 0; }
QScrollBar::handle:vertical { background: #485161; border-radius: 2px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QMenu { background: #1C212B; padding: 6px; }
QMenu::item:selected { background: #E5343D; }
"""
