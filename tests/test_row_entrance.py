import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import time
import unittest
from unittest.mock import patch

from PySide6.QtCore import QAbstractAnimation, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from f1widget.window import StandingsWindow
from test_widget import table


class RowEntranceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = StandingsWindow(False)
        teams = {'season': '2025', 'round': '3', 'ConstructorStandings': [
            {'position': str(i + 1), 'points': str(100 - i),
             'Constructor': {'constructorId': f'team{i}', 'name': f'Team {i}'}}
            for i in range(10)]}
        self.data = {mode: {'current': current, 'previous': None,
                            'saved_at': time.time(), 'source': 'TEST'}
                     for mode, current in [('drivers', table()), ('teams', teams)]}
        self.window.data.update(self.data)
        self.window.render(self.data['drivers'])
        self.app.processEvents()

    def tearDown(self):
        self.window.stop_rows_motion()
        self.window.timer.stop()
        self.window.tray.hide()
        self.window.hide()
        self.window.deleteLater()
        self.app.processEvents()

    def test_stagger_and_duplicate_response_preserve_motion_and_scroll(self):
        window = self.window
        content = window.scroll.widget()
        content.motion.setCurrentTime(90)
        self.assertGreater(content.effects[0].opacity(), content.effects[3].opacity())
        self.assertEqual(content.effects[5].opacity(), 0)
        window.scroll.verticalScrollBar().setValue(48)
        window.on_loaded('drivers', dict(self.data['drivers'], source='Saved'))
        self.assertIs(window.scroll.widget(), content)
        self.assertEqual(content.motion.currentTime(), 90)
        self.assertEqual(window.scroll.verticalScrollBar().value(), 48)
        content.motion.setCurrentTime(content.motion.duration())
        self.assertTrue(all(effect.opacity() == 1 for effect in content.effects))

    def test_rapid_clicks_and_late_responses_leave_latest_table_visible(self):
        window = self.window
        geometry = window.scroll.geometry()
        with patch.object(window, 'load'):
            for i in range(121):
                mode = 'teams' if i % 2 == 0 else 'drivers'
                old_motion = window.scroll.widget().motion
                # Verify cancellation before Qt deletes the replaced table.
                with patch.object(old_motion, 'stop', wraps=old_motion.stop) as stop:
                    QTest.mouseClick(window.tabs.buttons[mode], Qt.MouseButton.LeftButton)
                    stop.assert_called_once()
                current = window.scroll.widget()
                other = 'drivers' if mode == 'teams' else 'teams'
                window.on_loaded(other, self.data[other])
                self.assertIs(window.scroll.widget(), current)
                if i % 7 == 0:
                    QTest.qWait(5)
                self.assertEqual(window.scroll.geometry(), geometry)
                self.assertEqual(window.height(), 520)
            QTest.qWait(360)
        content = window.scroll.widget()
        self.assertEqual(window.mode, 'teams')
        self.assertEqual(len(content.effects), 10)
        self.assertEqual(content.motion.state(), QAbstractAnimation.State.Stopped)
        self.assertTrue(all(effect.opacity() == 1 for effect in content.effects))

    def test_loading_message_cancels_then_new_table_animates(self):
        window = self.window
        window.data.pop('teams')
        with patch.object(window, 'load'):
            window.switch_mode('teams')
        self.assertIsNone(window.rendered_table)
        window.on_loaded('drivers', self.data['drivers'])
        self.assertEqual(window.scroll.widget().text(), 'LOADING STANDINGS…')
        window.on_loaded('teams', self.data['teams'])
        self.assertEqual(window.scroll.widget().motion.state(), QAbstractAnimation.State.Running)
