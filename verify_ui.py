"""Render real Qt pages and check layout at the caller's QT_SCALE_FACTOR."""
import os
from pathlib import Path
import tempfile
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication, QPushButton, QLineEdit, QComboBox, QSpinBox, QLabel, QMessageBox, QWidget
from goose_studio import Studio
from PyQt6.QtTest import QTest

app = QApplication.instance() or QApplication([])
app.setStyle('Fusion')
scale = os.environ.get('QT_SCALE_FACTOR', '1')
out = Path('ui-verification')
out.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as data:
    w = Studio(Path(data), demo=True)
    w.quiet.setChecked(True)
    w.store.add_task('Read one chapter', 'School', 'High')
    w.refresh_tasks()
    for width, height in [(600, 440), (960, 640), (1100, 780)]:
        w.resize(width, height)
        w.show()
        for page in range(4):
            w.navigate(page)
            for _ in range(5):
                app.processEvents()
            QTest.qWait(150)  # Let native Windows resize/scrollbar events settle.
            area = w.pages.currentWidget()
            content = area.widget()
            if content.width() > area.viewport().width():
                for item in content.findChildren(QWidget):
                    if item.minimumSizeHint().width() > 250 or item.minimumWidth() > 250:
                        print('WIDTH_DIAGNOSTIC', type(item).__name__, getattr(item, 'text', lambda: '')()[:160], item.minimumSizeHint().width(), item.minimumWidth(), item.sizeHint().width(), item.sizePolicy().horizontalPolicy(), flush=True)
            assert content.width() <= area.viewport().width(), (width, page, 'horizontal overflow', content.width(), area.viewport().width())
            for control in content.findChildren((QPushButton, QLineEdit, QComboBox, QSpinBox)):
                if not control.isVisible():
                    continue
                assert control.height() >= control.minimumSizeHint().height(), (width, page, control.text() if hasattr(control, 'text') else type(control).__name__, control.height(), control.minimumSizeHint().height())
            assert w.time_label.height() >= 100
            w.grab().save(str(out / f'page-{page}-{width}x{height}-scale-{scale}.png'))
            area.verticalScrollBar().setValue(area.verticalScrollBar().maximum())
            app.processEvents()
            if page == 3:
                w.grab().save(str(out / f'controls-bottom-{width}-scale-{scale}.png'))
            area.verticalScrollBar().setValue(0)
    w.clock.toggle()
    w.clock.remaining -= 15
    remaining = w.clock.remaining
    w.close()
    app.processEvents()
    assert not w.isVisible()
    assert w.clock.running
    assert w.clock.remaining <= remaining
    assert w.store.tasks()
    w.open_dashboard()
    app.processEvents()
    assert w.isVisible()
    with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.No):
        assert w.request_quit()
    assert w._closed
print(f'UI checks passed at scale {scale}: 4 pages x 3 sizes, close/reopen/quit lifecycle')
