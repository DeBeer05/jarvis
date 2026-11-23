import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication


class MemoryVault:
    def __init__(self):
        self.values = {}
    def load(self, origin):
        return self.values.get(origin)
    def save(self, origin, value):
        self.values[origin] = value
    def delete(self, origin):
        self.values.pop(origin, None)


@pytest.fixture
def vault():
    return MemoryVault()


@pytest.fixture(scope="session")
def qt():
    app=QApplication.instance() or QApplication([])
    if os.name=="nt" and os.environ.get("QT_QPA_PLATFORM")=="offscreen":
        from PySide6.QtGui import QFontDatabase
        from pathlib import Path
        font=Path(os.environ.get("WINDIR","C:/Windows"))/"Fonts/segoeui.ttf"
        if font.exists():QFontDatabase.addApplicationFont(str(font))
    return app
