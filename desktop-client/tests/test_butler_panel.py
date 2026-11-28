"""User-form retries, revision binding and logout privacy without a server or screen."""
from copy import deepcopy
from datetime import datetime

from PySide6.QtWidgets import QWidget,QLineEdit,QComboBox

from jarvis_client.butler_panel import ButlerPanel


class Host(QWidget):
    def __init__(self):super().__init__();self.requests=[];self.principal={'permissions':[]}
    def call(self,method,path,body,done,failed):self.requests.append((method,path,deepcopy(body),done,failed))


SCHEMA={'labels':{'shopping':'Boodschappen','routine':'Routines'},'kinds':{
    'shopping':{'properties':{'name':{'type':'string','maxLength':120},'amount':{'type':'string','default':''},'checked':{'type':'boolean','default':False}}},
    'routine':{'properties':{'name':{'type':'string'},'at':{'type':'string'},'repeat':{'enum':['once','daily'],'default':'once'}}}}}


def panel(qt):
    host=Host();page=ButlerPanel(host);assert not host.requests
    page.load_schema();host.requests[-1][3](deepcopy(SCHEMA));host.requests[-1][3]({'items':[],'has_more':False})
    return host,page


def test_failed_save_reuses_key_and_edit_changes_it(qt):
    host,page=panel(qt)
    page.form.itemAt(1).widget().setText('Synthetisch brood')
    page.save_item();first=host.requests[-1];assert first[0]=='POST' and first[2]['data']['name']=='Synthetisch brood'
    first[4](RuntimeError('Synthetic failure'))
    page.save_item();second=host.requests[-1]
    assert second[2]['request_id']==first[2]['request_id']
    second[4](RuntimeError('Synthetic failure'))
    page.form.itemAt(1).widget().setText('Synthetische melk');page.save_item()
    assert host.requests[-1][2]['request_id']!=first[2]['request_id']
    page.clear();host.close()


def test_revision_and_calendar_offset_preserved_in_forms(qt):
    host,page=panel(qt);page.kind.setCurrentIndex(1)
    current={'id':'synthetic','kind':'routine','revision':4,'data':{'name':'Synthetic','at':'2027-02-01T14:00:00+01:00','repeat':'once'}}
    host.requests[-1][3]({'items':[current],'has_more':False});page.list.setCurrentRow(0)
    page.save_item();body=host.requests[-1][2]
    assert host.requests[-1][0]=='PUT' and body['revision']==4
    assert datetime.fromisoformat(body['data']['at']).tzinfo is not None and '[' not in body['data']['at']
    page.clear();host.close()


def test_logout_clears_private_fields_and_rejects_late_response(qt):
    host,page=panel(qt);page.origin.setText('Synthetic origin');page.mail.setText('synthetic-mail-id')
    page.inbox();late=host.requests[-1][3];page.clear()
    late({'items':[{'created':1,'payload':{'text':'Private synthetic briefing'}}]})
    assert not page.report.toPlainText() and not page.origin.text() and not page.mail.text()
    assert not page.editor.findChildren(QLineEdit)
    host.close()


def test_advisory_reminder_is_not_reported_as_scheduled(qt):
    host,page=panel(qt);page.current={'id':'synthetic','revision':1}
    page.remind_item();host.requests[-1][3]({'status':'advisory'})
    assert 'geen herinnering actief' in page.status.text()
    page.clear();host.close()


def test_autonomy_enum_uses_choices_and_explicit_ask_is_saved(qt):
    from types import SimpleNamespace
    from jarvis_client.natural_settings import NaturalSettingsPanel
    holder=SimpleNamespace(schema={'actions':['ReminderList','CalendarDelete'],'mandatory_approval':['CalendarDelete']},changed=lambda *_:None)
    field={'type':'object','additionalProperties':{'type':'string','enum':['allow','ask','block','advise']}}
    widget,read=NaturalSettingsPanel.field(holder,field,{})
    combos=widget.findChildren(QComboBox)
    assert len(combos)==2 and read()=={}
    combos[0].setCurrentIndex(combos[0].findData('ask'))
    assert read()=={'ReminderList':'ask'}
    assert combos[1].findData('allow')==-1
    combos[1].setCurrentIndex(combos[1].findData('advise'))
    assert read()['CalendarDelete']=='advise'
    widget.close()
