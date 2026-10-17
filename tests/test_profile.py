import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import unittest
from PySide6.QtWidgets import QApplication
from f1widget.models import parse_entries
from f1widget.profile import summarize
from f1widget.window import StandingsWindow
from test_widget import table


class ProfileTests(unittest.TestCase):
    def test_animation_interruptions_keep_latest_driver_and_stop_on_close(self):
        from PySide6.QtCore import QAbstractAnimation, QBuffer, QIODevice
        from PySide6.QtGui import QImage, QColor
        from PySide6.QtTest import QTest
        app = QApplication.instance() or QApplication([])
        window = StandingsWindow(False)
        window.current_season, window.current_round = "2025", 3
        image = QImage(24, 24, QImage.Format.Format_ARGB32)
        image.fill(QColor('red'))
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer, 'PNG')
        portrait = bytes(buffer.data())
        entries = parse_entries(table(4), 'drivers')
        for entry in entries:
            key = (entry.identity, '2025', 3)
            window.profile_results[key] = {'starts': 3, 'wins': [], 'podiums': 0, 'source': 'Saved'}
            window.portraits[key] = portrait
        for entry in entries * 20:
            window.select_driver(entry)
            QTest.qWait(2)
        final_key = (entries[-1].identity, '2025', 3)
        self.assertEqual(window.selected_driver, final_key)
        self.assertIn(entries[-1].code, window.card.title.text())
        window.portrait_loaded((entries[0].identity, '2025', 3), b'late invalid photo')
        self.assertFalse(window.card.portrait.image.isNull())
        QTest.qWait(240)
        self.assertAlmostEqual(window.card.text_opacity.opacity(), 1)
        self.assertAlmostEqual(window.card.portrait.progress, 1)
        window.select_driver(entries[0])
        window.close_card()
        QTest.qWait(240)
        self.assertFalse(window.card.isVisible())
        self.assertEqual(window.card.text_motion.state(), QAbstractAnimation.State.Stopped)
        self.assertEqual(window.card.portrait.motion.state(), QAbstractAnimation.State.Stopped)
        self.assertEqual(window.height(), 520)
        window.timer.stop()
        window.tray.hide()
        window.hide()

    def test_top_four_expand_and_collapse_without_layout_drift(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QPushButton
        import time
        app = QApplication.instance() or QApplication([])
        window = StandingsWindow(False)
        data = table(6)
        window.render({"current": data, "saved_at": time.time(), "source": "Saved"})
        for entry in parse_entries(data, "drivers")[:4]:
            key = (entry.identity, "2025", 3)
            window.profile_results[key] = {"starts": 3, "wins": [], "podiums": 0, "source": "Saved"}
            window.portraits[key] = b""
        app.processEvents()
        collapsed_list = window.scroll.geometry()
        for entry in parse_entries(data, "drivers")[:4] * 25:
            button = next(b for b in window.findChildren(QPushButton) if b.text() == entry.code)
            QTest.mouseClick(button, Qt.MouseButton.LeftButton)
            app.processEvents()
            self.assertTrue(window.card.isVisible())
            self.assertEqual(window.scroll.geometry(), collapsed_list)
            self.assertEqual(window.scroll.height(), 288)
            self.assertLess(window.scroll.geometry().bottom(), window.card.y())
            self.assertTrue(window.panel.rect().contains(window.card.geometry()))
            QTest.mouseClick(button, Qt.MouseButton.LeftButton)
            app.processEvents()
            self.assertEqual(window.height(), 520)
            self.assertEqual(window.scroll.geometry(), collapsed_list)
        window.timer.stop()
        window.tray.hide()
        window.hide()

    def test_stats_exclude_future_round_and_non_starts(self):
        races = [{"round": str(i), "raceName": f"Race {i}", "Results": [
            {"position": pos, "status": status}]} for i, pos, status in
            [(1, "1", "Finished"), (2, "3", "Finished"), (3, "20", "Did not start"),
             (4, "12", "Engine"), (5, "1", "Finished")]]
        stats = summarize(races, 4)
        self.assertEqual(stats, {"starts": 3, "wins": ["Race 1"], "podiums": 2})

    def test_toggle_switch_and_ignore_stale_response(self):
        app = QApplication.instance() or QApplication([])
        window = StandingsWindow(False)
        window.current_season, window.current_round = "2025", 3
        entries = parse_entries(table(2), "drivers")
        for entry in entries:
            key = (entry.identity, "2025", 3)
            window.profile_results[key] = {"starts": 3, "wins": [], "podiums": 0, "source": "Saved"}
            window.portraits[key] = b""
        window.select_driver(entries[0])
        app.processEvents()
        self.assertEqual(window.height(), 748)
        self.assertEqual(window.scroll.viewport().height(), 288)
        window.select_driver(entries[1])
        window.profile_loaded((entries[0].identity, "2025", 3), {"starts": 99, "wins": [], "podiums": 0, "source": "Live"})
        self.assertEqual(window.card.starts.text(), "Starts: 3 races")
        window.select_driver(entries[1])
        self.assertEqual(window.height(), 520)
        self.assertIsNone(window.selected_driver)
        window.timer.stop()
        window.tray.hide()
        window.hide()
