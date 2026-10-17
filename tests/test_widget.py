import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import tempfile
import time
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication
from f1widget.models import parse_entries, gap
from f1widget.service import StandingsService
from f1widget.window import StandingsWindow, ROW_HEIGHT


def table(count=12):
    return {"season": "2025", "round": "3", "DriverStandings": [
        {"position": str(i + 1), "points": str(100 - i * 3),
         "Driver": {"driverId": f"driver{i}", "code": ["VER", "LEC", "HAM", "NOR", "PIA", "RUS"][i % 6],
                    "givenName": "Test", "familyName": f"Driver{i}"},
         "Constructors": [{"constructorId": "ferrari", "name": "Ferrari"}]}
        for i in range(count)]}


class LogicTests(unittest.TestCase):
    def test_movement_and_fractional_gap(self):
        current, previous = table(), table()
        previous["DriverStandings"][0]["position"] = "3"
        self.assertEqual(parse_entries(current, "drivers", previous)[0].movement, 2)
        self.assertIsNone(parse_entries(current, "drivers")[0].movement)
        self.assertEqual(gap(Decimal("12.5"), Decimal("20")), "−7.5")
        self.assertEqual(gap(Decimal("20"), Decimal("20")), "—")

    def test_cache_and_offline_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            service = StandingsService(Path(directory))
            with patch.object(service, "fetch_table", return_value=table()) as fetch:
                self.assertEqual(service.load("drivers")["source"], "Live")
                self.assertEqual(fetch.call_args_list[1].args, ("2025", "drivers", 2))
            with patch.object(service, "fetch_table", side_effect=OSError("offline")) as fetch:
                self.assertEqual(service.load("drivers")["source"], "Saved")
                fetch.assert_not_called()
                self.assertEqual(service.load("drivers", True)["source"], "Offline · saved")

    def test_teams(self):
        data = {"ConstructorStandings": [{"position": "1", "points": "42", "Constructor": {"constructorId": "mclaren", "name": "McLaren"}}]}
        self.assertEqual(parse_entries(data, "teams")[0].name, "McLaren")

    def test_driver_numbers_are_not_championship_positions(self):
        data = table(2)
        data["DriverStandings"][0]["Driver"]["permanentNumber"] = "44"
        entries = parse_entries(data, "drivers")
        self.assertEqual(entries[0].number, "44")
        self.assertEqual(entries[0].position, 1)
        self.assertIsNone(entries[1].number)


class LayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setOrganizationName("WidgetF1Tests")

    def test_six_rows_and_scroll(self):
        window = StandingsWindow(autoload=False)
        window.render({"current": table(), "previous": None, "saved_at": time.time(), "source": "TEST DATA"})
        window.show()
        self.app.processEvents()
        self.assertEqual(window.scroll.viewport().height(), 6 * ROW_HEIGHT)
        self.assertEqual(window.scroll.verticalScrollBar().maximum(), 6 * ROW_HEIGHT)
        self.assertEqual(window.scroll.horizontalScrollBar().maximum(), 0)
        window.grab().save("preview.png")
        window.timer.stop()
        window.tray.hide()
        window.hide()


if __name__ == "__main__":
    unittest.main()
