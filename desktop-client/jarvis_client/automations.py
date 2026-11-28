"""Native automation panel; requests use MainWindow's guarded worker bridge."""
import json
import hashlib
import time
from datetime import datetime
from uuid import uuid4

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QTabWidget,QPushButton,QLabel,
    QLineEdit,QComboBox,QPlainTextEdit,QListWidget,QListWidgetItem,QMessageBox,QDateTimeEdit,QCheckBox,QSpinBox)
from jarvis_client.integration_reads import IntegrationReads, plain_label

BASE="/api/v1/automation"


class AutomationPanel(QWidget):
    def __init__(self, window):
        super().__init__(window); self.window=window; self.seen=set(); self.items=[]
        layout=QVBoxLayout(self)
        heading=QLabel("Agenda, taken en goedkeuringen"); layout.addWidget(heading)
        self.access=plain_label("Log in om je agenda, e-mail en taken te gebruiken.");layout.addWidget(self.access)
        access_actions=QHBoxLayout();layout.addLayout(access_actions)
        self.rights=QPushButton("Apparaatrechten instellen als eigenaar");self.rights.clicked.connect(self.open_rights);access_actions.addWidget(self.rights)
        self.check_rights=QPushButton("Rechten vernieuwen");self.check_rights.clicked.connect(lambda:self.window.manager.check());access_actions.addWidget(self.check_rights)
        self.ai_button=QPushButton("Agenda en e-mail via AI-chat / spraak");self.ai_button.clicked.connect(self.open_chat);access_actions.addWidget(self.ai_button)
        self.tabs=QTabWidget();layout.addWidget(self.tabs)
        for title in ("Agenda","E-mail","Herinneringen","Automatiseringen","Goedkeuringen","Activiteit","Meldingsinstellingen","Gekoppelde accounts"):
            page=QWidget();box=QVBoxLayout(page)
            info=QLabel({"Agenda":"Kies je agenda en periode. Wijzigingen via AI blijven gecontroleerde voorstellen.","E-mail":"Zoek berichten en lees expliciet de inhoud. Verzenden vraagt aparte goedkeuring.","Herinneringen":"Stel hieronder een datum, tijd en tekst in.","Goedkeuringen":"Selecteer een voorstel en controleer de volledige gevolgen."}.get(title,"Gebruik de gedeelde takenlijst en de acties hieronder.")); info.setWordWrap(True);box.addWidget(info)
            self.tabs.addTab(page,title)
        self.calendar_view=IntegrationReads(window,"calendar");self.tabs.widget(0).layout().addWidget(self.calendar_view)
        self.mail_view=IntegrationReads(window,"mail");self.tabs.widget(1).layout().addWidget(self.mail_view)
        self.tabs.currentChanged.connect(self.filter_jobs)
        self.search=QLineEdit();self.search.setPlaceholderText("Zoekterm, Gmail-zoekopdracht of bericht-ID");layout.addWidget(self.search)
        self.read_bar=QWidget();reads=QHBoxLayout(self.read_bar);reads.setContentsMargins(0,0,0,0)
        for title,callback in (("Agenda komende week",self.calendar),("Inbox zoeken",lambda:self.call("/email/search","POST",{"query":self.search.text() or "in:inbox"},self.display)),("E-mail openen",self.read_mail),("Samenvatten",lambda:self.call("/summarize","POST",{"text":self.details.toPlainText()[:12000]},self.display))):
            b=QPushButton(title);b.clicked.connect(callback);reads.addWidget(b)
        layout.addWidget(self.read_bar)
        self.jobs=QListWidget();self.jobs.currentRowChanged.connect(self.show_selected);layout.addWidget(self.jobs)
        self.details=QPlainTextEdit(); self.details.setReadOnly(True);self.details.setMaximumHeight(140);layout.addWidget(self.details)
        actions=QHBoxLayout()
        for title,callback in (("Vernieuwen",self.refresh),("Goedkeuren",lambda:self.decide(True)),("Weigeren",lambda:self.decide(False)),("Pauzeren",lambda:self.control("paused")),("Hervatten",lambda:self.control("queued")),("Annuleren",lambda:self.control("cancelled")),('Herstelvoorstel',self.undo)):
            b=QPushButton(title);b.clicked.connect(callback);actions.addWidget(b)
        self.job_actions=QWidget();self.job_actions.setLayout(actions);layout.addWidget(self.job_actions)
        self.text=QLineEdit();self.text.setPlaceholderText("Waar wil je aan herinnerd worden?");layout.addWidget(self.text)
        self.reminder_bar=QWidget();reminder=QHBoxLayout(self.reminder_bar);reminder.setContentsMargins(0,0,0,0);self.at=QDateTimeEdit();self.at.setCalendarPopup(True)
        from PySide6.QtCore import QDateTime
        self.at.setDateTime(QDateTime.currentDateTime().addSecs(3600));reminder.addWidget(self.at)
        self.repeat=QComboBox();self.repeat.addItems(["once","daily","weekly"]);reminder.addWidget(self.repeat)
        b=QPushButton("Herinnering instellen");b.clicked.connect(self.remind);reminder.addWidget(b);layout.addWidget(self.reminder_bar)
        self.priority_bar=QWidget();schedule=QHBoxLayout(self.priority_bar);schedule.setContentsMargins(0,0,0,0);layout.addWidget(self.priority_bar)
        self.priority=QComboBox()
        for value,title in enumerate(('Laag','Normaal','Belangrijk','Urgent')):self.priority.addItem(title,value)
        self.priority.setCurrentIndex(1);schedule.addWidget(self.priority)
        self.deadline_enabled=QCheckBox('Deadline');schedule.addWidget(self.deadline_enabled)
        self.deadline=QDateTimeEdit();self.deadline.setCalendarPopup(True);self.deadline.setDateTime(QDateTime.currentDateTime().addDays(1));schedule.addWidget(self.deadline)
        self.deadline.setEnabled(False);self.deadline_enabled.toggled.connect(self.deadline.setEnabled)
        self.instruction=QLineEdit();self.instruction.setPlaceholderText("Beschrijf de taak die je wilt voorbereiden");layout.addWidget(self.instruction)
        self.plan_button=QPushButton("Voorstel voorbereiden");self.plan_button.clicked.connect(self.plan);layout.addWidget(self.plan_button)
        self.advanced=QCheckBox("Geavanceerde actiegegevens bekijken en bewerken");layout.addWidget(self.advanced)
        self.tool=QComboBox();self.tool.addItems(["CalendarRead","CalendarCreate","CalendarUpdate","CalendarDelete","EmailSearch","EmailRead","EmailDraft","EmailSend","WorkflowCreate","WorkflowStatus","NotificationSend"]);layout.addWidget(self.tool)
        self.payload=QPlainTextEdit("{}");self.payload.setPlaceholderText("Actiegegevens in JSON");self.payload.setMaximumHeight(100);layout.addWidget(self.payload)
        self.submit_button=QPushButton("Actievoorstel indienen");self.submit_button.clicked.connect(self.submit);layout.addWidget(self.submit_button)
        self.advanced.toggled.connect(lambda _:self.filter_jobs())
        self.policy_bar=QWidget();policy=QHBoxLayout(self.policy_bar)
        self.quiet_start=QSpinBox();self.quiet_start.setRange(0,23);self.quiet_start.setValue(22)
        self.quiet_end=QSpinBox();self.quiet_end.setRange(0,23);self.quiet_end.setValue(7)
        self.max_hour=QSpinBox();self.max_hour.setRange(1,60);self.max_hour.setValue(10)
        for title,field in (("Stil vanaf",self.quiet_start),("Stil tot",self.quiet_end),("Maximaal per uur",self.max_hour)):
            policy.addWidget(QLabel(title));policy.addWidget(field)
        save=QPushButton("Meldingsregels opslaan");save.clicked.connect(self.save_policy);policy.addWidget(save);layout.addWidget(self.policy_bar)
        self.account=QPushButton("Account koppelen / agenda zoeken in eigenaarinterface");self.account.clicked.connect(self.open_web);layout.addWidget(self.account)
        self.timer=QTimer(self);self.timer.setInterval(30000);self.timer.timeout.connect(self.poll);self.timer.start()
        self.filter_jobs()

    def clear(self):
        self.calendar_view.clear();self.mail_view.clear()
        self.jobs.clear();self.details.clear();self.payload.setPlainText("{}");self.text.clear();self.instruction.clear();self.search.clear();self.items=[];self.all_items=[];self.seen.clear()

    def set_authorized(self,permissions,online):
        allowed=online and "automation:read" in permissions
        self.calendar_view.set_authorized(allowed);self.mail_view.set_authorized(allowed)
        self.ai_button.setEnabled(online and "chat:write" in permissions)
        self.rights.setEnabled(online);self.check_rights.setEnabled(online)
        self.access.setText("Agenda en e-mail beschikbaar. Typ of spreek je vraag in Chat / Spraak." if allowed else "Dit Windows-apparaat mist automatiseringsrechten of is offline. Open als eigenaar Apparaatrechten en geef Bekijken (automation:read) en eventueel Taken maken (automation:write).")

    def open_rights(self):
        if self.window.manager.api and self.window.principal:
            identifier=self.window.principal["device_id"]
            QDesktopServices.openUrl(QUrl(self.window.manager.api.origin+"/automations#device="+identifier))

    def open_chat(self):
        if self.window.running:return
        self.window.navigate(0)
        if not self.window.composer.toPlainText().strip():self.window.composer.setPlainText("Wat staat er morgen in mijn agenda?")
        self.window.composer.setFocus()

    def call(self,path="",method="GET",body=None,done=None):
        self.window.call(method,BASE+path,body,done or (lambda _:self.refresh()))

    def refresh(self):
        p=self.window.principal
        if p and "automation:read" in p["permissions"] and self.window.manager.state=="online":self.call(done=self.loaded)

    def loaded(self,data):
        self.all_items=data["items"];self.filter_jobs()
        if self.tabs.currentIndex()==5:self.details.setPlainText(json.dumps(data["history"],ensure_ascii=False,indent=2))
        path=self.window.store.directory/"notification-cursors.json"
        try:cursors=json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        except (OSError,ValueError):cursors={}
        origin=hashlib.sha256(self.window.manager.api.origin.encode()).hexdigest()
        floor=cursors.get(origin,time.time())
        for note in data["notifications"]:
            if note["id"] not in self.seen and note["at"]>floor:
                self.seen.add(note["id"])
                # Lock-screen text remains generic; content is visible only in authenticated UI.
                if self.window.preferences.notifications:self.window.deliver_notification("JARVIS", "Er staat een melding klaar. Open Automatiseringen.")
        cursors[origin]=max([floor,*[n["at"] for n in data["notifications"]]])
        try:
            path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_suffix(".tmp")
            temporary.write_text(json.dumps(cursors),encoding="utf-8");temporary.replace(path)
        except OSError:self.window.show_notice("Meldingspositie kon niet worden bewaard; controleer schrijfrechten.")

    def poll(self):
        p=self.window.principal
        if p and "automation:read" in p["permissions"] and self.window.manager.state=="online":self.refresh()

    def selected(self):
        index=self.jobs.currentRow()
        return self.items[index] if 0<=index<len(self.items) else None

    def undo(self):
        row=self.selected()
        if row:self.call('/jobs/'+row['id']+'/undo','POST',{},lambda _:self.refresh())

    def filter_jobs(self,*_):
        section=self.tabs.currentIndex();rows=getattr(self,"all_items",[])
        if hasattr(self,"account"):
            for widget in (self.search,self.read_bar):widget.hide()
            for widget in (self.jobs,self.details,self.job_actions):widget.setVisible(section not in (0,1))
            self.tabs.setMaximumHeight(16777215 if section in (0,1) else 120)
            for widget in (self.text,self.reminder_bar):widget.setVisible(section==2)
            self.priority_bar.setVisible(section in (2,3))
            for widget in (self.instruction,self.plan_button,self.advanced):widget.setVisible(section==3)
            for widget in (self.tool,self.payload,self.submit_button):widget.setVisible(section==3 and self.advanced.isChecked())
            self.policy_bar.setVisible(section==6);self.account.setVisible(section==7)
        self.items=[r for r in rows if (section!=2 or r["tool"]=="ReminderCreate") and (section!=4 or r["status"]=="approval")]
        self.jobs.clear()
        for row in self.items:self.jobs.addItem(row["tool"]+" · "+row["status"])

    def save_policy(self):
        self.call("/notifications","PUT",{"quiet_start":self.quiet_start.value(),"quiet_end":self.quiet_end.value(),"max_hour":self.max_hour.value(),"timezone":"Europe/Amsterdam","categories":["urgent","appointments","important","news"]})

    def display(self,data):self.details.setPlainText(json.dumps(data,ensure_ascii=False,indent=2))

    def calendar(self):
        from datetime import timedelta
        start=datetime.now().astimezone()
        self.call("/calendar/search","POST",{"calendar_id":"primary","start":start.isoformat(),"end":(start+timedelta(days=7)).isoformat(),"query":self.search.text()},self.display)

    def read_mail(self):
        from urllib.parse import quote
        identifier=self.search.text().strip()
        if identifier:self.call("/email/"+quote(identifier,safe=""),done=self.display)

    def plan(self):
        def proposed(data):
            self.display(data)
            if "tool" in data:
                self.advanced.setChecked(True);self.tool.setCurrentText(data["tool"]);self.payload.setPlainText(json.dumps(data["input"],ensure_ascii=False,indent=2))
        if self.instruction.text().strip():self.call("/plan","POST",{"instruction":self.instruction.text()},proposed)

    def show_selected(self,index):
        row=self.selected()
        self.details.setPlainText(json.dumps(row,ensure_ascii=False,indent=2) if row else "")

    def decide(self,approve):
        row=self.selected()
        if not row or row["status"]!="approval":return
        if QMessageBox.question(self,"Exacte actie controleren",("Goedkeuren?\n" if approve else "Weigeren?\n")+json.dumps(row["payload"],ensure_ascii=False,indent=2))!=QMessageBox.StandardButton.Yes:return
        self.call("/jobs/"+row["id"]+"/challenge","POST",done=lambda data:self.call("/jobs/"+row["id"]+"/decision","POST",{"token":data["token"],"approve":approve}))

    def control(self,status):
        row=self.selected()
        if row:self.call("/jobs/"+row["id"]+"/control","POST",{"status":status})

    def remind(self):
        text=self.text.text().strip()
        if not text:return
        local=self.at.dateTime().toPython().astimezone()
        self.call("/jobs","POST",{"tool":"ReminderCreate","input":{"text":text,"at":local.isoformat(),"repeat":self.repeat.currentText(),"timezone":"Europe/Amsterdam"},"idempotency_key":str(uuid4()),'priority':self.priority.currentData(),**({'deadline':self.deadline.dateTime().toPython().astimezone().isoformat()} if self.deadline_enabled.isChecked() else {})})

    def submit(self):
        try: payload=json.loads(self.payload.toPlainText())
        except ValueError:return self.window.show_notice("Vul geldige JSON-actiegegevens in.")
        if QMessageBox.question(self,"Actie indienen",self.tool.currentText()+"\n"+json.dumps(payload,ensure_ascii=False,indent=2))!=QMessageBox.StandardButton.Yes:return
        self.call("/jobs","POST",{"tool":self.tool.currentText(),"input":payload,"idempotency_key":str(uuid4()),'priority':self.priority.currentData(),**({'deadline':self.deadline.dateTime().toPython().astimezone().isoformat()} if self.deadline_enabled.isChecked() else {})})

    def open_web(self):
        if self.window.manager.api:QDesktopServices.openUrl(QUrl(self.window.manager.api.origin+"/automations"))
