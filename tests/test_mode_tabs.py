import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import unittest
from unittest.mock import patch
from PySide6.QtCore import Qt, QAbstractAnimation
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from f1widget.mode_tabs import ModeTabs
from f1widget.window import StandingsWindow


class ModeTabsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_reverse_starts_at_current_position_and_ignores_repeat(self):
        tabs = ModeTabs()
        tabs.resize(352, 32)
        tabs.show()
        events = []
        tabs.mode_requested.connect(events.append)
        tabs.request_mode('teams')
        tabs.motion.setCurrentTime(70)
        halfway = tabs.progress
        self.assertGreater(halfway, 0)
        self.assertLess(halfway, 1)
        tabs.request_mode('drivers')
        self.assertAlmostEqual(tabs.motion.startValue(), halfway)
        tabs.request_mode('drivers')
        self.assertEqual(events, ['teams', 'drivers'])
        QTest.qWait(250)
        self.assertAlmostEqual(tabs.progress, 0)
        self.assertEqual(tabs.motion.state(), QAbstractAnimation.State.Stopped)
        tabs.close()

    def test_rapid_clicks_keep_window_mode_and_geometry_in_sync(self):
        window = StandingsWindow(False)
        self.app.processEvents()
        geometry = window.scroll.geometry()
        with patch.object(window, 'load'):
            for i in range(101):
                mode = 'teams' if i % 2 == 0 else 'drivers'
                QTest.mouseClick(window.tabs.buttons[mode], Qt.MouseButton.LeftButton)
                if i % 7 == 0:
                    QTest.qWait(3)
                self.assertEqual(window.mode, mode)
                self.assertTrue(window.tabs.buttons[mode].isChecked())
            QTest.qWait(250)
            self.assertEqual(window.tabs.progress, 1)
            self.assertEqual(window.scroll.geometry(), geometry)
            self.assertEqual(window.height(), 520)
            window.switch_mode('drivers')
            self.assertTrue(window.tabs.buttons['drivers'].isChecked())
        window.timer.stop()
        window.tray.hide()
        window.hide()
