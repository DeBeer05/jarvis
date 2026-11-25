import threading
import time

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QSystemTrayIcon

from jarvis_client.connection import Jobs, ConnectionManager
from jarvis_client.api import ClientError
from jarvis_client.settings import Preferences, SettingsStore
from jarvis_client.window import MainWindow


class Manager(QObject):
    changed = Signal(str)
    authenticated = Signal(object)
    problem = Signal(object)
    def __init__(self, preferences, vault, jobs, parent):
        super().__init__(parent)
        self.preferences, self.api, self.busy = preferences, None, False
        self.state, self.generation, self.pinned = "offline", 0, False
        self.started, self.stopped = 0, False
    def start(self):
        self.started += 1
    def stop(self):
        self.stopped = True
    def reset(self):
        self.generation += 1


def window(tmp_path, vault):
    return MainWindow(SettingsStore(tmp_path), vault, preferences=Preferences(auto_connect=False), manager_factory=Manager)


def test_voice_page_keeps_written_overview_when_spoken_answer_is_short(qt,tmp_path,vault,monkeypatch):
    app=window(tmp_path,vault)
    app.running=True;app.server_speech=True;app.reply='';app.rows=[('JARVIS','')]
    spoken=[]
    def delta(text,*,ready=False):
        spoken.append((text,ready));app.voice.answer.emit(text)
    monkeypatch.setattr(app.voice,'delta',delta)
    monkeypatch.setattr(app,'notify',lambda *args:None)
    try:
        app.stream_event({'type':'speech','text':'Ik zet uitjes voor u klaar.'})
        app.stream_event({'type':'delta','text':'1. Wandeling\n2. Museum'})
        assert app.voice_panel.answer.toPlainText()=='1. Wandeling\n2. Museum'
        app.stream_event({'type':'speech','text':'De lijst staat in de app.'})
        assert app.voice_panel.answer.toPlainText()=='1. Wandeling\n2. Museum'
        app.stream_event({'type':'done','status':'completed','message':'1. Wandeling\n2. Museum\nControleer openingstijden.'})
        assert 'Controleer openingstijden.' in app.voice_panel.answer.toPlainText()
        assert all('Museum' not in text and ready for text,ready in spoken)
        assert not app.voice.recording
    finally:
        app.running=False;app.closing=True;app.tray.hide();app.close()


def test_initialization_navigation_and_safe_defaults(qt, tmp_path, vault):
    app = window(tmp_path, vault)
    app.show()
    qt.processEvents()
    assert app.pages.count() == 8 and app.isVisible()
    assert not app.send_button.isEnabled() and not app.delete_button.isEnabled()
    assert not app.setting_checks["startup"].isChecked()
    for index in range(8):
        app.navigate(index)
        assert app.pages.currentIndex() == index and app.nav[index].isChecked()
    assert not app.voice.consent and not app.voice.recording and not app.voice.wake_enabled
    app.closing = True
    app.tray.hide()
    app.close()


def test_automation_filters_and_logout_clear_private_data(qt,tmp_path,vault):
    app=window(tmp_path,vault)
    panel=app.automation_panel
    panel.all_items=[{"id":"synthetic","tool":"EmailSend","status":"approval","payload":{"preview":"Private synthetic body"}}]
    panel.filter_jobs();panel.jobs.setCurrentRow(0)
    assert "Private synthetic body" in panel.details.toPlainText()
    panel.tabs.setCurrentIndex(4);assert panel.jobs.count()==1
    panel.clear();panel.tabs.setCurrentIndex(3)
    assert panel.jobs.count()==0 and not panel.details.toPlainText()
    app.navigate(7);app.show();qt.processEvents()
    assert app.automation_panel.isVisible()
    app.grab().save(str(tmp_path/"automation-screen.png"))
    app.closing=True;app.tray.hide();app.close()


def test_worker_callbacks_return_on_main_thread(qt):
    jobs = Jobs()
    main_thread = threading.get_ident()
    seen, events = [], []
    jobs.submit(lambda emit: (emit("stream"), threading.get_ident())[1], lambda result: seen.append((result, threading.get_ident())), lambda error: seen.append(error), events.append)
    deadline = time.monotonic() + 3
    while (not seen or jobs.active) and time.monotonic() < deadline:
        qt.processEvents()
        time.sleep(0.01)
    assert seen[0][0] != main_thread and seen[0][1] == main_thread
    assert events == ["stream"] and not jobs.active


def test_plaintext_rendering_settings_and_permission_control(qt, tmp_path, vault):
    app = window(tmp_path, vault)
    app.rows = [("JARVIS", '<script>alert("test")</script>')]
    app.render()
    assert '<script>' in app.transcript.toPlainText()
    app.system_info()
    assert "niet toegestaan" in app.notice.text()
    app.local_permission.setChecked(True)
    app.system_info()
    assert "cpu_threads" in app.notice.text()
    app.theme_choice.setCurrentIndex(app.theme_choice.findData("light"))
    app.save_settings()
    assert SettingsStore(tmp_path).load().theme == "light"
    app.closing = True
    app.tray.hide()
    app.close()


def test_tray_close_vs_full_shutdown(qt, tmp_path, vault, monkeypatch):
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", lambda: True)
    app = window(tmp_path, vault)
    app.show()
    qt.processEvents()
    app.close()
    assert not app.isVisible() and not app.closing and app.tray.isVisible()
    app.restore()
    assert app.isVisible()
    app.shutdown()
    assert app.closing and app.manager.stopped and not app.tray.isVisible()
    app.shutdown_timer.stop()
    app.close()


def test_connection_manager_reconnects_and_uses_separate_origin_credentials(qt, vault):
    attempts, origins = [], []
    class Api:
        def __init__(self, origin, vault):
            self.origin = origin
            origins.append(origin)
        def probe(self):
            attempts.append(1)
            if len(attempts) == 1:
                raise ClientError("network", "offline")
        def session(self):
            return {"session_id": "synthetic", "permissions": []}
        def close(self):
            pass
    jobs = Jobs()
    manager = ConnectionManager(Preferences(), vault, jobs, factory=Api)
    states = []
    manager.changed.connect(states.append)
    manager.start()
    deadline = time.monotonic() + 4
    while manager.state != "online" and time.monotonic() < deadline:
        qt.processEvents()
        time.sleep(0.01)
    manager.stop()
    assert states == ["offline", "online"] and len(attempts) == 2
    assert origins == ["http://127.0.0.1:8765"] * 2
