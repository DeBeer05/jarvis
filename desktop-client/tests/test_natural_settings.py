from copy import deepcopy

from PySide6.QtWidgets import QWidget, QDoubleSpinBox

from jarvis_client.natural_settings import NaturalSettingsPanel


class Window(QWidget):
    def __init__(self):
        super().__init__();self.principal={"device_id":"synthetic"};self.calls=[]
    def call(self,method,path,body,success,failure=None):
        self.calls.append((method,path,deepcopy(body),success))
    def navigate(self,index):self.page=index


SCHEMA={"categories":{"ai":"AI en prestaties","personality":"Persoonlijkheid","autonomy":"Zelfstandigheid"},"actions":["CalendarRead","EmailSend"],"mandatory_approval":["EmailSend"],"user":{"properties":{key:{"$ref":"#/$defs/"+key} for key in ("ai","personality","autonomy")},"$defs":{
    "ai":{"properties":{"offline":{"type":"boolean","default":False},"temperature":{"type":"number","minimum":0,"maximum":1}}},
    "personality":{"properties":{"humor":{"type":"integer","minimum":0,"maximum":100},"profile":{"type":"string","enum":["friendly","professional"]},"custom_instructions":{"type":"string","maxLength":2000}}},
    "autonomy":{"properties":{"actions":{"type":"object"}}}}}}
DOCUMENT={"revision":7,"settings":{"ai":{"offline":False,"temperature":.2},"personality":{"humor":35,"profile":"friendly","custom_instructions":""},"autonomy":{"actions":{}}}}


def panel(qt):
    window=Window();view=NaturalSettingsPanel(window);view.schema=deepcopy(SCHEMA);view.loaded(deepcopy(DOCUMENT));return window,view


def test_typed_controls_preserve_categories_and_save_revision(qt):
    window,view=panel(qt)
    assert view.categories.count()==3 and not view.dirty
    control=view.scroll.widget().findChild(QDoubleSpinBox);control.setValue(.4)
    assert view.dirty
    view.categories.setCurrentRow(1)
    assert view.draft["ai"]["temperature"]==.4
    view.save()
    method,path,body,_=window.calls[-1]
    assert method=="PUT" and path.endswith("/settings") and body["revision"]==7
    assert body["settings"]["ai"]["temperature"]==.4 and body["settings"]["personality"]["humor"]==35
    assert not view.tabs.isEnabled() and view.loading
    view.failed(RuntimeError("synthetic conflict"))
    assert view.tabs.isEnabled() and view.dirty and view.draft["ai"]["temperature"]==.4
    view.cancel();assert not view.dirty and view.draft==DOCUMENT["settings"]
    window.close()


def test_save_uses_immutable_snapshot_until_server_reply(qt):
    window,view=panel(qt);requests=[]
    window.call=lambda method,path,body,success,failure=None:requests.append(body)
    view.scroll.widget().findChild(QDoubleSpinBox).setValue(.6);view.save()
    view.draft["ai"]["temperature"]=.8
    assert requests[-1]["settings"]["ai"]["temperature"]==.6
    view.failed(RuntimeError("synthetic network failure"))
    assert view.tabs.isEnabled() and view.draft["ai"]["temperature"]==.8
    window.close()


def test_search_and_mandatory_approval_choices_do_not_escalate(qt):
    from PySide6.QtWidgets import QComboBox
    window,view=panel(qt)
    view.search.setText("humor")
    assert view.categories.item(0).isHidden() and not view.categories.item(1).isHidden()
    view.search.clear();view.categories.setCurrentRow(2)
    combos=view.scroll.widget().findChildren(QComboBox)
    assert len(combos)==2 and combos[1].findData("allow")==-1
    view.collect();assert view.draft["autonomy"]["actions"]=={}
    combos[0].setCurrentIndex(combos[0].findData("block"));view.save()
    assert window.calls[-1][2]["settings"]["autonomy"]["actions"]=={"CalendarRead":"block"}
    window.close()


def test_logout_removes_personal_context_and_searches(qt):
    window,view=panel(qt)
    view.memory_loaded({"items":[{"id":"synthetic","content":"Private synthetic memory","category":"project","status":"active"}]})
    view.summaries_loaded({"items":[{"id":"synthetic","conversation_id":"synthetic","content":"Private synthetic summary"}]})
    view.memory_search.setText("Private search");view.clear()
    assert not view.tabs.isEnabled() and not view.memory_list.count() and not view.summary_text.toPlainText()
    assert not view.memory_search.text() and view.document is None
    window.close()


def test_diagnostics_show_unknown_measurements_without_inventing_gpu_or_audio(qt):
    window,view=panel(qt)
    view.diagnostics_loaded({"active_provider":"ollama","voice":{"capabilities":{"runtime_installed":False},"inference_busy":False},"sessions":[],"memory_counts":{"active":2},"resources":{"resident_bytes":10485760},"latency":{"stt_ms":1234,"context_tokens":900},"events":[]})
    assert view.diagnostic_labels["stt"].text()=="1.234 s" and view.diagnostic_labels["gpu"].text()=="Niet gemeten"
    assert view.diagnostic_labels["audio"].text()=="Nog niet gemeten" and "10.0 MiB" in view.diagnostic_labels["ram"].text()
    view.clear();assert view.diagnostic_document is None and view.diagnostic_labels["memory"].text()=="Nog niet gemeten"
    window.close()


def test_personality_preview_uses_unsaved_draft_without_saving(qt):
    window,view=panel(qt)
    view.categories.setCurrentRow(1)
    view.draft["personality"]["humor"]=80
    # collect() reads the visible controls, so edit through the actual input.
    from PySide6.QtWidgets import QSpinBox
    view.scroll.widget().findChild(QSpinBox).setValue(80)
    view.preview_personality()
    method,path,body,_=window.calls[-1]
    assert method=="POST" and path.endswith("/personality/preview")
    assert body["personality"]["humor"]==80
    assert view.document["settings"]["personality"]["humor"]==35 and view.dirty
    window.close()
