"""Absolute imports let PyInstaller discover the application package."""
import sys

from f1widget.app import main


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--smoke-test":
        # Exercise the frozen Qt runtime, HTTPS, cache and window without VS Code.
        import json
        from pathlib import Path
        from PySide6.QtWidgets import QApplication
        from f1widget.window import StandingsWindow, ROW_HEIGHT

        output = Path(sys.argv[2])
        try:
            app = QApplication([])
            app.setApplicationName("F1 Standings")
            app.setOrganizationName("WidgetF1")
            window = StandingsWindow(autoload=False)
            data = window.service.load("drivers", force=True)
            window.render(data)
            app.processEvents()
            assert not window.windowIcon().pixmap(32, 32).isNull(), "App icon is missing"
            assert window.scroll.viewport().height() == ROW_HEIGHT * 6
            assert window.scroll.verticalScrollBar().maximum() > 0
            assert data["source"].startswith("Live"), data["source"]
            window.grab().save(str(output.with_suffix(".png")))
            output.write_text(json.dumps({"ok": True, "frozen": bool(getattr(sys, "frozen", False)),
                                          "source": data["source"], "visible_rows": 6}), encoding="utf-8")
            window.timer.stop()
            window.tray.hide()
        except Exception as error:
            output.write_text(json.dumps({"ok": False, "error": str(error)}), encoding="utf-8")
            sys.exit(1)
    else:
        main()
