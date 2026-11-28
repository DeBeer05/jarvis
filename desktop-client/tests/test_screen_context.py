from concurrent.futures import ThreadPoolExecutor

from PySide6.QtGui import QImage,QPixmap
from PySide6.QtWidgets import QWidget
import pytest

from jarvis_client.screen_context import capture_png,ScreenPanel


class SyntheticScreen:
    def grabWindow(self,identifier):
        assert identifier==0
        image=QImage(2000,1200,QImage.Format.Format_RGB888);image.fill(0x204060)
        return QPixmap.fromImage(image)


def test_capture_helper_scales_synthetic_pixels_without_real_screen_or_network(qt):
    data,image=capture_png(SyntheticScreen())
    assert data.startswith(b'\x89PNG\r\n\x1a\n') and len(data)<=1_800_000
    assert image.width()<=1600 and image.height()<=1000
    assert b'tEXt' not in data and b'iCCP' not in data


def test_capture_cannot_touch_screen_from_worker_thread(qt):
    with ThreadPoolExecutor(max_workers=1) as executor:
        with pytest.raises(RuntimeError,match='hoofdthread'):executor.submit(capture_png,SyntheticScreen()).result()


def test_screen_preview_is_bound_to_settings_and_does_not_grant_consent_on_load(qt):
    class Host(QWidget):
        revision=3
        def __init__(self):super().__init__();self.calls=[]
        def call(self,method,path,body,done,*args):
            self.calls.append((method,path,body))
            if path.endswith('/device-settings'):done({'revision':1,'settings':{'screen_allowed':True}})
            elif path.endswith('/settings'):done({'revision':self.revision,'settings':{'vision':{'enabled':True,'provider':'gemini','daily_requests':10}}})
    host=Host();panel=ScreenPanel(host)
    assert not host.calls
    panel.refresh();assert all(method=='GET' for method,_,_ in host.calls)
    panel.image=b'synthetic';panel.analyze()
    assert host.calls[-1][2]['settings_revision']==3
    panel.image=b'synthetic';host.revision=4;panel.refresh()
    assert panel.image is None and not panel.send.isEnabled()
    panel.clear();host.close()
