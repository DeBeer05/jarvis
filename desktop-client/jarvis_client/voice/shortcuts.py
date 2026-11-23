import ctypes
from ctypes import wintypes
import sys

from PySide6.QtCore import QAbstractNativeEventFilter, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication


class GlobalFilter(QAbstractNativeEventFilter):
    def __init__(self, callbacks):
        super().__init__()
        self.callbacks = callbacks

    def nativeEventFilter(self, event_type, message):
        if sys.platform == "win32" and event_type in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x0312 and msg.wParam in self.callbacks:  # WM_HOTKEY
                self.callbacks[msg.wParam]()
                return True, 0
        return False, 0


class VoiceShortcuts:
    def __init__(self, window, ptt, stop):
        self.window, self.callbacks = window, (ptt, stop)
        self.local = []
        self.registered = []
        self.filter = GlobalFilter({0x4A50: ptt, 0x4A51: stop})
        QApplication.instance().installNativeEventFilter(self.filter)

    def configure(self, settings, global_enabled=False):
        sequences = [QKeySequence(settings.ptt_shortcut), QKeySequence(settings.stop_shortcut)]
        if any(sequence.isEmpty() or sequence.count() != 1 for sequence in sequences) or sequences[0] == sequences[1]:
            raise ValueError("Kies twee verschillende sneltoetsen met één toetscombinatie.")
        self.unregister()
        for shortcut in self.local:
            shortcut.setEnabled(False)
            shortcut.deleteLater()
        self.local = []
        for sequence, callback in zip(sequences, self.callbacks):
            shortcut = QShortcut(sequence, self.window)
            shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
            shortcut.activated.connect(callback)
            self.local.append(shortcut)
        if global_enabled:
            if sys.platform != "win32":
                raise ValueError("Globale spraaksneltoetsen zijn alleen beschikbaar op Windows.")
            try:
                for identifier, sequence in zip((0x4A50, 0x4A51), sequences):
                    combination = sequence[0]
                    key, modifiers = combination.key(), combination.keyboardModifiers()
                    native = {Qt.Key.Key_Space: 0x20, Qt.Key.Key_Escape: 0x1B}.get(key)
                    if Qt.Key.Key_A <= key <= Qt.Key.Key_Z or Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
                        native = int(key)
                    elif Qt.Key.Key_F1 <= key <= Qt.Key.Key_F12:
                        native = 0x70 + int(key) - int(Qt.Key.Key_F1)
                    if native is None:
                        raise ValueError("Gebruik voor globale sneltoetsen letters, cijfers, F1–F12, Space of Escape.")
                    mask = 0x4000  # MOD_NOREPEAT
                    for qt_modifier, windows_modifier in ((Qt.KeyboardModifier.AltModifier, 1), (Qt.KeyboardModifier.ControlModifier, 2),
                                                         (Qt.KeyboardModifier.ShiftModifier, 4), (Qt.KeyboardModifier.MetaModifier, 8)):
                        if modifiers & qt_modifier:
                            mask |= windows_modifier
                    if mask == 0x4000 or not ctypes.windll.user32.RegisterHotKey(None, identifier, mask, native):
                        raise ValueError("Globale sneltoets bezet of zonder modifier. Kies een andere combinatie.")
                    self.registered.append(identifier)
                for shortcut in self.local:
                    shortcut.setEnabled(False)
            except Exception:
                self.unregister()
                raise

    def unregister(self):
        if sys.platform == "win32":
            for identifier in self.registered:
                ctypes.windll.user32.UnregisterHotKey(None, identifier)
        self.registered.clear()
        for shortcut in self.local:
            shortcut.setEnabled(True)

    def close(self):
        self.unregister()
        QApplication.instance().removeNativeEventFilter(self.filter)
        for shortcut in self.local:
            shortcut.setEnabled(False)
