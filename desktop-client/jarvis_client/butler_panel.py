"""Native butler controls using existing authenticated worker requests."""
from datetime import datetime
from copy import deepcopy
from uuid import uuid4

from PySide6.QtCore import Qt,QDateTime
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QTabWidget,QPushButton,QLabel,
    QPlainTextEdit,QLineEdit,QComboBox,QFormLayout,QSpinBox,QCheckBox,QDateTimeEdit,QListWidget,QMessageBox,QDoubleSpinBox)

N='/api/v1/natural';A='/api/v1/automation'
LABELS={'name':'Naam','amount':'Aantal / bedrag','checked':'Afgevinkt','currency':'Valuta','cycle':'Periode','month':'Maand','day':'Dag','time':'Tijd (uu:mm)','category':'Soort','at':'Moment','repeat':'Herhaling','company':'Werkgever','status':'Voortgang','followup_at':'Opvolgmoment'}
VALUES={'monthly':'Maandelijks','yearly':'Jaarlijks','weekly':'Wekelijks','daily':'Dagelijks','once':'Eenmalig','birthday':'Verjaardag','anniversary':'Jubileum','prepared':'Voorbereid','sent':'Verzonden','reply_review':'Reactie controleren','interview':'Gesprek','rejected':'Afgewezen','offered':'Aanbod','closed':'Afgesloten'}


def plain(text=''):
    item=QLabel(text);item.setWordWrap(True);item.setTextFormat(Qt.TextFormat.PlainText);return item


class ButlerPanel(QWidget):
    def __init__(self,window):
        super().__init__(window);self.window=window;self.serial=0;self.busy=False;self.schema={};self.rows=[];self.current=None;self.controls={};self.pending=None
        layout=QVBoxLayout(self);self.status=plain('Open uw briefings, lijsten en gekoppelde apparaten, meneer.');layout.addWidget(self.status)
        self.tabs=QTabWidget();layout.addWidget(self.tabs)
        overview=QWidget();box=QVBoxLayout(overview);self.tabs.addTab(overview,'Briefings en meldingen')
        bar=QHBoxLayout();box.addLayout(bar)
        for title,path,method in (('Ochtendbriefing','/briefings/morning','GET'),('Avondbriefing','/briefings/evening','GET'),('Terugkomstbriefing','/briefings/return','GET'),('Briefings inplannen','/briefings/schedule','POST')):
            button=QPushButton(title);button.clicked.connect(lambda _=False,p=path,m=method:self.call(m,N+p,{} if m=='POST' else None,self.briefing));bar.addWidget(button)
        refresh=QPushButton('Meldingen en briefinggeschiedenis');refresh.clicked.connect(self.inbox);box.addWidget(refresh)
        self.report=QPlainTextEdit();self.report.setReadOnly(True);box.addWidget(self.report)
        safety=QHBoxLayout();box.addLayout(safety)
        for title,callback in (('Noodstop',self.stop),('Veiligheidsstatus',self.health),('Stop opheffen als eigenaar',self.resume)):
            button=QPushButton(title);button.clicked.connect(callback);safety.addWidget(button)
        self.make_lists();self.make_integrations()

    def call(self,method,path,body,done):
        serial=self.serial
        def complete(data):
            if serial==self.serial:self.busy=False;done(data)
        def failed(error):
            if serial==self.serial:self.busy=False;self.status.setText(getattr(error,'message','Niet bevestigd. Controleer uw verbinding, rechten en invoer.'))
        self.window.call(method,path,body,complete,failed)

    def clear(self):
        self.serial+=1;self.busy=False;self.schema={};self.rows=[];self.current=None;self.pending=None
        self.report.clear();self.integration_report.clear();self.list.clear();self.new_item()
        self.status.setText('Log in om uw persoonlijke butler te gebruiken.');self.mail.clear();self.origin.clear();self.destination.clear();self.distance.setValue(0)

    def briefing(self,data):
        if 'text' in data:self.report.setPlainText(data['text'])
        elif 'scheduled' in data:
            self.report.setPlainText('Ingeplande briefings: '+str(len(data['scheduled']))+'. Alleen in JARVIS; geen oproep gestart.'+(' Controleer geblokkeerde kanalen in uw instellingen.' if data.get('blocked') else ''))

    def inbox(self):
        self.call('GET',N+'/events?history=true',None,lambda data:self.report.setPlainText('\n\n'.join(datetime.fromtimestamp(item['created']).astimezone().strftime('%d-%m %H:%M')+'\n'+item['payload'].get('text','') for item in data['items']) or 'Er staan geen recente meldingen klaar, meneer.'))

    def stop(self):
        self.window.stop_answer()
        self.call('POST',A+'/safety',{'active':True},lambda _:self.status.setText('Noodstop actief. Taken blijven gepauzeerd tot u ze zelf hervat.'))

    def resume(self):
        if not self.window.principal or 'admin:account' not in self.window.principal['permissions']:
            self.window.automation_panel.open_rights();self.status.setText('Hef de stop op in eigenaarbeheer. Daarna hervat u taken afzonderlijk.');return
        self.call('POST',A+'/safety',{'active':False},lambda _:self.status.setText('Noodstop opgeheven; taken blijven afzonderlijk gepauzeerd.'))

    def health(self):
        def show(data):
            self.report.setPlainText(('Noodstop actief' if data['stopped'] else 'Geen noodstop')+'\nScheduler: '+('actief' if data['scheduler_enabled'] else 'uitgeschakeld')+'\nTaken te laat: '+str(data['overdue'])+'\nOnzekere uitkomsten: '+str(data['counts'].get('uncertain',0))+'\nGeen automatische herhaling van onzekere externe wijzigingen.')
        self.call('GET',A+'/health',None,show)

    def make_lists(self):
        page=QWidget();box=QVBoxLayout(page);self.tabs.addTab(page,'Persoonlijke lijsten')
        bar=QHBoxLayout();box.addLayout(bar);self.kind=QComboBox();bar.addWidget(self.kind)
        self.kind.currentIndexChanged.connect(lambda _:self.load_items())
        refresh=QPushButton('Lijsten ophalen');refresh.clicked.connect(self.load_schema);bar.addWidget(refresh)
        self.list=QListWidget();self.list.currentRowChanged.connect(self.select_item);box.addWidget(self.list)
        self.editor=QWidget();self.form=QFormLayout(self.editor);box.addWidget(self.editor)
        actions=QHBoxLayout();box.addLayout(actions)
        for title,callback in (('Nieuw',self.new_item),('Opslaan',self.save_item),('Verwijderen',self.delete_item),('Herinnering instellen',self.remind_item),('Kostenoverzicht',self.costs)):
            button=QPushButton(title);button.clicked.connect(callback);actions.addWidget(button)
        self.mail=QLineEdit();self.mail.setPlaceholderText('Optionele berichtreferentie uit uw gelezen sollicitatiemail');box.addWidget(self.mail)
        link=QPushButton('Gelezen reactie koppelen aan sollicitatie');link.clicked.connect(self.link_mail);box.addWidget(link)

    def load_schema(self):
        def loaded(data):
            self.schema=data;self.kind.blockSignals(True);self.kind.clear()
            for key,title in data['labels'].items():self.kind.addItem(title,key)
            self.kind.blockSignals(False);self.load_items()
        self.call('GET',N+'/life-items/schema',None,loaded)

    def load_items(self):
        if not self.schema or not self.kind.currentData():return
        expected=self.kind.currentData()
        def loaded(data):
            if self.kind.currentData()!=expected:return
            self.rows=data['items'];self.list.clear()
            for row in self.rows:self.list.addItem(('✓ ' if row['data'].get('checked') else '')+row['data']['name'])
            self.new_item();self.status.setText('Lijst bijgewerkt.'+(' Toon een specifiekere lijst; maximaal 200 items zichtbaar.' if data['has_more'] else ''))
        self.call('GET',N+'/life-items?kind='+self.kind.currentData(),None,loaded)

    def select_item(self,index):
        self.current=self.rows[index] if 0<=index<len(self.rows) else None;self.edit_item()

    def new_item(self):
        self.current=None;self.pending=None
        if hasattr(self,'form'):self.edit_item()

    def edit_item(self):
        while self.form.count():
            item=self.form.takeAt(0)
            if item.widget():
                widget=item.widget();widget.hide();widget.setParent(None);widget.deleteLater()
        self.controls={}
        if not self.schema or not self.kind.currentData():return
        definition=self.schema['kinds'][self.kind.currentData()];data=self.current['data'] if self.current else {}
        for key,field in definition['properties'].items():
            if field.get('x-internal'):continue
            value=data.get(key,field.get('default'));title=LABELS.get(key,field.get('title',key));kind=field.get('type')
            if key in ('at','followup_at'):
                widget=QWidget();bar=QHBoxLayout(widget);bar.setContentsMargins(0,0,0,0)
                enabled=QCheckBox('Ingesteld');enabled.setChecked(value is not None or key=='at');bar.addWidget(enabled)
                date=QDateTimeEdit();date.setCalendarPopup(True);date.setDisplayFormat('dd-MM-yyyy HH:mm');date.setDateTime(QDateTime.fromString(value,Qt.DateFormat.ISODate) if value else QDateTime.currentDateTime().addDays(1));bar.addWidget(date)
                date.setEnabled(enabled.isChecked());enabled.toggled.connect(date.setEnabled)
                self.controls[key]=lambda d=date,e=enabled:d.dateTime().toPython().astimezone().isoformat() if e.isChecked() else None
            elif 'enum' in field:
                widget=QComboBox()
                for choice in field['enum']:widget.addItem(VALUES.get(choice,choice),choice)
                widget.setCurrentIndex(max(0,widget.findData(value)));self.controls[key]=widget.currentData
            elif kind=='boolean':
                widget=QCheckBox();widget.setChecked(bool(value));self.controls[key]=widget.isChecked
            elif kind=='integer':
                widget=QSpinBox();widget.setRange(field.get('minimum',0),field.get('maximum',100000));widget.setValue(value if value is not None else field.get('minimum',0));self.controls[key]=widget.value
            else:
                widget=QLineEdit('' if value is None else str(value));widget.setMaxLength(field.get('maxLength',200));self.controls[key]=widget.text
            self.form.addRow(plain(title),widget)

    def save_item(self):
        if self.busy or not self.controls:return
        data=deepcopy(self.current['data']) if self.current else {};data.update({key:read() for key,read in self.controls.items()})
        if self.kind.currentData()=='subscription':data['amount']=data['amount'].replace(',','.')
        body={'kind':self.kind.currentData(),'data':data,'revision':self.current['revision'] if self.current else 0}
        if not self.pending or self.pending[0]!=body:self.pending=(deepcopy(body),str(uuid4()))
        body['request_id']=self.pending[1];self.busy=True
        self.call('PUT' if self.current else 'POST',N+'/life-items'+('/'+self.current['id'] if self.current else ''),body,lambda _:self.load_items())

    def delete_item(self):
        if not self.current:return
        if QMessageBox.question(self,'Item verwijderen','Wilt u dit item verwijderen?',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        self.call('DELETE',N+'/life-items/'+self.current['id']+'?revision='+str(self.current['revision']),None,lambda _:self.load_items())

    def remind_item(self):
        if self.current:self.call('POST',N+'/life-items/'+self.current['id']+'/reminder',{'revision':self.current['revision']},lambda row:self.status.setText({'queued':'Herinnering ingepland; agenda niet gewijzigd.','approval':'Het herinneringsvoorstel wacht op uw goedkeuring.','advisory':'Alleen een adviesvoorstel; geen herinnering actief.'}.get(row['status'],'Huidige taakstatus: '+row['status'])))

    def link_mail(self):
        if self.current and self.kind.currentData()=='application' and self.mail.text().strip():
            self.call('POST',N+'/life-items/'+self.current['id']+'/link-mail',{'revision':self.current['revision'],'message_id':self.mail.text().strip()},lambda _:self.load_items())

    def costs(self):
        def show(data):self.status.setText('Abonnementskosten per maand: '+(', '.join(currency+' '+amount for currency,amount in data['monthly_estimate'].items()) or 'nog niets ingevoerd')+'. Handmatige bedragen; geen bankkoppeling.')
        self.call('GET',N+'/financial-overview',None,show)

    def make_integrations(self):
        page=QWidget();box=QVBoxLayout(page);self.tabs.addTab(page,'Integraties en apparaten')
        refresh=QPushButton('Beschikbaarheid en apparaatstatus');refresh.clicked.connect(self.integrations);box.addWidget(refresh)
        owner=QPushButton('Host- en integratierechten als eigenaar');owner.clicked.connect(lambda:self.window.automation_panel.open_rights());box.addWidget(owner)
        self.integration_report=QPlainTextEdit();self.integration_report.setReadOnly(True);box.addWidget(self.integration_report)
        box.addWidget(plain('Home Assistant en routes gebruikt u pas na veilige configuratie op de server. Creality Cloud en Phone Link hebben hier geen ondersteunde publieke status-/oproepkoppeling.'))
        bar=QHBoxLayout();box.addLayout(bar);self.origin=QLineEdit();self.origin.setPlaceholderText('Vertrekplaats');bar.addWidget(self.origin);self.destination=QLineEdit();self.destination.setPlaceholderText('Bestemming');bar.addWidget(self.destination)
        route=QPushButton('Route opvragen');route.clicked.connect(self.route);bar.addWidget(route)
        costs=QFormLayout();box.addLayout(costs);self.distance=QDoubleSpinBox();self.distance.setRange(0,10000);self.liters=QDoubleSpinBox();self.liters.setRange(.1,100);self.liters.setValue(7);self.price=QDoubleSpinBox();self.price.setRange(.01,10);self.price.setValue(2)
        costs.addRow('Kilometers',self.distance);costs.addRow('Verbruik (liter / 100 km)',self.liters);costs.addRow('Zelf ingevoerde literprijs (€)',self.price)
        calculate=QPushButton('Ritkosten berekenen');calculate.clicked.connect(self.trip_cost);box.addWidget(calculate)

    def integrations(self):
        def show(data):
            home=data['home_assistant'];routes=data['routes'];self.integration_report.setPlainText('Home Assistant: '+('geconfigureerd' if home['configured'] else 'lokale beveiligde configuratie ontbreekt')+'\nRouteprovider: '+('geconfigureerd' if routes['configured'] else 'beveiligde sleutel ontbreekt')+'\nCreality Hi: geen publieke API geverifieerd.\nPhone Link: bediening blijft in Phone Link.\nRoutes zonder actuele verkeersdrukte.')
        self.call('GET',A+'/external',None,show)
        def devices(data):
            for item in data['items']:
                status=item['status'];battery=status.get('battery');details=[]
                if battery:details.append('batterij '+str(battery['value'])+'%'+(' (verouderd)' if battery['stale'] else ''))
                counts=status.get('notifications')
                if counts:details.append(str(sum(value['count'] for value in counts['value']))+' meldingen'+(' (verouderd)' if counts['stale'] else ''))
                if status.get('location'):details.append('locatie gedeeld'+(' (verouderd)' if status['location']['stale'] else ''))
                self.integration_report.appendPlainText('Apparaat: '+item['name']+' · '+', '.join(details))
        self.call('GET',N+'/device-status',None,devices)

    def route(self):
        self.call('POST',A+'/route-cities',{'origin':self.origin.text(),'destination':self.destination.text()},lambda data:(self.distance.setValue(data['distance_km']),self.integration_report.setPlainText('Route: '+data['origin']+' → '+data['destination']+'\nAfstand: '+str(round(data['distance_km'],1))+' km\nDuur: '+str(round(data['duration_seconds']/60))+' minuten. Geen live verkeer.')))

    def trip_cost(self):
        self.call('POST',A+'/trip-cost',{'distance_km':str(self.distance.value()),'liters_per_100km':str(self.liters.value()),'price_per_liter':str(self.price.value())},lambda data:self.integration_report.setPlainText('Geschat verbruik: '+data['liters']+' liter. Kosten: € '+data['estimated_fuel_cost_eur']+'. Eigen prijs; geen actuele pompprijs.'))
