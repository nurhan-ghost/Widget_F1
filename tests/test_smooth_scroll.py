import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import time
import unittest
from unittest.mock import patch

from PySide6.QtCore import QPoint, QPointF, Qt, QAbstractAnimation
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QAbstractSlider

from f1widget.window import StandingsWindow
from test_widget import table


class SmoothScrollTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = StandingsWindow(False)
        teams = {'season': '2025', 'round': '3', 'ConstructorStandings': [
            {'position': str(i + 1), 'points': str(100 - i),
             'Constructor': {'constructorId': f'team{i}', 'name': f'Team {i}'}}
            for i in range(10)]}
        self.window.data = {mode: {'current': data, 'previous': None,
                                  'saved_at': time.time(), 'source': 'TEST'}
                            for mode, data in [('drivers', table(22)), ('teams', teams)]}
        self.window.render(self.window.data['drivers'])
        self.app.processEvents()
        self.scroll = self.window.scroll
        self.bar = self.scroll.verticalScrollBar()

    def tearDown(self):
        self.scroll.stop_motion()
        self.window.timer.stop()
        self.window.tray.hide()
        self.window.hide()
        self.window.deleteLater()
        self.app.processEvents()

    def wheel(self, angle=-120, pixel=0, receiver=None):
        receiver = receiver or self.scroll.viewport()
        point = receiver.rect().center()
        event = QWheelEvent(QPointF(point), QPointF(receiver.mapToGlobal(point)),
                            QPoint(0, pixel), QPoint(0, angle), Qt.MouseButton.NoButton,
                            Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
        self.app.sendEvent(receiver, event)

    def test_burst_clamps_and_reverse_discards_old_target(self):
        for _ in range(200):
            self.wheel()
        self.assertEqual(self.scroll.target, self.bar.maximum())
        self.scroll.motion.setCurrentTime(60)
        current = self.bar.value()
        self.assertGreater(current, 0)
        self.assertLess(current, self.bar.maximum())
        self.wheel(120)
        self.assertEqual(self.scroll.motion.startValue(), current)
        self.assertEqual(self.scroll.target, current - 48)
        QTest.qWait(210)
        self.assertEqual(self.bar.value(), current - 48)
        self.assertEqual(self.scroll.motion.state(), QAbstractAnimation.State.Stopped)
        for _ in range(200):
            self.wheel(120)
        QTest.qWait(210)
        self.assertEqual(self.bar.value(), 0)

    def test_native_controls_and_pixel_scroll_cancel_animation(self):
        self.wheel(receiver=self.bar)
        self.scroll.motion.setCurrentTime(50)
        self.bar.setValue(200)
        QTest.qWait(210)
        self.assertEqual(self.bar.value(), 200)
        self.wheel()
        self.bar.triggerAction(QAbstractSlider.SliderAction.SliderSingleStepSub)
        expected = self.bar.value()
        QTest.qWait(210)
        self.assertEqual(self.bar.value(), expected)
        self.wheel()
        self.wheel(0, -13)
        self.assertEqual(self.bar.value(), expected + 13)
        self.assertEqual(self.scroll.motion.state(), QAbstractAnimation.State.Stopped)

    def test_fast_scroll_and_mode_switches_reset_motion_and_keep_geometry(self):
        geometry = self.scroll.geometry()
        with patch.object(self.window, 'load'):
            for i in range(80):
                self.wheel(-1200)
                self.scroll.motion.setCurrentTime(35)
                mode = 'teams' if i % 2 == 0 else 'drivers'
                self.window.switch_mode(mode)
                self.app.processEvents()
                self.assertEqual(self.bar.value(), 0)
                self.assertEqual(self.scroll.motion.state(), QAbstractAnimation.State.Stopped)
                self.assertEqual(self.scroll.geometry(), geometry)
                self.assertEqual(self.window.height(), 520)
            self.wheel(-12000)
            QTest.qWait(210)
            self.assertEqual(self.bar.value(), self.bar.maximum())
            self.window.message('LOADING')
            QTest.qWait(210)
            self.assertEqual(self.bar.value(), 0)

    def test_scrolling_keeps_every_visible_row_painted(self):
        with patch.object(self.window, 'load'):
            for index, mode in enumerate(('drivers', 'teams', 'drivers', 'teams')):
                self.window.switch_mode(mode)
                # Scroll both during the entrance and after it has finished.
                if index >= 2:
                    QTest.qWait(350)
                # Include partially clipped rows and the fifth/sixth row boundary.
                for offset in (1, 47, 48, 191, 192, 239, 240, 241, 96, 0):
                    self.bar.setValue(min(offset, self.bar.maximum()))
                    self.app.processEvents()
                    self.assertTrue(all(row.graphicsEffect() is None
                                        for row in self.scroll.widget().rows))
                    image = self.scroll.viewport().grab().toImage()
                    scale = image.devicePixelRatio()
                    for y in range(0, self.scroll.viewport().height(), 8):
                        if (y + self.bar.value()) % 48 == 47:
                            continue
                        color = image.pixelColor(round(2 * scale), round(y * scale))
                        self.assertGreaterEqual(color.red(), 25,
                                                (mode, offset, y, color.name()))
                        self.assertGreaterEqual(color.alpha(), 250,
                                                (mode, offset, y, color.name()))
