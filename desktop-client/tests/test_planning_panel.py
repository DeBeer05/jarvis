from PySide6.QtWidgets import QWidget
from jarvis_client.planning_panel import PlanningPanel


class Window(QWidget):
    def __init__(self):
        super().__init__();self.conversation='first';self.principal={'device_id':'synthetic'};self.running=False;self.calls=[];self.sent=[];self.notices=[]
    def call(self,*args):self.calls.append(args)
    def send_voice_text(self,text):self.sent.append(text)
    def show_notice(self,text):self.notices.append(text)


def test_late_overview_cannot_replace_another_conversation(qt):
    window=Window();panel=PlanningPanel(window)
    panel.refresh();callback=window.calls[-1][3]
    window.conversation='second';callback({'planning':{'overview':'Old private plan'}})
    assert not panel.overview.toPlainText()
    panel.refresh();window.calls[-1][3]({'planning':{'overview':'New plan'}})
    assert panel.overview.toPlainText()=='New plan'
    window.principal=None;panel.refresh()
    assert 'New plan' not in panel.overview.toPlainText()
    window.close()


def test_edits_use_existing_chat_and_running_turn_keeps_text(qt):
    window=Window();panel=PlanningPanel(window);panel.edit.setText('Doe toch zondag.')
    window.running=True;panel.apply()
    assert panel.edit.text() and not window.sent and window.notices
    window.running=False;panel.apply()
    assert window.sent==['Doe toch zondag.'] and not panel.edit.text()
    window.close()
