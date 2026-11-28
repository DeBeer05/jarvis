"""Owner-selected local programs and folders for authenticated device commands."""
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QCheckBox,QPushButton,QLabel,QLineEdit,QListWidget,QFileDialog,QComboBox)

N='/api/v1/natural'

class DevicePanel(QWidget):
    def __init__(self,window):
        super().__init__(window);self.window=window;self.document=None;self.programs={};self.roots=[]
        box=QVBoxLayout(self);self.status=QLabel('Kies wat uw andere apparaten op deze computer mogen bedienen.');self.status.setWordWrap(True);box.addWidget(self.status)
        refresh=QPushButton('Instellingen van deze computer laden');refresh.clicked.connect(self.load);box.addWidget(refresh)
        self.enabled=QCheckBox('Opdrachten van mijn andere gekoppelde apparaten ontvangen');box.addWidget(self.enabled)
        self.media=QCheckBox('Mediabediening toestaan');box.addWidget(self.media)
        self.apps=QCheckBox('Toegestane programma’s openen en sluiten');box.addWidget(self.apps)
        self.names=QListWidget();box.addWidget(self.names)
        bar=QHBoxLayout();box.addLayout(bar);self.name=QLineEdit();self.name.setPlaceholderText('Programmanaam, bijvoorbeeld Kladblok');bar.addWidget(self.name)
        add=QPushButton('Programma kiezen');add.clicked.connect(self.add_program);bar.addWidget(add)
        folder=QPushButton('Documentmap toestaan');folder.clicked.connect(self.add_root);box.addWidget(folder)
        clear=QPushButton('Programma’s en mappen uit de lijst verwijderen');clear.clicked.connect(self.clear_allowlist);box.addWidget(clear)
        save=QPushButton('Mijn apparaatkeuze opslaan');save.clicked.connect(self.save);box.addWidget(save)
        note=QLabel('Alleen vaste Windows-acties zijn mogelijk. Uw automatiseringsrechten en vereiste goedkeuringen blijven gelden. Een onderbroken opdracht wordt niet opnieuw uitgevoerd.');note.setWordWrap(True);box.addWidget(note)
        self.target=QComboBox();self.target.addItem('Automatisch: eigen of enige beschikbare computer','');box.addWidget(self.target)
        choose=QPushButton('Geselecteerde standaardcomputer opslaan');choose.clicked.connect(self.choose_target);box.addWidget(choose)
        self.report=QLabel('');self.report.setWordWrap(True);box.addWidget(self.report)
        status=QPushButton('Oracle en verbonden apparaten controleren');status.clicked.connect(self.check);box.addWidget(status)
    def reset(self):
        self.document=None;self.programs={};self.roots=[];self.names.clear();self.enabled.setChecked(False);self.media.setChecked(False);self.apps.setChecked(False);self.report.clear();self.target.clear();self.target.addItem('Automatisch: eigen of enige beschikbare computer','')
    def load(self):
        def show(data):
            self.document=data;settings=data['settings'];policy=settings.get('execution_policy',{})
            self.programs=dict(policy.get('programs',{}));self.roots=list(policy.get('roots',[]))
            self.enabled.setChecked(settings.get('execution_allowed',False));self.media.setChecked(policy.get('media_allowed',False));self.apps.setChecked(policy.get('programs_allowed',False));self.render()
        self.window.call('GET',N+'/device-settings',None,show)
    def render(self):
        self.names.clear();self.names.addItems([name+': '+path for name,path in self.programs.items()]+self.roots)
    def add_program(self):
        name=self.name.text().strip()
        if not name:self.status.setText('Geef het programma een herkenbare naam.');return
        path,_=QFileDialog.getOpenFileName(self,'Toegestaan programma kiezen','','Windows-programma (*.exe)')
        if path:self.programs[name]=path;self.render()
    def add_root(self):
        path=QFileDialog.getExistingDirectory(self,'Toegestane documentmap kiezen')
        if path and path not in self.roots:self.roots.append(path);self.render()
    def clear_allowlist(self):self.programs={};self.roots=[];self.render()
    def save(self):
        if not self.document:self.status.setText('Laad eerst de huidige apparaatinstellingen.');return
        settings={**self.document['settings'],'execution_allowed':self.enabled.isChecked(),'execution_policy':{'enabled':self.enabled.isChecked(),'programs':self.programs,'roots':self.roots,'media_allowed':self.media.isChecked(),'programs_allowed':self.apps.isChecked()}}
        def saved(data):self.document=data;self.status.setText('Uw apparaatkeuze is opgeslagen. De server blijft opdrachten en rechten controleren.')
        self.window.call('PUT',N+'/device-settings',{'revision':self.document['revision'],'settings':settings},saved)
    def choose_target(self):
        target=self.target.currentData()
        def loaded(data):
            self.window.call('PATCH',N+'/settings/routing',{'revision':data['revision'],'changes':{'windows_device':target}},lambda _:self.status.setText('Uw standaardcomputer is opgeslagen. Bestaande rechten blijven vereist.'))
        self.window.call('GET',N+'/settings',None,loaded)
    def check(self):
        def show(data):
            self.target.clear();self.target.addItem('Automatisch: eigen of enige beschikbare computer','')
            for item in data['devices']['items']:
                if item['type']=='windows':self.target.addItem(item['name'],item['id'])
            self.report.setText('Oracle: '+('bereikbaar' if data['oracle']['available'] else 'niet bereikbaar')+'\nControlecentrum: '+data['hub']+'\n'+ '\n'.join(item['name']+': '+('bereikbaar' if item['online'] else 'geen recente verbinding') for item in data['devices']['items']))
        self.window.call('GET',N+'/hybrid/status',None,show)
