import argparse
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtCore import QLockFile, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from jarvis_client import __version__
from jarvis_client.settings import SettingsStore
from jarvis_client.vault import VaultError, WindowsVault
from jarvis_client.window import MainWindow
from jarvis_client.activation import WindowActivation,show_existing


def main():
    parser = argparse.ArgumentParser(description="JARVIS Windows desktop client")
    parser.add_argument("--minimized", action="store_true")
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--self-test-report", type=Path)
    options = parser.parse_args()
    application = QApplication.instance() or QApplication([])
    application.setApplicationName("JARVIS Desktop")
    application.setOrganizationName("JARVIS")
    application.setQuitOnLastWindowClosed(False)
    store = SettingsStore(options.data_dir)
    store.directory.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(store.directory / "client.lock"))
    if not lock.tryLock(0):
        if show_existing(store.directory):return 0
        QMessageBox.information(None, "JARVIS", "JARVIS draait al. Open de app vanuit het systeemvak.")
        return 1
    activation=None
    try:
        preferences = store.load()
        vault = WindowsVault()
        if options.self_test_report:
            preferences.auto_connect = False
            preferences.notifications = False
        handler = RotatingFileHandler(store.directory / "client.log", maxBytes=262144, backupCount=2, encoding="utf-8")
        logger = logging.getLogger("jarvis.client")
        logger.setLevel(getattr(logging, preferences.log_level.upper()))
        logger.addHandler(handler)
        voice_logger = logging.getLogger("jarvis.voice")
        voice_logger.setLevel(logging.WARNING)
        voice_logger.addHandler(handler)
        logger.info("client_started version=%s", __version__)
        window = MainWindow(store, vault, preferences=preferences)
        activation=WindowActivation(store.directory,window.restore)
        if preferences.language == "en":
            for nav, title in zip(window.nav, ("Chat", "Conversations", "Devices", "Notifications", "Settings", "Account", "Voice")):
                nav.setText(title)
        if not options.minimized or not window.tray.isVisible():
            window.show()
        if options.self_test_report:
            def smoke():
                options.self_test_report.write_text(json.dumps({"version": __version__, "qt_window": window.isVisible(), "pages": window.pages.count(), "network_started": window.manager.busy, "microphone_active": window.voice.recording, "voice_worker_started": window.voice.worker.process is not None, "tray_available": window.tray.isSystemTrayAvailable()}), encoding="utf-8")
                window.shutdown()
            QTimer.singleShot(1000, smoke)
        result = application.exec()
        logger.info("client_stopped")
        handler.close()
        logger.removeHandler(handler)
        voice_logger.removeHandler(handler)
        return result
    except (ValueError, VaultError, OSError):
        QMessageBox.critical(None, "JARVIS starten", "De client kan instellingen of Windows Credential Manager niet openen. Gegevens zijn behouden; controleer de handleiding.")
        return 2
    finally:
        if activation:activation.close()
        lock.unlock()
