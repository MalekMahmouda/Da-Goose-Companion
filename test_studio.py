"""Regression tests: python -m unittest test_studio -v.
Headless Linux: QT_QPA_PLATFORM=offscreen python -m unittest test_studio -v
"""
import csv
import io
import json
import urllib.error
from datetime import datetime, timedelta
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from goose_studio import FocusClock, Store, Studio, QApplication, QMessageBox, SKINS, PeekWorker


class ClockTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.timer = FocusClock(lambda: self.now)
        self.timer.configure(1)

    def test_active_time(self):
        self.timer.toggle()
        self.now += 15
        self.assertFalse(self.timer.tick())
        self.assertEqual(self.timer.remaining, 45)

    def test_pause_does_not_count(self):
        self.timer.toggle()
        self.now += 10
        self.timer.toggle()
        self.now += 100
        self.timer.tick()
        self.assertEqual(self.timer.remaining, 50)
        self.timer.toggle()
        self.now += 5
        self.timer.tick()
        self.assertEqual(self.timer.remaining, 45)

    def test_completion_only_once(self):
        self.timer.toggle()
        self.now += 61
        self.assertTrue(self.timer.tick())
        self.assertFalse(self.timer.tick())
        self.assertEqual(self.timer.remaining, 0)

    def test_invalid_duration(self):
        for value in [0, -1, 181]:
            with self.assertRaises(ValueError):
                self.timer.configure(value)

    def test_break_mode(self):
        self.timer.configure(5, 'break')
        self.assertEqual(self.timer.mode, 'break')
        self.assertEqual(self.timer.remaining, 300)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)/'test.sqlite3'
        self.s = Store(self.path)

    def tearDown(self):
        self.s.db.close()
        self.tmp.cleanup()

    def test_add_search_complete_reopen(self):
        tid = self.s.add_task('Read chapter', 'School', 'High')
        self.assertEqual(len(self.s.tasks('school')), 1)
        self.s.toggle(tid)
        self.assertEqual(len(self.s.tasks()), 0)
        self.assertEqual(len(self.s.tasks(show_done=True)), 1)
        self.s.toggle(tid)
        self.assertEqual(len(self.s.tasks()), 1)

    def test_priority_order(self):
        self.s.add_task('Low', priority='Low')
        self.s.add_task('High', priority='High')
        self.assertEqual(self.s.tasks()[0]['title'], 'High')

    def test_blank_task_rejected(self):
        with self.assertRaises(ValueError):
            self.s.add_task('   ')

    def test_preferences_persist(self):
        self.s.set_pref('quiet', True)
        other = Store(self.path)
        self.assertTrue(other.pref('quiet'))
        other.db.close()

    def test_partial_not_completed(self):
        self.s.log_session(125, completed=False)
        self.assertEqual(self.s.week()[-1][1:], (125, 0))

    def test_week_zero_filled(self):
        self.assertEqual(len(self.s.week()), 7)
        self.assertEqual(sum(r[1] for r in self.s.week()), 0)
        yesterday = (datetime.now()-timedelta(days=1)).isoformat()
        self.s.log_session(60, ended=yesterday)
        self.assertEqual(self.s.week()[-2][1], 60)

    def test_delete_retains_history(self):
        tid = self.s.add_task('Test')
        self.s.log_session(60, tid)
        self.s.delete(tid)
        self.assertEqual(self.s.week()[-1][1], 60)
        new_id = self.s.add_task('A different task')
        self.assertNotEqual(new_id, tid)
        row = self.s.db.execute('SELECT task_id FROM sessions').fetchone()
        self.assertIsNone(row['task_id'])

    def test_export_is_safe_for_spreadsheets(self):
        tid = self.s.add_task('=2+2', '+project')
        self.s.log_session(60, tid)
        path = Path(self.tmp.name)/'export.csv'
        self.s.export(path)
        with path.open(encoding='utf-8-sig') as f:
            rows = list(csv.reader(f))
        self.assertEqual(rows[1][2], "'=2+2")
        self.assertEqual(rows[1][3], "'+project")


class UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.w = Studio(Path(self.tmp.name), demo=True)
        self.w.show()
        self.app.processEvents()

    def tearDown(self):
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.No):
            self.w.close()
        self.app.processEvents()
        self.tmp.cleanup()

    def test_all_pages_render(self):
        for index in range(4):
            self.w.navigate(index)
            self.app.processEvents()
            self.assertFalse(self.w.grab().isNull())

    def test_task_link_and_completion(self):
        self.w.task_title.setText('Ship a small feature')
        self.w.add_task()
        self.assertEqual(self.w.task_list.count(), 1)
        self.w.task_list.setCurrentRow(0)
        self.w.focus_selected()
        self.assertIsNotNone(self.w.focus_task.currentData())
        self.w.toggle_task()
        self.assertEqual(self.w.task_list.count(), 0)

    def test_completion_transitions_to_break_once(self):
        self.w.clock.configure(1)
        self.w.clock.remaining = 0.01
        self.w.clock.running = True
        self.w.clock._last -= 1
        self.w.tick()
        self.assertEqual(self.w.clock.mode, 'break')
        self.assertEqual(self.w.store.week()[-1][1:], (60, 1))
        self.w.tick()
        self.assertEqual(self.w.store.week()[-1][1:], (60, 1))

    def test_break_not_logged(self):
        self.w.clock.configure(1, 'break')
        self.w.clock.remaining = 0.01
        self.w.clock.running = True
        self.w.clock._last -= 1
        self.w.tick()
        self.assertEqual(self.w.clock.mode, 'focus')
        self.assertEqual(self.w.store.week()[-1][1], 0)

    def test_partial_session_saved(self):
        self.w.clock.remaining -= 62
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
            self.w.reset_focus()
        self.assertEqual(self.w.store.week()[-1][1:], (62, 0))

    def test_cancel_reset_preserves_timer(self):
        self.w.clock.remaining -= 45
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Cancel):
            self.assertFalse(self.w.reset_focus())
        self.assertGreaterEqual(self.w.clock.elapsed, 45)

    def test_no_key_no_capture(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': ''}), patch('goose_studio.capture_desktop_thumbnail') as capture:
            self.w.peek()
            capture.assert_not_called()

    def test_decline_no_capture(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-only'}), patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.No), patch('goose_studio.capture_desktop_thumbnail') as capture:
            self.w.peek()
            capture.assert_not_called()
            self.assertIn('Cancelled', self.w.ai_result.text())

    def test_wardrobe_all_skins_render(self):
        for index in range(self.w.skin.count()):
            self.w.skin.setCurrentIndex(index)
            self.w.preview.animate()
            self.assertFalse(self.w.preview.grab().isNull())

    def test_reminders(self):
        self.w.store.set_pref('water', True)
        self.w.last_water -= 2701
        self.w.tick()
        self.assertIn('sip of water', self.w.coach_text.text())

    def test_finish_click_on_boundary_logs_full_session(self):
        self.w.clock.configure(1)
        self.w.clock.remaining = 0.01
        self.w.clock.running = True
        self.w.clock._last -= 1
        self.w.reset_focus()
        self.assertEqual(self.w.store.week()[-1][1:], (60, 1))

    def test_mocked_peek_success_and_secret_cleanup(self):
        worker = PeekWorker('mock-image', 'test-only', 'example-model')
        messages = []
        worker.result.connect(messages.append)
        payload = {'candidates': [{'content': {'parts': [{'text': 'A local test response'}]}}]}
        with patch('urllib.request.urlopen', return_value=io.BytesIO(json.dumps(payload).encode())):
            worker.run()
        self.assertEqual(messages, ['A local test response'])
        self.assertEqual(worker.key, '')
        self.assertEqual(worker.image, '')

    def test_mocked_peek_http_error_hides_key(self):
        worker = PeekWorker('mock-image', 'test-only', 'example-model')
        messages = []
        worker.result.connect(messages.append)
        with patch('urllib.request.urlopen', side_effect=urllib.error.HTTPError('https://example.invalid', 429, 'limited', {}, None)):
            worker.run()
        self.assertIn('HTTP 429', messages[0])
        self.assertNotIn('test-only', messages[0])
        self.assertEqual(worker.key, '')

    def test_floating_companion_and_shutdown(self):
        self.w.quiet.setChecked(True)
        self.w.show_goose()
        self.app.processEvents()
        self.assertIsNotNone(self.w.goose)
        self.assertTrue(self.w.goose.quiet)
        self.assertFalse(self.w.goose.ai_timer.isActive())
        self.w.goose.monitor.stop()
        self.w.goose.monitor.wait(4000)


if __name__ == '__main__':
    unittest.main()
