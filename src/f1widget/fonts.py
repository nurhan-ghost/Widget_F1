"""Load user-supplied typefaces once, without installing system fonts."""
from functools import lru_cache
from pathlib import Path

from PySide6.QtGui import QFontDatabase


@lru_cache(maxsize=1)
def interface_font() -> str:
    directory = Path(__file__).parent / "assets" / "fonts"
    families = []
    for path in sorted(directory.glob("*")):
        if path.suffix.lower() not in (".ttf", ".otf"):
            continue
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id >= 0:
            families.extend(QFontDatabase.applicationFontFamilies(font_id))
    return next(iter(families), "Segoe UI")
